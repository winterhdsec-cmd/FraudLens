"""
向量记忆 - 基于语义的检索记忆
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np


class VectorMemory:
    """
    向量记忆
    
    基于语义相似度的记忆检索，支持：
    - 案件语义检索
    - 对话历史检索
    - 知识检索
    """
    
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.memories: List[Dict[str, Any]] = []
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        if not self.embedding_model:
            # 如果没有模型，使用简单的 hash 向量（仅用于测试）
            return self._hash_embedding(text)
        
        return self.embedding_model.encode([text])[0]
    
    def _hash_embedding(self, text: str, dim: int = 768) -> np.ndarray:
        """简单的 hash 向量（用于没有模型时的 fallback）"""
        hash_val = abs(hash(text)) % (2**32)
        np.random.seed(hash_val)
        return np.random.randn(dim).astype(np.float32)
    
    def add_memory(self, content: str, metadata: Dict[str, Any] = None):
        """添加记忆"""
        embedding = self._get_embedding(content)
        
        memory = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.memories.append(memory)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似记忆"""
        if not self.memories:
            return []
        
        query_embedding = self._get_embedding(query)
        
        # 计算相似度
        similarities = []
        for memory in self.memories:
            memory_embedding = memory["embedding"]
            
            # 余弦相似度
            similarity = np.dot(query_embedding, memory_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(memory_embedding) + 1e-8
            )
            
            similarities.append((memory, float(similarity)))
        
        # 排序并返回 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for memory, similarity in similarities[:top_k]:
            result = {
                "content": memory["content"],
                "similarity": similarity,
                "metadata": memory["metadata"],
                "timestamp": memory["timestamp"]
            }
            results.append(result)
        
        return results
    
    def get_all_memories(self) -> List[Dict[str, Any]]:
        """获取所有记忆"""
        return [
            {
                "content": m["content"],
                "metadata": m["metadata"],
                "timestamp": m["timestamp"]
            }
            for m in self.memories
        ]
    
    def clear(self):
        """清空记忆"""
        self.memories.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化（不包含向量）"""
        return {
            "memories": [
                {
                    "content": m["content"],
                    "metadata": m["metadata"],
                    "timestamp": m["timestamp"]
                }
                for m in self.memories
            ]
        }
