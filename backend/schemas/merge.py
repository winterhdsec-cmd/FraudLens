"""案件合并共享契约（原 routes/deps.py 内联定义迁移而来）。"""
from pydantic import BaseModel


class MergeConfirmRequest(BaseModel):
    case_id_a: str
    case_id_b: str
    gang_id: str
