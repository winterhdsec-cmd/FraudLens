"""
敏感信息脱敏工具（G2 · 云端 LLM 脱敏网关配套）。

仅做"可逆性极低的高危字段"掩码——身份证号 / 银行卡号 / 手机号 / 邮箱，
统一**保留后 4 位**、其余打 `*`：
    - 身份证 11010519900307123X  -> **************123X
    - 银行卡  6222021234567890123 -> ****************0123
    - 手机号  13812345678        -> *******5678
    - 邮箱    zhang@corp.com    -> ***@corp.com

设计取舍（诚实说明）：
- 姓名不做正则掩码——中文姓名无可靠正则边界，误伤/漏杀都不可控；
  姓名脱敏应在业务层（如仅展示姓氏）处理，本工具不代劳。
- 本工具为纯标准库实现，不依赖任何重型依赖，可独立单测。
"""
import re

# 身份证：17 位数字 + 1 位校验（数字或 X）
# 注：用 (?<!\d)/(?!\d) 而非 \b——中文在 Python re 中属 \w，
# 数字紧贴中文时 \b 不生效，会导致漏掩码。
_ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
# 银行卡：16~19 位连续数字
_BANK_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
# 手机号：1[3-9] + 9 位数字
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# 邮箱
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _mask_tail(match: "re.Match") -> str:
    s = match.group(0)
    return "*" * (len(s) - 4) + s[-4:]


def mask_sensitive(text):
    """对单段文本做敏感字段掩码；非字符串原样返回。"""
    if not text or not isinstance(text, str):
        return text
    # 顺序：邮箱 -> 身份证 -> 银行卡 -> 手机号（避免互相误吃）
    text = _EMAIL_RE.sub(lambda m: "***@" + m.group(0).split("@")[1], text)
    text = _ID_CARD_RE.sub(_mask_tail, text)
    text = _BANK_RE.sub(_mask_tail, text)
    text = _PHONE_RE.sub(_mask_tail, text)
    return text


def mask_messages(messages):
    """对 OpenAI 风格 messages 列表做掩码，返回新列表（不修改入参）。

    支持两种 content 形态：
    - str（如 {"role": "user", "content": "..."}）
    - list（多模态，如 [{"type": "text", "text": "..."}, {"type": "image_url", ...}]）
    """
    if not isinstance(messages, list):
        return messages
    out = []
    for m in messages:
        if not isinstance(m, dict):
            out.append(m)
            continue
        content = m.get("content")
        if isinstance(content, str):
            nm = dict(m)
            nm["content"] = mask_sensitive(content)
            out.append(nm)
        elif isinstance(content, list):
            nm = dict(m)
            nm["content"] = [
                ({**p, "text": mask_sensitive(p["text"])}
                 if isinstance(p, dict) and "text" in p else p)
                for p in content
            ]
            out.append(nm)
        else:
            out.append(m)
    return out
