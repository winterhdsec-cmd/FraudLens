from .base import BaseAgent, AgentConfig, AgentContext
from .preprocess_agent import PreprocessAgent
from .triage_agent import TriageAgent
from .analyst_agent import AnalystAgent
from .cluster_agent import ClusterAgent
from .profiler_agent import ProfilerAgent
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import time
import uuid
import json
import re
from datetime import datetime
from typing import Dict, Any, List
import sys
import os
from tools.response import logger

# 数据库 CRUD
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.crud import create_session, save_case, save_gang, complete_session


class ChiefAgent(BaseAgent):
    """研判协同智能体（v2 - 支持数据库持久化）"""

    STAGE_PROGRESS = {
        'data_preparation': {'start': 0, 'end': 10, 'name': '数据准备'},
        'case_triage': {'start': 10, 'end': 25, 'name': '智能分案'},
        'case_analysis': {'start': 25, 'end': 75, 'name': '案件分析'},
        'gang_discovery': {'start': 75, 'end': 95, 'name': '团伙发现'},
        'profile_enhancement': {'start': 95, 'end': 100, 'name': '画像增强'}
    }

    def __init__(self, config: AgentConfig, llm_analyze, llm_triage, socketio=None, session_id=None, persist=True):
        super().__init__(config)
        self.llm_analyze = llm_analyze
        self.llm_triage = llm_triage
        self.socketio = socketio
        self.session_id = session_id
        self.persist = persist  # 是否持久化到数据库

        self.agents = {
            'preprocess': PreprocessAgent(AgentConfig(agent_id="PreprocessAgent")),
            'triage': TriageAgent(AgentConfig(agent_id="TriageAgent"), llm_triage),
            'analyst': AnalystAgent(AgentConfig(agent_id="AnalystAgent"), llm_analyze),
            'cluster': ClusterAgent(AgentConfig(agent_id="ClusterAgent"), llm_analyze),
            'profiler': ProfilerAgent(AgentConfig(agent_id="ProfilerAgent"), llm_analyze)
        }

        self.context = {
            'raw_data': None,
            'cleaned_data': None,
            'case_splits': None,
            'analyzed_cases': None,
            'gangs': None,
            'network_data': None,
            'errors': [],
            'warnings': [],
            'processing_start_time': None,
            'current_stage': None,
            'current_trace_id': None
        }

        logger.info("[ChiefAgent] 初始化完成")

    def _emit_progress(self, stage: str, status: str, message: str, context: AgentContext = None):
        """
        通过WebSocket推送进度信息
        """
        if not self.socketio:
            return  # 未传入socketio，静默跳过
        
        stage_config = self.STAGE_PROGRESS.get(stage, {'start': 0, 'end': 100, 'name': stage})
        progress = stage_config['start'] if status == 'running' else stage_config['end']
        
        progress_data = {
            'stage': stage,
            'stage_name': stage_config['name'],
            'status': status,
            'progress': progress / 100,
            'progress_percent': progress,
            'message': message,
            'trace_id': context.trace_id if context else self.context.get('current_trace_id')
        }
        
        try:
            if self.session_id:
                self.socketio.emit('analysis_progress', progress_data, room=self.session_id)
            else:
                self.socketio.emit('analysis_progress', progress_data)
        except Exception as e:
            self._log("ERROR", f"WebSocket推送失败: {e}", context)

    def _update_progress(self, stage: str, status: str, message: str, context: AgentContext):
        """
        更新进度（内部方法）
        """
        self.context['current_stage'] = stage
        self._emit_progress(stage, status, message, context)
        self._log("INFO", f"阶段[{stage}] {status}: {message}", context)

    def simple_process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """简化版研判：直接发送给LLM提取，绕过复杂Agent流水线"""
        self._log("INFO", "开始简化版智能研判(单次LLM调用)", context)
        start_time = time.time()

        raw_text = ''
        for msg in payload.get('messages', []):
            if isinstance(msg, dict):
                raw_text += (msg.get('content', msg.get('text', '')) or '') + '\n'
            elif isinstance(msg, str):
                raw_text += msg + '\n'
        raw_text = raw_text.strip()

        if not raw_text:
            return {"success": False, "error": "没有有效内容", "total_cases": 0, "raw_cases": [], "gangs": []}

        prompt = f"""你是一名反诈情报分析师。请分析以下报案材料，提取所有案件信息并以JSON格式返回。

材料内容：
{raw_text[:6000]}

请严格按照以下JSON结构返回（不要包含markdown代码块标记，直接返回纯JSON）：
{{
  "cases": [
    {{
      "case_id": "如CASE001",
      "title": "案件标题",
      "scam_type": "诈骗类型",
      "description": "案情描述（包含受害人、嫌疑人、作案手法等）",
      "victim_name": "受害人姓名",
      "victim_gender": "性别",
      "victim_age": "年龄数字",
      "victim_phone": "联系电话",
      "victim_job": "职业",
      "victim_address": "户籍地址",
      "amount": "涉案金额如'¥158,000元'或'158,000元'",
      "amount_value": 158000,
      "date": "立案日期",
      "status": "待调查",
      "region": "案发地区",
      "type": "案件类型",
      "scam_phone": "诈骗电话号码",
      "phone_location": "号码归属地",
      "scam_url": "诈骗网址",
      "ip_address": "IP地址",
      "peak_hours": "作案时段",
      "target_group": "目标群体",
      "tools": "作案工具如'电话/Zoom/手机银行'",
      "comm_method": "沟通方式",
      "keywords": ["关键词1", "关键词2"],
      "related_accounts": ["涉案银行账号1", "涉案银行账号2"],
      "timeline": [
        {{"step": "步骤名", "description": "描述", "time": "时间"}}
      ],
      "roles": [
        {{"role": "角色如受害人/一级卡主", "entity": "姓名", "description": "描述"}}
      ],
      "fingerprint": ["特征描述1", "特征描述2"],
      "suggestions": ["处置建议1", "处置建议2"],
      "radar_data": {{
        "诈骗可能性": 95,
        "资金追回难度": 70,
        "团伙组织化程度": 60,
        "作案专业化程度": 80,
        "社会危害性": 75
      }}
    }}
  ],
  "gangs": [
    {{
      "gang_id": "GANG001",
      "gang_name": "团伙名称",
      "script_type": "诈骗剧本类型",
      "description": "团伙描述",
      "case_ids": ["CASE001", "CASE002"],
      "risk_level": "HIGH/MEDIUM/LOW",
      "fingerprint": ["特征1", "特征2"],
      "related_cases": ["CASE001"],
      "member_count": 3,
      "total_amount": "总涉案金额"
    }}
  ],
  "triage_summary": "分案说明"
}}

要求：
1. 如果有多个独立案件（不同受害人、不同诈骗场景），分别提取为多个case
2. **每个case必须归入至少一个gang**。如果多个案件诈骗手法相似或涉及相同嫌疑人，归入同一个gang。如果案件之间无关联，每个case独立成为一个gang。
3. **非常重要：gangs数组不能为空！有多少个case，至少要有多少个gang（一对一或一对多）**
4. 每个案件必须填写 victim_name、scam_type、amount、description、keywords、timeline、roles
5. radar_data 是0-100的评分，必须包含所有5个维度
6. 金额同时提供 amount（带单位的字符串）和 amount_value（纯数字）
7. 从材料中提取具体信息，不要编造

JSON结果："""
        try:
            response = self.llm_analyze.invoke(prompt)
            result_text = response.content if hasattr(response, 'content') else str(response)
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text.strip())
            result_text = re.sub(r'\s*```$', '', result_text)
            parsed = json.loads(result_text)
        except Exception as e:
            self._log("ERROR", f"LLM返回解析失败: {e}", context)
            return {
                "success": False, "error": f"LLM解析失败: {e}",
                "raw_response": result_text if 'result_text' in dir() else '',
                "total_cases": 0, "raw_cases": [], "gangs": []
            }

        cases = parsed.get('cases', [])
        gangs = parsed.get('gangs', [])

        for i, c in enumerate(cases):
            if not c.get('case_id'):
                c['case_id'] = f'CASE{i+1:03d}'
            c['id'] = c['case_id']

        for g in gangs:
            if not g.get('gang_id'):
                g['gang_id'] = f'GANG{gangs.index(g)+1:03d}'
            g['id'] = g['gang_id']
            if 'gang_name' not in g:
                g['gang_name'] = g.get('script_type', '未知团伙')
            if 'fingerprint' not in g or not g['fingerprint']:
                g['fingerprint'] = ['特征分析中']
            if 'related_cases' not in g:
                g['related_cases'] = [c['case_id'] for c in cases if c.get('case_id') in g.get('case_ids', [])]
            risk_level = g.get('risk_level', 'LOW')
            g['risk_label'] = '高风险' if risk_level == 'HIGH' else ('中风险' if risk_level == 'MEDIUM' else '低风险')
            g['risk_type'] = 'danger' if risk_level == 'HIGH' else ('warning' if risk_level == 'MEDIUM' else 'info')

        for c in cases:
            gang_ids = [g['gang_id'] for g in gangs if c['case_id'] in g.get('case_ids', [])]
            c['gang'] = gang_ids[0] if gang_ids else ''

        processing_time_ms = int((time.time() - start_time) * 1000)
        self._log("INFO", f"简化研判完成: {len(cases)}个案件, {len(gangs)}个团伙, 耗时{processing_time_ms}ms", context)

        return {
            "success": True,
            "total_cases": len(cases),
            "triage_status": "success",
            "raw_cases": cases,
            "gangs": gangs,
            "network_data": {"nodes": [], "links": []},
            "processing_info": {
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "processing_time_ms": processing_time_ms,
                "data_version": "2.0-simple",
                "agent_version": "AntiFraudDirectLLM-v1.0",
                "total_stages": 1,
                "errors": [],
                "warnings": []
            },
            "message": "智能研判完成"
        }

    def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        执行完整的智能研判流程
        """
        self._log("INFO", "开始智能研判流程", context)
        self.context['processing_start_time'] = time.time()
        self.context['current_trace_id'] = context.trace_id

        try:
            # ========== 阶段1: 数据准备 ==========
            self._update_progress('data_preparation', 'running', '正在清洗和标准化数据...', context)

            preprocess_result = self.agents['preprocess'].process(payload, context)
            standardized_messages = preprocess_result.get('standardized_messages', [])
            text_messages = preprocess_result.get('text_messages', [])

            self.context['cleaned_data'] = standardized_messages
            self.context['raw_data'] = payload

            if not standardized_messages:
                raise ValueError("数据清洗后无有效内容")

            self._update_progress('data_preparation', 'completed', f'数据清洗完成，共处理{len(standardized_messages)}条消息', context)

            # ========== 阶段2: 智能分案 ==========
            self._update_progress('case_triage', 'running', '正在进行智能分案...', context)

            triage_result = self.agents['triage'].process({
                'text_messages': text_messages
            }, context)
            splits = triage_result.get('splits', [])
            is_triage_failed = triage_result.get('is_triage_failed', False)
            confidence = triage_result.get('confidence', 0.0)
            pending_manual_review = triage_result.get('pending_manual_review', False)

            if is_triage_failed:
                self.context['warnings'].append("案件智能分割置信度较低，可能影响后续分析")
                for s in splits:
                    s['is_failed'] = True
            
            if pending_manual_review:
                self.context['warnings'].append(f"分案置信度({confidence:.2f})低于阈值，建议人工复核")

            self.context['case_splits'] = splits

            if not splits:
                raise ValueError("案件分割失败，未识别出任何案件")

            self._update_progress('case_triage', 'completed', f'智能分案完成，识别出{len(splits)}个案件', context)

            # ========== 阶段3: 并行案件深度分析 ==========
            self._update_progress('case_analysis', 'running', f'正在并行分析{len(splits)}个案件...', context)

            all_results = self._process_cases_in_parallel(splits, text_messages, context)
            all_results.sort(key=lambda x: x.get('case_id', 9999))
            self.context['analyzed_cases'] = all_results

            if not all_results:
                raise ValueError("所有案件分析均失败")

            self._update_progress('case_analysis', 'completed', f'案件分析完成，共分析{len(all_results)}个案件', context)

            # ========== 阶段4: 智能团伙发现 ==========
            self._update_progress('gang_discovery', 'running', '正在进行团伙聚类分析...', context)

            cluster_result = self.agents['cluster'].process({
                'cases': all_results
            }, context)
            gangs = cluster_result.get('gangs', [])
            self.context['gangs'] = gangs

            self._update_progress('gang_discovery', 'completed', f'团伙发现完成，识别出{len(gangs)}个团伙', context)

            # ========== 阶段5: 团伙画像增强 ==========
            self._update_progress('profile_enhancement', 'running', '正在增强团伙画像...', context)

            profiler_result = self.agents['profiler'].process({
                'gangs': gangs
            }, context)
            enhanced_gangs = profiler_result.get('gangs', [])
            self.context['gangs'] = enhanced_gangs

            self._update_progress('profile_enhancement', 'completed', '团伙画像增强完成', context)

            # ========== 阶段6: 生成网络数据 ==========
            self._log("INFO", "阶段6: 生成关联网络数据", context)
            self.context['current_stage'] = 'network_generation'

            network_data = self._generate_network_data(enhanced_gangs)
            self.context['network_data'] = network_data

            # ========== 阶段7: 汇总结果 ==========
            processing_time_ms = int((time.time() - self.context['processing_start_time']) * 1000)

            processing_info = {
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "processing_time_ms": processing_time_ms,
                "data_version": "2.0",
                "agent_version": "AntiFraudChiefAgent-v1.0",
                "total_stages": 7,
                "current_stage": self.context['current_stage'],
                "warnings": self.context['warnings'],
                "errors": self.context['errors']
            }

            # 持久化到数据库
            if self.persist:
                try:
                    self._log("INFO", "正在将分析结果持久化到数据库...", context)
                    from database import db
                    create_session(self.session_id, raw_input=payload.get('messages', []))
                    for case in all_results:
                        save_case(case, session_id=self.session_id)
                    for gang in enhanced_gangs:
                        save_gang(gang, session_id=self.session_id)
                    db.session.commit()
                    complete_session(
                        self.session_id,
                        status='completed',
                        processing_info=processing_info
                    )
                    self._log("INFO", f"数据库持久化完成: {len(all_results)} 个案件, {len(enhanced_gangs)} 个团伙", context)
                except Exception as db_err:
                    self._log("ERROR", f"数据库持久化失败: {db_err}", context)

            # 确保团伙数据格式正确
            for gang in enhanced_gangs:
                # 确保有 gang_name 字段
                if 'gang_name' not in gang:
                    gang['gang_name'] = gang.get('script_type', '未知团伙')

                # 确保有 fingerprint 字段
                if 'fingerprint' not in gang or not gang['fingerprint']:
                    gang['fingerprint'] = ['特征分析中']

                # 确保有 related_cases 字段
                if 'related_cases' not in gang:
                    gang['related_cases'] = []

                # 确保有 risk_label 字段
                if 'risk_label' not in gang:
                    risk_level = gang.get('risk_level', 'LOW')
                    gang['risk_label'] = '高风险' if risk_level == 'HIGH' else (
                        '中风险' if risk_level == 'MEDIUM' else '低风险')

                # 确保有 risk_type 字段
                if 'risk_type' not in gang:
                    risk_level = gang.get('risk_level', 'LOW')
                    gang['risk_type'] = 'danger' if risk_level == 'HIGH' else (
                        'warning' if risk_level == 'MEDIUM' else 'info')

            return {
                "success": True,
                "total_cases": len(all_results),
                "triage_status": "failed" if is_triage_failed else "success",
                "raw_cases": all_results,
                "gangs": enhanced_gangs,
                "network_data": network_data,
                "cluster_quality": cluster_result.get('cluster_quality', {}),
                "processing_info": processing_info,
                "message": "智能研判完成"
            }

        except Exception as e:
            self._log("ERROR", f"研判流程发生致命错误: {e}", context)
            import traceback
            traceback.print_exc()

            processing_time_ms = int((time.time() - self.context.get('processing_start_time', time.time())) * 1000)

            return {
                "success": False,
                "error": str(e),
                "processing_info": {
                    "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    "processing_time_ms": processing_time_ms,
                    "current_stage": self.context.get('current_stage', 'unknown'),
                    "errors": self.context['errors'] + [str(e)]
                },
                "message": "研判流程执行失败"
            }

    def _process_cases_in_parallel(self, splits: List[Dict[str, Any]], text_messages: List[str], context: AgentContext) -> List[Dict[str, Any]]:
        """
        并行处理多个案件
        """
        all_results = []
        MAX_WORKERS = 5
        THREAD_WAIT_TIMEOUT = 35

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_case = {}
            for split in splits:
                future = executor.submit(
                    self._process_single_case,
                    split,
                    text_messages,
                    context
                )
                future_to_case[future] = split

            for future in as_completed(future_to_case, timeout=THREAD_WAIT_TIMEOUT + 10):
                case_info = future_to_case[future]
                case_id = case_info.get('case_id', 'Unknown')
                try:
                    result = future.result(timeout=THREAD_WAIT_TIMEOUT)
                    all_results.append(result)
                    self._log("INFO", f"案件{case_id} 分析完成", context)
                except TimeoutError:
                    error_msg = f"案件{case_id} 分析超时 (>{THREAD_WAIT_TIMEOUT}s)"
                    self.context['errors'].append(error_msg)
                    all_results.append(self._create_fallback_result(case_info, error_msg))
                    self._log("WARNING", error_msg, context)
                except Exception as exc:
                    error_msg = f"案件{case_id} 分析异常: {str(exc)}"
                    self.context['errors'].append(error_msg)
                    all_results.append(self._create_fallback_result(case_info, error_msg))
                    self._log("ERROR", error_msg, context)

        return all_results

    def _process_single_case(self, split: Dict[str, Any], text_messages: List[str], context: AgentContext) -> Dict[str, Any]:
        result = self.agents['analyst'].process({
            'split': split,
            'text_messages': text_messages
        }, context)
        return result

    def _create_fallback_result(self, split, error_msg):
        """
        创建分析失败时的回退结果
        """
        start_idx = split.get('start', 0)
        end_idx = split.get('end', 0)
        return {
            "case_id": split.get('case_id', 'unknown'),
            "message_count": max(0, end_idx - start_idx + 1),
            "time_range": f"{start_idx} - {end_idx}",
            "risk_level": "UNKNOWN",
            "risk_label": "未知",
            "risk_type": "danger",
            "risk_score": 0,
            "scam_type": "系统异常",
            "victim": "未知",
            "amount": "未知",
            "ai_report": f"⚠️ {error_msg}",
            "keywords": ["Timeout", "Error"],
            "steps": [],
            "warning": error_msg,
            "is_error": True,
            "roles": []
        }

    def _generate_network_data(self, gangs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成网络数据
        """
        nodes = []
        links = []

        for gang in gangs:
            # 添加团伙节点
            gang_node = {
                'id': gang['gang_id'],
                'name': gang['gang_name'],
                'type': 'gang',
                'value': self._parse_amount_to_number(gang['total_amount_involved']),
                'risk_level': gang['risk_level'],
                'symbolSize': 50 + min(30, len(gang['related_cases']) * 5)
            }
            nodes.append(gang_node)

            # 添加案件节点和边
            for case in gang['related_cases']:
                case_id = case['case_id']
                case_node = {
                    'id': case_id,
                    'name': f"{case_id}\n{case['victim']}",
                    'type': 'case',
                    'value': self._parse_amount_to_number(case['amount']),
                    'risk_level': case['risk_level'],
                    'symbolSize': 30
                }
                nodes.append(case_node)

                # 添加边
                link = {
                    'source': gang['gang_id'],
                    'target': case_id,
                    'value': self._parse_amount_to_number(case['amount'])
                }
                links.append(link)

        return {'nodes': nodes, 'links': links}

    def _parse_amount_to_number(self, amount_str: str) -> float:
        """
        将金额字符串解析为数值
        """
        if not amount_str or amount_str == '未知金额':
            return 0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            return num
        return 0
