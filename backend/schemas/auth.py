"""认证相关共享契约（原 routes/deps.py 内联定义迁移而来）。"""
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ''
    role: str = 'police'
    department: str = ''
    phone: str = ''


class RefreshRequest(BaseModel):
    refresh_token: str
