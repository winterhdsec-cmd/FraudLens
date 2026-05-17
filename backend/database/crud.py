import numpy as np
import json
from datetime import datetime
from . import db
from .models import (
    AnalysisSession, Case, Gang, GangCaseRelation,
    Person, Account, Phone, EvidenceItem
)


def create_session(session_id, raw_input=None):
    session = AnalysisSession(
        session_id=session_id,
        status='running',
        raw_input=raw_input
    )
    db.session.add(session)
    db.session.commit()
    return session


def complete_session(session_id, status='completed', processing_info=None):
    session = AnalysisSession.query.filter_by(session_id=session_id).first()
    if session:
        session.status = status
        session.completed_at = datetime.utcnow()
        if processing_info:
            session.processing_info = processing_info
        db.session.commit()
    return session


def save_case(case_data, session_id=None):
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
        status='已分析',
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
    db.session.commit()

    entities = case_data.get('extracted_entities', {})
    if entities.get('phone_numbers'):
        person = Person(
            case_id=case['case_id'],
            name=case_data.get('victim', ''),
            role='victim',
            phone=', '.join(entities['phone_numbers'][:3])
        )
        db.session.add(person)
        db.session.commit()

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
    existing = Gang.query.filter_by(gang_id=gang_data['gang_id']).first()
    if existing:
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
    db.session.commit()

    for case_ref in gang_data.get('related_cases', []):
        relation = GangCaseRelation(
            gang_id=gang_data['gang_id'],
            case_id=str(case_ref.get('case_id', '')),
            similarity=case_ref.get('similarity', 0.0)
        )
        db.session.add(relation)

    db.session.commit()
    return gang


def get_all_cases():
    cases = Case.query.order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]


def get_case_by_id(case_id):
    case = Case.query.filter_by(case_id=case_id).first()
    return _case_to_dict(case) if case else None


def get_all_gangs():
    gangs = Gang.query.order_by(Gang.created_at.desc()).all()
    return [_gang_to_dict(g) for g in gangs]


def get_gang_by_id(gang_id):
    gang = Gang.query.filter_by(gang_id=gang_id).first()
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


def get_session_detail(session_id):
    session = AnalysisSession.query.filter_by(session_id=session_id).first()
    if not session:
        return None
    cases = Case.query.filter_by(session_id=session_id).all()
    gangs = Gang.query.filter_by(session_id=session_id).all()
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
    cases = Case.query.filter(
        db.or_(
            Case.case_id.ilike(f'%{query}%'),
            Case.victim_name.ilike(f'%{query}%'),
            Case.scam_type.ilike(f'%{query}%'),
            Case.amount.ilike(f'%{query}%')
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
    return {
        'case_id': c.case_id,
        'title': c.title,
        'scam_type': c.scam_type,
        'risk_level': c.risk_level,
        'risk_label': c.risk_label,
        'risk_type': c.risk_type,
        'risk_score': c.risk_score,
        'victim': c.victim_name,
        'victim_gender': c.victim_gender,
        'victim_age': c.victim_age,
        'victim_phone': c.victim_phone,
        'victim_job': c.victim_job,
        'victim_address': c.victim_address,
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
        'created_at': c.created_at.isoformat() if c.created_at else None
    }


def _gang_to_dict(g):
    if not g:
        return None
    related_cases = GangCaseRelation.query.filter_by(gang_id=g.gang_id).all()
    case_details = []
    for rel in related_cases:
        case = Case.query.filter_by(case_id=rel.case_id).first()
        if case:
            case_details.append({
                'case_id': case.case_id,
                'victim': case.victim_name,
                'amount': case.amount,
                'snippet': (case.ai_report or '')[:60] + '...' if case.ai_report else '',
                'risk_level': case.risk_level
            })

    return {
        'gang_id': g.gang_id,
        'gang_name': g.gang_name,
        'risk_level': g.risk_level,
        'risk_label': g.risk_label,
        'risk_type': g.risk_type,
        'threat_level': g.threat_level,
        'comprehensive_score': g.comprehensive_score,
        'confidence': g.confidence,
        'member_count_estimate': g.member_count_estimate,
        'tech_level': g.tech_level,
        'script_type': g.script_type,
        'total_cases': g.total_cases,
        'total_amount_involved': g.total_amount,
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
        'created_at': g.created_at.isoformat() if g.created_at else None
    }


VALID_STATUS_TRANSITIONS = {
    '待分析': ['已分析'],
    '已分析': ['已立案'],
    '已立案': ['侦办中'],
    '侦办中': ['已结案'],
    '已结案': [],
}


def update_case_status(case_id, new_status):
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
    db.session.commit()
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