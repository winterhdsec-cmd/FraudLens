"""
图分区器
将大规模图分割成多个子图，支持并行处理
"""
import networkx as nx
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


class GraphPartitioner:
    """
    图分区器
    
    支持多种分区策略:
    - 按地域分区 (城市/省份)
    - 按诈骗类型分区
    - 按连通分量分区
    - 基于Metis的平衡分区
    """
    
    def __init__(self, strategy: str = 'auto'):
        """
        Args:
            strategy: 分区策略 ('geo', 'type', 'connected', 'metis', 'auto')
        """
        self.strategy = strategy
        self.partitions: Dict[str, nx.Graph] = {}
    
    def partition(
        self,
        graph: nx.Graph,
        num_partitions: int = 4,
        **kwargs
    ) -> Dict[str, nx.Graph]:
        """
        执行图分区
        
        Args:
            graph: 输入图
            num_partitions: 目标分区数
            **kwargs: 分区参数
            
        Returns:
            分区字典 {partition_id: subgraph}
        """
        if len(graph.nodes) < 100:
            # 小图不分区
            return {'default': graph}
        
        # 自动选择策略
        if self.strategy == 'auto':
            strategy = self._auto_select_strategy(graph)
        else:
            strategy = self.strategy
        
        if strategy == 'geo':
            return self._partition_by_geo(graph, **kwargs)
        elif strategy == 'type':
            return self._partition_by_type(graph, **kwargs)
        elif strategy == 'connected':
            return self._partition_by_connected(graph, num_partitions)
        elif strategy == 'metis':
            return self._partition_by_metis(graph, num_partitions)
        else:
            return {'default': graph}
    
    def _auto_select_strategy(self, graph: nx.Graph) -> str:
        """根据图特征自动选择分区策略"""
        # 检查是否有地域信息
        has_geo = any(
            'city' in str(graph.nodes[n].get('node_type', '')).lower()
            for n in graph.nodes
        )
        
        # 检查是否有类型信息
        has_type = any(
            'scam_type' in str(graph.nodes[n].get('node_type', '')).lower()
            for n in graph.nodes
        )
        
        # 检查连通性
        num_components = nx.number_connected_components(graph)
        
        if has_geo and num_components > 1:
            return 'geo'
        elif has_type:
            return 'type'
        elif num_components > 1:
            return 'connected'
        else:
            return 'metis'
    
    def _partition_by_geo(
        self,
        graph: nx.Graph,
        geo_attribute: str = 'city'
    ) -> Dict[str, nx.Graph]:
        """按地域分区"""
        partitions = defaultdict(nx.Graph)
        
        for node_id, data in graph.nodes(data=True):
            # 提取地域信息
            geo = data.get(geo_attribute, 'unknown')
            
            # 如果是案件节点，从地址提取城市
            if data.get('node_type') == 'case':
                addr = data.get('victim_address', '')
                geo = self._extract_city(addr) or 'unknown'
            
            # 添加到对应分区
            partitions[geo].add_node(node_id, **data)
        
        # 添加边
        for u, v, data in graph.edges(data=True):
            u_geo = graph.nodes[u].get(geo_attribute, 'unknown')
            v_geo = graph.nodes[v].get(geo_attribute, 'unknown')
            
            # 如果是案件节点，提取城市
            if graph.nodes[u].get('node_type') == 'case':
                u_geo = self._extract_city(graph.nodes[u].get('victim_address', '')) or 'unknown'
            if graph.nodes[v].get('node_type') == 'case':
                v_geo = self._extract_city(graph.nodes[v].get('victim_address', '')) or 'unknown'
            
            # 同地域的边添加到分区
            if u_geo == v_geo:
                partitions[u_geo].add_edge(u, v, **data)
        
        return dict(partitions)
    
    def _partition_by_type(
        self,
        graph: nx.Graph,
        type_attribute: str = 'scam_type'
    ) -> Dict[str, nx.Graph]:
        """按诈骗类型分区"""
        partitions = defaultdict(nx.Graph)
        
        for node_id, data in graph.nodes(data=True):
            # 提取类型信息
            if data.get('node_type') == 'case':
                scam_type = data.get(type_attribute, 'unknown')
                partitions[scam_type].add_node(node_id, **data)
            else:
                # 非案件节点添加到所有分区
                for p in partitions.values():
                    p.add_node(node_id, **data)
        
        # 添加边
        for u, v, data in graph.edges(data=True):
            u_type = graph.nodes[u].get('scam_type', 'unknown')
            v_type = graph.nodes[v].get('scam_type', 'unknown')
            
            # 同类型的边添加到分区
            if u_type == v_type and u_type in partitions:
                partitions[u_type].add_edge(u, v, **data)
        
        return dict(partitions)
    
    def _partition_by_connected(
        self,
        graph: nx.Graph,
        num_partitions: int
    ) -> Dict[str, nx.Graph]:
        """按连通分量分区"""
        partitions = {}
        
        components = list(nx.connected_components(graph))
        
        # 如果连通分量数少于目标分区数，直接按分量分
        if len(components) <= num_partitions:
            for i, comp in enumerate(components):
                subgraph = graph.subgraph(comp).copy()
                partitions[f'component_{i}'] = subgraph
        else:
            # 合并小连通分量
            large_components = [c for c in components if len(c) >= 10]
            small_nodes = set()
            for c in components:
                if len(c) < 10:
                    small_nodes.update(c)
            
            for i, comp in enumerate(large_components[:num_partitions]):
                subgraph = graph.subgraph(comp).copy()
                partitions[f'component_{i}'] = subgraph
            
            # 剩余节点放入最后一个分区
            if small_nodes:
                remaining = set()
                for i in range(num_partitions, len(large_components)):
                    remaining.update(large_components[i])
                remaining.update(small_nodes)
                
                if remaining:
                    subgraph = graph.subgraph(remaining).copy()
                    partitions[f'component_{num_partitions}'] = subgraph
        
        return partitions
    
    def _partition_by_metis(
        self,
        graph: nx.Graph,
        num_partitions: int
    ) -> Dict[str, nx.Graph]:
        """使用Metis算法进行平衡分区"""
        try:
            import metis
        except ImportError:
            # Metis未安装，回退到简单分区
            return self._partition_by_connected(graph, num_partitions)
        
        # Metis分区
        _, parts = metis.part_graph(graph, nparts=num_partitions)
        
        partitions = defaultdict(nx.Graph)
        for node_id, part_id in zip(graph.nodes(), parts):
            partitions[f'part_{part_id}'].add_node(node_id, **graph.nodes[node_id])
        
        # 添加边
        for u, v, data in graph.edges(data=True):
            u_part = parts[list(graph.nodes()).index(u)]
            v_part = parts[list(graph.nodes()).index(v)]
            
            # 同分区的边
            if u_part == v_part:
                partitions[f'part_{u_part}'].add_edge(u, v, **data)
        
        return dict(partitions)
    
    @staticmethod
    def _extract_city(address: str) -> str:
        """从地址提取城市"""
        if not address:
            return ''
        
        if '省' in address:
            parts = address.split('省')
            if len(parts) > 1:
                city_part = parts[1]
                if '市' in city_part:
                    return city_part.split('市')[0] + '市'
        elif '市' in address:
            return address.split('市')[0] + '市'
        
        return ''
    
    def merge_results(
        self,
        partition_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        合并分区处理结果
        
        Args:
            partition_results: 分区结果 {partition_id: result}
            
        Returns:
            合并后的结果
        """
        merged_gangs = []
        total_stats = {
            'total_gangs': 0,
            'total_cases': 0,
            'total_amount': 0,
            'avg_cases_per_gang': 0,
            'high_risk_gangs': 0
        }
        
        gang_id_offset = 0
        
        for part_id, result in partition_results.items():
            # 合并团伙列表
            for gang in result.get('gangs', []):
                # 重新编号，避免冲突
                gang['gang_id'] = f"GANG_{gang_id_offset:03d}"
                gang['partition'] = part_id
                merged_gangs.append(gang)
                gang_id_offset += 1
            
            # 合并统计
            stats = result.get('stats', {})
            total_stats['total_gangs'] += stats.get('total_gangs', 0)
            total_stats['total_cases'] += stats.get('total_cases', 0)
            total_stats['total_amount'] += stats.get('total_amount', 0)
            total_stats['high_risk_gangs'] += stats.get('high_risk_gangs', 0)
        
        # 计算平均值
        if total_stats['total_gangs'] > 0:
            total_stats['avg_cases_per_gang'] = (
                total_stats['total_cases'] / total_stats['total_gangs']
            )
        
        return {
            'gangs': merged_gangs,
            'stats': total_stats,
            'partition_count': len(partition_results)
        }


class ParallelGNNProcessor:
    """
    并行GNN处理器
    支持多分区并行训练和推理
    """
    
    def __init__(
        self,
        partitioner: GraphPartitioner = None,
        max_workers: int = 4
    ):
        """
        Args:
            partitioner: 图分区器
            max_workers: 最大并行工作线程数
        """
        self.partitioner = partitioner or GraphPartitioner()
        self.max_workers = max_workers
    
    def process(
        self,
        graph: nx.Graph,
        cases: List[Dict[str, Any]],
        num_partitions: int = 4,
        use_gnn: bool = True,
        training_epochs: int = 100
    ) -> Dict[str, Any]:
        """
        并行处理图
        
        Args:
            graph: 输入图
            cases: 案件列表
            num_partitions: 分区数
            use_gnn: 是否使用GNN
            training_epochs: 训练轮数
            
        Returns:
            处理结果
        """
        # 1. 分区
        partitions = self.partitioner.partition(graph, num_partitions)
        
        if len(partitions) == 1:
            # 单分区，直接处理
            from .gang_detector import GangDetector
            detector = GangDetector()
            return detector.detect(cases, use_gnn=use_gnn, training_epochs=training_epochs)
        
        # 2. 并行处理每个分区
        partition_results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for part_id, subgraph in partitions.items():
                # 提取该分区的案件
                part_cases = [
                    c for c in cases
                    if c.get('case_id') in subgraph.nodes
                ]
                
                if not part_cases:
                    continue
                
                # 提交任务
                future = executor.submit(
                    self._process_partition,
                    part_id,
                    subgraph,
                    part_cases,
                    use_gnn,
                    training_epochs
                )
                futures[future] = part_id
            
            # 收集结果
            for future in as_completed(futures):
                part_id = futures[future]
                try:
                    result = future.result()
                    partition_results[part_id] = result
                except Exception as e:
                    partition_results[part_id] = {
                        'gangs': [],
                        'stats': {},
                        'error': str(e)
                    }
        
        # 3. 合并结果
        return self.partitioner.merge_results(partition_results)
    
    def _process_partition(
        self,
        part_id: str,
        subgraph: nx.Graph,
        cases: List[Dict[str, Any]],
        use_gnn: bool,
        training_epochs: int
    ) -> Dict[str, Any]:
        """处理单个分区"""
        from .gang_detector import GangDetector
        
        detector = GangDetector()
        detector.graph = subgraph
        detector.graph_builder.graph = subgraph
        detector.graph_builder._build_node_features()
        
        return detector.detect(
            cases=cases,
            use_gnn=use_gnn,
            training_epochs=training_epochs
        )
