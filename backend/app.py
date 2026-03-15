from flask import Flask, request, jsonify
from flask_cors import CORS
from tools import engine
import os
import json
import re
import traceback
from langchain_community.llms import Tongyi
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

app = Flask(__name__)
load_dotenv()
CORS(app)

# ====== 1. 配置 API Key ======
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 错误：未找到 DASHSCOPE_API_KEY 环境变量！")
    # 生产环境建议在此处退出，防止后续报错
else:
    print("✅ API Key 加载成功")

# 🔥【核心优化】全局超时配置 (单位：秒)
LLM_REQUEST_TIMEOUT = 30  # 单个 AI 请求的最大等待时间 (底层网络超时)
THREAD_WAIT_TIMEOUT = 35  # 线程池等待结果的最大时间 (略大于 LLM 超时，作为最后防线)
MAX_WORKERS = 5  # 最大并发线程数

# ====== 2. 初始化 Qwen 模型 (带超时配置) ======
llm_analyze = None
llm_triage = None

try:
    # 🔥【优化】添加 request_timeout 参数
    # 研判用最强模型
    llm_analyze = Tongyi(
        model_name="qwen-max",
        temperature=0.1,
        request_timeout=LLM_REQUEST_TIMEOUT
    )
    # 分案用最快模型 (turbo 速度极快，适合逻辑分类)
    llm_triage = Tongyi(
        model_name="qwen-turbo",
        temperature=0.1,
        request_timeout=LLM_REQUEST_TIMEOUT
    )
    print(f"✅ 双模型初始化成功！(Timeout: {LLM_REQUEST_TIMEOUT}s, Workers: {MAX_WORKERS})")
except Exception as e:
    print(f"❌ 模型初始化失败：{e}")

# ====== 3. 系统提示词 (保持不变) ======
SYSTEM_PROMPT_TEMPLATE = """
# Role
你是一名拥有 10 年经验的反诈中心资深研判专家。你的核心能力是从混乱对话中精准识别诈骗剧本、区分嫌疑人与受害人角色，并输出民警可直接使用的办案依据。

# Context
输入是一段包含受害者与骗子混合对话的聊天记录片段（可能经过聚类整理）。请忽略任何聚类标签，按语义逻辑重组对话。

# Knowledge Base (2025 版反诈分类标准)
请严格依据以下诈骗分类体系进行判断（这是国家反诈中心 APP 标准）：
- 冒充电商物流客服类：冒充电商客服、冒充物流客服、其他
- 冒充公检法及政府机关类：冒充公检法、冒充其他单位组织
- 刷单返利类：刷单返利类
- 贷款、代办信用卡类：虚假贷款、虚假代办信用卡、虚假提额套现、其他
- 冒充军警购物类：冒充军警购物诈骗
- 虚假网络投资理财类：虚假网络投资理财
- 虚假购物、服务类：虚假购物、虚假服务、其他
- 网络婚恋、交友类：冒充外国军人、网络婚恋、网络交友、其他
- 虚假征信类：消除校园贷记录、消除不良记录、其他
- 冒充领导、熟人等特定身份类：冒充领导、冒充熟人、冒充公众人物、冒充其他身份
- 网络游戏产品虚假交易类：游戏币点卡虚假充值、游戏账号装备虚假交易、其他
- 其他类型诈骗：虚假中奖诈骗、虚假招聘、充值 (红包) 返利、机票退改签诈骗、PS 图片诈骗、重金求子 (慈善捐款)、其他

# Tasks
## Step 1: 角色自动分离
- 识别【嫌疑人】(诈骗方) 和 【受害人】(被诱导方)
- 嫌疑人特征：主动引导、伪造身份（如公检法/客服/军警）、要求转账、制造恐慌、提及"安全账户"、"资金核查"、"做任务"、"内幕消息"、"FaceTime"、"屏幕共享"。
- 受害人特征：疑惑、顺从、被恐吓、执行操作、询问"怎么办"。

## Step 2: 诈骗深度研判
- 识别具体诈骗类型：必须从上述《Knowledge Base》中选择最匹配的 **大类** 和 **小类**。
- 提取关键证据链：敏感词、账号、APP、话术。
- 评估风险等级：
  - High：涉及转账、屏幕共享、下载特定 APP、提供验证码。
  - Medium：涉及个人信息泄露、诱导点击链接。
  - Low：仅是引流话术，未涉及实质性操作。

## Step 3: 严格输出格式
### Part A: 《案件研判结论》
[必须包含]
1. 【案件定性】：一句话概括类型（例：冒充电商物流客服类 - 冒充电商客服）。
2. 【关键证据】：3-5 个最具定罪价值的关键词（如：屏幕共享、安全账户、消除记录）。
3. 【作案流程】：按时间顺序简述核心步骤（例：引流 -> 恐吓/诱惑 -> 诱导操作 -> 转账）。
4. 【处置建议】：具体行动指令（例：立即止付、冻结涉案账户、联系受害人拦截）。

### Part B: 结构化数据 (JSON)
{{
  "risk_level": "High/Medium/Low",
  "scam_type": "诈骗大类 - 诈骗小类 (例如：冒充公检法及政府机关类 - 冒充公检法)",
  "evidence": {{
    "keywords": ["关键词 1", "关键词 2"],
    "accounts": ["卡号/账号"],
    "links": ["可疑链接"],
    "apps": ["涉及 APP"]
  }},
  "roles": [
    {{
      "role": "Suspect",
      "characteristics": ["特征 1", "特征 2"],
      "typical_phrases": ["典型话术 1", "典型话术 2"]
    }},
    {{
      "role": "Victim",
      "characteristics": ["特征 1", "特征 2"],
      "typical_phrases": ["典型话术 1", "典型话术 2"]
    }}
  ],
  "timeline": ["步骤 1", "步骤 2", "步骤 3"]
}}

# Constraints
- 严禁输出 Markdown 代码块标记 (如 ```json 或 ```markdown)。
- JSON 必须合法可解析，且必须是响应中的最后一部分，不要有任何其他文字跟随。
- 用简体中文。
- 仅输出 Part A + Part B。
- 如果输入为空或无法识别，请在 JSON 中返回 "scam_type": "无法识别"。

# Input Data
{context_data}

# Output
"""


# ====== 4. 数据预处理模块 ======
class DataPreprocessor:
    """
    负责清洗和标准化输入数据，是系统的"消化系统"。
    """

    @staticmethod
    def clean_text(text):
        """清洗文本：去除多余空格、换行，标准化时间格式"""
        if not isinstance(text, str):
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        return text

    @staticmethod
    def standardize_message_format(raw_messages):
        """
        将各种格式的输入统一转换为标准列表。
        """
        standardized = []

        for msg in raw_messages:
            # 情况 A: 纯字符串
            if isinstance(msg, str):
                content = DataPreprocessor.clean_text(msg)
                if content:
                    standardized.append({
                        "content": content,
                        "sender": "unknown",
                        "timestamp": None
                    })

            # 情况 B: 字典对象
            elif isinstance(msg, dict):
                content = msg.get('content', msg.get('text', ''))
                content = DataPreprocessor.clean_text(content)

                if content:
                    sender = msg.get('sender', msg.get('role', 'unknown'))
                    timestamp = msg.get('time', msg.get('timestamp', None))

                    standardized.append({
                        "content": content,
                        "sender": sender,
                        "timestamp": timestamp
                    })

            # 情况 C: 图片或其他媒体 (模拟 OCR)
            elif isinstance(msg, dict) and msg.get('type') == 'image':
                ocr_text = "【图片内容】检测到转账或验证码信息"
                standardized.append({
                    "content": ocr_text,
                    "sender": "unknown",
                    "timestamp": None
                })

        return standardized

    @staticmethod
    def extract_key_info_from_platform(data):
        """
        专门处理国家反诈平台的举报数据。
        """
        platform_info = []
        fields_to_extract = [
            ('诈骗类型', 'scam_type'),
            ('诈骗电话', 'phone'),
            ('APP 应用程序', 'app_name'),
            ('诈骗网址', 'url'),
            ('诈骗交易账户', 'account')
        ]

        for label, key in fields_to_extract:
            value = data.get(key)
            if value and value not in ['请选择', '请填写', '']:
                platform_info.append(f"【平台关键线索】{label}: {value}")

        return platform_info


# ====== 5. 智能分案函数 ======
def ai_triage_cases(text_messages):
    """使用 Qwen-Turbo 进行案件分案"""
    total_len = len(text_messages)

    # 边界情况：消息太少，不需要分案
    if total_len < 5:
        return [{"case_id": 1, "start": 0, "end": total_len - 1}], False

    # 1. 准备上下文
    MAX_CONTEXT = 200
    if total_len > MAX_CONTEXT:
        print(f"⚠️ 消息过长 ({total_len}条)，截取前 {MAX_CONTEXT} 条进行分案分析")
        sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages[:MAX_CONTEXT])])
        is_truncated = True
    else:
        sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages)])
        is_truncated = False

    # 2. 构建分案 Prompt
    prompt = f"""
# Role
你是一名拥有 10 年经验的反诈中心情报分析师。任务是对混杂聊天记录进行“案件串并”分析。

# Input Data
以下是按时间顺序排列的聊天记录片段：
{sample_text}
{'(注：数据已被截断，仅展示前 200 条)' if is_truncated else ''}

# Core Rules
1. **必须切割**：完全不同的诈骗剧本、不同的受害人身份、时间断层>7 天且无延续。
2. **必须合并**：同一剧本的自然演变、同一资金流的追索。
3. **输出格式**：仅输出一个标准的 JSON 数组，包含 case_id, start, end, reason。不要有任何 Markdown 标记。

# Output Example
[{{"case_id": 1, "start": 0, "end": 45, "reason": "刷单返利诱导期"}}, {{"case_id": 2, "start": 46, "end": 98, "reason": "转为冒充公检法恐吓"}}]

# Action
请分析上述数据，输出 JSON 数组：
"""

    try:
        if not llm_triage:
            raise Exception("LLM 未初始化")

        print("🤖 正在调用 Qwen-turbo 进行智能分案...")
        response = llm_triage.invoke(prompt)

        # 3. 清洗响应内容
        raw_text = response.strip()

        # 移除 Markdown 代码块标记
        clean_text = re.sub(r'```json\s*|```\s*', '', raw_text)

        # 4. 稳健的 JSON 提取逻辑
        json_obj = None
        try:
            json_obj = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            if match:
                try:
                    json_obj = json.loads(match.group())
                except:
                    pass

        if not json_obj or not isinstance(json_obj, list):
            raise ValueError("AI 返回的数据不是合法的 JSON 数组")

        # 5. 数据校验与修复
        splits = []
        for i, item in enumerate(json_obj):
            start = int(item.get('start', 0))
            end = int(item.get('end', 0))

            if start < 0: start = 0
            if end >= total_len: end = total_len - 1
            if start > end: start, end = end, start

            splits.append({
                "case_id": i + 1,
                "start": start,
                "end": end,
                "reason": item.get('reason', '自动分案')
            })

        if not splits:
            raise ValueError("AI 返回了空列表")

        splits.sort(key=lambda x: x['start'])

        if splits[0]['start'] != 0:
            splits[0]['start'] = 0

        for i in range(len(splits) - 1):
            if splits[i]['end'] + 1 < splits[i + 1]['start']:
                splits[i]['end'] = splits[i + 1]['start'] - 1

        if splits[-1]['end'] < total_len - 1:
            splits[-1]['end'] = total_len - 1

        print(f"✅ 分案成功：识别出 {len(splits)} 个案件")
        return splits, False

    except Exception as e:
        print(f"⚠️ AI 分案失败：{e}")
        # 降级策略：返回整个文本作为一个案件
        return [{"case_id": 1, "start": 0, "end": total_len - 1}], True


# ====== 6. 多模态清洗函数 (兼容旧逻辑) ======
def process_multimodal_data(raw_messages):
    cleaned_messages = []
    for msg in raw_messages:
        content = ""
        if isinstance(msg, dict):
            content = msg.get('content', '')
        elif isinstance(msg, str):
            content = msg
        else:
            continue

        if not isinstance(content, str):
            content = str(content)

        if isinstance(msg, dict) and msg.get('type') == 'image':
            content = f"[图片内容] 检测到转账或验证码信息"

        cleaned_messages.append(content)
    return cleaned_messages


# 🔥【新增】辅助函数：生成统一的“失败/超时”结果
def _create_fallback_result(split, error_msg):
    """
    当案件超时或报错时，返回一个符合前端格式的占位对象
    """
    start_idx = split.get('start', 0)
    end_idx = split.get('end', 0)
    case_text_count = max(0, end_idx - start_idx + 1)

    return {
        "case_id": split.get('case_id', 'unknown'),
        "message_count": case_text_count,
        "time_range": f"{start_idx} - {end_idx}",
        "risk_level": "UNKNOWN",
        "risk_label": "未知",
        "risk_type": "danger",
        "risk_score": 0,
        "scam_type": "系统异常",
        "ai_report": f"⚠️ {error_msg}",
        "keywords": ["Timeout", "Error"],
        "steps": [],
        "warning": error_msg,
        "is_error": True,
        "roles": []
    }


# ====== 7. 单个案件处理函数 ======
def process_single_case(split, text_messages, llm_analyze_instance):
    """
    独立处理单个案件的逻辑。
    """
    start_idx = split['start']
    end_idx = split['end']
    case_id = split['case_id']
    case_text = text_messages[start_idx:end_idx + 1]

    # ====== 传统聚类分析 (HDBSCAN) ======
    cluster_context = ""

    if len(case_text) > 2:
        try:
            result = engine.analyze(case_text)
            if "error" in result.get("stats", {}):
                cluster_context = "\n".join(case_text)
            else:
                labels = result['labels']
                unique_clusters = sorted(list(set(labels)))
                for cid in unique_clusters:
                    group_msgs = [case_text[i] for i, label in enumerate(labels) if label == cid]
                    count = len(group_msgs)
                    sample_msgs = "\n      - ".join(group_msgs[:5])
                    cluster_context += f"\n【群组 ID: {cid}】 (共 {count} 条消息)\n典型发言:\n      - {sample_msgs}\n"
                    if count > 5:
                        cluster_context += f"\n      ... (还有 {count - 5} 条)"
        except Exception as e:
            print(f"⚠️ [Case {case_id}] 聚类分析异常：{e}")
            cluster_context = "\n".join(case_text)
    else:
        cluster_context = "\n".join(case_text)

    # 默认失败结果
    ai_report_text = "⚠️ AI 服务暂时不可用"
    structured_data = {
        "risk_level": "Low",
        "scam_type": "未知诈骗类型",
        "evidence": {"keywords": [], "accounts": [], "links": [], "apps": []},
        "timeline": [],
        "roles": []
    }

    if llm_analyze_instance:
        try:
            # 限制 Prompt 长度
            if len(cluster_context) > 4000:
                cluster_context = cluster_context[:4000] + "\n...(内容过长已截断)"

            prompt = SYSTEM_PROMPT_TEMPLATE.format(context_data=cluster_context)
            print(f"🤖 [Case {case_id}] 正在请求 Qwen-Max 分析...")

            # 这里的 invoke 会因为初始化时的 request_timeout 而自动超时抛出异常
            response_text = llm_analyze_instance.invoke(prompt)

            # JSON 提取逻辑
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')

            if json_start != -1 and json_end != -1 and json_start < json_end:
                json_str = response_text[json_start:json_end + 1]
                json_str = re.sub(r'```json|```', '', json_str).strip()

                try:
                    temp_data = json.loads(json_str)
                    if isinstance(temp_data, dict):
                        structured_data = temp_data
                        ai_report_text = response_text[:json_start].strip()
                        if not ai_report_text:
                            ai_report_text = "分析完成 (仅返回 JSON)"
                    else:
                        structured_data["evidence"]["keywords"].append("AI 返回格式错误")
                        ai_report_text = response_text
                except json.JSONDecodeError as je:
                    print(f"❌ [Case {case_id}] JSON 解析失败：{je}")
                    structured_data["evidence"]["keywords"].append("JSON 语法错误")
                    ai_report_text = response_text
            else:
                print(f"⚠️ [Case {case_id}] 未在 AI 响应中找到有效的 JSON 结构")
                structured_data["evidence"]["keywords"].append("未找到 JSON 结构")
                ai_report_text = response_text

        except Exception as ai_err:
            # 这里会捕获到 request_timeout 抛出的异常
            print(f"❌ [Case {case_id}] AI 调用异常：{ai_err}")
            ai_report_text = f"⚠️ AI 生成失败：{str(ai_err)}"
            structured_data["evidence"]["keywords"].append(f"AI Error: {str(ai_err)}")

    # 类型安全检查与结果组装
    if not isinstance(structured_data, dict):
        structured_data = {"risk_level": "Low", "scam_type": "未知", "evidence": {"keywords": []}, "timeline": []}

    raw_risk = str(structured_data.get("risk_level", "Low")).upper()
    if raw_risk not in ["HIGH", "MEDIUM", "LOW"]:
        raw_risk = "LOW"

    return {
        "case_id": case_id,
        "message_count": len(case_text),
        "time_range": f"{start_idx} - {end_idx}",
        "risk_level": raw_risk,
        "risk_label": "高风险" if raw_risk == "HIGH" else "中风险" if raw_risk == "MEDIUM" else "低风险",
        "risk_type": "danger" if raw_risk == "HIGH" else "warning" if raw_risk == "MEDIUM" else "info",
        "risk_score": 90 if raw_risk == "HIGH" else 70 if raw_risk == "MEDIUM" else 30,
        "scam_type": structured_data.get("scam_type", "未知诈骗类型"),
        "ai_report": ai_report_text,
        "keywords": structured_data.get("evidence", {}).get("keywords", []),
        "steps": structured_data.get("timeline", []),
        "roles": structured_data.get("roles", []),
        "warning": "⚠️ 系统自动分案失败，已强制合并为 1 个案件" if split.get('is_failed', False) else None
    }


# ====== 8. 主路由逻辑 (核心优化区) ======
@app.route('/upload', methods=['POST'])
def upload_and_analyze():
    try:
        data = request.json
        raw_messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})

        if not raw_messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400

        print("🧹 正在清洗和标准化数据...")
        cleaned_messages = DataPreprocessor.standardize_message_format(raw_messages)

        platform_clues = DataPreprocessor.extract_key_info_from_platform(platform_data)
        if platform_clues:
            cleaned_messages.append({
                "content": "\n".join(platform_clues),
                "sender": "system",
                "timestamp": None
            })

        text_messages = [msg['content'] for msg in cleaned_messages]

        print("🔪 正在智能分案...")
        splits, is_triage_failed = ai_triage_cases(text_messages)
        if is_triage_failed:
            for s in splits:
                s['is_failed'] = True

        all_results = []
        print(f"🚀 启动并行处理，共 {len(splits)} 个案件 (并发:{MAX_WORKERS}, 超时:{THREAD_WAIT_TIMEOUT}s)...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 分发任务
            future_to_case = {
                executor.submit(process_single_case, split, text_messages, llm_analyze): split
                for split in splits
            }

            # 动态回收结果
            for future in as_completed(future_to_case):
                case_info = future_to_case[future]
                case_id = case_info.get('case_id', 'Unknown')

                try:
                    # 🔥【关键优化】添加 timeout 参数
                    # 如果超过 THREAD_WAIT_TIMEOUT 秒还没结果，直接抛 TimeoutError
                    result = future.result(timeout=THREAD_WAIT_TIMEOUT)
                    all_results.append(result)
                    print(f"✅ [Case {case_id}] 处理完成")

                except TimeoutError:
                    # 🔥【关键优化】捕获超时，生成降级数据
                    print(f"⚠️ [Case {case_id}] 处理超时 (>{THREAD_WAIT_TIMEOUT}s)，已标记为失败")
                    all_results.append(_create_fallback_result(case_info, f"分析超时 (限制{THREAD_WAIT_TIMEOUT}秒)"))

                except Exception as exc:
                    # 🔥【关键优化】捕获其他异常
                    error_msg = str(exc)
                    print(f'❌ [Case {case_id}] 处理发生异常：{error_msg}')
                    traceback.print_exc()
                    all_results.append(_create_fallback_result(case_info, f"处理出错：{error_msg}"))

        # 按 case_id 排序
        all_results.sort(key=lambda x: x.get('case_id', 9999))

        # 检查是否有错误
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


if __name__ == '__main__':
    print(f"🚀 反诈后端服务启动 (Pro Version - Timeout Optimized)...")
    print(f"⚙️  配置：并发={MAX_WORKERS}, LLM 超时={LLM_REQUEST_TIMEOUT}s, 线程等待={THREAD_WAIT_TIMEOUT}s")
    app.run(debug=True, port=5000, host='0.0.0.0')