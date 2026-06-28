"""
案件分析 Agent - 基于 ReAct 循环的智能分析
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.agent_runtime import AgentRuntime
from core.state import AgentState
from core.tool_sandbox import ToolSandbox
from tools.base import ToolRegistry
from tools.database_tools import SearchSimilarCasesTool, GetCaseDetailTool
from tools.evidence_tools import ExtractEvidenceTool
from tools.risk_tools import AssessRiskTool


class AnalystAgent:
    """
    案件分析智能体
    
    使用 ReAct 循环进行案件分析:
    1. 提取证据（银行卡号、手机号、IP等）
    2. 搜索相似案件（RAG 检索）
    3. 评估风险等级
    4. 生成分析报告
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        
        # 初始化工具
        self.tools = {
            "extract_evidence": ExtractEvidenceTool(),
            "search_similar_cases": SearchSimilarCasesTool(),
            "assess_risk": AssessRiskTool(),
            "get_case_detail": GetCaseDetailTool()
        }
        
        # 初始化工具沙箱
        self.sandbox = ToolSandbox(timeout=30.0, max_memory_mb=512, max_retries=2)
        
        # 初始化 Agent 运行时
        self.runtime = AgentRuntime(
            agent_id="analyst_agent",
            agent_type="analyst",
            tools={name: tool.execute for name, tool in self.tools.items()},
            max_iterations=5,
            enable_reflection=True
        )
    
    def analyze(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析案件（同步接口，兼容旧代码）
        
        Args:
            case_data: 案件数据，包含 description, text_messages 等
        
        Returns:
            分析结果字典
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._analyze_async(case_data)).result()
            else:
                result = loop.run_until_complete(self._analyze_async(case_data))
        except RuntimeError:
            # 没有事件循环，创建新的
            result = asyncio.run(self._analyze_async(case_data))
        
        return result
    
    async def _analyze_async(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """异步分析案件"""
        
        # 提取案件文本
        description = case_data.get("description", "")
        text_messages = case_data.get("text_messages", [])
        
        if text_messages:
            case_text = "\n".join(text_messages)
        else:
            case_text = description
        
        if not case_text:
            return self._create_fallback_result("缺少案件描述")
        
        # 1. 提取证据
        evidence_result = self.tools["extract_evidence"].execute(text=case_text)
        extracted_entities = evidence_result.data.get("extracted_evidence", {}) if evidence_result.success else {}
        
        # 2. 搜索相似案件
        similar_cases = []
        if description:
            similar_result = self.tools["search_similar_cases"].execute(
                description=description,
                top_k=3
            )
            if similar_result.success:
                similar_cases = similar_result.data.get("similar_cases", [])
        
        # 3. 评估风险
        risk_data = {
            "amount": case_data.get("amount", 0),
            "fraud_type": case_data.get("scam_type", "其他"),
            "victim_age": case_data.get("victim_age"),
            "extracted_entities": extracted_entities
        }
        risk_result = self.tools["assess_risk"].execute(case_data=risk_data)
        risk_info = risk_result.data if risk_result.success else {}
        
        # 4. 使用 LLM 生成深度分析
        ai_report = await self._generate_ai_report(case_text, extracted_entities, similar_cases, risk_info)
        
        # 5. 组装结果
        result = {
            "case_id": case_data.get("case_id", ""),
            "message_count": len(text_messages) if text_messages else 1,
            "risk_level": risk_info.get("risk_level", "MEDIUM"),
            "risk_label": risk_info.get("risk_label", "中风险"),
            "risk_type": "danger" if risk_info.get("risk_level") == "HIGH" else "warning" if risk_info.get("risk_level") == "MEDIUM" else "info",
            "risk_score": risk_info.get("risk_score", 70),
            "scam_type": case_data.get("scam_type", "未知"),
            "victim": case_data.get("victim_name", "未知"),
            "amount": str(case_data.get("amount", "未知")),
            "ai_report": ai_report,
            "keywords": self._extract_keywords(extracted_entities),
            "steps": [],
            "roles": [],
            "extracted_entities": self._format_entities(extracted_entities),
            "similar_cases": similar_cases,
            "warning": None
        }
        
        return result
    
    async def _generate_ai_report(
        self,
        case_text: str,
        extracted_entities: Dict,
        similar_cases: List,
        risk_info: Dict
    ) -> str:
        """使用 LLM 生成分析报告"""
        
        if not self.llm:
            return self._generate_basic_report(case_text, extracted_entities, risk_info)
        
        # 构建提示
        similar_cases_text = ""
        if similar_cases:
            similar_cases_text = "\n\n相似案件:\n" + "\n".join([
                f"- {c.get('title', '')} (相似度: {c.get('similarity', 0):.2f})"
                for c in similar_cases[:3]
            ])
        
        prompt = f"""你是一名反诈中心研判专家，请分析以下案件并给出研判结论。

案件描述:
{case_text[:2000]}

提取的证据:
{json.dumps(extracted_entities, ensure_ascii=False, indent=2)}

风险评估:
- 风险等级: {risk_info.get('risk_label', '未知')}
- 风险分数: {risk_info.get('risk_score', 0)}
- 风险因素: {', '.join(risk_info.get('risk_factors', []))}
{similar_cases_text}

请输出:
1. 案件定性（诈骗类型）
2. 关键证据（3-5个关键词）
3. 作案流程简述
4. 处置建议
"""
        
        try:
            response = await self.llm.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            return self._generate_basic_report(case_text, extracted_entities, risk_info)
    
    def _generate_basic_report(
        self,
        case_text: str,
        extracted_entities: Dict,
        risk_info: Dict
    ) -> str:
        """生成基础报告（无 LLM）"""
        
        report_parts = ["【案件研判结论】\n"]
        
        # 案件定性
        fraud_type = "待进一步分析"
        if "冒充" in case_text:
            if "公检法" in case_text or "公安" in case_text:
                fraud_type = "冒充公检法类诈骗"
            elif "客服" in case_text:
                fraud_type = "冒充客服类诈骗"
            elif "熟人" in case_text or "领导" in case_text:
                fraud_type = "冒充熟人类诈骗"
        elif "刷单" in case_text or "返利" in case_text:
            fraud_type = "刷单返利类诈骗"
        elif "投资" in case_text or "理财" in case_text:
            fraud_type = "虚假投资理财类诈骗"
        elif "贷款" in case_text:
            fraud_type = "虚假贷款类诈骗"
        
        report_parts.append(f"1. 【案件定性】{fraud_type}\n")
        
        # 关键证据
        keywords = []
        for entity_type, entity_data in extracted_entities.items():
            if isinstance(entity_data, dict) and entity_data.get("values"):
                keywords.extend(entity_data["values"][:2])
        
        report_parts.append(f"2. 【关键证据】{', '.join(keywords[:5]) if keywords else '待补充'}\n")
        
        # 风险因素
        risk_factors = risk_info.get("risk_factors", [])
        report_parts.append(f"3. 【风险因素】{'; '.join(risk_factors) if risk_factors else '暂无'}\n")
        
        # 处置建议
        recommendation = risk_info.get("recommendation", "建议进一步调查")
        report_parts.append(f"4. 【处置建议】{recommendation}")
        
        return "\n".join(report_parts)
    
    def _extract_keywords(self, extracted_entities: Dict) -> List[str]:
        """提取关键词"""
        keywords = []
        for entity_type, entity_data in extracted_entities.items():
            if isinstance(entity_data, dict):
                keywords.append(entity_data.get("description", entity_type))
        return keywords[:5]
    
    def _format_entities(self, extracted_entities: Dict) -> Dict[str, Any]:
        """格式化实体信息"""
        formatted = {
            "bank_accounts": [],
            "phone_numbers": [],
            "ip_addresses": [],
            "app_names": []
        }
        
        if "bank_account" in extracted_entities:
            formatted["bank_accounts"] = extracted_entities["bank_account"].get("values", [])
        if "phone" in extracted_entities:
            formatted["phone_numbers"] = extracted_entities["phone"].get("values", [])
        if "ip_address" in extracted_entities:
            formatted["ip_addresses"] = extracted_entities["ip_address"].get("values", [])
        
        return formatted
    
    def _create_fallback_result(self, error_msg: str) -> Dict[str, Any]:
        """创建分析失败时的回退结果"""
        return {
            "case_id": "",
            "message_count": 0,
            "risk_level": "UNKNOWN",
            "risk_label": "未知",
            "risk_type": "danger",
            "risk_score": 0,
            "scam_type": "系统异常",
            "victim": "未知",
            "amount": "未知",
            "ai_report": f"⚠️ {error_msg}",
            "keywords": ["Error"],
            "steps": [],
            "roles": [],
            "extracted_entities": {
                "bank_accounts": [],
                "phone_numbers": [],
                "ip_addresses": [],
                "app_names": []
            },
            "warning": error_msg,
            "is_error": True
        }
