import sys, types, importlib.util
BACKEND = "E:/FraudLens/backend"
if "tools" not in sys.modules:
    ft = types.ModuleType("tools")
    fru = types.ModuleType("tools.redis_utils")
    fru.get_redis = lambda: None
    sys.modules["tools"] = ft
    sys.modules["tools.redis_utils"] = fru
if "core" not in sys.modules:
    fc = types.ModuleType("core")
    fc.__path__ = []
    sys.modules["core"] = fc
    fcl = types.ModuleType("core.logger")

    class _L:
        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

    fcl.logger = _L()
    sys.modules["core.logger"] = fcl
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def load(n, r):
    s = importlib.util.spec_from_file_location(n, BACKEND + "/" + r)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


gb = load("graph_builder", "gnn/graph_builder.py")
sd = load("synthetic_data", "gnn/synthetic_data.py")
import numpy as np
import torch
han = load("han_model", "gnn/han_model.py")

cases, tx, gt = sd.generate_synthetic_dataset(seed=42, n_gangs=5, cases_per_gang=8)
b = gb.FraudGraphBuilder(use_db=False, use_cache=False)
G = b.build_graph(cases, accounts_tx=tx)
feat = b.get_node_features()
meta = b.get_meta_path_adjacency()
print("metapath keys:", list(meta.keys()))
for k, v in meta.items():
    print("  %s: shape=%s nonzero=%d diag=%d" % (k, v.shape, int((v > 0).sum()), int(np.diagonal(v).sum())))

ft_t = torch.as_tensor(feat, dtype=torch.float32)
mt = {k: torch.as_tensor(v, dtype=torch.float32) for k, v in meta.items()}
model = han.FraudHAN(in_dim=feat.shape[1], hidden_dim=64, embedding_dim=32,
                      num_classes=10, num_heads=4, num_layers=2)
tr = han.GraphCLTrainer(model, temperature=0.5, learning_rate=0.001)
hist = tr.pretrain(ft_t, mt, num_epochs=20, batch_size=min(256, ft_t.shape[0]))
print("pretrain last loss:", round(hist['loss'][-1], 4))
emb = model.get_embeddings(ft_t, mt)
print("HAN embed shape:", emb.shape, "finite:", bool(np.isfinite(emb).all()))
print("HAN SMOKE OK")
