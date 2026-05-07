from .base import BaseAgent, AgentConfig, AgentContext, TimeoutError
import json
import re
from typing import Dict, Any, List


class TriageAgent(BaseAgent):
    """分案策略智能体"""

    def __init__(self, config: AgentConfig, llm_triage):
        super().__init__(config)
        self.llm_triage = llm_triage

    CONFIDENCE_THRESHOLD = 0.6  # 人工复核阈值

    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        智能分案处理
        """
        self._log("INFO", "开始智能分案", context)
        
        text_messages = payload.get('text_messages', [])
        total_len = len(text_messages)
        confidence = 0.9  # 默认高置信度
        is_truncated = False
        
        if total_len < 5:
            self._log("INFO", "消息数量不足，直接返回单个案件", context)
            return {
                "splits": [{"case_id": 1, "start": 0, "end": total_len - 1}],
                "is_triage_failed": False,
                "confidence": 0.9,
                "pending_manual_review": False
            }

        MAX_CONTEXT = 200
        if total_len > MAX_CONTEXT:
            sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages[:MAX_CONTEXT])])
            is_truncated = True
        else:
            sample_text = "\n".join([f"[{i}] {msg}" for i, msg in enumerate(text_messages)])
            is_truncated = False

        prompt = f"""
        # Role
        你是一名拥有 10 年经验的反诈中心情报分析师。任务是对混杂聊天记录进行"案件串并"分析。

        # Input Data
        以下是按时间顺序排列的聊天记录片段：
        {sample_text}
        {'(注：数据已被截断，仅展示前 200 条)' if is_truncated else ''}

        # Core Rules
        1. **必须切割**：完全不同的诈骗剧本、不同的受害人身份、时间断层>7 天且无延续。
        2. **必须合并**：同一剧本的自然演变、同一资金流的追索。
        3. **输出格式**：仅输出一个标准的 JSON 数组，包含 case_id, start, end, reason。不要有任何 Markdown 标记。

        # Output Example
        [{"case_id": 1, "start": 0, "end": 45, "reason": "刷单返利诱导期"}, {"case_id": 2, "start": 46, "end": 98, "reason": "转为冒充公检法恐吓"}]

        # Action
        请分析上述数据，输出 JSON 数组：
        """

        try:
            if not self.llm_triage:
                raise Exception("LLM 未初始化")
            
            self._log("INFO", "调用LLM进行智能分案", context)
            response = self.llm_triage.invoke(prompt)
            raw_text = response.strip()
            clean_text = re.sub(r'```json\s*|```\s*', '', raw_text)
            json_obj = None

            try:
                json_obj = json.loads(clean_text)
            except json.JSONDecodeError:
                match = re.search(r'\[.*\]', clean_text, re.DOTALL)
                if match:
                    try:
                        json_obj = json.loads(match.group())
                    except:
                        pass

            if not json_obj or not isinstance(json_obj, list):
                raise ValueError("AI 返回的数据不是合法的 JSON 数组")

            splits = []
            for i, item in enumerate(json_obj):
                start = int(item.get('start', 0))
                end = int(item.get('end', 0))
                if start < 0: start = 0
                if end >= total_len: end = total_len - 1
                if start > end: start, end = end, start
                splits.append({"case_id": i + 1, "start": start, "end": end, "reason": item.get('reason', '自动分案')})

            if not splits:
                raise ValueError("AI 返回了空列表")

            splits.sort(key=lambda x: x['start'])
            has_boundary_correction = False
            
            if splits[0]['start'] != 0:
                splits[0]['start'] = 0
                has_boundary_correction = True

            for i in range(len(splits) - 1):
                if splits[i]['end'] + 1 < splits[i + 1]['start']:
                    splits[i]['end'] = splits[i + 1]['start'] - 1
                    has_boundary_correction = True

            if splits[-1]['end'] < total_len - 1:
                splits[-1]['end'] = total_len - 1
                has_boundary_correction = True

            # 计算置信度
            if is_truncated or has_boundary_correction:
                confidence = 0.6  # 有截断或边界修正，置信度降低
            else:
                confidence = 0.9  # 解析顺利且无修正
            
            # 判断是否需要人工复核
            pending_manual_review = confidence < self.CONFIDENCE_THRESHOLD
            
            if pending_manual_review:
                self._log("WARN", f"分案置信度低({confidence:.2f})，建议人工复核", context)

            self._log("INFO", f"分案成功：识别出 {len(splits)} 个案件，置信度={confidence:.2f}", context)
            return {
                "splits": splits,
                "is_triage_failed": False,
                "confidence": confidence,
                "pending_manual_review": pending_manual_review
            }

        except Exception as e:
            self._log("ERROR", f"AI 分案失败：{e}", context)
            # 完全回退，置信度最低
            confidence = 0.3
            pending_manual_review = True
            self._log("WARN", f"分案完全回退，置信度={confidence:.2f}，建议人工复核", context)
            return {
                "splits": [{"case_id": 1, "start": 0, "end": total_len - 1}],
                "is_triage_failed": True,
                "confidence": confidence,
                "pending_manual_review": pending_manual_review
            }
