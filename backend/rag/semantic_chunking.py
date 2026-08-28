"""
语义切分 - 基于语义边界的智能文档切分
相比固定长度切分，能更好地保持语义完整性
"""
import re
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from core.logger import logger


@dataclass
class SemanticChunk:
    """语义块"""
    text: str
    start_idx: int
    end_idx: int
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SemanticChunker:
    """
    语义切分器 - 基于语义边界的智能切分
    
    策略：
    1. 句子边界检测
    2. 主题变化检测（基于嵌入相似度）
    3. 长度约束（避免过长或过短）
    """
    
    def __init__(
        self,
        embedding_model=None,
        max_chunk_size: int = 500,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.7,
        overlap: int = 50
    ):
        """
        初始化切分器
        
        Args:
            embedding_model: 嵌入模型（用于语义相似度计算）
            max_chunk_size: 最大块大小（字符数）
            min_chunk_size: 最小块大小（字符数）
            similarity_threshold: 相似度阈值（低于此值则切分）
            overlap: 重叠字符数
        """
        self.embedding_model = embedding_model
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.similarity_threshold = similarity_threshold
        self.overlap = overlap
        
        logger.info(
            "SemanticChunker initialized",
            max_chunk_size=max_chunk_size,
            min_chunk_size=min_chunk_size,
            similarity_threshold=similarity_threshold
        )
    
    def chunk(self, text: str) -> List[SemanticChunk]:
        """
        语义切分
        
        Args:
            text: 原始文本
        
        Returns:
            语义块列表
        """
        if not text or len(text) < self.min_chunk_size:
            return [SemanticChunk(text=text, start_idx=0, end_idx=len(text))]
        
        # 1. 分句
        sentences = self._split_sentences(text)
        
        if not sentences:
            return [SemanticChunk(text=text, start_idx=0, end_idx=len(text))]
        
        # 2. 如果有嵌入模型，使用语义相似度检测边界
        if self.embedding_model:
            chunks = self._semantic_chunking(text, sentences)
        else:
            # 否则使用规则切分
            chunks = self._rule_based_chunking(text, sentences)
        
        # 3. 计算嵌入
        if self.embedding_model:
            for chunk in chunks:
                chunk.embedding = self._embed(chunk.text)
        
        logger.info("Semantic chunking completed", num_chunks=len(chunks))
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[Tuple[str, int]]:
        """
        分句，返回 (句子, 起始位置) 列表
        """
        # 中英文句子分割
        pattern = r'([。！？.!?]+)'
        parts = re.split(pattern, text)
        
        sentences = []
        current_pos = 0
        
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + parts[i + 1] if i + 1 < len(parts) else parts[i]
            sentence = sentence.strip()
            if sentence:
                start_idx = text.find(sentence, current_pos)
                sentences.append((sentence, start_idx))
                current_pos = start_idx + len(sentence)
        
        # 处理最后一部分
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentence = parts[-1].strip()
            start_idx = text.find(sentence, current_pos)
            sentences.append((sentence, start_idx))
        
        return sentences
    
    def _semantic_chunking(self, text: str, sentences: List[Tuple[str, int]]) -> List[SemanticChunk]:
        """
        基于语义相似度的切分
        """
        if not sentences:
            return []
        
        # 计算每个句子的嵌入
        sentence_embeddings = []
        for sent, _ in sentences:
            emb = self._embed(sent)
            sentence_embeddings.append(emb)
        
        # 计算相邻句子的相似度
        similarities = []
        for i in range(len(sentence_embeddings) - 1):
            sim = self._cosine_similarity(sentence_embeddings[i], sentence_embeddings[i + 1])
            similarities.append(sim)
        
        # 找到切分点（相似度低于阈值的位置）
        split_points = [0]  # 起始点
        current_chunk_start = 0
        current_chunk_length = 0
        
        for i, sim in enumerate(similarities):
            sent_length = len(sentences[i][0])
            current_chunk_length += sent_length
            
            # 如果相似度低且当前块足够长，则切分
            if sim < self.similarity_threshold and current_chunk_length >= self.min_chunk_size:
                split_points.append(i + 1)
                current_chunk_length = 0
            
            # 如果当前块太长，强制切分
            elif current_chunk_length >= self.max_chunk_size:
                split_points.append(i + 1)
                current_chunk_length = 0
        
        split_points.append(len(sentences))
        
        # 构建块
        chunks = []
        for i in range(len(split_points) - 1):
            start_sent_idx = split_points[i]
            end_sent_idx = split_points[i + 1]
            
            chunk_sentences = sentences[start_sent_idx:end_sent_idx]
            chunk_text = "".join([s[0] for s in chunk_sentences])
            
            if chunk_text.strip():
                start_idx = chunk_sentences[0][1]
                end_idx = start_idx + len(chunk_text)
                
                chunks.append(SemanticChunk(
                    text=chunk_text.strip(),
                    start_idx=start_idx,
                    end_idx=end_idx
                ))
        
        return chunks
    
    def _rule_based_chunking(self, text: str, sentences: List[Tuple[str, int]]) -> List[SemanticChunk]:
        """
        基于规则的切分（无嵌入模型时使用）
        """
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0
        
        for i, (sentence, start_idx) in enumerate(sentences):
            sent_length = len(sentence)
            
            # 如果加入当前句子会超过最大长度，且当前块足够长
            if current_length + sent_length > self.max_chunk_size and current_length >= self.min_chunk_size:
                chunk_text = "".join([s[0] for s in current_chunk])
                if chunk_text.strip():
                    chunks.append(SemanticChunk(
                        text=chunk_text.strip(),
                        start_idx=current_start,
                        end_idx=current_start + len(chunk_text)
                    ))
                
                # 开始新块（带重叠）
                if self.overlap > 0 and current_chunk:
                    # 保留最后几个句子作为重叠
                    overlap_text = "".join([s[0] for s in current_chunk[-2:]])
                    current_chunk = current_chunk[-2:]
                    current_length = len(overlap_text)
                    current_start = current_chunk[0][1]
                else:
                    current_chunk = []
                    current_length = 0
                    current_start = start_idx
            
            current_chunk.append((sentence, start_idx))
            current_length += sent_length
        
        # 处理最后一个块
        if current_chunk:
            chunk_text = "".join([s[0] for s in current_chunk])
            if chunk_text.strip():
                chunks.append(SemanticChunk(
                    text=chunk_text.strip(),
                    start_idx=current_start,
                    end_idx=current_start + len(chunk_text)
                ))
        
        return chunks
    
    def _embed(self, text: str) -> np.ndarray:
        """计算文本嵌入"""
        if not self.embedding_model:
            return None
        
        try:
            embedding = self.embedding_model.encode([text])[0]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.warning("Embedding failed", error=str(e))
            return None
    
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
