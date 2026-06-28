"""
统计和报表工具
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from .base import Tool, ToolInput, ToolOutput


class GetStatisticsInput(ToolInput):
    """获取统计数据输入"""
    period: str = Field("month", description="统计周期: day/week/month/year")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")


class GenerateReportInput(ToolInput):
    """生成报表输入"""
    report_type: str = Field("summary", description="报表类型: summary/daily/monthly")
    include_charts: bool = Field(True, description="是否包含图表数据")


class GetStatisticsTool(Tool):
    """获取统计数据"""
    
    name = "get_statistics"
    description = "获取案件统计数据，包括案件数量、涉案金额、诈骗类型分布等"
    input_schema = GetStatisticsInput
    
    def execute(
        self,
        period: str = "month",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ToolOutput:
        """执行统计"""
        try:
            from database import db
            from database.models import Case, Gang
            from sqlalchemy import func
            
            # 确定时间范围
            if start_date and end_date:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
            else:
                end = datetime.utcnow()
                if period == "day":
                    start = end - timedelta(days=1)
                elif period == "week":
                    start = end - timedelta(weeks=1)
                elif period == "month":
                    start = end - timedelta(days=30)
                else:  # year
                    start = end - timedelta(days=365)
            
            # 查询案件统计
            cases_query = db.session.query(Case).filter(
                Case.created_at >= start,
                Case.created_at <= end
            )
            
            total_cases = cases_query.count()
            total_amount = db.session.query(func.sum(Case.amount_value)).filter(
                Case.created_at >= start,
                Case.created_at <= end
            ).scalar() or 0
            
            # 按诈骗类型统计
            fraud_type_stats = db.session.query(
                Case.scam_type,
                func.count(Case.id),
                func.sum(Case.amount_value)
            ).filter(
                Case.created_at >= start,
                Case.created_at <= end
            ).group_by(Case.scam_type).all()
            
            # 按风险等级统计
            risk_level_stats = db.session.query(
                Case.risk_level,
                func.count(Case.id)
            ).filter(
                Case.created_at >= start,
                Case.created_at <= end
            ).group_by(Case.risk_level).all()
            
            # 团伙统计
            gang_count = db.session.query(Gang).filter(
                Gang.created_at >= start,
                Gang.created_at <= end
            ).count()
            
            result = {
                "period": {
                    "start": start.isoformat(),
                    "end": end.isoformat()
                },
                "summary": {
                    "total_cases": total_cases,
                    "total_amount": float(total_amount),
                    "total_gangs": gang_count,
                    "avg_amount_per_case": float(total_amount) / total_cases if total_cases > 0 else 0
                },
                "by_fraud_type": [
                    {
                        "fraud_type": ft,
                        "count": count,
                        "amount": float(amt or 0)
                    }
                    for ft, count, amt in fraud_type_stats
                ],
                "by_risk_level": [
                    {
                        "risk_level": rl,
                        "count": count
                    }
                    for rl, count in risk_level_stats
                ]
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class GenerateReportTool(Tool):
    """生成报表"""
    
    name = "generate_report"
    description = "生成案件分析报表，包括汇总报表、日报、月报等"
    input_schema = GenerateReportInput
    
    def execute(
        self,
        report_type: str = "summary",
        include_charts: bool = True
    ) -> ToolOutput:
        """执行生成"""
        try:
            from database import db
            from database.models import Case, Gang
            
            if report_type == "summary":
                report = self._generate_summary_report(include_charts)
            elif report_type == "daily":
                report = self._generate_daily_report(include_charts)
            elif report_type == "monthly":
                report = self._generate_monthly_report(include_charts)
            else:
                return ToolOutput(success=False, error=f"不支持的报表类型: {report_type}")
            
            return ToolOutput(success=True, data=report)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
    
    def _generate_summary_report(self, include_charts: bool) -> Dict[str, Any]:
        """生成汇总报表"""
        from database import db
        from database.models import Case, Gang
        from sqlalchemy import func
        
        total_cases = db.session.query(Case).count()
        total_amount = db.session.query(func.sum(Case.amount_value)).scalar() or 0
        total_gangs = db.session.query(Gang).count()
        
        report = {
            "report_type": "summary",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_cases": total_cases,
                "total_amount": float(total_amount),
                "total_gangs": total_gangs
            }
        }
        
        if include_charts:
            # 添加图表数据
            report["charts"] = self._generate_chart_data()
        
        return report
    
    def _generate_daily_report(self, include_charts: bool) -> Dict[str, Any]:
        """生成日报"""
        from database import db
        from database.models import Case
        from sqlalchemy import func
        
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        cases_today = db.session.query(Case).filter(
            Case.created_at >= today_start,
            Case.created_at <= today_end
        ).count()
        
        amount_today = db.session.query(func.sum(Case.amount_value)).filter(
            Case.created_at >= today_start,
            Case.created_at <= today_end
        ).scalar() or 0
        
        return {
            "report_type": "daily",
            "date": today.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "cases_today": cases_today,
                "amount_today": float(amount_today)
            }
        }
    
    def _generate_monthly_report(self, include_charts: bool) -> Dict[str, Any]:
        """生成月报"""
        from database import db
        from database.models import Case
        from sqlalchemy import func
        
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        cases_this_month = db.session.query(Case).filter(
            Case.created_at >= month_start
        ).count()
        
        amount_this_month = db.session.query(func.sum(Case.amount_value)).filter(
            Case.created_at >= month_start
        ).scalar() or 0
        
        return {
            "report_type": "monthly",
            "month": now.strftime("%Y-%m"),
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "cases_this_month": cases_this_month,
                "amount_this_month": float(amount_this_month)
            }
        }
    
    def _generate_chart_data(self) -> Dict[str, Any]:
        """生成图表数据"""
        from database import db
        from database.models import Case
        from sqlalchemy import func
        
        # 诈骗类型分布
        fraud_type_dist = db.session.query(
            Case.scam_type,
            func.count(Case.id)
        ).group_by(Case.scam_type).all()
        
        # 风险等级分布
        risk_level_dist = db.session.query(
            Case.risk_level,
            func.count(Case.id)
        ).group_by(Case.risk_level).all()
        
        return {
            "fraud_type_distribution": [
                {"name": ft, "value": count}
                for ft, count in fraud_type_dist
            ],
            "risk_level_distribution": [
                {"name": rl, "value": count}
                for rl, count in risk_level_dist
            ]
        }
