"""案卷材料（docx / pdf / 图片 OCR / 纯文本）→ 结构化 cases 适配器。

补齐 docs/14 的 B-L6 缺口 4.1：把 OCR / 文本 / 文档转化为系统主链路可消费的 cases 列表，
使民警可直接将真实案卷材料喂入研判（经 /agent-analyze 的 cases 字段）。

设计纪律（与 docs/14 / docs/06 一致）：
- 零出域：默认仅本地正则 + 文档标注行解析，不调 LLM；敏感明文不出域。
- 不伪造：脱敏账户（如 6222****1234）如实保留，绝不把掩码 * 补全为数字。
- 诚实边界：本模块是「材料接入 / 结构化」管道，不构成真实警务数据验证通过；
  输出 cases 的 source 固定标注 "extracted_from_document"，下游需结合真实研判。
"""
import io
import re
from typing import Any, Dict, List, Optional

from tools.evidence_tools import extract_entities_regex


# ── 4.3 鲁棒性补强：现有正则覆盖不到的真实脏数据写法 ──
# 脱敏账户：6222****1234 / 6214****8888（中间以 * 或 ·/… 掩码）
_MASKED_ACCOUNT_RE = re.compile(r'(?<!\d)(\d{4})[\*\u2026\u00b7\u30fb\-]+(\d{4})(?!\d)')
# 金额无"元"字：¥200,000（符号在前）/ 200,000¥（符号在后）/ ￥158000
_AMOUNT_NO_YUAN_RE = re.compile(
    r'(?:RMB|￥|¥)\s*(?P<a>\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\s*(?:RMB|￥|¥)?'
    r'|(?P<b>\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\s*(?:RMB|￥|¥)',
    re.IGNORECASE)
# 文档自带的结构化标注行（比 LLM 更可靠、零出域）
_STRUCT_FIELD_RE = {
    "scam_type": re.compile(r'(?:诈骗类型|案件类型|案由|诈骗手法类别)[:：|｜\s]*\s*(.+)', re.IGNORECASE),
    "victim_name": re.compile(r'(?:报案人|受害人|被害人|事主|报案人姓名)[:：|｜\s]*\s*([^\s,，。;；]+)'),
    "victim_phone": re.compile(r'(?:联系电话|手机|报案人电话|受害人电话|电话)[:：|｜\s]*\s*(\d[\d\s\-]{6,})'),
    "amount_value": re.compile(
        r'(?:涉案金额|损失金额|被骗金额|诈骗金额|涉案资金|转账总额)[:：|｜\s]*\s*(?:¥|￥|RMB)?\s*([\d,]+(?:\.\d{1,2})?)',
        re.IGNORECASE),
}
# 多案切分标题（案件一/二/三、案一/二/三、第一/二/三起）
_MULTI_CASE_RE = re.compile(
    r'(?:案件[一二三四五六七八九十\d]+|案[一二三四五六七八九十\d]+|第[一二三四五六七八九十\d]+起)[：: ]')
# 单个案件标题（用于提取 title）
_CASE_TITLE_RE = re.compile(r'(?:案件[一二三四五六七八九十\d]+|案[一二三四五六七八九十\d]+)[：: ]*\s*(.+)')
# 嫌疑人 / 开户人（简易提取，避免与受害人混淆）
_PERP_RE = re.compile(r'(?:开户人|户名|嫌疑人|涉案人)[：:]\s*([^\s,，。;；（(]+)')


def _dedupe(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def split_multi_cases(text: str) -> List[str]:
    """按『案件一/二/三』等标题切分多案；无多案标记则整体作为单案。"""
    if not text or not text.strip():
        return []
    matches = list(_MULTI_CASE_RE.finditer(text))
    if len(matches) <= 1:
        return [text.strip()]
    segments = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        line_start = text.rfind("\n", 0, start) + 1
        seg = text[line_start:end].strip()
        if seg:
            segments.append(seg)
    return segments


def extract_structured_fields(text: str) -> Dict[str, Any]:
    """从文档标注行提取 scam_type / victim_name / victim_phone / amount_value。"""
    fields = {"scam_type": "未知", "victim_name": "", "victim_phone": "", "amount_value": None}
    for key, rx in _STRUCT_FIELD_RE.items():
        m = rx.search(text)
        if not m:
            continue
        val = m.group(1).strip().strip("，。；;,")
        if key == "amount_value":
            try:
                fields[key] = float(val.replace(",", ""))
            except Exception:
                fields[key] = None
        else:
            fields[key] = val
    return fields


def extract_entities_robust(text: str) -> Dict[str, Any]:
    """B-L1 本地正则打底 + 4.3 补强（脱敏账户 / 无『元』金额）。返回统一格式。"""
    ents = extract_entities_regex(text)
    # 补脱敏账户（6222****1234）
    masked = set()
    for m in _MASKED_ACCOUNT_RE.finditer(text):
        masked.add(m.group(1) + "****" + m.group(2))
    if masked:
        ents["bank_accounts"] = _dedupe(list(ents.get("bank_accounts", [])) + list(masked))
    # 补无"元"金额（¥200,000）
    amts = list(ents.get("amounts", []))
    for m in _AMOUNT_NO_YUAN_RE.finditer(text):
        raw = re.sub(r'(?i)(RMB|￥|¥)', '', m.group(0)).replace(" ", "").strip()
        num = re.sub(r'[^\d.]', '', raw)
        if num:
            amt = f"{float(num):.2f}"
            if amt not in amts:
                amts.append(amt)
    if amts:
        ents["amounts"] = amts
    # 保序去重
    for k, v in list(ents.items()):
        if isinstance(v, list):
            ents[k] = _dedupe(v)
    return ents


def extract_perpetrators(text: str) -> List[Dict[str, str]]:
    """从『开户人：王强』等标注行提取嫌疑人（简易，零出域）。"""
    names = []
    for m in _PERP_RE.finditer(text):
        n = m.group(1).strip()
        if n and n not in names:
            names.append(n)
    return [{"name": n} for n in names]


# ── B-L11 数据血缘（2026-08-04）────────────────────────────────────── #
import uuid as _uuid
from datetime import datetime as _dt


def make_lineage(kind: str = "extracted_from_document", generator_version: str = "1.0",
                 extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """构造数据血缘头（B-L11）。

    Args:
        kind: 数据来源种类（synthetic / public_corpus / real_desensitized /
               extracted_from_document）
        generator_version: 生成器版本
        extra: 附加字段（如 schema_version / parser 等）
    """
    lineage = {
        "kind": kind,
        "generator_version": generator_version,
        "generated_at": _dt.utcnow().isoformat() + "Z",
        "lineage_id": _uuid.uuid4().hex[:12],
        "schema_version": "1.0",
    }
    if extra:
        lineage.update(extra)
    return lineage


def parse_case_document(text: str, lineage: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """把案卷材料文本转化为 cases 列表（主链路可消费）。

    返回每个 case：
      case_id / title / description（原始案情文本，analyst 抽实体源）/
      scam_type / victim_name / victim_phone / amount_value /
      extracted_entities（统一格式，供 cluster 关联）/ accounts / perpetrators / source。
    B-L11：source 扩展为结构化血缘（kind/generator_version/generated_at/schema_version）。
    """
    if not text or not text.strip():
        return []
    segments = split_multi_cases(text)
    # 文档级结构化候选：单案时表格常置于文末，段内无字段则用文档级候选补齐
    doc_fields = extract_structured_fields(text)
    cases = []
    for idx, seg in enumerate(segments, 1):
        structured = extract_structured_fields(seg)
        if len(segments) == 1:
            for k in ("victim_name", "victim_phone", "amount_value"):
                if not structured.get(k) and doc_fields.get(k):
                    structured[k] = doc_fields[k]
        entities = extract_entities_robust(seg)
        perps = extract_perpetrators(seg)
        title_m = _CASE_TITLE_RE.search(seg)
        title = title_m.group(1).strip() if title_m else (seg.split("\n")[0][:40] if seg else f"案件{idx}")
        accounts = [{"account_number": acct, "owner": ""}
                   for acct in entities.get("bank_accounts", [])]
        cases.append({
            "case_id": f"doc_case_{idx:03d}",
            "title": title,
            "description": seg,
            "scam_type": structured.get("scam_type", "未知"),
            "victim_name": structured.get("victim_name", ""),
            "victim_phone": structured.get("victim_phone", ""),
            "amount_value": structured.get("amount_value"),
            "extracted_entities": entities,
            "accounts": accounts,
            "perpetrators": perps,
            # B-L11：source 从字符串升级为结构化血缘对象（向后兼容：dict 或旧 str 均可）
            "source": lineage or make_lineage("extracted_from_document", extra={"parser": "case_document_io"}),
            "parse_note": "结构化字段取自文档标注行；实体取自本地正则抽取（零出域）；脱敏账户如实保留，未补全",
        })
    return cases


def extract_docx_in_order(content: bytes) -> str:
    """保持文档流顺序提取 docx（段落与表格交错），使表格归属其所在案件段。

    与 files._extract_docx（先段落、后表格、表格脱离上下文）不同，本函数按 body 子元素
    真实顺序遍历，使『案件一的报案人表格』正确落在案件一段内，便于结构化字段提取。
    """
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(io.BytesIO(content))
    parts = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn('w:p'):
            p = Paragraph(child, doc)
            if p.text.strip():
                parts.append(p.text)
        elif child.tag == qn('w:tbl'):
            tbl = Table(child, doc)
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells]
                parts.append(' | '.join(cells))
    return '\n'.join(parts)
