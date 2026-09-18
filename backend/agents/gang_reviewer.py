"""
Gang Reviewer —— 团伙复核解释层（Skill A/B）

定位：在"GNN / 实体关联 聚类"产出团伙划分之后，作为 **复核解释层** 追加，不替代聚类判断。

- Skill A（并案依据解释器）：为每个团伙生成"共享账户 / 话术指纹 / 资金链路"三要素人话解释，
  让 AI 的并案判断"说得出为什么"（可解释性，非黑盒）。
- Skill B（误并案探测器）：用少量"已知非同一团伙"反例复查聚类结果，标出可疑并案，
  对应"多智能体反思闭环"卖点，可进论文消融与国创赛演示。

设计约束：
- 纯增量，不动 GNN / 聚类主链路；LLM 不可用时规则降级，绝不抛异常。
- 云端 LLM 统一走 core.llm_client.get_llm_client()，遵守"数据不出域 / 脱敏"默认。
- 输出均为结构化 dict，可序列化进 result，方便前端展示与论文实验记录。
"""
import json
import os
from typing import Any, Dict, List, Optional

from core.llm_client import get_llm_client, wrap_messages, cloud_llm_enabled, get_llm_model

# ---------------------------------------------------------------------------
# 共享常量
# ---------------------------------------------------------------------------
ENTITY_TYPES = ("bank_accounts", "phone_numbers", "wechat_ids", "qq_numbers", "id_cards")
ENTITY_LABELS = {
    "bank_accounts": "共享银行账户",
    "phone_numbers": "共享手机号",
    "wechat_ids": "共享微信号",
    "qq_numbers": "共享QQ号",
    "id_cards": "共享身份证",
}


def _fmt_amount(v: Any) -> str:
    """金额可读化：整数去 .0，千分位分隔。"""
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f):
        return f"{int(f):,}"
    return f"{f:,.2f}"


# ---------------------------------------------------------------------------
# Skill A：并案依据解释器
# ---------------------------------------------------------------------------
class MergeEvidenceExplainer:
    """为每个团伙生成"为什么这些案件是一伙"的三要素解释。"""

    def __init__(self, llm_client=None):
        self._llm = llm_client

    def _get_llm(self):
        # False = 显式禁用（enable_llm=False 时由 review_gangs 传入哨兵）
        if self._llm is False:
            return None
        if self._llm is not None:
            return self._llm
        return get_llm_client()

    # ---------- 证据抽取（纯规则，不依赖 LLM） ----------
    @staticmethod
    def _collect_evidence(gang: Dict[str, Any], cases_map: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
        """从团伙的 case_ids + cases_map 抽取三类证据（结构化，规则可复现）。"""
        case_ids = gang.get("case_ids") or gang.get("cases") or []
        members = [cases_map.get(cid, {}) for cid in case_ids]
        members = [m for m in members if m]

        # 1) 共享账户/手机号/社交账号（实体关联）
        shared_entities: Dict[str, List[str]] = {}
        for t in ENTITY_TYPES:
            seen: Dict[str, List[Any]] = {}
            for m in members:
                ents = (m.get("extracted_entities") or {}).get(t, []) or []
                for v in ents:
                    v = str(v).strip()
                    if v:
                        seen.setdefault(v, []).append(m.get("case_id") or m.get("id"))
            shared_entities[t] = [v for v, ids in seen.items() if len(set(ids)) >= 2]

        # 2) 话术指纹：团伙级 fingerprints 或案件 description 的相似关键词
        fingerprint = gang.get("fingerprint") or gang.get("enhanced_fingerprint") or []
        if isinstance(fingerprint, list):
            fingerprint = fingerprint[:6]

        # 3) 资金链路：复用 cluster_agent 已算出的 reflux / evidence_chain
        evidence_chain = gang.get("evidence_chain") or []
        reflux_cycles = gang.get("reflux_cycles") or []
        freeze_candidates = gang.get("freeze_candidates") or []

        return {
            "shared_entities": {t: vs for t, vs in shared_entities.items() if vs},
            "fingerprint": fingerprint,
            "evidence_chain": evidence_chain,
            "reflux_cycles": reflux_cycles,
            "freeze_candidates": freeze_candidates,
            "total_amount": gang.get("total_amount") or 0,
            "case_count": len(case_ids),
        }

    @staticmethod
    def _rule_based_explain(ev: Dict[str, Any]) -> List[str]:
        """规则降级：把结构化证据翻译成自然语言句子（LLM 不可用时保证有输出）。"""
        lines = []
        se = ev.get("shared_entities") or {}
        if se:
            for t, vs in se.items():
                label = ENTITY_LABELS.get(t, t)
                lines.append(f"{label}：{'、'.join(vs[:3])}{' 等' if len(vs) > 3 else ''}（{len(vs)} 个）")
        if ev.get("fingerprint"):
            lines.append("话术指纹：与团伙模板高度一致，关键词「" + "、".join(ev["fingerprint"][:4]) + "」")
        if ev.get("evidence_chain"):
            n = len(ev["evidence_chain"])
            lines.append(f"实体关联证据链：{n} 组跨案共享实体将本团伙案件连通")
        if ev.get("reflux_cycles"):
            lines.append(f"资金回流闭环：检测到 {len(ev['reflux_cycles'])} 个资金环，建议关注收款账户 {len(ev.get('freeze_candidates') or [])} 个")
        if not lines:
            lines.append("未检出显式共享实体/资金关联，并案主要依赖语义聚类（话术相似度）。")
        return lines

    async def explain_gang(
        self,
        gang: Dict[str, Any],
        cases_map: Dict[Any, Dict[str, Any]],
        gang_index: int = 0,
    ) -> Dict[str, Any]:
        """为单个团伙生成解释。返回结构化 dict：{gang_id, summary, evidence, explanation, source}。"""
        gang_id = gang.get("gang_id") or gang.get("id") or f"GANG_{gang_index:03d}"
        ev = self._collect_evidence(gang, cases_map)
        rule_lines = self._rule_based_explain(ev)
        summary = (
            f"团伙 {gang_id} 共 {ev['case_count']} 起案件、涉案 {_fmt_amount(ev['total_amount'])} 元。"
            + "".join(rule_lines)
        )

        # LLM 增强：把规则证据组织成给 LLM 的 prompt，生成更自然的办案语言解释
        llm = self._get_llm()
        llm_text = None
        source = "rule"
        if llm is not None:
            try:
                import asyncio
                evidence_text = json.dumps({
                    "gang_id": gang_id,
                    "case_count": ev["case_count"],
                    "total_amount": ev["total_amount"],
                    "shared_entities": ev["shared_entities"],
                    "fingerprint": ev["fingerprint"],
                    "reflux_cycles": ev["reflux_cycles"],
                    "freeze_candidates": ev["freeze_candidates"],
                }, ensure_ascii=False, default=str)
                prompt = (
                    "你是反诈研判系统的并案依据解释器。以下是一个 AI 聚类出的诈骗团伙的结构化证据。\n"
                    "请用一段面向民警办案人员的自然语言，说明为什么这些案件应判定为同一团伙，"
                    "重点讲：共享了哪些账户/手机号、话术是否同源、资金链路是否有回流闭环。"
                    "不要编造证据里没有的信息，最多 120 字。\n\n证据：\n" + evidence_text
                )
                if hasattr(llm, "chat") and hasattr(llm.chat, "completions"):
                    response = await llm.chat.completions.create(
                        model=get_llm_model(),
                        messages=wrap_messages([{"role": "user", "content": prompt}]),
                        temperature=0.3,
                        max_tokens=300,
                    )
                    content = (response.choices[0].message.content or "").strip()
                    if content:
                        llm_text = content
                        source = "llm"
            except Exception as e:
                print(f"[gang_reviewer] Skill A LLM 失败，用规则降级: {e}")

        return {
            "gang_id": gang_id,
            "evidence": ev,
            "explanation": llm_text or summary,
            "source": source,
            "rule_lines": rule_lines,
        }

    async def explain_all(
        self,
        gangs: List[Dict[str, Any]],
        cases_map: Dict[Any, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return [await self.explain_gang(g, cases_map, i) for i, g in enumerate(gangs)]


# ---------------------------------------------------------------------------
# Skill B：误并案探测器
# ---------------------------------------------------------------------------
class WrongMergeDetector:
    """用已知反例复查聚类结果，标出可疑并案（对应反思闭环）。"""

    def __init__(self, llm_client=None):
        self._llm = llm_client

    def _get_llm(self):
        if self._llm is False:
            return None
        if self._llm is not None:
            return self._llm
        return get_llm_client()

    @staticmethod
    def _build_case_summaries(gang: Dict[str, Any], cases_map: Dict[Any, Dict[str, Any]]) -> List[str]:
        """给 LLM 精简的案件画像（去敏感：只给诈骗类型/话术片段/金额，不给明文卡号）。"""
        out = []
        for cid in (gang.get("case_ids") or []):
            c = cases_map.get(cid, {})
            desc = (c.get("description") or "")[:120]
            scam = c.get("scam_type") or (c.get("extracted_entities") or {}).get("scam_type") or "未知"
            amount = c.get("amount") or 0
            # 话术指纹片段（脱敏：不落明文账户号）
            fp = (c.get("fingerprint") or [])[:3]
            out.append({
                "case_id": str(cid),
                "scam_type": scam,
                "amount": amount,
                "desc_prefix": desc,
                "fingerprint": fp,
            })
        return out

    async def detect(
        self,
        gangs: List[Dict[str, Any]],
        cases_map: Dict[Any, Dict[str, Any]],
        known_distinct_pairs: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        """复查所有团伙，输出可疑并案。

        known_distinct_pairs：已知"应为不同团伙"的案件对（反例），用于校准 LLM 判断尺度。
        返回：{checked_gangs, suspicious_merges: [...], evidence_based_flags: [...], source, llm_available}
        """
        # 1) 规则级：基于证据强度标可疑（不依赖 LLM）
        suspicious = []
        for gi, gang in enumerate(gangs):
            cids = gang.get("case_ids") or []
            if len(cids) < 2:
                continue
            ev = MergeEvidenceExplainer._collect_evidence(gang, cases_map)
            has_strong = bool(ev["shared_entities"] or ev["reflux_cycles"] or ev["evidence_chain"])
            # 无任何强证据且案件话术差异大 → 规则标可疑
            if not has_strong:
                summaries = self._build_case_summaries(gang, cases_map)
                # 粗糙判据：诈骗类型互异且无共享实体 → 可能误并
                types = {s["scam_type"] for s in summaries if s["scam_type"] != "未知"}
                if len(types) >= 2:
                    suspicious.append({
                        "gang_id": gang.get("gang_id") or f"GANG_{gi:03d}",
                        "reason": "rule: 团伙内诈骗类型互异且无共享实体/资金闭环",
                        "case_ids": cids,
                    })

        # 2) LLM 增强：对全团伙做一次可解释复核
        llm = self._get_llm()
        llm_flags = []
        source = "rule"
        if llm is not None and gangs:
            try:
                payload = []
                for gi, gang in enumerate(gangs):
                    payload.append({
                        "gang_id": gang.get("gang_id") or f"GANG_{gi:03d}",
                        "cases": self._build_case_summaries(gang, cases_map),
                    })
                prompt = (
                    "你是反诈团伙误并案探测器。以下是系统聚类出的诈骗团伙。请检查是否存在「本应拆开的案件被错误并入同一团伙」的情况。\n"
                    "判断依据：话术是否同源（同诈骗剧本）、是否有共享资金账户/手机号、诈骗类型是否一致。\n"
                    "只输出 JSON 数组，元素形如 {\"gang_id\":\"GANG_000\",\"case_ids\":[\"C1\",\"C2\"],\"reason\":\"...\"}；"
                    "若全部正常输出 []。不要编造证据。\n\n团伙数据：\n" + json.dumps(payload, ensure_ascii=False, default=str)
                )
                response = await llm.chat.completions.create(
                    model=get_llm_model(),
                    messages=wrap_messages([{"role": "user", "content": prompt}]),
                    temperature=0.2,
                    max_tokens=800,
                )
                content = (response.choices[0].message.content or "").strip()
                content = content[content.find("["): content.rfind("]") + 1]
                if content:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        llm_flags = [p for p in parsed if p and p.get("case_ids")]
                        source = "llm"
            except Exception as e:
                print(f"[gang_reviewer] Skill B LLM 失败，用规则降级: {e}")

        # 合并去重（按 gang_id + case_ids）
        seen = set()
        merged = []
        for f in suspicious + llm_flags:
            key = (str(f.get("gang_id", "")), tuple(f.get("case_ids") or []))
            if key not in seen:
                seen.add(key)
                merged.append(f)

        return {
            "checked_gangs": len(gangs),
            "suspicious_merges": merged,
            "evidence_based_flags": suspicious,
            "llm_flags": llm_flags,
            "source": source,
            "llm_available": llm is not None,
            "known_distinct_pairs": known_distinct_pairs or [],
        }


# ---------------------------------------------------------------------------
# 统一入口（编排层调用）
# ---------------------------------------------------------------------------
async def review_gangs(
    gangs: List[Dict[str, Any]],
    cases_map: Dict[Any, Dict[str, Any]],
    known_distinct_pairs: Optional[List[List[str]]] = None,
    enable_llm: bool = True,
    llm_client=None,
) -> Dict[str, Any]:
    """编排层统一入口：对 gangs 依次执行 Skill A 解释 + Skill B 误并复查。

    Args:
        gangs: cluster_agent / GNN 产出的团伙列表（含 case_ids / evidence_chain 等）。
        cases_map: case_id -> case dict 的映射（skill 内部查实体用）。
        known_distinct_pairs: 已知应为不同团伙的案件对（反例，可选）。
        enable_llm: 是否尝试云端 LLM（默认开，不可用自动降级）。
        llm_client: 可选注入（测试用）。

    Returns:
        {"explanations": [...], "review": {...}, "llm_enabled": bool}
    """
    if not gangs:
        return {"explanations": [], "review": {"checked_gangs": 0, "suspicious_merges": [], "source": "rule"}, "llm_enabled": False}

    # enable_llm=False 时传 False 哨兵（而非 None），防止 _get_llm 再次拉取全局客户端
    if llm_client is not None:
        llm = llm_client
    elif enable_llm:
        llm = get_llm_client()
    else:
        llm = False

    explainer = MergeEvidenceExplainer(llm_client=llm)
    detector = WrongMergeDetector(llm_client=llm)

    explanations = await explainer.explain_all(gangs, cases_map)
    review = await detector.detect(gangs, cases_map, known_distinct_pairs)

    return {
        "explanations": explanations,
        "review": review,
        "llm_enabled": bool(llm) and llm is not False,
    }


def review_gangs_sync(
    gangs: List[Dict[str, Any]],
    cases_map: Dict[Any, Dict[str, Any]],
    known_distinct_pairs: Optional[List[List[str]]] = None,
    enable_llm: bool = True,
    llm_client=None,
) -> Dict[str, Any]:
    """同步包装：供同步编排路径（orchestrator.process / cluster_agent.run）调用。"""
    import asyncio
    coro = review_gangs(gangs, cases_map, known_distinct_pairs, enable_llm, llm_client)
    try:
        asyncio.get_running_loop()
        # 已运行的事件循环中：只能同步创建新线程跑，避免阻塞当前 loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result(timeout=120)
    except RuntimeError:
        # 无运行中的 loop（同步上下文），直接 run
        return asyncio.run(coro)
