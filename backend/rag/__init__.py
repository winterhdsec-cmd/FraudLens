"""
RAG 模块 - 知识库和检索增强生成
"""
from .knowledge_base import KnowledgeBase, Document, RetrievalResult, get_knowledge_base

__all__ = [
    "KnowledgeBase",
    "Document",
    "RetrievalResult",
    "get_knowledge_base"
]
