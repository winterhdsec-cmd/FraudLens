"""
FastAPI application for FraudLens.
Replaces the original Flask app.py with a modern ASGI architecture.
"""
import os
import sys
import json
import time
import uuid
import asyncio
import traceback
import threading
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from flask import Flask as _Flask
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'key.env')
load_dotenv(dotenv_path)

from database import db, init_db
from tools.response import logger

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "20051223")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
DB_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

_flask_app = _Flask(__name__)
_flask_app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
_flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(_flask_app)
_flask_app.app_context().push()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI) 启动")
    logger.info("=" * 60)
    from database.models import User
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', display_name='系统管理员', role='admin', department='反诈中心')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logger.info("默认管理员账号已创建 (admin/admin123)")
    try:
        from tools.engine import engine as _engine
        global fraud_engine
        fraud_engine = _engine
        logger.info("反诈引擎初始化成功")
    except Exception as e:
        logger.error(f"反诈引擎初始化失败: {e}")
        fraud_engine = None
    logger.info(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info("=" * 60)

    try:
        from database.models import AlertRecord
        if AlertRecord.query.count() == 0:
            now = datetime.utcnow()
            demo_alerts_data = [
                ('phone_match', 'FC20260519001', 'FC20260519002', ['138****1234', '139****5678'], 0.85),
                ('bank_match', 'FC20260519007', 'FC20260519003', ['6222****1234'], 0.72),
                ('phone_match', 'FC20260519008', 'FC20260519009', ['150****9012'], 0.68),
                ('app_match', 'FC20260519010', 'FC20260519011', ['腾讯会议', '瞩目'], 0.91),
                ('ip_match', 'FC20260519014', 'FC20260519015', ['192.168.1.*'], 0.63),
                ('bank_match', 'FC20260519019', 'FC20260519020', ['6217****5678', '6228****9012'], 0.78),
                ('phone_match', 'FC20260519022', 'FC20260519023', ['137****7890'], 0.71),
                ('app_match', 'FC20260519004', 'FC20260519005', ['腾讯会议'], 0.80),
            ]
            for at, cid, mcid, entities, conf in demo_alerts_data:
                record = AlertRecord(
                    alert_type=at, case_id=cid, matched_case_id=mcid,
                    matched_entities=entities, confidence=conf, created_at=now
                )
                db.session.add(record)
            db.session.commit()
            logger.info(f"演示预警数据已注入: {len(demo_alerts_data)} 条")
        else:
            logger.info(f"预警数据已存在: {AlertRecord.query.count()} 条")
    except Exception as e:
        logger.warning(f"预警数据注入跳过: {e}")

    try:
        import random
        from database.models import Case as _Case
        _all_cases = _Case.query.all()
        if CapitalFlow.query.count() <= 2:
            for i in range(min(8, len(_all_cases))):
                c = _all_cases[i]
                flow = CapitalFlow(case_id=c.case_id,
                    source_account=f"6222{random.randint(100000,999999)}",
                    target_account=f"6217{random.randint(100000,999999)}",
                    bank_name=random.choice(["工商银行","建设银行","农业银行"]),
                    amount=round(random.uniform(5000, 150000), 2),
                    direction='out' if i % 3 != 0 else 'in', level=random.randint(1, 3))
                db.session.add(flow)
            logger.info("资金流向数据已注入")
        if DispatchOrder.query.count() <= 1:
            for i in range(min(6, len(_all_cases))):
                d = DispatchOrder(case_id=_all_cases[i].case_id,
                    assigned_dept=random.choice(["刑侦大队","网安大队","辖区派出所","反诈中心"]),
                    status=random.choice(["pending","signed","completed"]))
                db.session.add(d)
            logger.info("派单数据已注入")
        if KeyPerson.query.count() <= 1:
            for i in range(8):
                p = KeyPerson(name=["刘某","张某","王某","李某","赵某","陈某","周某","吴某"][i],
                    id_number=f"420{random.randint(100000,999999)}",
                    phone=f"138{random.randint(10000000,99999999)}",
                    person_type=random.choice(["前科人员","高危人员","涉诈重点人"]),
                    risk_level=random.choice(["S","A","B"]),
                    bank_account=f"6222{random.randint(100000,999999)}")
                db.session.add(p)
            db.session.commit()
            logger.info("重点人员数据已注入")
    except Exception as e:
        logger.warning(f"P1演示数据注入跳过: {e}")

    try:
        from database.models import Gang, GangCaseRelation
        existing_gang_case = set(r.case_id for r in GangCaseRelation.query.all())
        orphan_cases = [c for c in _all_cases if c.case_id not in existing_gang_case]
        if orphan_cases:
            created = 0
            name_counters = {}
            for c in orphan_cases:
                base = c.scam_type or '未知类型'
                name_counters[base] = name_counters.get(base, 0) + 1
                victim_name = c.victim_name or c.title or ''
                unique_name = f'{base}案{name_counters[base]}-{victim_name[:6]}' if victim_name else f'{base}案{name_counters[base]}'
                solo_gang = Gang(
                    gang_id=f'SOLO_{c.case_id}',
                    gang_name=unique_name,
                    risk_level=c.risk_level or 'C',
                    risk_label={'HIGH': '高风险', 'MEDIUM': '中风险', 'LOW': '低风险', 'UNKNOWN': '未知'}.get(c.risk_level, '低风险'),
                    risk_type={'HIGH': 'danger', 'MEDIUM': 'warning', 'LOW': 'info', 'UNKNOWN': 'info'}.get(c.risk_level, 'info'),
                    threat_level={'HIGH': 'S', 'MEDIUM': 'A', 'LOW': 'B', 'UNKNOWN': 'C'}.get(c.risk_level, 'C'),
                    comprehensive_score=c.risk_score or 0,
                    total_cases=1,
                    total_amount=c.amount or '0',
                    total_amount_value=float(c.amount_value or 0),
                    fingerprint=[c.scam_type or '未知类型', '独立案件'],
                    description=f'基于{c.scam_type or "未知"}诈骗手法识别的独立案件',
                )
                db.session.add(solo_gang)
                db.session.flush()
                rel = GangCaseRelation(gang_id=solo_gang.gang_id, case_id=c.case_id, similarity=1.0)
                db.session.add(rel)
                created += 1
            db.session.commit()
            logger.info(f"独立团伙创建完成: {created} 个")
    except Exception as e:
        logger.warning(f"独立团伙创建跳过: {e}")
        db.session.rollback()

    yield
    logger.info("服务关闭")


app = FastAPI(title="FraudLens AI 反诈研判官系统", version="3.0", lifespan=lifespan)

from database.p1_routes import router as p1_router
app.include_router(p1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "type": type(exc).__name__}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

from routes.auth import router as auth_router
from routes.cases import router as cases_router
from routes.gangs import router as gangs_router
from routes.sessions import router as sessions_router
from routes.alerts import router as alerts_router
from routes.dashboard import router as dashboard_router
from routes.searches import router as searches_router
from routes.reports import router as reports_router
from routes.merges import router as merges_router
from routes.files import router as files_router
from routes.system import router as system_router

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(gangs_router)
app.include_router(sessions_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)
app.include_router(searches_router)
app.include_router(reports_router)
app.include_router(merges_router)
app.include_router(files_router)
app.include_router(system_router)

if __name__ == '__main__':
    import uvicorn
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI)")
    logger.info("=" * 60)
    logger.info("   POST /agent-analyze   (智能研判分析)")
    logger.info("   GET  /health          (健康检查)")
    logger.info("   GET  /api/cases       (案件列表)")
    logger.info("   WS   /ws/{session_id} (实时进度)")
    logger.info("=" * 60)
    uvicorn.run(app, host='0.0.0.0', port=5003)