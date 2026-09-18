"""
冻卡门控：可插拔的"可学习逻辑回归门控"路径（REQ-S3.6，2026-08-05）

设计纪律：
- 默认门控仍是经验加权启发式（ablation.compute_gate_decision），可学习门控为"可选插件"，
  默认不启用，开关 gating_mode='learned' 才切；切换不退化既有行为（REQ-S3 不退化约束）。
- 纯 numpy 实现 logistic regression（无 torch / sklearn 依赖），可离线单测、可序列化。
- 训练数据为合成真值（合成诈骗团伙特征 + 诚实边界标注），不触碰真实涉密数据——
  契合论文"诚实边界"与 REQ-S3 门控可解释、可复现诉求。

特征与 gang_detector._generate_gang_info 的经验加权置信度完全一致：
  scale_norm  规模（团伙案件数/8，封顶 1）
  amount_norm 资金（团伙总涉案金额/100万，封顶 1）
  acc_norm    账户（关联收款账户数/3，封顶 1）
  reflux_flag 资金回流闭环（有=1 / 无=0）
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# 冻结决策文案（与 ablation / gang_detector 既有输出保持一致）
FREEZE = "建议冻结"
REVIEW = "待人工复核"

# 特征顺序（与 gang_detector._generate_gang_info 计算一致）
FEATURE_NAMES = ["scale_norm", "amount_norm", "acc_norm", "reflux_flag"]

# 默认可学习门控权重落地路径（首次惰性训练后落盘，后续直接加载，保证可复现）
_DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "learned_gate.json")


def build_features(scale_norm: float, amount_norm: float, acc_norm: float,
                   reflux_flag: Any) -> List[float]:
    """组装 4 维特征向量。"""
    return [
        float(scale_norm),
        float(amount_norm),
        float(acc_norm),
        1.0 if reflux_flag else 0.0,
    ]


def default_true_rule(feats: Sequence[float]) -> int:
    """合成真值的"诚实边界"——线性加权判定（与启发式同构，但权重可辩护）。

    设计：回流闭环是最强冻结信号（权重最高），其次涉案资金，再次团伙规模，
    账户数权重最低。这比启发式写死的 0.3/0.2/0.2/0.3 更强调"回流闭环"这一
    客观拓扑证据，是可学习门控要恢复的"数据驱动诚实边界"。

    线性区域 → 逻辑回归可近乎完美拟合（clean 时 0 偏离），体现"学系数"而非"学不动边界"。
    """
    scale_norm, amount_norm, acc_norm, reflux_flag = (list(feats) + [0, 0, 0, 0])[:4]
    score = 0.25 * scale_norm + 0.35 * amount_norm + 0.10 * acc_norm + 0.70 * reflux_flag
    return 1 if score >= 0.40 else 0


def generate_synthetic_training(n: int = 3000, seed: int = 42,
                                rule=None, noise: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
    """生成合成训练集 (X, y)。

    Args:
        n: 样本数
        seed: 随机种子（保证可复现）
        rule: 真值判定函数 (feats)->0/1，默认 default_true_rule
        noise: 标签噪声比例（模拟真实真值不完美，避免过拟合到确定边界）
    """
    rng = np.random.default_rng(seed)
    rule = rule or default_true_rule
    scale = rng.uniform(0.0, 1.0, n)
    amount = rng.uniform(0.0, 1.0, n)
    acc = rng.uniform(0.0, 1.0, n)
    reflux = rng.integers(0, 2, n).astype(float)
    X = np.stack([scale, amount, acc, reflux], axis=1)
    y = np.array([rule(row) for row in X], dtype=float)
    if noise > 0:
        flip = rng.uniform(0.0, 1.0, n) < noise
        y = np.where(flip, 1 - y, y)
    return X, y


class LogisticGate:
    """最小逻辑回归门控（numpy 实现，权重可序列化，torch/sklearn-free）。"""

    def __init__(self, weights: Optional[Sequence[float]] = None, bias: float = 0.0):
        self.weights = np.array(weights, dtype=float) if weights is not None else np.zeros(4)
        self.bias = float(bias)

    @staticmethod
    def _sigmoid(z: np.ndarray) -> np.ndarray:
        z = np.clip(z, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-z))

    def predict_proba(self, X) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        logits = X @ self.weights + self.bias
        return self._sigmoid(logits).reshape(-1)

    def decide(self, X, gate: float = 0.5) -> str:
        p = self.predict_proba(X)
        return FREEZE if (p >= gate).any() else REVIEW

    def fit(self, X, y, lr: float = 0.1, epochs: int = 200, pos_weight: float = 1.0):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1, 1)
        n = max(X.shape[0], 1)
        w = np.zeros(X.shape[1], dtype=float)
        b = 0.0
        for _ in range(epochs):
            logits = X @ w + b
            p = self._sigmoid(logits).reshape(-1, 1)
            error = p - y
            # 正类加权 BCE 梯度，缓解真值中冻结/复核类别不平衡
            error = np.where(y == 1, error * pos_weight, error)
            dw = (X.T @ error).ravel() / n  # 降为 1-D，避免 (4,) 与 (4,1) 广播成 (4,4)
            db = float(error.sum()) / n
            w -= lr * dw
            b -= lr * db
        self.weights = w
        self.bias = float(b)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"weights": self.weights.tolist(), "bias": self.bias,
                "feature_names": FEATURE_NAMES}

    def save(self, path: str):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "LogisticGate":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls(weights=d.get("weights"), bias=d.get("bias", 0.0))

    @classmethod
    def train_default(cls, n: int = 5000, seed: int = 42, noise: float = 0.01) -> "LogisticGate":
        X, y = generate_synthetic_training(n=n, seed=seed, noise=noise)
        # 真值中冻结(1)通常少于复核(0)，适度上加权正类
        pos = float(y.sum()) or 1.0
        neg = float((1 - y).sum()) or 1.0
        pos_weight = max(1.0, neg / pos)
        return cls().fit(X, y, lr=0.1, epochs=400, pos_weight=pos_weight)


def get_default_gate(model_path: Optional[str] = None) -> LogisticGate:
    """获取默认可学习门控：优先从磁盘加载已训练权重，否则现场训练并落盘。"""
    path = model_path or _DEFAULT_MODEL_PATH
    try:
        if os.path.exists(path):
            return LogisticGate.load(path)
    except Exception:
        pass
    gate = LogisticGate.train_default()
    try:
        gate.save(path)
    except Exception:
        pass
    return gate


def compute_learned_gate_decision(features, gate: Optional[LogisticGate] = None,
                                  threshold: float = 0.5) -> str:
    """用可学习逻辑回归门控给出冻结决策（freeze / review）。"""
    model = gate or get_default_gate()
    return model.decide(features, gate=threshold)
