"""
社区检测算法
用于发现诈骗团伙
"""
import numpy as np
import networkx as nx
from typing import List, Dict, Tuple
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score


class CommunityDetector:
    """社区检测器"""
    
    def __init__(self, method: str = 'louvain'):
        """
        初始化社区检测器
        
        Args:
            method: 检测方法 ('louvain', 'label_propagation', 'spectral', 'dbscan')
        """
        self.method = method
        self.communities = {}
        
    def detect(self, graph: nx.Graph, embeddings: np.ndarray = None) -> Dict[int, List[str]]:
        """
        检测社区
        
        Args:
            graph: NetworkX图
            embeddings: 节点嵌入（可选，用于基于嵌入的方法）
            
        Returns:
            社区字典 {community_id: [node_ids]}
        """
        if self.method == 'louvain':
            return self._louvain_detection(graph)
        elif self.method == 'label_propagation':
            return self._label_propagation(graph)
        elif self.method == 'spectral':
            return self._spectral_clustering(graph, embeddings)
        elif self.method == 'dbscan':
            return self._dbscan_clustering(embeddings)
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def _louvain_detection(self, graph: nx.Graph) -> Dict[int, List[str]]:
        """Louvain社区检测"""
        try:
            from community import community_louvain
            partition = community_louvain.best_partition(graph)
        except ImportError:
            # 如果python-louvain未安装，使用NetworkX内置的Louvain
            partition = nx.community.louvain_communities(graph, seed=42)
            # 转换为字典格式
            partition_dict = {}
            for i, community in enumerate(partition):
                for node in community:
                    partition_dict[node] = i
            partition = partition_dict
        
        # 转换为 {community_id: [nodes]} 格式
        communities = {}
        for node, community_id in partition.items():
            if community_id not in communities:
                communities[community_id] = []
            communities[community_id].append(node)
        
        self.communities = communities
        return communities
    
    def _label_propagation(self, graph: nx.Graph) -> Dict[int, List[str]]:
        """标签传播社区检测"""
        communities = nx.community.label_propagation_communities(graph)
        
        # 转换为字典格式
        community_dict = {}
        for i, community in enumerate(communities):
            community_dict[i] = list(community)
        
        self.communities = community_dict
        return community_dict
    
    def _spectral_clustering(
        self,
        graph: nx.Graph,
        embeddings: np.ndarray = None,
        max_communities: int = 10
    ) -> Dict[int, List[str]]:
        """谱聚类（基于嵌入）"""
        if embeddings is None:
            raise ValueError("Spectral clustering requires embeddings")
        
        # 使用KMeans进行聚类
        n_clusters = min(max_communities, len(embeddings) // 2)
        n_clusters = max(2, n_clusters)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        # 转换为字典格式
        communities = {}
        nodes = list(graph.nodes())
        for i, label in enumerate(labels):
            if label not in communities:
                communities[label] = []
            communities[label].append(nodes[i])
        
        self.communities = communities
        return communities
    
    def _dbscan_clustering(
        self,
        embeddings: np.ndarray = None,
        eps: float = 0.5,
        min_samples: int = 2
    ) -> Dict[int, List[str]]:
        """DBSCAN聚类（基于嵌入）"""
        if embeddings is None:
            raise ValueError("DBSCAN clustering requires embeddings")
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(embeddings)
        
        # 转换为字典格式（忽略噪声点-1）
        communities = {}
        for i, label in enumerate(labels):
            if label == -1:
                continue  # 噪声点
            if label not in communities:
                communities[label] = []
            communities[label].append(i)
        
        self.communities = communities
        return communities
    
    def get_community_stats(self, graph: nx.Graph) -> Dict[str, any]:
        """
        获取社区统计信息
        
        Args:
            graph: NetworkX图
            
        Returns:
            统计信息字典
        """
        if not self.communities:
            return {}
        
        num_communities = len(self.communities)
        community_sizes = [len(members) for members in self.communities.values()]
        
        # 计算模块度
        try:
            if self.method == 'louvain':
                from community import community_louvain
                partition = {node: comm_id for comm_id, nodes in self.communities.items() for node in nodes}
                modularity = community_louvain.modularity(graph, partition)
            else:
                modularity = nx.community.modularity(
                    graph,
                    [set(nodes) for nodes in self.communities.values()]
                )
        except Exception as e:
            logger.warning(f"计算模块度失败: {e}")
            modularity = 0.0
        
        # 计算轮廓系数（如果有嵌入）
        silhouette = 0.0
        
        stats = {
            'num_communities': num_communities,
            'avg_community_size': np.mean(community_sizes) if community_sizes else 0,
            'max_community_size': max(community_sizes) if community_sizes else 0,
            'min_community_size': min(community_sizes) if community_sizes else 0,
            'modularity': modularity,
            'silhouette_score': silhouette
        }
        
        return stats
