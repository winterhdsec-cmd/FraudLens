"""
笔录 / OCR 文本 → 结构化案件实体（REQ-S1.4 落库链路，2026-08-05）

把上传的报案笔录、OCR 文本拆成多起案件，逐案抽取实体（账户/手机号/微信/QQ/金额/
身份证），识别诈骗类型与受害人，产出与 orchestrator / save_case 兼容的 case dict 列表。

设计纪律：
  - 纯正则 + 关键词，零 LLM、零出域，无网环境可跑（复用 tools.evidence_tools.extract_entities_regex）。
  - 只做"抽取 + 落库前的结构化"，不判定团伙；团伙交给 orchestrator。
  - 单文本最多拆 50 起，避免异常输入爆内存。
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List

from tools.evidence_tools import extract_entities_regex

# 诈骗类型关键词 → 标准 scam_type（与 synthetic_data / analyst 约定一致）
_SCAM_KEYWORDS = [
    ("刷单返利", ["刷单", "返利", "刷单返利", "兼职刷单"]),
    ("杀猪盘", ["杀猪盘", "虚假投资", "投资理财", "博彩", "网恋"]),
    ("冒充客服", ["京东客服", "京东金融", "冒充客服", "客服", "注销校园贷", "征信", "白条", "金条"]),
    ("贷款诈骗", ["贷款", "网贷", "套路贷", "低息贷款"]),
    ("冒充公检法", ["公检法", "公安", "检察院", "法院", "通缉令", "安全账户"]),
    ("冒充熟人", ["冒充领导", "冒充老板", "冒充好友", "借钱"]),
    ("网购退款", ["网购", "快递", "退款", "理赔", "淘宝", "退货"]),
    ("虚假中奖", ["中奖", "抽奖", "红包"]),
]


def _detect_scam_type(text: str, ents: Dict[str, Any]) -> str:
    for label, kws in _SCAM_KEYWORDS:
        for kw in kws:
            if kw in text:
                return label
    return "未知"


def _detect_victim(text: str) -> str:
    m = re.search(r"受害人([一-鿿]{1,4})(女士|先生|同学|大爷|大妈|老人)?", text)
    if m:
        return (m.group(1) + (m.group(2) or "")).strip()
    m = re.search(r"([一-鿿]{1,3})(女士|先生|同学)报警", text)
    if m:
        return (m.group(1) + m.group(2)).strip()
    return ""


def _has_case_signal(p: str) -> bool:
    """判断是否含有案情信号关键词（避免把闲聊/无关文本当案件）。"""
    return any(k in p for k in ("报警", "被骗", "转账", "诈骗", "损失", "汇款"))


def split_cases(text: str) -> List[str]:
    """把多案文本拆成若干"单案片段"（仅当含案情信号时才算案件）。"""
    if not text or not text.strip():
        return []
    # 以"受害人"为界切分（最自然的单案起点）
    parts = re.split(r"(?=受害人)", text)
    cases = [p.strip() for p in parts if p.strip() and _has_case_signal(p)]
    if not cases:
        # 回退：按空行分段，仍要求含案情信号（避免噪声文本被误判为案件）
        cases = [c.strip() for c in re.split(r"\n\s*\n", text)
                 if len(c.strip()) > 10 and _has_case_signal(c)]
    return cases[:50]


def text_to_cases(text: str, source: str = "笔录/OCR") -> List[Dict[str, Any]]:
    """把笔录/OCR 文本转为结构化案件列表（兼容 orchestrator 输入与 database.crud.save_case）。"""
    chunks = split_cases(text)
    out: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        ents = extract_entities_regex(ch)
        scam_type = _detect_scam_type(ch, ents)
        victim = _detect_victim(ch)
        amounts = []
        for a in ents.get("amounts", []):
            try:
                amounts.append(float(a))
            except (ValueError, TypeError):
                pass
        amount_value = max(amounts) if amounts else 0.0
        amount_str = f"{amount_value:.2f}" if amount_value else "0"
        case_id = f"CASE_TXT_{uuid.uuid4().hex[:8]}_{i}"
        out.append({
            "case_id": case_id,
            "title": (f"{victim}被{scam_type}案" if victim else f"案件{i + 1}（{scam_type}）"),
            "scam_type": scam_type,
            "victim": victim,
            "amount": amount_str,
            "amount_value": amount_value,
            "description": ch[:1000],
            "source": source,
            "extracted_entities": ents,
            "risk_level": "MEDIUM",
            "is_error": False,
        })
    return out
