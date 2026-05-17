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

# 添加 Python 3.8 的 site-packages 路径（仅当实际使用 Python 3.8 时）
python38_site_packages = os.path.join(
    os.path.expanduser('~'),
    'AppData', 'Roaming', 'Python', 'Python38', 'site-packages'
)
if sys.version_info[:2] == (3, 8) and os.path.exists(python38_site_packages):
    sys.path.insert(0, python38_site_packages)
    print(f"Added Python 3.8 site-packages: {python38_site_packages}")

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# 数据库
from database import db, init_db
from database.crud import (
    get_all_cases, get_case_by_id,
    get_all_gangs, get_gang_by_id,
    get_sessions, get_session_detail,
    search_cases, delete_session
)

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

# 数据库配置
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "20051223")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
init_db(app)

# 初始化认证
from database.auth import init_auth, register_routes, log_operation
init_auth(app)
register_routes(app)

# 创建默认管理员账号
from database.models import User
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', display_name='系统管理员', role='admin', department='反诈中心')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ 默认管理员账号已创建 (admin/admin123)")

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
    db_ok = False
    try:
        from database.models import Case
        Case.query.first()
        db_ok = True
    except:
        pass
    return jsonify({
        "status": "healthy",
        "service": "AI反诈研判官系统",
        "version": "2.1",
        "database": "connected" if db_ok else "disconnected",
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


# ========== CRUD API ==========

@app.route('/api/cases', methods=['GET'])
def api_get_cases():
    """获取所有案件"""
    try:
        cases = get_all_cases()
        return jsonify({"success": True, "cases": cases, "total": len(cases)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cases/<case_id>', methods=['GET'])
def api_get_case(case_id):
    """获取单个案件详情"""
    try:
        case = get_case_by_id(case_id)
        if case:
            return jsonify({"success": True, "case": case})
        return jsonify({"success": False, "error": "案件不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/gangs', methods=['GET'])
def api_get_gangs():
    """获取所有团伙"""
    try:
        gangs = get_all_gangs()
        return jsonify({"success": True, "gangs": gangs, "total": len(gangs)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/gangs/<gang_id>', methods=['GET'])
def api_get_gang(gang_id):
    """获取单个团伙详情"""
    try:
        gang = get_gang_by_id(gang_id)
        if gang:
            return jsonify({"success": True, "gang": gang})
        return jsonify({"success": False, "error": "团伙不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def api_get_sessions():
    """获取分析会话列表"""
    try:
        sessions = get_sessions()
        return jsonify({"success": True, "sessions": sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def api_get_session_detail(session_id):
    """获取分析会话详情（含案件和团伙数据）"""
    try:
        detail = get_session_detail(session_id)
        if detail:
            return jsonify({"success": True, **detail})
        return jsonify({"success": False, "error": "会话不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def api_delete_session(session_id):
    """删除分析会话及其关联数据"""
    try:
        delete_session(session_id)
        return jsonify({"success": True, "message": "删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/search', methods=['GET'])
def api_search():
    """搜索案件"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({"success": True, "cases": []})
        cases = search_cases(query)
        return jsonify({"success": True, "cases": cases, "total": len(cases)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== Case Status ==========

@app.route('/api/cases/<case_id>/status', methods=['PUT'])
@jwt_required()
def api_update_case_status(case_id):
    try:
        from database.crud import update_case_status
        data = request.json
        new_status = data.get('status', '')
        if not new_status:
            return jsonify({"success": False, "error": "缺少状态参数"}), 400
        result = update_case_status(case_id, new_status)
        claims = get_jwt()
        log_operation(int(get_jwt_identity()), claims.get('username', ''),
                      'update_status', 'case', case_id, {'new_status': new_status})
        return jsonify({"success": True, "case": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cases/stats', methods=['GET'])
def api_case_stats():
    try:
        from database.crud import get_case_stats
        stats = get_case_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== Merge Suggestions ==========

@app.route('/api/merges/suggest', methods=['POST'])
@jwt_required()
def api_suggest_merges():
    try:
        from database.merge import suggest_merges
        from database.crud import get_all_cases
        cases = get_all_cases()
        result = suggest_merges(cases)
        return jsonify({"success": True, "suggestions": result, "total": len(result)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/merges/confirm', methods=['POST'])
@jwt_required()
def api_confirm_merge():
    try:
        from database.merge import confirm_merge
        data = request.json
        result = confirm_merge(
            data.get('case_id_a', ''),
            data.get('case_id_b', ''),
            data.get('gang_id', ''),
            int(get_jwt_identity())
        )
        claims = get_jwt()
        log_operation(int(get_jwt_identity()), claims.get('username', ''),
                      'confirm_merge', 'merge', f"{data['case_id_a']}+{data['case_id_b']}")
        return jsonify({"success": True, "message": "合并成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/merges/pending', methods=['GET'])
@jwt_required()
def api_pending_merges():
    try:
        from database.merge import get_pending_merges
        suggestions = get_pending_merges()
        return jsonify({"success": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== Reports ==========

@app.route('/api/reports/case/<case_id>', methods=['GET'])
def api_case_report(case_id):
    try:
        from database.report import generate_case_report, export_case_docx
        fmt = request.args.get('format', 'pdf')
        if fmt == 'docx':
            filepath = export_case_docx(case_id)
        else:
            filepath = generate_case_report(case_id)
        filename = os.path.basename(filepath)
        return jsonify({
            "success": True,
            "file_path": f"/api/reports/download/{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/reports/gang/<gang_id>', methods=['GET'])
def api_gang_report(gang_id):
    try:
        from database.report import generate_gang_report
        filepath = generate_gang_report(gang_id)
        filename = os.path.basename(filepath)
        return jsonify({
            "success": True,
            "file_path": f"/api/reports/download/{filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/reports/download/<filename>', methods=['GET'])
def api_download_report(filename):
    try:
        from flask import send_from_directory
        reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        return send_from_directory(reports_dir, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== Enhanced Search ==========

@app.route('/api/search/advanced', methods=['GET'])
def api_advanced_search():
    try:
        from database.crud import search_cases
        entity_type = request.args.get('type', '')
        entity_value = request.args.get('value', '')
        if not entity_type or not entity_value:
            return jsonify({"success": False, "error": "请指定搜索类型和关键词"}), 400

        from database.models import Case
        cases = Case.query.order_by(Case.created_at.desc()).all()
        results = []
        for c in cases:
            entities = c.extracted_entities or {}
            if entity_type == 'phone' and entity_value in str(entities.get('phone_numbers', [])):
                results.append(c)
            elif entity_type == 'bank' and entity_value in str(entities.get('bank_accounts', [])):
                results.append(c)
            elif entity_type == 'ip' and entity_value in str(entities.get('ip_addresses', [])):
                results.append(c)
            elif entity_type == 'app' and entity_value in str(entities.get('app_names', [])):
                results.append(c)

        from database.crud import _case_to_dict
        return jsonify({
            "success": True,
            "cases": [_case_to_dict(c) for c in results],
            "total": len(results)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== Operation Logs (public read) ==========

@app.route('/api/logs', methods=['GET'])
def api_public_logs():
    try:
        from database.models import OperationLog
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(50).all()
        return jsonify({
            "success": True,
            "logs": [{
                'id': l.id,
                'username': l.username,
                'action': l.action,
                'target': f"{l.target_type}/{l.target_id}",
                'created_at': l.created_at.isoformat() if l.created_at else None
            } for l in logs]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 AI 反诈研判官系统 v2.1 启动")
    print("=" * 60)
    print("🔧 配置信息:")
    print(f"   - 数据库: MySQL ({DB_HOST}:{DB_PORT}/{DB_NAME})")
    print(f"   - 并发数: {MAX_WORKERS}")
    print(f"   - LLM超时: {LLM_REQUEST_TIMEOUT}s")
    print(f"   - 线程等待: {THREAD_WAIT_TIMEOUT}s")
    print(f"   - Agent架构: 三层智能体架构")
    print(f"   - 团伙发现: BGE → UMAP → HDBSCAN")
    print(f"   - WebSocket: 已启用")
    print("=" * 60)
    print("🌐 可用接口:")
    print("   POST /agent-analyze   (智能研判分析)")
    print("   POST /upload          (传统分析)")
    print("   GET  /health          (健康检查)")
    print("   GET  /api/cases       (案件列表)")
    print("   GET  /api/cases/<id>  (案件详情)")
    print("   GET  /api/gangs       (团伙列表)")
    print("   GET  /api/gangs/<id>  (团伙详情)")
    print("   GET  /api/sessions    (会话列表)")
    print("   GET  /api/sessions/<id> (会话详情)")
    print("   DELETE /api/sessions/<id> (删除会话)")
    print("   GET  /api/search?q=   (搜索案件)")
    print("   GET  /api/network-data (网络数据)")
    print("   WebSocket /socket.io  (实时进度推送)")
    print("=" * 60)

    socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
