"""
工具系统 - Agent 可调用的工具集合
"""
from .base import Tool, ToolRegistry
from .database_tools import (
    QueryCasesTool,
    GetCaseDetailTool,
    SearchSimilarCasesTool,
    CreateCaseTool,
    UpdateCaseTool
)
from .evidence_tools import ExtractEvidenceTool, ValidateEvidenceTool
from .risk_tools import AssessRiskTool, CalculateRiskScoreTool
from .statistics_tools import GetStatisticsTool, GenerateReportTool

__all__ = [
    'Tool', 'ToolRegistry',
    'QueryCasesTool', 'GetCaseDetailTool', 'SearchSimilarCasesTool',
    'CreateCaseTool', 'UpdateCaseTool',
    'ExtractEvidenceTool', 'ValidateEvidenceTool',
    'AssessRiskTool', 'CalculateRiskScoreTool',
    'GetStatisticsTool', 'GenerateReportTool'
]
