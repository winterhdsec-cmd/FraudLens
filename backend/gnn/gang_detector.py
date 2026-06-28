"""
GNN团伙发现主控制器
整合图构建、GNN学习、社区检测的完整流程
支持模型持久化、增量更新、优雅降级
"""
import os
import torch
import numpy as np
import networkx as nx
import pickle
import time
from typing import List, Dict, Any, Optional, Callable
from .graph_builder import FraudGraphBuilder
from .gnn_model import GraphSAGE
from .community import CommunityDetector


class GangDetector:
    """诈骗团伙检测器 - 生产级实现"""
    
    def __init__(
        self,
        embedding_dim: int = 128,
        hidden_dim: int = 64,
        num_layers: int = 2,
        community_method: str = 'louvain',
        model_dir: str = None,
        enable_persistence: bool = True,
        enable_fallback: bool = True
    ):
        """
        初始化团伙检测器
        
        Args:
            embedding_dim: 嵌入维度
            hidden_dim: 隐藏层维度
            num_layers: GraphSAGE层数
            community_method: 社区检测方法
            model_dir: 模型保存目录
            enable_persistence: 是否启用模型持久化
            enable_fallback: 是否启用优雅降级
        """
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.community_method = community_method
        self.model_dir = model_dir or os.path.join(os.path.dirname(__file__), 'models')
        self.enable_persistence = enable_persistence
        self.enable_fallback = enable_fallback
        
        # 确保模型目录存在
        if self.enable_persistence:
            os.makedirs(self.model_dir, exist_ok=True)
        
        # 组件
        self.graph_builder = FraudGraphBuilder()
        self.gnn_model = None
        self.community_detector = CommunityDetector(method=community_method)
        
        # 状态
        self.graph = None
        self.embeddings = None
        self.communities = None
        
        # 监控指标
        self.metrics = {
            'last_detect_time': 0,
            'last_train_time': 0,
            'total_detections': 0,
            'fallback_count': 0,
            'cache_hit_count': 0
        }
        
        # 尝试加载已训练模型
        if self.enable_persistence:
            self._try_load_model()
        
    def detect(
        self,
        cases: List[Dict[str, Any]],
        use_gnn: bool = True,
        training_epochs: int = 100,
        incremental: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        检测诈骗团伙 (生产级)
        
        Args:
            cases: 案件列表
            use_gnn: 是否使用GNN学习嵌入
            training_epochs: GNN训练轮数
            incremental: 是否增量更新(只处理新案件)
            progress_callback: 进度回调 fn(stage, percent)
            
        Returns:
            检测结果字典
        """
        t0 = time.time()
        self.metrics['total_detections'] += 1
        
        def _progress(stage: str, percent: float):
            if progress_callback:
                try:
                    progress_callback(stage, percent)
                except Exception:
                    pass
        
        if not cases:
            return {'gangs': [], 'stats': self._empty_stats(), 'communities': {}}
        
        # 1. 构建/更新异构图
        _progress('graph_build', 0.0)
        try:
            self.graph = self.graph_builder.build_graph(cases, incremental=incremental)
        except Exception as e:
            # 优雅降级：图构建失败，回退到简单规则聚类
            if self.enable_fallback:
                self.metrics['fallback_count'] += 1
                return self._fallback_detect(cases, str(e))
            raise
        
        if len(self.graph.nodes) == 0:
            return {'gangs': [], 'stats': self._empty_stats(), 'communities': {}}
        
        _progress('graph_build', 0.2)
        
        # 2. 获取节点嵌入
        _progress('embedding', 0.2)
        embeddings_obtained = False
        
        if use_gnn and len(self.graph.nodes) >= 3:
            try:
                t_train = time.time()
                self.embeddings = self._train_and_embed(
                    training_epochs,
                    progress_callback=lambda p: _progress('training', 0.2 + p * 0.5)
                )
                self.metrics['last_train_time'] = time.time() - t_train
                embeddings_obtained = True
                
                # 持久化模型
                if self.enable_persistence and self.gnn_model is not None:
                    self._save_model()
            except Exception as e:
                if self.enable_fallback:
                    self.metrics['fallback_count'] += 1
                    # 降级：使用原始特征
                    self.embeddings = self.graph_builder.get_node_features()
                    embeddings_obtained = True
                else:
                    raise
        
        if not embeddings_obtained:
            self.embeddings = self.graph_builder.get_node_features()
        
        _progress('community_detect', 0.7)
        
        # 3. 社区检测
        try:
            if self.embeddings is not None and len(self.embeddings) > 0:
                self.communities = self.community_detector.detect(
                    self.graph, self.embeddings
                )
            else:
                self.communities = self.community_detector.detect(self.graph)
        except Exception as e:
            if self.enable_fallback:
                self.metrics['fallback_count'] += 1
                # 降级：使用基于图结构的简单方法
                self.communities = self._fallback_community_detect()
            else:
                raise
        
        _progress('generate_gangs', 0.9)
        
        # 4. 生成团伙信息
        gangs = self._generate_gang_info(cases)
        
        # 5. 统计信息
        stats = self._calculate_stats(gangs)
        self.metrics['last_detect_time'] = time.time() - t0
        
        _progress('done', 1.0)
        
        return {
            'gangs': gangs,
            'stats': stats,
            'communities': self.communities,
            'metrics': {
                'total_time': round(self.metrics['last_detect_time'], 3),
                'train_time': round(self.metrics.get('last_train_time', 0), 3),
                'node_count': len(self.graph.nodes) if self.graph else 0,
                'edge_count': len(self.graph.edges) if self.graph else 0,
                'gang_count': len(gangs),
                'fallback_used': self.metrics['fallback_count'] > 0
            }
        }
    
    def _empty_stats(self) -> Dict[str, Any]:
        """空统计信息"""
        return {
            'total_gangs': 0, 'total_cases': 0, 'total_amount': 0,
            'avg_cases_per_gang': 0, 'high_risk_gangs': 0
        }
    
    def _fallback_detect(self, cases: List[Dict[str, Any]], error_msg: str) -> Dict[str, Any]:
        """优雅降级：GNN失败时回退到规则聚类"""
        from collections import defaultdict
        
        # 按诈骗类型+城市分组
        groups = defaultdict(list)
        for case in cases:
            scam_type = case.get('scam_type', '未知')
            addr = case.get('victim_address', '')
            city = self.graph_builder._extract_city(addr) if addr else '未知'
            key = f"{scam_type}_{city}"
            groups[key].append(case)
        
        gangs = []
        for idx, (key, group_cases) in enumerate(groups.items()):
            if len(group_cases) < 2:
                continue
            
            total_amount = sum(self._safe_float(c.get('amount_value', 0)) for c in group_cases)
            avg_risk = np.mean([self._safe_float(c.get('risk_score', 0)) for c in group_cases])
            
            risk_level = 'HIGH' if avg_risk >= 80 else ('MEDIUM' if avg_risk >= 60 else 'LOW')
            scam_type = key.split('_')[0]
            city = key.split('_')[1] if '_' in key else '未知'
            
            gangs.append({
                'gang_id': f'GANG_RULE_{idx:03d}',
                'case_count': len(group_cases),
                'case_ids': [c.get('case_id', '') for c in group_cases],
                'total_amount': total_amount,
                'avg_risk_score': float(avg_risk),
                'risk_level': risk_level,
                'primary_scam_type': scam_type,
                'scam_type_distribution': {scam_type: len(group_cases)},
                'primary_city': city,
                'city_distribution': {city: len(group_cases)},
                'description': f'[规则降级] {len(group_cases)}起{scam_type}诈骗案件，集中在{city}'
            })
        
        gangs.sort(key=lambda x: x['case_count'], reverse=True)
        
        return {
            'gangs': gangs,
            'stats': self._calculate_stats(gangs),
            'communities': {},
            'metrics': {
                'total_time': 0,
                'train_time': 0,
                'node_count': 0,
                'edge_count': 0,
                'gang_count': len(gangs),
                'fallback_used': True,
                'fallback_reason': error_msg
            }
        }
    
    def _fallback_community_detect(self) -> Dict[int, List[str]]:
        """降级社区检测：基于图连通分量"""
        communities = {}
        for i, component in enumerate(nx.connected_components(self.graph)):
            communities[i] = list(component)
        return communities
    
    def _train_and_embed(
        self,
        epochs: int = 100,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> np.ndarray:
        """
        训练GNN并获取节点嵌入
        支持模型缓存：如果图结构未变，直接复用已训练模型
        
        Args:
            epochs: 训练轮数
            progress_callback: 训练进度回调 fn(percent)
            
        Returns:
            节点嵌入矩阵
        """
        # 获取图数据
        features = self.graph_builder.get_node_features()
        adj = self.graph_builder.get_adjacency_matrix()
        
        if features is None or len(features) == 0:
            return None
        
        # 转换为Tensor
        features_tensor = torch.FloatTensor(features)
        adj_tensor = torch.FloatTensor(adj)
        
        in_dim = features.shape[1]
        
        # 检查是否可复用已训练模型（图结构未变）
        graph_hash = self._compute_graph_hash()
        if self.gnn_model is not None and hasattr(self, '_last_graph_hash') and self._last_graph_hash == graph_hash:
            # 图结构未变，直接用已有模型推理
            self.gnn_model.eval()
            with torch.no_grad():
                embeddings = self.gnn_model(features_tensor, adj_tensor)
            return embeddings.numpy()
        
        # 需要重新训练
        self.gnn_model = GraphSAGE(
            in_dim=in_dim,
            hidden_dim=self.hidden_dim,
            out_dim=self.embedding_dim,
            num_layers=self.num_layers
        )
        
        # 自监督训练（邻接矩阵重构）
        optimizer = torch.optim.Adam(self.gnn_model.parameters(), lr=0.01)
        
        report_interval = max(epochs // 10, 1)
        self.gnn_model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            
            embeddings = self.gnn_model(features_tensor, adj_tensor)
            
            # 重构损失
            reconstructed_adj = torch.sigmoid(torch.matmul(embeddings, embeddings.t()))
            loss = torch.nn.functional.mse_loss(reconstructed_adj, adj_tensor)
            
            loss.backward()
            optimizer.step()
            
            # 进度上报
            if progress_callback and (epoch + 1) % report_interval == 0:
                progress_callback((epoch + 1) / epochs)
        
        # 记录图hash
        self._last_graph_hash = graph_hash
        
        # 获取嵌入
        self.gnn_model.eval()
        with torch.no_grad():
            embeddings = self.gnn_model(features_tensor, adj_tensor)
        
        return embeddings.numpy()
    
    def _compute_graph_hash(self) -> int:
        """计算图结构hash，用于判断是否需要重新训练"""
        if not self.graph:
            return 0
        # 用节点数+边数+节点ID排序作为简易hash
        nodes = sorted(self.graph.nodes())
        return hash((len(nodes), len(self.graph.edges), tuple(nodes[:10])))
    
    def _save_model(self):
        """持久化模型到磁盘"""
        try:
            if self.gnn_model is None:
                return
            model_path = os.path.join(self.model_dir, 'gnn_model.pt')
            meta_path = os.path.join(self.model_dir, 'model_meta.pkl')
            
            torch.save(self.gnn_model.state_dict(), model_path)
            
            meta = {
                'embedding_dim': self.embedding_dim,
                'hidden_dim': self.hidden_dim,
                'num_layers': self.num_layers,
                'graph_hash': getattr(self, '_last_graph_hash', 0),
                'trained_at': time.time()
            }
            with open(meta_path, 'wb') as f:
                pickle.dump(meta, f)
        except Exception:
            pass  # 持久化失败不影响主流程
    
    def _try_load_model(self):
        """尝试从磁盘加载已训练模型"""
        try:
            model_path = os.path.join(self.model_dir, 'gnn_model.pt')
            meta_path = os.path.join(self.model_dir, 'model_meta.pkl')
            
            if not os.path.exists(model_path) or not os.path.exists(meta_path):
                return
            
            with open(meta_path, 'rb') as f:
                meta = pickle.load(f)
            
            # 用保存的元数据重建模型结构
            # 注意：in_dim 需要图数据才能确定，这里先不加载权重
            # 等 detect() 时根据实际 in_dim 加载
            self._saved_meta = meta
            self._saved_model_path = model_path
        except Exception:
            pass
    
    @staticmethod
    def _safe_float(val, default=0.0) -> float:
        """安全转换为float"""
        try:
            return float(val) if val != '' and val is not None else default
        except (ValueError, TypeError):
            return default
    
    def _generate_gang_info(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成团伙信息
        
        Args:
            cases: 案件列表
            
        Returns:
            团伙信息列表
        """
        if not self.communities:
            return []
        
        gangs = []
        case_map = {case['case_id']: case for case in cases}
        
        for gang_id, node_ids in self.communities.items():
            # 提取案件节点
            gang_cases = []
            for node_id in node_ids:
                if node_id in case_map:
                    gang_cases.append(case_map[node_id])
            
            if len(gang_cases) < 2:
                continue  # 至少2个案件才构成团伙
            
            # 计算团伙特征
            total_amount = sum(self._safe_float(case.get('amount_value', 0)) for case in gang_cases)
            avg_risk = np.mean([self._safe_float(case.get('risk_score', 0)) for case in gang_cases])
            
            # 诈骗类型分布
            scam_types = [case.get('scam_type', '') for case in gang_cases]
            type_counts = {}
            for t in scam_types:
                type_counts[t] = type_counts.get(t, 0) + 1
            primary_type = max(type_counts, key=type_counts.get) if type_counts else '未知'
            
            # 地域分布
            cities = []
            for case in gang_cases:
                addr = case.get('victim_address', '')
                if '市' in addr:
                    city = addr.split('市')[0] + '市'
                    cities.append(city)
            city_counts = {}
            for c in cities:
                city_counts[c] = city_counts.get(c, 0) + 1
            primary_city = max(city_counts, key=city_counts.get) if city_counts else '未知'
            
            # 风险等级
            if avg_risk >= 80:
                risk_level = 'HIGH'
            elif avg_risk >= 60:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            gang_info = {
                'gang_id': f'GANG_{int(gang_id):03d}',
                'case_count': len(gang_cases),
                'case_ids': [case['case_id'] for case in gang_cases],
                'total_amount': total_amount,
                'avg_risk_score': float(avg_risk),
                'risk_level': risk_level,
                'primary_scam_type': primary_type,
                'scam_type_distribution': type_counts,
                'primary_city': primary_city,
                'city_distribution': city_counts,
                'description': f'该团伙涉及{len(gang_cases)}起案件，主要为{primary_type}诈骗，'
                             f'集中在{primary_city}地区，涉案金额{total_amount:.2f}元'
            }
            
            gangs.append(gang_info)
        
        # 按案件数量排序
        gangs.sort(key=lambda x: x['case_count'], reverse=True)
        
        return gangs
    
    def _calculate_stats(self, gangs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算统计信息
        
        Args:
            gangs: 团伙列表
            
        Returns:
            统计信息字典
        """
        if not gangs:
            return {
                'total_gangs': 0,
                'total_cases': 0,
                'total_amount': 0,
                'avg_cases_per_gang': 0,
                'high_risk_gangs': 0
            }
        
        total_cases = sum(gang['case_count'] for gang in gangs)
        total_amount = sum(gang['total_amount'] for gang in gangs)
        high_risk_gangs = sum(1 for gang in gangs if gang['risk_level'] == 'HIGH')
        
        stats = {
            'total_gangs': len(gangs),
            'total_cases': total_cases,
            'total_amount': total_amount,
            'avg_cases_per_gang': total_cases / len(gangs) if gangs else 0,
            'high_risk_gangs': high_risk_gangs,
            'risk_distribution': {
                'HIGH': sum(1 for g in gangs if g['risk_level'] == 'HIGH'),
                'MEDIUM': sum(1 for g in gangs if g['risk_level'] == 'MEDIUM'),
                'LOW': sum(1 for g in gangs if g['risk_level'] == 'LOW')
            }
        }
        
        return stats
    
    def get_graph_visualization_data(self) -> Dict[str, Any]:
        """
        获取图可视化数据
        
        Returns:
            可视化数据字典
        """
        if self.graph is None:
            return {'nodes': [], 'edges': []}
        
        # 节点数据
        nodes = []
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get('node_type', 'unknown')
            
            # 获取社区标签
            community_id = -1
            for comm_id, members in self.communities.items():
                if node_id in members:
                    community_id = comm_id
                    break
            
            nodes.append({
                'id': node_id,
                'type': node_type,
                'community': community_id,
                **node_data
            })
        
        # 边数据
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                'source': u,
                'target': v,
                **data
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
