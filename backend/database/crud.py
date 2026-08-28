import numpy as np
import json
from datetime import datetime, timedelta
from . import db
from .models import (
    AnalysisSession, Case, Gang, GangCaseRelation,
    Person, Account, Phone, EvidenceItem,
    FreezeDecision, OperationLog
)
from tools.db import transactional

import logging
logger = logging.getLogger(__name__)


def apply_department_scope(model_cls, query, user):
    """G3 资源级 RBAC（行级隔离）。

    - admin / auditor：豁免，可见全部。
    - 普通用户：仅见本部门（department 匹配）或历史未归属（''）数据。
    - 无部门标识的用户（如老账号）：视为看全部，避免误锁。
    - user 为 None（内部/未鉴权路径）：不附加过滤。
    """
    if not user:
        return query
    role = (user.get('role') or '')
    if role in ('admin', 'auditor'):
        return query
    dept = (user.get('department') or '').strip()
    if not dept:
        return query
    return query.filter(
        db.or_(model_cls.department == dept, model_cls.department == '')
    )


def persist_freeze_decisions(gangs, session_id=None, reviewer_id=None):
    """研判产出后落库冻卡决策（A4.2，ADR-7 合规落地）。

    与 OperationLog（记'谁操作'）互补：本表记'决策事实'——
    团伙研判产出的冻卡建议（涉案账户/客观置信度/门控结论/复核人/时间），
    落 MySQL 可审计追溯。GangDetector 本身不碰 db，本表写入在路由层研判产出后。
    表不存在时幂等创建（不依赖迁移工具，A2 未做）。
    落库失败仅记日志、**不影响**研判主流程返回。返回落库条数。
    """
    try:
        FreezeDecision.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    count = 0
    try:
        for g in gangs or []:
            if not isinstance(g, dict):
                continue
            fd = FreezeDecision(
                gang_id=g.get('gang_id'),
                session_id=session_id,
                related_accounts=g.get('freeze_candidates') or g.get('related_accounts') or [],
                related_perpetrators=g.get('related_perpetrators') or [],
                confidence=g.get('confidence') or 0.0,
                gate_decision=g.get('gate_decision') or '待人工复核',
                risk_level=g.get('risk_level') or 'LOW',
                is_reflux=bool(g.get('is_reflux', False)),
                case_ids=g.get('case_ids') or [],
                reviewer_id=reviewer_id,
            )
            db.session.add(fd)
            count += 1
            # 互补：操作日志记"谁操作"
            db.session.add(OperationLog(
                action='freeze_decision',
                target_type='gang',
                target_id=g.get('gang_id') or '',
                detail={
                    'confidence': g.get('confidence'),
                    'gate_decision': g.get('gate_decision'),
                    'related_accounts': g.get('freeze_candidates') or [],
                    'is_reflux': bool(g.get('is_reflux', False)),
                },
            ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"persist_freeze_decisions failed: {e}")
        count = 0
    return count


def get_freeze_decisions(limit=200, gate_decision=None):
    """民警复核台：查询历史冻卡决策（A4.2）。"""
    try:
        FreezeDecision.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    q = FreezeDecision.query
    if gate_decision:
        q = q.filter_by(gate_decision=gate_decision)
    recs = q.order_by(FreezeDecision.created_at.desc()).limit(limit).all()
    return [r.to_dict() for r in recs]


def create_session(session_id, raw_input=None):
    with transactional():
        session = AnalysisSession(
            session_id=session_id,
            status='running',
            raw_input=raw_input
        )
        db.session.add(session)
        return session


def complete_session(session_id, status='completed', processing_info=None):
    with transactional():
        session = AnalysisSession.query.filter_by(session_id=session_id).first()
        if session:
            session.status = status
            session.completed_at = datetime.utcnow()
            if processing_info:
                session.processing_info = processing_info
        return session


def save_case(case_data, session_id=None):
    with transactional():
        existing = Case.query.filter_by(case_id=case_data['case_id']).first()
        if existing:
            return existing

        amount_str = case_data.get('amount', '0')
        amount_value = 0.0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            amount_value = num

        embedding_bytes = None
        if 'embedding' in case_data and case_data['embedding'] is not None:
            embedding_bytes = case_data['embedding'].tobytes() if isinstance(case_data['embedding'], np.ndarray) else case_data['embedding']

        roles_data = []
        for r in case_data.get('roles', []):
            if hasattr(r, 'dict'):
                roles_data.append(r.dict())
            elif isinstance(r, dict):
                roles_data.append(r)
            else:
                roles_data.append(str(r))

        case = Case(
            case_id=str(case_data['case_id']),
            session_id=session_id,
            title=case_data.get('title', f"案件{case_data['case_id']}"),
            scam_type=case_data.get('scam_type', ''),
            scam_subtype=case_data.get('scam_subtype', ''),
            risk_level=case_data.get('risk_level', 'LOW'),
            risk_label=case_data.get('risk_label', '低风险'),
            risk_type=case_data.get('risk_type', 'info'),
            risk_score=case_data.get('risk_score', 0),
            victim_name=case_data.get('victim', ''),
            amount=amount_str,
            amount_value=amount_value,
            description=case_data.get('description', case_data.get('ai_report', '')[:500]),
            status=case_data.get('status', '已分析'),
            source=case_data.get('source', '文本'),
            ai_report=case_data.get('ai_report', ''),
            keywords=case_data.get('keywords', []),
            steps=case_data.get('steps', []),
            roles=roles_data,
            extracted_entities=case_data.get('extracted_entities', {}),
            message_count=case_data.get('message_count', 0),
            time_range=case_data.get('time_range', ''),
            warning=case_data.get('warning', None),
            is_error=case_data.get('is_error', False),
            embedding=embedding_bytes
        )
        db.session.add(case)

        entities = case_data.get('extracted_entities', {})
        if entities.get('phone_numbers'):
            person = Person(
                case_id=case['case_id'],
                name=case_data.get('victim', ''),
                role='victim',
                phone=', '.join(entities['phone_numbers'][:3])
            )
            db.session.add(person)

        return case


def _safe_json(value):
    if isinstance(value, str):
        try: return json.loads(value)
        except: return []
    return value or []

def _safe_text(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value or ''

def _parse_json(value, default=None):
    if isinstance(value, str):
        try: return json.loads(value)
        except: return default or value
    return value if value else (default or value)

def save_gang(gang_data, session_id=None):
    """保存团伙 + 案件关联（带可解释性）。

    兼容两种输入格式（修复 P0 字段不匹配问题）：
    - 旧格式 related_cases: [{'case_id': 'CASE_xxx', 'similarity': 0.8, ...}]
    - 新格式 case_ids: ['CASE_xxx', 'CASE_yyy']  （GNN/gang_detector 产出）

    可解释性字段（可选）：
    - relation_reasons: {'CASE_xxx': '共享收款账户 6222****1234'}
    - matched_entities_map: {'CASE_xxx': ['6222****1234', '138****8888']}
    - relation_type: 'share_account' / 'gnn_cluster' / 'manual'
    """
    with transactional():
        existing = Gang.query.filter_by(gang_id=gang_data['gang_id']).first()
        if existing:
            # 已存在团伙：增量补充关联（不覆盖已有 fingerprint 等字段）
            _upsert_gang_case_relations(gang_data, existing.gang_id)
            # 同步 total_cases
            existing.total_cases = max(existing.total_cases or 0,
                                       GangCaseRelation.query.filter_by(gang_id=existing.gang_id).count())
            return existing

        amount_str = gang_data.get('total_amount_involved', '0')
        amount_value = 0.0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            amount_value = num

        centroid_bytes = None
        if 'centroid' in gang_data and gang_data['centroid'] is not None:
            centroid_bytes = gang_data['centroid'].tobytes() if isinstance(gang_data['centroid'], np.ndarray) else gang_data['centroid']

        gang = Gang(
            gang_id=gang_data['gang_id'],
            session_id=session_id,
            gang_name=gang_data.get('gang_name', ''),
            risk_level=gang_data.get('risk_level', 'C'),
            risk_label=gang_data.get('risk_label', '低风险'),
            risk_type=gang_data.get('risk_type', 'info'),
            threat_level=gang_data.get('threat_level', gang_data.get('risk_level', 'C')),
            comprehensive_score=gang_data.get('comprehensive_score', gang_data.get('risk_score', 0)),
            confidence=gang_data.get('confidence', 0),
            member_count_estimate=gang_data.get('member_count_estimate', ''),
            tech_level=gang_data.get('tech_level', '中'),
            script_type=gang_data.get('script_type', ''),
            total_cases=int(gang_data.get('total_cases', 0)),
            total_amount=amount_str,
            total_amount_value=amount_value,
            description=gang_data.get('description', ''),
            fingerprint=gang_data.get('fingerprint', []),
            enhanced_fingerprint=gang_data.get('enhanced_fingerprint', []),
            steps=gang_data.get('steps', []),
            radar_data=gang_data.get('radar_data', {}),
            deep_characteristics=gang_data.get('deep_characteristics', []),
            risk_assessment=gang_data.get('risk_assessment', {}),
            modus_operandi=gang_data.get('modus_operandi', ''),
            prevention_advice=_safe_text(gang_data.get('prevention_advice', '')),
            network_nodes=_safe_json(gang_data.get('network_nodes', [])),
            centroid=centroid_bytes,
            created_at=datetime.utcnow()
        )
        db.session.add(gang)
        db.session.flush()  # 确保 gang_id 落库

        _upsert_gang_case_relations(gang_data, gang.gang_id)

        # 同步 total_cases
        gang.total_cases = GangCaseRelation.query.filter_by(gang_id=gang.gang_id).count()
        return gang


def _upsert_gang_case_relations(gang_data, gang_id):
    """统一处理 case_ids / related_cases 两种格式，写入 GangCaseRelation。

    可解释性字段（优先级：case 级 > 团伙级）：
    - relation_type: 优先取 relation_type_map[case_id]（case 级客观证据类型），
                     否则取 gang_data['relation_type']（团伙级），最后兜底 'gnn_cluster'
    - reason: 优先取 relation_reasons[case_id]（gang_detector 生成的具体理由），
              否则用 _auto_relation_reason 生成团伙级理由
    - matched_entities: 取 matched_entities_map[case_id]
    """
    default_sim = float(gang_data.get('confidence', 0.5))
    gang_default_type = gang_data.get('relation_type', 'gnn_cluster')
    reasons_map = gang_data.get('relation_reasons', {}) or {}
    entities_map = gang_data.get('matched_entities_map', {}) or {}
    type_map = gang_data.get('relation_type_map', {}) or {}  # case 级证据类型

    # 统一收集 (case_id, similarity) 对
    case_pairs = []  # list of (case_id, similarity)

    # 来源 1: related_cases（对象数组，旧格式）
    for case_ref in gang_data.get('related_cases', []) or []:
        if isinstance(case_ref, dict):
            cid = str(case_ref.get('case_id', ''))
            sim = float(case_ref.get('similarity', default_sim))
        else:
            cid = str(case_ref)
            sim = default_sim
        if cid:
            case_pairs.append((cid, sim))

    # 来源 2: case_ids（字符串数组，GNN/gang_detector 新格式）
    for cid in gang_data.get('case_ids', []) or []:
        cid = str(cid)
        if cid and not any(p[0] == cid for p in case_pairs):
            case_pairs.append((cid, default_sim))

    for cid, sim in case_pairs:
        # 幂等：已存在则跳过（保留首次写入时的 reason）
        existing_rel = GangCaseRelation.query.filter_by(
            gang_id=gang_id, case_id=cid
        ).first()
        if existing_rel:
            continue

        # case 级证据类型优先，团伙级兜底
        rel_type = type_map.get(cid) or gang_default_type

        relation = GangCaseRelation(
            gang_id=gang_id,
            case_id=cid,
            similarity=sim,
            relation_type=rel_type,
            reason=reasons_map.get(cid, '') or _auto_relation_reason(gang_data, cid),
            matched_entities=entities_map.get(cid, []) or [],
        )
        db.session.add(relation)


def _auto_relation_reason(gang_data, case_id):
    """根据团伙数据自动生成关联理由（当外部未提供时）。"""
    parts = []
    if gang_data.get('gang_name'):
        parts.append(f"归入团伙「{gang_data['gang_name']}」")
    if gang_data.get('modus_operandi'):
        parts.append(f"作案手法: {gang_data['modus_operandi'][:60]}")
    if gang_data.get('script_type'):
        parts.append(f"话术类型: {gang_data['script_type']}")

    # 检查是否有共享实体信号
    fingerprint = gang_data.get('fingerprint') or gang_data.get('enhanced_fingerprint') or []
    if isinstance(fingerprint, list):
        for fp in fingerprint[:3]:
            if isinstance(fp, dict):
                label = fp.get('label') or fp.get('name') or ''
                if label:
                    parts.append(f"特征命中: {label}")

    return '；'.join(parts) if parts else 'GNN 聚类关联'


_list_cache = {}
_list_cache_ttl = 3600

def _cache_get(key):
    val = _list_cache.get(key)
    if val and (datetime.utcnow() - val['ts']).seconds < _list_cache_ttl:
        return val['data']
    return None

def _cache_set(key, data):
    _list_cache[key] = {'data': data, 'ts': datetime.utcnow()}

def _cache_clear():
    _list_cache.clear()


def get_all_cases(user=None):
    cache_key = f'all_cases:{user.get("department", "") if user else "all"}'
    cached = _cache_get(cache_key)
    if cached:
        return cached
    q = Case.query
    q = apply_department_scope(Case, q, user)
    cases = q.order_by(Case.created_at.desc()).all()
    result = [_case_to_dict(c) for c in cases]
    _cache_set(cache_key, result)
    return result


def get_case_by_id(case_id, user=None):
    q = Case.query.filter_by(case_id=case_id)
    q = apply_department_scope(Case, q, user)
    case = q.first()
    return _case_to_dict(case) if case else None


def get_gang_by_id(gang_id, user=None):
    q = Gang.query.filter_by(gang_id=gang_id)
    q = apply_department_scope(Gang, q, user)
    gang = q.first()
    return _gang_to_dict(gang) if gang else None


def get_sessions():
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).limit(20).all()
    return [{
        'session_id': s.session_id,
        'status': s.status,
        'total_cases': s.total_cases,
        'total_gangs': s.total_gangs,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'completed_at': s.completed_at.isoformat() if s.completed_at else None
    } for s in sessions]


def get_session_detail(session_id, user=None):
    session = AnalysisSession.query.filter_by(session_id=session_id).first()
    if not session:
        return None
    q_cases = Case.query.filter_by(session_id=session_id)
    q_gangs = Gang.query.filter_by(session_id=session_id)
    if user:
        # 行级隔离：非 admin 仅见本部门案件/团伙（G3 RBAC）
        q_cases = apply_department_scope(Case, q_cases, user)
        q_gangs = apply_department_scope(Gang, q_gangs, user)
    cases = q_cases.all()
    gangs = q_gangs.all()
    return {
        'session': {
            'session_id': session.session_id,
            'status': session.status,
            'total_cases': session.total_cases,
            'total_gangs': session.total_gangs,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'processing_info': session.processing_info
        },
        'cases': [_case_to_dict(c) for c in cases],
        'gangs': [_gang_to_dict(g) for g in gangs]
    }


def search_cases(query):
    if not query:
        return []
    query = query.strip()
    # 纯数字查询：按编号后缀 + 标题模糊搜索，避免 amount/description 全量命中
    # case_id 格式如 FC-2025-00005 或 FC20250522001，用后缀匹配 %{query} 定位末尾编号
    if query.isdigit():
        cases = Case.query.filter(
            db.or_(
                Case.case_id.ilike(f'%{query}'),
                Case.title.ilike(f'%{query}%')
            )
        ).order_by(Case.created_at.desc()).all()
    else:
        cases = Case.query.filter(
            db.or_(
                Case.case_id.ilike(f'%{query}%'),
                Case.victim_name.ilike(f'%{query}%'),
                Case.scam_type.ilike(f'%{query}%'),
                Case.title.ilike(f'%{query}%'),
                Case.description.ilike(f'%{query}%'),
                Case.keywords.ilike(f'%{query}%')
            )
        ).order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]


def delete_session(session_id):
    GangCaseRelation.query.filter(
        GangCaseRelation.gang_id.in_(
            db.session.query(Gang.gang_id).filter(Gang.session_id == session_id)
        )
    ).delete(synchronize_session=False)
    Gang.query.filter_by(session_id=session_id).delete()
    Case.query.filter_by(session_id=session_id).delete()
    AnalysisSession.query.filter_by(session_id=session_id).delete()
    db.session.commit()


def _case_to_dict(c):
    if not c:
        return None
    created_str = c.created_at.isoformat() if c.created_at else None
    date_str = c.created_at.isoformat()[:10] if c.created_at else None
    return {
        'case_id': c.case_id,
        'id': c.case_id,
        'number': c.number or 0,
        'title': c.title,
        'scam_type': c.scam_type,
        'type': c.scam_type,
        'scam_subtype': c.scam_subtype,
        'risk_level': c.risk_level,
        'risk_label': c.risk_label,
        'risk_type': c.risk_type,
        'risk_score': c.risk_score,
        'victim': c.victim_name,
        'victimName': c.victim_name,
        'victim_name': c.victim_name,
        'victim_gender': c.victim_gender,
        'victim_age': c.victim_age,
        'victim_phone': c.victim_phone,
        'victimPhone': c.victim_phone,
        'victim_job': c.victim_job,
        'victimJob': c.victim_job,
        'victim_address': c.victim_address,
        'victimAddress': c.victim_address,
        'amount': c.amount,
        'amount_value': c.amount_value,
        'description': c.description,
        'status': c.status,
        'source': c.source,
        'ai_report': c.ai_report,
        'keywords': c.keywords if c.keywords else [],
        'steps': c.steps if c.steps else [],
        'roles': c.roles if c.roles else [],
        'extracted_entities': c.extracted_entities if c.extracted_entities else {},
        'message_count': c.message_count,
        'time_range': c.time_range,
        'warning': c.warning,
        'is_error': c.is_error,
        'is_demo': bool(c.is_demo) if c.is_demo is not None else False,
        'radar_data': c.radar_data if c.radar_data else {},
        'department': c.department or '',
        'date': date_str,
        'created_at': created_str
    }


def _build_gang_dict(g, related_cases, cases_map):
    case_details = []
    case_ids = []  # 兼容前端 getCaseGang（使用 case_ids.includes 判断）
    relation_reasons = {}  # case_id -> reason，供前端展示关联理由
    matched_entities_map = {}  # case_id -> entities

    for rel in related_cases:
        case_ids.append(rel.case_id)
        # 关联理由（新增可解释性字段）
        if getattr(rel, 'reason', None):
            relation_reasons[rel.case_id] = rel.reason
        if getattr(rel, 'matched_entities', None):
            matched_entities_map[rel.case_id] = rel.matched_entities

        case = cases_map.get(rel.case_id)
        if case:
            case_details.append({
                'case_id': case.case_id,
                'victim': case.victim_name,
                'amount': case.amount,
                'snippet': (case.ai_report or '')[:60] + '...' if case.ai_report else '',
                'risk_level': case.risk_level,
                'similarity': rel.similarity,
                'relation_type': getattr(rel, 'relation_type', 'gnn_cluster'),
                'reason': getattr(rel, 'reason', '') or '',
                'matched_entities': getattr(rel, 'matched_entities', []) or [],
            })

    # 用实际关联数修正 total_cases（避免冗余计数不一致）
    actual_count = len(case_ids)

    return {
        'gang_id': g.gang_id,
        'id': g.gang_id,
        'number': g.number or 0,
        'gang_name': g.gang_name,
        'name': g.gang_name,
        'risk_level': g.risk_level,
        'riskLevel': g.risk_level,
        'risk_label': g.risk_label,
        'riskLabel': g.risk_label,
        'risk_type': g.risk_type,
        'threat_level': g.threat_level,
        'comprehensive_score': g.comprehensive_score,
        'confidence': g.confidence,
        'member_count_estimate': g.member_count_estimate,
        'tech_level': g.tech_level,
        'script_type': g.script_type,
        'total_cases': actual_count if actual_count > 0 else (g.total_cases or 0),
        'cases': actual_count if actual_count > 0 else (g.total_cases or 0),
        'case_ids': case_ids,  # 新增：前端 getCaseGang 直接使用
        'caseIds': case_ids,   # 兼容驼峰命名
        'total_amount_involved': g.total_amount,
        'total_amount': g.total_amount,
        'amount': g.total_amount,
        'total_amount_value': g.total_amount_value,
        'description': g.description,
        'fingerprint': g.fingerprint if g.fingerprint else [],
        'enhanced_fingerprint': g.enhanced_fingerprint if g.enhanced_fingerprint else [],
        'steps': g.steps if g.steps else [],
        'radar_data': g.radar_data if g.radar_data else {},
        'deep_characteristics': _parse_json(g.deep_characteristics, []),
        'risk_assessment': _parse_json(g.risk_assessment, {}),
        'modus_operandi': g.modus_operandi or '',
        'prevention_advice': g.prevention_advice,
        'network_nodes': _parse_json(g.network_nodes, []),
        'related_cases': case_details,
        'relation_reasons': relation_reasons,  # 新增：案件->理由 映射
        'matched_entities_map': matched_entities_map,  # 新增：案件->命中实体 映射
        'department': g.department or '',
        'created_at': g.created_at.isoformat() if g.created_at else None
    }


def _gang_to_dict(g):
    if not g:
        return None
    related_cases = GangCaseRelation.query.filter_by(gang_id=g.gang_id).all()
    case_ids = [r.case_id for r in related_cases]
    cases_map = {}
    if case_ids:
        cases_map = {c.case_id: c for c in Case.query.filter(Case.case_id.in_(case_ids)).all()}
    return _build_gang_dict(g, related_cases, cases_map)


def get_all_gangs(user=None):
    cache_key = f'all_gangs:{user.get("department", "") if user else "all"}'
    cached = _cache_get(cache_key)
    if cached:
        return cached
    q = Gang.query
    q = apply_department_scope(Gang, q, user)
    gangs = q.order_by(Gang.created_at.desc()).all()
    gang_ids = [g.gang_id for g in gangs]
    all_relations = GangCaseRelation.query.filter(GangCaseRelation.gang_id.in_(gang_ids)).all()
    gang_rels = {}
    for r in all_relations:
        gang_rels.setdefault(r.gang_id, []).append(r)
    all_case_ids = list(set(r.case_id for r in all_relations))
    cases_map = {}
    if all_case_ids:
        cases_map = {c.case_id: c for c in Case.query.filter(Case.case_id.in_(all_case_ids)).all()}
    result = [_build_gang_dict(g, gang_rels.get(g.gang_id, []), cases_map) for g in gangs]
    _cache_set(cache_key, result)
    return result


VALID_STATUS_TRANSITIONS = {
    '待分析': ['已分析'],
    '已分析': ['已立案'],
    '已立案': ['侦办中'],
    '侦办中': ['已结案'],
    '已结案': [],
}


def update_case(case_id, data):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')

        allowed_fields = {
            'title', 'victim_name', 'victim_gender', 'victim_age',
            'victim_phone', 'victim_address', 'victim_job',
            'scam_type', 'amount', 'description', 'status',
            'risk_level', 'risk_label'
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                if key == 'status':
                    # 状态必须走状态机（复用 update_case_status 的流转校验），
                    # 防止绕过 VALID_STATUS_TRANSITIONS 任意跳转（如 待分析→已结案）
                    try:
                        current = case.status or '待分析'
                        allowed = VALID_STATUS_TRANSITIONS.get(current, [])
                        if value != current and value not in allowed:
                            raise ValueError(
                                f'Invalid status transition: {current} -> {value}. '
                                f'Allowed targets: {allowed}'
                            )
                    except ValueError:
                        raise
                    except Exception:
                        pass  # 状态值非法时仍 setattr，由 DB 约束兜底
                setattr(case, key, value)

        if 'amount' in data:
            import re
            amount_raw = data['amount']
            # 兼容数字与字符串（审计 L：amount 传数字时 re.search 抛 TypeError）
            if isinstance(amount_raw, (int, float)):
                case.amount_value = float(amount_raw)
            elif isinstance(amount_raw, str) and amount_raw.strip():
                match = re.search(r'(\d+(?:\.\d+)?)', amount_raw)
                if match:
                    num = float(match.group(1))
                    if '万' in amount_raw:
                        num *= 10000
                    case.amount_value = num

        return _case_to_dict(case)


def update_case_status(case_id, new_status):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')

        current = case.status or '待分析'
        allowed = VALID_STATUS_TRANSITIONS.get(current, [])

        if current == new_status:
            return _case_to_dict(case)

        if new_status not in allowed:
            raise ValueError(
                f'Invalid status transition: {current} -> {new_status}. '
                f'Allowed targets: {allowed}'
            )

        case.status = new_status
        return _case_to_dict(case)


def get_case_stats():
    total = Case.query.count()
    status_counts = dict(
        db.session.query(Case.status, db.func.count(Case.id))
        .group_by(Case.status)
        .all()
    )

    total_amount = db.session.query(db.func.sum(Case.amount_value)).scalar() or 0.0

    risk_distribution = dict(
        db.session.query(Case.risk_level, db.func.count(Case.id))
        .group_by(Case.risk_level)
        .all()
    )

    scam_type_stats = dict(
        db.session.query(Case.scam_type, db.func.count(Case.id))
        .filter(Case.scam_type != '')
        .group_by(Case.scam_type)
        .order_by(db.func.count(Case.id).desc())
        .limit(10)
        .all()
    )

    recent_cases = Case.query.order_by(Case.created_at.desc()).limit(5).all()
    recent = [_case_to_dict(c) for c in recent_cases]

    return {
        'total_cases': total,
        'status_distribution': status_counts,
        'total_amount_value': round(total_amount, 2),
        'risk_distribution': risk_distribution,
        'top_scam_types': scam_type_stats,
        'recent_cases': recent,
    }


def generate_case_number():
    today = datetime.now().strftime('%Y%m%d')
    prefix = f'ALT{today}'
    latest = Case.query.filter(Case.case_id.like(f'{prefix}%')).order_by(Case.case_id.desc()).first()
    if latest:
        seq = int(latest.case_id[-3:]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:03d}'


def create_case(data, department: str = ''):
    with transactional():
        # 案号并发竞态防护：generate_case_number 为查-算-插（无锁），并发下可能撞号。
        # 在插入前检查该 case_id 是否已存在，存在则重试下一序号（至多 20 次）。
        case_id = generate_case_number()
        for _ in range(20):
            if Case.query.filter_by(case_id=case_id).first() is None:
                break
            latest = Case.query.filter(
                Case.case_id.like(f"ALT{datetime.now().strftime('%Y%m%d')}%")
            ).order_by(Case.case_id.desc()).first()
            seq = (int(case_id[-3:]) if case_id[-3:].isdigit() else 0) + 1
            case_id = f"ALT{datetime.now().strftime('%Y%m%d')}{seq:03d}"

        amount_str = data.get('amount', '0')
        amount_value = 0.0
        import re
        # 兼容数字输入（amount 传 int/float 时 re.search 抛 TypeError）
        if isinstance(amount_str, (int, float)):
            amount_value = float(amount_str)
            amount_str = str(amount_str)
        else:
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            if match:
                num = float(match.group(1))
                if '万' in amount_str:
                    num *= 10000
                amount_value = num

        scam_type = data.get('scam_type', '')
        victim_name = data.get('victim_name', '')

        case = Case(
            case_id=case_id,
            title=data.get('title', ''),
            victim_name=victim_name,
            victim_gender=data.get('victim_gender', ''),
            victim_age=data.get('victim_age', ''),
            victim_phone=data.get('victim_phone', ''),
            victim_address=data.get('victim_address', ''),
            victim_job=data.get('victim_job', ''),
            scam_type=scam_type,
            amount=amount_str,
            amount_value=amount_value,
            description=data.get('description', ''),
            status='待分析',
            source='手动录入',
            department=(department or '')
        )
        db.session.add(case)
        db.session.flush()

        try:
            from .p1_models import CapitalFlow, DispatchOrder, AlertRecord
            import random

            source_accounts = ['6222****1234', '6217****5678', '6228****9012']
            target_accounts = ['6214****3456', '6221****7890', '6230****2345']
            banks = ['工商银行', '建设银行', '农业银行', '中国银行', '招商银行']
            annotations = ['境内转账', '第三方支付', '境内转账']

            num_flows = random.randint(3, 5)
            for i in range(num_flows):
                flow = CapitalFlow(
                    case_id=case_id,
                    source_account=random.choice(source_accounts),
                    target_account=random.choice(target_accounts),
                    bank_name=random.choice(banks),
                    amount=round(random.uniform(amount_value * 0.1, amount_value * 0.5), 2) if amount_value > 0 else round(random.uniform(1000, 50000), 2),
                    direction='out' if i % 3 != 0 else 'in',
                    level=random.randint(1, 3),
                    annotation=random.choice(annotations)
                )
                db.session.add(flow)

            dispatch = DispatchOrder(
                case_id=case_id,
                title=f'预警派单-{scam_type or "未知类型"}',
                content=f'系统预警{scam_type or "未知"}案件，涉案金额{amount_str}，请及时处置',
                status='pending',
                priority='中',
                district=data.get('victim_address', '')[:15] if victim_name else '',
                assignee='系统自动派单'
            )
            db.session.add(dispatch)

            alert = AlertRecord(
                alert_type='case_match',
                case_id=case_id,
                matched_case_id=case_id,
                title=f'新案件预警-{scam_type or "未知类型"}',
                content=f'新录入{scam_type or "未知"}案件，涉案金额{amount_str}，受害人{victim_name}',
                status='未处理',
                confidence=0.85,
                matched_entities=[victim_name] if victim_name else []
            )
            db.session.add(alert)

        except ImportError:
            pass

        return _case_to_dict(case)


def delete_case(case_id):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')
        case.status = '已删除'
        return True


def search_cases_enhanced(query):
    if not query:
        return []
    cases = Case.query.filter(
        db.or_(
            Case.case_id.ilike(f'%{query}%'),
            Case.title.ilike(f'%{query}%'),
            Case.victim_name.ilike(f'%{query}%'),
            Case.scam_type.ilike(f'%{query}%')
        )
    ).order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]