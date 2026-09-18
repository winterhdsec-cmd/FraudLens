"""
异构图基线：RGCN 与 GAT（纯 torch 实现，与 FraudHAN 同协议对比）

设计目标（公平对比三原则）：
1. 输入完全一致：features [N,in_dim] + meta_path_adjacency 字典（与 baseline_gnn_han 同出处）。
2. 训练协议完全一致：与 HAN 相同的 GraphCL 对比学习（edge_drop / feature_mask 双视图、NT-Xent）。
3. 评测协议完全一致：案件节点嵌入 -> StandardScaler -> KMeans(n_true) -> pairwise F1/NMI/ARI。

三模型差异仅在"聚合与注意力机制"，用以隔离注意力带来的增量：
- RGCNBaseline ：逐元路径关系专属传播（关系权重），元路径间 **均值** 融合（无注意力）。
- GATBaseline  ：逐元路径图注意力（单头），元路径间 **均值** 融合（无语义注意力）。
- FraudHAN     ：逐元路径注意力 + 语义注意力（元路径级注意力）。

诚实口径：这些基线同样在"合成案件图"上评测，与 HAN 同属合成验证；
它们用于回答"异构图注意力是否优于更简单的异构图传播"，而非"真实数据验证"。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


def _row_norm(adj: torch.Tensor) -> torch.Tensor:
    """对称/行归一化邻接 (A+I) / D，避免孤立节点除零。"""
    n = adj.shape[0]
    a = adj + torch.eye(n, device=adj.device, dtype=adj.dtype)
    deg = a.sum(1, keepdim=True).clamp(min=1.0)
    return a / deg


def _binarize(adj: torch.Tensor) -> torch.Tensor:
    return (adj > 0).float()


class RGCNBaseline(nn.Module):
    """逐元路径关系专属线性传播；元路径间均值融合（无注意力）。"""

    def __init__(self, in_dim: int, hidden_dim: int = 64, out_dim: int = 32,
                 num_layers: int = 2, meta_paths: list = None, dropout: float = 0.3):
        super().__init__()
        self.meta_paths = meta_paths or ["case_account_case", "case_perpetrator_case",
                                         "case_type_case", "case_city_case", "case_text_case"]
        self.num_layers = num_layers
        # 每层、每个元路径一个关系专属权重
        self.W = nn.ModuleDict()
        for l in range(num_layers):
            for m in self.meta_paths:
                self.W[f"{l}_{m}"] = nn.Linear(in_dim if l == 0 else hidden_dim, hidden_dim)
        self.out_proj = nn.Linear(hidden_dim, out_dim)
        self.drop = nn.Dropout(dropout)
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])

    def forward(self, features: torch.Tensor, meta_path_adjs: dict) -> torch.Tensor:
        h = features
        for l in range(self.num_layers):
            outs = []
            for m in self.meta_paths:
                if m not in meta_path_adjs:
                    continue
                adj = _row_norm(meta_path_adjs[m].to(features.device))
                h_m = self.W[f"{l}_{m}"](h)
                h_m = adj @ h_m                      # 关系专属传播
                h_m = F.elu(h_m)
                h_m = self.norms[l](h_m)
                outs.append(h_m)
            if not outs:
                break
            h = torch.stack(outs, dim=0).mean(dim=0)  # 元路径间均值（无注意力）
            h = self.drop(h)
        return self.out_proj(h)


class GATBaseline(nn.Module):
    """逐元路径单头图注意力；元路径间均值融合（无语义注意力）。"""

    def __init__(self, in_dim: int, hidden_dim: int = 64, out_dim: int = 32,
                 num_layers: int = 2, meta_paths: list = None, dropout: float = 0.3,
                 leak: float = 0.2):
        super().__init__()
        self.meta_paths = meta_paths or ["case_account_case", "case_perpetrator_case",
                                         "case_type_case", "case_city_case", "case_text_case"]
        self.num_layers = num_layers
        self.leak = leak
        self.W = nn.ModuleDict()
        self.att_src = nn.ParameterDict()
        self.att_dst = nn.ParameterDict()
        for l in range(num_layers):
            for m in self.meta_paths:
                self.W[f"{l}_{m}"] = nn.Linear(in_dim if l == 0 else hidden_dim, hidden_dim)
                self.att_src[f"{l}_{m}"] = nn.Parameter(torch.zeros(hidden_dim))
                self.att_dst[f"{l}_{m}"] = nn.Parameter(torch.zeros(hidden_dim))
        self.out_proj = nn.Linear(hidden_dim, out_dim)
        self.drop = nn.Dropout(dropout)
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])

    def forward(self, features: torch.Tensor, meta_path_adjs: dict) -> torch.Tensor:
        h = features
        neg_inf = float("-inf")
        for l in range(self.num_layers):
            outs = []
            for m in self.meta_paths:
                if m not in meta_path_adjs:
                    continue
                n = h.shape[0]
                # 二值邻接 + 自环，保证每个节点至少有自注意力（避免孤立节点 softmax(-inf)=NaN）
                adj = _binarize(meta_path_adjs[m].to(features.device))
                adj = (adj + torch.eye(n, device=features.device, dtype=adj.dtype)).clamp(max=1.0)
                hW = self.W[f"{l}_{m}"](h)                       # [N, H]
                src = (hW * self.att_src[f"{l}_{m}"]).sum(1, keepdim=True)  # [N,1]
                dst = (hW * self.att_dst[f"{l}_{m}"]).sum(1, keepdim=True)  # [N,1]
                e = F.leaky_relu(src + dst.T, self.leak)         # [N,N]
                e = e.masked_fill(adj == 0, neg_inf)
                a = torch.softmax(e, dim=1)                      # 行归一注意力
                h_m = a @ hW                                     # 注意力聚合
                h_m = F.elu(h_m)
                h_m = self.norms[l](h_m)
                outs.append(h_m)
            if not outs:
                break
            h = torch.stack(outs, dim=0).mean(dim=0)
            h = self.drop(h)
        return self.out_proj(h)


# ----------------------------------------------------------------------------
# 通用 GraphCL 对比学习（与 han_model.GraphCLTrainer 同协议）
# ----------------------------------------------------------------------------
def _edge_drop(adj: torch.Tensor, p: float = 0.8) -> torch.Tensor:
    return adj * torch.bernoulli(torch.ones_like(adj) * p)


def _feature_mask(features: torch.Tensor, p: float = 0.85) -> torch.Tensor:
    return features * torch.bernoulli(torch.ones_like(features) * p)


def _encode(model, features, meta_t):
    """统一编码接口：FraudHAN 走 .han 编码器，基线走自身 forward。"""
    if hasattr(model, "han"):
        return model.han(features, meta_t)
    return model(features, meta_t)


def graphcl_pretrain(model, feat_t: torch.Tensor, meta_t: dict,
                     epochs: int = 100, batch: int = 256, lr: float = 5e-4,
                     temp: float = 0.5, device: str = "cpu"):
    model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    n = feat_t.shape[0]

    def ntxent(z1, z2):
        z1 = F.normalize(z1, dim=1)
        z2 = F.normalize(z2, dim=1)
        sim = torch.matmul(z1, z2.T) / temp
        lab = torch.arange(z1.shape[0], device=device)
        return F.cross_entropy(sim, lab)

    for _ in range(epochs):
        idx = torch.randperm(n)[:batch]
        bf = feat_t[idx]
        bmetas = {k: v[idx][:, idx] for k, v in meta_t.items()}
        # 视图1：边丢弃（特征不变）
        v1_f, v1_m = bf, {k: _edge_drop(v) for k, v in bmetas.items()}
        # 视图2：特征掩码（边不变）
        v2_f, v2_m = _feature_mask(bf), bmetas
        z1 = _encode(model, v1_f, v1_m)
        z2 = _encode(model, v2_f, v2_m)
        loss = ntxent(z1, z2)
        if not torch.isfinite(loss):
            continue
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    return model


def extract_case_embeddings(model, feat_t, meta_t, case_idx, scaler=None):
    model.eval()
    with torch.no_grad():
        emb = _encode(model, feat_t, meta_t).cpu().numpy()
    ce = np.asarray(emb[case_idx], dtype=np.float32)
    if scaler:
        ce = scaler.fit_transform(ce)
    return ce
