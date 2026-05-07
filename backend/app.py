"""
AI 反诈研判官系统 (Agent 架构)
版本: 2.0
架构: 三层智能体架构
- 交互层: Web前端 (Vue.js)
- 决策与协同层: 反诈研判官Agent (AntiFraudChiefAgent)
- 感知与执行层: 专家工具集 (IntelligentGangDiscoverer, DataPreprocessor, 等)
"""

import sys
import os
import json
import traceback
import time
import uuid

# 添加 Python 3.8 的 site-packages 路径（包含 langchain 相关包）
python38_site_packages = os.path.join(
    os.path.expanduser('~'),
    'AppData', 'Roaming', 'Python', 'Python38', 'site-packages'
)
sys.path.insert(0, python38_site_packages)
print(f"Added Python 3.8 site-packages: {python38_site_packages}")

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# LLM 相关
try:
    from langchain_community.llms import Tongyi
    from dotenv import load_dotenv
    print("langchain imports successful")
except ImportError as e:
    print(f"Error importing langchain: {e}")
    # 模拟 langchain 模块
    class MockTongyi:
        def __init__(self, **kwargs):
            pass
        def invoke(self, prompt, **kwargs):
            import time
            time.sleep(1)  # 模拟延迟
            return """【案件研判结论】\n1. 【案件定性】：刷单返利类诈骗\n2. 【关键证据】：刷单、返利、任务、提现\n3. 【作案流程】：引流 -> 小额返利 -> 大额投入 -> 无法提现\n4. 【处置建议】：立即冻结涉案账户，联系受害人止损\n{"risk_level": "High", "scam_type": "刷单返利类 - 刷单返利类", "victim_name": "张先生", "amount": "5000元", "evidence": {"keywords": ["刷单", "返利", "提现"], "accounts": [], "links": [], "apps": []}, "roles": [{"role": "Suspect", "characteristics": ["主动引导", "要求转账"], "typical_phrases": ["做任务", "返利"]}, {"role": "Victim", "characteristics": ["顺从", "执行操作"], "typical_phrases": ["好的", "已转账"]}], "timeline": ["引流", "小额返利", "大额投入"]}"""
    Tongyi = MockTongyi
    # 模拟 dotenv
    class MockDotenv:
        @staticmethod
        def load_dotenv():
            pass
    load_dotenv = MockDotenv.load_dotenv

# 导入新的Agent架构
from agents.chief_agent import ChiefAgent
from agents.base import AgentContext, AgentConfig

# 初始化Flask应用
app = Flask(__name__)
load_dotenv()
CORS(app, origins=['http://localhost:5173'])

# 配置WebSocket
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173", async_mode='threading')

# 存储会话信息
active_sessions = {}

# 配置参数
api_key = os.getenv("DASHSCOPE_API_KEY", "mock-key")
if not api_key or api_key == "":
    print("⚠️ 警告：未找到 DASHSCOPE_API_KEY 环境变量，将使用模拟模式")

# 超时配置
LLM_REQUEST_TIMEOUT = 30
THREAD_WAIT_TIMEOUT = 35
MAX_WORKERS = 5

# 初始化模型
llm_analyze = None
llm_triage = None
try:
    llm_analyze = Tongyi(
        model_name="qwen-max",
        temperature=0.1,
        request_timeout=LLM_REQUEST_TIMEOUT
    )
    llm_triage = Tongyi(
        model_name="qwen-turbo",
        temperature=0.1,
        request_timeout=LLM_REQUEST_TIMEOUT
    )
    print(f"✅ 双模型初始化成功！(Timeout: {LLM_REQUEST_TIMEOUT}s, Workers: {MAX_WORKERS})")
except Exception as e:
    print(f"⚠️ 模型初始化警告：{e}，将使用模拟模式")

# WebSocket连接处理
@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    print(f"🔌 WebSocket 连接建立: {session_id}")
    active_sessions[session_id] = {
        'connected': True,
        'start_time': time.time()
    }
    emit('connected', {'message': '连接成功', 'session_id': session_id})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    print(f"🔌 WebSocket 连接断开: {session_id}")
    if session_id in active_sessions:
        del active_sessions[session_id]

@socketio.on('analysis_progress')
def handle_progress(data):
    """接收并转发进度消息"""
    session_id = request.sid
    print(f"📤 进度更新: {session_id} -> {data}")


@app.route('/upload', methods=['POST'])
async def upload_and_analyze():
    """
    传统分析接口 (向后兼容)
    保持原有的处理逻辑，但不使用智能团伙发现
    """
    try:
        data = request.json
        raw_messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})

        if not raw_messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400

        print("🧹 正在清洗和标准化数据...")
        # 这里可以调用PreprocessAgent，但为了保持兼容性，使用简化版本
        from agents.preprocess_agent import PreprocessAgent
        preprocess_agent = PreprocessAgent(AgentConfig(agent_id="PreprocessAgent"))
        preprocess_result = await preprocess_agent.process({
            'messages': raw_messages,
            'platform_data': platform_data
        }, AgentContext(session_id=str(uuid.uuid4()), trace_id=str(uuid.uuid4())))
        cleaned_messages = preprocess_result.get('standardized_messages', [])
        text_messages = preprocess_result.get('text_messages', [])

        print("🔪 正在智能分案...")
        from agents.triage_agent import TriageAgent
        triage_agent = TriageAgent(AgentConfig(agent_id="TriageAgent"), llm_triage)
        triage_result = await triage_agent.process({
            'text_messages': text_messages
        }, AgentContext(session_id=str(uuid.uuid4()), trace_id=str(uuid.uuid4())))
        splits = triage_result.get('splits', [])
        is_triage_failed = triage_result.get('is_triage_failed', False)
        if is_triage_failed:
            for s in splits:
                s['is_failed'] = True

        all_results = []
        print(f"🚀 启动并行处理，共 {len(splits)} 个案件 (并发:{MAX_WORKERS}, 超时:{THREAD_WAIT_TIMEOUT}s)...")

        from agents.analyst_agent import AnalystAgent
        analyst_agent = AnalystAgent(AgentConfig(agent_id="AnalystAgent"), llm_analyze)

        import asyncio
        
        async def process_case(split):
            return await analyst_agent.process({
                'split': split,
                'text_messages': text_messages
            }, AgentContext(session_id=str(uuid.uuid4()), trace_id=str(uuid.uuid4())))

        async def process_all_cases():
            tasks = []
            for split in splits:
                task = asyncio.create_task(process_case(split))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    print(f'❌ [Case {splits[i].get("case_id", "Unknown")}] 处理发生异常：{error_msg}')
                    split = splits[i]
                    start_idx = split.get('start', 0)
                    end_idx = split.get('end', 0)
                    fallback_result = {
                        "case_id": split.get('case_id', 'unknown'),
                        "message_count": max(0, end_idx - start_idx + 1),
                        "time_range": f"{start_idx} - {end_idx}",
                        "risk_level": "UNKNOWN",
                        "risk_label": "未知",
                        "risk_type": "danger",
                        "risk_score": 0,
                        "scam_type": "系统异常",
                        "victim": "未知",
                        "amount": "未知",
                        "ai_report": f"⚠️ 处理出错：{error_msg}",
                        "keywords": ["Error"],
                        "steps": [],
                        "warning": f"处理出错：{error_msg}",
                        "is_error": True,
                        "roles": [],
                        "extracted_entities": {
                            "bank_accounts": [],
                            "phone_numbers": [],
                            "ip_addresses": [],
                            "app_names": [],
                            "threat_intel": {}
                        }
                    }
                    all_results.append(fallback_result)
                else:
                    all_results.append(result)
                    print(f"✅ [Case {result.get('case_id', 'Unknown')}] 处理完成")
        
        await process_all_cases()

        all_results.sort(key=lambda x: x.get('case_id', 9999))
        has_errors = any(r.get('is_error', False) for r in all_results)

        return jsonify({
            "success": True,
            "total_cases": len(all_results),
            "triage_status": "failed" if is_triage_failed else "success",
            "results": all_results,
            "warning": "部分案件处理超时或失败，请检查日志" if has_errors else None
        })

    except Exception as e:
        print(f"❌ 服务器内部致命错误：{e}")
        traceback.print_exc()
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/agent-analyze', methods=['POST'])
async def agent_analyze():
    """
    Agent智能研判接口 (推荐使用)
    使用完整的Agent架构进行智能研判，支持WebSocket实时进度推送
    """
    try:
        data = request.json
        raw_messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})
        session_id = data.get('session_id', str(uuid.uuid4()))

        if not raw_messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400

        print("=" * 60)
        print("🚀 反诈研判官Agent启动智能研判流程...")
        print(f"📡 会话ID: {session_id}")
        print("=" * 60)

        # 创建ChiefAgent（带WebSocket支持）
        chief_agent = ChiefAgent(
            AgentConfig(agent_id="ChiefAgent"),
            llm_analyze,
            llm_triage,
            socketio=socketio,
            session_id=session_id
        )

        # 调用ChiefAgent进行智能研判
        context = AgentContext(
            session_id=session_id,
            trace_id=str(uuid.uuid4())
        )
        result = await chief_agent.process({
            'messages': raw_messages,
            'platform_data': platform_data
        }, context)

        print("=" * 60)
        print(f"✅ 智能研判完成！状态: {'成功' if result.get('success') else '失败'}")
        if result.get('success'):
            print(f"   发现案件: {result.get('total_cases', 0)} 个")
            print(f"   识别团伙: {len(result.get('gangs', []))} 个")
            print(f"   处理耗时: {result.get('processing_info', {}).get('processing_time_ms', 0)}ms")
        print("=" * 60)

        # 通过WebSocket发送最终结果通知
        try:
            socketio.emit('analysis_complete', {
                'success': result.get('success'),
                'total_cases': result.get('total_cases', 0),
                'total_gangs': len(result.get('gangs', [])),
                'trace_id': context.trace_id
            }, room=session_id)
        except Exception as e:
            print(f"⚠️ WebSocket发送完成通知失败: {e}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Agent路由错误: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "AI反诈研判官系统",
        "version": "2.0",
        "agent_status": "active",
        "models": {
            "qwen_max": "active" if llm_analyze else "inactive",
            "qwen_turbo": "active" if llm_triage else "inactive"
        },
        "websocket_enabled": True,
        "active_sessions": len(active_sessions)
    })


@app.route('/api/network-data', methods=['GET'])
def get_network_data():
    """网络数据接口示例"""
    return jsonify({
        "success": True,
        "message": "此接口需要基于会话或数据库实现完整功能",
        "sample_data": {
            "nodes": [
                {"id": "GANG_001", "name": "示例团伙", "type": "gang", "value": 50000},
                {"id": "CASE_001", "name": "示例案件", "type": "case", "value": 15000, "gang_id": "GANG_001"}
            ],
            "links": [
                {"source": "GANG_001", "target": "CASE_001", "value": 15000}
            ]
        }
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 AI 反诈研判官系统 v2.0 启动")
    print("=" * 60)
    print("🔧 配置信息:")
    print(f"   - 并发数: {MAX_WORKERS}")
    print(f"   - LLM超时: {LLM_REQUEST_TIMEOUT}s")
    print(f"   - 线程等待: {THREAD_WAIT_TIMEOUT}s")
    print(f"   - Agent架构: 三层智能体架构")
    print(f"   - 团伙发现: BGE + HDBSCAN 智能聚类")
    print(f"   - WebSocket: 已启用")
    print("=" * 60)
    print("🌐 可用接口:")
    print("   - POST /upload        (传统分析，向后兼容)")
    print("   - POST /agent-analyze (智能分析，推荐使用)")
    print("   - GET  /health        (健康检查)")
    print("   - GET  /api/network-data (网络数据)")
    print("   - WebSocket /socket.io (实时进度推送)")
    print("=" * 60)

    # 使用socketio启动应用
    socketio.run(app, debug=False, port=5000, host='0.0.0.0')
