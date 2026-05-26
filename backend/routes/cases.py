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
    update_case, search_cases_enhanced
)
import json

from database import db
from database.models import Case, Gang, GangCaseRelation
from database.p1_models import CapitalFlow
from .deps import get_current_user, log_operation, db_retry

def _radar_cache_get(key):
    try:
        from tools.redis_utils import get_redis
        r = get_redis()
        if r:
            data = r.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None

def _radar_cache_set(key, data, ttl=86400):
    try:
        from tools.redis_utils import get_redis
        r = get_redis()
        if r:
            r.setex(key, ttl, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass

router = APIRouter(prefix='/api/cases', tags=['案件'])


@router.get('')
@db_retry()
async def api_get_cases(current_user: dict = Depends(get_current_user)):
    try:
        cases = get_all_cases()
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
    except Exception:
        pass

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
    except Exception:
        pass
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
    except Exception:
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
    except Exception:
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
        case = get_case_by_id(case_id)
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
        case = create_case(body)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'create', 'case', case['case_id'], ip_address=ip)
        return {"success": True, "case": case}
    except Exception as e:
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