from .base import BaseAgent, AgentConfig, AgentContext
import json
import re
import time
from typing import Dict, Any, List


class ProfilerAgent(BaseAgent):
    """画像生成智能体"""

    def __init__(self, config: AgentConfig, llm_analyze=None):
        super().__init__(config)
        self.llm_analyze = llm_analyze

    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        生成团伙全息画像
        """
        gangs = payload.get('gangs', [])
        self._log("INFO", f"开始为 {len(gangs)} 个团伙生成全息画像", context)

        enhanced_gangs = []
        for gang in gangs:
            enhanced_gang = await self.enhance_gang_profile(gang, context)
            enhanced_gangs.append(enhanced_gang)

        self._log("INFO", "团伙画像生成完成", context)
        return {"gangs": enhanced_gangs}

    async def enhance_gang_profile(self, gang: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        增强团伙画像，添加更多分析维度
        """
        # 确保必要字段存在
        gang = self._ensure_gang_fields(gang)

        # 如果有LLM，使用LLM增强画像
        if self.llm_analyze:
            gang = await self._enhance_with_llm(gang, context)

        # 添加雷达图数据
        gang['radar_data'] = self._generate_radar_data(gang)

        # 添加特征指纹增强
        gang['enhanced_fingerprint'] = self._enhance_fingerprint(gang)

        # 计算团伙综合评分
        gang['comprehensive_score'] = self._calculate_comprehensive_score(gang)

        # 计算威胁评级
        threat_level = self._calculate_threat_level(gang)
        gang['threat_level'] = threat_level
        
        self._log("INFO", f"团伙 {gang.get('gang_id')} 威胁评级计算完成: {threat_level}", context)

        return gang

    def _ensure_gang_fields(self, gang: Dict[str, Any]) -> Dict[str, Any]:
        """确保团伙对象包含所有必要字段"""
        default_fields = {
            'gang_id': f"GANG_{int(time.time())}",
            'gang_name': '未命名团伙',
            'risk_level': 'LOW',
            'risk_label': '低风险',
            'risk_type': 'info',
            'confidence': 60,
            'member_count_estimate': '未知',
            'active_time': '未知',
            'tech_level': '中',
            'script_type': '未知类型',
            'total_cases': 0,
            'total_amount_involved': '未知',
            'related_cases': [],
            'fingerprint': [],
            'steps': [],
            'description': '',
            'network_nodes': []
        }

        for key, default_value in default_fields.items():
            if key not in gang:
                gang[key] = default_value

        return gang

    async def _enhance_with_llm(self, gang: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        使用LLM增强团伙画像
        """
        # 准备案件摘要
        case_summaries = []
        for case in gang.get('related_cases', []):
            summary = (f"案件ID: {case.get('case_id', 'N/A')}, "
                       f"类型: {case.get('scam_type', '未知')}, "
                       f"风险: {case.get('risk_level', 'LOW')}, "
                       f"金额: {case.get('amount', '未知')}, "
                       f"关键词: {', '.join(case.get('keywords', ['无']))[:50]}")
            case_summaries.append(summary)

        cases_context = "\n".join(case_summaries)

        # 构建提示词
        prompt = f"""你是一名资深反诈画像专家，擅长从多个案件中提取犯罪团伙的核心特征。

请基于以下案件信息，为该犯罪团伙生成一份详细的全息画像：

【团伙基本信息】
团伙名称：{gang.get('gang_name', '未命名团伙')}
当前风险等级：{gang.get('risk_level', 'LOW')}
已知特征：{', '.join(gang.get('fingerprint', []))}

【关联案件】
{cases_context}

【任务】
请生成以下内容：
1. **团伙深度特征**：2-3个最核心的作案特征，包括技术手段、话术特点、组织方式等
2. **风险评估**：综合评估团伙的社会危害性、技术能力、反侦察能力
3. **作案模式**：详细描述该团伙的典型作案流程
4. **预警建议**：针对该类型团伙的防范建议

请以严格的JSON格式输出，键名如下：deep_characteristics, risk_assessment, modus_operandi, prevention_advice
不要输出任何其他解释性文字。
"""

        try:
            self._log("INFO", f"调用LLM增强团伙 {gang.get('gang_id')} 画像", context)
            response = self.llm_analyze.invoke(prompt)

            # 解析LLM返回的JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                llm_result = json.loads(json_match.group())
                # 更新团伙画像
                gang['deep_characteristics'] = llm_result.get('deep_characteristics', [])
                gang['risk_assessment'] = llm_result.get('risk_assessment', {})
                gang['modus_operandi'] = llm_result.get('modus_operandi', '')
                gang['prevention_advice'] = llm_result.get('prevention_advice', '')
        except Exception as e:
            self._log("ERROR", f"LLM增强画像失败: {e}", context)

        return gang

    def _generate_radar_data(self, gang: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成雷达图数据
        """
        # 基于团伙特征计算雷达图维度
        dimensions = [
            {"name": "技术能力", "value": 50},
            {"name": "组织严密性", "value": 50},
            {"name": "反侦察能力", "value": 50},
            {"name": "社会危害", "value": 50},
            {"name": "作案频率", "value": 50},
            {"name": "隐蔽性", "value": 50}
        ]

        # 根据团伙特征调整维度值
        risk_level = gang.get('risk_level', 'LOW')
        if risk_level == 'HIGH':
            for dim in dimensions:
                dim['value'] = min(100, dim['value'] + 30)
        elif risk_level == 'MEDIUM':
            for dim in dimensions:
                dim['value'] = min(100, dim['value'] + 15)

        # 根据案件数量调整
        total_cases = gang.get('total_cases', 0)
        if total_cases > 10:
            dimensions[4]['value'] = 90  # 作案频率
        elif total_cases > 5:
            dimensions[4]['value'] = 70

        # 根据技术等级调整
        tech_level = gang.get('tech_level', '中')
        if tech_level == '高':
            dimensions[0]['value'] = 90  # 技术能力
            dimensions[2]['value'] = 85  # 反侦察能力
        elif tech_level == '中':
            dimensions[0]['value'] = 60
            dimensions[2]['value'] = 50

        return {
            "indicator": dimensions,
            "series_data": [dim['value'] for dim in dimensions]
        }

    def _enhance_fingerprint(self, gang: Dict[str, Any]) -> List[str]:
        """
        增强特征指纹
        """
        base_fingerprint = gang.get('fingerprint', [])
        enhanced = []

        # 添加基于案件的特征
        cases = gang.get('related_cases', [])
        if cases:
            # 统计常见关键词
            keyword_count = {}
            for case in cases:
                for keyword in case.get('keywords', []):
                    keyword_count[keyword] = keyword_count.get(keyword, 0) + 1

            # 提取高频关键词
            top_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:3]
            for keyword, _ in top_keywords:
                if keyword not in base_fingerprint:
                    enhanced.append(keyword)

        # 添加基于风险等级的特征
        risk_level = gang.get('risk_level', 'LOW')
        if risk_level == 'HIGH':
            if '高风险操作' not in base_fingerprint:
                enhanced.append('高风险操作')
        elif risk_level == 'MEDIUM':
            if '中等风险' not in base_fingerprint:
                enhanced.append('中等风险')

        # 添加基于案件数量的特征
        total_cases = gang.get('total_cases', 0)
        if total_cases > 5:
            if '多起案件' not in base_fingerprint:
                enhanced.append('多起案件')

        return base_fingerprint + enhanced

    def _calculate_comprehensive_score(self, gang: Dict[str, Any]) -> int:
        """
        计算团伙综合评分
        """
        score = 50

        # 基于风险等级
        risk_level = gang.get('risk_level', 'LOW')
        if risk_level == 'HIGH':
            score += 30
        elif risk_level == 'MEDIUM':
            score += 15

        # 基于案件数量
        total_cases = gang.get('total_cases', 0)
        score += min(20, total_cases * 2)

        # 基于技术等级
        tech_level = gang.get('tech_level', '中')
        if tech_level == '高':
            score += 10
        elif tech_level == '低':
            score -= 10

        return min(100, max(0, score))

    def _calculate_threat_level(self, gang: Dict[str, Any]) -> str:
        """
        计算团伙威胁评级（S/A/B/C级）
        评分规则：
        - 金额权重40%：>100万得100分，50-100万得80分，10-50万得60分，<10万得30分
        - 案件数权重30%：>10起得100分，5-10起得80分，2-4起得60分，1起得30分
        - 技术等级权重20%：高=100分，中=60分，低=30分
        - 跨地域权重10%：涉案城市>3个得100分，2-3个得70分，1个得40分
        - 综合分≥85为S，70-84为A，50-69为B，<50为C
        """
        # 解析金额
        amount_str = gang.get('total_amount_involved', '0元')
        amount_num = self._parse_amount(amount_str)
        
        # 金额评分（40%权重）
        if amount_num >= 1000000:
            amount_score = 100
        elif amount_num >= 500000:
            amount_score = 80
        elif amount_num >= 100000:
            amount_score = 60
        else:
            amount_score = 30
        
        # 案件数评分（30%权重）
        total_cases = gang.get('total_cases', 0)
        if total_cases > 10:
            case_score = 100
        elif total_cases >= 5:
            case_score = 80
        elif total_cases >= 2:
            case_score = 60
        else:
            case_score = 30
        
        # 技术等级评分（20%权重）
        tech_level = gang.get('tech_level', '中')
        if tech_level == '高':
            tech_score = 100
        elif tech_level == '中':
            tech_score = 60
        else:
            tech_score = 30
        
        # 跨地域评分（10%权重）- 从related_cases中提取地域信息，默认计为1个城市
        related_cases = gang.get('related_cases', [])
        # 简单估算：每5个案件增加一个城市
        city_count = min(1 + len(related_cases) // 5, 5)
        
        if city_count > 3:
            region_score = 100
        elif city_count >= 2:
            region_score = 70
        else:
            region_score = 40
        
        # 计算综合评分
        total_score = (amount_score * 0.4) + (case_score * 0.3) + (tech_score * 0.2) + (region_score * 0.1)
        
        # 确定威胁等级
        if total_score >= 85:
            return 'S'
        elif total_score >= 70:
            return 'A'
        elif total_score >= 50:
            return 'B'
        else:
            return 'C'

    def _parse_amount(self, amount_str: str) -> float:
        """解析金额字符串为数值"""
        if not amount_str or amount_str == '未知金额':
            return 0.0
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            return num
        return 0.0
