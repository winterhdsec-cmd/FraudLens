"""
风险评估工具
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .base import Tool, ToolInput, ToolOutput


class AssessRiskInput(ToolInput):
    """风险评估输入"""
    case_data: Dict[str, Any] = Field(..., description="案件数据")


class CalculateRiskScoreInput(ToolInput):
    """计算风险分数输入"""
    amount: float = Field(..., description="涉案金额")
    fraud_type: str = Field(..., description="诈骗类型")
    victim_age: Optional[int] = Field(None, description="受害人年龄")
    has_evidence: bool = Field(False, description="是否有证据")


class AssessRiskTool(Tool):
    """评估案件风险"""
    
    name = "assess_risk"
    description = "根据案件数据评估风险等级，返回风险等级（HIGH/MEDIUM/LOW）和风险分数（0-100）"
    input_schema = AssessRiskInput
    
    # 诈骗类型风险权重
    FRAUD_TYPE_WEIGHTS = {
        "冒充公检法": 0.9,
        "投资理财": 0.85,
        "冒充客服": 0.7,
        "刷单返利": 0.65,
        "冒充熟人": 0.6,
        "网络贷款": 0.55,
        "其他": 0.5
    }
    
    def execute(self, case_data: Dict[str, Any]) -> ToolOutput:
        """执行风险评估"""
        try:
            amount = float(case_data.get("amount", 0))
            fraud_type = case_data.get("fraud_type", "其他")
            victim_age = case_data.get("victim_age")
            has_evidence = bool(case_data.get("extracted_entities"))
            
            # 计算风险分数
            risk_score = self._calculate_risk_score(
                amount=amount,
                fraud_type=fraud_type,
                victim_age=victim_age,
                has_evidence=has_evidence
            )
            
            # 确定风险等级
            if risk_score >= 80:
                risk_level = "HIGH"
                risk_label = "高风险"
            elif risk_score >= 60:
                risk_level = "MEDIUM"
                risk_label = "中风险"
            else:
                risk_level = "LOW"
                risk_label = "低风险"
            
            # 生成风险因素
            risk_factors = self._identify_risk_factors(
                amount=amount,
                fraud_type=fraud_type,
                victim_age=victim_age
            )
            
            result = {
                "risk_level": risk_level,
                "risk_label": risk_label,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "recommendation": self._generate_recommendation(risk_level, risk_factors)
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
    
    def _calculate_risk_score(
        self,
        amount: float,
        fraud_type: str,
        victim_age: Optional[int],
        has_evidence: bool
    ) -> int:
        """计算风险分数"""
        score = 0
        
        # 金额因素（0-40分）
        if amount >= 500000:
            score += 40
        elif amount >= 100000:
            score += 30
        elif amount >= 50000:
            score += 20
        elif amount >= 10000:
            score += 10
        else:
            score += 5
        
        # 诈骗类型因素（0-30分）
        type_weight = self.FRAUD_TYPE_WEIGHTS.get(fraud_type, 0.5)
        score += int(type_weight * 30)
        
        # 受害人年龄因素（0-15分）
        if victim_age:
            if victim_age >= 60:
                score += 15  # 老年人更易受害
            elif victim_age <= 22:
                score += 10  # 年轻人
            else:
                score += 5
        
        # 证据因素（0-15分）
        if has_evidence:
            score += 15
        
        return min(score, 100)
    
    def _identify_risk_factors(
        self,
        amount: float,
        fraud_type: str,
        victim_age: Optional[int]
    ) -> list:
        """识别风险因素"""
        factors = []
        
        if amount >= 100000:
            factors.append(f"涉案金额较大（{amount:,.0f}元）")
        
        if fraud_type in ["冒充公检法", "投资理财"]:
            factors.append(f"诈骗类型风险高（{fraud_type}）")
        
        if victim_age and victim_age >= 60:
            factors.append(f"受害人为老年人（{victim_age}岁），易受骗")
        
        return factors
    
    def _generate_recommendation(self, risk_level: str, risk_factors: list) -> str:
        """生成建议"""
        if risk_level == "HIGH":
            return "建议立即立案侦查，优先处理。注意保护受害人权益，及时冻结涉案账户。"
        elif risk_level == "MEDIUM":
            return "建议尽快立案，安排专人跟进。加强受害人防诈骗教育。"
        else:
            return "建议登记备案，持续关注。对受害人进行防诈骗宣传。"


class CalculateRiskScoreTool(Tool):
    """计算风险分数"""
    
    name = "calculate_risk_score"
    description = "根据涉案金额、诈骗类型、受害人年龄等因素计算风险分数（0-100）"
    input_schema = CalculateRiskScoreInput
    
    def execute(
        self,
        amount: float,
        fraud_type: str,
        victim_age: Optional[int] = None,
        has_evidence: bool = False
    ) -> ToolOutput:
        """执行计算"""
        try:
            assess_tool = AssessRiskTool()
            case_data = {
                "amount": amount,
                "fraud_type": fraud_type,
                "victim_age": victim_age,
                "extracted_entities": {} if has_evidence else None
            }
            
            result = assess_tool.execute(case_data)
            
            if result.success:
                return ToolOutput(
                    success=True,
                    data={
                        "risk_score": result.data["risk_score"],
                        "risk_level": result.data["risk_level"]
                    }
                )
            else:
                return result
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
