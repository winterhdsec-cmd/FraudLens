"""
默认 Agent 注册引导（B1.3 / B1.4）

由 Orchestrator 在 __init__ 时调用 register_default_agents() 完成默认流水线装配：
  - AnalystAgent -> stage "analyze"
  - ClusterAgent  -> stage "cluster"
  - DemoAgent     -> stage "augment"（仅当 ENABLE_DEMO_AGENT=true，B1.4 可插拔演示）

新增研判步骤只需在本函数注册，Orchestrator 文件 diff 为零（满足 B1.4）。
"""
import os

from agents.registry import registry
from agents.analyst_agent import AnalystAgent
from agents.cluster_agent import ClusterAgent


def register_default_agents() -> None:
    """注册默认研判 Agent（类注册，首次 get 惰性实例化，import 不触发 torch）。"""
    registry.register(AnalystAgent, stage="analyze")
    registry.register(ClusterAgent, stage="cluster")

    # B-L8：专科 Agent 拆分（stage="specialist"，不参与默认主链路执行）
    from agents.specialist_agents import register_specialist_agents
    register_specialist_agents()

    # 可选演示 Agent（env 开关；默认关闭，避免影响生产研判）
    if os.getenv("ENABLE_DEMO_AGENT", "false").lower() == "true":
        from agents.demo_agent import DemoAgent
        registry.register(DemoAgent, stage="augment")
