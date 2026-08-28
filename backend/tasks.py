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

from database import db, init_db
from celery_app import celery_app
from celery import Task


# ---------- 初始化 SQLAlchemy 2.0（去除 Flask 依赖，消除 P0 架构异味） ----------
init_db()


@celery_app.task(bind=True, name='tasks.run_analysis_task')
def run_analysis_task(self, messages, session_id, accounts_tx=None):
    """Full analysis pipeline using OrchestratorAgent."""
    try:
        from agents.orchestrator import OrchestratorAgent

        self.update_state(state='PROGRESS', meta={
            'stage': 'init',
            'progress': 0,
            'message': '初始化分析引擎'
        })

        # 初始化 OrchestratorAgent
        orchestrator = OrchestratorAgent()

        self.update_state(state='PROGRESS', meta={
            'stage': 'analysis',
            'progress': 5,
            'message': '开始智能研判'
        })

        # 将消息格式转换为案件列表
        cases = []
        for msg in messages:
            if isinstance(msg, dict):
                cases.append(msg)
            elif isinstance(msg, str):
                # 如果是字符串，尝试解析或创建基本案件结构
                cases.append({
                    "description": msg,
                    "case_id": f"case_{len(cases)}"
                })

        result = orchestrator.process(cases, context={"accounts_tx": accounts_tx, "session_id": session_id})

        # 与同步路由（routes/system.py）对齐：研判产出的团伙/冻卡决策必须落库，
        # 否则 Celery 模式下前端 overview 查不到团伙与案件关联（M4）。
        try:
            from database.crud import persist_freeze_decisions, save_gang, _cache_clear
            _sid = result.get('session_id', session_id)
            persist_freeze_decisions(result.get('gangs', []) or [], session_id=_sid)
            _saved = 0
            for g in (result.get('gangs', []) or []):
                g.setdefault('relation_type', 'gnn_cluster')
                try:
                    save_gang(g, session_id=_sid)
                    _saved += 1
                except Exception as _ge:
                    print(f"团伙 {g.get('gang_id')} 关联落库失败: {_ge}")
            if _saved:
                _cache_clear()
        except Exception as _e:
            print(f"Celery 研判落库失败(不影响返回): {_e}")

        self.update_state(state='PROGRESS', meta={
            'stage': 'complete',
            'progress': 100,
            'message': '分析完成'
        })

        # REQ-S7 失败边界诚实提示：透传 abnormal / 低质量分派生 warnings + 四单流转 slips
        try:
            from agents.schemas import build_warnings
            warnings = build_warnings(result)
        except Exception:
            warnings = []

        return {
            'success': result.get('status') == 'completed',
            'total_cases': result.get('statistics', {}).get('total_cases', 0),
            'total_gangs': len(result.get('gangs', [])),
            'session_id': result.get('session_id', session_id),
            'raw_cases': result.get('cases', []),
            'gangs': result.get('gangs', []),
            'cluster_quality': {
                'quality_score': result.get('statistics', {}).get('quality_score', 0)
            },
            'processing_info': {
                'processing_time': result.get('statistics', {}).get('processing_time', 0)
            },
            'slips': result.get('slips', {}),
            'abnormal': result.get('abnormal', 'none'),
            'abnormal_detail': result.get('abnormal_detail'),
            'warnings': warnings,
            'error': result.get('error'),
            'message': '分析完成' if result.get('status') == 'completed' else '分析失败'
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


@celery_app.task(bind=True, name='tasks.import_csv_task')
def import_csv_task(self, filepath):
    """Import cases from CSV file."""
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


@celery_app.task(bind=True, name='tasks.import_excel_task')
def import_excel_task(self, filepath):
    """Import cases from Excel file."""
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


@celery_app.task(bind=True, name='tasks.suggest_merges_task')
def suggest_merges_task(self):
    """Run merge suggestions on all cases."""
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