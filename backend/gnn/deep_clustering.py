"""
深度聚类 - 基于 GNN 嵌入的高级社区检测
结合自编码器和聚类算法，发现更精细的团伙结构
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Optional, Tuple
from sklearn.cluster import KMeans, SpectralClustering
from sklearn.mixture import GaussianMixture
from core.logger import logger


class GraphAutoEncoder(nn.Module):
    """
    图自编码器 - 学习节点的紧凑表示
    用于降维和特征提取，提升聚类效果
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = None,
        latent_dim: int = 32,
        dropout: float = 0.2
    ):
        super(GraphAutoEncoder, self).__init__()
        
        hidden_dims = hidden_dims or [128, 64]
        
        # 编码器
        encoder_layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        encoder_layers.append(nn.Linear(prev_dim, latent_dim))
        self.encoder = nn.Sequential(*encoder_layers)
        
        # 解码器
        decoder_layers = []
        prev_dim = latent_dim
        for hidden_dim in reversed(hidden_dims):
            decoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        decoder_layers.append(nn.Linear(prev_dim, input_dim))
        self.decoder = nn.Sequential(*decoder_layers)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            x: 输入特征 [num_nodes, input_dim]
        
        Returns:
            (latent, reconstructed): 潜在表示和重构特征
        """
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return latent, reconstructed
    
    def encode(self, x: torch.Tensor) -> np.ndarray:
        """编码为潜在表示"""
        self.eval()
        with torch.no_grad():
            latent = self.encoder(x)
        return latent.cpu().numpy()


class DeepClustering(nn.Module):
    """
    深度聚类网络 - 联合学习特征表示和聚类分配
    使用可微的聚类层，端到端训练
    """
    
    def __init__(
        self,
        input_dim: int,
        num_clusters: int,
        hidden_dims: List[int] = None,
        latent_dim: int = 32,
        alpha: float = 1.0
    ):
        super(DeepClustering, self).__init__()
        
        self.num_clusters = num_clusters
        self.alpha = alpha
        
        # 特征提取器
        self.feature_extractor = GraphAutoEncoder(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            latent_dim=latent_dim
        )
        
        # 聚类中心（可学习参数）
        self.cluster_centers = nn.Parameter(
            torch.randn(num_clusters, latent_dim)
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            x: 输入特征 [num_nodes, input_dim]
        
        Returns:
            (latent, cluster_assignments): 潜在表示和聚类分配概率
        """
        # 提取特征
        latent, _ = self.feature_extractor(x)
        
        # 计算到聚类中心的距离
        # latent: [num_nodes, latent_dim]
        # cluster_centers: [num_clusters, latent_dim]
        distances = torch.cdist(latent, self.cluster_centers, p=2)
        
        # 使用 Student's t-distribution 计算分配概率
        # q_ij = (1 + ||z_i - mu_j||^2 / alpha)^(-(alpha+1)/2)
        q = 1.0 / (1.0 + distances ** 2 / self.alpha)
        q = q ** ((self.alpha + 1.0) / 2.0)
        q = q / q.sum(dim=1, keepdim=True)
        
        return latent, q
    
    def predict(self, x: torch.Tensor) -> np.ndarray:
        """预测聚类标签"""
        self.eval()
        with torch.no_grad():
            _, q = self.forward(x)
            labels = torch.argmax(q, dim=1).cpu().numpy()
        return labels


class AdvancedCommunityDetector:
    """
    高级社区检测器 - 结合多种聚类算法
    支持 GNN 嵌入 + 深度聚类
    """
    
    def __init__(self, method: str = "deep_clustering"):
        """
        初始化检测器
        
        Args:
            method: 聚类方法 - "deep_clustering", "kmeans", "spectral", "gmm"
        """
        self.method = method
        self.model = None
        self.cluster_model = None
        
        logger.info("AdvancedCommunityDetector initialized", method=method)
    
    def detect(
        self,
        embeddings: np.ndarray,
        num_clusters: int = None,
        num_epochs: int = 100,
        learning_rate: float = 0.001
    ) -> Tuple[np.ndarray, Dict]:
        """
        检测社区
        
        Args:
            embeddings: 节点嵌入 [num_nodes, embedding_dim]
            num_clusters: 聚类数（None 则自动选择）
            num_epochs: 训练轮数（深度聚类）
            learning_rate: 学习率
        
        Returns:
            (labels, info): 聚类标签和检测信息
        """
        num_nodes = embeddings.shape[0]
        
        # 自动选择聚类数（如果没有指定）
        if num_clusters is None:
            num_clusters = self._estimate_num_clusters(embeddings)
            logger.info("Estimated num_clusters", num_clusters=num_clusters)
        
        # 确保聚类数合理
        num_clusters = min(num_clusters, num_nodes // 2)
        num_clusters = max(num_clusters, 2)
        
        if self.method == "deep_clustering":
            return self._deep_clustering(embeddings, num_clusters, num_epochs, learning_rate)
        elif self.method == "kmeans":
            return self._kmeans_clustering(embeddings, num_clusters)
        elif self.method == "spectral":
            return self._spectral_clustering(embeddings, num_clusters)
        elif self.method == "gmm":
            return self._gmm_clustering(embeddings, num_clusters)
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def _deep_clustering(
        self,
        embeddings: np.ndarray,
        num_clusters: int,
        num_epochs: int,
        learning_rate: float
    ) -> Tuple[np.ndarray, Dict]:
        """深度聚类"""
        input_dim = embeddings.shape[1]
        
        # 转换为张量
        embeddings_tensor = torch.FloatTensor(embeddings)
        
        # 创建模型
        self.model = DeepClustering(
            input_dim=input_dim,
            num_clusters=num_clusters,
            hidden_dims=[128, 64],
            latent_dim=32
        )
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # 训练
        self.model.train()
        losses = []
        
        for epoch in range(num_epochs):
            # 前向传播
            latent, q = self.model(embeddings_tensor)
            
            # 重构损失
            _, reconstructed = self.model.feature_extractor(embeddings_tensor)
            recon_loss = F.mse_loss(reconstructed, embeddings_tensor)
            
            # 聚类损失（鼓励明确的聚类分配）
            # 使用目标分布 p 作为软标签
            p = q ** 2 / q.sum(dim=0)
            p = p / p.sum(dim=1, keepdim=True)
            cluster_loss = F.kl_div(q.log(), p, reduction='batchmean')
            
            # 总损失
            loss = recon_loss + cluster_loss
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            losses.append(loss.item())
            
            if (epoch + 1) % 20 == 0:
                logger.info(f"Deep clustering epoch {epoch + 1}/{num_epochs}, Loss: {loss.item():.4f}")
        
        # 预测
        labels = self.model.predict(embeddings_tensor)
        
        info = {
            "method": "deep_clustering",
            "num_clusters": num_clusters,
            "final_loss": losses[-1],
            "losses": losses
        }
        
        return labels, info
    
    def _kmeans_clustering(
        self,
        embeddings: np.ndarray,
        num_clusters: int
    ) -> Tuple[np.ndarray, Dict]:
        """K-Means 聚类"""
        self.cluster_model = KMeans(
            n_clusters=num_clusters,
            random_state=42,
            n_init=10
        )
        
        labels = self.cluster_model.fit_predict(embeddings)
        
        info = {
            "method": "kmeans",
            "num_clusters": num_clusters,
            "inertia": self.cluster_model.inertia_
        }
        
        return labels, info
    
    def _spectral_clustering(
        self,
        embeddings: np.ndarray,
        num_clusters: int
    ) -> Tuple[np.ndarray, Dict]:
        """谱聚类"""
        self.cluster_model = SpectralClustering(
            n_clusters=num_clusters,
            random_state=42,
            n_init=10,
            affinity='nearest_neighbors'
        )
        
        labels = self.cluster_model.fit_predict(embeddings)
        
        info = {
            "method": "spectral",
            "num_clusters": num_clusters
        }
        
        return labels, info
    
    def _gmm_clustering(
        self,
        embeddings: np.ndarray,
        num_clusters: int
    ) -> Tuple[np.ndarray, Dict]:
        """高斯混合模型聚类"""
        self.cluster_model = GaussianMixture(
            n_components=num_clusters,
            random_state=42,
            covariance_type='full'
        )
        
        labels = self.cluster_model.fit_predict(embeddings)
        
        info = {
            "method": "gmm",
            "num_clusters": num_clusters,
            "bic": self.cluster_model.bic(embeddings),
            "aic": self.cluster_model.aic(embeddings)
        }
        
        return labels, info
    
    def _estimate_num_clusters(self, embeddings: np.ndarray, max_k: int = 20) -> int:
        """
        自动估计最佳聚类数
        使用轮廓系数法
        """
        from sklearn.metrics import silhouette_score
        
        best_k = 2
        best_score = -1
        
        # 尝试不同的 k 值
        for k in range(2, min(max_k + 1, len(embeddings) // 2)):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, labels)
            
            if score > best_score:
                best_score = score
                best_k = k
        
        return best_k
