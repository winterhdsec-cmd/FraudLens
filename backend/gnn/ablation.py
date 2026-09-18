"""
FraudLens 消融实验工具（torch-free，可离线单测，供 eval_framework 调用）。

论文实验设计要求的消融项：
- 去反思（no_reflection）：由 orchestrator 的 ENABLE_REFLECTION_LOOP 开关控制（见 agents/orchestrator.py）。
- 去置信度门控（no_gating）：由本模块 compute_gate_decision(gating_enabled=False) 控制，
  并由 evaluate_gating_ablation() 量化"有门控 vs 去门控"在冻结决策上的误冻率差异。

本文件不 import torch / numpy / 任何重型依赖，确保隔离环境可离线验证。
"""
from typing import Dict, Any, List, Optional

# 经验加权置信度门控阈值（与 gang_detector._generate_gang_info 历史取值一致）
GATE_DEFAULT = 0.5

# 冻结决策文案（与 gang_detector / routes 既有输出保持一致）
FREEZE = "建议冻结"
REVIEW = "待人工复核"


def compute_gate_decision(
    confidence: float,
    gating_enabled: bool = True,
    gate: float = GATE_DEFAULT,
) -> str:
    """经验加权置信度门控决策。

    gating_enabled=True（默认/生产）：confidence >= gate 才输出'建议冻结'，
        否则交人工复核（契合 B5：绝不模型猜测定冻卡）。
    gating_enabled=False（去门控消融 #8）：一律输出'建议冻结'（不再拦截低置信团伙），
        用于衡量门控对"误冻率"的贡献。
    """
    if not gating_enabled:
        return FREEZE
    return FREEZE if float(confidence) >= gate else REVIEW


def evaluate_gating_ablation(
    gangs: List[Dict[str, Any]],
    true_gang_ids: Any,
) -> Dict[str, Any]:
    """对比'有门控' vs '去门控'在冻结决策上的误冻率，量化门控价值。

    Args:
        gangs: 检测出的团伙列表，每项需含 'gang_id' 与 'confidence'。
        true_gang_ids: 真实存在的团伙 id 集合（真值标签），用于判定"误冻"。

    Returns:
        {
          'freeze_gated' / 'freeze_ungated': 两种模式下被建议冻结的团伙数,
          'false_freeze_gated' / 'false_freeze_ungated': 误冻（不在真值中）的团伙数,
          'false_freeze_rate_gated' / 'false_freeze_rate_ungated': 误冻率,
          'gating_reduces_false_freeze': 门控是否确实降低了误冻率,
        }
    """
    true_set = set(true_gang_ids) if true_gang_ids is not None else set()

    gated_freeze: List[Any] = []
    ungated_freeze: List[Any] = []
    for g in gangs:
        gid = g.get("gang_id")
        conf = float(g.get("confidence", 0.0))
        if compute_gate_decision(conf, gating_enabled=True) == FREEZE:
            gated_freeze.append(gid)
        ungated_freeze.append(gid)  # 去门控：全部建议冻结

    def _false_freeze(freeze_list: List[Any]):
        if not freeze_list:
            return 0, 0.0
        ff = sum(1 for gid in freeze_list if gid not in true_set)
        return ff, ff / len(freeze_list)

    ff_g, rate_g = _false_freeze(gated_freeze)
    ff_u, rate_u = _false_freeze(ungated_freeze)
    return {
        "freeze_gated": len(gated_freeze),
        "false_freeze_gated": ff_g,
        "false_freeze_rate_gated": round(rate_g, 4),
        "freeze_ungated": len(ungated_freeze),
        "false_freeze_ungated": ff_u,
        "false_freeze_rate_ungated": round(rate_u, 4),
        "gating_reduces_false_freeze": rate_g < rate_u,
    }
