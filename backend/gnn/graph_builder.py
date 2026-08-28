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
    
    def __init__(self, use_db: bool = True, use_cache: bool = True, use_text_channel: bool = True):
        """
        初始化图构建器

        Args:
            use_db: 是否使用数据库持久化
            use_cache: 是否使用Redis缓存
            use_text_channel: 是否启用话术语义通道（A3 双通道并入 GNN，BGE 文本嵌入）
        """
        self.graph = None
        self.node_features = {}
        self.node_text_features = {}  # A3: case 节点文本嵌入（BGE/hash 降级），供 case_text_case 元路径
        self.node_to_idx = {}
        self.idx_to_node = {}
        self.use_db = use_db
        self.use_cache = use_cache
        self.use_text_channel = use_text_channel
        self.redis_client = get_redis() if use_cache else None
        
    def build_graph(
        self,
        cases: List[Dict[str, Any]],
        incremental: bool = False,
        accounts_tx: Optional[List[Dict[str, Any]]] = None
    ) -> nx.Graph:
        """
        从案件列表构建异构图

        Args:
            cases: 案件列表（可携带扩展字段 accounts/perpetrators）
            incremental: 是否增量构建(只处理新案件)
            accounts_tx: 账户间资金流转记录列表，每条 {from_account, to_account, amount, timestamp}

        Returns:
            NetworkX图对象
        """
        # schema 标记：本次是否包含资金/违法者数据（用于缓存/库 schema 校验，规避旧缓存维度错位）
        self._expect_fund = any(
            (case.get('accounts') or case.get('perpetrators')) for case in cases
        )
        # 重置节点索引映射（防止重复 build_graph 残留旧节点导致 KeyError，R10 防御性）
        self.node_to_idx = {}
        self.idx_to_node = {}
        # 尝试从缓存加载
        if not incremental and self.use_cache and self.redis_client:
            cached_graph = self._load_from_cache()
            if cached_graph:
                self.graph = cached_graph
                self._build_node_features()
                self._build_node_text_features(cases)
                return self.graph
        
        # 尝试从数据库加载
        if not incremental and self.use_db:
            db_graph = self._load_from_db()
            if db_graph and len(db_graph.nodes) > 0:
                self.graph = db_graph
                self._build_node_features()
                self._build_node_text_features(cases)
                return self.graph
        
        # 增量更新模式
        if incremental and self.graph:
            return self._incremental_update(cases)
        
        # 构建新图
        G = nx.Graph() if not incremental else self.graph
        if G is None:
            G = nx.Graph()
        
        # 节点类型：case(案件), victim(受害人), phone(电话), scam_type(诈骗类型),
        #           city(城市), account(收款账户), perpetrator(违法者)
        # 注：原注释中的 bank/app 未在代码中实现，本次以 account/perpetrator 落地资金链
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

            # === 资金链：收款账户节点并连接（核心改造）===
            for acc in (case.get('accounts') or []):
                acc = str(acc).strip()
                if not acc:
                    continue
                account_id = f'account_{acc}'
                if account_id not in G:
                    G.add_node(account_id, node_type='account', account_no=acc)
                    self.node_to_idx[account_id] = node_idx
                    self.idx_to_node[node_idx] = account_id
                    node_idx += 1
                G.add_edge(case_id, account_id, relation='has_account')

            # === 资金链：违法者节点并连接（核心改造）===
            for perp in (case.get('perpetrators') or []):
                perp = str(perp).strip()
                if not perp:
                    continue
                perpetrator_id = f'perpetrator_{perp}'
                if perpetrator_id not in G:
                    G.add_node(perpetrator_id, node_type='perpetrator', name=perp)
                    self.node_to_idx[perpetrator_id] = node_idx
                    self.idx_to_node[node_idx] = perpetrator_id
                    node_idx += 1
                G.add_edge(case_id, perpetrator_id, relation='has_perpetrator')
        
        # 添加案件间相似边（基于诈骗类型和地址）—— 辅助通道
        case_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'case']
        for i, case1_id in enumerate(case_nodes):
            for case2_id in case_nodes[i+1:]:
                case1 = G.nodes[case1_id]
                case2 = G.nodes[case2_id]

                similarity = self._calculate_similarity(case1, case2)
                if similarity > 0.3:  # 相似度阈值
                    G.add_edge(case1_id, case2_id, relation='similar', weight=similarity)

        # === 资金链：收款账户重叠边（最强信号，消解假阳性串并）===
        # 两个案件共享同一收款账户 => 高度可能是同一团伙
        account_to_cases = defaultdict(list)
        for n, d in G.nodes(data=True):
            if d.get('node_type') == 'case':
                for nb in G.neighbors(n):
                    if G.nodes[nb].get('node_type') == 'account':
                        account_to_cases[nb].append(n)
        for acc_id, linked_cases in account_to_cases.items():
            for i, c1 in enumerate(linked_cases):
                for c2 in linked_cases[i+1:]:
                    self._add_relation_edge(G, c1, c2, 'share_account', 1.0)

        # === 资金链：违法者重叠边（强信号）===
        perp_to_cases = defaultdict(list)
        for n, d in G.nodes(data=True):
            if d.get('node_type') == 'case':
                for nb in G.neighbors(n):
                    if G.nodes[nb].get('node_type') == 'perpetrator':
                        perp_to_cases[nb].append(n)
        for perp_id, linked_cases in perp_to_cases.items():
            for i, c1 in enumerate(linked_cases):
                for c2 in linked_cases[i+1:]:
                    self._add_relation_edge(G, c1, c2, 'share_perpetrator', 0.8)

        # === 资金链：账户间资金流转边（有向时序，方向/金额/时间存边属性）===
        if accounts_tx:
            for tx in accounts_tx:
                f = str(tx.get('from_account', '')).strip()
                t = str(tx.get('to_account', '')).strip()
                if not f or not t or f == t:
                    continue
                f_id, t_id = f'account_{f}', f'account_{t}'
                for aid in (f_id, t_id):
                    if aid not in G:
                        acc_no = f if aid == f_id else t
                        G.add_node(aid, node_type='account', account_no=acc_no)
                        self.node_to_idx[aid] = node_idx
                        self.idx_to_node[node_idx] = aid
                        node_idx += 1
                G.add_edge(
                    f_id, t_id,
                    relation='fund_flow',
                    amount=float(tx.get('amount', 0) or 0),
                    timestamp=str(tx.get('timestamp', '')),
                    from_account=f,
                    to_account=t
                )
        
        self.graph = G
        self._build_node_features()
        self._build_node_text_features(cases)
        
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
    
    def _add_relation_edge(self, G, u, v, relation, weight):
        """添加案件间关系边；若已存在则合并关系标记（如 share_account+share_perpetrator），取较大权重"""
        if G.has_edge(u, v):
            cur = G[u][v].get('relation', '')
            if relation not in cur.split('+'):
                G[u][v]['relation'] = (cur + '+' + relation).strip('+')
                G[u][v]['weight'] = max(float(G[u][v].get('weight', 0)), weight)
        else:
            G.add_edge(u, v, relation=relation, weight=weight)
    
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
                # 案件特征：金额、风险分数、时间等（结构化，非 hash）
                features = self._encode_case_features(node_data, feature_dim)
            elif node_type == 'account':
                # 收款账户特征：统计特征（去 hash，核心改造）
                features = self._encode_account_features(node_data, feature_dim, self.graph)
            elif node_type == 'perpetrator':
                # 违法者特征：统计特征（去 hash）
                features = self._encode_perpetrator_features(node_data, feature_dim, self.graph)
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

    # ---------- A3: 话术语义通道（双通道并入 GNN） ----------

    def _build_node_text_features(self, cases: Optional[List[Dict[str, Any]]] = None):
        """用 BGE 文本嵌入编码案件话术，作为 HAN 的语义通道（双通道之一）。

        文本取自案件节点上的 script/description/content/text/title 字段。
        若 BGE 不可用，降级为确定性 hash 向量（与 core.embedding 降级一致），保证管道不崩。
        """
        self.node_text_features = {}
        if not self.graph or not self.use_text_channel:
            return
        case_items = []  # [(node_idx, text), ...]
        for node_id, idx in self.node_to_idx.items():
            nd = self.graph.nodes[node_id]
            if nd.get('node_type') != 'case':
                continue
            text = self._extract_case_text(nd)
            if text:
                case_items.append((idx, text))
        if not case_items:
            return  # 无文本 → 不启用语义通道

        texts = [t for _, t in case_items]
        emb_model = None
        try:
            from core.embedding import get_embedding_model
            emb_model = get_embedding_model()
        except Exception:
            emb_model = None
        if emb_model is not None and getattr(emb_model, 'model', None) is not None:
            vecs = emb_model.encode(texts)  # (k, 1024) 归一化
            for (idx, _), v in zip(case_items, vecs):
                self.node_text_features[idx] = np.asarray(v, dtype=np.float32)
        else:
            # 降级：确定性 hash 向量（dim=1024），与 core/embedding._hash_fallback 一致
            for idx, t in case_items:
                self.node_text_features[idx] = self._hash_text_vec(t, dim=1024)

    @staticmethod
    def _extract_case_text(node_data: Dict[str, Any]) -> str:
        """拼接案件文本字段（话术/描述/内容/标题）"""
        parts = []
        for key in ('script', 'description', 'content', 'text', 'title'):
            val = node_data.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        return ' '.join(parts)

    @staticmethod
    def _hash_text_vec(text: str, dim: int = 1024) -> np.ndarray:
        """确定性 hash 降级向量（与 core.embedding._hash_fallback 一致）"""
        h = abs(hash(text)) % (2 ** 32)
        np.random.seed(h)
        v = np.random.randn(dim).astype(np.float32)
        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm
        return v

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
    
    def _encode_account_features(self, account_data: Dict, dim: int, graph: nx.Graph) -> np.ndarray:
        """编码收款账户特征（去 hash，使用可解释统计特征）"""
        features = np.zeros(dim, dtype=np.float32)
        acc_no = account_data.get('account_no', '')
        node_id = f'account_{acc_no}'
        # 关联案件数（入边 case 数）
        in_cases = 0
        total_flow = 0.0
        out_deg = 0
        try:
            for nb in graph.neighbors(node_id):
                if graph.nodes[nb].get('node_type') == 'case':
                    in_cases += 1
            for _, _, edata in graph.edges(node_id, data=True):
                if edata.get('relation') == 'fund_flow':
                    total_flow += float(edata.get('amount', 0) or 0)
                    out_deg += 1
        except Exception:
            pass
        features[0] = min(in_cases / 10.0, 1.0)
        features[1] = min(out_deg / 10.0, 1.0)
        features[2] = min(total_flow / 1_000_000.0, 1.0)
        features[3] = 1.0  # 账户节点标识位
        return features
    
    def _encode_perpetrator_features(self, perp_data: Dict, dim: int, graph: nx.Graph) -> np.ndarray:
        """编码违法者特征（去 hash，使用关联案件数）"""
        features = np.zeros(dim, dtype=np.float32)
        node_id = f'perpetrator_{perp_data.get("name", "")}'
        in_cases = 0
        try:
            for nb in graph.neighbors(node_id):
                if graph.nodes[nb].get('node_type') == 'case':
                    in_cases += 1
        except Exception:
            pass
        features[0] = min(in_cases / 10.0, 1.0)
        features[1] = 1.0  # 违法者节点标识位
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

    def _metapath_text(self, threshold: float = 0.5) -> np.ndarray:
        """A3: 话术语义通道 case_text_case —— case 节点间 BGE 余弦相似度邻接（含自环）。

        与结构化元路径（经账户/违法者/类型/城市 2 跳）并列，在 HAN 语义注意力下融合，
        构成"资金链 + 话术"双通道。无文本特征时返回单位阵（不生效）。

        边为二值（cosine>=threshold 即连边）；阈值 0.5 与 BGE 归一化嵌入的同类/异类分布匹配。
        A-BGE 复测结论：本通道在标准(结构清晰)场景为中性、在结构含噪场景下提供小幅正增益，
        属"辅助判别信号"而非主导信号（详见 docs/04 §六口径）。
        """
        if not self.graph or not self.node_text_features:
            n = len(self.graph.nodes) if self.graph else 0
            return np.eye(n, dtype=np.float32) if n else np.array([])
        N = len(self.graph.nodes)
        M = np.zeros((N, N), dtype=np.float32)
        case_idxs = [
            i for i in range(N)
            if self.graph.nodes[self.idx_to_node[i]].get('node_type') == 'case'
            and i in self.node_text_features
        ]
        for a in range(len(case_idxs)):
            i = case_idxs[a]
            M[i, i] = 1.0  # 自环
            vi = self.node_text_features[i]
            ni = np.linalg.norm(vi)
            for b in range(a + 1, len(case_idxs)):
                j = case_idxs[b]
                vj = self.node_text_features[j]
                nj = np.linalg.norm(vj)
                sim = float(np.dot(vi, vj) / (ni * nj + 1e-9))
                if sim >= threshold:
                    M[i, j] = 1.0
                    M[j, i] = 1.0
        return M

    def get_meta_path_adjacency(self) -> Dict[str, np.ndarray]:
        """获取各元路径的邻接矩阵（真异构：每条元路径拓扑不同）。

        不同于旧实现把同一张全图邻接矩阵复制成 4 份，
        此处按元路径分别构造：
          - case_account_case    : 经收款账户(共享/资金往来)的 2 跳
          - case_perpetrator_case: 经违法者的 2 跳
          - case_type_case       : 经诈骗类型的 2 跳（辅助通道）
          - case_city_case       : 经城市的 2 跳（辅助通道）
        返回 {元路径名: (N×N) 二值邻接矩阵(含自环)}，与 get_node_features 节点顺序一致。
        """
        if not self.graph:
            return {}
        A = nx.to_numpy_array(self.graph)
        A = (A > 0).astype(np.float32)
        N = A.shape[0]
        idx2node = self.idx_to_node  # int -> node_id
        if idx2node is None:
            nodes = list(self.graph.nodes())
            idx2node = {i: n for i, n in enumerate(nodes)}
        node2type = {
            i: self.graph.nodes[idx2node[i]].get('node_type')
            for i in range(N)
        }

        def _metapath(mid_type: str) -> np.ndarray:
            # 构造 case<->mid_type 的二部邻接
            B = np.zeros((N, N), dtype=np.float32)
            for i in range(N):
                ti = node2type[i]
                if ti not in ('case', mid_type):
                    continue
                for j in range(N):
                    tj = node2type[j]
                    if (ti == 'case' and tj == mid_type) or \
                       (ti == mid_type and tj == 'case'):
                        if A[i, j] > 0:
                            B[i, j] = 1.0
            # 2 跳闭包（case-mid-case / mid-case-mid / mid-mid 经共享 case）
            M = B @ B.T
            M = (M > 0).astype(np.float32)
            np.fill_diagonal(M, 1.0)  # 自环
            return M

        adjs = {
            'case_account_case': _metapath('account'),
            'case_perpetrator_case': _metapath('perpetrator'),
            'case_type_case': _metapath('scam_type'),
            'case_city_case': _metapath('city'),
        }
        # A3 双通道：话术语义通道（BGE 文本相似元路径），与结构化通道在 HAN 注意力下融合
        if self.use_text_channel and self.node_text_features:
            adjs['case_text_case'] = self._metapath_text()
        return adjs
    
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
    
    def get_fund_flow_digraph(self) -> nx.DiGraph:
        """抽取资金流转有向子图（仅 fund_flow 边），用于资金回流闭环检测。
        
        节点为 account，边方向由边属性 from_account->to_account 决定
        （主图虽为无向 nx.Graph，但 fund_flow 的方向存于边属性），
        边带 amount / timestamp。返回 nx.DiGraph。
        """
        DG = nx.DiGraph()
        if not self.graph:
            return DG
        for u, v, d in self.graph.edges(data=True):
            if d.get('relation') != 'fund_flow':
                continue
            f = d.get('from_account') or u
            t = d.get('to_account') or v
            f_id, t_id = f'account_{f}', f'account_{t}'
            DG.add_node(f_id, account_no=f)
            DG.add_node(t_id, account_no=t)
            DG.add_edge(f_id, t_id,
                        amount=float(d.get('amount', 0) or 0),
                        timestamp=str(d.get('timestamp', '')))
        return DG
    
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
            
            # schema 校验：本次期望资金数据但库图无 account 节点 => 丢弃重建
            if getattr(self, '_expect_fund', False):
                has_account = any(d.get('node_type') == 'account'
                                  for _, d in G.nodes(data=True))
                if not has_account:
                    return None
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
            
            # schema 校验：本次期望资金数据但缓存图无 account 节点 => 丢弃重建
            if getattr(self, '_expect_fund', False):
                has_account = any(d.get('node_type') == 'account'
                                  for _, d in G.nodes(data=True))
                if not has_account:
                    return None
            return G
        except Exception as e:
            print(f"从缓存加载图失败: {e}")
            return None
    
    def clear_cache(self):
        """清除缓存"""
        if self.redis_client:
            self.redis_client.delete('fraud_graph')
