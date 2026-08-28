"""
止付冻结执行器（ADR-19，R-2）。

抽象接口 FreezeExecutor + Mock 实现。
真实对接反诈平台/银行时，实现具体的 executor 并在路由层注入即可（端口-适配器模式）。

设计：
  - execute(order) 接收 FreezeOrder，对每个 target_account 执行并返回 FreezeReceipt 列表
  - Mock 实现模拟成功回执，便于办案流程端到端演示
  - 真实实现需对接属地反诈平台/银行接口（非技术阻塞，待警务协调）
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any


class FreezeReceiptDTO:
    """执行回执数据传输对象（与 FreezeReceipt 模型解耦）"""
    def __init__(self, target_account: str, bank_name: str, execution_status: str,
                 execution_message: str, executed_by: str, external_ref: str,
                 freeze_until: datetime = None):
        self.target_account = target_account
        self.bank_name = bank_name
        self.execution_status = execution_status  # success/failed/partial
        self.execution_message = execution_message
        self.executed_by = executed_by
        self.external_ref = external_ref
        self.freeze_until = freeze_until

    def to_dict(self):
        return {
            'target_account': self.target_account,
            'bank_name': self.bank_name,
            'execution_status': self.execution_status,
            'execution_message': self.execution_message,
            'executed_by': self.executed_by,
            'external_ref': self.external_ref,
            'freeze_until': self.freeze_until.isoformat() if self.freeze_until else None,
        }


class FreezeExecutor:
    """止付冻结执行器抽象接口（端口）。

    真实实现示例：
        class AntiFraudPlatformExecutor(FreezeExecutor):
            def execute(self, order):
                # 调用属地反诈平台 API
                ...
    """

    def execute(self, order: Any) -> List[FreezeReceiptDTO]:
        """对工单内每个目标账户执行止付冻结，返回回执列表。

        Args:
            order: FreezeOrder 模型实例（含 target_accounts JSON）
        Returns:
            List[FreezeReceiptDTO]，每个目标账户一条回执
        """
        raise NotImplementedError


class MockFreezeExecutor(FreezeExecutor):
    """Mock 实现：模拟止付冻结执行成功，生成回执。

    用于办案流程端到端演示与测试。真实对接待警务协调后替换为真实 executor。
    冻结期限默认 6 个月（符合《公安机关办理刑事案件程序规定》冻结期限）。
    """

    EXECUTOR_NAME = "mock_channel"
    FREEZE_DURATION_DAYS = 180  # 6 个月

    def execute(self, order: Any) -> List[FreezeReceiptDTO]:
        receipts = []
        targets = order.target_accounts or []
        if isinstance(targets, str):
            # 兼容旧格式
            targets = [{"account": targets, "bank": "", "holder": ""}]

        for t in targets:
            account = t.get("account", "") if isinstance(t, dict) else str(t)
            bank = t.get("bank", "") if isinstance(t, dict) else ""
            if not account:
                continue
            # Mock：所有账户模拟执行成功
            external_ref = f"MOCK-{order.order_id}-{account[-4:]}"
            receipts.append(FreezeReceiptDTO(
                target_account=account,
                bank_name=bank,
                execution_status="success",
                execution_message=f"Mock 执行成功：账户 {account} 已冻结（模拟）",
                executed_by=self.EXECUTOR_NAME,
                external_ref=external_ref,
                freeze_until=datetime.utcnow() + timedelta(days=self.FREEZE_DURATION_DAYS),
            ))
        return receipts


# ── 工厂：根据配置选择 executor ──
_executor_instance = None


def get_freeze_executor() -> FreezeExecutor:
    """获取止付冻结执行器（单例）。

    配置 FREEZE_EXECUTOR=mock（默认）/antifraud_platform/<custom>。
    真实 executor 通过实现 FreezeExecutor 并在此注册。
    """
    global _executor_instance
    if _executor_instance is not None:
        return _executor_instance
    import os
    executor_type = os.getenv("FREEZE_EXECUTOR", "mock").lower()
    if executor_type == "mock" or executor_type == "":
        _executor_instance = MockFreezeExecutor()
    else:
        # 默认回退 Mock（真实 executor 待对接）
        _executor_instance = MockFreezeExecutor()
    return _executor_instance
