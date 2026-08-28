"""
Demo Agent（B1.4，Phase B 可插拔验证）

证明：新增一个研判步骤，**无需修改 Orchestrator 主文件**，只要实现 AgentProtocol
并在注册表登记（stage="augment"），Orchestrator 的 analyze_node 会自动将其输出
合并进 analyzed_cases。

- 生产默认关闭：仅当环境变量 ENABLE_DEMO_AGENT=true 时，本模块被 agents/defaults.py
  导入并自动注册，Orchestrator 文件 diff 为 0。
- 演示逻辑（torch-free）：对每案附加一个 demo 增强标记 + 摘要，供测试断言其已生效。
"""
import os
from typing import Dict, Any

from agents.protocol import AgentProtocol
from agents.registry import registry


class DemoAgent(AgentProtocol):
    name = "demo_agent"
    stage = "augment"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """augment 阶段：在 AnalystAgent 结果上附加增量字段。"""
        case = context.get("case") or {}
        analyzed = context.get("analyzed") or {}
        case_id = case.get("case_id") or analyzed.get("case_id") or "unknown"
        scam_type = analyzed.get("scam_type") or case.get("scam_type") or "未知"
        return {
            "demo_augmented": True,
            "demo_agent": self.name,
            "demo_summary": f"[demo] case={case_id} type={scam_type}",
        }


# 生产默认关闭；仅当 env 开启时自动注册（保持默认研判不受影响）
if os.getenv("ENABLE_DEMO_AGENT", "false").lower() == "true":
    registry.register(DemoAgent, stage="augment")
