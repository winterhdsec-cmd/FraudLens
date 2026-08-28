"""
FraudLens 共享接口契约包（T3 / docs/13 G17）。

统一沉淀各路由共用的 Pydantic 请求/响应模型，消除 routes 内各自定义 model 的
重复与漂移。所有模型定义集中于此，路由文件仅做 `from schemas.xxx import ...`，
类名与字段保持向后兼容（端点签名不变）。

模块划分：
  - auth.py     登录/注册/刷新令牌
  - analysis.py 研判请求 / GNN 团伙发现请求
  - chat.py     AI 对话请求/响应/会话信息
  - merge.py    案件合并确认
  - admin.py    管理面（API Key 更新等）
"""
from .auth import LoginRequest, RegisterRequest, RefreshRequest
from .analysis import AnalyzeRequest, GNNDetectRequest
from .chat import ChatRequest, ChatResponse, SessionInfo
from .merge import MergeConfirmRequest
from .admin import APIKeyUpdateRequest

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "RefreshRequest",
    "AnalyzeRequest",
    "GNNDetectRequest",
    "ChatRequest",
    "ChatResponse",
    "SessionInfo",
    "MergeConfirmRequest",
    "APIKeyUpdateRequest",
]
