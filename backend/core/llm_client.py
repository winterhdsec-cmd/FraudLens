"""
云端 LLM 统一网关（G2 · 云端 LLM 脱敏网关）。

设计目标（对应 docs/13 G2）：
- **单一出口**：所有云端 LLM 客户端（DeepSeek 等）必须经 `get_llm_client()` 创建，
  禁止在 agent/路由里 `AsyncOpenAI(...)` 散落直连。
- **默认关闭、数据不出域**：`DISABLE_CLOUD_LLM` 默认 `1`（关闭）。代码安全默认即"不出域"；
  运行时由 `docker-compose.yml` 以 `${DISABLE_CLOUD_LLM:-0}` 覆盖，保证当前演示可用。
  真正的安全部署不覆盖该变量即自动关闭公网 LLM。
- **启用时强制脱敏**：`CLOUD_LLM_MASK` 默认 `1`；调用方用 `mask_messages()` 包裹出向 prompt，
  确保不含明文身份证/银行卡/手机号/邮箱（见 `tools/mask.py`）。

注意：本模块只负责"客户端创建 + 开关 + 脱敏包裹"，不负责具体调用。
调用方在拿到 client 后、发起 `chat.completions.create` 前，应先 `mask_messages(...)`。
"""
import os
from typing import Optional, List, Any, Dict

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:  # 评测等无 openai 的精简环境
    AsyncOpenAI = None
    OpenAI = None

from tools.mask import mask_sensitive, mask_messages  # noqa: F401  (mask_sensitive 供直接调用)


def cloud_llm_enabled() -> bool:
    """云端 LLM 是否启用（默认关闭，对应数据不出域默认）。"""
    return os.getenv("DISABLE_CLOUD_LLM", "1") != "1"


def cloud_llm_mask_enabled() -> bool:
    """启用时是否对出向 prompt 脱敏（默认开启）。"""
    return os.getenv("CLOUD_LLM_MASK", "1") != "0"


def get_llm_model() -> str:
    """统一的模型名出口。

    历史坑：agents 里 9 处写死 model="deepseek-chat"，导致把 LLM 切到
    阿里云 DashScope（key.env: DEEPSEEK_BASE_URL/MODEL=qwen3.8-flash）后，
    仍向新端点请求 deepseek-chat → 404 model_not_found → 问答/分析/复核
    全部静默降级成兜底话术。所有 LLM 调用必须经这里取模型名，禁止再写死。
    """
    try:
        from core.config import settings

        name = (getattr(settings, "DEEPSEEK_MODEL", "") or "").strip()
        if name:
            return name
    except Exception:
        pass
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"


def get_llm_client(sync: bool = False):
    """返回云端 LLM 客户端；关闭或未配置密钥时返回 None（调用方须降级处理）。

    sync=False -> AsyncOpenAI（agent/异步路径）；sync=True -> OpenAI（文件/OCR 同步路径）。
    """
    if not cloud_llm_enabled():
        return None
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    if sync:
        if OpenAI is None:
            return None
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            timeout=60,
        )
    if AsyncOpenAI is None:
        return None
    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        timeout=60,
    )


def wrap_messages(messages):
    """启用脱敏时包裹 messages；关闭时原样返回。供调用方一行接入。"""
    if cloud_llm_mask_enabled():
        return mask_messages(messages)
    return messages
