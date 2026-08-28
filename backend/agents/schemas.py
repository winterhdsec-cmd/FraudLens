"""
四单流转文档契约（B-L7，2026-08-04）

对标中正智云"四张单闭环"方法论（警情单→研判单→指令单→反馈单），
为 FraudLens 主链路增加"单"级标准化文档契约：
  - AlarmSlip      警情单：接警要素（案件 / 受害者 / 金额 / 账户 / 话术）
  - AnalysisSlip   研判单：资金流 + 通信流 + 矛盾分析结论
  - DispatchSlip   指令单：团伙聚类结果 + 处置建议 + 置信度
  - FeedbackSlip   反馈单：证据链 + 复盘评价（对接 B-L9 复盘六动作）

设计纪律：
  - **不改变现有数据结构**：四个 Slip 字段从现有 extracted_entities / gangs /
    evidence_chain / freeze_candidates 等映射而来，旧字段 100% 保留。
  - Pydantic v2（项目 requirements 已声明 pydantic>=2.0.0）。
  - 每单只承担一个交付物（事实 / 判断 / 任务 / 结果），"下一个环节拿到就能用"。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------- #
# 四单契约
# --------------------------------------------------------------------- #
class AlarmSlip(BaseModel):
    """警情单：接警要素。由 plan/preprocess 阶段产出，作为分析阶段输入。"""

    case_ids: List[str] = Field(default_factory=list, description="案件编号列表")
    n_cases: int = Field(default=0, description="案件数量")
    total_amount: float = Field(default=0.0, description="涉案金额合计")
    scam_types: List[str] = Field(default_factory=list, description="诈骗类型去重列表")
    key_entities: Dict[str, List[str]] = Field(
        default_factory=dict, description="关键实体汇总（账户/手机号/微信/QQ）"
    )
    risk_levels: List[str] = Field(default_factory=list, description="案件风险等级列表")

    @classmethod
    def from_cases(cls, cases: List[Dict[str, Any]]) -> "AlarmSlip":
        """从案件列表构建警情单（preprocess 之后的案件）。"""
        case_ids = [c.get("case_id", "") for c in cases]
        total_amount = sum(float(c.get("amount", 0) or 0) for c in cases)
        scam_types = sorted({c.get("scam_type", "未知") for c in cases if c.get("scam_type", "未知") != "未知"})
        risk_levels = [c.get("risk_level", "MEDIUM") for c in cases if c.get("risk_level")]
        key_entities: Dict[str, List[str]] = {}
        seen: Dict[str, set] = {}
        for c in cases:
            ents = c.get("extracted_entities", {}) or {}
            for t in ("bank_accounts", "phone_numbers", "wechat_ids", "qq_numbers"):
                for v in (ents.get(t) or []):
                    seen.setdefault(t, set()).add(str(v))
        for t, vs in seen.items():
            key_entities[t] = sorted(vs)
        return cls(
            case_ids=case_ids,
            n_cases=len(cases),
            total_amount=round(total_amount, 2),
            scam_types=scam_types,
            key_entities=key_entities,
            risk_levels=risk_levels,
        )


class AnalysisSlip(BaseModel):
    """研判单：资金流 + 通信流 + 矛盾分析结论。由 analyze 阶段产出。"""

    case_analyses: List[Dict[str, Any]] = Field(default_factory=list, description="单案分析结果（analyzed_cases）")
    fund_flow_notes: List[str] = Field(default_factory=list, description="资金流分析要点")
    comm_flow_notes: List[str] = Field(default_factory=list, description="通信流分析要点")
    contradiction_notes: List[str] = Field(default_factory=list, description="矛盾识别要点（话术 vs 资金不一致）")
    analysis_quality: float = Field(default=0.0, description="分析质量分（0-1）")

    @classmethod
    def from_analyzed(cls, analyzed_cases: List[Dict[str, Any]]) -> "AnalysisSlip":
        """从分析后案件构建研判单。"""
        notes_fund: List[str] = []
        notes_comm: List[str] = []
        notes_contra: List[str] = []
        for c in analyzed_cases:
            ents = c.get("extracted_entities", {}) or {}
            bank = ents.get("bank_accounts", []) or []
            phones = ents.get("phone_numbers", []) or []
            wechat = ents.get("wechat_ids", []) or []
            qq = ents.get("qq_numbers", []) or []
            if bank:
                notes_fund.append(f"{c.get('case_id','')}: 涉及 {len(bank)} 个收款账户")
            if phones or wechat or qq:
                notes_comm.append(
                    f"{c.get('case_id','')}: 涉及手机号 {len(phones)} / 微信 {len(wechat)} / QQ {len(qq)}"
                )
            # 矛盾识别启发式：话术（scam_type）与金额量级不匹配
            scam = c.get("scam_type", "") or ents.get("scam_type", "")
            amt = float(c.get("amount", 0) or 0)
            if scam == "刷单返利" and amt > 50000:
                notes_contra.append(f"{c.get('case_id','')}: 刷单返利案金额偏高({amt:.0f}元)，需复核")
            if scam == "冒充客服" and amt > 100000:
                notes_contra.append(f"{c.get('case_id','')}: 冒充客服案金额异常({amt:.0f}元)，需复核")
        quality = min(1.0, 0.5 + 0.1 * len(notes_fund) + 0.1 * len(notes_comm)) if analyzed_cases else 0.0
        return cls(
            case_analyses=analyzed_cases,
            fund_flow_notes=notes_fund,
            comm_flow_notes=notes_comm,
            contradiction_notes=notes_contra,
            analysis_quality=round(quality, 4),
        )


class DispatchSlip(BaseModel):
    """指令单：团伙聚类结果 + 处置建议 + 置信度。由 cluster 阶段产出。"""

    gangs: List[Dict[str, Any]] = Field(default_factory=list, description="团伙列表（含 evidence_chain）")
    total_gangs: int = Field(default=0, description="团伙数量")
    quality_score: float = Field(default=0.0, description="聚类质量分")
    strategy: Dict[str, Any] = Field(default_factory=dict, description="聚类策略")
    freeze_suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="冻卡建议（按置信度门控）")
    dispatch_notes: List[str] = Field(default_factory=list, description="处置建议")

    @classmethod
    def from_gang_result(cls, gang_result: Dict[str, Any]) -> "DispatchSlip":
        """从团伙聚类结果构建指令单。"""
        gangs = gang_result.get("gangs", [])
        freeze: List[Dict[str, Any]] = []
        dispatch: List[str] = []
        for g in gangs:
            if g.get("is_reflux") or g.get("risk_level") == "HIGH":
                freeze.append({
                    "gang_id": g.get("gang_id"),
                    "risk_level": g.get("risk_level"),
                    "freeze_candidates": g.get("freeze_candidates", []),
                    "reason": "资金回流闭环或高风险",
                })
                dispatch.append(f"{g.get('gang_id','')}: 建议冻结 {len(g.get('freeze_candidates', []))} 个账户")
            else:
                dispatch.append(f"{g.get('gang_id','')}: 建议人工复核（置信度不足）")
        return cls(
            gangs=gangs,
            total_gangs=gang_result.get("total_gangs", len(gangs)),
            quality_score=gang_result.get("quality_score", 0.0),
            strategy=gang_result.get("strategy", {}),
            freeze_suggestions=freeze,
            dispatch_notes=dispatch,
        )


class FeedbackSlip(BaseModel):
    """反馈单：证据链 + 复盘评价。由 reflect 阶段产出（对接 B-L9 复盘六动作）。"""

    quality_score: float = Field(default=0.0, description="总体质量分")
    reflection: Dict[str, Any] = Field(default_factory=dict, description="反思记录（should_retry/retry_count 等）")
    evidence_summary: List[str] = Field(default_factory=list, description="证据链摘要")
    review_chain: Optional[Dict[str, Any]] = Field(default=None, description="复盘六动作记录（B-L9）")
    abnormal: str = Field(default="none", description="异常卡标记：none/missing_data/model_conflict/timeout（B-L13）")
    abnormal_detail: Optional[Dict[str, Any]] = Field(default=None, description="异常详情")

    @classmethod
    def from_reflection(cls, reflection: Dict[str, Any], gangs: List[Dict[str, Any]]) -> "FeedbackSlip":
        """从反思结果构建反馈单。"""
        evidence: List[str] = []
        for g in gangs:
            for ec in g.get("evidence_chain", []):
                evidence.append(
                    f"因共享{ec.get('type','')} {ec.get('value','')} 关联案件 {','.join(ec.get('case_ids', []))}"
                )
        return cls(
            quality_score=reflection.get("quality_score", 0.0),
            reflection=reflection,
            evidence_summary=evidence[:10],
        )


def build_warnings(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 orchestrator 结果中的 abnormal / 低质量分 转成前端可渲染的告警列表（REQ-S7 失败边界提示）。

    纯结构化派生，不依赖 LLM/外部服务。返回 [{"level","type","message","action"}]。
    level: error（阻断级，如数据缺失）/ warning（建议人工复核）。
    """
    warnings: List[Dict[str, Any]] = []

    abnormal = result.get("abnormal", "none") or "none"
    abnormal_detail = result.get("abnormal_detail") or {}
    if abnormal != "none":
        level = "error" if abnormal == "missing_data" else "warning"
        warnings.append({
            "level": level,
            "type": abnormal,
            "message": abnormal_detail.get("reason", f"检测到异常：{abnormal}"),
            "action": abnormal_detail.get("action", "建议人工介入复核"),
            "stage": abnormal_detail.get("stage"),
        })

    # 低质量分提示：质量分 < 0.6 视为"可信度较低，仅供参考"
    slips = result.get("slips") or {}
    feedback = slips.get("feedback") or {}
    qs = feedback.get("quality_score", 0.0) or 0.0
    if not qs and result.get("statistics"):
        qs = float(result.get("statistics", {}).get("quality_score", 0.0) or 0.0)
    if qs and qs < 0.6:
        warnings.append({
            "level": "warning",
            "type": "low_confidence",
            "message": f"本次研判质量分较低（{qs:.2f}），结果仅供参考，建议人工复核",
            "action": "人工复核团伙划分与冻卡建议",
        })

    return warnings


def build_slips(
    cases: List[Dict[str, Any]],
    analyzed_cases: List[Dict[str, Any]],
    gang_result: Dict[str, Any],
    reflection: Dict[str, Any],
    review_chain: Optional[Dict[str, Any]] = None,
    abnormal: str = "none",
    abnormal_detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """把主链路各阶段产出组装为四单流转容器。

    Args:
        cases: 预处理后的案件列表（用于构建警情单）
        analyzed_cases: 分析后案件（用于构建研判单）
        gang_result: 团伙聚类结果（用于构建指令单）
        reflection: 反思记录（用于构建反馈单）
        review_chain: 复盘六动作记录（可选，B-L9）
        abnormal: 异常标记（可选，B-L13）
        abnormal_detail: 异常详情（可选，B-L13）
    """
    alarm = AlarmSlip.from_cases(cases)
    analysis = AnalysisSlip.from_analyzed(analyzed_cases)
    dispatch = DispatchSlip.from_gang_result(gang_result)
    feedback = FeedbackSlip.from_reflection(reflection, gang_result.get("gangs", []))
    feedback.review_chain = review_chain
    feedback.abnormal = abnormal
    feedback.abnormal_detail = abnormal_detail
    return {
        "alarm": alarm.model_dump(),
        "analysis": analysis.model_dump(),
        "dispatch": dispatch.model_dump(),
        "feedback": feedback.model_dump(),
    }
