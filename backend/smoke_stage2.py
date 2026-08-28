"""Stage 2 收尾冒烟测试：资金回流闭环检测(#12) + 可冻卡清单/置信度门控(#9)。
验证数据源、集成到 GangDetector、以及门控不误报/弱团伙不冻结。
"""
import sys, os, types, importlib.util, logging
from collections import defaultdict

BACKEND = "E:/FraudLens/backend"

# --- 轻量桩：规避后端重型依赖链 ---
for mod in ["tools", "tools.redis_utils"]:
    m = types.ModuleType(mod)
    if mod.endswith("redis_utils"):
        m.get_redis = lambda: None
    sys.modules[mod] = m
_core = types.ModuleType("core")
_core_logger = types.ModuleType("core.logger")
_core_logger.logger = logging.getLogger("core")
sys.modules["core"] = _core
sys.modules["core.logger"] = _core_logger


if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
import gnn.graph_builder as gb
import gnn.synthetic_data as sd
import gnn.gang_detector as gd
import networkx as nx

# ---------- 1) 正向：含回流闭环的数据 ----------
cases, tx, gt = sd.generate_synthetic_dataset(
    seed=42, n_gangs=5, cases_per_gang=8, reflux_cycle_prob=1.0)
builder = gb.FraudGraphBuilder(use_db=False, use_cache=False)
G = builder.build_graph(cases, accounts_tx=tx)

# #12 数据源：有向资金子图 + 全局简单环
DG = builder.get_fund_flow_digraph()
cycles = list(nx.simple_cycles(DG))
assert len(cycles) > 0, "预期检出资金回流闭环"
print(f"[OK] fund_flow 有向子图: 节点={DG.number_of_nodes()} 边={DG.number_of_edges()} 检出闭环={len(cycles)}")
print("     示例闭环:", " -> ".join(cycles[0]), "-> ...")

# 用真值构造 communities（case + 其关联 account 节点）
comm = defaultdict(list)
for cid, g in gt.items():
    comm[g].append(cid)
for n, d in G.nodes(data=True):
    if d.get('node_type') == 'case':
        g = gt.get(n)
        for nb in G.neighbors(n):
            if G.nodes[nb].get('node_type') == 'account':
                comm[g].append(nb)
communities = {g: list(set(ids)) for g, ids in comm.items()}

# 不实例化完整 GangDetector（规避 __init__ 重型依赖），仅绑定所需方法到轻量实例
det = gd.GangDetector.__new__(gd.GangDetector)
det.graph = G
det.graph_builder = builder
det.communities = communities
# 绕过 __init__（规避重型依赖），需手动补 _generate_gang_info 依赖的实例属性（正常 __init__ 会设置）
det.enable_gating = True       # 客观置信度门控默认开启
det.use_text_channel = True    # A3 双通道默认开启

reflux = det.detect_reflux_cycles(communities)
n_reflux = sum(1 for v in reflux.values() if v['is_reflux'])
assert n_reflux > 0, "应至少1个团伙检出回流闭环"
print(f"[OK] detect_reflux_cycles: {n_reflux}/{len(communities)} 团伙标 is_reflux")

gangs = det._generate_gang_info(cases)
assert len(gangs) > 0
for ginfo in gangs:
    for k in ('freeze_candidates', 'confidence', 'gate_decision', 'is_reflux', 'reflux_cycles'):
        assert k in ginfo, f"缺字段 {k}"
    assert ginfo['gate_decision'] in ("建议冻结", "待人工复核")
    assert 0.0 <= ginfo['confidence'] <= 1.0
assert any(g['is_reflux'] for g in gangs), "应至少1个团伙 is_reflux=True"
print(f"[OK] _generate_gang_info: {len(gangs)} 团伙, #9 字段齐全")
ex = max(gangs, key=lambda x: x['confidence'])
print(f"     高置信示例: {ex['gang_id']} cases={ex['case_count']} "
      f"freeze={ex['freeze_candidates']} conf={ex['confidence']} "
      f"gate={ex['gate_decision']} is_reflux={ex['is_reflux']}")

# ---------- 2) 反向：无回流数据不应误报 ----------
cases0, tx0, gt0 = sd.generate_synthetic_dataset(
    seed=7, n_gangs=4, cases_per_gang=6, reflux_cycle_prob=0.0)
G0 = builder.build_graph(cases0, accounts_tx=tx0)
DG0 = builder.get_fund_flow_digraph()
assert len(list(nx.simple_cycles(DG0))) == 0, "无回流数据应检出0闭环"
print(f"[OK] 反向(无回流): fund_flow 子图闭环数=0 (未误报)")

# ---------- 3) 弱团伙门控：不过阈值 -> 待人工复核（契合 B5 绝不猜测定冻卡） ----------
weak_cases = [
    {"case_id": "W0", "scam_type": "刷单返利", "victim_address": "湖北武汉",
     "amount_value": 3000, "risk_score": 65, "accounts": ["ACC-W-00"],
     "perpetrators": ["PERP-W-00"]},
    {"case_id": "W1", "scam_type": "刷单返利", "victim_address": "湖北武汉",
     "amount_value": 3000, "risk_score": 65, "accounts": ["ACC-W-00"],
     "perpetrators": ["PERP-W-00"]},
]
Gw = builder.build_graph(weak_cases)  # 无 accounts_tx -> 无 fund_flow
det.graph = Gw
det.graph_builder = builder
det.communities = {99: ["W0", "W1", "account_ACC-W-00", "perpetrator_PERP-W-00"]}
gw = det._generate_gang_info(weak_cases)
assert len(gw) == 1
assert gw[0]['gate_decision'] == "待人工复核", \
    f"弱团伙应待人工复核, got {gw[0]['gate_decision']}"
assert gw[0]['is_reflux'] is False
print(f"[OK] 弱团伙门控: cases={gw[0]['case_count']} conf={gw[0]['confidence']} "
      f"gate={gw[0]['gate_decision']} (正确未建议冻结)")

print("\n=== ALL SMOKE STAGE2 PASSED ===")
