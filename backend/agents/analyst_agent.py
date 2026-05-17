from .base import BaseAgent, AgentConfig, AgentContext, TimeoutError
import json
import re
from typing import Dict, Any, List
import sys
import os

# 添加backend目录到路径以便导入tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import engine


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
{"risk_level": "High/Medium/Low", "scam_type": "诈骗类型", "victim_name": "受害人", "amount": "金额", "evidence": {"keywords":[]}, "roles":[], "timeline":[]}

# Constraints
- 严禁输出 Markdown 代码块标记
- JSON 必须合法可解析，且必须是响应中的最后一部分
- 用简体中文
- 仅输出 Part A + Part B

# Input Data
{context_data}

# Output
"""


class AnalystAgent(BaseAgent):
    """案件分析智能体"""

    def __init__(self, config: AgentConfig, llm_analyze):
        super().__init__(config)
        self.llm_analyze = llm_analyze

    def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        split = payload.get('split')
        text_messages = payload.get('text_messages', [])
        
        if not split:
            return self._create_fallback_result(split, "缺少案件分割信息")
        
        start_idx = split['start']
        end_idx = split['end']
        case_id = split['case_id']
        case_text = text_messages[start_idx:end_idx + 1]
        
        self._log("INFO", f"开始分析案件 {case_id}", context)

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
                self._log("ERROR", f"聚类分析异常：{e}", context)
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

        if self.llm_analyze:
            try:
                if len(cluster_context) > 4000:
                    cluster_context = cluster_context[:4000] + "\n...(内容过长已截断)"
                prompt = SYSTEM_PROMPT_TEMPLATE.replace('{context_data}', cluster_context)
                self._log("INFO", f"请求LLM深度分析案件 {case_id}", context)
                response_text = self.llm_analyze.invoke(prompt)

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
                        self._log("ERROR", f"JSON 解析失败：{je}", context)
                        structured_data["evidence"]["keywords"].append("JSON 语法错误")
                        ai_report_text = response_text
                else:
                    self._log("WARNING", "未在 AI 响应中找到有效的 JSON 结构", context)
                    structured_data["evidence"]["keywords"].append("未找到 JSON 结构")
                    ai_report_text = response_text

            except Exception as ai_err:
                self._log("ERROR", f"AI 调用异常：{ai_err}", context)
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

        # 提取实体信息
        extracted_entities = self._extract_entities(ai_report_text, cluster_context)
        
        # 查询外部威胁情报（mock实现）
        threat_intel = self._query_threat_intel(extracted_entities)
        
        # 合并威胁情报到实体
        extracted_entities['threat_intel'] = threat_intel

        result = {
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
            "extracted_entities": extracted_entities,
            "warning": "⚠️ 系统自动分案失败，已强制合并为 1 个案件" if split.get('is_failed', False) else None
        }
        
        # 记录实体提取日志
        total_entities = sum(len(v) for k, v in extracted_entities.items() if k != 'threat_intel' and isinstance(v, list))
        self._log("INFO", f"案件 {case_id} 实体提取完成，共提取 {total_entities} 个实体", context)
        self._log("INFO", f"案件 {case_id} 分析完成", context)
        return result

    def _create_fallback_result(self, split, error_msg):
        """创建分析失败时的回退结果"""
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
            "roles": [],
            "extracted_entities": {
                "bank_accounts": [],
                "phone_numbers": [],
                "ip_addresses": [],
                "app_names": [],
                "threat_intel": {}
            }
        }

    def _extract_entities(self, ai_report: str, cluster_context: str) -> Dict[str, Any]:
        """
        从ai_report和cluster_context中提取结构化实体
        """
        combined_text = f"{ai_report}\n{cluster_context}"
        
        # 提取银行卡号（支持脱敏格式）
        bank_pattern = r'\b(\d{4}[*]{0,8}\d{4})\b'
        bank_accounts = list(set(re.findall(bank_pattern, combined_text)))
        
        # 提取手机号（支持脱敏格式）
        phone_pattern = r'\b(1[3-9]\d{0,4}[*]{0,4}\d{0,4})\b'
        phone_numbers = list(set(re.findall(phone_pattern, combined_text)))
        
        # 提取IP地址（支持脱敏格式）
        ip_pattern = r'\b(\d{1,3}(?:\.\*){0,3}\d{0,3})\b'
        ip_addresses = list(set(re.findall(ip_pattern, combined_text)))
        
        # 提取APP名称
        app_pattern = r'(腾讯会议|京东金融|支付宝|微信|QQ|抖音|淘宝|拼多多|美团|小米|华为|钉钉|企业微信|快手|微博|百度|网易|新浪|滴滴|携程|去哪儿|饿了么)'
        app_names = list(set(re.findall(app_pattern, combined_text)))
        
        return {
            "bank_accounts": bank_accounts[:5],  # 最多返回5个
            "phone_numbers": phone_numbers[:5],
            "ip_addresses": ip_addresses[:5],
            "app_names": app_names[:5]
        }

    def _query_threat_intel(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询外部威胁情报（mock实现）
        """
        threat_intel = {
            "bank_account_risk": "unknown",
            "ip_location": "未知",
            "ip_risk": "unknown",
            "app_reputation": "unknown"
        }
        
        # 根据提取的实体生成mock情报
        if entities.get('bank_accounts'):
            threat_intel["bank_account_risk"] = "high" if len(entities['bank_accounts']) > 0 else "unknown"
        
        if entities.get('ip_addresses'):
            threat_intel["ip_location"] = "湖南省长沙市"
            threat_intel["ip_risk"] = "medium"
        
        if entities.get('app_names'):
            threat_intel["app_reputation"] = "suspicious" if len(entities['app_names']) > 1 else "normal"
        
        return threat_intel
