
"""
AI 反诈研判官系统 (Agent 架构)
版本: 2.0
架构: 三层智能体架构
- 交互层: Web前端 (Vue.js)
- 决策与协同层: 反诈研判官Agent (AntiFraudChiefAgent)
- 感知与执行层: 专家工具集 (IntelligentGangDiscoverer, DataPreprocessor, 等)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from tools import engine
import os
import json
import re
import traceback
import time
from langchain_community.llms import Tongyi
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from collections import defaultdict

import numpy as np
from sentence_transformers import SentenceTransformer
import hdbscan


# ====================================================================
# 感知与执行层 (Expert Tools Layer)
# 这一层包含所有具体的功能模块，每个模块都是一个独立的"专家工具"
# Agent 可以像调用工具一样使用这些模块
# ====================================================================

# --------------------------------------------------------------------
# 工具A: 数据清洗引擎 (Data Preprocessor)
# 功能: 标准化输入数据格式，提取平台关键线索
# 开发者: 原有模块，已稳定
# --------------------------------------------------------------------
class DataPreprocessor:
    """工具A: 数据清洗与标准化引擎"""

    @staticmethod
    def clean_text(text):
        """清理文本中的冗余字符和格式"""
        if not isinstance(text, str):
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        return text

    @staticmethod
    def standardize_message_format(raw_messages):
        """标准化消息格式，统一为 {content, sender, timestamp} 结构"""
        standardized = []
        for msg in raw_messages:
            if isinstance(msg, str):
                content = DataPreprocessor.clean_text(msg)
                if content:
                    standardized.append({"content": content, "sender": "unknown", "timestamp": None})
            elif isinstance(msg, dict):
                content = msg.get('content', msg.get('text', ''))
                content = DataPreprocessor.clean_text(content)
                if content:
                    sender = msg.get('sender', msg.get('role', 'unknown'))
                    timestamp = msg.get('time', msg.get('timestamp', None))
                    standardized.append({"content": content, "sender": sender, "timestamp": timestamp})
            elif isinstance(msg, dict) and msg.get('type') == 'image':
                ocr_text = "【图片内容】检测到转账或验证码信息"
                standardized.append({"content": ocr_text, "sender": "unknown", "timestamp": None})
        return standardized

    @staticmethod
    def extract_key_info_from_platform(data):
        """从平台数据中提取关键线索（诈骗电话、APP、网址等）"""
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


# --------------------------------------------------------------------
# 工具B: 智能分案专家 (Case Triage Expert)
# 功能: 判断聊天记录中包含几个独立的诈骗案件
# 开发者: 原有模块，基于 qwen-turbo
# --------------------------------------------------------------------
def ai_triage_cases(text_messages, llm_triage):
    """工具B: 智能案件分割专家 - 识别混杂聊天记录中的独立案件"""
    total_len = len(text_messages)
    if total_len < 5:
        return [{"case_id": 1, "start": 0, "end": total_len - 1}], False

    MAX_CONTEXT = 200
    if total_len > MAX_CONTEXT:
        sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages[:MAX_CONTEXT])])
        is_truncated = True
    else:
        sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages)])
        is_truncated = False

    prompt = f"""
# Role
你是一名拥有 10 年经验的反诈中心情报分析师。任务是对混杂聊天记录进行"案件串并"分析。

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
        print("🤖 [工具B] 正在调用 Qwen-turbo 进行智能分案...")
        response = llm_triage.invoke(prompt)
        raw_text = response.strip()
        clean_text = re.sub(r'```json\s*|```\s*', '', raw_text)
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

        splits = []
        for i, item in enumerate(json_obj):
            start = int(item.get('start', 0))
            end = int(item.get('end', 0))
            if start < 0: start = 0
            if end >= total_len: end = total_len - 1
            if start > end: start, end = end, start
            splits.append({"case_id": i + 1, "start": start, "end": end, "reason": item.get('reason', '自动分案')})

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

        print(f"✅ [工具B] 分案成功：识别出 {len(splits)} 个案件")
        return splits, False

    except Exception as e:
        print(f"⚠️ [工具B] AI 分案失败：{e}")
        return [{"case_id": 1, "start": 0, "end": total_len - 1}], True


# --------------------------------------------------------------------
# 工具C: 案件深度分析专家 (Case Analysis Expert)
# 功能: 对单个案件进行深度分析，提取诈骗类型、风险、证据等
# 开发者: 原有模块，基于 qwen-max
# --------------------------------------------------------------------
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
- **提取受害人姓名和涉案金额**：从对话中推断受害人称呼（如张先生、李女士等），若无则填写"未知"；涉案金额从对话中提取数字和单位（如"5000元"、"2万元"）。

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
  "victim_name": "受害人姓名或称呼",
  "amount": "涉案金额（如：5000元）",
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


def process_single_case(split, text_messages, llm_analyze_instance):
    """工具C: 单个案件深度分析专家 - 对分割出的单个案件进行完整分析"""
    start_idx = split['start']
    end_idx = split['end']
    case_id = split['case_id']
    case_text = text_messages[start_idx:end_idx + 1]

    # 聚类分析
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
            print(f"⚠️ [工具C-案件{case_id}] 聚类分析异常：{e}")
            cluster_context = "\n".join(case_text)
    else:
        cluster_context = "\n".join(case_text)

    # AI 深度分析
    ai_report_text = "⚠️ AI 服务暂时不可用"
    structured_data = {
        "risk_level": "Low",
        "scam_type": "未知诈骗类型",
        "victim_name": "未知",
        "amount": "未知金额",
        "evidence": {"keywords": [], "accounts": [], "links": [], "apps": []},
        "timeline": [],
        "roles": []
    }

    if llm_analyze_instance:
        try:
            if len(cluster_context) > 4000:
                cluster_context = cluster_context[:4000] + "\n...(内容过长已截断)"
            prompt = SYSTEM_PROMPT_TEMPLATE.format(context_data=cluster_context)
            print(f"🤖 [工具C-案件{case_id}] 正在请求 Qwen-Max 深度分析...")
            response_text = llm_analyze_instance.invoke(prompt)

            # 解析响应
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
                    print(f"❌ [工具C-案件{case_id}] JSON 解析失败：{je}")
                    structured_data["evidence"]["keywords"].append("JSON 语法错误")
                    ai_report_text = response_text
            else:
                print(f"⚠️ [工具C-案件{case_id}] 未在 AI 响应中找到有效的 JSON 结构")
                structured_data["evidence"]["keywords"].append("未找到 JSON 结构")
                ai_report_text = response_text

        except Exception as ai_err:
            print(f"❌ [工具C-案件{case_id}] AI 调用异常：{ai_err}")
            ai_report_text = f"⚠️ AI 生成失败：{str(ai_err)}"
            structured_data["evidence"]["keywords"].append(f"AI Error: {str(ai_err)}")

    if not isinstance(structured_data, dict):
        structured_data = {"risk_level": "Low", "scam_type": "未知", "victim_name": "未知", "amount": "未知金额",
                           "evidence": {"keywords": []}, "timeline": []}

    # 标准化输出
    raw_risk = str(structured_data.get("risk_level", "Low")).upper()
    if raw_risk not in ["HIGH", "MEDIUM", "LOW"]:
        raw_risk = "LOW"

    victim_name = structured_data.get("victim_name", "未知")
    amount = structured_data.get("amount", "未知金额")
    scam_type = structured_data.get("scam_type", "未知诈骗类型")

    return {
        "case_id": case_id,
        "message_count": len(case_text),
        "time_range": f"{start_idx} - {end_idx}",
        "risk_level": raw_risk,
        "risk_label": "高风险" if raw_risk == "HIGH" else "中风险" if raw_risk == "MEDIUM" else "低风险",
        "risk_type": "danger" if raw_risk == "HIGH" else "warning" if raw_risk == "MEDIUM" else "info",
        "risk_score": 90 if raw_risk == "HIGH" else 70 if raw_risk == "MEDIUM" else 30,
        "scam_type": scam_type,
        "victim": victim_name,
        "amount": amount,
        "ai_report": ai_report_text,
        "keywords": structured_data.get("evidence", {}).get("keywords", []),
        "steps": structured_data.get("timeline", []),
        "roles": structured_data.get("roles", []),
        "warning": "⚠️ 系统自动分案失败，已强制合并为 1 个案件" if split.get('is_failed', False) else None
    }


def _create_fallback_result(split, error_msg):
    """工具C-辅助: 创建分析失败时的回退结果"""
    start_idx = split.get('start', 0)
    end_idx = split.get('end', 0)
    return {
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
        "ai_report": f"⚠️ {error_msg}",
        "keywords": ["Timeout", "Error"],
        "steps": [],
        "warning": error_msg,
        "is_error": True,
        "roles": []
    }


# --------------------------------------------------------------------
# 工具D: 智能团伙发现专家 (Intelligent Gang Discoverer)
# 功能: 实现申报书中的 "BGE语义向量化 + HDBSCAN无监督聚类"
# 开发者: 新增模块，核心创新点
# --------------------------------------------------------------------
class IntelligentGangDiscoverer:
    """
    工具D: 智能团伙发现专家
    功能: 基于申报书描述的"电诈话术语义指纹"与"HDBSCAN无监督聚类"技术，
          从离散案件中智能发现犯罪团伙，并生成深度画像。
    技术栈: Sentence-BERT (BGE) + HDBSCAN + LLM
    """

    def __init__(self, embedding_model_name=None, llm_analyze=None):
        """
        简化的初始化方法
        """
        import os

        # 如果未指定模型路径，使用默认
        if embedding_model_name is None:
            embedding_model_name = r"C:\Users\hd\Desktop\FraudLens\backend\bge-large-zh-v1.5"

        print(f"[工具D] 正在加载语义编码模型: {embedding_model_name}...")

        try:
            # 方法1：直接通过 Transformers 加载（已经成功的方法）
            from sentence_transformers import models
            from transformers import AutoTokenizer, AutoModel

            # 加载 tokenizer 和模型
            tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
            transformer_model = AutoModel.from_pretrained(embedding_model_name)

            # 创建 SentenceTransformer
            word_embedding_model = models.Transformer(embedding_model_name)
            pooling_model = models.Pooling(
                word_embedding_model.get_word_embedding_dimension(),
                pooling_mode_mean_tokens=True
            )

            self.embedder = SentenceTransformer(
                modules=[word_embedding_model, pooling_model]
            )
            print("✅ 通过 Transformers 加载成功")

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

        # 验证模型
        try:
            test_embedding = self.embedder.encode(["测试"], normalize_embeddings=True)
            print(f"✅ 模型验证成功，维度: {test_embedding.shape}")
        except Exception as e:
            print(f"⚠️ 模型验证警告: {e}")

        # HDBSCAN配置
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=2,
            min_samples=1,
            cluster_selection_epsilon=0.5,
            metric='euclidean',
            prediction_data=True
        )

        self.llm_analyze = llm_analyze
        print("[工具D] 模型加载完毕。")
    def extract_semantic_fingerprint(self, cases):
        """
        步骤1: 提取"电诈话术语义指纹"
        融合案件的多维信息，生成用于向量化的文本表征
        """
        fingerprints = []
        for case in cases:
            # 提取关键文本信息
            scam_type = case.get('scam_type', '未知类型')
            keywords = ' '.join(case.get('keywords', []))[:100]
            steps = ' '.join(case.get('steps', []))[:150]
            ai_report = case.get('ai_report', '')[:200]

            # 构建语义指纹文本（聚类质量的关键）
            fingerprint_text = (
                f"诈骗类型：{scam_type}。"
                f"关键词：{keywords}。"
                f"作案步骤：{steps}。"
                f"案情摘要：{ai_report}"
            )
            fingerprints.append(fingerprint_text)
        return fingerprints

    def discover(self, cases):
        """
        主函数: 智能团伙发现
        输入: 案件分析结果列表
        输出: 智能发现的团伙列表（与前端兼容的格式）
        """
        if len(cases) < 2:
            print("[工具D] 案件数量不足2，无法进行有效聚类。")
            return self._create_single_case_gangs(cases)

        print(f"[工具D] 开始对 {len(cases)} 个案件进行智能团伙聚类...")

        # 1. 提取语义指纹
        fingerprint_texts = self.extract_semantic_fingerprint(cases)
        print(f"  [工具D] 已生成 {len(fingerprint_texts)} 个语义指纹。")

        # 2. 转换为高维语义向量
        print("  [工具D] 正在进行语义向量编码...")
        try:
            embeddings = self.embedder.encode(
                fingerprint_texts,
                normalize_embeddings=True,  # 归一化，便于计算余弦相似度
                show_progress_bar=False
            )
            print(f"  [工具D] 向量编码完成，维度: {embeddings.shape}")
        except Exception as e:
            print(f"  ❌ [工具D] 语义向量编码失败: {e}，回退到规则聚类。")
            return self._fallback_to_rule_based_clustering(cases)

        # 3. HDBSCAN无监督聚类
        print("  [工具D] 正在执行HDBSCAN无监督聚类...")
        cluster_labels = self.clusterer.fit_predict(embeddings)
        # cluster_labels: -1 表示噪声点（独立案件），>=0 表示团伙ID
        unique_labels = set(cluster_labels)
        noise_count = list(cluster_labels).count(-1)
        print(
            f"  [工具D] 聚类完成。发现 {len(unique_labels) - (1 if -1 in unique_labels else 0)} 个潜在团伙，{noise_count} 个独立案件。")

        # 4. 组织案件到团伙
        gangs_map = {}
        for idx, label in enumerate(cluster_labels):
            if label not in gangs_map:
                gangs_map[label] = []
            gangs_map[label].append(cases[idx])

        # 5. 为每个团伙生成智能画像
        print("  [工具D] 正在为各团伙生成智能画像...")
        final_gangs = []
        for label, case_list in gangs_map.items():
            if label == -1:
                # 噪声点（独立案件），每个单独作为一个"团伙"处理
                for case in case_list:
                    solo_gang = self._create_solo_case_gang(case)
                    final_gangs.append(solo_gang)
            else:
                # 真正的团伙簇
                gang_profile = self._generate_gang_profile_via_llm(label, case_list)
                final_gangs.append(gang_profile)

        print(f"[工具D] 聚类完成，共生成 {len(final_gangs)} 个团伙/独立案件单元。")
        return final_gangs

    def _generate_gang_profile_via_llm(self, gang_label, case_list):
        """
        调用大语言模型，分析团伙内案件的共性，生成智能画像
        包括：团伙代号、核心特征、风险等级等
        """
        if not self.llm_analyze:
            print("  ⚠️ [工具D] LLM 不可用，使用规则生成团伙画像")
            return self._create_fallback_gang_profile(gang_label, case_list)

        # 准备给LLM的上下文
        case_summaries = []
        for case in case_list:
            summary = (f"案件ID: {case.get('case_id', 'N/A')}, "
                       f"类型: {case.get('scam_type', '未知')}, "
                       f"风险: {case.get('risk_level', 'LOW')}, "
                       f"金额: {case.get('amount', '未知')}, "
                       f"关键词: {', '.join(case.get('keywords', ['无']))[:50]}")
            case_summaries.append(summary)

        cases_context = "\n".join(case_summaries)

        # 构建给LLM的提示词
        prompt = f"""你是一个资深反诈串并案专家。请分析以下 {len(case_list)} 个高度关联的诈骗案件，它们已被算法初步判定为同一团伙所为。

【案件列表】
{cases_context}

【任务】
请基于上述案件信息，为该犯罪团伙生成一份精准的"数字画像"：

1. **团伙代号**：起一个贴切、专业、易记的代号（例如"夜枭"、"幻影客服团"、"多卡宝洗钱组"）。请避免使用"团伙A"、"组1"这类无意义名称。
2. **核心特征**：提炼该团伙2-4个最显著的行为、技术或话术特征（例如："擅长利用屏幕共享软件远程操控"、"话术迭代快，每周更新剧本"、"使用虚拟货币结算，资金追踪难"）。
3. **主要诈骗类型**：总结其主要作案手法（例如："冒充金融平台客服注销贷款类"、"兼职刷单返利类"）。
4. **团伙整体风险等级**：综合所有案件的风险，给出整体评级（HIGH, MEDIUM, LOW）。
5. **简要描述**：用一两句话概括该团伙的作案模式。

请以严格的JSON格式输出，键名如下：gang_name, characteristics, primary_scam_type, risk_level, description。
不要输出任何其他解释性文字。
"""

        try:
            print(f"  [工具D-团伙{gang_label}] 正在调用LLM生成智能画像...")
            response = self.llm_analyze.invoke(prompt)

            # 解析LLM返回的JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                llm_result = json.loads(json_match.group())
            else:
                # 如果LLM没返回纯JSON，尝试直接解析整个响应
                llm_result = json.loads(response)

            # 计算团伙的统计信息
            total_amount_yuan = 0
            highest_risk = 'LOW'
            for case in case_list:
                # 金额解析
                amount_str = case.get('amount', '0元')
                match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
                if match:
                    num = float(match.group(1))
                    if '万' in amount_str:
                        num *= 10000
                    total_amount_yuan += num
                # 风险等级
                case_risk = case.get('risk_level', 'LOW')
                if case_risk == 'HIGH':
                    highest_risk = 'HIGH'
                elif case_risk == 'MEDIUM' and highest_risk != 'HIGH':
                    highest_risk = 'MEDIUM'

            total_amount_wan = f'{total_amount_yuan / 10000:.1f}万元' if total_amount_yuan > 0 else '未知'
            risk_label = '高风险' if highest_risk == 'HIGH' else ('中风险' if highest_risk == 'MEDIUM' else '低风险')
            risk_type = 'danger' if highest_risk == 'HIGH' else ('warning' if highest_risk == 'MEDIUM' else 'info')

            # 成员规模估算
            member_estimate = '5-8 人'
            if total_amount_yuan > 200000:
                member_estimate = '15-20 人'
            elif total_amount_yuan > 50000:
                member_estimate = '10-15 人'
            if len(case_list) > 10:
                member_estimate = f'{member_estimate.split("-")[0]}+ 人'

            # 构建与前端兼容的gang对象
            gang_obj = {
                'gang_id': f'GANG_AI_{gang_label:03d}',
                'gang_name': llm_result.get('gang_name', f'智能识别团伙{gang_label}'),
                'risk_level': llm_result.get('risk_level', highest_risk),
                'risk_type': risk_type,
                'risk_label': risk_label,
                'confidence': min(95, 70 + len(case_list) * 3),
                'member_count_estimate': member_estimate,
                'active_time': '需进一步分析',
                'tech_level': '中',
                'script_type': llm_result.get('primary_scam_type', '混合型诈骗'),
                'total_cases': len(case_list),
                'total_amount_involved': total_amount_wan,
                'related_cases': [{
                    'case_id': c.get('case_id', f'CASE_{idx}'),
                    'victim': c.get('victim', '未知'),
                    'amount': c.get('amount', '未知金额'),
                    'snippet': (c.get('ai_report', '')[:60] + '...') if c.get('ai_report') else '无详细片段',
                    'risk_level': c.get('risk_level', 'LOW')
                } for idx, c in enumerate(case_list, 1)],
                'fingerprint': llm_result.get('characteristics', ['特征分析中']),
                'steps': case_list[0].get('steps', []) if case_list else [],
                'description': llm_result.get('description', ''),
                'network_nodes': self._generate_gang_network_nodes(gang_label, case_list, total_amount_yuan)
            }

            return gang_obj

        except Exception as e:
            print(f"  ⚠️ [工具D-团伙{gang_label}] LLM生成团伙画像时出错: {e}，使用备用方案。")
            return self._create_fallback_gang_profile(gang_label, case_list)

    def _generate_gang_network_nodes(self, gang_label, case_list, total_amount):
        """为团伙生成网络节点数据"""
        network_nodes = []
        # 添加团伙中心节点
        network_nodes.append({
            'id': f'GANG_AI_{gang_label:03d}',
            'name': f'团伙{gang_label}',
            'type': 'gang',
            'value': total_amount,
            'risk_level': 'HIGH' if total_amount > 100000 else ('MEDIUM' if total_amount > 30000 else 'LOW')
        })
        # 添加关联的案件节点
        for case in case_list:
            amount_str = case.get('amount', '0元')
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            case_value = 0
            if match:
                case_value = float(match.group(1))
                if '万' in amount_str:
                    case_value *= 10000

            network_nodes.append({
                'id': case.get('case_id', f'UNKNOWN_{gang_label}'),
                'name': f"{case.get('case_id', '案件')}\n{case.get('victim', '未知')}",
                'type': 'case',
                'value': case_value,
                'gang_id': f'GANG_AI_{gang_label:03d}',
                'risk_level': case.get('risk_level', 'LOW')
            })

        return network_nodes

    def _create_solo_case_gang(self, case):
        """为独立案件（噪声点）创建一个虚拟的'团伙'，以便前端统一展示"""
        return {
            'gang_id': f'SOLO_{case.get("case_id", "UNKNOWN")}',
            'gang_name': f'独立案件 - {case.get("scam_type", "未知类型")}',
            'risk_level': case.get('risk_level', 'LOW'),
            'risk_type': 'danger' if case.get('risk_level') == 'HIGH' else (
                'warning' if case.get('risk_level') == 'MEDIUM' else 'info'),
            'risk_label': '高风险' if case.get('risk_level') == 'HIGH' else (
                '中风险' if case.get('risk_level') == 'MEDIUM' else '低风险'),
            'confidence': 60,
            'member_count_estimate': '1 人',
            'active_time': '未知',
            'tech_level': '未知',
            'script_type': case.get('scam_type', '未知'),
            'total_cases': 1,
            'total_amount_involved': case.get('amount', '未知金额'),
            'related_cases': [{
                'case_id': case.get('case_id', 'UNKNOWN'),
                'victim': case.get('victim', '未知'),
                'amount': case.get('amount', '未知金额'),
                'snippet': (case.get('ai_report', '')[:60] + '...') if case.get('ai_report') else '无详细片段',
                'risk_level': case.get('risk_level', 'LOW')
            }],
            'fingerprint': case.get('keywords', []),
            'steps': case.get('steps', []),
            'description': '此案件为独立个案，未与其他案件形成明显团伙模式。',
            'network_nodes': self._generate_solo_network_nodes(case)
        }

    def _generate_solo_network_nodes(self, case):
        """为独立案件生成网络节点数据"""
        amount_str = case.get('amount', '0元')
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        case_value = 0
        if match:
            case_value = float(match.group(1))
            if '万' in amount_str:
                case_value *= 10000

        return [{
            'id': case.get('case_id', 'UNKNOWN'),
            'name': f"独立案件\n{case.get('victim', '未知')}",
            'type': 'case',
            'value': case_value,
            'gang_id': f'SOLO_{case.get("case_id", "UNKNOWN")}',
            'risk_level': case.get('risk_level', 'LOW')
        }]

    def _create_fallback_gang_profile(self, gang_label, case_list):
        """LLM调用失败时，使用规则生成团伙画像的备用方案"""
        scam_types = [c.get('scam_type', '未知').split(' - ')[0] for c in case_list]
        primary_type = max(set(scam_types), key=scam_types.count) if scam_types else '未知类型'

        # 简单的命名规则
        gang_name_map = {
            '冒充电商': '幻影客服团',
            '刷单': '夜枭刷单组',
            '冒充公检法': '黑面判官团',
            '网络贷款': '伪金流水军',
            '投资理财': '杀猪盘狩猎者'
        }
        gang_name = gang_name_map.get(primary_type, f'{primary_type}犯罪团伙')

        # 计算统计信息
        total_amount_yuan = 0
        highest_risk = 'LOW'
        for case in case_list:
            amount_str = case.get('amount', '0元')
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            if match:
                num = float(match.group(1))
                if '万' in amount_str:
                    num *= 10000
                total_amount_yuan += num

            case_risk = case.get('risk_level', 'LOW')
            if case_risk == 'HIGH':
                highest_risk = 'HIGH'
            elif case_risk == 'MEDIUM' and highest_risk != 'HIGH':
                highest_risk = 'MEDIUM'

        total_amount_wan = f'{total_amount_yuan / 10000:.1f}万元' if total_amount_yuan > 0 else '未知'
        risk_label = '高风险' if highest_risk == 'HIGH' else ('中风险' if highest_risk == 'MEDIUM' else '低风险')
        risk_type = 'danger' if highest_risk == 'HIGH' else ('warning' if highest_risk == 'MEDIUM' else 'info')

        # 构建团伙对象
        return {
            'gang_id': f'GANG_FB_{gang_label:03d}',
            'gang_name': gang_name,
            'risk_level': highest_risk,
            'risk_type': risk_type,
            'risk_label': risk_label,
            'confidence': 75,
            'member_count_estimate': '5-8 人',
            'active_time': '需进一步分析',
            'tech_level': '中',
            'script_type': primary_type,
            'total_cases': len(case_list),
            'total_amount_involved': total_amount_wan,
            'related_cases': [{
                'case_id': c.get('case_id', f'CASE_{idx}'),
                'victim': c.get('victim', '未知'),
                'amount': c.get('amount', '未知金额'),
                'snippet': (c.get('ai_report', '')[:60] + '...') if c.get('ai_report') else '无详细片段',
                'risk_level': c.get('risk_level', 'LOW')
            } for idx, c in enumerate(case_list, 1)],
            'fingerprint': [f'擅长{primary_type}诈骗', '话术标准化'],
            'steps': case_list[0].get('steps', []) if case_list else [],
            'description': f'基于{primary_type}诈骗手法识别的犯罪团伙',
            'network_nodes': self._generate_gang_network_nodes(gang_label, case_list, total_amount_yuan)
        }

    def _fallback_to_rule_based_clustering(self, cases):
        """当智能聚类失败时，回退到基于规则（诈骗主类型）的聚类方法"""
        print("  [工具D] 回退至基于规则的聚类...")
        groups = defaultdict(list)
        for case in cases:
            main_type = case.get('scam_type', '未知类型').split(' - ')[0]
            groups[main_type].append(case)

        final_gangs = []
        for idx, (scam_type, case_list) in enumerate(groups.items()):
            final_gangs.append(self._create_fallback_gang_profile(idx, case_list))
        return final_gangs

    def _create_single_case_gangs(self, cases):
        """处理只有单个案件的情况"""
        if not cases:
            return []
        elif len(cases) == 1:
            return [self._create_solo_case_gang(cases[0])]
        else:
            # 理论上不会走到这里
            return []


# --------------------------------------------------------------------
# 工具E: 网络数据生成器 (Network Data Generator)
# 功能: 为前端网络图生成节点和边的数据
# 开发者: 新增模块，支持可视化
# --------------------------------------------------------------------
def generate_network_data(gangs):
    """
    工具E: 网络数据生成器
    功能: 基于团伙数据生成ECharts网络图所需的节点和边数据
    """
    nodes = []
    links = []

    for gang in gangs:
        # 添加团伙节点
        gang_node = {
            'id': gang['gang_id'],
            'name': gang['gang_name'],
            'type': 'gang',
            'value': parse_amount_to_number(gang['total_amount_involved']),
            'risk_level': gang['risk_level'],
            'symbolSize': 50 + min(30, len(gang['related_cases']) * 5)
        }
        nodes.append(gang_node)

        # 添加案件节点和边
        for case in gang['related_cases']:
            case_id = case['case_id']
            case_node = {
                'id': case_id,
                'name': f"{case_id}\n{case['victim']}",
                'type': 'case',
                'value': parse_amount_to_number(case['amount']),
                'risk_level': case['risk_level'],
                'symbolSize': 30
            }
            nodes.append(case_node)

            # 添加边
            link = {
                'source': gang['gang_id'],
                'target': case_id,
                'value': parse_amount_to_number(case['amount'])
            }
            links.append(link)

    return {'nodes': nodes, 'links': links}


def parse_amount_to_number(amount_str):
    """辅助函数: 将金额字符串解析为数值"""
    if not amount_str or amount_str == '未知金额':
        return 0
    match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
    if match:
        num = float(match.group(1))
        if '万' in amount_str:
            num *= 10000
        return num
    return 0


# ====================================================================
# 决策与协同层 (Decision & Coordination Layer)
# 这一层是系统的"大脑" - 反诈研判官Agent
# 负责协调所有工具，制定研判策略，处理异常
# ====================================================================

class AntiFraudChiefAgent:
    """
    决策与协同层: 反诈研判官Agent
    角色: 反诈中心首席研判官
    职责: 协调所有专家工具，制定研判策略，确保研判流程的智能化和可靠性
    """

    def __init__(self, llm_analyze, llm_triage):
        """
        初始化Agent
        Args:
            llm_analyze: 案件深度分析LLM (qwen-max)
            llm_triage: 案件分案LLM (qwen-turbo)
        """
        self.llm_analyze = llm_analyze
        self.llm_triage = llm_triage

        # 初始化所有工具
        self.tools = {
            'preprocess': DataPreprocessor,  # 工具A
            'triage': ai_triage_cases,  # 工具B
            'analyze_case': process_single_case,  # 工具C
            'discover_gangs': None,  # 工具D (稍后初始化)
            'generate_network': generate_network_data  # 工具E
        }

        # 初始化智能团伙发现引擎
        self.tools['discover_gangs'] = IntelligentGangDiscoverer(llm_analyze=llm_analyze)

        # 任务上下文
        self.context = {
            'raw_data': None,
            'cleaned_data': None,
            'case_splits': None,
            'analyzed_cases': None,
            'gangs': None,
            'network_data': None,
            'errors': [],
            'warnings': [],
            'processing_start_time': None,
            'current_stage': None
        }

        print("[Agent] 反诈研判官Agent初始化完成")

    def run(self, raw_messages, platform_data):
        """
        执行完整的智能研判流程
        遵循: 数据准备 -> 智能分案 -> 并行分析 -> 团伙发现 -> 结果生成的流程
        """
        self.context['processing_start_time'] = time.time()

        try:
            # ========== 阶段1: 数据准备 ==========
            self._log("阶段1: 数据清洗与标准化")
            self.context['current_stage'] = 'data_preparation'

            cleaned_messages = self.tools['preprocess'].standardize_message_format(raw_messages)
            platform_clues = self.tools['preprocess'].extract_key_info_from_platform(platform_data)

            if platform_clues:
                cleaned_messages.append({
                    "content": "\n".join(platform_clues),
                    "sender": "system",
                    "timestamp": None
                })

            self.context['cleaned_data'] = cleaned_messages
            self.context['raw_data'] = raw_messages

            if not cleaned_messages:
                raise ValueError("数据清洗后无有效内容")

            # ========== 阶段2: 智能分案 ==========
            self._log("阶段2: 案件智能分割")
            self.context['current_stage'] = 'case_triage'

            text_messages = [msg['content'] for msg in cleaned_messages]
            splits, is_triage_failed = self.tools['triage'](text_messages, self.llm_triage)

            if is_triage_failed:
                self.context['warnings'].append("案件智能分割置信度较低，可能影响后续分析")
                for s in splits:
                    s['is_failed'] = True

            self.context['case_splits'] = splits

            if not splits:
                raise ValueError("案件分割失败，未识别出任何案件")

            # ========== 阶段3: 并行案件深度分析 ==========
            self._log(f"阶段3: 并行深度分析 ({len(splits)}个案件)")
            self.context['current_stage'] = 'case_analysis'

            all_results = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_case = {
                    executor.submit(
                        self.tools['analyze_case'],
                        split,
                        text_messages,
                        self.llm_analyze
                    ): split for split in splits
                }

                for future in as_completed(future_to_case):
                    case_info = future_to_case[future]
                    case_id = case_info.get('case_id', 'Unknown')
                    try:
                        result = future.result(timeout=THREAD_WAIT_TIMEOUT)
                        all_results.append(result)
                        self._log(f"✅ 案件{case_id} 分析完成", level="SUCCESS")
                    except TimeoutError:
                        error_msg = f"案件{case_id} 分析超时 (>{THREAD_WAIT_TIMEOUT}s)"
                        self.context['errors'].append(error_msg)
                        all_results.append(_create_fallback_result(case_info, error_msg))
                        self._log(f"⚠️ {error_msg}", level="WARNING")
                    except Exception as exc:
                        error_msg = f"案件{case_id} 分析异常: {str(exc)}"
                        self.context['errors'].append(error_msg)
                        all_results.append(_create_fallback_result(case_info, error_msg))
                        self._log(f"❌ {error_msg}", level="ERROR")

            all_results.sort(key=lambda x: x.get('case_id', 9999))
            self.context['analyzed_cases'] = all_results

            if not all_results:
                raise ValueError("所有案件分析均失败")

            # ========== 阶段4: 智能团伙发现 ==========
            self._log("阶段4: 智能团伙聚类与画像")
            self.context['current_stage'] = 'gang_discovery'

            if len(all_results) >= 2:
                try:
                    gangs = self.tools['discover_gangs'].discover(all_results)
                    self.context['gangs'] = gangs
                    self._log(f"✅ 发现 {len(gangs)} 个犯罪团伙/独立案件", level="SUCCESS")
                except Exception as e:
                    error_msg = f"智能团伙发现失败: {str(e)}"
                    self.context['errors'].append(error_msg)
                    self._log(f"❌ {error_msg}", level="ERROR")
                    # 回退到简单聚类
                    gangs = self._simple_fallback_clustering(all_results)
                    self.context['gangs'] = gangs
            else:
                # 案件太少，直接作为独立案件处理
                gangs = [self.tools['discover_gangs']._create_solo_case_gang(case) for case in all_results]
                self.context['gangs'] = gangs
                self._log(f"✅ 处理 {len(gangs)} 个独立案件", level="SUCCESS")

            # ========== 阶段5: 生成网络数据 ==========
            self._log("阶段5: 生成关联网络数据")
            self.context['current_stage'] = 'network_generation'

            network_data = self.tools['generate_network'](gangs)
            self.context['network_data'] = network_data

            # ========== 阶段6: 汇总结果 ==========
            processing_time_ms = int((time.time() - self.context['processing_start_time']) * 1000)

            processing_info = {
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "processing_time_ms": processing_time_ms,
                "data_version": "2.0",
                "agent_version": "AntiFraudChiefAgent-v1.0",
                "total_stages": 5,
                "current_stage": self.context['current_stage'],
                "warnings": self.context['warnings'],
                "errors": self.context['errors']
            }


            for gang in gangs:
                # 确保有 gang_name 字段
                if 'gang_name' not in gang:
                    gang['gang_name'] = gang.get('script_type', '未知团伙')

                # 确保有 fingerprint 字段
                if 'fingerprint' not in gang or not gang['fingerprint']:
                    gang['fingerprint'] = ['特征分析中']

                # 确保有 related_cases 字段
                if 'related_cases' not in gang:
                    gang['related_cases'] = []

                # 确保有 risk_label 字段
                if 'risk_label' not in gang:
                    risk_level = gang.get('risk_level', 'LOW')
                    gang['risk_label'] = '高风险' if risk_level == 'HIGH' else (
                        '中风险' if risk_level == 'MEDIUM' else '低风险')

                # 确保有 risk_type 字段
                if 'risk_type' not in gang:
                    risk_level = gang.get('risk_level', 'LOW')
                    gang['risk_type'] = 'danger' if risk_level == 'HIGH' else (
                        'warning' if risk_level == 'MEDIUM' else 'info')

            return {
                "success": True,
                "total_cases": len(all_results),
                "triage_status": "failed" if is_triage_failed else "success",
                "raw_cases": all_results,
                "gangs": gangs,
                "network_data": network_data,  # 网络数据单独返回
                "processing_info": processing_info,
                "message": "智能研判完成"
            }

        except Exception as e:
            self._log(f"❌ 研判流程发生致命错误: {e}", level="ERROR")
            import traceback
            traceback.print_exc()

            processing_time_ms = int((time.time() - self.context.get('processing_start_time', time.time())) * 1000)

            return {
                "success": False,
                "error": str(e),
                "processing_info": {
                    "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    "processing_time_ms": processing_time_ms,
                    "current_stage": self.context.get('current_stage', 'unknown'),
                    "errors": self.context['errors'] + [str(e)]
                },
                "message": "研判流程执行失败"
            }

    def _simple_fallback_clustering(self, cases):
        """简单的回退聚类方案"""
        groups = defaultdict(list)
        for case in cases:
            main_type = case.get('scam_type', '未知').split(' - ')[0]
            groups[main_type].append(case)

        gangs = []
        for idx, (scam_type, case_list) in enumerate(groups.items()):
            gang = {
                'gang_id': f'GANG_FB_{idx:03d}',
                'gang_name': f'{scam_type}团伙',
                'risk_level': 'LOW',
                'risk_type': 'info',
                'risk_label': '低风险',
                'confidence': 60,
                'member_count_estimate': '未知',
                'active_time': '未知',
                'tech_level': '未知',
                'script_type': scam_type,
                'total_cases': len(case_list),
                'total_amount_involved': '未知',
                'related_cases': [{
                    'case_id': c.get('case_id', f'CASE_{i}'),
                    'victim': c.get('victim', '未知'),
                    'amount': c.get('amount', '未知'),
                    'snippet': c.get('ai_report', '')[:60] + '...' if c.get('ai_report') else '无',
                    'risk_level': c.get('risk_level', 'LOW')
                } for i, c in enumerate(case_list, 1)],
                'fingerprint': ['回退聚类'],
                'steps': [],
                'description': '回退聚类结果',
                'network_nodes': []
            }
            gangs.append(gang)

        return gangs

    def _log(self, message, level="INFO"):
        """Agent日志记录"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[Agent {level} {timestamp}] {message}")


# ====================================================================
# 交互层 (Interaction Layer) - Flask Web 服务器
# 这一层提供Web API接口，连接前端与Agent
# ====================================================================

# 初始化Flask应用
app = Flask(__name__)
load_dotenv()
CORS(app)

# 配置参数
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 错误：未找到 DASHSCOPE_API_KEY 环境变量！")
    exit(1)
else:
    print("✅ API Key 加载成功")

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
    print(f"❌ 模型初始化失败：{e}")
    exit(1)

# 初始化Agent
chief_agent = None
try:
    chief_agent = AntiFraudChiefAgent(llm_analyze, llm_triage)
    print("🚀 反诈研判官Agent启动成功！")
except Exception as e:
    print(f"❌ Agent初始化失败：{e}")
    exit(1)


@app.route('/upload', methods=['POST'])
def upload_and_analyze():
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
        cleaned_messages = DataPreprocessor.standardize_message_format(raw_messages)
        platform_clues = DataPreprocessor.extract_key_info_from_platform(platform_data)
        if platform_clues:
            cleaned_messages.append({"content": "\n".join(platform_clues), "sender": "system", "timestamp": None})

        text_messages = [msg['content'] for msg in cleaned_messages]

        print("🔪 正在智能分案...")
        splits, is_triage_failed = ai_triage_cases(text_messages, llm_triage)
        if is_triage_failed:
            for s in splits:
                s['is_failed'] = True

        all_results = []
        print(f"🚀 启动并行处理，共 {len(splits)} 个案件 (并发:{MAX_WORKERS}, 超时:{THREAD_WAIT_TIMEOUT}s)...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_case = {executor.submit(process_single_case, split, text_messages, llm_analyze): split for split
                              in splits}
            for future in as_completed(future_to_case):
                case_info = future_to_case[future]
                case_id = case_info.get('case_id', 'Unknown')
                try:
                    result = future.result(timeout=THREAD_WAIT_TIMEOUT)
                    all_results.append(result)
                    print(f"✅ [Case {case_id}] 处理完成")
                except TimeoutError:
                    print(f"⚠️ [Case {case_id}] 处理超时 (>{THREAD_WAIT_TIMEOUT}s)，已标记为失败")
                    all_results.append(_create_fallback_result(case_info, f"分析超时 (限制{THREAD_WAIT_TIMEOUT}秒)"))
                except Exception as exc:
                    error_msg = str(exc)
                    print(f'❌ [Case {case_id}] 处理发生异常：{error_msg}')
                    traceback.print_exc()
                    all_results.append(_create_fallback_result(case_info, f"处理出错：{error_msg}"))

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
def agent_analyze():
    """
    Agent智能研判接口 (推荐使用)
    使用完整的Agent架构进行智能研判
    """
    try:
        data = request.json
        raw_messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})

        if not raw_messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400

        print("=" * 60)
        print("🚀 反诈研判官Agent启动智能研判流程...")
        print("=" * 60)

        # 调用Agent进行智能研判
        result = chief_agent.run(raw_messages, platform_data)

        print("=" * 60)
        print(f"✅ 智能研判完成！状态: {'成功' if result.get('success') else '失败'}")
        if result.get('success'):
            print(f"   发现案件: {result.get('total_cases', 0)} 个")
            print(f"   识别团伙: {len(result.get('gangs', []))} 个")
            print(f"   处理耗时: {result.get('processing_info', {}).get('processing_time_ms', 0)}ms")
        print("=" * 60)

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
        "agent_status": "active" if chief_agent else "inactive",
        "models": {
            "qwen_max": "active" if llm_analyze else "inactive",
            "qwen_turbo": "active" if llm_triage else "inactive"
        }
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
    print("=" * 60)
    print("🌐 可用接口:")
    print("   - POST /upload        (传统分析，向后兼容)")
    print("   - POST /agent-analyze (智能分析，推荐使用)")
    print("   - GET  /health        (健康检查)")
    print("   - GET  /api/network-data (网络数据)")
    print("=" * 60)

    app.run(debug=True, port=5000, host='0.0.0.0')