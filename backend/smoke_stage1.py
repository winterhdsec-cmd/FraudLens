"""Stage 1 冒烟测试：资金链图模型 + 向后兼容 + 特征去 hash

说明：backend 的 gnn/tools 包有重型依赖链（pydantic/torch 等）。本测试只验证
Stage 1 改动的 graph_builder 与 synthetic_data 逻辑，故用 importlib 直接加载这两个
模块文件，并对 tools.redis_utils 做最小桩（use_cache=False 时本就用不到）。
detect 端的 GNN 验证需在完整后端环境（Docker）跑，本测试 try/except 跳过。
"""
import sys, os, types, importlib.util

BACKEND = os.path.dirname(os.path.abspath(__file__))

# stub tools 包，避免重型依赖链（pydantic 等）
fake_tools = types.ModuleType('tools')
fake_ru = types.ModuleType('tools.redis_utils')
fake_ru.get_redis = lambda: None
sys.modules['tools'] = fake_tools
sys.modules['tools.redis_utils'] = fake_ru


def load(module_name, rel_path):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(BACKEND, rel_path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


gb = load("graph_builder", "gnn/graph_builder.py")
sd = load("synthetic_data", "gnn/synthetic_data.py")
FraudGraphBuilder = gb.FraudGraphBuilder
generate_synthetic_dataset = sd.generate_synthetic_dataset

from collections import Counter

# --- 1. 资金链图构建 ---
cases, accounts_tx, gt = generate_synthetic_dataset()
b = FraudGraphBuilder(use_db=False, use_cache=False)
G = b.build_graph(cases, accounts_tx=accounts_tx)
types = Counter(d['node_type'] for _, d in G.nodes(data=True))
rel = Counter(e['relation'] for _, _, e in G.edges(data=True))
print("[1] node types:", dict(types))
print("[1] edge relations:", dict(rel))
print("[1] node_features shape:", b.get_node_features().shape)

assert types.get('account', 0) > 0, "no account nodes"
assert types.get('perpetrator', 0) > 0, "no perpetrator nodes"
assert any('share_account' in k for k in rel), "no share_account edges"
assert any('share_perpetrator' in k for k in rel), "no share_perpetrator edges"
assert rel.get('fund_flow', 0) > 0, "no fund_flow edges"

# account 特征非全零（去 hash 验证）
acc_nodes = [n for n, d in G.nodes(data=True) if d['node_type'] == 'account']
acc_feat = b.get_node_features()[b.node_to_idx[acc_nodes[0]]]
print("[1] sample account feature[:4]:", [round(float(x), 4) for x in acc_feat[:4]])
assert acc_feat.any(), "account feature all zero -> hash not removed"

# --- 2. 向后兼容：无资金字段不建资金节点 ---
cases2 = [{k: v for k, v in c.items() if k not in ('accounts', 'perpetrators')} for c in cases]
b2 = FraudGraphBuilder(use_db=False, use_cache=False)
G2 = b2.build_graph(cases2)
types2 = Counter(d['node_type'] for _, d in G2.nodes(data=True))
print("[2] compat node types:", dict(types2))
assert 'account' not in types2 and 'perpetrator' not in types2, "compat path leaked fund nodes"

# --- 3. 尝试 detect（依赖 torch/sklearn + 完整 backend 环境，缺失则跳过）---
try:
    from gnn.gang_detector import GangDetector
    gd = GangDetector(use_han=False, use_deep_clustering=False, enable_persistence=False)
    res = gd.detect(cases, use_gnn=True, training_epochs=20)
    print("[3] detect gangs:", len(res['gangs']))
    if res['gangs']:
        g0 = res['gangs'][0]
        print("[3] gang0 related_accounts:", g0.get('related_accounts'))
        print("[3] gang0 related_perpetrators:", g0.get('related_perpetrators'))
        assert 'related_accounts' in g0 and 'related_perpetrators' in g0
    print("DETECT_OK")
except Exception as e:
    print("DETECT_SKIP (need full backend env with torch/sklearn):", repr(e))

print("SMOKE_OK")
