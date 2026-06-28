"""
RAG 知识库系统 - 基于腾讯 WeKnora 最佳实践
支持文档处理、多路召回、上下文压缩
"""
import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np

from core.logger import logger, tracer


@dataclass
class Document:
    """文档对象"""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    chunk_id: Optional[str] = None
    source: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RetrievalResult:
    """检索结果"""
    document: Document
    score: float
    highlight: Optional[str] = None


class DocumentProcessor:
    """
    文档处理器 - 参考 WeKnora 的文档处理管道
    
    功能：
    1. 文档切分（支持多种策略）
    2. 元数据提取
    3. 向量化
    """
    
    def __init__(self, embedding_model=None, chunk_size: int = 500, chunk_overlap: int = 50):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_document(self, text: str, strategy: str = "fixed") -> List[str]:
        """
        文档切分
        
        Args:
            text: 原始文本
            strategy: 切分策略 - "fixed"(固定长度), "sentence"(按句子), "paragraph"(按段落)
        
        Returns:
            切分后的文本块列表
        """
        if not text or not text.strip():
            return []
        
        if strategy == "fixed":
            return self._split_by_fixed_size(text)
        elif strategy == "sentence":
            return self._split_by_sentence(text)
        elif strategy == "paragraph":
            return self._split_by_paragraph(text)
        else:
            return self._split_by_fixed_size(text)
    
    def _split_by_fixed_size(self, text: str) -> List[str]:
        """固定长度切分"""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # 尝试在句子边界切分
            if end < text_len:
                # 向前查找句子边界
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in ['。', '！', '？', '.', '!', '?']:
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 移动起始位置（考虑重叠）
            start = end - self.chunk_overlap if end < text_len else text_len
        
        return chunks
    
    def _split_by_sentence(self, text: str) -> List[str]:
        """按句子切分"""
        import re
        # 中文句子分割
        sentences = re.split(r'([。！？.!?])', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 加上标点
            
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks
    
    def _split_by_paragraph(self, text: str) -> List[str]:
        """按段落切分"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if current_length + len(para) > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(para)
            current_length += len(para)
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def extract_metadata(self, text: str, source: str = None) -> Dict[str, Any]:
        """提取文档元数据"""
        metadata = {
            "char_count": len(text),
            "source": source,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # 尝试提取关键词（简单实现）
        keywords = self._extract_keywords(text)
        if keywords:
            metadata["keywords"] = keywords
        
        return metadata
    
    def _extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """简单关键词提取（基于词频）"""
        import re
        # 移除标点
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个'}
        words = [w for w in words if len(w) > 1 and w not in stop_words]
        
        # 统计词频
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 返回 top_k
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_k]]
    
    def embed_chunks(self, chunks: List[str]) -> List[np.ndarray]:
        """向量化文本块"""
        if not self.embedding_model:
            # 使用 hash 向量作为 fallback
            return [self._hash_embedding(chunk) for chunk in chunks]
        
        return self.embedding_model.encode(chunks)
    
    def _hash_embedding(self, text: str, dim: int = 768) -> np.ndarray:
        """Hash 向量（fallback）"""
        hash_val = abs(hash(text)) % (2**32)
        np.random.seed(hash_val)
        return np.random.randn(dim).astype(np.float32)


class KnowledgeBase:
    """
    知识库 - 参考 WeKnora 的模块化架构
    
    功能：
    1. 文档存储和管理
    2. 向量索引
    3. 多路召回（向量检索 + 关键词检索）
    4. 上下文压缩
    """
    
    def __init__(self, embedding_model=None, storage_path: str = None):
        self.embedding_model = embedding_model
        self.storage_path = storage_path or "data/knowledge_base"
        
        # 文档存储
        self.documents: Dict[str, Document] = {}
        self.chunks: List[Document] = []
        
        # 文档处理器
        self.processor = DocumentProcessor(embedding_model=embedding_model)
        
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        
        logger.info("KnowledgeBase initialized", storage_path=self.storage_path)
    
    def add_document(self, content: str, source: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        添加文档到知识库
        
        Args:
            content: 文档内容
            source: 文档来源
            metadata: 额外元数据
        
        Returns:
            文档ID
        """
        with tracer.span("kb.add_document", source=source, content_length=len(content)):
            # 生成文档ID
            doc_id = hashlib.md5(f"{content}_{datetime.utcnow().isoformat()}".encode()).hexdigest()
            
            # 提取元数据
            doc_metadata = self.processor.extract_metadata(content, source)
            if metadata:
                doc_metadata.update(metadata)
            
            # 创建文档对象
            doc = Document(
                doc_id=doc_id,
                content=content,
                metadata=doc_metadata,
                source=source
            )
            
            # 切分文档
            chunks = self.processor.split_document(content)
            
            # 向量化
            embeddings = self.processor.embed_chunks(chunks)
            
            # 创建 chunk 对象
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk = Document(
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_id=chunk_id,
                    embedding=embedding,
                    metadata=doc_metadata,
                    source=source
                )
                self.chunks.append(chunk)
            
            # 存储文档
            self.documents[doc_id] = doc
            
            logger.info(
                "Document added to knowledge base",
                doc_id=doc_id,
                chunks_count=len(chunks),
                source=source
            )
            
            return doc_id
    
    def search(self, query: str, top_k: int = 5, strategy: str = "vector") -> List[RetrievalResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            strategy: 检索策略 - "vector"(向量检索), "keyword"(关键词), "hybrid"(混合)
        
        Returns:
            检索结果列表
        """
        with tracer.span("kb.search", query=query[:100], top_k=top_k, strategy=strategy):
            if not self.chunks:
                logger.warning("Knowledge base is empty")
                return []
            
            if strategy == "vector":
                return self._vector_search(query, top_k)
            elif strategy == "keyword":
                return self._keyword_search(query, top_k)
            elif strategy == "hybrid":
                return self._hybrid_search(query, top_k)
            else:
                return self._vector_search(query, top_k)
    
    def _vector_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """向量检索"""
        # 向量化查询
        query_embedding = self.processor.embed_chunks([query])[0]
        
        # 计算相似度
        similarities = []
        for chunk in self.chunks:
            if chunk.embedding is not None:
                similarity = np.dot(query_embedding, chunk.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk.embedding) + 1e-8
                )
                similarities.append((chunk, float(similarity)))
        
        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for chunk, score in similarities[:top_k]:
            results.append(RetrievalResult(document=chunk, score=score))
        
        return results
    
    def _keyword_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """关键词检索"""
        import re
        
        # 简单关键词匹配
        query_keywords = set(re.findall(r'\w+', query.lower()))
        
        scores = []
        for chunk in self.chunks:
            chunk_keywords = set(re.findall(r'\w+', chunk.content.lower()))
            
            # Jaccard 相似度
            intersection = len(query_keywords & chunk_keywords)
            union = len(query_keywords | chunk_keywords)
            score = intersection / union if union > 0 else 0
            
            scores.append((chunk, score))
        
        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for chunk, score in scores[:top_k]:
            results.append(RetrievalResult(document=chunk, score=score))
        
        return results
    
    def _hybrid_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """混合检索（向量 + 关键词）"""
        # 分别检索
        vector_results = self._vector_search(query, top_k * 2)
        keyword_results = self._keyword_search(query, top_k * 2)
        
        # 融合分数（RRF - Reciprocal Rank Fusion）
        doc_scores = {}
        
        for rank, result in enumerate(vector_results):
            doc_id = result.document.chunk_id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"document": result.document, "score": 0}
            doc_scores[doc_id]["score"] += 1.0 / (rank + 1)
        
        for rank, result in enumerate(keyword_results):
            doc_id = result.document.chunk_id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"document": result.document, "score": 0}
            doc_scores[doc_id]["score"] += 1.0 / (rank + 1)
        
        # 排序并返回 top_k
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
        
        results = []
        for item in sorted_docs[:top_k]:
            results.append(RetrievalResult(document=item["document"], score=item["score"]))
        
        return results
    
    def compress_context(self, results: List[RetrievalResult], max_length: int = 2000) -> str:
        """
        上下文压缩 - 将检索结果压缩到指定长度
        
        Args:
            results: 检索结果
            max_length: 最大长度
        
        Returns:
            压缩后的上下文
        """
        if not results:
            return ""
        
        # 按相关性排序
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        context_parts = []
        current_length = 0
        
        for result in sorted_results:
            content = result.document.content
            
            if current_length + len(content) > max_length:
                # 截断
                remaining = max_length - current_length
                if remaining > 100:
                    context_parts.append(content[:remaining] + "...")
                break
            
            context_parts.append(content)
            current_length += len(content)
        
        return "\n\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "storage_path": self.storage_path,
            "has_embedding_model": self.embedding_model is not None
        }
    
    def save(self, filepath: str = None):
        """保存知识库到磁盘"""
        filepath = filepath or os.path.join(self.storage_path, "knowledge_base.json")
        
        data = {
            "documents": {
                doc_id: {
                    "doc_id": doc.doc_id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "source": doc.source,
                    "created_at": doc.created_at
                }
                for doc_id, doc in self.documents.items()
            },
            "chunks": [
                {
                    "doc_id": chunk.doc_id,
                    "content": chunk.content,
                    "chunk_id": chunk.chunk_id,
                    "metadata": chunk.metadata,
                    "source": chunk.source,
                    "embedding": chunk.embedding.tolist() if chunk.embedding is not None else None
                }
                for chunk in self.chunks
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info("Knowledge base saved", filepath=filepath)
    
    def load(self, filepath: str = None):
        """从磁盘加载知识库"""
        filepath = filepath or os.path.join(self.storage_path, "knowledge_base.json")
        
        if not os.path.exists(filepath):
            logger.warning("Knowledge base file not found", filepath=filepath)
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载文档
        for doc_id, doc_data in data.get("documents", {}).items():
            self.documents[doc_id] = Document(**doc_data)
        
        # 加载 chunks
        for chunk_data in data.get("chunks", []):
            if chunk_data.get("embedding"):
                chunk_data["embedding"] = np.array(chunk_data["embedding"], dtype=np.float32)
            self.chunks.append(Document(**chunk_data))
        
        logger.info(
            "Knowledge base loaded",
            documents_count=len(self.documents),
            chunks_count=len(self.chunks)
        )


# 全局知识库实例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取全局知识库实例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
        # 尝试加载已存在的知识库
        _knowledge_base.load()
    return _knowledge_base
