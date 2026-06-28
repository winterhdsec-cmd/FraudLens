"""
GNN团伙发现工具封装
供Agent调用的工具接口
"""
from typing import Dict, Any, List
from .gang_detector import GangDetector


class GNNGangDiscoveryTool:
    """GNN团伙发现工具"""
    
    def __init__(self):
        self.name = "gnn_gang_discovery"
        self.description = "使用图神经网络发现诈骗团伙"
        self.parameters = {
            "type": "object",
            "properties": {
                "cases": {
                    "type": "array",
                    "description": "案件列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string"},
                            "victim_name": {"type": "string"},
                            "victim_phone": {"type": "string"},
                            "victim_address": {"type": "string"},
                            "victim_age": {"type": "string"},
                            "victim_gender": {"type": "string"},
                            "scam_type": {"type": "string"},
                            "amount_value": {"type": "number"},
                            "risk_score": {"type": "number"},
                            "description": {"type": "string"}
                        },
                        "required": ["case_id", "scam_type"]
                    }
                },
                "use_gnn": {
                    "type": "boolean",
                    "description": "是否使用GNN学习嵌入（默认True）",
                    "default": True
                },
                "training_epochs": {
                    "type": "integer",
                    "description": "GNN训练轮数（默认100）",
                    "default": 100
                },
                "community_method": {
                    "type": "string",
                    "description": "社区检测方法（louvain/label_propagation/spectral）",
                    "default": "louvain"
                }
            },
            "required": ["cases"]
        }
        
    def run(self, cases: List[Dict[str, Any]], use_gnn: bool = True, 
            training_epochs: int = 100, community_method: str = "louvain") -> Dict[str, Any]:
        """
        执行团伙发现
        
        Args:
            cases: 案件列表
            use_gnn: 是否使用GNN
            training_epochs: 训练轮数
            community_method: 社区检测方法
            
        Returns:
            团伙发现结果
        """
        try:
            detector = GangDetector(
                community_method=community_method
            )
            
            result = detector.detect(
                cases=cases,
                use_gnn=use_gnn,
                training_epochs=training_epochs
            )
            
            return {
                "success": True,
                "gangs": result["gangs"],
                "stats": result["stats"],
                "message": f"成功发现 {result['stats']['total_gangs']} 个诈骗团伙"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"团伙发现失败: {str(e)}"
            }
    
    def get_graph_visualization(self) -> Dict[str, Any]:
        """获取图可视化数据"""
        if hasattr(self, '_last_detector'):
            return self._last_detector.get_graph_visualization_data()
        return {"nodes": [], "edges": []}


class GraphAnalysisTool:
    """图分析工具"""
    
    def __init__(self):
        self.name = "graph_analysis"
        self.description = "分析诈骗关联图的结构特征"
        self.parameters = {
            "type": "object",
            "properties": {
                "cases": {
                    "type": "array",
                    "description": "案件列表"
                }
            },
            "required": ["cases"]
        }
        
    def run(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析图结构
        
        Args:
            cases: 案件列表
            
        Returns:
            图分析结果
        """
        try:
            from .graph_builder import FraudGraphBuilder
            
            builder = FraudGraphBuilder()
            graph = builder.build_graph(cases)
            
            # 计算图统计信息
            import networkx as nx
            
            stats = {
                "num_nodes": graph.number_of_nodes(),
                "num_edges": graph.number_of_edges(),
                "density": nx.density(graph),
                "connected_components": nx.number_connected_components(graph),
                "avg_clustering": nx.average_clustering(graph),
                "avg_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
            }
            
            # 节点类型统计
            node_types = {}
            for node, data in graph.nodes(data=True):
                node_type = data.get('node_type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            stats["node_types"] = node_types
            
            return {
                "success": True,
                "stats": stats,
                "message": f"图分析完成: {stats['num_nodes']} 个节点, {stats['num_edges']} 条边"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"图分析失败: {str(e)}"
            }


# 工具注册表
GNN_TOOLS = {
    "gnn_gang_discovery": GNNGangDiscoveryTool,
    "graph_analysis": GraphAnalysisTool
}
