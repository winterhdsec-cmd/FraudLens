"""
GNN团伙发现主控制器
整合图构建、GNN学习、社区检测的完整流程
支持模型持久化、增量更新、优雅降级
支持 HAN 异构图注意力网络和深度聚类
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
from .han_model import FraudHAN, GraphCLTrainer
from .deep_clustering import AdvancedCommunityDetector
from .ablation import compute_gate_decision, GATE_DEFAULT
from core.logger import logger


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
        enable_fallback: bool = True,
        use_han: bool = True,  # 启用HAN
        use_deep_clustering: bool = True,  # 启用深度聚类
        enable_gating: bool = True,  # 经验加权置信度门控（#8 消融可关）
        use_text_channel: bool = True,  # 话术语义通道（A3 双通道并入 GNN，消融可关）
        gating_mode: str = "heuristic",  # 门控模式：'heuristic'(默认经验加权) | 'learned'(可学习逻辑回归)
        learned_gate=None,  # 可学习门控模型（gnn.learned_gating.LogisticGate），gating_mode='learned' 时用
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
            use_han: 是否使用 HAN 异构图注意力网络
            use_deep_clustering: 是否使用深度聚类
            enable_gating: 经验加权门控总开关（#8 消融可关，默认开）
            gating_mode: 门控模式选择；'heuristic' 走经验加权置信度，'learned' 走可学习逻辑回归门控
            learned_gate: 预训练的 LogisticGate 模型；gating_mode='learned' 且未传入时惰性取默认合成真值模型
        """
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.community_method = community_method
        self.model_dir = model_dir or os.path.join(os.path.dirname(__file__), 'models')
        self.enable_persistence = enable_persistence
        self.enable_fallback = enable_fallback
        self.use_han = use_han
        self.use_deep_clustering = use_deep_clustering
        # 经验加权置信度门控开关：默认开启；env ENABLE_CONFIDENCE_GATING=false 或 enable_gating=False（#8 消融）时关闭
        self.enable_gating = enable_gating and (
            os.getenv("ENABLE_CONFIDENCE_GATING", "true").lower() != "false"
        )
        # REQ-S3.6 门控模式：默认经验加权；'learned' 可插拔可学习逻辑回归门控（默认不启用，不退化）
        self.gating_mode = gating_mode if gating_mode in ("heuristic", "learned") else "heuristic"
        self.learned_gate = learned_gate
        # A3 双通道开关：默认开启；env USE_TEXT_CHANNEL=false 或 use_text_channel=False（双通道消融）时关闭
        self.use_text_channel = use_text_channel and (
            os.getenv("USE_TEXT_CHANNEL", "true").lower() != "false"
        )
        
        # 确保模型目录存在
        if self.enable_persistence:
            os.makedirs(self.model_dir, exist_ok=True)
        
        # 组件
        # A4.3 推荐方案①：研判(detect)强制从源(案件)重建图，绝不 load Redis/MySQL 旧图，
        # 消除“图不落库”与“缓存/库旧图 stale”隐患。前端展示用的图快照由 persist_graph_snapshot 单独写回。
        self.graph_builder = FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=self.use_text_channel)
        self.gnn_model = None
        self.han_model = None
        
        # 根据配置选择社区检测方法
        if use_deep_clustering:
            self.community_detector = AdvancedCommunityDetector(method='deep_clustering')
            logger.info("Using AdvancedCommunityDetector with deep_clustering")
        else:
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
        accounts_tx: Optional[List[Dict[str, Any]]] = None,
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
            self.graph = self.graph_builder.build_graph(
                cases, incremental=incremental, accounts_tx=accounts_tx)
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
                
                # 持久化模型（gnn 或 han 任一存在即保存，修复 use_han 时从不落盘）
                if self.enable_persistence and (
                        self.gnn_model is not None or self.han_model is not None):
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
        
        # A4.3 推荐方案①：研判从源重建后，显式写“干净图快照”供前端展示（独立 try，失败不影响研判返回）
        self.persist_graph_snapshot()
        
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
    
    def persist_graph_snapshot(self):
        """研判完成后把从源重建的图快照写回 DB+Redis，供前端展示最近一次图（A4.3 推荐方案①）。

        研判本身走 use_db=False 的 builder 从源重建，绝不 load 旧图（防 stale）；
        此处用默认 builder（use_db=True, use_cache=True）承载本次图并持久化，
        前端图端点（读 DB/Redis）即可取到“最近一次研判结果”。
        先 truncate 旧快照避免脏数据残留（GraphNode/GraphEdge 仅作展示，无业务真值）。
        """
        try:
            if self.graph is None:
                return
            from database import db
            from database.models import GraphNode, GraphEdge
            # 先清旧快照，保证前端看到的是“最近一次”干净图
            GraphEdge.query.delete()
            GraphNode.query.delete()
            db.session.commit()
            # 用默认 builder 承载本次图并持久化（写 DB + Redis）
            snap = FraudGraphBuilder(use_db=True, use_cache=True)
            snap.graph = self.graph
            snap.node_features = self.graph_builder.node_features
            snap.node_to_idx = self.graph_builder.node_to_idx
            snap.idx_to_node = self.graph_builder.idx_to_node
            snap._save_to_db()
            snap._save_to_cache()
        except Exception as e:
            logger.warning(f"图快照持久化失败(仅供前端展示，不影响研判): {e}")

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
        支持 GraphSAGE 和 HAN 两种模型
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
        
        # 根据配置选择模型
        if self.use_han:
            return self._train_han(features_tensor, adj_tensor, graph_hash, epochs, progress_callback)
        else:
            return self._train_graphsage(features_tensor, adj_tensor, graph_hash, epochs, progress_callback)
    
    def _train_graphsage(
        self,
        features_tensor: torch.Tensor,
        adj_tensor: torch.Tensor,
        graph_hash: int,
        epochs: int,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> np.ndarray:
        """使用 GraphSAGE 训练"""
        # 检查是否可复用
        if self.gnn_model is not None and hasattr(self, '_last_graph_hash') and self._last_graph_hash == graph_hash:
            self.gnn_model.eval()
            with torch.no_grad():
                embeddings = self.gnn_model(features_tensor, adj_tensor)
            return embeddings.numpy()
        
        in_dim = features_tensor.shape[1]
        
        # 创建模型
        self.gnn_model = GraphSAGE(
            in_dim=in_dim,
            hidden_dim=self.hidden_dim,
            out_dim=self.embedding_dim,
            num_layers=self.num_layers
        )
        self._last_in_dim = in_dim

        # 尝试加载已保存权重（图hash/维度匹配则跳过重训）
        if self._maybe_load_saved_weights(self.gnn_model, graph_hash, in_dim):
            self._last_graph_hash = graph_hash
            self.gnn_model.eval()
            with torch.no_grad():
                embeddings = self.gnn_model(features_tensor, adj_tensor)
            return embeddings.numpy()

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
    
    def _build_meta_path_adjs(self) -> Dict[str, torch.Tensor]:
        """从图构建器获取真异构元路径邻接矩阵并转为 tensor。

        每条元路径对应不同拓扑（经账户/违法者/类型/城市的 2 跳），
        替代旧实现中"同一张全图邻接矩阵复制 4 份"的假异构。
        """
        np_adjs = self.graph_builder.get_meta_path_adjacency()
        if not np_adjs:
            # 兜底：退化为单位阵（仍保证 HAN 可前向）
            n = self.graph_builder.get_node_features().shape[0] if \
                self.graph_builder.get_node_features() is not None else 1
            ident = np.eye(n, dtype=np.float32)
            return {mp: torch.FloatTensor(ident) for mp in
                    ["case_account_case", "case_perpetrator_case",
                     "case_type_case", "case_city_case", "case_text_case"]}
        return {k: torch.FloatTensor(v) for k, v in np_adjs.items()}

    def _train_han(
        self,
        features_tensor: torch.Tensor,
        adj_tensor: torch.Tensor,
        graph_hash: int,
        epochs: int,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> np.ndarray:
        """使用 HAN 异构图注意力网络训练"""
        # 检查是否可复用
        current_meta_paths = list(getattr(self, '_han_meta_paths', []) or [])
        if self.han_model is not None and hasattr(self, '_last_graph_hash') and self._last_graph_hash == graph_hash \
                and current_meta_paths == self.han_model.meta_paths:
            self.han_model.eval()
            with torch.no_grad():
                meta_path_adjs = self._build_meta_path_adjs()
                embeddings = self.han_model.han(features_tensor, meta_path_adjs)
            return embeddings.numpy()

        in_dim = features_tensor.shape[1]

        # 创建 HAN 模型
        self.han_model = FraudHAN(
            in_dim=in_dim,
            hidden_dim=self.hidden_dim,
            embedding_dim=self.embedding_dim,
            num_classes=10,
            num_heads=4,
            num_layers=self.num_layers
        )
        self._han_meta_paths = list(self.han_model.meta_paths)
        self._last_in_dim = in_dim

        # 尝试加载已保存权重（模型类型/维度/图hash 匹配则跳过重训）
        if self._maybe_load_saved_weights(self.han_model, graph_hash, in_dim):
            self._last_graph_hash = graph_hash
            self.han_model.eval()
            with torch.no_grad():
                meta_path_adjs = self._build_meta_path_adjs()
                embeddings = self.han_model.han(features_tensor, meta_path_adjs)
            return embeddings.numpy()

        # 构建元路径邻接矩阵（真异构：每条元路径拓扑不同）
        meta_path_adjs = self._build_meta_path_adjs()
        
        # 使用图对比学习训练
        trainer = GraphCLTrainer(
            model=self.han_model,
            temperature=0.5,
            learning_rate=0.001
        )
        
        # 预训练（自监督）
        logger.info("Starting HAN pretraining with GraphCL")
        history = trainer.pretrain(
            features=features_tensor,
            meta_path_adjs=meta_path_adjs,
            num_epochs=epochs,
            batch_size=min(256, features_tensor.shape[0])
        )
        
        # 记录图hash
        self._last_graph_hash = graph_hash
        
        # 获取嵌入
        self.han_model.eval()
        with torch.no_grad():
            embeddings = self.han_model.han(features_tensor, meta_path_adjs)
        
        logger.info("HAN training completed", final_loss=history['loss'][-1] if history['loss'] else 0)
        
        return embeddings.numpy()
    
    def _compute_graph_hash(self) -> int:
        """计算图结构hash，用于判断是否需要重新训练"""
        if not self.graph:
            return 0
        # 用节点数+边数+节点ID排序作为简易hash
        nodes = sorted(self.graph.nodes())
        return hash((len(nodes), len(self.graph.edges), tuple(nodes[:10])))
    
    def _save_model(self):
        """持久化模型到磁盘（修复：use_han=True 时 gnn_model 为 None，
        旧实现直接 return 导致 HAN 权重从不落盘——死代码）"""
        try:
            model = self.gnn_model if self.gnn_model is not None else self.han_model
            if model is None:
                return
            model_type = 'graphsage' if self.gnn_model is not None else 'han'
            model_path = os.path.join(self.model_dir, f'{model_type}_model.pt')
            meta_path = os.path.join(self.model_dir, f'{model_type}_meta.pkl')

            torch.save(model.state_dict(), model_path)

            meta = {
                'model_type': model_type,
                'embedding_dim': self.embedding_dim,
                'hidden_dim': self.hidden_dim,
                'num_layers': self.num_layers,
                'in_dim': getattr(self, '_last_in_dim', 0),
                'graph_hash': getattr(self, '_last_graph_hash', 0),
                'trained_at': time.time()
            }
            with open(meta_path, 'wb') as f:
                pickle.dump(meta, f)
        except Exception:
            pass  # 持久化失败不影响主流程

    def _try_load_model(self):
        """尝试从磁盘加载已训练模型（修复：旧实现只记录路径从不真正加载，
        _saved_meta/_saved_model_path 全库无读取处——死代码）"""
        try:
            for model_type in ('graphsage', 'han'):
                model_path = os.path.join(self.model_dir, f'{model_type}_model.pt')
                meta_path = os.path.join(self.model_dir, f'{model_type}_meta.pkl')

                if not os.path.exists(model_path) or not os.path.exists(meta_path):
                    continue
                with open(meta_path, 'rb') as f:
                    meta = pickle.load(f)
                if meta.get('model_type') != model_type:
                    continue
                self._saved_meta = meta
                self._saved_model_path = model_path
                self._saved_model_type = model_type
                self._saved_state = torch.load(
                    model_path, map_location='cpu', weights_only=True)
        except Exception:
            self._saved_state = None

    def _maybe_load_saved_weights(self, model, graph_hash: int, in_dim: int):
        """训练前尝试加载已保存权重（须模型类型/维度/图hash 全匹配，否则返回 False 走重训）。

        返回 True 表示加载成功，调用方跳过训练直接用缓存嵌入。
        """
        try:
            meta = getattr(self, '_saved_meta', None)
            if not meta:
                return False
            if meta.get('graph_hash', -1) != graph_hash:
                return False
            if meta.get('in_dim', in_dim) != in_dim:
                return False
            st = getattr(self, '_saved_state', None)
            if st is None:
                return False
            model.load_state_dict(st)
            logger.info("已从磁盘加载模型权重（图结构匹配，跳过重训）")
            return True
        except Exception as e:
            logger.warning(f"加载保存权重失败(走重训): {e}")
            return False
    
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
        # 资金回流闭环检测（客观，依赖图拓扑 + fund_flow 方向）
        reflux_map = self.detect_reflux_cycles(self.communities)
        
        for gang_id, node_ids in self.communities.items():
            # 提取案件节点与资金链节点
            gang_cases = []
            related_accounts = []
            related_perpetrators = []
            rc = reflux_map.get(gang_id, {'cycles': [], 'is_reflux': False})
            for node_id in node_ids:
                node_type = None
                if self.graph is not None and node_id in self.graph:
                    node_type = self.graph.nodes[node_id].get('node_type')
                if node_type == 'account':
                    related_accounts.append(self.graph.nodes[node_id].get('account_no', node_id))
                elif node_type == 'perpetrator':
                    related_perpetrators.append(self.graph.nodes[node_id].get('name', node_id))
                elif node_id in case_map:
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
            
            # 经验加权置信度（不依赖 LLM 自评）：规模 + 资金 + 账户 + 回流闭环 启发式加权
            scale_norm = min(len(gang_cases) / 8.0, 1.0)
            amount_norm = min(total_amount / 1_000_000.0, 1.0)
            acc_norm = min(len(related_accounts) / 3.0, 1.0)
            reflux_flag = 1.0 if rc['is_reflux'] else 0.0
            confidence = round(
                0.30 * scale_norm + 0.20 * amount_norm
                + 0.20 * acc_norm + 0.30 * reflux_flag, 3)
            # 经验加权置信度门控：过阈值才输出冻结建议，否则交人工复核（契合 B5：绝不模型猜测定冻卡）
            # 去门控消融（#8）：gating_enabled=False 时一律建议冻结（不再拦截低置信团伙）
            if self.gating_mode == "learned":
                # REQ-S3.6 可插拔可学习逻辑回归门控：从合成真值训练，数据驱动阈值（默认不启用，不退化）
                from gnn.learned_gating import compute_learned_gate_decision, build_features
                _feats = build_features(scale_norm, amount_norm, acc_norm, reflux_flag)
                gate_decision = compute_learned_gate_decision(_feats, gate=self.learned_gate)
            else:
                gate_decision = compute_gate_decision(confidence, gating_enabled=self.enable_gating)

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
                'related_accounts': related_accounts,
                'related_perpetrators': related_perpetrators,
                'reflux_cycles': rc['cycles'],
                'is_reflux': rc['is_reflux'],
                'freeze_candidates': sorted(set(related_accounts)),
                'confidence': confidence,
                'gate_decision': gate_decision,
                'description': f'该团伙涉及{len(gang_cases)}起案件，主要为{primary_type}诈骗，'
                             f'集中在{primary_city}地区，涉案金额{total_amount:.2f}元，'
                             f'关联收款账户{len(related_accounts)}个、违法者{len(related_perpetrators)}名'
                             + ('，检测到资金回流闭环' if rc['is_reflux'] else '')
            }

            # 案件-团伙关联可解释性证据（case 级客观证据）
            relation_reasons, matched_entities_map, relation_type_map = self._build_case_evidence(
                node_ids, gang_cases, rc['cycles']
            )
            gang_info['relation_reasons'] = relation_reasons
            gang_info['matched_entities_map'] = matched_entities_map
            gang_info['relation_type_map'] = relation_type_map
            # 默认 relation_type 设为团伙级（保持向后兼容），但每个 case 有独立 type
            gang_info.setdefault('relation_type', 'gnn_cluster')

            gangs.append(gang_info)
        
        # 按案件数量排序
        gangs.sort(key=lambda x: x['case_count'], reverse=True)
        
        return gangs

    def detect_reflux_cycles(self, communities=None) -> Dict[Any, Dict[str, Any]]:
        """检测每个团伙内的资金回流闭环（资金回流到同团伙账户）。

        实现：抽取资金有向子图(nx.DiGraph)，用 networkx.simple_cycles 找
        简单环；再按团伙关联账户节点过滤，仅保留完全落在某团伙账户集内的环。
        返回 {gang_id: {'cycles': [[acc,...],...], 'is_reflux': bool}}。

        注：仅依赖图拓扑与 fund_flow 方向，客观可复现，不依赖 LLM 自评。
        """
        if communities is None:
            communities = self.communities or {}
        reflux: Dict[Any, Dict[str, Any]] = {
            gid: {'cycles': [], 'is_reflux': False} for gid in communities
        }
        if self.graph_builder is None or self.graph is None:
            return reflux
        DG = self.graph_builder.get_fund_flow_digraph()
        if DG.number_of_nodes() == 0:
            return reflux
        try:
            all_cycles = list(nx.simple_cycles(DG))
        except Exception:
            all_cycles = []
        for gid, node_ids in communities.items():
            seed_acc = {
                nid for nid in node_ids
                if nid in self.graph and self.graph.nodes[nid].get('node_type') == 'account'
            }
            # 资金流闭包：种子账户沿 fund_flow 正向/反向可达的所有账户
            # （收款账户 -> 中转 -> 上游归集 -> 回流），构成团伙完整资金网络
            acc_domain = set(seed_acc)
            for s in seed_acc:
                if s in DG:
                    acc_domain |= set(nx.descendants(DG, s))
                    acc_domain |= set(nx.ancestors(DG, s))
            cycles = [cyc for cyc in all_cycles if acc_domain.issuperset(set(cyc))]
            reflux[gid] = {'cycles': cycles, 'is_reflux': len(cycles) > 0}
        return reflux

    def _build_case_evidence(self, gang_node_ids, gang_cases, reflux_cycles) -> tuple:
        """为团伙内每个 case 生成关联证据。

        Returns:
            (relation_reasons, matched_entities_map, relation_type_map)
            - relation_reasons: {case_id: "共享账户 6222****1234；参与资金回流闭环"}
            - matched_entities_map: {case_id: ["6222****1234", "138****8888"]}
            - relation_type_map: {case_id: "share_account"}  # 按主要证据来源判定
              relation_type 取值: share_account / share_perpetrator / share_phone / reflux / similar_text / gnn_cluster
        """
        relation_reasons = {}
        matched_entities_map = {}
        relation_type_map = {}

        if self.graph is None or not gang_cases:
            return relation_reasons, matched_entities_map, relation_type_map

        graph = self.graph
        gang_case_ids = [c.get('case_id') for c in gang_cases if c.get('case_id')]
        gang_case_set = set(gang_case_ids)

        def _mask(value, is_name: bool = False) -> str:
            """脱敏：账号/电话保留前4后4中间****；人名保留姓+*+末位（单字保留原样）"""
            s = '' if value is None else str(value)
            if is_name:
                if len(s) <= 1:
                    return s
                return s[0] + '*' + s[-1]
            if len(s) <= 8:
                return s
            return s[:4] + '****' + s[-4:]

        # 预计算：团伙内每个 entity 节点被哪些团伙内 case 直接连接
        account_to_cases = {}
        perp_to_cases = {}
        phone_to_cases = {}
        for case_id in gang_case_ids:
            if case_id not in graph:
                continue
            for nb in graph.neighbors(case_id):
                if nb not in graph:
                    continue
                ntype = graph.nodes[nb].get('node_type')
                if ntype == 'account':
                    account_to_cases.setdefault(nb, set()).add(case_id)
                elif ntype == 'perpetrator':
                    perp_to_cases.setdefault(nb, set()).add(case_id)
                elif ntype == 'phone':
                    phone_to_cases.setdefault(nb, set()).add(case_id)

        # 资金回流环涉及的账户节点集合
        reflux_account_nodes = set()
        try:
            for cyc in (reflux_cycles or []):
                for acc_id in cyc:
                    reflux_account_nodes.add(acc_id)
        except Exception:
            pass

        # 团伙内 case 之间的 similar 边（无向，去重）
        similar_pairs = set()
        for case_id in gang_case_ids:
            if case_id not in graph:
                continue
            try:
                for nb, edata in graph[case_id].items():
                    if nb in gang_case_set and edata.get('relation') == 'similar':
                        similar_pairs.add(frozenset({case_id, nb}))
            except Exception:
                pass

        for case_id in gang_case_ids:
            reasons = []
            matched = []
            rel_type = None

            # 1. 共享账户证据：该 case 连接的 account 是否也被团伙内其他 case 连接
            shared_accounts = []
            if case_id in graph:
                for nb in graph.neighbors(case_id):
                    if nb not in graph:
                        continue
                    if graph.nodes[nb].get('node_type') != 'account':
                        continue
                    linked = account_to_cases.get(nb, set())
                    if len(linked) >= 2:  # 含当前 case，>=2 即被其他 case 共享
                        acc_no = graph.nodes[nb].get('account_no', nb)
                        if acc_no and acc_no not in shared_accounts:
                            shared_accounts.append(acc_no)
            if shared_accounts:
                masked_accs = [_mask(a) for a in shared_accounts]
                reasons.append('共享收款账户 ' + '、'.join(masked_accs))
                matched.extend(masked_accs)
                rel_type = 'share_account'

            # 2. 资金回流证据：该 case 连接的 account 是否出现在回流闭环中
            in_reflux = False
            if case_id in graph:
                for nb in graph.neighbors(case_id):
                    if nb in reflux_account_nodes:
                        in_reflux = True
                        break
            if in_reflux:
                reasons.append('参与资金回流闭环')
                if rel_type is None:
                    rel_type = 'reflux'

            # 3. 共享违法者证据
            shared_perps = []
            if case_id in graph:
                for nb in graph.neighbors(case_id):
                    if nb not in graph:
                        continue
                    if graph.nodes[nb].get('node_type') != 'perpetrator':
                        continue
                    linked = perp_to_cases.get(nb, set())
                    if len(linked) >= 2:
                        name = graph.nodes[nb].get('name', nb)
                        if name and name not in shared_perps:
                            shared_perps.append(name)
            if shared_perps:
                masked_perps = [_mask(p, is_name=True) for p in shared_perps]
                reasons.append('共享违法者' + '、'.join(masked_perps))
                matched.extend(masked_perps)
                if rel_type is None:
                    rel_type = 'share_perpetrator'

            # 4. 共享电话证据
            shared_phones = []
            if case_id in graph:
                for nb in graph.neighbors(case_id):
                    if nb not in graph:
                        continue
                    if graph.nodes[nb].get('node_type') != 'phone':
                        continue
                    linked = phone_to_cases.get(nb, set())
                    if len(linked) >= 2:
                        number = graph.nodes[nb].get('number', nb)
                        if number and number not in shared_phones:
                            shared_phones.append(number)
            if shared_phones:
                masked_phones = [_mask(p) for p in shared_phones]
                reasons.append('共享电话 ' + '、'.join(masked_phones))
                matched.extend(masked_phones)
                if rel_type is None:
                    rel_type = 'share_phone'

            # 5. 文本相似证据
            has_similar = any(case_id in pair for pair in similar_pairs)
            if has_similar:
                reasons.append('与团伙内其他案件文本相似')
                if rel_type is None:
                    rel_type = 'similar_text'

            # 6. 兜底：无客观证据
            if rel_type is None:
                rel_type = 'gnn_cluster'
                reasons.append('GNN 聚类关联')

            relation_reasons[case_id] = '；'.join(reasons)
            matched_entities_map[case_id] = matched
            relation_type_map[case_id] = rel_type

        return relation_reasons, matched_entities_map, relation_type_map

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
