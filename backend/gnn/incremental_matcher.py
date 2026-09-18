"""
增量团伙匹配：新案先与已知团伙画像匹配，挂不上的攒批才重聚类。

设计哲学（复用 P3 共识伪标签的"客观置信度门控"）：
  资金共享 + 话术余弦双信号**严格一致**才挂上（宁缺毋滥），
  单信号命中不采信——与 consensus anchor 的"双源一致取交集、巨簇弃用"同构，
  把"规则给锚点、GNN 做泛化"的闭环从批量聚类延伸到流式增量。

对外接口（与 DB 解耦，合成数据可直接喂 case dict 验证）：
  - build_gang_profiles(gangs_members, text_threshold=None) -> profiles
        gangs_members: {gang_id: [case_dict, ...]} 成员案件字典列表
        profile = {case_ids, account_pool, n_members, script_centroid}
  - match_cases_batch(profiles, new_cases, text_threshold=None)
        -> {case_id: {"gang_id", "score", "matched_accounts", "matched_type"}}
  匹配线程安全（只读 profiles），可并发喂案。

账户号鲁棒提取：生产路由传 dict 列表（{'account_number': ...}），
合成数据传纯字符串（'ACC-xxx'），两者都兼容。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 双信号一致门控阈值：话术 BGE 余弦下限。
# 同类团伙话术余弦通常 >0.8（同模板），跨类 <0.6；0.7 为保守档，
# 宁放走（攒批重聚类）也不错挂（宁缺毋滥）。
DEFAULT_TEXT_THRESHOLD = 0.70


def _extract_accounts(case: Dict[str, Any]) -> List[str]:
    """账户号鲁棒提取：兼容 dict 列表与纯字符串列表。"""
    out: List[str] = []
    for a in case.get("accounts") or []:
        if isinstance(a, dict):
            v = a.get("account_number") or a.get("account_no") or ""
        else:
            v = str(a)
        v = str(v).strip()
        if v:
            out.append(v)
    return out


def _case_script_text(case: Dict[str, Any]) -> str:
    """案件话术文本（与 graph_builder 的 _extract_case_text 同字段优先级）。"""
    parts = []
    for key in ("script", "description", "content", "text", "title"):
        val = case.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    joined = " ".join(parts).strip()
    if not joined:
        joined = f"{case.get('scam_type','')} {case.get('victim_address','')}"
    return joined


_BGE_MODEL = None


def _bge_encode(texts: List[str]) -> Optional[np.ndarray]:
    """本地 bge-large-zh-v1.5 批量编码（归一化向量），失败返回 None。"""
    global _BGE_MODEL
    import torch
    from transformers import AutoTokenizer, AutoModel
    model_path = os.path.join(BACKEND, "bge-large-zh-v1.5")
    if not os.path.exists(model_path):
        return None
    if _BGE_MODEL is None:
        _BGE_MODEL = (
            AutoTokenizer.from_pretrained(model_path),
            AutoModel.from_pretrained(model_path).eval(),
        )
    tok, model = _BGE_MODEL
    enc = tok(list(texts), padding=True, truncation=True, max_length=128,
              return_tensors="pt")
    with torch.no_grad():
        out = model(**enc)
    emb = torch.nn.functional.normalize(out.last_hidden_state[:, 0, :], dim=1)
    return emb.cpu().numpy()


class GangProfile:
    __slots__ = ("gang_id", "case_ids", "account_pool", "n_members", "script_centroid")

    def __init__(self, gang_id: str, case_ids: List[str],
                 account_pool: set, script_centroid: Optional[np.ndarray]):
        self.gang_id = gang_id
        self.case_ids = case_ids
        self.account_pool = account_pool
        self.n_members = len(case_ids)
        self.script_centroid = script_centroid


def build_gang_profiles(
    gangs_members: Dict[str, List[Dict[str, Any]]],
    text_threshold: float = DEFAULT_TEXT_THRESHOLD,
) -> Dict[str, GangProfile]:
    """聚合团伙画像：账户池（并集）+ 话术 BGE 质心（成员均值）。

    门控：成员不足 2 案的团伙不产画像（单案无统计意义，宁缺毋滥），
    交由攒批重聚类。话术质心为成员向量均值再归一化，未做 max-pool 平均。
    """
    profiles: Dict[str, GangProfile] = {}
    for gang_id, members in gangs_members.items():
        if not members:
            continue
        case_ids = [m.get("case_id", "") for m in members if m.get("case_id")]
        if len(case_ids) < 2:
            continue
        account_pool = set()
        for m in members:
            account_pool.update(_extract_accounts(m))
        scripts = [_case_script_text(m) for m in members]
        emb = _bge_encode(scripts)
        centroid = None
        if emb is not None:
            centroid = emb.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
        profiles[gang_id] = GangProfile(
            gang_id=gang_id,
            case_ids=case_ids,
            account_pool=account_pool,
            script_centroid=centroid,
        )
    return profiles


def match_cases_batch(
    profiles: Dict[str, GangProfile],
    new_cases: List[Dict[str, Any]],
    text_threshold: float = DEFAULT_TEXT_THRESHOLD,
) -> Dict[str, Dict[str, Any]]:
    """新案与已知画像匹配，返回 {case_id: {gang_id, score, matched_accounts, matched_type}}。

    门控规则（复用共识伪标签哲学，宁缺毋滥）：
      - consensus : 资金共享(>=1 账户) AND 话术余弦 >= text_threshold → 挂上
      - 单信号（仅资金 或 仅话术）不采信 → 不匹配，攒批重聚类
      - 资金共享命中多个团伙 → 取话术余弦最高者（防弱资金误挂）
    """
    if not profiles or not new_cases:
        return {}

    scripts = [_case_script_text(c) for c in new_cases]
    emb = _bge_encode(scripts)

    results: Dict[str, Dict[str, Any]] = {}
    for i, case in enumerate(new_cases):
        cid = case.get("case_id", "")
        if not cid:
            continue
        case_accounts = _extract_accounts(case)
        if emb is not None:
            case_vec = emb[i]
        else:
            case_vec = None

        best = None
        for profile in profiles.values():
            shared = case_accounts and set(case_accounts) & profile.account_pool
            text_sim = -1.0
            if case_vec is not None and profile.script_centroid is not None:
                text_sim = float(np.dot(case_vec, profile.script_centroid))
            if not shared:
                continue
            if text_sim < text_threshold:
                continue
            if best is None or text_sim > best["score"]:
                best = {
                    "gang_id": profile.gang_id,
                    "score": text_sim,
                    "matched_accounts": sorted(shared),
                    "matched_type": "consensus",
                }
        if best is not None:
            results[cid] = best
    return results
