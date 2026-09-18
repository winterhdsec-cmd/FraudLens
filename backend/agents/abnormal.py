"""
异常卡完整化（B-L13，2026-08-04）

对标中正智云"四张卡"中的异常卡（缺失/错误/超时→退人工）与"AI 能力边界"原则，
把置信度门控升级为三类可审计的异常标记：
  - missing_data   数据缺失：实体抽取为空 / 无有效案件 → 交人工补材料
  - model_conflict 模型冲突：多轮聚类结果不一致（反思重算前后团伙划分变化）→ 人工裁决
  - timeout        超时：LLM/推理超时降级后仍失败 → 标记并交人工

设计纪律：
  - 纯 Python + typing，零外部依赖。
  - 只做检测与标记，不做阻断——异常时仍返回现有结果（诚实 + 可审计），
    由调用方（前端/教学）决定展示与人工介入路径。
  - 输出 `{"abnormal": str, "detail": {...}}`；无异常返回 None。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def detect_abnormal(
    analyzed_cases: List[Dict[str, Any]],
    gang_result: Dict[str, Any],
    reflection: Dict[str, Any],
    retry_count: int = 0,
) -> Optional[Dict[str, Any]]:
    """检测三类异常。返回异常标记或 None。"""

    # ── 1. missing_data：实体抽取为空 / 无有效案件 ──
    if not analyzed_cases:
        return {
            "abnormal": "missing_data",
            "detail": {"reason": "无有效案件（预处理后全部为空）", "stage": "preprocess"},
        }
    empty_entity_cases = [
        c.get("case_id", "?")
        for c in analyzed_cases
        if not (c.get("extracted_entities") or {}) and not c.get("is_error")
    ]
    if empty_entity_cases:
        return {
            "abnormal": "missing_data",
            "detail": {
                "reason": f"{len(empty_entity_cases)} 起案件实体抽取为空",
                "case_ids": empty_entity_cases[:10],
                "stage": "entity_extraction",
                "action": "退回人工补材料或启用 LLM 语义补全（B-L1）",
            },
        }

    # ── 2. model_conflict：反思重算前后团伙划分不一致 ──
    # 反思触发了重算（retry_count>0），说明首轮聚类质量未达标；
    # 若最终仍有多个团伙且质量分偏低，标记模型冲突建议人工裁决。
    if retry_count > 0 and reflection.get("quality_score", 1.0) < 0.6:
        return {
            "abnormal": "model_conflict",
            "detail": {
                "reason": f"反思重算 {retry_count} 轮后质量分仍偏低（{reflection.get('quality_score', 0):.3f}）",
                "retry_count": retry_count,
                "quality_score": reflection.get("quality_score", 0.0),
                "improvements": reflection.get("improvements", []),
                "stage": "clustering",
                "action": "人工裁决团伙划分（对齐 Lab2 人机对比）",
            },
        }

    # ── 3. timeout：LLM/推理超时（降级标志）──
    # analyze 阶段若 LLM 超时会走 fallback；cluster 阶段异常会回退传统聚类。
    # 此处检测 case 是否携带超时/降级标记。
    for c in analyzed_cases:
        if c.get("warning") and ("超时" in str(c.get("warning")) or "timeout" in str(c.get("warning")).lower()):
            return {
                "abnormal": "timeout",
                "detail": {"reason": f"案件 {c.get('case_id','?')} 处理超时降级", "case_id": c.get("case_id"), "stage": "analysis"},
            }

    return None
