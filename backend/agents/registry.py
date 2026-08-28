"""
Agent 注册表（B1.2，Phase B Agent 注册表）

提供 AgentRegistry 单例：register / get / list / agents_for_stage / pipeline。
- 支持注册「实例」或「类」；类在首次 get 时惰性实例化（避免包导入即触发重依赖，如 torch）。
- 按 stage 分组，保持注册顺序（声明式流水线的执行顺序 = 注册顺序）。
- 默认导出单例 `registry`，供 Orchestrator 与各 Agent 模块共享。

设计要点（与 docs/07 §3.5 对齐）：
  - Orchestrator 的主流程不 hardcode analyst/cluster，而是从 registry 读取；
  - 新增研判步骤（如 B1.4 DemoAgent）只需在 agents/__init__ 注册，Orchestrator 文件 diff 为零。
"""
from typing import Dict, Any, List, Optional, Type, Union

from agents.protocol import AgentProtocol


class AgentRegistry:
    """Agent 注册表单例。"""

    _instance: Optional["AgentRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._agents: Dict[str, Dict[str, Any]] = {}   # name -> {cls, instance, stage}
            inst._order: List[str] = []                    # 注册顺序
            inst._stages: Dict[str, List[str]] = {}        # stage -> [names]
            cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------ #
    # 注册
    # ------------------------------------------------------------------ #
    def register(
        self,
        agent: Union[AgentProtocol, Type[AgentProtocol]],
        stage: Optional[str] = None,
        name: Optional[str] = None,
    ) -> "AgentRegistry":
        """注册一个 agent（实例或类）。重复注册同名会覆盖。"""
        if isinstance(agent, type):
            agent_cls = agent
            agent_name = name or getattr(agent_cls, "name", agent_cls.__name__)
            entry = {"cls": agent_cls, "instance": None,
                     "stage": stage or getattr(agent_cls, "stage", "analyze")}
        else:
            agent_name = name or getattr(agent, "name", type(agent).__name__)
            entry = {"cls": type(agent), "instance": agent,
                     "stage": stage or getattr(agent, "stage", "analyze")}

        self._agents[agent_name] = entry
        if agent_name not in self._order:
            self._order.append(agent_name)

        st = entry["stage"]
        self._stages.setdefault(st, [])
        if agent_name not in self._stages[st]:
            self._stages[st].append(agent_name)
        return self

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get(self, name: str) -> Optional[AgentProtocol]:
        """按名取 agent 实例（类则惰性实例化）。"""
        entry = self._agents.get(name)
        if not entry:
            return None
        if entry["instance"] is None:
            entry["instance"] = entry["cls"]()
        return entry["instance"]

    def list(self) -> List[str]:
        """返回所有已注册 agent 名称（按注册顺序）。"""
        return list(self._order)

    def agents_for_stage(self, stage: str) -> List[AgentProtocol]:
        """返回某阶段下所有 agent 实例（按注册顺序）。"""
        names = self._stages.get(stage, [])
        return [self.get(n) for n in names]

    def pipeline(self, stages: Optional[List[str]] = None) -> Dict[str, List[AgentProtocol]]:
        """返回 {stage: [agents]} 的声明式流水线（仅含非空阶段）。"""
        stages = stages or ["plan", "preprocess", "analyze", "cluster", "augment", "reflect"]
        return {s: self.agents_for_stage(s) for s in stages if self.agents_for_stage(s)}

    def reset(self) -> None:
        """清空注册表（测试用）。"""
        self._agents = {}
        self._order = []
        self._stages = {}


# 默认单例
registry = AgentRegistry()
