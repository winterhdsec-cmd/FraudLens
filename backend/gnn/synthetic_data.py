"""
合成案件 + 资金流数据生成器（可复现、不涉密）

用途：
- 在没有真实查控数据的前提下，生成结构可信的诈骗案件与资金流转记录，
  用于驱动 graph_builder 的资金链图模型，并作为论文四基线 + 消融实验的评测数据。
- 每个"团伙"共享独立收款账户（与"资金链主导串并案"的设定一致）；不同团伙默认
  不共享账户，以验证 share_account 边能将同伙案件正确聚簇，且不被同城市/同类型/
  同金额的弱相似边误拉（假阳性串并消解）。

生成结果：
- cases:        List[Dict]      案件列表（兼容现有 demo 字段 + 扩展 accounts/perpetrators）
- accounts_tx:  List[Dict]      账户间资金流转记录 {from_account, to_account, amount, timestamp}
- ground_truth: Dict[case_id, gang_id]  真值团伙标签（供评测计算 NMI / ARI / F1）
"""
import random
from typing import List, Dict, Any, Tuple

# B-L11：数据血缘（2026-08-04）
import uuid as _uuid
from datetime import datetime as _dt

GENERATOR_VERSION = "2.0"

CITY_POOL = [
    ("广东省", "广州市"), ("广东省", "深圳市"), ("浙江省", "杭州市"),
    ("浙江省", "温州市"), ("江苏省", "南京市"), ("四川省", "成都市"),
    ("河南省", "郑州市"), ("湖南省", "长沙市"), ("福建省", "厦门市"),
    ("山东省", "青岛市"),
]
SCAM_TYPES = [
    "刷单返利", "虚假贷款", "冒充客服", "杀猪盘", "冒充公检法", "虚假投资",
]
GENDERS = ["男", "女"]

# A3: 各诈骗类型的话术模板（同团伙案件共享相似话术，使双通道语义通道在评测中可生效）
SCRIPT_TEMPLATES = {
    "刷单返利": "您好，兼职刷单返利任务，垫付即返本金加佣金，操作简单日结工资。",
    "虚假贷款": "您好，无抵押低息贷款秒到账，需先下载 APP 认证，客服一对一办理。",
    "冒充客服": "您好，您购买的商品存在质量问题，将为您双倍理赔，请配合关闭自动扣费。",
    "杀猪盘": "缘分不易，我在投资平台有内部渠道，跟着操作稳赚不赔，先小投入试水。",
    "冒充公检法": "这里是某某公安局，您名下账户涉嫌洗钱，需将资金转入安全账户配合清查。",
    "虚假投资": "老师带单虚拟币/股票内幕消息，跟单复利翻倍，专属会员群每日荐股。",
}


def generate_synthetic_dataset(
    n_gangs: int = 5,
    cases_per_gang: int = 8,
    seed: int = 42,
    cross_gang_account_share: float = 0.0,
    reflux_cycle_prob: float = 0.0,
    intra_share_prob: float = 1.0,
    attr_noise: float = 0.0,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """
    生成合成数据集

    Args:
        n_gangs: 团伙数量
        cases_per_gang: 每个团伙案件数
        seed: 随机种子（保证可复现）
        cross_gang_account_share: 跨团伙账户共享概率（制造干扰，默认 0）
        reflux_cycle_prob: 资金回流闭环生成概率（制造已知闭环，默认 0，用于评测/演示）
        intra_share_prob: 团伙内账户共享概率（默认 1.0 = 必共享；<1.0 退化结构通道同质性）
        attr_noise: 属性噪声概率（默认 0；>0 时本案件以小概率改用随机 type/city/perpetrator，
                    破坏 type/city/perpetrator 结构通道的团伙同质性。脚本仍按团伙模板，
                    故话术(text)通道成为唯一可靠判别信号 —— 用于体现双通道真实增益）

    Returns:
        (cases, accounts_tx, ground_truth)
    """
    rng = random.Random(seed)
    cases: List[Dict[str, Any]] = []
    accounts_tx: List[Dict[str, Any]] = []
    ground_truth: Dict[str, int] = {}

    # B-L11：合成数据血缘头（每条案件 source 继承，可追溯生成参数）
    lineage = {
        "kind": "synthetic",
        "generator_version": GENERATOR_VERSION,
        "generated_at": _dt.utcnow().isoformat() + "Z",
        "lineage_id": _uuid.uuid4().hex[:12],
        "schema_version": "1.0",
        "params": {
            "n_gangs": n_gangs,
            "cases_per_gang": cases_per_gang,
            "seed": seed,
            "cross_gang_account_share": cross_gang_account_share,
            "reflux_cycle_prob": reflux_cycle_prob,
            "intra_share_prob": intra_share_prob,
            "attr_noise": attr_noise,
        },
    }

    for gang in range(n_gangs):
        # 每个团伙分配 1~2 个独立收款账户 + 1~3 个违法者
        n_acc = rng.randint(1, 2)
        gang_accounts = [f"ACC-{gang:03d}-{j:02d}" for j in range(n_acc)]
        n_perp = rng.randint(1, 3)
        gang_perps = [f"PERP-{gang:03d}-{k:02d}" for k in range(n_perp)]

        # 团伙内资金层级：收款账户 -> 中转账户 -> 上游归集账户
        hub = f"HUB-{gang:03d}-00"
        upstream = f"UP-{gang:03d}-00"
        gang_total_amount = 0.0

        scam_type = rng.choice(SCAM_TYPES)
        prov, city = rng.choice(CITY_POOL)

        # A3: 同团伙案件共享相似话术模板（便于双通道语义通道在评测中生效）
        script_template = SCRIPT_TEMPLATES.get(scam_type, SCRIPT_TEMPLATES["刷单返利"])

        for i in range(cases_per_gang):
            case_id = f"CASE-{gang:03d}-{i:03d}"
            amount = round(rng.uniform(5000, 200000), 2)
            gang_total_amount += amount

            # 属性噪声（A-BGE 复测）：小概率让本案件的 类型/城市/违法者 偏离团伙，
            # 破坏 type/city/perpetrator 结构通道的团伙同质性；脚本仍按团伙模板（文本信号保留）。
            if attr_noise > 0 and rng.random() < attr_noise:
                c_type = rng.choice(SCAM_TYPES)
                c_prov, c_city = rng.choice(CITY_POOL)
                c_perps = [f"PERP-X-{rng.randint(0, 999):03d}"]
            else:
                c_type, c_prov, c_city, c_perps = scam_type, prov, city, list(gang_perps)

            # 团伙内账户共享退化（A-BGE 复测）：小概率本案不挂团伙账户，
            # 弱化 account/fund_flow 结构通道的团伙同质性
            if intra_share_prob >= 1.0 or rng.random() < intra_share_prob:
                case_accounts = list(gang_accounts)
            else:
                case_accounts = []

            # A3: 同团伙案件共享相似话术（金额不同但话术模板相同，双通道语义通道可聚同伙）
            script_noise = rng.choice(["", "（限时名额）", "（官方认证）", "（系统维护中）"])
            script = (f"{script_template}{script_noise}"
                      f"受害人位于{prov}{city}，涉案金额约{amount:.0f}元。")

            case = {
                "case_id": case_id,
                "victim_name": f"受害人-{gang:03d}-{i:03d}",
                "victim_phone": f"1{rng.randint(3,9)}{rng.randint(10**8, 10**9-1)}",
                "scam_type": c_type,
                "victim_address": f"{c_prov}{c_city}",
                "amount_value": amount,
                "risk_score": rng.randint(60, 95),
                "victim_age": rng.randint(18, 70),
                "victim_gender": rng.choice(GENDERS),
                "script": script,  # A3: 话术文本（双通道语义通道输入）
                # 资金链扩展字段
                "accounts": case_accounts,
                "perpetrators": c_perps,
                # B-L11：数据血缘（kind= synthetic，含生成参数，可追溯）
                "source": dict(lineage),
            }

            # 跨团伙账户共享（干扰项）：小概率把别的团伙账户挂到本案
            if cross_gang_account_share > 0 and gang > 0 and rng.random() < cross_gang_account_share:
                other = rng.randint(0, gang - 1)
                case["accounts"].append(f"ACC-{other:03d}-00")

            cases.append(case)
            ground_truth[case_id] = gang

        # 资金流转：每个收款账户 -> 中转 -> 上游（带时间戳与金额）
        base_ts = 1700000000 + gang * 86400
        for acc in gang_accounts:
            accounts_tx.append({
                "from_account": acc,
                "to_account": hub,
                "amount": round(gang_total_amount / max(n_acc, 1) * 0.9, 2),
                "timestamp": str(base_ts),
            })
        accounts_tx.append({
            "from_account": hub,
            "to_account": upstream,
            "amount": round(gang_total_amount * 0.85, 2),
            "timestamp": str(base_ts + 3600),
        })

        # 资金回流闭环（受控，默认 0）：UP -> 收款账户，形成 acc->hub->up->acc 闭环
        # 用于演示/评测资金回流检测（真实场景对应洗钱层资金回流同一收款卡）
        if reflux_cycle_prob > 0 and rng.random() < reflux_cycle_prob:
            accounts_tx.append({
                "from_account": upstream,
                "to_account": gang_accounts[0],
                "amount": round(gang_total_amount * 0.1, 2),
                "timestamp": str(base_ts + 7200),
            })

    return cases, accounts_tx, ground_truth


if __name__ == "__main__":
    cases, accounts_tx, gt = generate_synthetic_dataset()
    n_account_nodes = len({a for c in cases for a in c["accounts"]})
    print(f"cases={len(cases)} gangs={len(set(gt.values()))} "
          f"distinct_case_accounts={n_account_nodes} fund_flow_edges={len(accounts_tx)}")
    print("ground_truth sample:", dict(list(gt.items())[:3]))
