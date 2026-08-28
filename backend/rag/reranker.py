"""
重排序模块 - 提升检索结果质量
支持交叉编码器、规则重排、多样性重排等策略
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from core.logger import logger


@dataclass
class RerankedResult:
    """重排序结果"""
    document: Any
    original_score: float
    reranked_score: float
    rank: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CrossEncoderReranker:
    """
    交叉编码器重排序器
    
    原理：对 (query, document) 对进行联合编码，计算相关性分数
    优势：比双塔模型更准确，但计算成本更高
    """
    
    def __init__(self, model_name: str = None):
        """
        初始化重排序器
        
        Args:
            model_name: 预训练模型名称（如果为 None，使用规则重排）
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        
        # 如果有模型名称，尝试加载
        if model_name:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.model.eval()
                logger.info("CrossEncoder model loaded", model=model_name)
            except Exception as e:
                logger.warning("Failed to load cross-encoder model", error=str(e))
                self.model = None
    
    def rerank(
        self,
        query: str,
        documents: List[Any],
        top_k: int = None
    ) -> List[RerankedResult]:
        """
        重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前 K 个结果
        
        Returns:
            重排序后的结果列表
        """
        if not documents:
            return []
        
        # 如果有模型，使用交叉编码器
        if self.model:
            scores = self._cross_encoder_rerank(query, documents)
        else:
            # 否则使用规则重排
            scores = self._rule_based_rerank(query, documents)
        
        # 构建结果
        results = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            results.append(RerankedResult(
                document=doc,
                original_score=getattr(doc, 'score', 0.0),
                reranked_score=score,
                rank=i + 1
            ))
        
        # 按重排序分数排序
        results.sort(key=lambda x: x.reranked_score, reverse=True)
        
        # 更新排名
        for i, result in enumerate(results):
            result.rank = i + 1
        
        # 返回 top_k
        if top_k:
            results = results[:top_k]
        
        logger.info("Reranking completed", num_docs=len(documents), top_k=top_k)
        
        return results
    
    def _cross_encoder_rerank(self, query: str, documents: List[Any]) -> List[float]:
        """使用交叉编码器计算分数"""
        import torch
        
        scores = []
        
        for doc in documents:
            text = doc.content if hasattr(doc, 'content') else str(doc)
            
            # 编码
            inputs = self.tokenizer(
                query,
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # 预测
            with torch.no_grad():
                outputs = self.model(**inputs)
                score = outputs.logits.squeeze().item()
            
            scores.append(score)
        
        return scores
    
    def _rule_based_rerank(self, query: str, documents: List[Any]) -> List[float]:
        """
        规则重排（无模型时使用）

        策略：
        1. 关键词匹配度（中文使用 jieba 分词，避免空格切分失效）
        2. 文档长度惩罚
        3. 位置权重
        """
        # 中文分词：优先 jieba，失败时回退到字符级 n-gram
        query_keywords = self._tokenize_zh(query)
        scores = []

        for doc in documents:
            text = doc.content if hasattr(doc, 'content') else str(doc)
            doc_keywords = self._tokenize_zh(text)

            # 关键词匹配度（Jaccard 相似度）
            intersection = len(query_keywords & doc_keywords)
            union = len(query_keywords | doc_keywords)
            keyword_score = intersection / union if union > 0 else 0

            # 文档长度惩罚（避免过长或过短）
            doc_length = len(text)
            ideal_length = 300  # 理想长度
            length_penalty = 1.0 - abs(doc_length - ideal_length) / 1000
            length_penalty = max(0.5, min(1.0, length_penalty))

            # 原始分数
            original_score = getattr(doc, 'score', 0.0)

            # 综合分数
            final_score = (
                0.5 * original_score +
                0.3 * keyword_score +
                0.2 * length_penalty
            )
            
            scores.append(final_score)

        return scores

    @staticmethod
    def _tokenize_zh(text: str) -> set:
        """中文分词：优先 jieba，失败时回退到 2-gram 字符切分"""
        if not text:
            return set()
        text = text.lower().strip()
        try:
            import jieba
            return set(w for w in jieba.cut(text) if len(w.strip()) >= 2)
        except ImportError:
            # 回退：2-gram 字符切分（对中文比空格切分有效得多）
            chars = [c for c in text if c.isalnum()]
            if len(chars) < 2:
                return set(chars)
            return set(chars[i] + chars[i + 1] for i in range(len(chars) - 1))


class MMRReranker:
    """
    MMR (Maximal Marginal Relevance) 重排序器
    
    原理：在相关性和多样性之间取得平衡
    公式：MMR = argmax[λ * Sim(d, q) - (1-λ) * max(Sim(d, d'))]
    """
    
    def __init__(self, lambda_param: float = 0.7, embedding_model=None):
        """
        初始化 MMR 重排序器
        
        Args:
            lambda_param: 相关性权重（0-1），越高越注重相关性
            embedding_model: 嵌入模型（用于计算相似度）
        """
        self.lambda_param = lambda_param
        self.embedding_model = embedding_model
        
        logger.info("MMRReranker initialized", lambda_param=lambda_param)
    
    def rerank(
        self,
        query: str,
        documents: List[Any],
        top_k: int = None
    ) -> List[RerankedResult]:
        """
        MMR 重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前 K 个结果
        
        Returns:
            重排序后的结果列表
        """
        if not documents:
            return []
        
        # 计算文档嵌入
        doc_embeddings = []
        for doc in documents:
            if hasattr(doc, 'embedding') and doc.embedding is not None:
                doc_embeddings.append(doc.embedding)
            elif self.embedding_model:
                text = doc.content if hasattr(doc, 'content') else str(doc)
                emb = self.embedding_model.encode([text])[0]
                doc_embeddings.append(np.array(emb, dtype=np.float32))
            else:
                doc_embeddings.append(None)
        
        # 计算查询嵌入
        if self.embedding_model:
            query_embedding = np.array(self.embedding_model.encode([query])[0], dtype=np.float32)
        else:
            query_embedding = None
        
        # MMR 选择
        selected_indices = []
        remaining_indices = list(range(len(documents)))
        
        while remaining_indices and (top_k is None or len(selected_indices) < top_k):
            best_idx = None
            best_mmr_score = -float('inf')
            
            for idx in remaining_indices:
                doc = documents[idx]
                doc_emb = doc_embeddings[idx]
                
                # 相关性分数
                if query_embedding is not None and doc_emb is not None:
                    relevance = self._cosine_similarity(query_embedding, doc_emb)
                else:
                    relevance = getattr(doc, 'score', 0.0)
                
                # 多样性分数（与已选文档的最大相似度）
                if selected_indices:
                    max_similarity = 0
                    for sel_idx in selected_indices:
                        sel_emb = doc_embeddings[sel_idx]
                        if doc_emb is not None and sel_emb is not None:
                            sim = self._cosine_similarity(doc_emb, sel_emb)
                            max_similarity = max(max_similarity, sim)
                    diversity = max_similarity
                else:
                    diversity = 0
                
                # MMR 分数
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * diversity
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
        
        # 构建结果
        results = []
        for rank, idx in enumerate(selected_indices):
            doc = documents[idx]
            results.append(RerankedResult(
                document=doc,
                original_score=getattr(doc, 'score', 0.0),
                reranked_score=best_mmr_score,
                rank=rank + 1
            ))
        
        logger.info("MMR reranking completed", num_docs=len(documents), selected=len(selected_indices))
        
        return results
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if vec1 is None or vec2 is None:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class RerankPipeline:
    """
    重排序管道 - 串联多个重排策略
    
    流程：初始检索 → 交叉编码器重排 → MMR 多样性重排
    """
    
    def __init__(
        self,
        cross_encoder_model: str = None,
        lambda_param: float = 0.7,
        embedding_model=None
    ):
        """
        初始化管道
        
        Args:
            cross_encoder_model: 交叉编码器模型名称
            lambda_param: MMR 相关性权重
            embedding_model: 嵌入模型
        """
        self.cross_encoder = CrossEncoderReranker(cross_encoder_model)
        self.mmr_reranker = MMRReranker(lambda_param, embedding_model)
        
        logger.info("RerankPipeline initialized")
    
    def rerank(
        self,
        query: str,
        documents: List[Any],
        top_k: int = 5,
        use_mmr: bool = True
    ) -> List[RerankedResult]:
        """
        重排序管道
        
        Args:
            query: 查询文本
            documents: 初始检索结果
            top_k: 返回前 K 个结果
            use_mmr: 是否使用 MMR 重排
        
        Returns:
            重排序后的结果列表
        """
        if not documents:
            return []
        
        # 第一步：交叉编码器重排
        logger.info("Step 1: Cross-encoder reranking")
        reranked = self.cross_encoder.rerank(query, documents, top_k=top_k * 2)
        
        # 第二步：MMR 多样性重排
        if use_mmr:
            logger.info("Step 2: MMR diversity reranking")
            docs = [r.document for r in reranked]
            final_results = self.mmr_reranker.rerank(query, docs, top_k=top_k)
        else:
            final_results = reranked[:top_k]
        
        logger.info("Rerank pipeline completed", final_count=len(final_results))
        
        return final_results
