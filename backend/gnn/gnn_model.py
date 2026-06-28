"""
GraphSAGE模型实现
用于学习节点嵌入表示
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional


class GraphSAGELayer(nn.Module):
    """GraphSAGE层"""
    
    def __init__(self, in_dim: int, out_dim: int, aggregator_type: str = 'mean'):
        super(GraphSAGELayer, self).__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.aggregator_type = aggregator_type
        
        # 聚合器
        self.aggregator = nn.Linear(in_dim, in_dim, bias=False)
        
        # 更新器
        self.update = nn.Linear(in_dim * 2, out_dim, bias=False)
        
        # 归一化
        self.norm = nn.LayerNorm(out_dim)
        
    def forward(self, features: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            features: 节点特征矩阵 [num_nodes, in_dim]
            adj: 邻接矩阵 [num_nodes, num_nodes]
            
        Returns:
            更新后的节点特征 [num_nodes, out_dim]
        """
        # 聚合邻居信息
        if self.aggregator_type == 'mean':
            # 均值聚合
            neighbor_agg = torch.matmul(adj, features)
            degree = torch.sum(adj, dim=1, keepdim=True)
            degree = torch.clamp(degree, min=1.0)  # 避免除零
            agg = neighbor_agg / degree
        elif self.aggregator_type == 'gcn':
            # GCN风格聚合
            agg = torch.matmul(adj, features)
        else:
            agg = torch.matmul(adj, features)
        
        # 变换聚合结果
        agg = self.aggregator(agg)
        
        # 拼接当前节点特征和聚合结果
        concat = torch.cat([features, agg], dim=1)
        
        # 更新节点特征
        output = self.update(concat)
        
        # 归一化
        output = self.norm(output)
        
        # 激活函数
        output = F.relu(output)
        
        return output


class GraphSAGE(nn.Module):
    """GraphSAGE模型"""
    
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        out_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
        aggregator_type: str = 'mean'
    ):
        """
        初始化GraphSAGE
        
        Args:
            in_dim: 输入特征维度
            hidden_dim: 隐藏层维度
            out_dim: 输出嵌入维度
            num_layers: 层数
            dropout: dropout率
            aggregator_type: 聚合器类型 ('mean', 'gcn')
        """
        super(GraphSAGE, self).__init__()
        
        self.num_layers = num_layers
        self.dropout = dropout
        
        # 构建多层GraphSAGE
        self.layers = nn.ModuleList()
        
        # 第一层
        self.layers.append(GraphSAGELayer(in_dim, hidden_dim, aggregator_type))
        
        # 中间层
        for _ in range(num_layers - 2):
            self.layers.append(GraphSAGELayer(hidden_dim, hidden_dim, aggregator_type))
        
        # 最后一层
        if num_layers > 1:
            self.layers.append(GraphSAGELayer(hidden_dim, out_dim, aggregator_type))
        
        self.dropout_layer = nn.Dropout(dropout)
        
    def forward(self, features: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            features: 节点特征矩阵 [num_nodes, in_dim]
            adj: 邻接矩阵 [num_nodes, num_nodes]
            
        Returns:
            节点嵌入 [num_nodes, out_dim]
        """
        h = features
        
        for i, layer in enumerate(self.layers):
            h = layer(h, adj)
            
            # 最后一层不使用dropout
            if i < len(self.layers) - 1:
                h = self.dropout_layer(h)
        
        return h
    
    def get_embeddings(self, features: torch.Tensor, adj: torch.Tensor) -> np.ndarray:
        """
        获取节点嵌入（用于下游任务）
        
        Args:
            features: 节点特征矩阵
            adj: 邻接矩阵
            
        Returns:
            节点嵌入numpy数组
        """
        self.eval()
        with torch.no_grad():
            embeddings = self.forward(features, adj)
        return embeddings.cpu().numpy()


class FraudGNN(nn.Module):
    """诈骗团伙发现GNN模型（带节点分类头）"""
    
    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        embedding_dim: int = 64,
        num_classes: int = 10,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        """
        初始化FraudGNN
        
        Args:
            in_dim: 输入特征维度
            hidden_dim: 隐藏层维度
            embedding_dim: 嵌入维度
            num_classes: 分类数（团伙数）
            num_layers: GraphSAGE层数
            dropout: dropout率
        """
        super(FraudGNN, self).__init__()
        
        # GraphSAGE骨干网络
        self.sage = GraphSAGE(
            in_dim=in_dim,
            hidden_dim=hidden_dim,
            out_dim=embedding_dim,
            num_layers=num_layers,
            dropout=dropout
        )
        
        # 节点分类头
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
        
    def forward(
        self,
        features: torch.Tensor,
        adj: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            features: 节点特征矩阵
            adj: 邻接矩阵
            
        Returns:
            (embeddings, logits): 节点嵌入和分类logits
        """
        # 获取节点嵌入
        embeddings = self.sage(features, adj)
        
        # 节点分类
        logits = self.classifier(embeddings)
        
        return embeddings, logits
    
    def get_embeddings(self, features: torch.Tensor, adj: torch.Tensor) -> np.ndarray:
        """获取节点嵌入"""
        self.eval()
        with torch.no_grad():
            embeddings = self.sage(features, adj)
        return embeddings.cpu().numpy()
