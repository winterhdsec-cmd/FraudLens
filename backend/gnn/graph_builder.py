"""
异构图构建器
从案件数据构建诈骗关联图
支持从数据库加载/保存，增量更新
"""
import networkx as nx
import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict
from tools.redis_utils import get_redis
import json


class FraudGraphBuilder:
    """诈骗关联图构建器"""
    
    def __init__(self, use_db: bool = True, use_cache: bool = True):
        """
        初始化图构建器
        
        Args:
            use_db: 是否使用数据库持久化
            use_cache: 是否使用Redis缓存
        """
        self.graph = None
        self.node_features = {}
        self.node_to_idx = {}
        self.idx_to_node = {}
        self.use_db = use_db
        self.use_cache = use_cache
        self.redis_client = get_redis() if use_cache else None
        
    def build_graph(self, cases: List[Dict[str, Any]], incremental: bool = False) -> nx.Graph:
        """
        从案件列表构建异构图
        
        Args:
            cases: 案件列表
            incremental: 是否增量构建(只处理新案件)
            
        Returns:
            NetworkX图对象
        """
        # 尝试从缓存加载
        if not incremental and self.use_cache and self.redis_client:
            cached_graph = self._load_from_cache()
            if cached_graph:
                self.graph = cached_graph
                self._build_node_features()
                return self.graph
        
        # 尝试从数据库加载
        if not incremental and self.use_db:
            db_graph = self._load_from_db()
            if db_graph and len(db_graph.nodes) > 0:
                self.graph = db_graph
                self._build_node_features()
                return self.graph
        
        # 增量更新模式
        if incremental and self.graph:
            return self._incremental_update(cases)
        
        # 构建新图
        G = nx.Graph() if not incremental else self.graph
        if G is None:
            G = nx.Graph()
        
        # 节点类型：case(案件), victim(受害人), phone(电话), bank(银行卡), app(应用)
        node_idx = 0
        
        for case in cases:
            case_id = case.get('case_id', f'case_{node_idx}')
            
            # 添加案件节点
            if case_id not in G:
                G.add_node(case_id, node_type='case', **case)
                self.node_to_idx[case_id] = node_idx
                self.idx_to_node[node_idx] = case_id
                node_idx += 1
            
            # 添加受害人节点并连接
            victim_name = case.get('victim_name', '').strip()
            if victim_name:
                victim_id = f'victim_{victim_name}'
                if victim_id not in G:
                    G.add_node(victim_id, node_type='victim', name=victim_name)
                    self.node_to_idx[victim_id] = node_idx
                    self.idx_to_node[node_idx] = victim_id
                    node_idx += 1
                G.add_edge(case_id, victim_id, relation='has_victim')
            
            # 添加电话节点并连接
            victim_phone = case.get('victim_phone', '').strip()
            if victim_phone:
                phone_id = f'phone_{victim_phone}'
                if phone_id not in G:
                    G.add_node(phone_id, node_type='phone', number=victim_phone)
                    self.node_to_idx[phone_id] = node_idx
                    self.idx_to_node[node_idx] = phone_id
                    node_idx += 1
                G.add_edge(case_id, phone_id, relation='has_phone')
            
            # 添加诈骗类型节点并连接
            scam_type = case.get('scam_type', '').strip()
            if scam_type:
                type_id = f'type_{scam_type}'
                if type_id not in G:
                    G.add_node(type_id, node_type='scam_type', name=scam_type)
                    self.node_to_idx[type_id] = node_idx
                    self.idx_to_node[node_idx] = type_id
                    node_idx += 1
                G.add_edge(case_id, type_id, relation='is_type')
            
            # 添加地址节点并连接（用于发现地域关联）
            victim_address = case.get('victim_address', '').strip()
            if victim_address:
                # 提取城市级别
                city = self._extract_city(victim_address)
                if city:
                    city_id = f'city_{city}'
                    if city_id not in G:
                        G.add_node(city_id, node_type='city', name=city)
                        self.node_to_idx[city_id] = node_idx
                        self.idx_to_node[node_idx] = city_id
                        node_idx += 1
                    G.add_edge(case_id, city_id, relation='in_city')
        
        # 添加案件间相似边（基于诈骗类型和地址）
        case_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'case']
        for i, case1_id in enumerate(case_nodes):
            for case2_id in case_nodes[i+1:]:
                case1 = G.nodes[case1_id]
                case2 = G.nodes[case2_id]
                
                similarity = self._calculate_similarity(case1, case2)
                if similarity > 0.3:  # 相似度阈值
                    G.add_edge(case1_id, case2_id, relation='similar', weight=similarity)
        
        self.graph = G
        self._build_node_features()
        
        # 保存到数据库和缓存
        if self.use_db:
            self._save_to_db()
        if self.use_cache and self.redis_client:
            self._save_to_cache()
        
        return G
    
    def _extract_city(self, address: str) -> str:
        """从地址提取城市"""
        # 简单规则：提取"省"后、"市"前的部分
        if '省' in address:
            parts = address.split('省')
            if len(parts) > 1:
                city_part = parts[1]
                if '市' in city_part:
                    return city_part.split('市')[0] + '市'
        elif '市' in address:
            return address.split('市')[0] + '市'
        return ''
    
    def _calculate_similarity(self, case1: Dict, case2: Dict) -> float:
        """计算两个案件的相似度"""
        similarity = 0.0
        weights = {'type': 0.4, 'city': 0.3, 'amount': 0.3}
        
        # 诈骗类型相似度
        if case1.get('scam_type') == case2.get('scam_type'):
            similarity += weights['type']
        
        # 地域相似度
        city1 = self._extract_city(case1.get('victim_address', ''))
        city2 = self._extract_city(case2.get('victim_address', ''))
        if city1 and city2 and city1 == city2:
            similarity += weights['city']
        
        # 金额相似度（归一化到0-1）
        amount1 = float(case1.get('amount_value', 0))
        amount2 = float(case2.get('amount_value', 0))
        if amount1 > 0 and amount2 > 0:
            max_amount = max(amount1, amount2)
            min_amount = min(amount1, amount2)
            amount_sim = min_amount / max_amount
            similarity += weights['amount'] * amount_sim
        
        return similarity
    
    def _build_node_features(self):
        """构建节点特征矩阵"""
        if not self.graph:
            return
        
        num_nodes = len(self.graph.nodes)
        feature_dim = 128  # 特征维度
        
        # 初始化特征矩阵
        self.node_features = np.zeros((num_nodes, feature_dim), dtype=np.float32)
        
        for node_id, idx in self.node_to_idx.items():
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get('node_type', 'unknown')
            
            # 根据节点类型生成特征
            if node_type == 'case':
                # 案件特征：金额、风险分数、时间等
                features = self._encode_case_features(node_data, feature_dim)
            elif node_type == 'victim':
                # 受害人特征：年龄、性别等
                features = self._encode_victim_features(node_data, feature_dim)
            elif node_type == 'phone':
                # 电话特征：号段等
                features = self._encode_phone_features(node_data, feature_dim)
            elif node_type == 'scam_type':
                # 诈骗类型特征：one-hot编码
                features = self._encode_type_features(node_data, feature_dim)
            elif node_type == 'city':
                # 城市特征：one-hot编码
                features = self._encode_city_features(node_data, feature_dim)
            else:
                features = np.zeros(feature_dim, dtype=np.float32)
            
            self.node_features[idx] = features
    
    @staticmethod
    def _safe_float(val, default=0.0) -> float:
        """安全转换为float"""
        try:
            return float(val) if val != '' and val is not None else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _safe_int(val, default=0) -> int:
        """安全转换为int"""
        try:
            return int(val) if val != '' and val is not None else default
        except (ValueError, TypeError):
            return default
    
    def _encode_case_features(self, case_data: Dict, dim: int) -> np.ndarray:
        """编码案件特征"""
        features = np.zeros(dim, dtype=np.float32)
        
        # 金额归一化（假设最大金额100万）
        amount = self._safe_float(case_data.get('amount_value', 0))
        features[0] = min(amount / 1000000, 1.0)
        
        # 风险分数
        risk_score = self._safe_float(case_data.get('risk_score', 0))
        features[1] = risk_score / 100.0
        
        # 诈骗类型one-hot（简化为前10维）
        scam_type = case_data.get('scam_type', '')
        type_hash = hash(scam_type) % 10
        features[2 + type_hash] = 1.0
        
        # 受害人年龄
        age = self._safe_int(case_data.get('victim_age', 0))
        features[12] = min(age / 100.0, 1.0)
        
        # 受害人性别
        gender = case_data.get('victim_gender', '')
        features[13] = 1.0 if gender == '男' else 0.0
        
        return features
    
    def _encode_victim_features(self, victim_data: Dict, dim: int) -> np.ndarray:
        """编码受害人特征"""
        features = np.zeros(dim, dtype=np.float32)
        name = victim_data.get('name', '')
        # 使用名字hash作为特征
        name_hash = hash(name) % dim
        features[name_hash] = 1.0
        return features
    
    def _encode_phone_features(self, phone_data: Dict, dim: int) -> np.ndarray:
        """编码电话特征"""
        features = np.zeros(dim, dtype=np.float32)
        number = phone_data.get('number', '')
        # 提取号段（前3位）
        if len(number) >= 3:
            prefix = number[:3]
            prefix_hash = hash(prefix) % dim
            features[prefix_hash] = 1.0
        return features
    
    def _encode_type_features(self, type_data: Dict, dim: int) -> np.ndarray:
        """编码诈骗类型特征"""
        features = np.zeros(dim, dtype=np.float32)
        type_name = type_data.get('name', '')
        type_hash = hash(type_name) % dim
        features[type_hash] = 1.0
        return features
    
    def _encode_city_features(self, city_data: Dict, dim: int) -> np.ndarray:
        """编码城市特征"""
        features = np.zeros(dim, dtype=np.float32)
        city_name = city_data.get('name', '')
        city_hash = hash(city_name) % dim
        features[city_hash] = 1.0
        return features
    
    def get_adjacency_matrix(self) -> np.ndarray:
        """获取邻接矩阵"""
        if not self.graph:
            return np.array([])
        return nx.to_numpy_array(self.graph)
    
    def get_node_features(self) -> np.ndarray:
        """获取节点特征矩阵"""
        return self.node_features
    
    def get_edge_index(self) -> np.ndarray:
        """获取边索引（用于GNN）"""
        if not self.graph:
            return np.array([[], []])
        
        edges = list(self.graph.edges)
        if not edges:
            return np.array([[], []])
        
        edge_index = np.array([[self.node_to_idx[u], self.node_to_idx[v]] 
                               for u, v in edges]).T
        return edge_index
    
    def _save_to_db(self):
        """保存图到数据库"""
        try:
            from database import db
            from database.models import GraphNode, GraphEdge
            
            # 保存节点
            for node_id, data in self.graph.nodes(data=True):
                node_type = data.get('node_type', 'unknown')
                features = {k: v for k, v in data.items() if k != 'node_type'}
                
                existing = GraphNode.query.filter_by(node_id=node_id).first()
                if existing:
                    existing.node_type = node_type
                    existing.features = features
                else:
                    new_node = GraphNode(node_id=node_id, node_type=node_type, features=features)
                    db.session.add(new_node)
            
            # 保存边
            for u, v, data in self.graph.edges(data=True):
                relation = data.get('relation', 'unknown')
                weight = data.get('weight', 1.0)
                properties = {k: v for k, v in data.items() if k not in ['relation', 'weight']}
                
                existing = GraphEdge.query.filter_by(source_id=u, target_id=v, relation=relation).first()
                if not existing:
                    new_edge = GraphEdge(
                        source_id=u, target_id=v, relation=relation,
                        weight=weight, properties=properties
                    )
                    db.session.add(new_edge)
            
            db.session.commit()
        except Exception as e:
            print(f"保存图到数据库失败: {e}")
            db.session.rollback()
    
    def _load_from_db(self) -> Optional[nx.Graph]:
        """从数据库加载图"""
        try:
            from database.models import GraphNode, GraphEdge
            
            nodes = GraphNode.query.all()
            edges = GraphEdge.query.all()
            
            if not nodes:
                return None
            
            G = nx.Graph()
            
            # 加载节点
            for node in nodes:
                G.add_node(node.node_id, node_type=node.node_type, **(node.features or {}))
            
            # 加载边
            for edge in edges:
                G.add_edge(edge.source_id, edge.target_id, relation=edge.relation,
                          weight=edge.weight, **(edge.properties or {}))
            
            return G
        except Exception as e:
            print(f"从数据库加载图失败: {e}")
            return None
    
    def _save_to_cache(self):
        """保存图到Redis缓存"""
        try:
            if not self.redis_client:
                return
            
            # 序列化图数据
            nodes = []
            for node_id, data in self.graph.nodes(data=True):
                nodes.append({'id': node_id, 'data': data})
            
            edges = []
            for u, v, data in self.graph.edges(data=True):
                edges.append({'source': u, 'target': v, 'data': data})
            
            cache_data = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False)
            self.redis_client.setex('fraud_graph', 3600, cache_data)  # 1小时过期
        except Exception as e:
            print(f"保存图到缓存失败: {e}")
    
    def _load_from_cache(self) -> Optional[nx.Graph]:
        """从Redis缓存加载图"""
        try:
            if not self.redis_client:
                return None
            
            cache_data = self.redis_client.get('fraud_graph')
            if not cache_data:
                return None
            
            data = json.loads(cache_data)
            G = nx.Graph()
            
            # 加载节点
            for node in data['nodes']:
                G.add_node(node['id'], **node['data'])
            
            # 加载边
            for edge in data['edges']:
                G.add_edge(edge['source'], edge['target'], **edge['data'])
            
            return G
        except Exception as e:
            print(f"从缓存加载图失败: {e}")
            return None
    
    def clear_cache(self):
        """清除缓存"""
        if self.redis_client:
            self.redis_client.delete('fraud_graph')
