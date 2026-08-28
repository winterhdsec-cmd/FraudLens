import numpy as np
import hdbscan
from tools.response import logger
from core.embedding import get_embedding_model


class FraudAnalysisEngine:
    """反诈分析引擎（话术语义聚类）。

    工程整改(T1): 不再用 transformers 独立加载第二份 BGE 模型,
    而是复用 core.embedding 的全局单例(get_embedding_model),
    从而保证全系统只有一份 Embedding 模型(消除双加载器技术债 P1)。
    若 Embedding 模型不可用,core.embedding 内部会走 hash 降级,引擎不崩。
    """

    def __init__(self):
        try:
            self._embedder = get_embedding_model()
            logger.info("反诈引擎已复用 core.embedding 单例 BGE 模型（双加载器已收敛）")
        except Exception as e:
            logger.warning(f"反诈引擎获取 Embedding 模型失败,将走 hash 降级: {e}")
            self._embedder = None

    def encode(self, texts, normalize=True, batch_size=32):
        """批量编码:委托给 core.embedding 单例,保证全系统只有一份 BGE。"""
        if not texts:
            return np.array([])

        if self._embedder is None:
            self._embedder = get_embedding_model()

        embeddings = self._embedder.encode(texts, batch_size=batch_size)

        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1e-9, norms)
            embeddings = embeddings / norms

        return embeddings

    def analyze(self, messages):
        """
        Web 接口调用的主函数
        """
        if not messages:
            return {"labels": [], "stats": {}}
        # 👇【新增】强制要求至少 10 条消息
        logger.info(f"正在处理 {len(messages)} 条消息...")
        if len(messages) < 10:
            logger.warning(f"消息数量不足 ({len(messages)} < 10)，拒绝分析")
            return {
                "labels": [],
                "stats": {
                    "error": f"请输入至少 10 条聊天记录才能进行分析（当前仅 {len(messages)} 条）"
                }
            }

        logger.info(f"正在处理 {len(messages)} 条消息...")

        # 1. 向量化（复用 core.embedding 单例）
        embeddings = self.encode(messages)

        if embeddings.shape[0] == 0:
            return {"labels": [], "stats": {"error": "无有效数据"}}

        # 2. 聚类 (HDBSCAN)
        # 调整参数以适应小样本测试
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=2,
            min_samples=1,
            metric='euclidean',
            cluster_selection_method='eom'
        )

        logger.info("正在进行 HDBSCAN 聚类...")
        labels = clusterer.fit_predict(embeddings)

        # 3. 统计
        stats = {}
        unique_labels = set(labels)
        for label in unique_labels:
            count = int(np.sum(labels == label))
            if label == -1:
                stats["正常/杂音"] = count
            else:
                stats[f"疑似团伙-{label}"] = count

        return {
            "labels": [int(l) for l in labels],
            "stats": stats
        }


# 全局初始化（失败不再让 engine 为 None,而是优雅降级）
try:
    engine = FraudAnalysisEngine()
except Exception as e:
    logger.info("=" * 50)
    logger.warning("警告：反诈引擎初始化失败！")
    logger.info(f"原因：{e}")
    logger.info("请检查 backend/bge-large-zh-v1.5 文件夹是否正确。")
    logger.info("=" * 50)
    engine = None
