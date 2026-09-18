"""agents 包（B1.3 Agent 注册表）

仅暴露 registry 单例，避免在包导入时触发重依赖或循环导入。
默认 Agent 注册在 agents/defaults.py 的 register_default_agents() 中完成，
由 Orchestrator 在 __init__ 时显式调用。
"""
from agents.registry import registry

__all__ = ["registry"]
