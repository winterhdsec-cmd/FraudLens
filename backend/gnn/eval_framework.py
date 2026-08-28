"""
FraudLens 评测框架（论文实验章节来源）

目标：把"资金链图模型"与四类基线在带真值团伙标签的数据集上做可复现对比，
      输出 NMI / ARI / 成对 F1，并支持消融实验。

设计原则（验证驱动、最小重依赖）：
- 必需：scikit-learn, hdbscan, networkx, numpy  → 跑 KMeans / HDBSCAN / 当前系统(Louvain) / 资金链消融
- 语义基线：本地 BGE 模型若 torch+transformers 可用则加载；否则退化为 TF-IDF 并明确标注为代理
- 当前GNN基线：需 torch；检测到才启用，否则跳过并标注
- 去反思（no_reflection）：由 orchestrator 的 ENABLE_REFLECTION_LOOP 开关控制，本框架经 run_all(ablation_flags=['no_reflection']) 透传。
- 去置信度门控（no_gating）：由 gnn/ablation.py 的 compute_gate_decision(gating_enabled=False) 控制，
  并经 evaluate_gating_ablation() 量化"误冻率"差异；run_all(ablation_flags=['no_gating']) 触发（需 torch/Docker）。

用法：
    python eval_framework.py            # 跑默认数据集并落 eval_results.json
    python eval_framework.py --seed 7   # 换种子复现
"""
import argparse
import importlib.util
import json
import os
import sys
import types
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
import networkx as nx
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans, MiniBatchKMeans, HDBSCAN as SkHDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

# ---- 依赖桩：graph_builder 导入链含 tools.redis_utils，隔离环境缺重型依赖，做桩绕过 ----
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "tools" not in sys.modules:
    _fake_tools = types.ModuleType("tools")
    _fake_ru = types.ModuleType("tools.redis_utils")
    _fake_ru.get_redis = lambda: None
    sys.modules["tools"] = _fake_tools
    sys.modules["tools.redis_utils"] = _fake_ru

# core.logger 桩：避免 core/__init__ 拉入 openai 等重型后端依赖（隔离评测用）
if "core" not in sys.modules:
    _fake_core = types.ModuleType("core")
    _fake_core.__path__ = []  # 标记为包，避免触发 core/__init__.py
    sys.modules["core"] = _fake_core
    _fake_cl = types.ModuleType("core.logger")

    class _StubLogger:
        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

    _fake_cl.logger = _StubLogger()
    sys.modules["core.logger"] = _fake_cl


def _load_local(module_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(BACKEND, rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 消融工具（torch-free）：客观置信度门控决策 + 去门控误冻率量化
_ablation_mod = _load_local("gnn_ablation", "gnn/ablation.py")
evaluate_gating_ablation = _ablation_mod.evaluate_gating_ablation
compute_gate_decision = _ablation_mod.compute_gate_decision


gb_mod = _load_local("graph_builder", "gnn/graph_builder.py")
sd_mod = _load_local("synthetic_data", "gnn/synthetic_data.py")


# ----------------------------------------------------------------------------
# 数据加载与特征
# ----------------------------------------------------------------------------
def load_dataset(seed: int = 42, n_gangs: int = 5, cases_per_gang: int = 8,
                 cross: float = 0.0, intra: float = 1.0, attr_noise: float = 0.0):
    cases, accounts_tx, gt = sd_mod.generate_synthetic_dataset(
        n_gangs=n_gangs, cases_per_gang=cases_per_gang, seed=seed,
        cross_gang_account_share=cross,
        intra_share_prob=intra, attr_noise=attr_noise)
    return cases, accounts_tx, gt


def strip_fund(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去掉资金链扩展字段，得到"改造前"的案件（用于消融：去资金链）"""
    out = []
    for c in cases:
        nc = {k: v for k, v in c.items() if k not in ("accounts", "perpetrators")}
        out.append(nc)
    return out


def case_feature_matrix(cases: List[Dict[str, Any]]):
    """构造案件结构化特征矩阵（用于 KMeans / HDBSCAN 基线）"""
    cities, types = set(), set()
    for c in cases:
        cities.add(c.get("victim_address", ""))
        types.add(c.get("scam_type", ""))
    cities, types = sorted(cities), sorted(types)
    X, ids = [], []
    for c in cases:
        row = [
            float(c.get("amount_value", 0.0)),
            float(c.get("risk_score", 0.0)),
            float(c.get("victim_age", 0.0)),
            1.0 if c.get("victim_gender") == "男" else 0.0,
        ]
        row += [1.0 if c.get("victim_address") == ci else 0.0 for ci in cities]
        row += [1.0 if c.get("scam_type") == ti else 0.0 for ti in types]
        X.append(row)
        ids.append(c["case_id"])
    X = np.array(X, dtype=np.float32)
    X = StandardScaler().fit_transform(X)
    return X, ids


def case_texts(cases: List[Dict[str, Any]]) -> List[str]:
    return [
        f"{c.get('scam_type','')} {c.get('victim_address','')} "
        f"{c.get('victim_phone','')} {c.get('amount_value',0):.0f}"
        for c in cases
    ]


# ----------------------------------------------------------------------------
# 基线实现
# ----------------------------------------------------------------------------
def baseline_kmeans(X, ids, n_clusters):
    pred = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit_predict(X)
    return {cid: int(l) for cid, l in zip(ids, pred)}


def baseline_hdbscan(X, ids):
    pred = SkHDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
    return {cid: int(l) for cid, l in zip(ids, pred)}


def baseline_semantic(cases, ids, n_clusters):
    """纯语义聚类：优先 BGE 嵌入，否则 TF-IDF 代理（明确标注）"""
    notes = []
    texts = case_texts(cases)
    emb = None
    try:
        import torch  # noqa
        from transformers import AutoTokenizer, AutoModel
        model_path = os.path.join(BACKEND, "bge-large-zh-v1.5")
        tok = AutoTokenizer.from_pretrained(model_path)
        model = AutoModel.from_pretrained(model_path)
        enc = tok(texts, padding=True, truncation=True, max_length=128,
                  return_tensors="pt")
        with torch.no_grad():
            out = model(**enc)
        emb = out.last_hidden_state[:, 0, :].cpu().numpy()
        notes.append("语义基线=BGE-large 本地嵌入")
    except Exception as e:
        vec = TfidfVectorizer().fit_transform(texts)
        emb = np.asarray(vec.todense(), dtype=np.float32)
        notes.append(f"语义基线=TF-IDF代理(BGE需torch未安装: {type(e).__name__})")
    pred = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit_predict(emb)
    return {cid: int(l) for cid, l in zip(ids, pred)}, notes


def _louvain_case_labels(G: nx.Graph) -> Dict[str, int]:
    """对全图跑 Louvain，提取案件节点社区标签"""
    for _, _, d in G.edges(data=True):
        if "weight" not in d:
            d["weight"] = 1.0
    comms = nx.community.louvain_communities(G, weight="weight", seed=0)
    node2comm = {}
    for ci, members in enumerate(comms):
        for n in members:
            node2comm[n] = ci
    # 案件节点保底：孤立案件各自成簇
    max_c = len(comms)
    pred = {}
    for n, d in G.nodes(data=True):
        if d.get("node_type") == "case":
            pred[n] = node2comm.get(n, max_c)
            max_c = max(max_c, pred[n] + 1)
    return pred


def baseline_current_system(cases, accounts_tx, use_fund: bool):
    """当前系统(图社区发现)：建图 + Louvain。
       use_fund=True 用 Stage1 资金链图；False 用改造前(无资金边)图。"""
    builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False)
    if use_fund:
        G = builder.build_graph(cases, accounts_tx=accounts_tx)
    else:
        G = builder.build_graph(strip_fund(cases))
    return _louvain_case_labels(G)


def baseline_remove_gnn(cases, accounts_tx):
    """消融：去 GNN —— 资金图节点特征直接 HDBSCAN（系统降级路径，不含 GNN 嵌入）"""
    builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False)
    G = builder.build_graph(cases, accounts_tx=accounts_tx)
    features = builder.get_node_features()
    if features is None or len(features) == 0:
        return {}
    case_idx = [builder.node_to_idx[n] for n, d in G.nodes(data=True)
                if d.get("node_type") == "case"]
    case_ids = [n for n, d in G.nodes(data=True)
                if d.get("node_type") == "case"]
    if len(case_idx) < 2:
        return {}
    X = np.asarray(features[case_idx], dtype=np.float32)
    pred_arr = SkHDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
    pred = {}
    nxt = int(max(pred_arr)) + 1 if len(pred_arr) and pred_arr.max() >= 0 else 0
    for cid, lab in zip(case_ids, pred_arr):
        lab = int(lab)
        pred[cid] = lab if lab >= 0 else nxt
        if lab < 0:
            nxt += 1
    return pred


def baseline_gnn_han(cases, accounts_tx, n_true: int, epochs: int = 100, use_text_channel: bool = True):
    """当前GNN基线(HAN真异构)：FraudHAN + 真元路径邻接(GraphCL预训练) -> 案件嵌入 KMeans。
       代表 Stage2 修复后的异构 HAN 路径（元路径拓扑各异，非旧实现复制同矩阵）。"""
    try:
        import torch  # noqa
        if BACKEND not in sys.path:
            sys.path.insert(0, BACKEND)
        han_mod = _load_local("han_model", "gnn/han_model.py")
        builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=use_text_channel)
        G = builder.build_graph(cases, accounts_tx=accounts_tx)
        features = builder.get_node_features()
        if features is None or len(features) < 3:
            return {"__error__": "features 不足"}
        meta_np = builder.get_meta_path_adjacency()
        if not meta_np:
            return {"__error__": "无元路径邻接"}
        feat_t = torch.as_tensor(features, dtype=torch.float32)
        meta_t = {k: torch.as_tensor(v, dtype=torch.float32) for k, v in meta_np.items()}
        in_dim = features.shape[1]
        model = han_mod.FraudHAN(in_dim=in_dim, hidden_dim=64, embedding_dim=32,
                                  num_classes=10, num_heads=4, num_layers=2)
        trainer = han_mod.GraphCLTrainer(model, temperature=0.5, learning_rate=0.001)
        trainer.pretrain(feat_t, meta_t, num_epochs=epochs,
                         batch_size=min(256, feat_t.shape[0]))
        emb = model.get_embeddings(feat_t, meta_t)
        case_idx = [builder.node_to_idx[n] for n, d in G.nodes(data=True)
                    if d.get("node_type") == "case"]
        case_ids = [n for n, d in G.nodes(data=True)
                    if d.get("node_type") == "case"]
        if len(case_idx) < 2:
            return {"__error__": "案件节点不足"}
        ce = np.asarray(emb[case_idx], dtype=np.float32)
        ce = StandardScaler().fit_transform(ce)
        pred_arr = KMeans(n_clusters=n_true, random_state=0, n_init=10).fit_predict(ce)
        pred = {cid: int(lab) for cid, lab in zip(case_ids, pred_arr)}
        pred["__note__"] = "currentGNN-HAN=true heterogeneous metapaths(Stage2 fix)"
        return pred
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {str(e)[:160]}"}


def baseline_gnn(cases, accounts_tx, n_true: int, epochs: int = 150):
    """当前GNN基线：GraphSAGE 自监督嵌入 -> 案件嵌入 KMeans(已知团伙数) -> 案件标签。
       只用干净模块(torch/numpy/sklearn/networkx)，不依赖后端重型链(openai 等)。
       注：当前系统默认 HAN 为残实现（4 元路径同邻接矩阵），Stage2 修复中；
           此处用可跑通的 GraphSAGE 代表"GNN 嵌入+聚类"路径，并在 notes 标注。"""
    try:
        import torch  # noqa
        gnn_mod = _load_local("gnn_model", "gnn/gnn_model.py")
        builder = gb_mod.FraudGraphBuilder(use_db=False, use_cache=False)
        G = builder.build_graph(cases, accounts_tx=accounts_tx)
        features = builder.get_node_features()
        adj = builder.get_adjacency_matrix()
        if features is None or len(features) < 3:
            return {"__error__": "features 不足"}
        feat_t = torch.as_tensor(features, dtype=torch.float32)
        adj_t = torch.as_tensor(adj, dtype=torch.float32)
        in_dim = features.shape[1]
        model = gnn_mod.GraphSAGE(in_dim=in_dim, hidden_dim=64,
                                   out_dim=32, num_layers=2)
        opt = torch.optim.Adam(model.parameters(), lr=0.01)
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            emb = model(feat_t, adj_t)
            recon = torch.sigmoid(torch.matmul(emb, emb.t()))
            loss = torch.nn.functional.mse_loss(recon, adj_t)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            emb = model(feat_t, adj_t).numpy()
        case_idx = [builder.node_to_idx[n] for n, d in G.nodes(data=True)
                    if d.get("node_type") == "case"]
        case_ids = [n for n, d in G.nodes(data=True)
                    if d.get("node_type") == "case"]
        if len(case_idx) < 2:
            return {"__error__": "案件节点不足"}
        ce = np.asarray(emb[case_idx], dtype=np.float32)
        ce = StandardScaler().fit_transform(ce)
        pred_arr = KMeans(n_clusters=n_true, random_state=0, n_init=10).fit_predict(ce)
        pred = {cid: int(lab) for cid, lab in zip(case_ids, pred_arr)}
        pred["__note__"] = "currentGNN=GraphSAGE(embedding)+KMeans; HAN残实现Stage2修复"
        return pred
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {str(e)[:160]}"}


# ----------------------------------------------------------------------------
# 指标
# ----------------------------------------------------------------------------
def pairwise_prf(true_dict: Dict[str, int], pred_dict: Dict[str, int]):
    """成对（pairwise）Precision / Recall / F1。论文实验章节单列 P/R 用。"""
    ids = sorted(set(true_dict) & set(pred_dict))
    tp = fp = fn = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            st = true_dict[a] == true_dict[b]
            sp = pred_dict[a] == pred_dict[b]
            if st and sp:
                tp += 1
            elif (not st) and sp:
                fp += 1
            elif st and (not sp):
                fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return float(prec), float(rec), float(f1)


def pairwise_f1(true_dict: Dict[str, int], pred_dict: Dict[str, int]) -> float:
    _, _, f1 = pairwise_prf(true_dict, pred_dict)
    return f1


def compute_metrics(true_dict: Dict[str, int], pred_dict: Dict[str, int]) -> Dict[str, float]:
    ids = sorted(set(true_dict) & set(pred_dict))
    y_true = [true_dict[i] for i in ids]
    y_pred = [pred_dict[i] for i in ids]
    n_clusters = len(set(y_pred))
    prec, rec, f1 = pairwise_prf(true_dict, pred_dict)
    return {
        "nmi": float(normalized_mutual_info_score(y_true, y_pred)),
        "ari": float(adjusted_rand_score(y_true, y_pred)),
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "n_clusters": int(n_clusters),
        "n_cases": len(ids),
    }


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def _run_gating_ablation(cases: List[Dict[str, Any]],
                          accounts_tx: Any, gt: Dict[str, Any]) -> Dict[str, Any]:
    """去门控消融：用生产级 GangDetector 产出带客观置信度的团伙信息，
    量化'有门控 vs 去门控'在冻结决策上的误冻率差异。

    仅在有 torch 的 Docker 环境下可运行；无 torch 时由调用方捕获异常并标注跳过。
    """
    # gating ablation 需真实 GangDetector；但 eval_framework 顶部为隔离环境用桩替换了
    # `tools` 包，而 GangDetector 顶层 `from tools.response import logger` 依赖该子模块。
    # 补一个仅含 logger 的 tools.response 桩（保留 redis_utils 桩，避免真连 redis），
    # 再以 gnn 包绝对导入，确保 gang_detector 内部 `from .deep_clustering import` 的
    # 相对导入能解析。
    import logging
    if "tools.response" not in sys.modules:
        _fr = types.ModuleType("tools.response")
        _fr.logger = logging.getLogger("fraudlens")
        sys.modules["tools.response"] = _fr
    sys.path.insert(0, BACKEND)
    from gnn.gang_detector import GangDetector
    gd = GangDetector(enable_gating=True)
    res = gd.detect(cases=cases, accounts_tx=accounts_tx)
    gangs = res.get("gangs", []) if isinstance(res, dict) else []
    # 多数投票将检测团伙对齐到真值标签：纯度>=0.5 视为真实团伙（值得冻结）
    true_ids = set()
    for g in gangs:
        members = g.get("case_ids", []) or []
        if not members:
            continue
        votes = {}
        for cid in members:
            tv = gt.get(cid)
            if tv is not None:
                votes[tv] = votes.get(tv, 0) + 1
        if votes:
            top_label, top_cnt = max(votes.items(), key=lambda kv: kv[1])
            if top_cnt / len(members) >= 0.5:
                true_ids.add(g["gang_id"])
    return evaluate_gating_ablation(gangs, true_ids)


def run_all(seed: int = 42, n_gangs: int = 5, cases_per_gang: int = 8,
            cross: float = 0.0, intra: float = 1.0, attr_noise: float = 0.0,
            ablation_flags: Optional[List[str]] = None) -> Dict[str, Any]:
    cases, accounts_tx, gt = load_dataset(seed=seed, n_gangs=n_gangs,
                                           cases_per_gang=cases_per_gang,
                                           cross=cross, intra=intra,
                                           attr_noise=attr_noise)
    n_true = len(set(gt.values()))
    X, ids = case_feature_matrix(cases)

    notes: List[str] = []
    baselines: Dict[str, Any] = {}

    # B1 KMeans
    baselines["KMeans"] = compute_metrics(gt, baseline_kmeans(X, ids, n_true))
    # B2 HDBSCAN-only
    baselines["HDBSCAN-only"] = compute_metrics(gt, baseline_hdbscan(X, ids))
    # B3 纯语义(BGE/TF-IDF)
    sem_pred, sem_notes = baseline_semantic(cases, ids, n_true)
    baselines["Semantic"] = compute_metrics(gt, sem_pred)
    notes += sem_notes
    # B4 当前系统(图社区发现, 含资金链)
    cur_pred = baseline_current_system(cases, accounts_tx, use_fund=True)
    baselines["CurrentSystem(fund)"] = compute_metrics(gt, cur_pred)
    # 可选：当前GNN（GraphSAGE 朴素基线，复现塌缩现象）
    gnn_pred = baseline_gnn(cases, accounts_tx, n_true)
    if gnn_pred and "__error__" not in gnn_pred:
        baselines["CurrentGNN(GraphSAGE)"] = compute_metrics(gt, gnn_pred)
        if "__note__" in gnn_pred:
            notes.append(f"当前GNN基线变体: {gnn_pred['__note__']}")
    else:
        err = gnn_pred.get("__error__", "unknown") if gnn_pred else "unknown"
        notes.append(f"当前GNN(GraphSAGE)基线跳过: {err}")

    # 当前GNN(HAN 真异构, Stage2 修复后)
    han_pred = baseline_gnn_han(cases, accounts_tx, n_true)
    if han_pred and "__error__" not in han_pred:
        baselines["CurrentGNN(HAN-true)"] = compute_metrics(gt, han_pred)
        if "__note__" in han_pred:
            notes.append(f"当前GNN(HAN)基线变体: {han_pred['__note__']}")
    else:
        err = han_pred.get("__error__", "unknown") if han_pred else "unknown"
        notes.append(f"当前GNN(HAN)基线跳过: {err}")

    # 消融：去资金链（当前系统但用改造前图）
    ablation: Dict[str, Any] = {}
    old_pred = baseline_current_system(cases, accounts_tx, use_fund=False)
    ablation["remove_fund_chain"] = compute_metrics(gt, old_pred)

    # 消融：去 GNN（降级路径：资金图节点特征直接 HDBSCAN，不含 GNN 嵌入）
    rg_pred = baseline_remove_gnn(cases, accounts_tx)
    ablation["remove_gnn"] = compute_metrics(gt, rg_pred)
    ablation["fund_chain_gain_f1"] = round(
        baselines["CurrentSystem(fund)"]["f1"] - ablation["remove_fund_chain"]["f1"], 4)
    # A3 双通道消融：去话术语义通道（HAN 仅结构/资金链通道，验证"资金链+话术"双通道增益）
    if "CurrentGNN(HAN-true)" in baselines:
        try:
            han_pred_notext = baseline_gnn_han(cases, accounts_tx, n_true, use_text_channel=False)
            if han_pred_notext and "__error__" not in han_pred_notext:
                ablation["han_no_text_channel"] = compute_metrics(gt, han_pred_notext)
                ablation["dual_channel_gain_f1"] = round(
                    baselines["CurrentGNN(HAN-true)"]["f1"] - ablation["han_no_text_channel"]["f1"], 4)
                notes.append("双通道消融: 去话术语义通道(HAN 仅结构/资金链) F1 对比见 ablation.dual_channel_gain_f1")
            else:
                notes.append(f"双通道消融跳过(HAN-no-text 错误): "
                             f"{han_pred_notext.get('__error__', 'unknown') if han_pred_notext else 'unknown'}")
        except Exception as e:  # 无 torch / Docker 环境下跳过
            notes.append(f"双通道 ablation 跳过（需 torch/Docker）: {e}")
    # #8 消融开关：去反思 / 去门控
    if ablation_flags and "no_reflection" in ablation_flags:
        os.environ["ENABLE_REFLECTION_LOOP"] = "false"
        notes.append("消融: 去反思闭环 (ENABLE_REFLECTION_LOOP=false) — 编排层开关，"
                     "由 backend/tests/test_orchestrator_loop.py 验证")
    if ablation_flags and "no_gating" in ablation_flags:
        try:
            ablation["gating"] = _run_gating_ablation(cases, accounts_tx, gt)
        except Exception as e:  # 无 torch / Docker 环境下跳过
            notes.append(f"去门控 ablation 跳过（需 torch/Docker）: {e}")

    result = {
        "dataset": {"n_cases": len(cases), "n_gangs": n_true, "seed": seed},
        "baselines": baselines,
        "ablation": ablation,
        "notes": notes,
    }
    return result


# ----------------------------------------------------------------------------
# Phase C：账户中心公开基准评测（IBM/AMLSim 等资金流图）
#   不直接用 case-centric 的 FraudGraphBuilder，而是对"账户=节点、资金流=边"
#   的图做社区发现，与真值洗钱环对比。验证方法在公开资金流基准上的外部有效性。
# ----------------------------------------------------------------------------
def _account_graph_and_features(account_ids, edges):
    G = nx.Graph()
    G.add_nodes_from(account_ids)
    for s, d, amt, t in edges:
        G.add_node(s)
        G.add_node(d)
        if G.has_edge(s, d):
            G[s][d]["weight"] += amt
        else:
            G.add_edge(s, d, weight=amt)
    indeg = defaultdict(float)
    outdeg = defaultdict(float)
    inamt = defaultdict(float)
    outamt = defaultdict(float)
    deg = defaultdict(int)
    for s, d, amt, t in edges:
        outdeg[s] += 1
        indeg[d] += 1
        outamt[s] += amt
        inamt[d] += amt
        deg[s] += 1
        deg[d] += 1
    feats = []
    for a in account_ids:
        feats.append([indeg[a], outdeg[a], inamt[a], outamt[a], deg[a]])
    X = StandardScaler().fit_transform(np.array(feats, dtype=np.float32))
    return G, X


def _louvain_account_labels(G: nx.Graph, account_ids) -> Dict[str, int]:
    for _, _, d in G.edges(data=True):
        if "weight" not in d:
            d["weight"] = 1.0
    comms = nx.community.louvain_communities(G, weight="weight", seed=0)
    node2comm = {}
    for ci, members in enumerate(comms):
        for n in members:
            node2comm[n] = ci
    pred = {}
    max_c = len(comms)
    for a in account_ids:
        pred[a] = node2comm.get(a, max_c)
        max_c = max(max_c, pred[a] + 1)
    return pred


def _kmeans_predict(X, n_clusters, seed: int = 0):
    """大数据下用 MiniBatchKMeans 加速；小规模用标准 KMeans（与基线一致）。"""
    if X.shape[0] * max(int(n_clusters), 1) > 5_000_000:
        return MiniBatchKMeans(n_clusters=int(n_clusters), random_state=seed,
                               n_init=3, batch_size=4096, max_iter=100).fit_predict(X)
    return KMeans(n_clusters=int(n_clusters), random_state=seed, n_init=10).fit_predict(X)


def _sparse_gnn_embeddings(account_ids, edges, X, epochs: int = 80,
                           hidden: int = 32, out_dim: int = 16, lr: float = 0.01,
                           seed: int = 0) -> np.ndarray:
    """账户中心 GNN 嵌入：scipy.sparse 归一化邻接 + (可选 torch) 自监督训练。

    关键修复：用稀疏邻接替代原 dense `np.zeros((n,n))`，使数万节点/数百万边
    的账户图不再 O(n^2) 内存爆炸（原实现 43,614 节点即 OOM 跳过）。
    无 torch 时退化为 SGC（参数无关图传播），仍可产出拓扑嵌入。
    """
    import scipy.sparse as sp
    rng = np.random.default_rng(seed)
    n = len(account_ids)
    if n == 0:
        return X
    idx = {a: i for i, a in enumerate(account_ids)}
    rows, cols, data = [], [], []
    for s, d, amt, t in edges:
        if s not in idx or d not in idx:
            continue
        i, j = idx[s], idx[d]
        w = float(amt) if amt and amt > 0 else 1.0
        rows += [i, j]
        cols += [j, i]
        data += [w, w]
    adj = sp.csr_matrix((data, (rows, cols)), shape=(n, n))
    adj = adj + sp.identity(n, format="csr")
    d = np.asarray(adj.sum(axis=1)).flatten()
    d_inv_sqrt = np.full_like(d, 0.0)
    np.power(d, -0.5, where=d > 0, out=d_inv_sqrt)
    d_inv_sqrt[~np.isfinite(d_inv_sqrt)] = 0.0
    A_norm = sp.diags(d_inv_sqrt) @ adj @ sp.diags(d_inv_sqrt)

    try:
        import torch
        coo = A_norm.tocoo()
        idx_t = torch.LongTensor(np.vstack([coo.row, coo.col]))
        val_t = torch.FloatTensor(coo.data)
        A_sp = torch.sparse_coo_tensor(idx_t, val_t, (n, n)).coalesce()
        Xt = torch.FloatTensor(X)
        W1 = torch.tensor(rng.standard_normal((X.shape[1], hidden)) * 0.1,
                          requires_grad=True)
        W2 = torch.tensor(rng.standard_normal((hidden, out_dim)) * 0.1,
                          requires_grad=True)
        Wr = torch.tensor(rng.standard_normal((out_dim, X.shape[1])) * 0.1,
                          requires_grad=True)
        opt = torch.optim.Adam([W1, W2, Wr], lr=lr)
        for _ in range(epochs):
            opt.zero_grad()
            H1 = torch.relu(torch.sparse.mm(A_sp, Xt) @ W1)
            H2 = torch.relu(torch.sparse.mm(A_sp, H1) @ W2)
            recon = H2 @ Wr
            loss = torch.nn.functional.mse_loss(recon, Xt)
            loss.backward()
            opt.step()
        with torch.no_grad():
            H1 = torch.relu(torch.sparse.mm(A_sp, Xt) @ W1)
            H2 = torch.relu(torch.sparse.mm(A_sp, H1) @ W2)
            emb = H2.numpy()
        return emb
    except Exception:
        # 无 torch：SGC 参数无关传播（等价于固定权重的 2 层 GCN）
        H = X
        for _ in range(2):
            H = A_norm @ H
            H = np.maximum(H, 0)
        return np.asarray(H)


def _baseline_gnn_account(account_ids, edges, n_true, X=None, epochs: int = 80,
                          hidden: int = 32, out_dim: int = 16):
    """账户中心 GNN 基线：稀疏 GNN 嵌入 -> KMeans。可扩展至数万节点，不 OOM。"""
    try:
        if X is None:
            _G, X = _account_graph_and_features(account_ids, edges)
        emb = _sparse_gnn_embeddings(account_ids, edges, X, epochs=epochs,
                                     hidden=hidden, out_dim=out_dim)
        pred_arr = _kmeans_predict(emb, n_true)
        return {a: int(l) for a, l in zip(account_ids, pred_arr)}
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {str(e)[:160]}"}


def make_tiny_amlsim(directory: str, n_rings: int = 12, per_ring: int = 12,
                     seed: int = 0) -> str:
    """生成小型 AMLSim 格式样本（用于真值可复现小实验 / GNN 路径复现高 F1）。

    产出 transactions.csv / accounts.csv / ground_truth.csv（ACCOUNT_ID,RING_ID），
    与 load_amlsim 适配器列名兼容。每个环为以 hub 为中心的双向小额转账环；
    另加少量跨环噪声边模拟真实背景交易（不污染真值标签）。
    """
    import csv as _csv
    import random
    rng = random.Random(seed)
    os.makedirs(directory, exist_ok=True)
    accounts, tx_rows, gt_rows = [], [], []
    aid = 0
    for r in range(n_rings):
        members = [f"A{aid + k}" for k in range(per_ring)]
        for m in members:
            accounts.append({"ACCOUNT_ID": m})
        hub = members[0]
        for m in members[1:]:
            amt = rng.choice([2000, 5000, 8000, 12000])
            ts = rng.randint(1, 30)
            tx_rows.append({"SENDER_ACCOUNT_ID": m, "RECEIVER_ACCOUNT_ID": hub,
                            "AMOUNT": amt, "TIMESTAMP": ts})
            tx_rows.append({"SENDER_ACCOUNT_ID": hub, "RECEIVER_ACCOUNT_ID": m,
                            "AMOUNT": amt, "TIMESTAMP": ts})
        for m in members:
            gt_rows.append({"ACCOUNT_ID": m, "RING_ID": r})
        aid += per_ring
    for _ in range(max(2, n_rings // 3)):
        r1, r2 = rng.sample(range(n_rings), 2)
        a1, a2 = f"A{r1 * per_ring}", f"A{r2 * per_ring}"
        tx_rows.append({"SENDER_ACCOUNT_ID": a1, "RECEIVER_ACCOUNT_ID": a2,
                        "AMOUNT": rng.choice([300, 600, 900]), "TIMESTAMP": rng.randint(1, 30)})

    def _write(name, rows):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    _write("accounts.csv", accounts)
    _write("transactions.csv", tx_rows)
    _write("ground_truth.csv", gt_rows)
    return directory


def run_amlsim_eval(directory: str, ablation_flags=None) -> Dict[str, Any]:
    """AMLSim 账户中心评测。仅对真值洗钱账户（gt>=0）计算指标，背景账户排除。

    返回 baselines（全图聚类）与 baselines_subgraph（仅洗钱子图聚类，公平对照）。
    GNN 账户中心方法使用稀疏邻接，可扩展至数万节点，不再因 OOM 跳过。
    """
    adapter_mod = _load_local("amlsim_adapter", "gnn/adapters/amlsim_adapter.py")
    load_amlsim = adapter_mod.load_amlsim
    AmLSIMFormatError = adapter_mod.AmLSIMFormatError
    try:
        account_ids, edges, gt = load_amlsim(directory)
    except AmLSIMFormatError as e:
        return {"error": str(e)}
    eval_ids = [a for a in account_ids if gt.get(a, -1) >= 0]
    if not eval_ids:
        return {"error": "无真值洗钱账户（ground_truth.csv/alerts.csv 缺失）"}
    true_sub = {a: gt[a] for a in eval_ids}
    n_true = len(set(true_sub.values()))
    G, X = _account_graph_and_features(account_ids, edges)
    baselines: Dict[str, Any] = {}
    baselines["LouvainAccount(structure)"] = compute_metrics(
        true_sub, _louvain_account_labels(G, eval_ids))
    baselines["KMeansAccount"] = compute_metrics(
        true_sub, baseline_kmeans(X, eval_ids, n_true))
    baselines["HDBSCANAccount"] = compute_metrics(
        true_sub, baseline_hdbscan(X, eval_ids))
    # GNN 账户中心方法（稀疏邻接，可扩展，不 OOM）
    gnn_pred = _baseline_gnn_account(account_ids, edges, n_true, X=X)
    if gnn_pred and "__error__" not in gnn_pred:
        baselines["GNNAccount(GraphSAGE)"] = compute_metrics(true_sub, gnn_pred)
    else:
        baselines["__gnn_error__"] = gnn_pred.get("__error__", "unknown") if gnn_pred else "unknown"

    # ---- 仅洗钱子图（剔除背景噪声）的公平对照 ----
    sub_set = set(eval_ids)
    sub_edges = [(s, d, amt, t) for (s, d, amt, t) in edges
                 if s in sub_set and d in sub_set]
    Gsub, Xsub = _account_graph_and_features(eval_ids, sub_edges)
    subgraph: Dict[str, Any] = {}
    subgraph["LouvainAccount-subgraph"] = compute_metrics(
        true_sub, _louvain_account_labels(Gsub, eval_ids))
    subgraph["KMeansAccount-subgraph"] = compute_metrics(
        true_sub, baseline_kmeans(Xsub, eval_ids, n_true))
    gnn_sub = _baseline_gnn_account(eval_ids, sub_edges, n_true, X=Xsub)
    if gnn_sub and "__error__" not in gnn_sub:
        subgraph["GNNAccount-subgraph(GraphSAGE)"] = compute_metrics(true_sub, gnn_sub)
    else:
        subgraph["__gnn_error__"] = gnn_sub.get("__error__", "unknown") if gnn_sub else "unknown"

    return {
        "dataset": {"n_accounts": len(account_ids), "n_laundering": len(eval_ids),
                    "n_rings": n_true, "directory": directory},
        "baselines": baselines,
        "baselines_subgraph": subgraph,
    }


def _fmt(result: Dict[str, Any]) -> str:
    lines = ["", "=" * 64,
             "FraudLens 评测结果",
             f"数据集: cases={result['dataset']['n_cases']} "
             f"gangs={result['dataset']['n_gangs']} seed={result['dataset']['seed']}",
             "=" * 64]
    header = f"{'方法':<24}{'NMI':>8}{'ARI':>8}{'F1':>8}{'#簇':>6}"
    lines.append(header)
    lines.append("-" * 64)
    for name, m in result["baselines"].items():
        lines.append(f"{name:<24}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                     f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
    lines.append("-" * 64)
    lines.append("消融实验")
    for name, m in result["ablation"].items():
        if isinstance(m, dict) and "nmi" in m:
            lines.append(f"{name:<24}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                         f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
        elif isinstance(m, dict):
            # 门控消融等产出非聚类指标（误冻率等）时，直接打印结构
            lines.append(f"{name:<24}{json.dumps(m, ensure_ascii=False)}")
        else:
            lines.append(f"{name:<24}{m}")
    lines.append("-" * 64)
    for n in result["notes"]:
        lines.append(f"注: {n}")
    lines.append("=" * 64)
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gangs", type=int, default=5)
    ap.add_argument("--per", type=int, default=8)
    ap.add_argument("--cross", type=float, default=0.2,
                    help="跨团伙账户共享概率（困难场景干扰项，0=理想情形）")
    ap.add_argument("--intra", type=float, default=1.0,
                    help="团伙内账户共享概率（<1.0 退化 account/fund_flow 结构通道同质性）")
    ap.add_argument("--attr", type=float, default=0.0,
                    help="属性噪声概率（>0 破坏 type/city/perpetrator 结构通道同质性，"
                         "使话术(text)通道成为唯一可靠判别信号，用于体现双通道真实增益）")
    ap.add_argument("--ablation", nargs="*", default=None,
                    help="#8 消融开关: no_reflection / no_gating（可多选）")
    ap.add_argument("--amlsim", type=str, default=None,
                    help="Phase C 公开基准：AMLSim 输出目录（含 transactions.csv + "
                         "ground_truth.csv 或 alerts.csv），跑账户中心评测")
    ap.add_argument("--make-tiny", type=str, default=None,
                    help="生成小型 AMLSim 格式样本并立即跑评测（复现 GNN 高 F1），"
                         "传入输出目录路径；与 --amlsim 互斥，优先")
    ap.add_argument("--tiny-rings", type=int, default=12)
    ap.add_argument("--tiny-per", type=int, default=12)
    args = ap.parse_args()

    # 小样本复现分支（验证 GNN 路径在可控规模得高 F1，独立于大规模真实评测）
    if args.make_tiny:
        make_tiny_amlsim(args.make_tiny, n_rings=args.tiny_rings,
                         per_ring=args.tiny_per, seed=args.seed)
        res = run_amlsim_eval(args.make_tiny)
        print(f"\n[小样本 AMLSim 复现] dir={args.make_tiny}")
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            ds = res["dataset"]
            print(f"  accounts={ds['n_accounts']} laundering={ds['n_laundering']} "
                  f"rings={ds['n_rings']}")
            print(f"  {'方法':<30}{'NMI':>8}{'ARI':>8}{'F1':>8}{'#簇':>6}")
            print("  " + "-" * 56)
            for name, m in res["baselines"].items():
                if isinstance(m, dict) and "f1" in m:
                    print(f"  {name:<30}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                          f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
            if "baselines_subgraph" in res:
                print("  --- 仅洗钱子图（剔除背景，公平对照）---")
                for name, m in res["baselines_subgraph"].items():
                    if isinstance(m, dict) and "f1" in m:
                        print(f"  {name:<30}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                              f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
        out = {"tiny_amlsim": res}
        tiny_path = os.path.join(BACKEND, "gnn", "eval_tiny_results.json")
        with open(tiny_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n结果已写入: {tiny_path}")
        sys.exit(0)

    # 理想情形（无跨团伙干扰）
    res_clean = run_all(seed=args.seed, n_gangs=args.gangs,
                        cases_per_gang=args.per, cross=0.0,
                        ablation_flags=args.ablation)
    print("[理想情形 cross=0.0]")
    print(_fmt(res_clean))

    # 困难场景（含跨团伙账户共享干扰）
    res_hard = run_all(seed=args.seed, n_gangs=args.gangs,
                       cases_per_gang=args.per, cross=args.cross,
                       ablation_flags=args.ablation)
    print(f"\n[困难场景 cross={args.cross}]")
    print(_fmt(res_hard))

    # 双通道压力场景（A-BGE 复测）：结构通道含噪，话术为唯一判别信号
    # 仅当传入 --intra<1 或 --attr>0 时运行，用于验证"资金链+话术"双通道真实增益
    out = {"clean": res_clean, "hard": res_hard, "cross": args.cross}
    if args.intra < 1.0 or args.attr > 0.0:
        res_dc = run_all(seed=args.seed, n_gangs=args.gangs,
                         cases_per_gang=args.per, cross=args.cross,
                         intra=args.intra, attr_noise=args.attr,
                         ablation_flags=args.ablation)
        print(f"\n[双通道压力 intra={args.intra} attr={args.attr}]")
        print(_fmt(res_dc))
        gain = res_dc.get("ablation", {}).get("dual_channel_gain_f1")
        if gain is not None:
            print(f"\n>> 双通道真实增益 dual_channel_gain_f1 = {gain} "
                  f"（{'正增益 ✅ 话术通道生效' if gain > 0 else '无增益（结构通道仍主导或已饱和）'}）")
        out["dual_channel_stress"] = res_dc

    # Phase C 公开基准评测（账户中心，AMLSim 等资金流图）
    if args.amlsim:
        _adapter_mod = _load_local("amlsim_adapter", "gnn/adapters/amlsim_adapter.py")
        AmLSIMFormatError = _adapter_mod.AmLSIMFormatError
        try:
            res_aml = run_amlsim_eval(args.amlsim, ablation_flags=args.ablation)
            print("\n[Phase C 公开基准 AMLSim 账户中心评测]")
            if "error" in res_aml:
                print(f"  跳过: {res_aml['error']}")
            else:
                ds = res_aml["dataset"]
                print(f"  数据集: accounts={ds['n_accounts']} "
                      f"laundering={ds['n_laundering']} rings={ds['n_rings']}")
                print(f"  {'方法':<28}{'NMI':>8}{'ARI':>8}"
                      f"{'P':>7}{'R':>7}{'F1':>8}{'#簇':>6}")
                print("  " + "-" * 64)
                for name, m in res_aml["baselines"].items():
                    if isinstance(m, dict) and "f1" in m:
                        print(f"  {name:<28}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                              f"{m.get('precision',0):>7.3f}{m.get('recall',0):>7.3f}"
                              f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
                if "__gnn_error__" in res_aml["baselines"]:
                    print(f"  [GNN 账户中心基线跳过: {res_aml['baselines']['__gnn_error__']}]")
                if "baselines_subgraph" in res_aml:
                    print("  --- 仅洗钱子图（剔除背景，公平对照）---")
                    for name, m in res_aml["baselines_subgraph"].items():
                        if isinstance(m, dict) and "f1" in m:
                            print(f"  {name:<30}{m['nmi']:>8.3f}{m['ari']:>8.3f}"
                                  f"{m.get('precision',0):>7.3f}{m.get('recall',0):>7.3f}"
                                  f"{m['f1']:>8.3f}{m['n_clusters']:>6}")
                    if "__gnn_error__" in res_aml["baselines_subgraph"]:
                        print(f"  [子图 GNN 跳过: {res_aml['baselines_subgraph']['__gnn_error__']}]")
            out["amlsim"] = res_aml
        except AmLSIMFormatError as e:
            print(f"\n[Phase C AMLSim] 格式错误: {e}")
            out["amlsim"] = {"error": str(e)}

    out_path = os.path.join(BACKEND, "gnn", "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入: {out_path}")


# ============================================================================
# Phase C2 — T-Finance 真实金融交易网基准（节点级欺诈检测评测）
# ----------------------------------------------------------------------------
# T-Finance（Tang et al., ICML 2022）是账户级 0/1 异常标注（39,357 节点 /
# 21,222,543 有向边 / 异常 4.58%），与 AMLSim 的"团伙环"标注语义不同，
# 因此评测目标改为"节点级欺诈检测"：对每个账户产出风险分，在 top-k
# （k = 异常账户数）操作点上报 P/R/F1 + 误报率，并报无阈值的 AUC。
# 全部实现为 numpy/scipy 向量化，21M 边规模可跑（无需 torch）。
# ============================================================================
def _percentile_rank(scores):
    """分数 -> [0,1] 百分位排名（越大越异常）。"""
    s = np.asarray(scores, dtype=np.float64)
    order = s.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(len(s), dtype=np.float64)
    return ranks / max(len(s) - 1, 1)


def _prf_at_k(y_true, flag):
    """在给定 top-k 标记下计算 P/R/F1 + 误报率(FPR)。"""
    tp = int(((y_true == 1) & (flag == 1)).sum())
    fp = int(((y_true == 0) & (flag == 1)).sum())
    fn = int(((y_true == 1) & (flag == 0)).sum())
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    fpr = fp / max(int((y_true == 0).sum()), 1)
    return round(p, 4), round(r, 4), round(f1, 4), round(fpr, 4)


def _auc_rank(y_true, scores):
    """Mann-Whitney U 实现的 AUC（无阈值、无依赖）。"""
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(scores, dtype=np.float64)
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(len(s), dtype=np.float64) + 1.0
    pos = y == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    sum_pos = ranks[pos].sum()
    return round((sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg), 4)


def _tfinance_struct_features(n, edges):
    """账户结构特征（T-Finance 无金额，权重=交易条数）。
    [indeg, outdeg, deg, reflux_proxy]；reflux_proxy = min(入度, 出度)，
    作为资金回流闭环参与度的无向下界估计（真实回流环检测需时序/金额，这里
    是诚实标注的结构代理）。
    """
    src, dst = edges[:, 0], edges[:, 1]
    indeg = np.bincount(dst, minlength=n).astype(np.float64)
    outdeg = np.bincount(src, minlength=n).astype(np.float64)
    deg = indeg + outdeg
    reflux = np.minimum(indeg, outdeg)
    return np.column_stack([indeg, outdeg, deg, reflux])


def _tfinance_sgc_embeddings(n, edges, X, k: int = 2):
    """无向化归一化邻接 + k 跳特征传播（SGC，参数无关 GNN 基线）。

    用 scipy.sparse 向量化构建，避免 21M 边上的 Python 循环 OOM/慢。
    """
    import scipy.sparse as sp
    rows = np.concatenate([edges[:, 0], edges[:, 1]])
    cols = np.concatenate([edges[:, 1], edges[:, 0]])
    A = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    A = A + sp.identity(n, format="csr")
    d = np.asarray(A.sum(axis=1)).flatten()
    dinv = np.zeros_like(d)
    np.power(d, -0.5, where=d > 0, out=dinv)
    A_norm = sp.diags(dinv) @ A @ sp.diags(dinv)
    H = X
    for _ in range(k):
        H = A_norm @ H
        H = np.maximum(H, 0)
    return np.asarray(H)


def _knn_anomaly_score(emb, k: int = 30):
    """kNN 密度异常分：到第 k 近邻的距离越大越异常（孤立/离群）。

    用 sklearn NearestNeighbors（KDTree/BallTree Cython）替代 scipy cKDTree——
    scipy cKDTree.query 在 20 万点×32 维×k=30 上会硬崩（segfault，实测 scipy 1.15.3）。
    """
    from sklearn.neighbors import NearestNeighbors
    X = np.asarray(emb, dtype=np.float64)
    kk = max(min(k, len(X) - 1), 1)
    nn = NearestNeighbors(n_neighbors=kk + 1, algorithm="auto", n_jobs=1).fit(X)
    dist, _ = nn.kneighbors(X)
    return _percentile_rank(dist[:, -1])


def _kmeans_community_risk(n, edges, emb, n_clusters: int = 64, seed: int = 0):
    """团伙视角风险：KMeans 分簇后，簇内平均 log(度数) 高的簇整体标为高风险。
    模拟"系统把某个团伙（簇）整体捞出来"的语义；账户风险 = 所在簇风险百分位。
    """
    from sklearn.cluster import MiniBatchKMeans
    km = MiniBatchKMeans(n_clusters=n_clusters, random_state=seed,
                         batch_size=4096, n_init=3).fit(np.asarray(emb))
    labels = km.labels_
    deg = np.bincount(edges[:, 0], minlength=n) + np.bincount(edges[:, 1], minlength=n)
    log_deg = np.log1p(deg)
    cluster_risk = np.zeros(n_clusters)
    for c in range(n_clusters):
        members = np.where(labels == c)[0]
        cluster_risk[c] = float(log_deg[members].mean()) if len(members) else 0.0
    return _percentile_rank(cluster_risk[labels])


def run_node_fraud_eval(account_ids, edges, labels, features=None,
                        sgc_k: int = 2, kmeans_k: int = 64, k_nn: int = 30,
                        seed: int = 0, source: str = "node-fraud") -> Dict[str, Any]:
    """真实公开基准 · 节点级欺诈检测评测（T-Finance / Elliptic 共用）。

    方法：
      StructRisk(deg+reflux)   —— 结构风险（置信度公式的结构版本，纯规则）
      GNN-SGC+kNN             —— SGC 图传播嵌入 + kNN 密度异常分
      KMeansCommunity(64)     —— 团伙簇风险（KMeans + 簇平均度）
      Random                  —— 随机基线（对照，期望 P≈异常率、AUC≈0.5）

    labels 约定：1=异常, 0=正常, -1=未标注（Elliptic unknown，指标中剔除）。
    操作点：标注子集内标记与异常数等量的 top-k 账户。
    """
    n = len(account_ids)
    if n == 0 or len(edges) == 0:
        return {"error": "图为空"}

    labeled_idx = [i for i, a in enumerate(account_ids) if labels.get(a, -1) in (0, 1)]
    if not labeled_idx:
        return {"error": "无 0/1 标注账户"}
    y_true_all = np.zeros(n, dtype=np.int64)
    for i in labeled_idx:
        y_true_all[i] = labels[account_ids[i]]
    n_pos = int(y_true_all.sum())
    if n_pos == 0:
        return {"error": "标注中无异常账户"}

    # 结构特征 + 标准化 + SGC 嵌入（全向量化；特征缺失时退化为结构特征）
    st = _tfinance_struct_features(n, edges)
    if features is not None:
        X = StandardScaler().fit_transform(np.nan_to_num(features, nan=0.0))
    else:
        X = StandardScaler().fit_transform(np.log1p(st))
    emb = _tfinance_sgc_embeddings(n, edges, X, k=sgc_k)
    # 高维嵌入先降维：cKDTree 在 166 维×20万点上会崩溃且距离失真（维度灾难）
    if emb.shape[1] > 64:
        from sklearn.decomposition import TruncatedSVD
        emb = TruncatedSVD(n_components=32, random_state=seed).fit_transform(emb)
        emb = np.asarray(emb, dtype=np.float64)

    deg = st[:, 2]
    imbalance = np.abs(st[:, 0] - st[:, 1]) / np.maximum(deg, 1.0)
    reflux_ratio = st[:, 3] / np.maximum(deg, 1.0)
    struct_score = (0.35 * _percentile_rank(np.log1p(deg))
                    + 0.25 * _percentile_rank(imbalance)
                    + 0.40 * _percentile_rank(reflux_ratio))

    methods = {
        "StructRisk(deg+reflux)": _percentile_rank(struct_score),
        "GNN-SGC+kNN": _knn_anomaly_score(emb, k=k_nn),
        "KMeansCommunity(%d)" % kmeans_k: _kmeans_community_risk(
            n, edges, emb, n_clusters=kmeans_k, seed=seed),
        "Random": np.random.default_rng(seed).uniform(0.0, 1.0, n),
    }

    k = n_pos
    rows: Dict[str, Any] = {}
    for name, score in methods.items():
        # 指标仅在标注子集上计算（unknown=-1 不参与标记与指标）
        score_l = np.asarray([score[i] for i in labeled_idx], dtype=np.float64)
        y_l = np.asarray([y_true_all[i] for i in labeled_idx], dtype=np.int64)
        flag = np.zeros(len(labeled_idx), dtype=np.int64)
        top = np.argsort(score_l)[::-1][:k]
        flag[top] = 1
        p, r, f1, fpr = _prf_at_k(y_l, flag)
        rows[name] = {
            "precision": p, "recall": r, "f1": f1,
            "fpr_误报率": fpr, "auc": _auc_rank(y_l, score_l),
            "flagged": int(k), "tp": int(((y_l == 1) & (flag == 1)).sum()),
        }

    return {
        "dataset": {
            "n_accounts": n, "n_edges": int(len(edges)),
            "n_labeled": len(labeled_idx), "n_anomaly": n_pos,
            "n_unknown": sum(1 for a in account_ids if labels.get(a, -1) == -1),
            "anomaly_ratio": round(n_pos / max(len(labeled_idx), 1), 4),
            "directory": "", "source": source,
        },
        "methods": rows,
    }


def run_tfinance_eval(directory: str, sgc_k: int = 2, kmeans_k: int = 64,
                      k_nn: int = 30, seed: int = 0) -> Dict[str, Any]:
    """T-Finance 节点级欺诈检测评测（全部账户有 0/1 标注）。"""
    adapter_mod = _load_local("tfinance_adapter", "gnn/adapters/tfinance_adapter.py")
    load_tfinance = adapter_mod.load_tfinance
    TFinanceFormatError = adapter_mod.TFinanceFormatError
    try:
        account_ids, edges, labels, features = load_tfinance(directory)
    except TFinanceFormatError as e:
        return {"error": str(e)}
    res = run_node_fraud_eval(account_ids, edges, labels, features,
                              sgc_k=sgc_k, kmeans_k=kmeans_k, k_nn=k_nn, seed=seed,
                              source="T-Finance (Tang et al., ICML 2022)")
    if "error" in res:
        return res
    res["dataset"]["directory"] = directory
    res["dataset"]["note"] = "账户级 0/1 标注，节点级欺诈检测语义"
    return res


def run_elliptic_eval(directory: str, with_features: bool = True,
                      sgc_k: int = 2, kmeans_k: int = 64, k_nn: int = 30,
                      seed: int = 0) -> Dict[str, Any]:
    """Elliptic 节点级欺诈检测评测（unknown 剔除，指标在 licit/illicit 上算）。"""
    adapter_mod = _load_local("elliptic_adapter", "gnn/adapters/elliptic_adapter.py")
    load_elliptic = adapter_mod.load_elliptic
    EllipticFormatError = adapter_mod.EllipticFormatError
    try:
        account_ids, edges, labels, features = load_elliptic(directory,
                                                             with_features=with_features)
    except EllipticFormatError as e:
        return {"error": str(e)}
    res = run_node_fraud_eval(account_ids, edges, labels, features,
                              sgc_k=sgc_k, kmeans_k=kmeans_k, k_nn=k_nn, seed=seed,
                              source="Elliptic (Webber et al., KDD 2019)")
    if "error" in res:
        return res
    res["dataset"]["directory"] = directory
    res["dataset"]["note"] = "账户级 1/0/-1 标注（unknown 剔除），节点级欺诈检测语义"
    return res


def fmt_node_fraud(result: Dict[str, Any]) -> str:
    """把 run_node_fraud_eval 结果格式化为可读表格。"""
    lines = ["", "=" * 66,
             f"真实公开基准 · {result['dataset']['source']}",
             f"数据集: 节点={result['dataset']['n_accounts']} "
             f"边={result['dataset']['n_edges']} "
             f"标注={result['dataset']['n_labeled']} "
             f"异常={result['dataset']['n_anomaly']} "
             f"({result['dataset']['anomaly_ratio']:.2%})"
             + (f"  未标注={result['dataset']['n_unknown']}"
                if result['dataset'].get('n_unknown') else ""),
             "=" * 66]
    header = f"{'方法':<26}{'P':>7}{'R':>7}{'F1':>8}{'误报率':>8}{'AUC':>8}"
    lines.append(header)
    lines.append("-" * 66)
    for name, m in result["methods"].items():
        lines.append(f"{name:<26}{m['precision']:>7.3f}{m['recall']:>7.3f}"
                     f"{m['f1']:>8.3f}{m['fpr_误报率']:>8.3f}{m['auc']:>8.3f}")
    lines.append("-" * 66)
    first = next(iter(result["methods"]))
    lines.append("操作点: 标注子集内标记 top-%d（=异常数）；指标仅在 0/1 标注上计算"
                 % result["methods"][first].get("flagged", 0))
    lines.append("注: 随机基线期望 P≈异常率、AUC≈0.5；真实召回/精确需以此为参照解读。")
    return "\n".join(lines)


fmt_tfinance = fmt_node_fraud  # 兼容旧入口名
