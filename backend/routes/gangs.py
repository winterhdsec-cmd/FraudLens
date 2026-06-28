"""
Gang routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from database import db
from database.models import Gang, Case, GraphNode, GraphEdge
from database.crud import get_all_gangs, get_gang_by_id
from routes.cases import _compute_gang_radar
from .deps import get_current_user, db_retry

router = APIRouter(prefix='/api/gangs', tags=['团伙'])


class GNNDetectRequest(BaseModel):
    """GNN团伙发现请求"""
    use_gnn: bool = True
    training_epochs: int = 100
    community_method: str = 'louvain'


@router.get('')
@db_retry()
async def api_get_gangs(current_user: dict = Depends(get_current_user)):
    try:
        gangs = get_all_gangs()
        return {"success": True, "gangs": gangs, "total": len(gangs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/detect/gnn')
async def api_detect_gangs_gnn(
    request: GNNDetectRequest,
    current_user: dict = Depends(get_current_user)
):
    """使用GNN进行团伙发现"""
    try:
        # 从数据库获取所有案件
        cases_db = db.session.query(Case).all()
        
        if not cases_db:
            return {"success": False, "error": "没有案件数据"}
        
        # 转换为字典格式
        cases = []
        for case in cases_db:
            cases.append({
                'case_id': case.case_id,
                'victim_name': case.victim_name,
                'victim_phone': case.victim_phone,
                'victim_address': case.victim_address,
                'victim_age': case.victim_age,
                'victim_gender': case.victim_gender,
                'scam_type': case.scam_type,
                'amount_value': case.amount_value,
                'risk_score': case.risk_score,
                'description': case.description
            })
        
        # 使用GNN进行团伙发现
        from gnn import GangDetector
        detector = GangDetector(
            community_method=request.community_method
        )
        
        result = detector.detect(
            cases=cases,
            use_gnn=request.use_gnn,
            training_epochs=request.training_epochs
        )
        
        # 获取图可视化数据
        graph_data = detector.get_graph_visualization_data()
        
        return {
            "success": True,
            "gangs": result['gangs'],
            "stats": result['stats'],
            "graph": graph_data
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get('/{gang_id}')
async def api_get_gang(gang_id: str, current_user: dict = Depends(get_current_user)):
    try:
        gang = get_gang_by_id(gang_id)
        if gang:
            return {"success": True, "gang": gang}
        return JSONResponse(status_code=404, content={"success": False, "error": "团伙不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{gang_id}/radar')
async def api_get_gang_radar(gang_id: str, current_user: dict = Depends(get_current_user)):
    try:
        gang = db.session.query(Gang).filter(Gang.gang_id == gang_id).first()
        if not gang:
            return JSONResponse(status_code=404, content={"success": False, "error": "团伙不存在"})
        radar = _compute_gang_radar(gang)
        return {"success": True, "gang_id": gang_id, "radar": radar}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ==================== 图查询API ====================

@router.get('/graph/stats')
async def api_get_graph_stats(current_user: dict = Depends(get_current_user)):
    """获取图统计信息"""
    try:
        node_count = db.session.query(GraphNode).count()
        edge_count = db.session.query(GraphEdge).count()
        
        # 按类型统计节点
        node_types = db.session.query(
            GraphNode.node_type, 
            db.func.count(GraphNode.id)
        ).group_by(GraphNode.node_type).all()
        
        # 按关系统计边
        edge_relations = db.session.query(
            GraphEdge.relation,
            db.func.count(GraphEdge.id)
        ).group_by(GraphEdge.relation).all()
        
        return {
            "success": True,
            "stats": {
                "node_count": node_count,
                "edge_count": edge_count,
                "node_types": {t: c for t, c in node_types},
                "edge_relations": {r: c for r, c in edge_relations}
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/graph/similar-cases/{case_id}')
async def api_get_similar_cases(case_id: str, limit: int = Query(10, ge=1, le=50), current_user: dict = Depends(get_current_user)):
    """查询与指定案件相似的案件"""
    try:
        # 查找相似边
        similar_edges = db.session.query(GraphEdge).filter(
            GraphEdge.relation == 'similar',
            (GraphEdge.source_id == case_id) | (GraphEdge.target_id == case_id)
        ).order_by(GraphEdge.weight.desc()).limit(limit).all()
        
        similar_cases = []
        for edge in similar_edges:
            target_id = edge.target_id if edge.source_id == case_id else edge.source_id
            
            # 获取目标案件信息
            case = db.session.query(Case).filter(Case.case_id == target_id).first()
            if case:
                similar_cases.append({
                    "case_id": case.case_id,
                    "title": case.title,
                    "scam_type": case.scam_type,
                    "risk_level": case.risk_level,
                    "amount": case.amount_value,
                    "similarity": edge.weight
                })
        
        return {
            "success": True,
            "case_id": case_id,
            "similar_cases": similar_cases,
            "count": len(similar_cases)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/graph/node/{node_id}')
async def api_get_node_detail(node_id: str, current_user: dict = Depends(get_current_user)):
    """获取节点详情及其关联"""
    try:
        node = db.session.query(GraphNode).filter(GraphNode.node_id == node_id).first()
        if not node:
            return JSONResponse(status_code=404, content={"success": False, "error": "节点不存在"})
        
        # 查询关联边
        edges = db.session.query(GraphEdge).filter(
            (GraphEdge.source_id == node_id) | (GraphEdge.target_id == node_id)
        ).all()
        
        connections = []
        for edge in edges:
            other_id = edge.target_id if edge.source_id == node_id else edge.source_id
            other_node = db.session.query(GraphNode).filter(GraphNode.node_id == other_id).first()
            
            connections.append({
                "node_id": other_id,
                "node_type": other_node.node_type if other_node else "unknown",
                "relation": edge.relation,
                "weight": edge.weight,
                "direction": "outgoing" if edge.source_id == node_id else "incoming"
            })
        
        return {
            "success": True,
            "node": {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "features": node.features,
                "created_at": node.created_at.isoformat() if node.created_at else None
            },
            "connections": connections,
            "connection_count": len(connections)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/graph/paths')
async def api_find_paths(
    from_node: str = Query(..., description="起始节点ID"),
    to_node: str = Query(..., description="目标节点ID"),
    max_depth: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """查找两个节点之间的路径"""
    try:
        import networkx as nx
        
        # 从数据库加载图
        nodes = db.session.query(GraphNode).all()
        edges = db.session.query(GraphEdge).all()
        
        G = nx.Graph()
        for node in nodes:
            G.add_node(node.node_id, node_type=node.node_type)
        for edge in edges:
            G.add_edge(edge.source_id, edge.target_id, weight=edge.weight)
        
        # 检查节点是否存在
        if from_node not in G or to_node not in G:
            return {"success": False, "error": "节点不存在"}
        
        # 查找最短路径
        try:
            path = nx.shortest_path(G, source=from_node, target=to_node, weight='weight')
            path_length = nx.shortest_path_length(G, source=from_node, target=to_node, weight='weight')
            
            # 获取路径节点详情
            path_nodes = []
            for node_id in path:
                node = db.session.query(GraphNode).filter(GraphNode.node_id == node_id).first()
                if node:
                    path_nodes.append({
                        "node_id": node.node_id,
                        "node_type": node.node_type
                    })
            
            return {
                "success": True,
                "path": path_nodes,
                "path_length": path_length,
                "hop_count": len(path) - 1
            }
        except nx.NetworkXNoPath:
            return {
                "success": True,
                "path": [],
                "message": "两个节点之间不存在路径"
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/graph/rebuild')
async def api_rebuild_graph(current_user: dict = Depends(get_current_user)):
    """重建图数据"""
    try:
        from gnn.graph_builder import FraudGraphBuilder
        
        # 获取所有案件
        cases = db.session.query(Case).all()
        if not cases:
            return {"success": False, "error": "没有案件数据"}
        
        # 转换为字典格式
        case_dicts = []
        for case in cases:
            case_dicts.append({
                'case_id': case.case_id,
                'victim_name': case.victim_name,
                'victim_phone': case.victim_phone,
                'victim_address': case.victim_address,
                'victim_age': case.victim_age,
                'victim_gender': case.victim_gender,
                'scam_type': case.scam_type,
                'amount_value': case.amount_value,
                'risk_score': case.risk_score
            })
        
        # 重建图
        builder = FraudGraphBuilder(use_db=True, use_cache=True)
        graph = builder.build_graph(case_dicts)
        
        return {
            "success": True,
            "message": "图数据重建成功",
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})