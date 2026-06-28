"""
团伙发现 Agent - 自适应聚类 + 反思机制 + GNN增强
"""
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.agent_runtime import AgentRuntime
from core.state import AgentState
from gnn import GangDetector


class ClusterAgent:
    """
    团伙发现智能体
    
    使用自适应聚类算法和GNN发现诈骗团伙:
    1. 分析数据特征（数量、维度、分布）
    2. 选择最优聚类策略（传统聚类或GNN）
    3. 执行聚类/图神经网络学习
    4. 评估聚类质量
    5. 反思并调整（如果质量不佳）
    """
    
    def __init__(self, llm_client=None, embedding_model=None, use_gnn=True):
        self.llm = llm_client
        self.embedding_model = embedding_model
        self.use_gnn = use_gnn
        
        # 初始化 Agent 运行时
        self.runtime = AgentRuntime(
            agent_id="cluster_agent",
            agent_type="cluster",
            tools={},
            max_iterations=3,
            enable_reflection=True
        )
        
        # 初始化GNN检测器
        if self.use_gnn:
            self.gnn_detector = GangDetector(
                embedding_dim=64,
                hidden_dim=32,
                num_layers=2,
                community_method='louvain'
            )
    
    def discover_gangs(self, cases: List[Dict[str, Any]], use_gnn: bool = None) -> Dict[str, Any]:
        """
        发现诈骗团伙
        
        Args:
            cases: 案件列表，每个案件包含 description, case_id 等
            use_gnn: 是否使用GNN（None表示使用默认设置）
        
        Returns:
            团伙发现结果
        """
        if not cases:
            return {"gangs": [], "total_gangs": 0}
        
        # 确定是否使用GNN
        should_use_gnn = use_gnn if use_gnn is not None else self.use_gnn
        
        # 如果使用GNN且有足够数据
        if should_use_gnn and hasattr(self, 'gnn_detector') and len(cases) >= 3:
            try:
                # 使用GNN进行团伙发现
                result = self.gnn_detector.detect(
                    cases=cases,
                    use_gnn=True,
                    training_epochs=100
                )
                
                # 添加方法标记
                result['method'] = 'gnn'
                result['quality_score'] = result.get('stats', {}).get('silhouette_score', 0.5)
                result['strategy'] = {'method': 'gnn', 'params': {}}
                
                return result
            except Exception as e:
                print(f"GNN团伙发现失败: {e}，回退到传统聚类")
        
        # 传统聚类方法
        # 1. 提取文本特征
        texts = [c.get("description", "") for c in cases]
        embeddings = self._encode_texts(texts)
        
        # 2. 分析数据特征
        data_profile = self._profile_data(embeddings, cases)
        
        # 3. 选择聚类策略
        strategy = self._select_strategy(data_profile)
        
        # 4. 执行聚类
        clusters, quality_score = self._execute_clustering(embeddings, strategy)
        
        # 5. 反思并调整（如果质量不佳）
        if quality_score < 0.5:
            new_strategy = self._reflect_and_adjust(strategy, quality_score, data_profile)
            clusters, quality_score = self._execute_clustering(embeddings, new_strategy)
        
        # 6. 生成团伙信息
        gangs = self._generate_gang_info(cases, clusters, embeddings)
        
        return {
            "gangs": gangs,
            "total_gangs": len(gangs),
            "quality_score": quality_score,
            "strategy": strategy,
            "method": "traditional_clustering"
        }
    
    def _encode_texts(self, texts: List[str]) -> np.ndarray:
        """编码文本为向量"""
        if not self.embedding_model:
            # 使用简单的 hash 向量（fallback）
            return self._hash_embeddings(texts)
        
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings
        except Exception as e:
            print(f"Embedding 失败: {e}")
            return self._hash_embeddings(texts)
    
    def _hash_embeddings(self, texts: List[str], dim: int = 768) -> np.ndarray:
        """简单的 hash 向量（fallback）"""
        embeddings = []
        for text in texts:
            hash_val = abs(hash(text)) % (2**32)  # 确保在有效范围内
            np.random.seed(hash_val)
            emb = np.random.randn(dim).astype(np.float32)
            embeddings.append(emb)
        return np.array(embeddings)
    
    def _profile_data(self, embeddings: np.ndarray, cases: List[Dict]) -> Dict[str, Any]:
        """分析数据特征"""
        n_samples = len(embeddings)
        n_features = embeddings.shape[1] if len(embeddings.shape) > 1 else 1
        
        # 计算统计信息
        mean_norm = np.mean(np.linalg.norm(embeddings, axis=1))
        std_norm = np.std(np.linalg.norm(embeddings, axis=1))
        
        return {
            "n_samples": n_samples,
            "n_features": n_features,
            "mean_norm": float(mean_norm),
            "std_norm": float(std_norm),
            "density": "high" if n_samples > 100 else "medium" if n_samples > 20 else "low"
        }
    
    def _select_strategy(self, data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """选择聚类策略"""
        n_samples = data_profile["n_samples"]
        density = data_profile["density"]
        
        # 基于数据特征选择策略
        if n_samples < 10:
            # 数据量很小，使用简单的 DBSCAN
            strategy = {
                "method": "dbscan",
                "params": {
                    "eps": 0.5,
                    "min_samples": 2
                }
            }
        elif n_samples < 50:
            # 数据量中等，使用 HDBSCAN
            strategy = {
                "method": "hdbscan",
                "params": {
                    "min_cluster_size": 3,
                    "min_samples": 2,
                    "cluster_selection_epsilon": 0.3
                }
            }
        else:
            # 数据量大，使用 HDBSCAN + 降维
            strategy = {
                "method": "hdbscan_with_umap",
                "params": {
                    "umap_params": {
                        "n_neighbors": 15,
                        "min_dist": 0.1,
                        "n_components": 2
                    },
                    "hdbscan_params": {
                        "min_cluster_size": 5,
                        "min_samples": 3,
                        "cluster_selection_epsilon": 0.4
                    }
                }
            }
        
        return strategy
    
    def _execute_clustering(
        self,
        embeddings: np.ndarray,
        strategy: Dict[str, Any]
    ) -> Tuple[List[int], float]:
        """执行聚类"""
        method = strategy["method"]
        params = strategy["params"]
        
        try:
            if method == "dbscan":
                from sklearn.cluster import DBSCAN
                clusterer = DBSCAN(**params)
                labels = clusterer.fit_predict(embeddings)
            
            elif method == "hdbscan":
                import hdbscan
                clusterer = hdbscan.HDBSCAN(**params)
                labels = clusterer.fit_predict(embeddings)
            
            elif method == "hdbscan_with_umap":
                from umap import UMAP
                import hdbscan
                
                # 先降维
                reducer = UMAP(**params["umap_params"])
                reduced = reducer.fit_transform(embeddings)
                
                # 再聚类
                clusterer = hdbscan.HDBSCAN(**params["hdbscan_params"])
                labels = clusterer.fit_predict(reduced)
            
            else:
                # 默认使用简单的 KMeans
                from sklearn.cluster import KMeans
                n_clusters = min(5, len(embeddings) // 3)
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
                labels = clusterer.fit_predict(embeddings)
            
            # 计算质量分数
            quality_score = self._calculate_quality_score(embeddings, labels)
            
            return labels.tolist(), quality_score
        
        except Exception as e:
            print(f"聚类失败: {e}")
            # 返回默认结果（所有样本归为一类）
            return [0] * len(embeddings), 0.0
    
    def _calculate_quality_score(self, embeddings: np.ndarray, labels: List[int]) -> float:
        """计算聚类质量分数"""
        try:
            from sklearn.metrics import silhouette_score
            
            # 过滤掉噪声点（标签为 -1）
            valid_mask = [l != -1 for l in labels]
            if sum(valid_mask) < 2:
                return 0.0
            
            valid_embeddings = embeddings[valid_mask]
            valid_labels = [l for l, v in zip(labels, valid_mask) if v]
            
            # 检查是否有至少2个不同的簇
            unique_labels = set(valid_labels)
            if len(unique_labels) < 2:
                return 0.0
            
            # 计算轮廓系数
            score = silhouette_score(valid_embeddings, valid_labels)
            
            # 归一化到 0-1
            normalized_score = (score + 1) / 2
            
            return float(normalized_score)
        
        except Exception as e:
            print(f"质量评估失败: {e}")
            return 0.5
    
    def _reflect_and_adjust(
        self,
        strategy: Dict[str, Any],
        quality_score: float,
        data_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """反思并调整策略"""
        
        # 如果质量太低，调整参数
        if quality_score < 0.3:
            # 增加聚类数量
            if strategy["method"] == "hdbscan":
                strategy["params"]["min_cluster_size"] = max(2, strategy["params"]["min_cluster_size"] - 1)
                strategy["params"]["cluster_selection_epsilon"] *= 0.8
            elif strategy["method"] == "dbscan":
                strategy["params"]["eps"] *= 0.8
        
        return strategy
    
    def _generate_gang_info(
        self,
        cases: List[Dict[str, Any]],
        labels: List[int],
        embeddings: np.ndarray
    ) -> List[Dict[str, Any]]:
        """生成团伙信息"""
        
        # 按标签分组
        gang_dict = {}
        for case, label in zip(cases, labels):
            if label == -1:
                continue  # 跳过噪声点
            
            if label not in gang_dict:
                gang_dict[label] = []
            gang_dict[label].append(case)
        
        # 生成团伙信息
        gangs = []
        for gang_id, gang_cases in gang_dict.items():
            if len(gang_cases) < 2:
                continue  # 跳过只有一个案件的团伙
            
            # 计算团伙统计
            total_amount = sum(float(c.get("amount", 0)) for c in gang_cases)
            avg_risk_score = sum(c.get("risk_score", 0) for c in gang_cases) / len(gang_cases)
            
            # 提取共同特征
            fraud_types = [c.get("scam_type", "未知") for c in gang_cases]
            most_common_type = max(set(fraud_types), key=fraud_types.count)
            
            gang_info = {
                "gang_id": f"GANG_{gang_id:03d}",
                "gang_name": f"{most_common_type}犯罪团伙{gang_id + 1}号",
                "total_cases": len(gang_cases),
                "total_amount": total_amount,
                "avg_risk_score": avg_risk_score,
                "risk_level": "HIGH" if avg_risk_score >= 80 else "MEDIUM" if avg_risk_score >= 60 else "LOW",
                "fraud_type": most_common_type,
                "case_ids": [c.get("case_id") for c in gang_cases],
                "description": f"基于{most_common_type}诈骗手法的犯罪团伙，涉及{len(gang_cases)}起案件"
            }
            
            gangs.append(gang_info)
        
        return gangs
