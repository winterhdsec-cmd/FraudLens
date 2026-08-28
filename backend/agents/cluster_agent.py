"""
团伙发现 Agent - 自适应聚类 + 反思机制 + GNN增强
"""
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.agent_runtime import AgentRuntime
from core.state import AgentState
from agents.protocol import AgentProtocol


class ClusterAgent(AgentProtocol):
    """
    团伙发现智能体
    
    使用自适应聚类算法和GNN发现诈骗团伙:
    1. 分析数据特征（数量、维度、分布）
    2. 选择最优聚类策略（传统聚类或GNN）
    3. 执行聚类/图神经网络学习
    4. 评估聚类质量
    5. 反思并调整（如果质量不佳）
    """

    # Agent 注册表契约（B1.1 / B1.3）
    name = "cluster"
    stage = "cluster"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """AgentProtocol 入口：团伙发现。context={"cases": [...], "use_gnn": bool, "accounts_tx": [...]}。"""
        cases = context.get("cases", [])
        use_gnn = context.get("use_gnn", self.use_gnn)
        accounts_tx = context.get("accounts_tx")
        if use_gnn and getattr(self, "gnn_detector", None) is None:
            # 惰性构建（当 use_gnn 与 __init__ 设置不一致时）
            from gnn import GangDetector
            self.gnn_detector = GangDetector(
                embedding_dim=64, hidden_dim=32, num_layers=2, community_method='louvain'
            )
        result = self.discover_gangs(cases, use_gnn=use_gnn, accounts_tx=accounts_tx)
        # 复核解释层（Skill A/B）：对成功的团伙划分追加"并案依据解释 + 误并复查"
        # 纯增量、不侵入聚类主链路；LLM 不可用时规则降级，绝不抛异常中断。
        try:
            gangs = result.get("gangs") or []
            if gangs:
                from .gang_reviewer import review_gangs_sync
                cases_map = {str(c.get("case_id") or c.get("id")): c for c in cases}
                known_pairs = context.get("known_distinct_pairs") or []
                review = review_gangs_sync(gangs, cases_map, known_distinct_pairs)
                result["review"] = review.get("review", {})
                result["explanations"] = review.get("explanations", [])
                result["llm_enabled"] = review.get("llm_enabled", False)
        except Exception as e:
            print(f"[cluster_agent] 复核层跳过（不中断主流程）: {e}")
        return result
    
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
        
        # 初始化GNN检测器（惰性导入，避免无 torch 环境 import 即崩）
        if self.use_gnn:
            from gnn import GangDetector
            self.gnn_detector = GangDetector(
                embedding_dim=64,
                hidden_dim=32,
                num_layers=2,
                community_method='louvain'
            )
    
    def discover_gangs(self, cases: List[Dict[str, Any]], use_gnn: bool = None, accounts_tx: Any = None) -> Dict[str, Any]:
        """
        发现诈骗团伙

        Args:
            cases: 案件列表，每个案件包含 description, case_id 等
            use_gnn: 是否使用GNN（None表示使用默认设置）
            accounts_tx: 账户间资金流转记录（可选，B-L3 资金回流闭环检测用）

        Returns:
            团伙发现结果
        """
        if not cases:
            return {"gangs": [], "total_gangs": 0}

        # B-L2：实体关联聚类优先（按共享账户/手机号/微信/QQ 并案，结果可解释）
        # 仅在存在跨案共享实体时才生效；否则交回 GNN/embedding 兜底。
        entity_result = self._cluster_by_entities(cases, accounts_tx=accounts_tx)
        if entity_result is not None:
            return entity_result

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

                # 添加方法标记 + 补齐编排层契约字段（detect 顶层无 total_gangs/quality_score）
                result['method'] = 'gnn'
                result['total_gangs'] = result.get('stats', {}).get(
                    'total_gangs', len(result.get('gangs', []))
                )
                # stats 当前不含轮廓系数，暂以 0.5 占位；待 GNN 暴露 silhouette 后替换
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
    
    # ------------------------------------------------------------------ #
    # B-L2：实体关联聚类（按共享账户/手机号/微信/QQ 并案，可解释）
    # ------------------------------------------------------------------ #
    def _cluster_by_entities(self, cases: List[Dict[str, Any]], accounts_tx: Any = None) -> Optional[Dict[str, Any]]:
        """
        按共享实体关联并案：以案件为点、共享实体为边建二部图，并查集求连通分量。
        仅在存在跨案共享实体时返回结果；否则返回 None（交回 GNN/embedding 兜底）。
        B-L3：对产出的团伙附加资金回流闭环检测（需 accounts_tx）。
        """
        link_types = ["bank_accounts", "phone_numbers", "wechat_ids", "qq_numbers"]
        ent_to_cases: Dict[tuple, List[int]] = {}
        for i, c in enumerate(cases):
            ents = c.get("extracted_entities", {}) or {}
            for t in link_types:
                for v in (ents.get(t) or []):
                    v = str(v).strip()
                    if v:
                        ent_to_cases.setdefault((t, v), []).append(i)

        # 仅保留被 ≥2 案共享的实体作为"并案证据"
        shared = {k: idxs for k, idxs in ent_to_cases.items() if len(idxs) >= 2}
        if not shared:
            return None

        # 并查集
        parent = list(range(len(cases)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for idxs in shared.values():
            for o in idxs[1:]:
                union(idxs[0], o)

        groups: Dict[int, List[int]] = {}
        for i in range(len(cases)):
            groups.setdefault(find(i), []).append(i)

        gang_groups = [m for m in groups.values() if len(m) >= 2]
        if not gang_groups:
            return None

        # B-L3：资金回流闭环检测（复用 graph_builder 的 fund_flow 有向图 + networkx 环检测）
        reflux_map = self._detect_reflux(cases, gang_groups, shared, accounts_tx)
        gangs = self._generate_entity_gang_info(cases, gang_groups, shared, reflux_map=reflux_map)
        return {
            "gangs": gangs,
            "total_gangs": len(gangs),
            "quality_score": 1.0,
            "strategy": {"method": "entity_association"},
            "method": "entity_association",
        }

    def _generate_entity_gang_info(
        self,
        cases: List[Dict[str, Any]],
        gang_groups: List[List[int]],
        shared: Dict[tuple, List[int]],
        reflux_map: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """生成实体关联团伙信息（含 evidence_chain、entities 汇总与 B-L3 回流闭环字段）"""
        gangs = []
        for gid, members in enumerate(gang_groups):
            member_set = set(members)

            # B-L3：回流闭环信息（缺 accounts_tx 时 is_reflux=False，诚实不造假）
            rf = (reflux_map or {}).get(gid, {"cycles": [], "is_reflux": False, "freeze_candidates": []})
            reflux_cycles = rf.get("cycles", [])
            is_reflux = bool(rf.get("is_reflux", False))
            freeze_candidates = rf.get("freeze_candidates", [])
            # 证据链：哪些共享实体把本团伙的案件连起来
            evidence_chain = []
            for (t, v), idxs in shared.items():
                if member_set.issuperset(set(idxs)):
                    evidence_chain.append({
                        "type": t,
                        "value": v,
                        "case_ids": [cases[i].get("case_id") for i in idxs],
                    })

            # 诈骗类型：优先多数案 scam_type
            fraud_types = []
            for i in members:
                ft = cases[i].get("scam_type")
                if not ft or ft == "未知":
                    ft = (cases[i].get("extracted_entities", {}) or {}).get("scam_type", "未知")
                fraud_types.append(ft)
            filtered = [f for f in fraud_types if f and f != "未知"]
            most_common = max(set(filtered), key=filtered.count) if filtered else "未知"

            # 汇总团伙实体
            ent_pool: Dict[str, set] = {}
            for i in members:
                ents = cases[i].get("extracted_entities", {}) or {}
                for t in ("bank_accounts", "phone_numbers", "wechat_ids", "qq_numbers", "id_cards"):
                    for v in (ents.get(t) or []):
                        ent_pool.setdefault(t, set()).add(str(v))

            total_amount = sum(float(cases[i].get("amount", 0) or 0) for i in members)
            risk_scores = [float(cases[i].get("risk_score", 0) or 0) for i in members]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

            desc = (
                f"基于共享实体（账户/手机号/社交账号）关联发现的{most_common}犯罪团伙，"
                f"涉及{len(members)}起案件"
            )
            if is_reflux:
                desc += (f"；检测到资金回流闭环（{len(reflux_cycles)} 个环），"
                         f"建议冻结关联收款账户 {len(freeze_candidates)} 个")

            gangs.append({
                "gang_id": f"GANG_{gid:03d}",
                "gang_name": f"{most_common}犯罪团伙{gid + 1}号",
                "total_cases": len(members),
                "total_amount": total_amount,
                "avg_risk_score": avg_risk,
                "risk_level": "HIGH" if avg_risk >= 80 else "MEDIUM" if avg_risk >= 60 else "LOW",
                "fraud_type": most_common,
                "case_ids": [cases[i].get("case_id") for i in members],
                "entities": {t: sorted(vs) for t, vs in ent_pool.items() if vs},
                "evidence_chain": evidence_chain,
                # B-L3：资金回流闭环（客观、可复现，依赖 fund_flow 方向）
                "reflux_cycles": reflux_cycles,
                "is_reflux": is_reflux,
                "freeze_candidates": freeze_candidates,
                "description": desc,
            })
        return gangs

    # ------------------------------------------------------------------ #
    # B-L3：资金回流闭环检测（复用 graph_builder 的 fund_flow 有向图）
    # ------------------------------------------------------------------ #
    def _detect_reflux(
        self,
        cases: List[Dict[str, Any]],
        gang_groups: List[List[int]],
        shared: Dict[tuple, List[int]],
        accounts_tx: Any = None,
    ) -> Dict[int, Dict[str, Any]]:
        """对每个实体关联团伙做资金回流闭环检测。

        复用 gnn.graph_builder.FraudGraphBuilder 的 fund_flow 有向子图 + networkx.simple_cycles，
        与 gang_detector.detect_reflux_cycles 同口径（仅依赖图拓扑与 fund_flow 方向，客观可复现）。
        仅当提供 accounts_tx（账户间资金流转记录）时才可能产生闭环边；缺失时诚实返回 is_reflux=False。
        """
        import networkx as nx

        empty = lambda: {gid: {"cycles": [], "is_reflux": False, "freeze_candidates": []}
                         for gid in range(len(gang_groups))}
        try:
            from gnn.graph_builder import FraudGraphBuilder
        except Exception as e:
            print(f"B-L3 导入 FraudGraphBuilder 失败: {e}")
            return empty()

        result = empty()
        if not accounts_tx:
            return result  # 无资金流转记录 → 无闭环，不造假

        # 把每个 case 的 bank_accounts 投影为图的 account 节点
        gb_cases = []
        for c in cases:
            cc = dict(c)
            ents = c.get("extracted_entities", {}) or {}
            cc["accounts"] = list(ents.get("bank_accounts", []) or [])
            gb_cases.append(cc)

        try:
            builder = FraudGraphBuilder(use_db=False, use_cache=False, use_text_channel=False)
            builder.build_graph(gb_cases, accounts_tx=accounts_tx)
            DG = builder.get_fund_flow_digraph()
            if DG.number_of_nodes() == 0:
                return result
            try:
                all_cycles = list(nx.simple_cycles(DG))
            except Exception:
                all_cycles = []
        except Exception as e:
            print(f"B-L3 回流检测建图失败: {e}")
            return result

        for gid, members in enumerate(gang_groups):
            acc_set = set()
            for i in members:
                ents = cases[i].get("extracted_entities", {}) or {}
                for a in (ents.get("bank_accounts") or []):
                    acc_set.add(f"account_{a}")
            # 资金流闭包：种子账户沿 fund_flow 正向/反向可达的所有账户
            acc_domain = set(acc_set)
            for s in acc_set:
                if s in DG:
                    try:
                        acc_domain |= set(nx.descendants(DG, s))
                        acc_domain |= set(nx.ancestors(DG, s))
                    except Exception:
                        pass
            cycles = [cyc for cyc in all_cycles if acc_domain.issuperset(set(cyc))]
            # 去前缀（"account_" 为 8 字符），输出可读账户号
            clean_cycles = [[a[8:] if a.startswith("account_") else a for a in cyc] for cyc in cycles]
            freeze = sorted({a[8:] if a.startswith("account_") else a
                             for cyc in cycles for a in cyc})
            result[gid] = {
                "cycles": clean_cycles,
                "is_reflux": len(cycles) > 0,
                "freeze_candidates": freeze,
            }
        return result

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
