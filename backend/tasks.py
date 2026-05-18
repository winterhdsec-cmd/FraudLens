"""
Celery tasks for FraudLens.
"""
import asyncio
import os
import sys
import time
import json

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'key.env'))

from celery_app import celery_app
from celery import Task


def _init_task_db():
    """Initialize database context for Celery workers."""
    from flask import Flask
    from database import db, init_db

    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "20051223")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "fraudlens")

    flask_app = Flask(__name__)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_db(flask_app)
    ctx = flask_app.app_context()
    ctx.push()
    return flask_app, ctx


@celery_app.task(bind=True, name='tasks.run_analysis_task')
def run_analysis_task(self, messages, session_id):
    """Full analysis pipeline using ChiefAgent."""
    flask_app, ctx = _init_task_db()
    try:
        import uuid
        from agents.chief_agent import ChiefAgent
        from agents.base import AgentConfig, AgentContext

        api_key = os.getenv("DASHSCOPE_API_KEY", "mock-key")
        LLM_REQUEST_TIMEOUT = 30

        try:
            from langchain_community.llms import Tongyi
            from agents.llm_wrapper import wrap_llm
            raw_analyze = Tongyi(
                model_name="qwen-turbo",
                temperature=0.1,
                request_timeout=LLM_REQUEST_TIMEOUT
            )
            raw_triage = Tongyi(
                model_name="qwen-turbo",
                temperature=0.1,
                request_timeout=LLM_REQUEST_TIMEOUT
            )
            llm_analyze = wrap_llm(raw_analyze, max_concurrent=3)
            llm_triage = wrap_llm(raw_triage, max_concurrent=3)
        except ImportError:
            llm_analyze = None
            llm_triage = None

        self.update_state(state='PROGRESS', meta={
            'stage': 'init',
            'progress': 0,
            'message': '初始化分析引擎'
        })

        progress_updates = []

        class TaskProgressAdapter:
            def __init__(self, task, sid):
                self.task = task
                self.session_id = sid

            def emit(self, event, data, room=None):
                nonlocal progress_updates
                progress_data = {
                    'event': event,
                    'data': data,
                    'ts': time.time()
                }
                progress_updates.append(progress_data)
                try:
                    import redis
                    r = redis.Redis(host='localhost', port=6379, db=0)
                    r.publish(f'progress:{self.session_id}', json.dumps(progress_data, default=str))
                    r.close()
                except Exception:
                    pass
                try:
                    stage = data.get('stage', 'unknown')
                    progress_percent = data.get('progress_percent', 0)
                    message = data.get('message', '')
                    self.task.update_state(state='PROGRESS', meta={
                        'stage': stage,
                        'progress': progress_percent,
                        'message': message
                    })
                except Exception:
                    pass

        chief_agent = ChiefAgent(
            AgentConfig(agent_id="ChiefAgent"),
            llm_analyze,
            llm_triage,
            socketio=TaskProgressAdapter(self, session_id),
            session_id=session_id,
            persist=True
        )

        context = AgentContext(
            session_id=session_id,
            trace_id=str(uuid.uuid4())
        )

        self.update_state(state='PROGRESS', meta={
            'stage': 'analysis',
            'progress': 5,
            'message': '开始智能研判'
        })

        result = chief_agent.process({
            'messages': messages,
            'platform_data': {}
        }, context)

        self.update_state(state='PROGRESS', meta={
            'stage': 'complete',
            'progress': 100,
            'message': '分析完成'
        })

        return {
            'success': result.get('success', False),
            'total_cases': result.get('total_cases', 0),
            'total_gangs': len(result.get('gangs', [])),
            'session_id': session_id,
            'raw_cases': result.get('raw_cases', []),
            'gangs': result.get('gangs', []),
            'cluster_quality': result.get('cluster_quality', {}),
            'processing_info': result.get('processing_info', {}),
            'warnings': result.get('warnings', []),
            'error': result.get('error'),
            'message': result.get('message', '')
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        self.update_state(state='FAILURE', meta={
            'error': str(e)
        })
        return {
            'success': False,
            'error': str(e),
            'session_id': session_id
        }
    finally:
        ctx.pop()


@celery_app.task(bind=True, name='tasks.import_csv_task')
def import_csv_task(self, filepath):
    """Import cases from CSV file."""
    flask_app, ctx = _init_task_db()
    try:
        from database.importer import import_from_csv

        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': '开始导入CSV文件'
        })

        result = import_from_csv(filepath)

        self.update_state(state='PROGRESS', meta={
            'progress': 100,
            'message': 'CSV导入完成'
        })

        return {
            'success': True,
            'total_imported': result.get('total_imported', 0),
            'errors': result.get('errors', []),
            'total_amount': result.get('total_amount', 0.0)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        ctx.pop()


@celery_app.task(bind=True, name='tasks.import_excel_task')
def import_excel_task(self, filepath):
    """Import cases from Excel file."""
    flask_app, ctx = _init_task_db()
    try:
        from database.importer import import_from_excel

        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': '开始导入Excel文件'
        })

        result = import_from_excel(filepath)

        self.update_state(state='PROGRESS', meta={
            'progress': 100,
            'message': 'Excel导入完成'
        })

        return {
            'success': True,
            'total_imported': result.get('total_imported', 0),
            'errors': result.get('errors', []),
            'total_amount': result.get('total_amount', 0.0)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        ctx.pop()


@celery_app.task(bind=True, name='tasks.suggest_merges_task')
def suggest_merges_task(self):
    """Run merge suggestions on all cases."""
    flask_app, ctx = _init_task_db()
    try:
        from database.merge import suggest_merges
        from database.crud import get_all_cases

        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': '获取所有案件数据'
        })

        cases = get_all_cases()
        self.update_state(state='PROGRESS', meta={
            'progress': 50,
            'message': f'正在分析 {len(cases)} 个案件的合并建议'
        })

        suggestions = suggest_merges(cases)

        self.update_state(state='PROGRESS', meta={
            'progress': 100,
            'message': f'合并建议生成完成，共 {len(suggestions)} 条'
        })

        return {
            'success': True,
            'total_suggestions': len(suggestions),
            'suggestions': [{
                'id': s.id,
                'case_id_a': s.case_id_a,
                'case_id_b': s.case_id_b,
                'similarity': s.similarity,
                'reason': s.reason
            } for s in suggestions]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        ctx.pop()