"""
RAG 工具集 - 支持知识库检索和上下文增强
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .base import Tool, ToolInput, ToolOutput
from rag.knowledge_base import get_knowledge_base


# 输入 Schema
class SearchKnowledgeInput(ToolInput):
    """搜索知识库输入"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, description="返回最相关的K个结果")
    strategy: str = Field("hybrid", description="检索策略: vector/keyword/hybrid")


class AddDocumentInput(ToolInput):
    """添加文档输入"""
    content: str = Field(..., description="文档内容")
    source: Optional[str] = Field(None, description="文档来源")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class GetKnowledgeBaseStatsInput(ToolInput):
    """获取知识库统计输入"""
    pass


# 工具实现
class SearchKnowledgeTool(Tool):
    """搜索知识库"""
    
    name = "search_knowledge"
    description = "在知识库中搜索相关信息，支持向量检索、关键词检索和混合检索"
    input_schema = SearchKnowledgeInput
    
    def execute(
        self,
        query: str,
        top_k: int = 5,
        strategy: str = "hybrid"
    ) -> ToolOutput:
        """执行搜索"""
        try:
            kb = get_knowledge_base()
            
            results = kb.search(query=query, top_k=top_k, strategy=strategy)
            
            result_data = {
                "query": query,
                "strategy": strategy,
                "results_count": len(results),
                "results": [
                    {
                        "content": r.document.content,
                        "score": r.score,
                        "source": r.document.source,
                        "metadata": r.document.metadata
                    }
                    for r in results
                ]
            }
            
            return ToolOutput(success=True, data=result_data)
        
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class AddDocumentToKBTool(Tool):
    """添加文档到知识库"""
    
    name = "add_document_to_kb"
    description = "将新文档添加到知识库，自动切分和向量化"
    input_schema = AddDocumentInput
    
    def execute(
        self,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolOutput:
        """执行添加"""
        try:
            kb = get_knowledge_base()
            
            doc_id = kb.add_document(content=content, source=source, metadata=metadata)
            
            # 保存到磁盘
            kb.save()
            
            result_data = {
                "doc_id": doc_id,
                "source": source,
                "content_length": len(content),
                "message": "文档已成功添加到知识库"
            }
            
            return ToolOutput(success=True, data=result_data)
        
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class GetKnowledgeBaseStatsTool(Tool):
    """获取知识库统计信息"""
    
    name = "get_kb_stats"
    description = "获取知识库的统计信息，包括文档数量、chunk数量等"
    input_schema = GetKnowledgeBaseStatsInput
    
    def execute(self) -> ToolOutput:
        """执行查询"""
        try:
            kb = get_knowledge_base()
            stats = kb.get_stats()
            
            return ToolOutput(success=True, data=stats)
        
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class RetrieveAndCompressContextTool(Tool):
    """检索并压缩上下文"""
    
    name = "retrieve_context"
    description = "检索相关知识并压缩为上下文，用于增强 LLM 生成"
    input_schema = SearchKnowledgeInput
    
    def execute(
        self,
        query: str,
        top_k: int = 5,
        strategy: str = "hybrid"
    ) -> ToolOutput:
        """执行检索和压缩"""
        try:
            kb = get_knowledge_base()
            
            # 检索
            results = kb.search(query=query, top_k=top_k, strategy=strategy)
            
            # 压缩上下文
            compressed_context = kb.compress_context(results, max_length=2000)
            
            result_data = {
                "query": query,
                "context": compressed_context,
                "results_count": len(results),
                "context_length": len(compressed_context)
            }
            
            return ToolOutput(success=True, data=result_data)
        
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
