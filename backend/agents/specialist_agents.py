"""
专科 Agent 拆分（B-L8，2026-08-04）

对标中正智云"11 个专科 Agent"架构，把 analyst / cluster / chat 三个粗粒度 Agent
的职责拆为 9 个可插拔专科 Agent，注册进 registry（stage="specialist"）：

  extractor     接警要素抽取（复用 AnalystAgent._analyze_async 的实体抽取逻辑）
  fundflow      资金流分析（复用 ClusterAgent._detect_reflux / graph_builder）
  commflow      通信流分析（手机号/微信/QQ 关联特征）
  contradiction 矛盾识别（话术 vs 资金量级不一致）
  case_rag      话术/类案检索（对接 B-L12 corpus_rag）
  gangcluster   团伙聚类（复用 ClusterAgent.discover_gangs / _cluster_by_entities）
  profiler      团伙画像（从 gang_result 生成画像摘要）
  reporter      报告生成（复用 AnalystAgent._generate_basic_report / LLM）
  chat_tutor    教学问答（规则式，面向 Lab 场景）

设计纪律：
  - **主链路行为不变**：全部注册到 stage="specialist"，不参与默认 analyze/cluster
    主链路执行；原 AnalystAgent/ClusterAgent/ChatAgent 保留为聚合门面。
  - 教学模式可按 Lab 单独挂载（如 Lab2 只跑 case_rag + gangcluster）。
  - 惰性导入重依赖（torch/networkx/BGE），import 本模块不触发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.protocol import AgentProtocol


class _SpecialistAgent(AgentProtocol):
    """专科 Agent 基类：stage 统一为 specialist。"""
    name: str = "specialist"
    stage: str = "specialist"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


# --------------------------------------------------------------------- #
# 1. extractor 接警要素抽取
# --------------------------------------------------------------------- #
class ExtractorAgent(_SpecialistAgent):
    name = "extractor"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"text": str} 或 {"case": dict}。返回 extracted_entities。"""
        text = context.get("text")
        case = context.get("case")
        if text is None and case is not None:
            text = case.get("description", "") or "\n".join(case.get("text_messages", []))
        if not text:
            return {"is_error": True, "error": "missing text", "agent": self.name}

        from tools.evidence_tools import extract_entities_regex
        entities = extract_entities_regex(text)
        # 可选 LLM 语义补全（复用 AnalystAgent 的抽取逻辑）
        if context.get("use_llm") and context.get("llm_client"):
            from agents.analyst_agent import AnalystAgent
            aa = AnalystAgent(llm_client=context["llm_client"])
            import asyncio
            try:
                llm_ents = asyncio.run(aa._extract_entities_llm(text))
                if llm_ents:
                    entities = aa._merge_entities(entities, llm_ents)
            except Exception:
                pass
        return {"extracted_entities": entities, "agent": self.name}


# --------------------------------------------------------------------- #
# 2. fundflow 资金流分析
# --------------------------------------------------------------------- #
class FundFlowAgent(_SpecialistAgent):
    name = "fundflow"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"cases": [...], "accounts_tx": [...]}。返回资金流分析（含回流闭环检测）。"""
        cases = context.get("cases", [])
        accounts_tx = context.get("accounts_tx")

        notes: List[str] = []
        for c in cases:
            ents = c.get("extracted_entities", {}) or {}
            bank = ents.get("bank_accounts", []) or []
            if bank:
                notes.append(f"{c.get('case_id','')}: 涉及 {len(bank)} 个收款账户")

        reflux = {"is_reflux": False, "cycles": [], "freeze_candidates": []}
        if accounts_tx:
            try:
                from gnn.graph_builder import FraudGraphBuilder
                import networkx as nx
                builder = FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=False)
                gb_cases = []
                for c in cases:
                    cc = dict(c)
                    ents = c.get("extracted_entities", {}) or {}
                    cc["accounts"] = list(ents.get("bank_accounts", []) or [])
                    gb_cases.append(cc)
                builder.build_graph(gb_cases, accounts_tx=accounts_tx)
                DG = builder.get_fund_flow_digraph()
                cycles = list(nx.simple_cycles(DG)) if DG.number_of_nodes() else []
                clean = [[a[8:] if a.startswith("account_") else a for a in cyc] for cyc in cycles]
                freeze = sorted({a[8:] if a.startswith("account_") else a for cyc in cycles for a in cyc})
                reflux = {"is_reflux": len(cycles) > 0, "cycles": clean, "freeze_candidates": freeze}
            except Exception as e:
                reflux["error"] = str(e)

        return {"fund_flow_notes": notes, "reflux": reflux, "agent": self.name}


# --------------------------------------------------------------------- #
# 3. commflow 通信流分析
# --------------------------------------------------------------------- #
class CommFlowAgent(_SpecialistAgent):
    name = "commflow"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"cases": [...]}。返回通信流关联特征（手机号/微信/QQ 共享分析）。"""
        cases = context.get("cases", [])
        notes: List[str] = []
        comm_entities: Dict[str, List[str]] = {"phone_numbers": [], "wechat_ids": [], "qq_numbers": []}
        for c in cases:
            ents = c.get("extracted_entities", {}) or {}
            phones = ents.get("phone_numbers", []) or []
            wechat = ents.get("wechat_ids", []) or []
            qq = ents.get("qq_numbers", []) or []
            if phones or wechat or qq:
                notes.append(
                    f"{c.get('case_id','')}: 手机号 {len(phones)} / 微信 {len(wechat)} / QQ {len(qq)}"
                )
            for t in ("phone_numbers", "wechat_ids", "qq_numbers"):
                for v in (ents.get(t) or []):
                    if str(v) not in comm_entities[t]:
                        comm_entities[t].append(str(v))
        return {"comm_flow_notes": notes, "comm_entities": comm_entities, "agent": self.name}


# --------------------------------------------------------------------- #
# 4. contradiction 矛盾识别
# --------------------------------------------------------------------- #
class ContradictionAgent(_SpecialistAgent):
    name = "contradiction"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"cases": [...]}。返回话术 vs 资金量级矛盾提示（启发式）。"""
        cases = context.get("cases", [])
        notes: List[str] = []
        for c in cases:
            ents = c.get("extracted_entities", {}) or {}
            scam = c.get("scam_type", "") or ents.get("scam_type", "")
            amt = float(c.get("amount", 0) or 0)
            cid = c.get("case_id", "")
            if scam == "刷单返利" and amt > 50000:
                notes.append(f"{cid}: 刷单返利案金额偏高({amt:.0f}元)，需复核")
            if scam == "冒充客服" and amt > 100000:
                notes.append(f"{cid}: 冒充客服案金额异常({amt:.0f}元)，需复核")
        return {"contradiction_notes": notes, "agent": self.name}


# --------------------------------------------------------------------- #
# 5. case_rag 话术/类案检索（对接 B-L12 corpus_rag）
# --------------------------------------------------------------------- #
class CaseRAGAgent(_SpecialistAgent):
    name = "case_rag"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"query": str, "top_k": int}。返回相似话术/类案。"""
        query = context.get("query") or context.get("case_description", "")
        top_k = int(context.get("top_k", 3))
        if not query:
            return {"is_error": True, "error": "missing query", "agent": self.name}
        try:
            from gnn.adapters.corpus_rag import CorpusRAG
            rag = CorpusRAG()
            hits = rag.search(query, top_k=top_k)
            return {"similar_cases": hits, "agent": self.name}
        except Exception as e:
            return {"similar_cases": [], "error": str(e), "agent": self.name}


# --------------------------------------------------------------------- #
# 6. gangcluster 团伙聚类
# --------------------------------------------------------------------- #
class GangClusterAgent(_SpecialistAgent):
    name = "gangcluster"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"cases": [...], "use_gnn": bool, "accounts_tx": [...]}。返回团伙聚类结果。"""
        from agents.cluster_agent import ClusterAgent
        cl = ClusterAgent(
            llm_client=context.get("llm_client"),
            embedding_model=context.get("embedding_model"),
            use_gnn=bool(context.get("use_gnn", True)),
        )
        result = cl.discover_gangs(
            cases=context.get("cases", []),
            use_gnn=context.get("use_gnn"),
            accounts_tx=context.get("accounts_tx"),
        )
        result["agent"] = self.name
        return result


# --------------------------------------------------------------------- #
# 7. profiler 团伙画像
# --------------------------------------------------------------------- #
class ProfilerAgent(_SpecialistAgent):
    name = "profiler"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"gang_result": {...}}。返回团伙画像摘要。"""
        gang_result = context.get("gang_result", {})
        gangs = gang_result.get("gangs", [])
        profiles = []
        for g in gangs:
            profiles.append({
                "gang_id": g.get("gang_id"),
                "fraud_type": g.get("fraud_type"),
                "risk_level": g.get("risk_level"),
                "n_cases": g.get("total_cases"),
                "total_amount": g.get("total_amount"),
                "entities_summary": {
                    t: len(vs) for t, vs in (g.get("entities", {}) or {}).items()
                },
                "is_reflux": g.get("is_reflux", False),
                "freeze_candidates_n": len(g.get("freeze_candidates", []) or []),
            })
        return {"profiles": profiles, "agent": self.name}


# --------------------------------------------------------------------- #
# 8. reporter 报告生成
# --------------------------------------------------------------------- #
class ReporterAgent(_SpecialistAgent):
    name = "reporter"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"case": dict, "llm_client": optional}。返回单案研判报告。"""
        case = context.get("case")
        if not case:
            return {"is_error": True, "error": "missing case", "agent": self.name}
        from agents.analyst_agent import AnalystAgent
        aa = AnalystAgent(llm_client=context.get("llm_client"))
        result = aa.analyze(case)
        result["agent"] = self.name
        return result


# --------------------------------------------------------------------- #
# 9. chat_tutor 教学问答（规则式，面向 Lab 场景）
# --------------------------------------------------------------------- #
class ChatTutorAgent(_SpecialistAgent):
    name = "chat_tutor"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """context={"question": str}。返回规则式教学问答（Lab 场景引导）。"""
        q = (context.get("question") or "").strip()
        if not q:
            return {"is_error": True, "error": "missing question", "agent": self.name}

        answer = self._answer(q)
        return {"answer": answer, "agent": self.name}

    @staticmethod
    def _answer(question: str) -> str:
        q = question
        if any(k in q for k in ("串并", "并案", "同伙")):
            return (
                "串并案是判断多个案件是否由同一团伙实施的过程。可先按共享账户/手机号/微信/QQ "
                "做人工判断，再运行系统对比（Lab2）。提示：系统能发现多跳关联，但也会漏掉"
                "基于办案经验的线索——AI 是辅助工具而非替代。"
            )
        if any(k in q for k in ("冻卡", "冻结", "门控")):
            return (
                "冻卡决策要权衡误冻与漏冻：阈值设高会误冻无辜者账户（影响取款），设低会放过"
                "团伙转移资金（Lab3）。算法只给置信度，责任由人承担——请记录你的决策理由。"
            )
        if any(k in q for k in ("边界", "局限", "失败", "不准")):
            return (
                "反诈 GNN 的能力边界：合成数据不等于真实警务数据；盲扫全败（F1≈0.002），"
                "锚点扩线才有效（Lab4）。诚实评估模型能力是职业责任。"
            )
        if any(k in q for k in ("流程", "研判", "步骤")):
            return (
                "研判流程：案情分析（Lab1）→ 工具辅助串并案（Lab2）→ 冻卡决策（Lab3）→ "
                "边界反思（Lab4）。系统内部是警情单→研判单→指令单→反馈单的四单流转。"
            )
        return (
            "我是 FraudLens 教学问答助手，可解答串并案、冻卡决策、模型边界、研判流程等问题。"
            "当前为规则式回答，LLM 增强版本可接入 DeepSeek。"
        )


# --------------------------------------------------------------------- #
# 注册表引导
# --------------------------------------------------------------------- #
SPECIALIST_CLASSES: List[type] = [
    ExtractorAgent,
    FundFlowAgent,
    CommFlowAgent,
    ContradictionAgent,
    CaseRAGAgent,
    GangClusterAgent,
    ProfilerAgent,
    ReporterAgent,
    ChatTutorAgent,
]


def register_specialist_agents() -> None:
    """注册 9 个专科 Agent（stage="specialist"，不参与默认主链路执行）。"""
    from agents.registry import registry
    for cls in SPECIALIST_CLASSES:
        registry.register(cls, stage="specialist", name=cls.name)
