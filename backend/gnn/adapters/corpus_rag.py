"""
话术/类案向量库 RAG（B-L12，2026-08-04）

对标中正智云"知识图谱 + 向量库双底座"，为 FraudLens 补充**话术/类案检索**能力：
把公开反诈话术语料（合成生成器的语义种子）嵌入本地向量库，支持
"给一段案情 → 返回相似话术模式/类案"，补齐"无真值评测集"的教学短板。

设计纪律：
  - **本地优先**：默认用 TF-IDF（sklearn）+ 余弦相似度，零外部依赖、数据不出域；
    BGE（sentence-transformers）可用时自动升级为语义嵌入（可选，需本地模型）。
  - 不引云向量库（Milvus/Qdrant 等），保持公安院校部署的合规与轻量。
  - 语料以公开话术模板为种子（与 synthetic_data.SCRIPT_TEMPLATES 同源），
    并支持追加教学语料（add_documents）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# 内置公开话术种子（与 gnn/synthetic_data.SCRIPT_TEMPLATES 同源，避免循环依赖）
DEFAULT_CORPUS: List[Dict[str, str]] = [
    {"text": "您好，兼职刷单返利任务，垫付即返本金加佣金，操作简单日结工资。", "category": "刷单返利", "source": "public_corpus"},
    {"text": "无抵押低息贷款秒到账，需先下载 APP 认证，客服一对一办理。", "category": "虚假贷款", "source": "public_corpus"},
    {"text": "您购买的商品存在质量问题，将为您双倍理赔，请配合关闭自动扣费。", "category": "冒充客服", "source": "public_corpus"},
    {"text": "缘分不易，我在投资平台有内部渠道，跟着操作稳赚不赔，先小投入试水。", "category": "杀猪盘", "source": "public_corpus"},
    {"text": "这里是某某公安局，您名下账户涉嫌洗钱，需将资金转入安全账户配合清查。", "category": "冒充公检法", "source": "public_corpus"},
    {"text": "老师带单虚拟币/股票内幕消息，跟单复利翻倍，专属会员群每日荐股。", "category": "虚假投资", "source": "public_corpus"},
]


class CorpusRAG:
    """话术/类案向量检索。默认 TF-IDF；BGE 可用时自动升级。"""

    def __init__(self, corpus: Optional[List[Dict[str, str]]] = None, use_bge: bool = False):
        self.docs: List[Dict[str, str]] = list(corpus if corpus is not None else DEFAULT_CORPUS)
        self._bge = None
        self._tfidf = None
        self._matrix = None
        if use_bge or os.getenv("RAG_USE_BGE", "false").lower() == "true":
            self._try_load_bge()
        self._build_index()

    # ------------------------------------------------------------------ #
    # 索引构建
    # ------------------------------------------------------------------ #
    def _try_load_bge(self) -> None:
        """尝试加载 BGE 嵌入（可选）。失败则保持 TF-IDF 路径。"""
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv("RAG_BGE_MODEL", "BAAI/bge-small-zh-v1.5")
            self._bge = SentenceTransformer(model_name)
        except Exception as e:
            print(f"B-L12 BGE 加载失败，使用 TF-IDF: {e}")
            self._bge = None

    def _build_index(self) -> None:
        if self._bge is not None:
            self._bge_vectors = self._bge.encode([d["text"] for d in self.docs], normalize_embeddings=True)
        else:
            # 中文短文本用字符级 2-3 gram（整词 token 会因"刷单返利"vs"兼职刷单返利任务"
            # 等切分差异无法匹配；字符 n-gram 对中文鲁棒）
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
            self._matrix = self._tfidf.fit_transform([d["text"] for d in self.docs])

    def add_documents(self, docs: List[Dict[str, str]]) -> None:
        """追加教学语料（如学生自建话术库），并重建索引。"""
        self.docs.extend(docs)
        self._build_index()

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索 top-k 相似话术/类案。返回 [{text, category, source, score}]。"""
        if not query or not self.docs:
            return []
        top_k = max(1, min(top_k, len(self.docs)))

        if self._bge is not None:
            qv = self._bge.encode([query], normalize_embeddings=True)[0]
            import numpy as np
            scores = self._bge_vectors @ qv
        else:
            qv = self._tfidf.transform([query])
            from sklearn.metrics.pairwise import cosine_similarity
            scores = cosine_similarity(qv, self._matrix).ravel()

        order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[:top_k]
        return [
            {
                "text": self.docs[i]["text"],
                "category": self.docs[i].get("category", "未知"),
                "source": self.docs[i].get("source", "public_corpus"),
                "score": round(float(scores[i]), 4),
            }
            for i in order
        ]

    def suggest_category(self, query: str, top_k: int = 1) -> Optional[str]:
        """给一段案情 → 返回最相似的话术类别（教学 Lab2 用）。"""
        hits = self.search(query, top_k=top_k)
        return hits[0]["category"] if hits else None
