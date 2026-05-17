from datetime import datetime, timedelta
from sqlalchemy import func
from . import db
from .models import Case, Gang, AnalysisSession


def get_dashboard_data():
    total_cases = Case.query.count()
    total_gangs = Gang.query.count()

    total_amount = db.session.query(func.sum(Case.amount_value)).scalar() or 0.0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cases = Case.query.filter(Case.created_at >= today_start).count()

    active_alerts = 0
    try:
        from .alert import _alerts
        active_alerts = sum(1 for a in _alerts if not a.resolved)
    except ImportError:
        pass

    risk_rows = db.session.query(
        Case.risk_level, func.count(Case.id)
    ).group_by(Case.risk_level).all()
    risk_distribution = {r[0]: r[1] for r in risk_rows}
    for level in ['HIGH', 'MEDIUM', 'LOW']:
        risk_distribution.setdefault(level, 0)

    status_rows = db.session.query(
        Case.status, func.count(Case.id)
    ).group_by(Case.status).all()
    status_distribution = {r[0]: r[1] for r in status_rows}

    scam_type_rows = db.session.query(
        Case.scam_type,
        func.count(Case.id),
        func.sum(Case.amount_value)
    ).filter(Case.scam_type != '').group_by(Case.scam_type).order_by(
        func.count(Case.id).desc()
    ).limit(10).all()
    top_scam_types = [
        {'name': r[0], 'count': r[1], 'amount': round(r[2] or 0.0, 2)}
        for r in scam_type_rows
    ]

    six_months_ago = datetime.utcnow() - timedelta(days=180)
    trend_rows = db.session.query(
        func.date_format(Case.created_at, '%%Y-%%m').label('month'),
        func.count(Case.id),
        func.sum(Case.amount_value)
    ).filter(Case.created_at >= six_months_ago).group_by(
        func.date_format(Case.created_at, '%%Y-%%m')
    ).order_by('month').all()

    trend_data = {
        'dates': [r[0] for r in trend_rows],
        'counts': [r[1] for r in trend_rows],
        'amounts': [round(r[2] or 0.0, 2) for r in trend_rows]
    }

    threat_rows = db.session.query(
        Gang.threat_level, func.count(Gang.id)
    ).group_by(Gang.threat_level).all()
    gang_threat_distribution = {r[0]: r[1] for r in threat_rows}
    for level in ['S', 'A', 'B', 'C']:
        gang_threat_distribution.setdefault(level, 0)

    recent_cases_query = Case.query.order_by(Case.created_at.desc()).limit(5).all()
    recent_cases = []
    for c in recent_cases_query:
        recent_cases.append({
            'case_id': c.case_id,
            'title': c.title,
            'victim': c.victim_name,
            'scam_type': c.scam_type,
            'amount': c.amount,
            'amount_value': c.amount_value,
            'risk_level': c.risk_level,
            'status': c.status,
            'created_at': c.created_at.isoformat() if c.created_at else None
        })

    return {
        'total_cases': total_cases,
        'total_gangs': total_gangs,
        'total_amount': round(total_amount, 2),
        'today_cases': today_cases,
        'active_alerts': active_alerts,
        'risk_distribution': risk_distribution,
        'status_distribution': status_distribution,
        'top_scam_types': top_scam_types,
        'trend_data': trend_data,
        'gang_threat_distribution': gang_threat_distribution,
        'recent_cases': recent_cases
    }