"""
数据库查询工具
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .base import Tool, ToolInput, ToolOutput


# 输入 Schema
class QueryCasesInput(ToolInput):
    """查询案件输入"""
    fraud_type: Optional[str] = Field(None, description="诈骗类型")
    risk_level: Optional[str] = Field(None, description="风险等级: HIGH/MEDIUM/LOW")
    status: Optional[str] = Field(None, description="案件状态")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")
    limit: int = Field(50, description="返回数量限制")


class GetCaseDetailInput(ToolInput):
    """获取案件详情输入"""
    case_id: str = Field(..., description="案件ID")


class SearchSimilarCasesInput(ToolInput):
    """搜索相似案件输入"""
    description: str = Field(..., description="案件描述")
    top_k: int = Field(5, description="返回最相似的K个案件")


class GetGangsInput(ToolInput):
    """查询团伙输入"""
    risk_level: Optional[str] = Field(None, description="风险等级: S/A/B，不传返回全部")
    gang_id: Optional[str] = Field(None, description="团伙ID，传则只返回该团伙及其成员案件")
    limit: int = Field(20, description="返回团伙数量限制")


class CreateCaseInput(ToolInput):
    """创建案件输入"""
    title: str = Field(..., description="案件标题")
    description: str = Field(..., description="案件描述")
    fraud_type: str = Field(..., description="诈骗类型")
    amount: float = Field(0, description="涉案金额")
    victim_name: Optional[str] = Field(None, description="受害人姓名")
    victim_phone: Optional[str] = Field(None, description="受害人电话")


class UpdateCaseInput(ToolInput):
    """更新案件输入"""
    case_id: str = Field(..., description="案件ID")
    status: Optional[str] = Field(None, description="案件状态")
    risk_level: Optional[str] = Field(None, description="风险等级")
    ai_report: Optional[str] = Field(None, description="AI分析报告")


# 工具实现
class QueryCasesTool(Tool):
    """查询案件列表"""
    
    name = "query_cases"
    description = "根据条件查询案件列表，支持按诈骗类型、风险等级、状态、日期范围筛选"
    input_schema = QueryCasesInput
    
    def execute(
        self,
        fraud_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> ToolOutput:
        """执行查询"""
        try:
            from database import db
            from database.models import Case
            from database.crud import apply_department_scope
            
            query = db.session.query(Case)
            # 部门隔离：普通账号经问答也只能看到本部门案件（admin/auditor 豁免）
            query = apply_department_scope(Case, query, getattr(self, 'context', {}).get('user'))
            
            if fraud_type:
                query = query.filter(Case.scam_type == fraud_type)
            if risk_level:
                query = query.filter(Case.risk_level == risk_level)
            if status:
                query = query.filter(Case.status == status)
            if start_date:
                query = query.filter(Case.created_at >= datetime.fromisoformat(start_date))
            if end_date:
                query = query.filter(Case.created_at <= datetime.fromisoformat(end_date))
            
            cases = query.limit(limit).all()
            
            result = {
                "total": len(cases),
                "cases": [
                    {
                        "case_id": c.case_id,
                        "title": c.title,
                        "fraud_type": c.scam_type,
                        "risk_level": c.risk_level,
                        "risk_score": c.risk_score,
                        "amount": c.amount,
                        "victim_name": c.victim_name,
                        "status": c.status,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in cases
                ]
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class GetCaseDetailTool(Tool):
    """获取案件详情"""
    
    name = "get_case_detail"
    description = "根据案件ID获取案件的详细信息，包括受害人信息、案件描述、AI分析报告等"
    input_schema = GetCaseDetailInput
    
    def execute(self, case_id: str) -> ToolOutput:
        """执行查询"""
        try:
            from database import db
            from database.models import Case
            from database.crud import apply_department_scope
            
            query = db.session.query(Case).filter_by(case_id=case_id)
            # 部门隔离：越权访问按"不存在"处理，不泄露案件是否存在
            query = apply_department_scope(Case, query, getattr(self, 'context', {}).get('user'))
            case = query.first()
            
            if not case:
                return ToolOutput(success=False, error=f"案件 {case_id} 不存在或无访问权限")
            
            result = {
                "case_id": case.case_id,
                "title": case.title,
                "description": case.description,
                "fraud_type": case.scam_type,
                "scam_subtype": case.scam_subtype,
                "risk_level": case.risk_level,
                "risk_score": case.risk_score,
                "amount": case.amount,
                "amount_value": case.amount_value,
                "victim_name": case.victim_name,
                "victim_gender": case.victim_gender,
                "victim_age": case.victim_age,
                "victim_phone": case.victim_phone,
                "victim_job": case.victim_job,
                "victim_address": case.victim_address,
                "status": case.status,
                "ai_report": case.ai_report,
                "keywords": case.keywords,
                "extracted_entities": case.extracted_entities,
                "radar_data": case.radar_data,
                "created_at": case.created_at.isoformat() if case.created_at else None
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class SearchSimilarCasesTool(Tool):
    """搜索相似案件"""
    
    name = "search_similar_cases"
    description = "根据案件描述搜索语义相似的案件，用于发现关联案件和串并案分析"
    input_schema = SearchSimilarCasesInput
    
    def execute(self, description: str, top_k: int = 5) -> ToolOutput:
        """执行搜索"""
        try:
            from tools.embedding_utils import get_embedding_model
            from database import db
            from database.models import Case
            from database.crud import apply_department_scope
            import numpy as np
            
            # 编码查询文本
            bge = get_embedding_model()
            query_embedding = bge.encode([description])[0]
            
            # 获取候选案件（同样受部门隔离约束）
            query = db.session.query(Case).filter(Case.description != '')
            query = apply_department_scope(Case, query, getattr(self, 'context', {}).get('user'))
            cases = query.all()
            
            if not cases:
                return ToolOutput(success=True, data={"similar_cases": [], "count": 0})
            
            # 计算相似度
            similarities = []
            for case in cases:
                if case.embedding:
                    case_embedding = np.frombuffer(case.embedding, dtype=np.float32)
                    similarity = np.dot(query_embedding, case_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(case_embedding)
                    )
                    similarities.append((case, float(similarity)))
            
            # 排序并取 top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_cases = similarities[:top_k]
            
            result = {
                "similar_cases": [
                    {
                        "case_id": case.case_id,
                        "title": case.title,
                        "fraud_type": case.scam_type,
                        "similarity": sim,
                        "description": case.description[:200] + "..." if len(case.description) > 200 else case.description
                    }
                    for case, sim in top_cases
                ],
                "count": len(top_cases)
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class GetGangsTool(Tool):
    """查询已识别的诈骗团伙（GNN 聚类结果）"""

    name = "get_gangs"
    description = ("查询系统已识别的诈骗团伙及其成员案件（GNN 图神经网络聚类结果）。"
                   "可按风险等级筛选，或按团伙ID查某个团伙的成员案件清单；"
                   "也可回答'某案件属于哪个团伙'这类串并归属问题。")
    input_schema = GetGangsInput

    def execute(
        self,
        risk_level: Optional[str] = None,
        gang_id: Optional[str] = None,
        limit: int = 20
    ) -> ToolOutput:
        try:
            from database import db
            from database.models import Gang, GangCaseRelation, Case
            from database.crud import apply_department_scope

            user = getattr(self, 'context', {}).get('user')
            query = db.session.query(Gang)
            # 团伙同样按部门隔离（Gang 表有 department 字段）
            query = apply_department_scope(Gang, query, user)

            if risk_level:
                query = query.filter(Gang.risk_level == risk_level.upper())
            if gang_id:
                query = query.filter(Gang.gang_id == gang_id)

            gangs = query.limit(limit).all()
            if not gangs:
                return ToolOutput(success=True, data={"total": 0, "gangs": []})

            gang_ids = [g.gang_id for g in gangs]
            rels = db.session.query(GangCaseRelation).filter(
                GangCaseRelation.gang_id.in_(gang_ids)
            ).all()

            members: Dict[str, list] = {gid: [] for gid in gang_ids}
            case_ids = {r.case_id for r in rels}
            titles = {}
            if case_ids:
                cq = db.session.query(Case.case_id, Case.title, Case.amount, Case.risk_level).filter(
                    Case.case_id.in_(list(case_ids))
                )
                cq = apply_department_scope(Case, cq, user)
                titles = {c.case_id: c for c in cq.all()}
            for r in rels:
                # 成员案件也按可见范围过滤，避免通过团伙侧漏出越权案件
                if r.case_id in titles:
                    members.setdefault(r.gang_id, []).append(r.case_id)

            result = {
                "total": len(gangs),
                "gangs": [
                    {
                        "gang_id": g.gang_id,
                        "gang_name": g.gang_name,
                        "risk_level": g.risk_level,
                        "risk_label": g.risk_label,
                        "threat_level": g.threat_level,
                        "member_count": len(members.get(g.gang_id, [])),
                        "total_amount": g.total_amount,
                        "script_type": g.script_type,
                        "members": [
                            {
                                "case_id": cid,
                                "title": titles[cid].title,
                                "amount": titles[cid].amount,
                                "risk_level": titles[cid].risk_level,
                            }
                            for cid in members.get(g.gang_id, [])
                        ],
                    }
                    for g in gangs
                ],
            }
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class CreateCaseTool(Tool):
    """创建新案件"""
    
    name = "create_case"
    description = "创建新的诈骗案件记录"
    input_schema = CreateCaseInput
    
    def execute(
        self,
        title: str,
        description: str,
        fraud_type: str,
        amount: float = 0,
        victim_name: Optional[str] = None,
        victim_phone: Optional[str] = None
    ) -> ToolOutput:
        """执行创建"""
        try:
            from database import db
            from database.models import Case
            import uuid
            from datetime import datetime
            
            case_id = f"CASE_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
            
            case = Case(
                case_id=case_id,
                title=title,
                description=description,
                scam_type=fraud_type,
                amount=str(amount),
                amount_value=amount,
                victim_name=victim_name or "",
                victim_phone=victim_phone or "",
                status="待分析",
                created_at=datetime.utcnow()
            )
            
            db.session.add(case)
            db.session.commit()
            
            result = {
                "case_id": case_id,
                "message": "案件创建成功"
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            db.session.rollback()
            return ToolOutput(success=False, error=str(e))


class UpdateCaseTool(Tool):
    """更新案件信息"""
    
    name = "update_case"
    description = "更新案件的状态、风险等级或AI分析报告"
    input_schema = UpdateCaseInput
    
    def execute(
        self,
        case_id: str,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        ai_report: Optional[str] = None
    ) -> ToolOutput:
        """执行更新"""
        try:
            from database import db
            from database.models import Case
            
            case = db.session.query(Case).filter_by(case_id=case_id).first()
            
            if not case:
                return ToolOutput(success=False, error=f"案件 {case_id} 不存在")
            
            if status:
                case.status = status
            if risk_level:
                case.risk_level = risk_level
            if ai_report:
                case.ai_report = ai_report
            
            db.session.commit()
            
            result = {
                "case_id": case_id,
                "message": "案件更新成功"
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            db.session.rollback()
            return ToolOutput(success=False, error=str(e))
