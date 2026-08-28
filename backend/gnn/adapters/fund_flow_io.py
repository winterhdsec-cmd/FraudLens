"""资金流水（fund flow）导入/转换工具。

把 AMLSim 输出目录或银行 CSV/Excel 流水，结构化为主链路消费的
accounts_tx 列表（每条 {from_account, to_account, amount, timestamp}），
供 /agent-analyze 的资金链图构建与回流闭环检测消费。

设计纪律（与 docs/14 / docs/06 一致）：
- 列名容错：支持 SENDER/RECEIVER、FROM/TO、SRC/DST、AMOUNT/VALUE、TIMESTAMP/TIME/DATE
  以及中文别名（付款账号/收款账号/金额/交易时间 等）。
- 不编造：缺发送/接收账户关键列时明确报错，不静默丢弃行。
- 不出域：纯本地解析，无外部依赖；Excel 走可选 openpyxl，缺失时明确提示改用 CSV。
"""
import csv
import io
from typing import Any, Dict, List, Tuple


# 列名容错（含中文别名，便于一线民警直接上传银行导出的中文表头流水）
_SENDER_VARIANTS = (
    "SENDER_ACCOUNT_ID", "SENDER_ACCOUNT", "SENDER", "FROM_ACCOUNT", "FROM_ACCT",
    "FROM", "SRC_ACCOUNT", "SRC", "PAYER_ACCOUNT", "付款账号", "转出账号", "付款方账号",
)
_RECEIVER_VARIANTS = (
    "RECEIVER_ACCOUNT_ID", "RECEIVER_ACCOUNT", "RECEIVER", "TO_ACCOUNT", "TO_ACCT",
    "TO", "DST_ACCOUNT", "DST", "PAYEE_ACCOUNT", "收款账号", "转入账号", "收款方账号",
)
_AMOUNT_VARIANTS = ("AMOUNT", "TX_AMOUNT", "VALUE", "金额", "交易金额", "转账金额")
_TIME_VARIANTS = ("TIMESTAMP", "TIME", "DATE", "TX_TIME", "交易时间", "时间", "交易日期")
_ACCOUNT_VARIANTS = ("ACCOUNT_ID", "ACCOUNT", "ID", "账号")


def _resolve(columns, variants):
    """在列名中解析目标列（大小写不敏感兜底）。"""
    for v in variants:
        if v in columns:
            return v
    lower = {str(c).upper(): c for c in columns}
    for v in variants:
        if v.upper() in lower:
            return lower[v.upper()]
    return None


def _to_float(x):
    try:
        return float(str(x).replace(",", "").replace("¥", "").replace("￥", "").strip())
    except Exception:
        return 0.0


def _to_str(x):
    return str(x).strip() if x is not None else ""


def _build_from_rows(header, rows) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    c_s = _resolve(header, _SENDER_VARIANTS)
    c_r = _resolve(header, _RECEIVER_VARIANTS)
    c_a = _resolve(header, _AMOUNT_VARIANTS)
    c_t = _resolve(header, _TIME_VARIANTS)
    if not (c_s and c_r):
        raise ValueError(
            f"流水文件缺少发送/接收账户列（已有列: {list(header)}）；"
            f"需含类似 SENDER_ACCOUNT_ID / RECEIVER_ACCOUNT_ID 或 付款账号 / 收款账号"
        )
    s_idx, r_idx = header.index(c_s), header.index(c_r)
    a_idx = header.index(c_a) if c_a else None
    t_idx = header.index(c_t) if c_t else None

    accounts_tx: List[Dict[str, Any]] = []
    accounts = set()
    amts = []
    for row in rows:
        if len(row) <= max(s_idx, r_idx):
            continue
        s = _to_str(row[s_idx])
        d = _to_str(row[r_idx])
        if not s or not d:
            continue
        amt = _to_float(row[a_idx]) if a_idx is not None else 0.0
        t = _to_str(row[t_idx]) if t_idx is not None else ""
        accounts_tx.append({"from_account": s, "to_account": d, "amount": amt, "timestamp": t})
        accounts.add(s)
        accounts.add(d)
        if amt:
            amts.append(amt)
    stats = {
        "n_transactions": len(accounts_tx),
        "n_accounts": len(accounts),
        "amount_min": min(amts) if amts else 0.0,
        "amount_max": max(amts) if amts else 0.0,
    }
    return accounts_tx, stats


def parse_fund_flow_csv(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    reader = csv.reader(io.StringIO(text))
    all_rows = [r for r in reader if r]
    if not all_rows:
        return [], {"error": "空文件"}
    header = [c.strip() for c in all_rows[0]]
    return _build_from_rows(header, all_rows[1:])


def parse_fund_flow_file(filename: str, content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """按扩展名选择解析器。CSV/TXT 直接解析；XLSX 尝试 openpyxl（可选依赖）。"""
    ext = (filename or "").lower().split(".")[-1]
    if ext in ("csv", "txt"):
        text = content.decode("utf-8-sig", errors="ignore")
        return parse_fund_flow_csv(text)
    if ext in ("xlsx", "xlsm", "xls"):
        try:
            import openpyxl
        except Exception:
            raise ValueError("解析 Excel 需 openpyxl（pip install openpyxl）；建议导出为 CSV 后上传")
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            if row is None:
                continue
            rows.append([("" if v is None else str(v)) for v in row])
        if not rows:
            return [], {"error": "空文件"}
        header = [c.strip() for c in rows[0]]
        return _build_from_rows(header, rows[1:])
    raise ValueError(f"不支持的流水文件格式: .{ext}（支持 csv/txt/xlsx）")


def amlsim_to_accounts_tx(directory: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """把 AMLSim 输出目录转换为 accounts_tx 列表（供主链路 fund_flow 消费）。

    复用 adapters.amlsim_adapter.load_amlsim 的 edges（src,dst,amount,timestamp），
    映射为 {from_account,to_account,amount,timestamp}。
    """
    from .amlsim_adapter import load_amlsim

    account_ids, edges, gt = load_amlsim(directory)
    accounts_tx = [
        {"from_account": s, "to_account": d, "amount": amt, "timestamp": t}
        for (s, d, amt, t) in edges
    ]
    rings = {v for v in gt.values() if isinstance(v, int) and v >= 0}
    stats = {
        "n_transactions": len(accounts_tx),
        "n_accounts": len(account_ids),
        "n_ground_truth_rings": len(rings),
        "source": "amlsim",
    }
    return accounts_tx, stats
