"""
Gang routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List

from database import db
from database.models import Gang, Case, GraphNode, GraphEdge
from database.crud import get_all_gangs, get_gang_by_id, persist_freeze_decisions, get_freeze_decisions
from routes.cases import _compute_gang_radar
from .deps import get_current_user, db_retry, log_operation
from schemas.analysis import GNNDetectRequest
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/gangs', tags=['团伙'])


# GNNDetectRequest 已迁移至 schemas.analysis（T3 / docs/13 G17）

@router.get('')
@db_retry()
async def api_get_gangs(current_user: dict = Depends(get_current_user)):
    try:
        gangs = get_all_gangs(current_user)
        return {"success": True, "gangs": gangs, "total": len(gangs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/freeze-decisions')
@db_retry()
async def api_get_freeze_decisions(
    gate: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """民警复核台：查询历史冻卡决策（A4.2，ADR-7 合规落地）。"""
    try:
        recs = get_freeze_decisions(gate_decision=gate)
        return {"success": True, "decisions": recs, "total": len(recs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# AI 复核层结果缓存（Skill A 解释 + Skill B 误并探测）
_review_cache = {}


def _mask_account_no(value) -> str:
    """账户脱敏：保留前4后4，中间****（与 gang_detector._mask 一致）。"""
    s = '' if value is None else str(value)
    if len(s) <= 8:
        return s
    return s[:4] + '****' + s[-4:]


def _run_incremental_detect(cases, current_user, request):
    """增量团伙发现：新案先与已知团伙画像匹配（账户池 + 话术 BGE 余弦，
    双信号一致才挂上，复用 P3 共识门控"宁缺毋滥"哲学），挂不上的攒批(>=2)才重聚类。

    返回结构与全量路径兼容（gangs/stats/graph），另附 mode='incremental' 与
    matched_gangs 摘要；不触发任何全库重聚类。
    """
    import time as _t
    from database.models import Gang, GangCaseRelation
    from database.crud import save_gang, _cache_clear
    from gnn.incremental_matcher import build_gang_profiles, match_cases_batch
    t0 = _t.time()

    rel_rows = db.session.query(GangCaseRelation.case_id).all()
    associated = {r[0] for r in rel_rows}
    case_by_id = {c['case_id']: c for c in cases if c.get('case_id')}
    new_cases = [c for c in cases if c.get('case_id') and c['case_id'] not in associated]

    stats = {
        'total_cases': len(cases),
        'associated_cases': len(associated),
        'new_cases': len(new_cases),
        'matched_cases': 0,
        'held_cases': len(new_cases),
    }

    if not new_cases:
        stats['elapsed_ms'] = int((_t.time() - t0) * 1000)
        return {'success': True, 'mode': 'incremental', 'gangs': [], 'stats': stats, 'graph': {}}

    # 团伙画像：gang_id -> 成员案件 dict（经 GangCaseRelation 已落库的关联）
    gangs = db.session.query(Gang).all()
    gang_rels = {}
    for r in db.session.query(GangCaseRelation).all():
        gang_rels.setdefault(r.gang_id, []).append(r.case_id)
    gangs_members = {}
    for g in gangs:
        members = [case_by_id[cid] for cid in gang_rels.get(g.gang_id, []) if cid in case_by_id]
        if members:
            gangs_members[g.gang_id] = members

    profiles = build_gang_profiles(gangs_members)
    matches = match_cases_batch(profiles, new_cases)
    stats['matched_cases'] = len(matches)

    matched_by_gang = {}
    for cid, m in matches.items():
        matched_by_gang.setdefault(m['gang_id'], []).append(cid)
        try:
            save_gang({
                'gang_id': m['gang_id'],
                'case_ids': [cid],
                'relation_type': 'incremental_match',
                'relation_reasons': {cid: f"资金共享 + 话术匹配（余弦{m['score']:.2f}）"},
                'matched_entities_map': {cid: [_mask_account_no(a) for a in m['matched_accounts']]},
            }, session_id=f"gnn_incremental_{current_user.get('id', '')}")
        except Exception as _ge:
            logger.warning(f"增量关联落库失败 {cid}: {_ge}")
    if matches:
        _cache_clear()

    unmatched = [c for c in new_cases if c['case_id'] not in matches]
    stats['held_cases'] = len(unmatched)

    batch_gangs, batch_graph, batch_stats = [], {}, {}
    if len(unmatched) >= 2:
        from gnn import GangDetector
        detector = GangDetector(community_method=request.community_method)
        batch = detector.detect(unmatched, use_gnn=request.use_gnn,
                                training_epochs=request.training_epochs)
        batch_gangs = batch.get('gangs', []) or []
        batch_stats = batch.get('stats', {}) or {}
        batch_graph = batch.get('graph', {}) or {}
        try:
            persist_freeze_decisions(batch_gangs)
            try:
                from core.metrics_exporter import inc_gangs, inc_freeze
                inc_gangs(len(batch_gangs))
                inc_freeze(len(batch_gangs))
            except Exception:
                pass
        except Exception as _e:
            logger.warning(f"批量冻卡决策落库失败(不影响研判返回): {_e}")
        try:
            _saved = 0
            for g in batch_gangs:
                g.setdefault('relation_type', 'gnn_cluster')
                try:
                    save_gang(g, session_id=f"gnn_detect_{current_user.get('id', '')}")
                    _saved += 1
                except Exception as _ge:
                    logger.warning(f"团伙 {g.get('gang_id')} 关联落库失败: {_ge}")
            if _saved:
                _cache_clear()
        except Exception as _e:
            logger.warning(f"GNN 团伙关联落库失败(不影响返回): {_e}")
    else:
        batch_stats['note'] = '攒批不足(<2)，待下次检测'

    stats['elapsed_ms'] = int((_t.time() - t0) * 1000)
    return {
        'success': True,
        'mode': 'incremental',
        'gangs': batch_gangs,
        'stats': {**batch_stats, **stats},
        'graph': batch_graph,
        'matched_gangs': [
            {'gang_id': gid, 'matched_cases': len(cids)} for gid, cids in matched_by_gang.items()
        ],
    }


@router.get('/review-results')
@db_retry()
async def api_gang_review_results(
    use_llm: int = Query(0, description='1=启用 LLM 增强（慢），默认纯规则毫秒级'),
    current_user: dict = Depends(get_current_user),
):
    """并案复核层：对全部团伙输出「并案依据解释」（Skill A）与「可疑误并清单」（Skill B）。

    纯增量的复核展示接口，不影响聚类主链路；LLM 不可用时自动规则降级，绝不 500。
    """
    import time as _t
    from agents.gang_reviewer import review_gangs_sync
    key = f"review_{int(bool(use_llm))}"
    ttl = 60 if use_llm else 300
    now = _t.time()
    cached = _review_cache.get(key)
    if cached and now - cached['ts'] < ttl:
        return cached['data']
    try:
        from database.crud import get_all_cases
        gangs = get_all_gangs(current_user)
        cases = get_all_cases(current_user)
        cases_map = {(c.get('case_id') or c.get('id')): c for c in cases if c}
        # total_amount 序列化为字符串（如 '765700'），skill 内需要数值
        for g in gangs:
            tv = g.get('total_amount_value')
            try:
                g['total_amount'] = float(tv) if tv else float(str(g.get('total_amount') or 0).replace('元', '').replace('¥', '').replace(',', '').strip())
            except (ValueError, TypeError):
                g['total_amount'] = 0
        result = review_gangs_sync(gangs, cases_map, enable_llm=bool(use_llm))
        resp = {"success": True, "checked_gangs": len(gangs), **result}
        _review_cache[key] = {'data': resp, 'ts': now}
        return resp
    except Exception as e:
        logger.exception('gang review-results failed')
        # 复核层失败：诚实返回 success=False，前端据 error 展示失败态，
        # 而非 success=True 让前端误判复核成功（原实现吞异常）
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"团伙复核失败: {str(e)[:200]}",
        })


@router.post('/detect/gnn')
async def api_detect_gangs_gnn(
    request: GNNDetectRequest,
    current_user: dict = Depends(get_current_user)
):
    """使用GNN进行团伙发现

    改进点（P0 修复）：
    1. 补全传给 detector 的字段：accounts / perpetrators / extracted_entities，
       让资金链通道（share_account / fund_flow / 回流闭环）真正生效
    2. 检测结果通过 save_gang 落库 GangCaseRelation（旧版只写 FreezeDecision）
    3. 关联带可解释性字段（relation_type / reason / matched_entities）
    """
    try:
        # G7 审计：记录 GNN 团伙发现发起
        try:
            log_operation(
                current_user['id'], current_user.get('username', ''),
                'gnn_detect_start', 'gang', '',
                {'use_gnn': request.use_gnn, 'community_method': request.community_method,
                 'mode': request.mode or 'auto'},
                ip_address=''
            )
        except Exception as _e:
            logger.warning(f"GNN发现留痕失败: {_e}")

        # 从数据库获取所有案件
        cases_db = db.session.query(Case).all()

        if not cases_db:
            return {"success": False, "error": "没有案件数据"}

        # 一次性加载所有案件的 Person / Account / Phone，避免 N+1 查询
        from database.models import Person, Account, Phone
        case_ids_all = [c.case_id for c in cases_db]
        persons_by_case = {}
        for p in db.session.query(Person).filter(Person.case_id.in_(case_ids_all)).all():
            persons_by_case.setdefault(p.case_id, []).append(p)
        person_ids_all = [p.id for ps in persons_by_case.values() for p in ps]
        accounts_by_person = {}
        for a in db.session.query(Account).filter(Account.person_id.in_(person_ids_all)).all():
            accounts_by_person.setdefault(a.person_id, []).append(a)
        phones_by_person = {}
        for ph in db.session.query(Phone).filter(Phone.person_id.in_(person_ids_all)).all():
            phones_by_person.setdefault(ph.person_id, []).append(ph)

        # 转换为字典格式（补全 detector 所需的全部字段）
        cases = []
        for case in cases_db:
            persons = persons_by_case.get(case.case_id, [])
            suspects = [p for p in persons if (p.role or '').lower() in ('suspect', 'perpetrator')]
            victims = [p for p in persons if (p.role or '').lower() == 'victim']

            # 汇总账户（来自所有相关人员）
            all_accounts = []
            for p in persons:
                for a in accounts_by_person.get(p.id, []):
                    all_accounts.append({
                        'account_number': a.account_number,
                        'bank_name': a.bank_name,
                        'risk_level': a.risk_level,
                        'owner': p.name,
                        'owner_role': p.role,
                    })

            # 汇总电话
            all_phones = []
            for p in persons:
                for ph in phones_by_person.get(p.id, []):
                    all_phones.append({
                        'phone_number': ph.phone_number,
                        'carrier': ph.carrier,
                        'owner': p.name,
                        'owner_role': p.role,
                    })

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
                'description': case.description,
                # 新增：让资金链通道生效的关键字段
                'accounts': all_accounts,
                'perpetrators': [{'name': s.name, 'phone': s.phone, 'gender': s.gender, 'age': s.age}
                                 for s in suspects],
                'victims': [{'name': v.name, 'phone': v.phone} for v in victims],
                'phones': all_phones,
                'extracted_entities': case.extracted_entities or {},
                'ai_report': case.ai_report or '',
                'created_at': case.created_at.isoformat() if case.created_at else None,
            })

        # 【增量匹配】mode='auto'（默认）且已有团伙画像时，新案先匹配画像，
        # 挂不上的攒批才重聚类；'full' 走下方全量重聚类（旧行为，结果与历史可比）。
        if (request.mode or 'auto').lower() != 'full' and db.session.query(Gang).count() > 0:
            return _run_incremental_detect(cases, current_user, request)

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

        # A4.2 冻卡决策持久化（独立 try，失败不影响研判返回）
        try:
            _gangs = result.get('gangs', [])
            persist_freeze_decisions(_gangs)
            # G8：团伙数 + 冻卡决策数 计数
            try:
                from core.metrics_exporter import inc_gangs, inc_freeze
                inc_gangs(len(_gangs))
                inc_freeze(len(_gangs))
            except Exception:
                pass
        except Exception as _e:
            logger.warning(f"冻卡决策落库失败(不影响研判返回): {_e}")

        # 【P0 修复】GNN 检测结果落库 GangCaseRelation
        # 旧版只写 FreezeDecision，团伙-案件关联完全丢失，刷新即消失
        try:
            from database.crud import save_gang, _cache_clear
            _saved_count = 0
            for g in result.get('gangs', []) or []:
                g.setdefault('relation_type', 'gnn_cluster')
                # 用团伙置信度作为默认 similarity
                if 'confidence' in g:
                    g.setdefault('relation_reasons', {})
                try:
                    save_gang(g, session_id=f"gnn_detect_{current_user.get('id', '')}")
                    _saved_count += 1
                except Exception as _ge:
                    logger.warning(f"团伙 {g.get('gang_id')} 关联落库失败: {_ge}")
            if _saved_count:
                logger.info(f"GNN 检测团伙-案件关联已落库: {_saved_count} 个团伙")
                _cache_clear()
        except Exception as _e:
            logger.warning(f"GNN 团伙关联落库失败(不影响返回): {_e}")

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
        gang = get_gang_by_id(gang_id, current_user)
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