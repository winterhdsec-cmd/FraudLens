"""
复盘六动作闭环 Agent（B-L9，2026-08-04）

对标中正智云"复盘六动作"方法论（触发→串链→归因→交办→复验→关闭，
"一错一因一改一验"），把教学/业务"评"从一次性打分升级为可追溯的复盘闭环：
  1. trigger  触发：研判结果与真值标签不一致（或质量分低于阈值）时启动复盘
  2. chain    串链：研判结果与真值按 case_id 同一编号对齐
  3. attribute 归因：差异落在哪个环节（抽取/聚类/门控），基于字段级 diff
  4. assign   交办：提示补哪块知识 / 哪个环节复查 / 调哪个参数
  5. reverify 复验：给类似案例重跑（或记录"待复验"状态）
  6. close    关闭：结论 + 记录（落审计 / 返回给调用方）

设计纪律：
  - 零外部依赖（纯 Python + typing），任何环境可 import。
  - 归因采用启发式规则（与 B-L13 异常卡同风格）：实体缺失→抽取环节、
    团伙划分不同→聚类环节、置信度不足→门控环节；不引入新算法依赖。
  - 输出 `review_chain` dict，挂到 FeedbackSlip（B-L7 反馈单）返回。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ReflectAgent:
    """复盘六动作闭环。"""

    name = "reflect"
    stage = "reflect"

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行复盘闭环。

        context 约定：
          {
            "analyzed_cases": [<分析后案件 dict>],   # 研判结果（含 extracted_entities）
            "gang_result":    {"gangs": [...], ...}, # 团伙聚类结果
            "ground_truth":   {                      # 真值标签（可选，教学评测用）
                "entities": {case_id: {entity_type: [values]}},
                "gangs":    [{"case_ids": [...]}, ...],
            },
            "quality_score": 0.9154,                 # 总体质量分（可选）
          }

        返回：
          {"review_chain": {trigger, chain, attribute, assign, reverify, close}}
        """
        analyzed = context.get("analyzed_cases", [])
        gang_result = context.get("gang_result", {})
        ground_truth = context.get("ground_truth") or {}
        quality_score = context.get("quality_score", 0.0)

        review = self._build_review_chain(
            analyzed_cases=analyzed,
            gang_result=gang_result,
            ground_truth=ground_truth,
            quality_score=quality_score,
        )
        return {"review_chain": review}

    # ------------------------------------------------------------------ #
    # 六动作
    # ------------------------------------------------------------------ #
    def _build_review_chain(
        self,
        analyzed_cases: List[Dict[str, Any]],
        gang_result: Dict[str, Any],
        ground_truth: Dict[str, Any],
        quality_score: float,
    ) -> Dict[str, Any]:
        # 1. trigger：是否触发复盘
        trigger_reason = self._trigger(analyzed_cases, gang_result, ground_truth, quality_score)
        if trigger_reason is None:
            return {
                "triggered": False,
                "trigger_reason": None,
                "chain": [],
                "attribute": None,
                "assign": None,
                "reverify": None,
                "close": {
                    "status": "passed",
                    "conclusion": "研判结果与真值一致或质量达标，无需复盘",
                    "recorded_at": datetime.utcnow().isoformat() + "Z",
                },
            }

        # 2. chain：串链对齐（研判 vs 真值）
        chain = self._chain(analyzed_cases, gang_result, ground_truth)

        # 3. attribute：归因
        attribute = self._attribute(chain, gang_result, ground_truth)

        # 4. assign：交办
        assign = self._assign(attribute)

        # 5. reverify：复验
        reverify = self._reverify(attribute, gang_result, ground_truth)

        # 6. close：关闭
        close = self._close(attribute, reverify)

        return {
            "triggered": True,
            "trigger_reason": trigger_reason,
            "chain": chain,
            "attribute": attribute,
            "assign": assign,
            "reverify": reverify,
            "close": close,
        }

    # -- 1. trigger ----------------------------------------------------- #
    def _trigger(
        self,
        analyzed_cases: List[Dict[str, Any]],
        gang_result: Dict[str, Any],
        ground_truth: Dict[str, Any],
        quality_score: float,
    ) -> Optional[str]:
        """触发条件：① 有真值且不一致；② 无真值时质量分低。"""
        if ground_truth:
            pred_gangs = self._pred_gang_map(gang_result)
            gold_gangs = self._gold_gang_map(ground_truth)
            if pred_gangs != gold_gangs:
                return "研判结果与真值团伙划分不一致"
            gt_entities = ground_truth.get("entities") or {}
            for cid, gt in gt_entities.items():
                pred = self._find_case_entities(analyzed_cases, cid)
                for t, vals in gt.items():
                    if set(vals or []) - set(pred.get(t, []) or []):
                        return f"案件 {cid} 实体抽取缺失（{t}）"
            return None
        if quality_score < 0.6:
            return f"质量分偏低（{quality_score:.3f} < 0.6）"
        return None

    # -- 2. chain ------------------------------------------------------- #
    def _chain(
        self,
        analyzed_cases: List[Dict[str, Any]],
        gang_result: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """串链：按 case_id 对齐研判与真值，列出每条差异。"""
        rows: List[Dict[str, Any]] = []

        # 实体层 diff
        gt_entities = (ground_truth or {}).get("entities") or {}
        for cid, gt in gt_entities.items():
            pred = self._find_case_entities(analyzed_cases, cid)
            for t, vals in gt.items():
                miss = sorted(set(vals or []) - set(pred.get(t, []) or []))
                if miss:
                    rows.append({
                        "level": "entity",
                        "case_id": cid,
                        "type": t,
                        "pred": sorted(pred.get(t, []) or []),
                        "gold": sorted(vals or []),
                        "missing": miss,
                    })

        # 团伙层 diff
        pred_map = self._pred_gang_map(gang_result)
        gold_map = self._gold_gang_map(ground_truth)
        all_cids = sorted(set(pred_map) | set(gold_map))
        for cid in all_cids:
            p = pred_map.get(cid, -1)
            g = gold_map.get(cid, -2)
            if p != g:
                rows.append({
                    "level": "gang",
                    "case_id": cid,
                    "pred_gang": p,
                    "gold_gang": g,
                })
        return rows

    # -- 3. attribute --------------------------------------------------- #
    def _attribute(
        self,
        chain: List[Dict[str, Any]],
        gang_result: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """归因：差异落在哪个环节（抽取/聚类/门控）。"""
        entity_diffs = [r for r in chain if r["level"] == "entity"]
        gang_diffs = [r for r in chain if r["level"] == "gang"]

        if entity_diffs:
            missing_types = sorted({r["type"] for r in entity_diffs})
            return {
                "stage": "entity_extraction",
                "stage_cn": "实体抽取环节",
                "reason": f"{len(entity_diffs)} 处实体缺失/不一致（{', '.join(missing_types)}）",
                "detail": entity_diffs[:5],
            }
        if gang_diffs:
            return {
                "stage": "clustering",
                "stage_cn": "团伙聚类环节",
                "reason": f"{len(gang_diffs)} 起案件团伙归属与真值不一致",
                "detail": gang_diffs[:5],
            }
        # 无真值或全一致 → 门控（置信度）
        return {
            "stage": "gating",
            "stage_cn": "置信度门控环节",
            "reason": "研判一致但置信度未达阈值，需人工复核",
            "detail": [],
        }

    # -- 4. assign ------------------------------------------------------ #
    def _assign(self, attribute: Dict[str, Any]) -> List[Dict[str, Any]]:
        """交办：按归因环节给具体改进建议（可执行）。"""
        stage = attribute.get("stage")
        if stage == "entity_extraction":
            return [
                {"task": "补全实体抽取规则", "action": "检查 extract_entities_regex 对全角数字/括号/换行的覆盖，或启用 LLM 语义补全（B-L1）"},
                {"task": "复核原始材料", "action": "回到案卷/报案文本核对被漏实体（重点：账户/手机号/微信/QQ）"},
            ]
        if stage == "clustering":
            return [
                {"task": "复查聚类参数", "action": "检查共享实体关联阈值与 GNN 元路径权重，或改用实体关联聚类优先（B-L2）"},
                {"task": "人工串并核对", "action": "对归因到聚类的案件做人工串并案复核（对齐 Lab2 人机对比）"},
            ]
        return [
            {"task": "复核置信度门控", "action": "检查四因子加权（规模/金额/账户数/回流标志），必要时调阈值（B-L13）"},
            {"task": "人工冻卡复核", "action": "冻卡决策交人工审批，标注置信度与依据（对齐 Lab3 伦理权衡）"},
        ]

    # -- 5. reverify ---------------------------------------------------- #
    def _reverify(
        self,
        attribute: Dict[str, Any],
        gang_result: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> Dict[str, Any]:
        """复验：记录"待复验"状态（教学 Lab4 中学生可重跑类似案例验证改进）。"""
        stage = attribute.get("stage")
        return {
            "status": "pending",
            "plan": f"应用{attribute.get('stage_cn','')}改进后，用同类案例重跑研判并对比结果",
            "next_case_hint": (
                "补一个与本次失败同构的案例（如同类话术/同结构资金链）验证改进是否生效"
                if ground_truth else "构造最小闭环（2-3 案）复验改进前后差异"
            ),
        }

    # -- 6. close ------------------------------------------------------- #
    def _close(self, attribute: Dict[str, Any], reverify: Dict[str, Any]) -> Dict[str, Any]:
        """关闭：结论 + 记录。"""
        return {
            "status": "open_for_reverify",
            "conclusion": (
                f"归因：{attribute.get('stage_cn','未知环节')}（{attribute.get('reason','')}）；"
                f"复验：{reverify.get('plan','')}"
            ),
            "recorded_at": datetime.utcnow().isoformat() + "Z",
            "audit_note": "复盘记录应落审计（OperationLog），供教学/复盘追溯",
        }

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_case_entities(analyzed_cases: List[Dict[str, Any]], case_id: str) -> Dict[str, Any]:
        for c in analyzed_cases:
            if c.get("case_id") == case_id:
                return c.get("extracted_entities", {}) or {}
        return {}

    @staticmethod
    def _pred_gang_map(gang_result: Dict[str, Any]) -> Dict[str, int]:
        m: Dict[str, int] = {}
        for gi, g in enumerate(gang_result.get("gangs", [])):
            for cid in g.get("case_ids", []):
                m[cid] = gi
        return m

    @staticmethod
    def _gold_gang_map(ground_truth: Dict[str, Any]) -> Dict[str, int]:
        m: Dict[str, int] = {}
        for gi, g in enumerate((ground_truth or {}).get("gangs", []) or []):
            for cid in g.get("case_ids", []):
                m[cid] = gi
        return m
