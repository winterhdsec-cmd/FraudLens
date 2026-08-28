"""管理面共享契约（原 routes/system.py 内联定义迁移而来）。"""
from typing import Optional
from pydantic import BaseModel


class APIKeyUpdateRequest(BaseModel):
    """API Key 更新请求（管理面）。"""
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
