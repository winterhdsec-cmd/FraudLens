"""
RAG 模块 - 知识库和检索增强生成
支持高级特性：语义切分、查询改写、重排序
"""
from .knowledge_base import KnowledgeBase, Document, RetrievalResult, get_knowledge_base
from .semantic_chunking import SemanticChunker, SemanticChunk
from .query_rewrite import QueryRewriter, rewrite_and_merge
from .reranker import CrossEncoderReranker, MMRReranker, RerankPipeline, RerankedResult

__all__ = [
    "KnowledgeBase",
    "Document",
    "RetrievalResult",
    "get_knowledge_base",
    "SemanticChunker",
    "SemanticChunk",
    "QueryRewriter",
    "rewrite_and_merge",
    "CrossEncoderReranker",
    "MMRReranker",
    "RerankPipeline",
    "RerankedResult"
]
