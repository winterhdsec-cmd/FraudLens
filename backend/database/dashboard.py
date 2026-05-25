import json
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from . import db
from .models import Case, Gang, AnalysisSession

RISK_LEVEL_COLORS = {
    'HIGH': '#ef4444', 'MEDIUM': '#f59e0b', 'LOW': '#00d4ff',
    'CRITICAL': '#7f1d1d', 'UNKNOWN': '#64748b',
    'S': '#ef4444', 'A': '#f59e0b', 'B': '#8b5cf6', 'C': '#10b981'
}
RISK_LEVEL_LABELS = {
    'HIGH': '\u9ad8\u98ce\u9669', 'MEDIUM': '\u4e2d\u98ce\u9669', 'LOW': '\u4f4e\u98ce\u9669',
    'CRITICAL': '\u6781\u9ad8\u98ce\u9669', 'UNKNOWN': '\u672a\u77e5',
    'S': 'S\u7ea7', 'A': 'A\u7ea7', 'B': 'B\u7ea7', 'C': 'C\u7ea7'
}
STATUS_COLORS = {
    '\u5f85\u5206\u6790': '#64748b', '\u5df2\u5206\u6790': '#8b5cf6',
    '\u5df2\u7acb\u6848': '#f59e0b', '\u4fa6\u529e\u4e2d': '#00d4ff',
    '\u5df2\u7ed3\u6848': '#10b981', '\u5df2\u5220\u9664': '#64748b'
}
SCAM_TYPE_COLORS = ['#ef4444', '#f59e0b', '#8b5cf6', '#00d4ff', '#10b981', '#ec4899', '#14b8a6', '#f97316', '#6366f1']


def _format_amount(value):
    if value >= 10000:
        return f'\u00a5{round(value/10000, 1)}\u4e07'
    return f'\u00a5{round(value, 2)}'


_memory_cache = {}
_memory_cache_ttl = 300

def _get_cached(key):
    cached = _memory_cache.get(key)
    if cached and (datetime.utcnow() - cached['ts']).seconds < _memory_cache_ttl:
        return cached['data']
    return None

def _set_cache(key, data):
    _memory_cache[key] = {'data': data, 'ts': datetime.utcnow()}
    if len(_memory_cache) > 20:
        cutoff = datetime.utcnow() - timedelta(seconds=_memory_cache_ttl)
        _memory_cache.clear()


def get_dashboard_data():
    cached = _get_cached('dashboard_stats')
    if cached:
        return cached

    try:
        import redis as redis_lib
        r = redis_lib.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', ''),
            socket_connect_timeout=2
        )
        cached_redis = r.get('dashboard_stats')
        if cached_redis:
            data = json.loads(cached_redis)
            _set_cache('dashboard_stats', data)
            return data
    except Exception:
        pass

    total_cases = Case.query.count()
    total_gangs = Gang.query.count()

    total_amount = db.session.query(func.sum(Case.amount_value)).scalar() or 0.0
    total_amount_formatted = _format_amount(total_amount)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cases = Case.query.filter(Case.created_at >= today_start).count()

    last_month_start = datetime.utcnow() - timedelta(days=30)
    last_month_cases = Case.query.filter(Case.created_at >= last_month_start).count()

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

    risk_distribution_array = [
        {
            'name': k,
            'label': RISK_LEVEL_LABELS.get(k, k),
            'value': v,
            'itemStyle': {'color': RISK_LEVEL_COLORS.get(k, '#64748b')}
        }
        for k, v in risk_distribution.items() if v > 0
    ]

    status_rows = db.session.query(
        Case.status, func.count(Case.id)
    ).group_by(Case.status).all()
    status_distribution = {r[0]: r[1] for r in status_rows}

    status_distribution_array = [
        {
            'name': k,
            'value': v,
            'itemStyle': {'color': STATUS_COLORS.get(k, '#64748b')}
        }
        for k, v in status_distribution.items() if v > 0
    ]

    scam_type_rows = db.session.query(
        Case.scam_type,
        func.count(Case.id),
        func.sum(Case.amount_value)
    ).filter(Case.scam_type != '').group_by(Case.scam_type).order_by(
        func.count(Case.id).desc()
    ).limit(10).all()
    top_scam_types = [
        {
            'name': r[0], 'count': r[1], 'amount': round(r[2] or 0.0, 2),
            'color': SCAM_TYPE_COLORS[i % len(SCAM_TYPE_COLORS)]
        }
        for i, r in enumerate(scam_type_rows)
    ]

    six_months_ago = datetime.utcnow() - timedelta(days=180)
    trend_rows = db.session.query(
        func.concat(func.year(Case.created_at), '-', func.lpad(func.month(Case.created_at), 2, '0')).label('month'),
        func.count(Case.id),
        func.sum(Case.amount_value)
    ).filter(Case.created_at >= six_months_ago).group_by(
        func.concat(func.year(Case.created_at), '-', func.lpad(func.month(Case.created_at), 2, '0'))
    ).order_by('month').all()

    trend_data = {
        'dates': [r[0] for r in trend_rows],
        'counts': [r[1] for r in trend_rows],
        'amounts': [round(r[2] or 0.0, 2) for r in trend_rows]
    }

    monthly_trend = []
    for i, date in enumerate(trend_data['dates']):
        month_label = date[5:] if len(date) >= 7 else date
        monthly_trend.append({
            'month': month_label,
            'cases': trend_data['counts'][i],
            'amount': trend_data['amounts'][i]
        })

    threat_rows = db.session.query(
        Gang.threat_level, func.count(Gang.id)
    ).group_by(Gang.threat_level).all()
    gang_threat_distribution = {r[0]: r[1] for r in threat_rows}
    for level in ['S', 'A', 'B', 'C']:
        gang_threat_distribution.setdefault(level, 0)

    gang_threat_array = [
        {
            'name': k, 'label': RISK_LEVEL_LABELS.get(k, k),
            'value': v,
            'itemStyle': {'color': RISK_LEVEL_COLORS.get(k, '#64748b')}
        }
        for k, v in gang_threat_distribution.items() if v > 0
    ]

    recent_cases_query = Case.query.order_by(Case.created_at.desc()).limit(5).all()
    recent_cases = []
    for c in recent_cases_query:
        recent_cases.append({
            'case_id': c.case_id,
            'id': c.case_id,
            'title': c.title,
            'victim': c.victim_name,
            'victimName': c.victim_name,
            'scam_type': c.scam_type,
            'type': c.scam_type,
            'amount': c.amount,
            'amount_value': c.amount_value,
            'risk_level': c.risk_level,
            'status': c.status,
            'date': c.created_at.isoformat()[:10] if c.created_at else None,
            'created_at': c.created_at.isoformat() if c.created_at else None
        })

    is_empty = total_cases == 0

    if is_empty:
        risk_distribution_array = []
        status_distribution_array = []
        top_scam_types = []
        monthly_trend = []
        trend_data = {'dates': [], 'counts': [], 'amounts': []}
        recent_cases = []
        gang_threat_array = []

    data = {
        'total_cases': total_cases,
        'total_gangs': total_gangs,
        'total_amount': round(total_amount, 2),
        'total_amount_formatted': total_amount_formatted,
        'today_cases': today_cases,
        'last_month_cases': last_month_cases,
        'active_alerts': active_alerts,
        'risk_distribution': risk_distribution_array,
        'risk_distribution_raw': risk_distribution,
        'status_distribution': status_distribution_array,
        'status_distribution_raw': status_distribution,
        'top_scam_types': top_scam_types,
        'trend_data': trend_data,
        'monthly_trend': monthly_trend,
        'gang_threat_distribution': gang_threat_array,
        'gang_threat_raw': gang_threat_distribution,
        'recent_cases': recent_cases,
        'is_empty': is_empty,
        'empty_message': '\u6682\u65e0\u6848\u4ef6\u6570\u636e\uff0c\u8bf7\u5148\u8fdb\u884c\u667a\u80fd\u7814\u5224' if is_empty else '',
        'data_updated_at': datetime.utcnow().isoformat(),
        'data_source': '基于历史警情数据生成（演示数据）',
        'data_update_frequency': '每日自动更新'
    }

    _set_cache('dashboard_stats', data)
    try:
        import redis as redis_lib
        r2 = redis_lib.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', ''),
            socket_connect_timeout=2
        )
        r2.setex('dashboard_stats', 300, json.dumps(data, default=str, ensure_ascii=False))
        r2.close()
    except Exception:
        pass

    return data