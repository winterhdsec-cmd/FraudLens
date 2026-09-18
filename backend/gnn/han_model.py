"""
异构图注意力网络 (HAN) - 用于诈骗团伙发现
支持多种节点类型和元路径，学习不同关系的重要性
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from core.logger import logger


class SemanticAttention(nn.Module):
    """
    语义级注意力 - 学习不同元路径的重要性
    """
    
    def __init__(self, in_dim: int, hidden_dim: int = 128, uniform: bool = False):
        super(SemanticAttention, self).__init__()
        self.uniform = uniform
        self.project = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1, bias=False)
        )
    
    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        计算元路径权重
        
        Args:
            z: 不同元路径的节点表示 [num_meta_paths, num_nodes, in_dim]
        
        Returns:
            加权融合后的节点表示 [num_nodes, in_dim]
        """
        # 计算每个元路径的注意力分数
        w = self.project(z).mean(dim=1)  # [num_meta_paths, 1]
        if self.uniform:
            # 消融模式：固定等权平均（不学习元路径权重），验证语义注意力是否真实生效
            beta = torch.full_like(w.detach(), 1.0 / z.shape[0])
        else:
            beta = torch.softmax(w, dim=0)  # [num_meta_paths, 1]
        self.last_beta = beta.detach()
        
        # 加权融合：扩展到 [num_meta_paths, num_nodes, in_dim] 与 z 逐元素乘
        beta = beta.unsqueeze(-1)  # [num_meta_paths, 1, 1]
        beta = beta.expand(z.shape[0], z.shape[1], z.shape[2])
        output = (beta * z).sum(dim=0)  # [num_nodes, in_dim]
        
        return output


class HANLayer(nn.Module):
    """
    HAN 层 - 元路径内的图注意力
    """
    
    def __init__(self, in_dim: int, out_dim: int, num_heads: int = 8, dropout: float = 0.3):
        super(HANLayer, self).__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.num_heads = num_heads
        
        # 多头注意力
        self.attention_heads = nn.ModuleList([
            nn.MultiheadAttention(
                embed_dim=in_dim,
                num_heads=1,
                dropout=dropout,
                batch_first=True
            )
            for _ in range(num_heads)
        ])
        
        # 输出投影
        self.output_proj = nn.Linear(in_dim * num_heads, out_dim)
        
        # 归一化
        self.norm = nn.LayerNorm(out_dim)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, features: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            features: 节点特征 [num_nodes, in_dim]
            adj: 邻接矩阵 [num_nodes, num_nodes]
        
        Returns:
            更新后的节点特征 [num_nodes, out_dim]
        """
        num_nodes = features.shape[0]

        # 注意力偏置：非边 -inf 屏蔽 + 边权 log(w) 加性偏置。
        # 二值邻接时 log(1)=0，偏置为 0，与原行为完全一致；
        # 软权重邻接（如文本通道相似度边权）时，注意力 logits += log(w)，
        # 等效于对相似度高的邻居加权（细粒度语义信息不再被二值化抹平）。
        bias = torch.zeros_like(adj)
        nonzero = adj > 0
        bias[nonzero] = torch.log(adj[nonzero].clamp(min=1e-6))
        bias[~nonzero] = -1e9  # 非边屏蔽（含 w=0）

        # 多头注意力
        head_outputs = []
        for head in self.attention_heads:
            # 使用邻接矩阵作为注意力掩码（加性偏置形式）
            attn_mask = bias.unsqueeze(0).expand(num_nodes, -1, -1)
            
            # 自注意力
            features_expanded = features.unsqueeze(0)  # [1, num_nodes, in_dim]
            attn_output, _ = head(
                features_expanded,
                features_expanded,
                features_expanded,
                attn_mask=attn_mask[0]
            )
            head_outputs.append(attn_output.squeeze(0))
        
        # 拼接多头输出
        concat = torch.cat(head_outputs, dim=1)  # [num_nodes, in_dim * num_heads]
        
        # 投影
        output = self.output_proj(concat)
        output = self.norm(output)
        output = F.elu(output)
        output = self.dropout(output)
        
        return output


class HAN(nn.Module):
    """
    异构图注意力网络 (HAN)
    """
    
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        out_dim: int = 64,
        num_heads: int = 8,
        num_layers: int = 2,
        meta_paths: List[str] = None,
        dropout: float = 0.3,
        semantic_attention_mode: str = "learn"
    ):
        super(HAN, self).__init__()
        
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim
        self.num_layers = num_layers
        self.meta_paths = meta_paths or ["default"]
        
        # 为每个元路径创建 HAN 层
        self.meta_path_layers = nn.ModuleDict()
        for mp in self.meta_paths:
            layers = nn.ModuleList()
            layers.append(HANLayer(in_dim, hidden_dim, num_heads, dropout))
            for _ in range(num_layers - 1):
                layers.append(HANLayer(hidden_dim, hidden_dim, num_heads, dropout))
            self.meta_path_layers[mp] = layers
        
        # 语义注意力（"learn"=学习元路径权重；"mean"=固定等权平均，消融用）
        self.semantic_attention = SemanticAttention(
            hidden_dim, uniform=(semantic_attention_mode == "mean"))
        
        # 输出投影
        self.output_proj = nn.Linear(hidden_dim, out_dim)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """
        前向传播
        
        Args:
            features: 节点特征 [num_nodes, in_dim]
            meta_path_adjs: 不同元路径的邻接矩阵字典
        
        Returns:
            节点嵌入 [num_nodes, out_dim]
        """
        # 对每个元路径进行图注意力
        meta_path_embeddings = []
        for mp in self.meta_paths:
            if mp not in meta_path_adjs:
                continue
            
            adj = meta_path_adjs[mp]
            h = features
            
            # 通过该元路径的 HAN 层
            for layer in self.meta_path_layers[mp]:
                h = layer(h, adj)
            
            meta_path_embeddings.append(h)
        
        if not meta_path_embeddings:
            # 如果没有元路径，使用默认处理
            meta_path_embeddings.append(features)
        
        # 堆叠不同元路径的嵌入 [num_meta_paths, num_nodes, hidden_dim]
        z = torch.stack(meta_path_embeddings, dim=0)
        
        # 语义注意力融合
        fused = self.semantic_attention(z)
        
        # 输出投影
        output = self.output_proj(fused)
        output = self.dropout(output)
        
        return output
    
    def get_embeddings(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor]
    ) -> np.ndarray:
        """获取节点嵌入"""
        self.eval()
        with torch.no_grad():
            embeddings = self.forward(features, meta_path_adjs)
        return embeddings.cpu().numpy()


class FraudHAN(nn.Module):
    """
    诈骗团伙发现 HAN 模型
    """
    
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        embedding_dim: int = 64,
        num_classes: int = 10,
        num_heads: int = 8,
        num_layers: int = 2,
        dropout: float = 0.3,
        semantic_attention_mode: str = "learn"
    ):
        super(FraudHAN, self).__init__()
        
        # 默认元路径（真异构：各自拓扑不同，见 graph_builder.get_meta_path_adjacency）
        self.meta_paths = [
            "case_account_case",
            "case_perpetrator_case",
            "case_type_case",
            "case_city_case",
            "case_text_case"   # A3: 话术语义通道（双通道并入 GNN，BGE 文本相似元路径）
        ]
        
        # HAN 骨干网络
        self.han = HAN(
            in_dim=in_dim,
            hidden_dim=hidden_dim,
            out_dim=embedding_dim,
            num_heads=num_heads,
            num_layers=num_layers,
            meta_paths=self.meta_paths,
            dropout=dropout,
            semantic_attention_mode=semantic_attention_mode
        )
        
        # 链路预测头（用于自监督训练）
        self.link_predictor = nn.Sequential(
            nn.Linear(embedding_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
        
        # 节点分类头（用于团伙分类）
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            features: 节点特征 [num_nodes, in_dim]
            meta_path_adjs: 不同元路径的邻接矩阵
        
        Returns:
            (embeddings, logits): 节点嵌入和分类 logits
        """
        embeddings = self.han(features, meta_path_adjs)
        logits = self.classifier(embeddings)
        return embeddings, logits
    
    def predict_link(self, embeddings: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        预测链路
        
        Args:
            embeddings: 节点嵌入 [num_nodes, embedding_dim]
            edge_index: 边索引 [2, num_edges]
        
        Returns:
            链路预测概率 [num_edges]
        """
        src_emb = embeddings[edge_index[0]]
        dst_emb = embeddings[edge_index[1]]
        pair_emb = torch.cat([src_emb, dst_emb], dim=1)
        return self.link_predictor(pair_emb).squeeze()
    
    def get_embeddings(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor]
    ) -> np.ndarray:
        """获取节点嵌入"""
        return self.han.get_embeddings(features, meta_path_adjs)


class GraphCLTrainer:
    """
    图对比学习训练器
    支持自监督预训练 + 微调模式
    """
    
    def __init__(
        self,
        model: FraudHAN,
        temperature: float = 0.5,
        learning_rate: float = 0.001,
        device: str = "cpu"
    ):
        self.model = model.to(device)
        self.temperature = temperature
        self.device = device
        
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
        
        logger.info("GraphCLTrainer initialized", temperature=temperature, lr=learning_rate)
    
    def augment_graph(
        self,
        features: torch.Tensor,
        adj: Any,
        strategy: str = "edge_drop"
    ) -> Tuple[torch.Tensor, Any]:
        """
        图增强（支持单张邻接矩阵或元路径邻接字典）
        
        Args:
            features: 原始特征
            adj: 原始邻接矩阵(torch.Tensor) 或 元路径邻接字典(Dict[str, Tensor])
            strategy: 增强策略 - "edge_drop", "feature_mask", "subgraph"
        
        Returns:
            增强后的特征和(对应结构的)邻接
        """
        if isinstance(adj, dict):
            # 元路径字典：edge_drop 作用到每条元路径；feature_mask 只作用特征；
            # subgraph 作用于共享节点集（所有元路径同序）
            if strategy == "edge_drop":
                aug_adjs = {k: self._edge_drop(v) for k, v in adj.items()}
                return features, aug_adjs
            elif strategy == "feature_mask":
                return self._feature_mask(features), adj
            elif strategy == "subgraph":
                aug_features, node_mask = self._subgraph_mask(features)
                aug_adjs = {k: v[node_mask][:, node_mask] for k, v in adj.items()}
                return aug_features, aug_adjs
            else:
                return features, adj

        # 单张邻接（兼容旧调用）
        if strategy == "edge_drop":
            return features, self._edge_drop(adj)
        elif strategy == "feature_mask":
            return self._feature_mask(features), adj
        elif strategy == "subgraph":
            aug_features, node_mask = self._subgraph_mask(features)
            return aug_features, adj[node_mask][:, node_mask]
        else:
            return features, adj

    @staticmethod
    def _edge_drop(adj: torch.Tensor) -> torch.Tensor:
        mask = torch.bernoulli(torch.ones_like(adj) * 0.8)
        return adj * mask

    @staticmethod
    def _feature_mask(features: torch.Tensor) -> torch.Tensor:
        mask = torch.bernoulli(torch.ones_like(features) * 0.85)
        return features * mask

    @staticmethod
    def _subgraph_mask(features: torch.Tensor):
        num_nodes = features.shape[0]
        node_mask = torch.bernoulli(torch.ones(num_nodes) * 0.8).bool()
        return features[node_mask], node_mask
    
    def contrastive_loss(self, z1: torch.Tensor, z2: torch.Tensor) -> torch.Tensor:
        """
        对比损失 (NT-Xent)
        
        Args:
            z1: 视图1的嵌入 [batch_size, dim]
            z2: 视图2的嵌入 [batch_size, dim]
        
        Returns:
            对比损失
        """
        batch_size = z1.shape[0]
        
        # 归一化
        z1 = F.normalize(z1, dim=1)
        z2 = F.normalize(z2, dim=1)
        
        # 计算相似度矩阵
        similarity_matrix = torch.matmul(z1, z2.T) / self.temperature
        
        # 创建标签
        labels = torch.arange(batch_size).to(self.device)
        
        # 计算损失
        loss = F.cross_entropy(similarity_matrix, labels)
        
        return loss
    
    def pretrain(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor],
        num_epochs: int = 100,
        batch_size: int = 256,
        mode: str = "graphcl"
    ) -> Dict[str, List[float]]:
        """
        自监督预训练

        Args:
            features: 节点特征
            meta_path_adjs: 元路径邻接矩阵
            num_epochs: 训练轮数
            batch_size: 批次大小
            mode: "graphcl" = NT-Xent 对比（默认，行为不变）；
                  "byol" = BYOL 式动量编码器免负样本回归（小样本图场景防塌缩，
                  依据：GCL 负样本数需随节点数平方增长才有效，N≤256 时
                  NT-Xent 负样本不足 → 表示塌缩 clusters=1，见 probe v5 记录）

        Returns:
            训练历史
        """
        if mode == "byol":
            return self._pretrain_byol(features, meta_path_adjs, num_epochs, batch_size)
        self.model.train()
        history = {"loss": []}
        
        num_nodes = features.shape[0]
        
        for epoch in range(num_epochs):
            epoch_losses = []
            
            # 随机采样批次
            indices = torch.randperm(num_nodes)[:batch_size]
            batch_features = features[indices]
            batch_adjs = {mp: adj[indices][:, indices] for mp, adj in meta_path_adjs.items()}
            
            # 创建两个增强视图（遍历全部元路径，保留异构结构）
            aug_features1, aug_adjs1 = self.augment_graph(batch_features, batch_adjs, "edge_drop")
            aug_features2, aug_adjs2 = self.augment_graph(batch_features, batch_adjs, "feature_mask")
            
            # 获取两个视图的嵌入（使用各自视图的完整元路径邻接）
            z1 = self.model.han(aug_features1, aug_adjs1)
            z2 = self.model.han(aug_features2, aug_adjs2)
            
            # 计算对比损失
            loss = self.contrastive_loss(z1, z2)
            
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            epoch_losses.append(loss.item())
            
            if (epoch + 1) % 10 == 0:
                avg_loss = np.mean(epoch_losses)
                logger.info(f"Epoch {epoch + 1}/{num_epochs}, Loss: {avg_loss:.4f}")
            
            history["loss"].append(np.mean(epoch_losses))

        return history

    @torch.no_grad()
    def _ema_update(self, online: nn.Module, target: nn.Module, tau: float):
        """目标网络 = 在线网络的指数滑动平均（BYOL 核心，免负样本防塌缩）"""
        for po, pt in zip(online.parameters(), target.parameters()):
            pt.data.mul_(tau).add_(po.data, alpha=1 - tau)

    def _pretrain_byol(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor],
        num_epochs: int = 100,
        batch_size: int = 256,
        tau: float = 0.9,
        warmup_tau: float = 0.996
    ) -> Dict[str, List[float]]:
        """BYOL 式自监督预训练（免负样本）。

        在线网络编码视图1 -> predictor -> 回归目标网络编码的视图2（对称两项）。
        目标网络仅由在线网络 EMA 得到，不反传梯度。无负样本，故在小图
        （N≤256，负样本天然不足）场景下不会因 NT-Xent 负样本坍缩而塌缩。
        tau 随 epoch 由 warmup_tau 退火到 tau（BYOL 原文做法）。
        """
        import copy
        emb_dim = self.model.han.out_dim
        if not hasattr(self, "predictor"):
            self.predictor = nn.Sequential(
                nn.Linear(emb_dim, emb_dim), nn.ReLU(), nn.Linear(emb_dim, emb_dim)
            ).to(self.device)
            self.opt_byol = torch.optim.Adam(
                list(self.model.parameters()) + list(self.predictor.parameters()),
                lr=self.optimizer.param_groups[0]["lr"], weight_decay=1e-5)
        target = copy.deepcopy(self.model.han)
        for p in target.parameters():
            p.requires_grad_(False)

        self.model.train()
        history = {"loss": []}
        num_nodes = features.shape[0]

        for epoch in range(num_epochs):
            t = min(tau, warmup_tau + (tau - warmup_tau) * epoch / max(1, num_epochs))
            indices = torch.randperm(num_nodes)[:batch_size]
            bf = features[indices]
            ba = {mp: adj[indices][:, indices] for mp, adj in meta_path_adjs.items()}

            f1, a1 = self.augment_graph(bf, ba, "edge_drop")
            f2, a2 = self.augment_graph(bf, ba, "feature_mask")

            z1 = self.model.han(f1, a1)
            z2 = self.model.han(f2, a2)
            with torch.no_grad():
                y1t = target(f1, a1)
                y2t = target(f2, a2)

            p1 = F.normalize(self.predictor(z1), dim=1)
            p2 = F.normalize(self.predictor(z2), dim=1)
            q1 = F.normalize(y1t, dim=1)
            q2 = F.normalize(y2t, dim=1)
            # 标准 BYOL 对称损失：L = 0.5·[(2-2cos(p1,q2)) + (2-2cos(p2,q1))]，收敛时 → 0
            loss = 0.5 * ((2 - 2 * (p1 * q2).sum(1).mean()) +
                          (2 - 2 * (p2 * q1).sum(1).mean()))

            self.opt_byol.zero_grad()
            loss.backward()
            self.opt_byol.step()
            with torch.no_grad():
                self._ema_update(self.model.han, target, t)

            history["loss"].append(float(loss.item()))
            if (epoch + 1) % 10 == 0:
                logger.info(f"[BYOL] Epoch {epoch + 1}/{num_epochs}, Loss: {loss.item():.4f}")

        return history

    def finetune(
        self,
        features: torch.Tensor,
        meta_path_adjs: Dict[str, torch.Tensor],
        labels: torch.Tensor,
        num_epochs: int = 50,
        learning_rate: float = 0.0001
    ) -> Dict[str, List[float]]:
        """
        微调（节点分类）
        
        Args:
            features: 节点特征
            meta_path_adjs: 元路径邻接矩阵
            labels: 节点标签
            num_epochs: 训练轮数
            learning_rate: 学习率
        
        Returns:
            训练历史
        """
        # 调整学习率
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = learning_rate
        
        self.model.train()
        history = {"loss": [], "accuracy": []}
        
        criterion = nn.CrossEntropyLoss()
        
        for epoch in range(num_epochs):
            # 前向传播
            embeddings, logits = self.model(features, meta_path_adjs)
            
            # 计算损失
            loss = criterion(logits, labels)
            
            # 计算准确率
            _, predicted = torch.max(logits, 1)
            accuracy = (predicted == labels).float().mean().item()
            
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            history["loss"].append(loss.item())
            history["accuracy"].append(accuracy)
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch + 1}/{num_epochs}, Loss: {loss.item():.4f}, Acc: {accuracy:.4f}")
        
        return history
