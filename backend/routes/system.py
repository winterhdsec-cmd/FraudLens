"""
System routes: health, logs, network-data, agent-analyze, tasks, WebSocket.
"""
import os
import json
import uuid
import asyncio
import traceback

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

from .deps import (
    logger, USE_CELERY, ProgressAdapter, progress_store, progress_locks,
    AnalyzeRequest
)

router = APIRouter(tags=['系统'])


@router.get('/health')
async def health_check():
    db_ok = False
    try:
        from database.models import Case
        Case.query.first()
        db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy",
        "service": "AI反诈研判官系统",
        "version": "3.0",
        "database": "connected" if db_ok else "disconnected",
        "agent_status": "active",
        "websocket_enabled": True
    }


@router.post('/agent-analyze')
async def api_agent_analyze(data: AnalyzeRequest, request: Request):
    try:
        raw_messages = data.messages
        platform_data = data.platform_data
        session_id = data.session_id or str(uuid.uuid4())
        if not raw_messages and not platform_data:
            raise HTTPException(status_code=400, detail="没有收到消息内容或平台数据")
        if USE_CELERY:
            from tasks import run_analysis_task
            task = run_analysis_task.delay(raw_messages, session_id)
            return {
                "success": True,
                "task_id": task.id,
                "session_id": session_id,
                "message": "分析任务已提交到队列"
            }
        logger.info("=" * 60)
        logger.info("反诈研判官Agent启动智能研判流程 (同步模式)...")
        logger.info(f"会话ID: {session_id}")
        logger.info("=" * 60)
        from agents.chief_agent import ChiefAgent
        from agents.base import AgentConfig, AgentContext
        llm_analyze = None
        llm_triage = None
        try:
            from langchain_community.chat_models import ChatOpenAI
            from agents.llm_wrapper import wrap_llm
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            raw_analyze = ChatOpenAI(model=model, temperature=0.1, request_timeout=120,
                                      api_key=api_key, base_url=base_url)
            raw_triage = ChatOpenAI(model=model, temperature=0.1, request_timeout=120,
                                    api_key=api_key, base_url=base_url)
            llm_analyze = wrap_llm(raw_analyze, max_concurrent=3)
            llm_triage = wrap_llm(raw_triage, max_concurrent=3)
        except ImportError:
            logger.warning("使用模拟模式 (langchain不可用)")
        progress_adapter = ProgressAdapter(session_id)
        progress_adapter.emit('analysis_progress', {
            'stage': 'init', 'stage_name': '初始化', 'status': 'running',
            'progress': 0, 'progress_percent': 0, 'message': '初始化分析引擎'
        })
        chief_agent = ChiefAgent(
            AgentConfig(agent_id="ChiefAgent"),
            llm_analyze, llm_triage,
            socketio=progress_adapter, session_id=session_id, persist=True
        )
        context = AgentContext(session_id=session_id, trace_id=str(uuid.uuid4()))
        result = chief_agent.process({
            'messages': raw_messages, 'platform_data': platform_data
        }, context)
        progress_adapter.emit('analysis_complete', {
            'success': result.get('success'),
            'total_cases': result.get('total_cases', 0),
            'total_gangs': len(result.get('gangs', [])),
            'trace_id': context.trace_id
        })
        logger.info("=" * 60)
        logger.info("智能研判完成！")
        logger.info("=" * 60)
        return result
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/api/tasks/{task_id}')
async def api_get_task(task_id: str):
    try:
        if not USE_CELERY:
            return JSONResponse(status_code=400, content={
                "success": False, "error": "Celery模式未启用"
            })
        from celery.result import AsyncResult
        from celery_app import celery_app
        task_result = AsyncResult(task_id, app=celery_app)
        if task_result.failed():
            return {"success": False, "task_id": task_id, "status": "FAILURE", "error": str(task_result.result)}
        elif task_result.successful():
            return {"success": True, "task_id": task_id, "status": "SUCCESS", "result": task_result.result}
        else:
            meta = task_result.info or {}
            return {"success": True, "task_id": task_id, "status": task_result.state, "meta": meta}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/api/logs')
async def api_public_logs():
    try:
        from database.models import OperationLog
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(50).all()
        return {
            "success": True,
            "logs": [{
                'id': l.id, 'username': l.username, 'action': l.action,
                'target': f"{l.target_type}/{l.target_id}",
                'created_at': l.created_at.isoformat() if l.created_at else None
            } for l in logs]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/api/network-data')
async def api_network_data():
    return {
        "success": True,
        "message": "此接口需要基于会话或数据库实现完整功能",
        "sample_data": {
            "nodes": [
                {"id": "GANG_001", "name": "示例团伙", "type": "gang", "value": 50000},
                {"id": "CASE_001", "name": "示例案件", "type": "case", "value": 15000, "gang_id": "GANG_001"}
            ],
            "links": [
                {"source": "GANG_001", "target": "CASE_001", "value": 15000}
            ]
        }
    }


@router.websocket('/ws/{session_id}')
async def websocket_progress(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})
    last_index = 0
    try:
        if USE_CELERY:
            try:
                import redis as _redis
                r = _redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', '6379')), password=os.getenv('REDIS_PASSWORD', None) or None, db=int(os.getenv('REDIS_DB', '0')))
                pubsub = r.pubsub()
                pubsub.subscribe(f'progress:{session_id}')
                while True:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        data = json.loads(message['data'])
                        await websocket.send_json(data)
                    await asyncio.sleep(0.1)
            except Exception:
                pass
        else:
            while True:
                lock = progress_locks.get(session_id)
                store = progress_store.get(session_id, [])
                new_items = []
                if lock:
                    with lock:
                        if last_index < len(store):
                            new_items = store[last_index:]
                            last_index = len(store)
                else:
                    if last_index < len(store):
                        new_items = store[last_index:]
                        last_index = len(store)
                for item in new_items:
                    try:
                        await websocket.send_json(item)
                    except Exception:
                        pass
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket错误 ({session_id}): {e}")
    finally:
        progress_store.pop(session_id, None)
        progress_locks.pop(session_id, None)