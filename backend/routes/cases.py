"""
Case CRUD routes.
"""
import os
import math
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database.crud import (
    get_all_cases, get_case_by_id, get_case_stats,
    update_case_status, create_case, delete_case,
    update_case, search_cases_enhanced, save_case
)
import json

from database import db
from database.models import Case, Gang, GangCaseRelation, AlertRecord
from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
from .deps import get_current_user, log_operation, db_retry
from tools.response import logger

def _radar_cache_get(key):
    try:
        from tools.redis_utils import get_redis
        r = get_redis()
        if r:
            data = r.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis缓存读取失败: {e}")
    return None

def _radar_cache_set(key, data, ttl=86400):
    try:
        from tools.redis_utils import get_redis
        r = get_redis()
        if r:
            r.setex(key, ttl, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Redis缓存写入失败: {e}")

router = APIRouter(prefix='/api/cases', tags=['案件'])


@router.get('')
@db_retry()
async def api_get_cases(current_user: dict = Depends(get_current_user)):
    try:
        cases = get_all_cases(current_user)
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def _compute_case_radar(case) -> dict:
    cache_key = f'radar:case:{case.case_id}'
    cached = _radar_cache_get(cache_key)
    if cached:
        return cached

    if case.radar_data and isinstance(case.radar_data, dict) and len(case.radar_data) >= 4:
        first_key = next(iter(case.radar_data))
        if any(ord(c) > 0x4e00 for c in first_key):
            return case.radar_data

    amount_val = case.amount_value or 0
    if amount_val <= 0:
        try:
            amount_val = float(case.amount or 0)
        except (ValueError, TypeError):
            amount_val = 0

    scam_sophistication = min(95, 30 + (amount_val / 10000) * 2)
    if case.scam_type and '冒充' in (case.scam_type or ''):
        scam_sophistication = min(95, scam_sophistication + 15)
    if case.scam_type and '杀猪盘' in (case.scam_type or ''):
        scam_sophistication = min(95, scam_sophistication + 20)

    fund_dispersion = 30
    steps = case.steps or []
    if isinstance(steps, list) and len(steps) > 0:
        fund_dispersion = min(95, 25 + len(steps) * 12)
    try:
        flow_count = db.session.query(CapitalFlow).filter(
            CapitalFlow.case_id == case.case_id
        ).count()
        if flow_count > 0:
            fund_dispersion = min(95, 25 + flow_count * 8)
    except Exception as e:
        logger.warning(f"查询资金流向失败: {e}")

    tech_level = 35
    entities = case.extracted_entities or {}
    if isinstance(entities, dict):
        if entities.get('url') or entities.get('ip'):
            tech_level += 15
        if entities.get('app') or entities.get('platform'):
            tech_level += 10
    keywords = case.keywords or []
    if isinstance(keywords, list):
        tech_kw = ['屏幕共享', '远程操控', 'VPN', '虚拟货币', 'USDT', 'APP', '钓鱼网站']
        for kw in tech_kw:
            if any(kw in str(k) for k in keywords):
                tech_level += 8
    tech_level = min(95, tech_level)

    victim_targeting = 30
    if case.victim_age:
        victim_targeting += 10
    if case.victim_job:
        victim_targeting += 8
    if case.scam_type:
        targeting_map = {
            '冒充客服': 75, '刷单返利': 65, '冒充公检法': 80,
            '投资理财': 70, '网络贷款': 55, '冒充熟人': 60,
            '杀猪盘': 85, '注销校园贷': 50
        }
        for k, v in targeting_map.items():
            if k in (case.scam_type or ''):
                victim_targeting = max(victim_targeting, v)
    victim_targeting = min(95, victim_targeting)

    cross_region = 30
    addr = case.victim_address or ''
    if addr and len(addr) > 6:
        cross_region += 15
    if entities and isinstance(entities, dict):
        if entities.get('overseas') or entities.get('境外'):
            cross_region += 25
    try:
        flows = db.session.query(CapitalFlow).filter(
            CapitalFlow.case_id == case.case_id,
            CapitalFlow.annotation.ilike('%境外%')
        ).count()
        if flows > 0:
            cross_region += 20
    except Exception as e:
        logger.warning(f"查询境外资金流向失败: {e}")
    cross_region = min(95, cross_region)

    anti_detection = 30
    anti_kw = ['虚拟号码', 'VOIP', 'GOIP', '伪装', '翻墙', '加密', '匿名']
    if isinstance(keywords, list):
        for ak in anti_kw:
            if any(ak in str(k) for k in keywords):
                anti_detection += 12
    if case.risk_level in ['HIGH', 'S', 'CRITICAL']:
        anti_detection += 15
    anti_detection = min(95, anti_detection)

    radar = {
        '诈骗话术成熟度': int(scam_sophistication),
        '资金分散程度': int(fund_dispersion),
        '技术手段先进性': int(tech_level),
        '受害者画像精准度': int(victim_targeting),
        '跨区域作案特征': int(cross_region),
        '反侦察能力': int(anti_detection)
    }

    try:
        case.radar_data = radar
        db.session.commit()
    except Exception as e:
        logger.warning(f"保存案件雷达图数据失败: {e}")
        db.session.rollback()

    _radar_cache_set(cache_key, radar)
    return radar


@router.get('/{case_id}/radar')
async def api_get_case_radar(case_id: str, current_user: dict = Depends(get_current_user)):
    try:
        case = db.session.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        radar = _compute_case_radar(case)
        return {"success": True, "case_id": case_id, "radar": radar}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def _compute_gang_radar(gang) -> dict:
    cache_key = f'radar:gang:{gang.gang_id}'
    cached = _radar_cache_get(cache_key)
    if cached:
        return cached

    if gang.radar_data and isinstance(gang.radar_data, dict) and len(gang.radar_data) >= 4:
        first_key = next(iter(gang.radar_data))
        if any(ord(c) > 0x4e00 for c in first_key):
            return gang.radar_data

    relations = db.session.query(GangCaseRelation).filter(
        GangCaseRelation.gang_id == gang.gang_id
    ).all()
    case_ids = [r.case_id for r in relations]

    if not case_ids:
        return {
            '诈骗话术成熟度': 50, '资金分散程度': 50,
            '成员关联密度': 50, '跨区域作案特征': 50,
            '技术手段先进性': 50, '受害者画像精准度': 50
        }

    cases = db.session.query(Case).filter(Case.case_id.in_(case_ids)).all()
    if not cases:
        return {
            '诈骗话术成熟度': 50, '资金分散程度': 50,
            '成员关联密度': 50, '跨区域作案特征': 50,
            '技术手段先进性': 50, '受害者画像精准度': 50
        }

    radar_sum = {}
    for c in cases:
        cr = _compute_case_radar(c)
        for k, v in cr.items():
            radar_sum[k] = radar_sum.get(k, 0) + v

    n = len(cases)
    radar = {k: min(95, int(v / n)) for k, v in radar_sum.items()}

    member_density = min(95, 30 + len(case_ids) * 8)
    radar['成员关联密度'] = member_density

    try:
        gang.radar_data = radar
        db.session.commit()
    except Exception as e:
        logger.warning(f"保存团伙雷达图数据失败: {e}")
        db.session.rollback()

    _radar_cache_set(cache_key, radar)
    return radar


@router.get('/stats')
async def api_case_stats(current_user: dict = Depends(get_current_user)):
    try:
        stats = get_case_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/search')
async def api_search_cases(q: str = '', current_user: dict = Depends(get_current_user)):
    try:
        if not q:
            return {"success": True, "cases": []}
        cases = search_cases_enhanced(q)
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{case_id}')
async def api_get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    try:
        case = get_case_by_id(case_id, current_user)
        if case:
            return {"success": True, "case": case}
        return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/{case_id}')
async def api_update_case(case_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        result = update_case(case_id, body)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'update', 'case', case_id, ip_address=ip)
        return {"success": True, "case": result}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/{case_id}/status')
async def api_update_case_status(case_id: str, request: Request,
                                  current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        new_status = body.get('status', '')
        if not new_status:
            raise HTTPException(status_code=400, detail="缺少状态参数")
        result = update_case_status(case_id, new_status)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'update_status', 'case', case_id, {'new_status': new_status}, ip_address=ip)
        return {"success": True, "case": result}
    except HTTPException:
        raise
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('')
async def api_create_case(request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        case = create_case(body, current_user.get('department', ''))
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'create', 'case', case['case_id'], ip_address=ip)
        return {"success": True, "case": case}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/from-text')
async def api_create_cases_from_text(request: Request,
                                     current_user: dict = Depends(get_current_user)):
    """笔录 / OCR 文本 → 抽取结构化案件并批量落库（REQ-S1.4 落库链路）。

    请求体: {"text": "受害人张三报警称...", "source": "笔录/OCR"}
    纯正则零出域抽取，落库复用 save_case（含 extracted_entities → Person 关联），
    新案默认 status='待分析'，可直接进入 orchestrator 研判链路。
    """
    try:
        body = await request.json()
        text = (body.get('text') or '').strip()
        source = body.get('source') or '笔录/OCR'
        if not text:
            raise HTTPException(status_code=400, detail="缺少 text 文本")

        # 懒导入，避免 routes 包加载时触发 agents 重依赖
        from agents.text_to_cases import text_to_cases
        cases = text_to_cases(text, source=source)
        if not cases:
            return {"success": True, "created": 0, "case_ids": [],
                    "message": "未从文本中识别到案件"}

        saved_ids = []
        for c in cases:
            try:
                case = save_case(c)  # 复用落库；status 默认'待分析'，实体→Person 关联
                saved_ids.append(case.case_id)
            except Exception as e:
                logger.warning(f"单案落库失败 {c.get('case_id')}: {e}")

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'create_from_text', 'case', ','.join(saved_ids[:20]),
                      {'count': len(saved_ids), 'source': source}, ip_address=ip)
        return {"success": True, "created": len(saved_ids),
                "case_ids": saved_ids, "cases": cases}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete('/demo')
async def api_delete_demo_cases(request: Request,
                                 current_user: dict = Depends(get_current_user)):
    """清空所有演示数据（is_demo=True 的案件及其关联数据）。需要 admin 权限。"""
    if (current_user.get('role') or '') != 'admin':
        return JSONResponse(status_code=403, content={"success": False, "error": "需要管理员权限"})
    try:
        demo_cases = db.session.query(Case).filter(Case.is_demo == True).all()
        demo_case_ids = [c.case_id for c in demo_cases]
        if not demo_case_ids:
            return {"success": True, "deleted_cases": 0, "deleted_related": 0}

        deleted_related = 0
        demo_id_set = set(demo_case_ids)

        # 资金流
        try:
            n = db.session.query(CapitalFlow).filter(
                CapitalFlow.case_id.in_(demo_case_ids)
            ).delete(synchronize_session=False)
            deleted_related += n or 0
        except Exception as e:
            logger.warning(f"清理资金流失败: {e}")
        # 派单
        try:
            n = db.session.query(DispatchOrder).filter(
                DispatchOrder.case_id.in_(demo_case_ids)
            ).delete(synchronize_session=False)
            deleted_related += n or 0
        except Exception as e:
            logger.warning(f"清理派单失败: {e}")
        # 预警（case_id 或 matched_case_id 命中演示案件）
        try:
            n = db.session.query(AlertRecord).filter(
                db.or_(
                    AlertRecord.case_id.in_(demo_case_ids),
                    AlertRecord.matched_case_id.in_(demo_case_ids),
                )
            ).delete(synchronize_session=False)
            deleted_related += n or 0
        except Exception as e:
            logger.warning(f"清理预警失败: {e}")
        # 团伙关联 + 删除已无关联的孤儿团伙（演示数据创建的团伙）
        try:
            n = db.session.query(GangCaseRelation).filter(
                GangCaseRelation.case_id.in_(demo_case_ids)
            ).delete(synchronize_session=False)
            deleted_related += n or 0
            remaining_gang_ids = {
                r[0] for r in db.session.query(GangCaseRelation.gang_id).distinct().all()
            }
            for g in db.session.query(Gang).all():
                if g.gang_id not in remaining_gang_ids:
                    db.session.delete(g)
                    deleted_related += 1
        except Exception as e:
            logger.warning(f"清理团伙关联失败: {e}")
        # 重点人员：从 case_ids 中移除演示案件引用，无剩余引用则删除
        try:
            for p in db.session.query(KeyPerson).all():
                ids = p.case_ids if isinstance(p.case_ids, list) else []
                remaining = [cid for cid in ids if cid not in demo_id_set]
                if remaining == ids:
                    continue
                if remaining:
                    p.case_ids = remaining
                else:
                    db.session.delete(p)
                    deleted_related += 1
        except Exception as e:
            logger.warning(f"清理重点人员失败: {e}")
        # 案件本体
        deleted_cases = db.session.query(Case).filter(
            Case.case_id.in_(demo_case_ids)
        ).delete(synchronize_session=False)

        db.session.commit()

        # 清列表缓存，避免脏读
        try:
            from database.crud import _cache_clear
            _cache_clear()
        except Exception:
            pass

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'delete_demo', 'cases', f'{deleted_cases} demo cases',
                      ip_address=ip)
        return {
            "success": True,
            "deleted_cases": deleted_cases or 0,
            "deleted_related": deleted_related,
        }
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete('/{case_id}')
async def api_delete_case(case_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        delete_case(case_id)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'delete', 'case', case_id, ip_address=ip)
        return {"success": True, "message": "已删除"}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})