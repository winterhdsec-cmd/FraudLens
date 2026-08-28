"""
Embedding 模型管理器
支持多种中文 Embedding 模型：BGE、M3E、Text2Vec 等
"""
import os
import numpy as np
from typing import List, Optional, Union
from core.logger import logger
from core.config import settings


class EmbeddingModel:
    """Embedding 模型基类"""
    
    def __init__(self, model_name: str, dim: int):
        self.model_name = model_name
        self.dim = dim
        self.model = None
        
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """编码文本为向量"""
        raise NotImplementedError
    
    def encode_queries(self, queries: List[str]) -> np.ndarray:
        """编码查询（某些模型对查询和文档使用不同策略）"""
        return self.encode(queries)
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """编码文档"""
        return self.encode(documents)


class BGEEmbedding(EmbeddingModel):
    """BGE Embedding 模型（北京智源）"""
    
    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        super().__init__(model_name, dim=1024)
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # 优先使用本地模型路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_model_path = os.path.join(base_dir, "bge-large-zh-v1.5")
            
            if os.path.exists(local_model_path):
                logger.info("Loading BGE model from local path", path=local_model_path)
                self.model = SentenceTransformer(
                    local_model_path,
                    device="cpu"
                )
                logger.info("BGE model loaded successfully from local")
            else:
                logger.info("Local model not found, trying to load", model=self.model_name)
                cache_dir = os.path.join("data", "models", "embeddings")
                os.makedirs(cache_dir, exist_ok=True)
                
                self.model = SentenceTransformer(
                    self.model_name,
                    cache_folder=cache_dir,
                    device="cpu"
                )
                logger.info("BGE model loaded successfully", model=self.model_name)
            
        except ImportError:
            logger.warning("sentence-transformers not installed, using hash fallback")
            self.model = None
        except Exception as e:
            logger.error("Failed to load BGE model", error=str(e))
            self.model = None
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """编码文本"""
        if self.model is None:
            # 降级到 hash 向量
            return self._hash_fallback(texts)
        
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            # BGE 模型推荐对查询添加 instruction
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True  # 归一化，便于计算余弦相似度
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error("BGE encoding failed", error=str(e))
            return self._hash_fallback(texts)
    
    def encode_queries(self, queries: List[str]) -> np.ndarray:
        """编码查询（BGE 推荐添加 instruction）"""
        if self.model is None:
            return self._hash_fallback(queries)
        
        try:
            # BGE 模型推荐对查询添加 "为这个句子生成表示以用于检索：" 前缀
            instruction = "为这个句子生成表示以用于检索："
            queries_with_instruction = [instruction + q for q in queries]
            
            embeddings = self.model.encode(
                queries_with_instruction,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error("BGE query encoding failed", error=str(e))
            return self._hash_fallback(queries)
    
    def _hash_fallback(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Hash 向量降级方案（仅在 BGE 模型不可用时使用）

        重要：这是降级方案，检索结果无语义意义。首次调用时会记录 ERROR 级别告警，
        避免静默掩盖模型加载失败问题。
        """
        if not getattr(self, "_degraded_warned", False):
            logger.error(
                "Embedding 模型降级为 hash 随机向量，RAG 检索结果将无语义意义！"
                "请检查 BGE 模型路径或 sentence_transformers 安装。"
            )
            self._degraded_warned = True

        if isinstance(texts, str):
            texts = [texts]

        embeddings = []
        for text in texts:
            hash_val = abs(hash(text)) % (2**32)
            np.random.seed(hash_val)
            emb = np.random.randn(self.dim).astype(np.float32)
            # 归一化
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)

        return np.array(embeddings, dtype=np.float32)

    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式（hash 随机向量）"""
        return getattr(self, "_degraded_warned", False)


class M3EEmbedding(EmbeddingModel):
    """M3E Embedding 模型（Moka AI）"""
    
    def __init__(self, model_name: str = "moka-ai/m3e-large"):
        super().__init__(model_name, dim=768)
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("Loading M3E model", model=self.model_name)
            
            cache_dir = os.path.join("data", "models", "embeddings")
            os.makedirs(cache_dir, exist_ok=True)
            
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
                device="cpu"
            )
            
            logger.info("M3E model loaded successfully", model=self.model_name)
            
        except Exception as e:
            logger.error("Failed to load M3E model", error=str(e))
            self.model = None
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """编码文本"""
        if self.model is None:
            return self._hash_fallback(texts)
        
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error("M3E encoding failed", error=str(e))
            return self._hash_fallback(texts)
    
    def _hash_fallback(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Hash 向量降级方案"""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        for text in texts:
            hash_val = abs(hash(text)) % (2**32)
            np.random.seed(hash_val)
            emb = np.random.randn(self.dim).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
        
        return np.array(embeddings, dtype=np.float32)


class Text2VecEmbedding(EmbeddingModel):
    """Text2Vec Embedding 模型（shibing624）"""
    
    def __init__(self, model_name: str = "shibing624/text2vec-base-chinese"):
        super().__init__(model_name, dim=768)
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("Loading Text2Vec model", model=self.model_name)
            
            cache_dir = os.path.join("data", "models", "embeddings")
            os.makedirs(cache_dir, exist_ok=True)
            
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
                device="cpu"
            )
            
            logger.info("Text2Vec model loaded successfully", model=self.model_name)
            
        except Exception as e:
            logger.error("Failed to load Text2Vec model", error=str(e))
            self.model = None
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """编码文本"""
        if self.model is None:
            return self._hash_fallback(texts)
        
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error("Text2Vec encoding failed", error=str(e))
            return self._hash_fallback(texts)
    
    def _hash_fallback(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Hash 向量降级方案"""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        for text in texts:
            hash_val = abs(hash(text)) % (2**32)
            np.random.seed(hash_val)
            emb = np.random.randn(self.dim).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
        
        return np.array(embeddings, dtype=np.float32)


# 全局 Embedding 模型实例
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model(model_name: str = None) -> EmbeddingModel:
    """获取 Embedding 模型实例"""
    global _embedding_model
    
    if _embedding_model is not None:
        return _embedding_model
    
    # 使用配置中的模型名称
    if model_name is None:
        model_name = settings.EMBEDDING_MODEL
    
    logger.info("Initializing embedding model", model=model_name)
    
    # 根据模型名称选择实现
    if "bge" in model_name.lower():
        _embedding_model = BGEEmbedding(model_name)
    elif "m3e" in model_name.lower():
        _embedding_model = M3EEmbedding(model_name)
    elif "text2vec" in model_name.lower():
        _embedding_model = Text2VecEmbedding(model_name)
    else:
        # 默认使用 BGE
        logger.warning("Unknown model type, using BGE as default")
        _embedding_model = BGEEmbedding(model_name)
    
    return _embedding_model


def reset_embedding_model():
    """重置 Embedding 模型（用于测试）"""
    global _embedding_model
    _embedding_model = None
