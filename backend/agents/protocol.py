"""
Agent 协议（B1.1，Phase B Agent 注册表）

统一所有研判智能体的输入输出契约，使 Orchestrator 流水线可声明式装配、
任意扩展而无需改动主文件（B1.3 / B1.4）。

stage 取值约定（与 Orchestrator 流水线节点对应）：
  - plan       规划阶段（当前由 Orchestrator 内部方法实现）
  - preprocess 预处理阶段（当前由 Orchestrator 内部方法实现）
  - analyze    案件分析阶段：run(context={"case": <dict>}) -> 单案分析结果 dict
  - augment    分析增强阶段：run(context={"case": <dict>, "analyzed": <dict>})
                返回增量字段，被合并进该案件的 analyzed_cases
  - cluster    团伙发现阶段：run(context={"cases": [...], "use_gnn": bool}) -> gang_result dict
  - reflect    反思阶段（当前由 Orchestrator 内部方法实现，闭环用）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AgentProtocol(ABC):
    """所有可注册 Agent 的统一协议。"""

    # 子类定义：name（唯一标识）、stage（所属阶段）
    name: str = "unnamed_agent"
    stage: str = "analyze"

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行该 agent 的单步逻辑。

        context 约定（按 stage）：
          - analyze : {"case": <案件 dict>}
          - augment : {"case": <案件 dict>, "analyzed": <已合并的分析 dict>}
          - cluster : {"cases": [<分析后案件>], "use_gnn": bool}

        返回 dict：
          - analyze/augment 阶段返回的结果会被合并进 analyzed_cases（augment 为增量合并）
          - cluster 阶段返回 gang_result（含 gangs/total_gangs/quality_score 等）
        """
        raise NotImplementedError

    def run_safe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """带容错的 run 包装：异常不中断主流水线，返回 error 结构由调用方决定是否合并。"""
        try:
            return self.run(context)
        except Exception as e:  # noqa: BLE001
            return {
                "is_error": True,
                "error": str(e),
                "agent": self.name,
                "stage": self.stage,
            }
