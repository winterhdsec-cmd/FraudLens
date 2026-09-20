"""空表数据填充 - 脱敏演示数据种子（G4 数据饱满化）

背景
----
复赛演示时 9 张表为空，导致前端多处页面显示"暂无数据"：
  accounts / persons / phones         → 团伙研判的人物-账户-电话三要素
  evidence_items                      → 案件详情「证据材料」页签
  freeze_approvals / freeze_receipts  → 冻结审批链与回执
  imported_fund_flows                 → 资金流水导入留痕
  merge_suggestions                   → 并案建议
  review_opinions                     → 复核意见

设计原则
--------
1. **脱敏优先**：手机号 138****8888、银行卡 6222 **** **** 8888、
   身份证 4201**********1234、人名 张*明。中间一律打星号，
   与 CLOUD_LLM_MASK 的出向脱敏口径一致，演示截图可直接外发。
2. **不编造真实主体**：全部为程序生成，人名/账号均为构造值，
   不对应任何真实自然人或账户。
3. **外键自洽**：case_id / order_id / review_id / person_id 均取自
   库中已存在的真实主键，保证 JOIN 与列表页能正常渲染。
4. **幂等**：可重复运行。默认 skip-if-nonempty；--force 先清空本脚本
   写入的表再重建（只清这 9 张表，不碰业务主数据）。
5. **可复现**：固定随机种子。

用法
----
  python seed_empty_tables.py            # 仅在表为空时填充
  python seed_empty_tables.py --force    # 清空这 9 张表后重建
  python seed_empty_tables.py --dry-run  # 只报告将要写入的行数
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

# 只加载 backend/key.env —— 与 main.py 的加载方式一致；根目录 .env 仅供
# docker-compose 做 ${VAR:-default} 插值，不由本脚本读取（避免两套配置互相干扰）。
load_dotenv(Path(__file__).resolve().parent / "key.env")

from sqlalchemy import text  # noqa: E402

from database import db  # noqa: E402

SEED = 20260918
random.seed(SEED)

# 本脚本负责的表（--force 时只清这些）
MANAGED_TABLES = [
    "accounts", "persons", "phones",
    "evidence_items",
    "freeze_approvals", "freeze_receipts",
    "imported_fund_flows",
    "merge_suggestions",
    "review_opinions",
]

# 清库顺序：必须先删子表（accounts/phones 外键指向 persons），
# 否则 DELETE FROM persons 会被外键约束拒绝。
DELETE_ORDER = [
    "accounts", "phones", "persons",       # 子 → 父
    "evidence_items",
    "freeze_approvals", "freeze_receipts",
    "imported_fund_flows",
    "merge_suggestions",
    "review_opinions",
]

# ---------------------------------------------------------------- 脱敏素材库
# 人名：姓氏 + 星号 + 末字（保留可辨识度但不可还原）
_SURNAMES = "王李张刘陈杨黄赵周吴徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
_GIVEN = "伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英建华文博宇轩浩然的雪梅国庆志强晓东春燕海燕建国建军伟东小燕小林凤兰玉兰"

_PHONE_PREFIX = ["138", "139", "136", "135", "137", "150", "151", "152", "158", "159",
                 "166", "173", "175", "177", "180", "181", "182", "185", "186", "187",
                 "188", "189", "130", "131", "132", "155", "156", "176", "178"]
_CARRIERS = ["中国移动", "中国联通", "中国电信", "中国广电"]

_BANKS = ["中国工商银行", "中国农业银行", "中国银行", "中国建设银行", "交通银行",
          "招商银行", "兴业银行", "浦发银行", "民生银行", "中信银行", "光大银行",
          "平安银行", "广发银行", "华夏银行", "邮储银行", "北京银行", "南京银行"]

# 银行 BIN 段（用于生成"看起来像"的卡号前缀；均为公开的卡组织段，不含真实账户）
_CARD_BINS = ["622202", "622848", "622588", "622609", "621661", "622622",
              "622568", "622909", "621700", "622700", "622262", "621286",
              "622280", "621225", "621226", "622150", "620521"]

_JOBS = ["公司职员", "个体经营", "教师", "学生", "退休人员", "自由职业", "公务员",
         "企业主", "财务人员", "医务工作者", "IT 从业者", "务工人员", "销售",
         "家庭主妇", "工程师", "会计"]
_CITIES = ["湖北省武汉市", "湖北省襄阳市", "湖北省宜昌市", "湖北省黄石市", "湖北省十堰市",
           "湖北省荆州市", "湖北省荆门市", "湖北省孝感市", "湖南省长沙市", "河南省郑州市",
           "广东省深圳市", "广东省广州市", "浙江省杭州市", "江苏省南京市", "四川省成都市"]

_SUSPECT_ROLES = ["主犯", "从犯", "话务员", "取款手", "卡农", "技术支撑", "引流人员", "洗钱"]
_VICTIM_ROLE = "受害人"

_EVIDENCE_TYPES = [
    ("通话记录", "调取被害人通话详单，共 {n} 条记录，其中境外号码 {k} 次"),
    ("银行流水", "调取涉案账户交易明细，累计转账 {n} 笔，涉案金额 {amt} 元"),
    ("聊天记录", "提取被害人手机聊天记录，含诈骗话术文本 {n} 条"),
    ("转账凭证", "被害人提供的银行转账回执 {n} 张，收款账户为 {acct}"),
    ("嫌疑人供述", "讯问笔录，嫌疑人供认参与话务引流环节，获利 {amt} 元"),
    ("电子数据", "手机取证镜像，恢复已删除的诈骗话术文档与被害人名单"),
    ("视频监控", "涉案 ATM 取款监控视频片段，时长约 {n} 分钟"),
    ("第三方支付记录", "调取第三方支付平台交易流水，涉及账户 {n} 个"),
]


def mask_name() -> str:
    """张* / 张*明 —— 保留姓氏与首末字"""
    s = random.choice(_SURNAMES)
    g = random.choice(_GIVEN)
    if random.random() < 0.5:
        return f"{s}*"
    return f"{s}*{g}"


def mask_phone() -> str:
    """138****8888 —— 前 3 后 4 保留，中间 4 位打星"""
    return f"{random.choice(_PHONE_PREFIX)}****{random.randint(0, 9999):04d}"


def mask_card() -> str:
    """6222 **** **** 8888 —— BIN 保留，中段打星，末 4 位保留"""
    bin6 = random.choice(_CARD_BINS)
    return f"{bin6[:4]} **** **** {random.randint(0, 9999):04d}"


def mask_id_card() -> str:
    """4201**********1234 —— 地区码与末 4 位保留"""
    area = random.choice(["4201", "4206", "4205", "4208", "4301", "4101", "4403", "3301"])
    return f"{area}**********{random.randint(0, 9999):04d}"


def mask_address(city: str) -> str:
    """保留到区/街道粒度，门牌号打星"""
    return f"{city}**区**街道**号"


def rand_dt(days_back: int = 180, min_days_back: int = 0) -> datetime:
    """随机过去时间点。min_days_back 用于给后续"必须更晚"的时间留出空间。"""
    lo = max(0, min(min_days_back, days_back))
    return datetime.now() - timedelta(
        days=random.randint(lo, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def rand_dt_after(base: datetime, min_days: int = 1, max_days: int = 30) -> datetime:
    """生成严格晚于 base 且不晚于"当前时刻"的时间点。

    用于「复核时间晚于创建时间」这类时序约束。若 base 距现在太近、容不下完整
    偏移量，则退化为在 (base, now-1h] 区间内取点，**始终保证返回值 > base**
    （否则会出现"复核早于创建"的逻辑矛盾）。
    """
    cap = datetime.now() - timedelta(hours=1)
    offset = timedelta(
        days=random.randint(min_days, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    candidate = base + offset
    if candidate <= cap:
        return candidate

    room = cap - base
    if room > timedelta(minutes=5):
        # 在 base 与 cap 之间取点，严格晚于 base
        return base + room * random.uniform(0.25, 0.95)
    # 极端退化：base 已贴近 cap。仍返回严格晚于 base 的值
    return base + timedelta(minutes=random.randint(1, 30))


def ping(c) -> dict:
    """读取库中已有的真实主键，供外键自洽填写"""
    info = {}
    info["cases"] = [r[0] for r in c.execute(
        text("SELECT case_id FROM cases ORDER BY id LIMIT 120")).fetchall()]
    info["case_rows"] = c.execute(text(
        "SELECT case_id, scam_type, victim_gender, victim_age, victim_job, "
        "victim_name, amount_value FROM cases ORDER BY id LIMIT 120")).fetchall()
    info["users"] = [r[0] for r in c.execute(
        text("SELECT id FROM users WHERE role IN ('admin','analyst','investigator') ORDER BY id LIMIT 20")
    ).fetchall()] or [r[0] for r in c.execute(text("SELECT id FROM users ORDER BY id LIMIT 20")).fetchall()]
    info["user_rows"] = c.execute(text(
        "SELECT id, username, display_name, role, department FROM users ORDER BY id LIMIT 20")).fetchall()
    info["gangs"] = [r[0] for r in c.execute(
        text("SELECT gang_id FROM gangs ORDER BY id LIMIT 30")).fetchall()]
    info["freeze_orders"] = c.execute(text(
        "SELECT order_id, case_id, gang_id, applicant_id, applicant_name, "
        "target_accounts, freeze_amount FROM freeze_orders ORDER BY id")).fetchall()
    info["review_tasks"] = c.execute(text(
        "SELECT review_id, case_id, gang_id, assigned_to_id, assigned_to_name, "
        "assigned_department, status FROM review_tasks ORDER BY id")).fetchall()
    info["flow_accounts"] = [r[0] for r in c.execute(text(
        "SELECT target_account FROM capital_flows "
        "WHERE target_account REGEXP '^[0-9]{10,}$' "
        "GROUP BY target_account LIMIT 200")).fetchall()]
    info["sessions"] = [r[0] for r in c.execute(text(
        "SELECT session_id FROM analysis_sessions ORDER BY id LIMIT 20")).fetchall()]
    return info


# ------------------------------------------------------------------ 各表构建
def build_persons_accounts_phones(info) -> tuple:
    """人物-账户-电话三要素。

    每案：1 名受害人 + 1~3 名嫌疑人；每嫌疑人配 1~2 个账户 + 1 个电话。
    role 取值与 gangs.py 的 suspects 过滤口径一致（suspect / victim）。
    """
    persons, accounts, phones = [], [], []
    for row in info["case_rows"]:
        case_id, scam_type, v_gender, v_age, v_job, v_name, amount = row
        city = random.choice(_CITIES)

        # 受害人（1 名，沿用案件已有画像字段）
        persons.append({
            "case_id": case_id,
            "name": mask_name(),
            "role": "victim",
            "gender": v_gender or random.choice(["男", "女"]),
            "age": str(v_age or random.randint(20, 65)),
            "phone": mask_phone(),
            "job": v_job or random.choice(_JOBS),
            "address": mask_address(city),
        })

        # 嫌疑人 1~3 名
        for _ in range(random.randint(1, 3)):
            p = {
                "case_id": case_id,
                "name": mask_name(),
                "role": "suspect",
                "gender": random.choice(["男", "女"]),
                "age": str(random.randint(19, 55)),
                "phone": mask_phone(),
                "job": random.choice(_SUSPECT_ROLES),
                "address": mask_address(random.choice(_CITIES)),
            }
            persons.append(p)

    return persons, accounts, phones


def build_evidence(info) -> list:
    """案件证据材料（每案 2~5 条），供 /api/report 的「五、证据材料」章节使用"""
    items = []
    for row in info["case_rows"]:
        case_id, scam_type, _, _, _, _, amount = row
        amt = int(amount or random.randint(10000, 500000))
        for _ in range(random.randint(2, 5)):
            ev_type, tpl = random.choice(_EVIDENCE_TYPES)
            content = tpl.format(
                n=random.randint(3, 260),
                k=random.randint(1, 18),
                amt=f"{amt:,}",
                acct=mask_card(),
            )
            items.append({
                "case_id": case_id,
                "type": ev_type,
                "content": content,
                "status": random.choice(["已固定", "已固定", "已固定", "待鉴定", "已鉴定"]),
                "created_at": rand_dt(150),
            })
    return items


def _extract_accounts(raw) -> list:
    """freeze_orders.target_accounts 有两种历史存法：
       - ["6222...", ...]                          （纯字符串数组）
       - [{"bank_name":..,"account_number":..}, ...]（对象数组）
       统一抽出「账户号 + 银行名」列表，供回执表使用。
    """
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for it in data:
        if isinstance(it, dict):
            num = it.get("account_number") or it.get("account") or ""
            bank = it.get("bank_name") or ""
            # 历史演示数据里的账号是明文长串，这里统一转成脱敏格式
            out.append((maskify_card(num) if num else mask_card(), bank))
        elif isinstance(it, str) and it:
            out.append((maskify_card(it), ""))
    return out or []


def maskify_card(num: str) -> str:
    """把已有账号转为脱敏形态：保留前 4 后 4，其余打星。"""
    digits = "".join(ch for ch in str(num) if ch.isdigit())
    if len(digits) >= 12:
        return f"{digits[:4]} **** **** {digits[-4:]}"
    if len(digits) > 7:
        return f"{digits[:3]}****{digits[-4:]}"
    return digits or mask_card()


def build_freeze_chain(info) -> tuple:
    """冻结审批链 + 执行回执。

    基于已有 freeze_orders（3 张），每张补 1~2 级审批与 1 张回执。
    注：这 3 张单子的 target_accounts 指向同一个测试账户，若原样照搬会出现
    「三条回执长得一模一样」的克隆感。故按序号为后续单子换用该案资金流中
    的其它（已脱敏）账户，保持真实感。
    """
    approvals, receipts = [], []
    level_names = ["中队长", "大队长", "反诈中心负责人"]
    flow_pool = sorted({maskify_card(a) for a in (info["flow_accounts"] or [])})

    for idx, fo in enumerate(info["freeze_orders"]):
        (order_id, case_id, gang_id, applicant_id, applicant_name,
         target_accounts, freeze_amount) = fo
        extracted = _extract_accounts(target_accounts) or [(mask_card(), "")]
        tgt_num, tgt_bank = extracted[0]
        # 第 2 条起换账户，避免三条回执完全同质
        if idx > 0 and flow_pool:
            tgt_num = flow_pool[idx % len(flow_pool)]
            tgt_bank = random.choice(_BANKS)

        n_levels = random.randint(1, 2)
        # 审批链时序：下一级必须晚于上一级；起点回拨 2 天留出递增空间
        prev_at = rand_dt(60, min_days_back=2)
        for lvl in range(1, n_levels + 1):
            u = random.choice(info["user_rows"])
            # 语义一致性：decision 与 comment 必须匹配（pending = 尚未表决，
            # 不能出现"同意冻结"这类已表决批语）；同一张单子中间层级若未决，
            # 后续层级不应存在（见下方 break）。
            decision = "approved" if lvl < n_levels else random.choice(
                ["approved", "approved", "approved", "pending"]
            )
            if decision == "approved":
                comment = random.choice([
                    "案情清楚、紧急程度高，同意冻结。",
                    "涉案账户资金仍在流动，同意立即冻结。",
                    "证据链完整，同意按流程冻结。",
                    "同意，注意同步告知开户行。",
                ])
            else:
                comment = random.choice([
                    "补充被害人陈述后再次提交。",
                    "涉案金额需与银行流水二次核对，暂缓表决。",
                    "待补充上级审批意见后表决。",
                ])
            approvals.append({
                "order_id": order_id,
                "approver_id": u[0],
                "approver_name": u[2] or u[1],
                "approver_role": level_names[min(lvl, len(level_names) - 1)],
                "approval_level": lvl,
                "decision": decision,
                "comment": comment,
                "created_at": prev_at,
            })
            if decision == "pending":
                # 未表决则不会继续往上流转
                break
            prev_at = rand_dt_after(prev_at, min_days=0, max_days=3)

        receipts.append({
            "order_id": order_id,
            "target_account": tgt_num,
            "bank_name": tgt_bank or random.choice(_BANKS),
            "execution_status": random.choice(["success", "success", "success", "pending"]),
            "execution_message": random.choice([
                f"冻结指令已送达{tgt_bank or '开户行'}，账户状态变更为只收不付，冻结金额上限 {int(freeze_amount or 0):,} 元。",
                "已通过银联接口完成冻结，冻结金额以实际入账为准。",
                "已在反诈平台提交冻结，等待银行回执。",
            ]),
            "executed_by": applicant_name or "admin",
            "external_ref": f"BANK{random.randint(10**11, 10**12 - 1)}",
            "freeze_until": datetime.now() + timedelta(days=random.choice([30, 90, 180])),
            "created_at": rand_dt(60),
        })
    return approvals, receipts


def build_imported_flows(info) -> list:
    """资金流水导入留痕（AMLSim / 银行 CSV 导入记录）

    注意：capital_flows 里存的是**未脱敏**的长账号，直接搬过来会污染演示数据，
    因此这里统一走 maskify_card 转成脱敏形态。
    """
    rows = []
    ops = [u[2] or u[1] for u in info["user_rows"]]
    sources = ["AMLSim_sample_transactions.csv", "银行流水_导出_202608.csv",
               "涉案账户交易明细_0820.xlsx", "第三方支付流水_0901.csv",
               "反诈平台下发数据_0905.xlsx"]
    raw_accts = info["flow_accounts"] or [mask_card() for _ in range(40)]
    # 先统一脱敏，再抽样，避免明文账号外泄
    pool = sorted({maskify_card(a) for a in raw_accts})
    for _ in range(random.randint(20, 40)):
        fa = random.choice(pool)
        ta = random.choice(pool)
        while ta == fa:
            ta = random.choice(pool)
        rows.append({
            "operator": random.choice(ops),
            "session_id": random.choice(info["sessions"]) if info["sessions"] else "",
            "source_file": random.choice(sources),
            "from_account": fa,
            "to_account": ta,
            "amount": round(random.uniform(500, 480000), 2),
            "tx_timestamp": rand_dt(120).strftime("%Y-%m-%d %H:%M:%S"),
            "raw": json.dumps({
                "from_account": fa, "to_account": ta,
                "note": "导入留痕（演示数据，账号已脱敏）",
            }, ensure_ascii=False),
            "created_at": rand_dt(120),
        })
    return rows


def build_merge_suggestions(info) -> list:
    """并案建议（案情相似度触发）"""
    cases = info["cases"]
    if len(cases) < 4:
        return []
    rows = []
    used = set()
    for _ in range(random.randint(12, 20)):
        a, b = random.sample(cases, 2)
        key = tuple(sorted((a, b)))
        if key in used:
            continue
        used.add(key)
        sim = round(random.uniform(0.72, 0.97), 4)
        status = random.choice(["pending"] * 5 + ["approved", "rejected"])
        ## 创建时间至少回拨 2 天，给"复核时间必须更晚且不能是未来"留出空间
        created_at = rand_dt(90, min_days_back=2)
        # 语义一致性：pending 表示「尚未复核」，必须 reviewed_by / reviewed_at 均为空；
        # 已出结论（approved / rejected）必须同时具备复核人与复核时间，且复核时间晚于创建时间。
        if status == "pending":
            reviewed_by = None
            reviewed_at = None
        else:
            reviewed_by = random.choice(info["users"])
            reviewed_at = rand_dt_after(created_at, min_days=1, max_days=30)
        rows.append({
            "case_id_a": a,
            "case_id_b": b,
            "similarity": sim,
            "reason": random.choice([
                "诈骗话术高度相似，均涉及「注销校园贷」话术模板",
                "涉案收款账户存在同一账户再次出现",
                "被害人接到的诈骗电话前 7 位一致",
                "作案时间集中于同一周，作案手法一致",
                "AI 生成案情向量余弦相似度超阈值",
                "同一 GOIP 设备关联，疑似同一话务窝点",
            ]),
            "status": status,
            "reviewed_by": reviewed_by,
            "created_at": created_at,
            "reviewed_at": reviewed_at,
        })
    return rows


def build_review_opinions(info) -> list:
    """复核意见（挂到已有 review_tasks 上）"""
    rows = []
    if not info["review_tasks"]:
        return rows
    for rt in info["review_tasks"]:
        review_id, case_id, gang_id, to_id, to_name, dept, status = rt
        for _ in range(random.randint(1, 3)):
            u = random.choice(info["user_rows"])
            otype = random.choice(["confirm", "correct", "reject", "supplement"])
            rows.append({
                "review_id": review_id,
                "reviewer_id": u[0],
                "reviewer_name": u[2] or u[1],
                "opinion_type": otype,
                "correction_data": json.dumps({
                    "field": random.choice(["risk_level", "scam_type", "amount_value", "gang_id"]),
                    "note": "演示用复核意见，不含真实案件信息",
                }, ensure_ascii=False),
                "comment": {
                    "confirm": "复核确认 AI 研判结论，串并关系成立。",
                    "correct": "风险等级偏高，建议由「高危」下调为「中危」。",
                    "reject": "证据不足，暂不并入该团伙，退回补充侦查。",
                    "supplement": "建议补充资金回流链路佐证后再次提交复核。",
                }[otype],
                "created_at": rand_dt(50),
            })
    return rows


# ------------------------------------------------------------------ 写库
def _json_cols(c, table: str) -> set:
    """返回该表中类型为 json 的列名（pymysql 不认识 dict，需先 dumps 成字符串）"""
    rows = c.execute(text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
        "AND DATA_TYPE = 'json'"), {"t": table}).fetchall()
    return {r[0] for r in rows}


def insert_rows(c, table: str, rows: list, json_cols: set = None) -> int:
    if not rows:
        return 0
    json_cols = json_cols if json_cols is not None else _json_cols(c, table)
    # 统一键集合，缺字段补 None，避免 executemany 列数错位
    cols = list(rows[0].keys())
    payload = []
    for r in rows:
        item = {}
        for k in cols:
            v = r.get(k)
            if k in json_cols and v is not None and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False)
            item[k] = v
        payload.append(item)
    collist = ", ".join(f"`{k}`" for k in cols)
    ph = ", ".join(f":{k}" for k in cols)
    c.execute(text(f"INSERT INTO `{table}` ({collist}) VALUES ({ph})"), payload)
    return len(payload)


def main() -> int:
    ap = argparse.ArgumentParser(description="填充 9 张空表（脱敏演示数据）")
    ap.add_argument("--force", action="store_true",
                    help="先清空本脚本管理的 9 张表再重建")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = ap.parse_args()

    print("=" * 70)
    print("空表数据填充 · 脱敏演示数据种子")
    print(f"随机种子 = {SEED}   force={args.force}   dry_run={args.dry_run}")
    print("=" * 70)

    with db.engine.begin() as c:
        counts = {t: c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
                  for t in MANAGED_TABLES}
        print("\n[当前行数]")
        for t in MANAGED_TABLES:
            flag = "  <== 空" if counts[t] == 0 else ""
            print(f"  {t:24s} {counts[t]:>7d}{flag}")

        if args.force:
            print("\n[--force] 清空本脚本管理的表…")
            if not args.dry_run:
                # 按子→父顺序删除，规避外键约束
                for t in DELETE_ORDER:
                    c.execute(text(f"DELETE FROM `{t}`"))
            print("  已清空（其余业务表未触碰）")
        else:
            occupied = [t for t in MANAGED_TABLES if counts[t] > 0]
            if occupied:
                print(f"\n[跳过] 以下表已有数据，不覆盖：{occupied}")
                print("        如需重建请加 --force")

    targets = MANAGED_TABLES if args.force else [
        t for t in MANAGED_TABLES if counts[t] == 0
    ]

    with db.engine.begin() as c:
        info = ping(c)

        print(f"\n[数据源] 案件 {len(info['cases'])} / 用户 {len(info['users'])} "
              f"/ 团伙 {len(info['gangs'])} / 冻结单 {len(info['freeze_orders'])} "
              f"/ 复核任务 {len(info['review_tasks'])} / 流水账号 {len(info['flow_accounts'])}")

        persons, _a, _p = build_persons_accounts_phones(info)
        evidence = build_evidence(info)
        approvals, receipts = build_freeze_chain(info)
        flows = build_imported_flows(info)
        merges = build_merge_suggestions(info)
        opinions = build_review_opinions(info)

        # persons 先落库拿到自增 id，再据此生成 accounts / phones（外键自洽）
        plan_persons = persons if "persons" in targets else []
        plan_evidence = evidence if "evidence_items" in targets else []
        plan_approvals = approvals if "freeze_approvals" in targets else []
        plan_receipts = receipts if "freeze_receipts" in targets else []
        plan_flows = flows if "imported_fund_flows" in targets else []
        plan_merges = merges if "merge_suggestions" in targets else []
        plan_opinions = opinions if "review_opinions" in targets else []

        print("\n[将写入]")
        print(f"  persons               {len(plan_persons):>7d}")
        print(f"  accounts              {'(随 persons 联动)' if 'accounts' in targets else 0:>7}")
        print(f"  phones                {'(随 persons 联动)' if 'phones' in targets else 0:>7}")
        print(f"  evidence_items        {len(plan_evidence):>7d}")
        print(f"  freeze_approvals      {len(plan_approvals):>7d}")
        print(f"  freeze_receipts       {len(plan_receipts):>7d}")
        print(f"  imported_fund_flows   {len(plan_flows):>7d}")
        print(f"  merge_suggestions     {len(plan_merges):>7d}")
        print(f"  review_opinions       {len(plan_opinions):>7d}")

        if args.dry_run:
            print("\n[dry-run] 未写库。")
            return 0

        written = {}

        # 1) persons
        if plan_persons:
            written["persons"] = insert_rows(c, "persons", plan_persons)
            # 拿回自增 id 与 case_id/role 的对应
            got = c.execute(text(
                "SELECT id, case_id, role FROM persons ORDER BY id")).fetchall()
            # 按 case_id 分组，受害人与嫌疑人分别建账户/电话
            by_case = {}
            for pid, cid, role in got:
                by_case.setdefault((cid, role), []).append(pid)
            acc_rows, ph_rows = [], []
            for (cid, role), pids in by_case.items():
                for pid in pids:
                    if role == _VICTIM_ROLE:
                        acc_rows.append({
                            "person_id": pid,
                            "account_number": mask_card(),
                            "bank_name": random.choice(_BANKS),
                            "risk_level": random.choice(["LOW", "LOW", "MEDIUM"]),
                        })
                        ph_rows.append({
                            "person_id": pid,
                            "phone_number": mask_phone(),
                            "carrier": random.choice(_CARRIERS),
                            "risk_level": "LOW",
                        })
                    else:
                        for _ in range(random.randint(1, 2)):
                            acc_rows.append({
                                "person_id": pid,
                                "account_number": mask_card(),
                                "bank_name": random.choice(_BANKS),
                                "risk_level": random.choice(["HIGH", "HIGH", "MEDIUM", "CRITICAL"]),
                            })
                        ph_rows.append({
                            "person_id": pid,
                            "phone_number": mask_phone(),
                            "carrier": random.choice(_CARRIERS),
                            "risk_level": random.choice(["HIGH", "MEDIUM"]),
                        })
            if "accounts" in targets:
                written["accounts"] = insert_rows(c, "accounts", acc_rows)
            if "phones" in targets:
                written["phones"] = insert_rows(c, "phones", ph_rows)

        # 2) 其余表
        if plan_evidence:
            written["evidence_items"] = insert_rows(c, "evidence_items", plan_evidence)
        if plan_approvals:
            written["freeze_approvals"] = insert_rows(c, "freeze_approvals", plan_approvals)
        if plan_receipts:
            written["freeze_receipts"] = insert_rows(c, "freeze_receipts", plan_receipts)
        if plan_flows:
            written["imported_fund_flows"] = insert_rows(c, "imported_fund_flows", plan_flows)
        if plan_merges:
            written["merge_suggestions"] = insert_rows(c, "merge_suggestions", plan_merges)
        if plan_opinions:
            written["review_opinions"] = insert_rows(c, "review_opinions", plan_opinions)

        print("\n[已写入]")
        for k, v in written.items():
            print(f"  {k:24s} {v:>7d}")

    # 复核
    print("\n[复核 · 现值]")
    with db.engine.connect() as c2:
        for t in MANAGED_TABLES:
            n = c2.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
            print(f"  {t:24s} {n:>7d}")

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
