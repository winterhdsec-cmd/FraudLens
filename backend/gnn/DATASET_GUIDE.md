# HAN 训练数据集指南

## 快速开始

### 1. 下载数据集（推荐 Elliptic Bitcoin）

#### Elliptic Bitcoin Dataset（推荐）
```bash
# 1. 访问 Kaggle 下载页面
https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

# 2. 下载数据集（需要 Kaggle 账号）
# 3. 解压到以下目录：
e:\FraudLens\backend\data\datasets\elliptic\
```

目录结构应该是：
```
elliptic/
├── elliptic_txs_features.csv      # 节点特征
├── elliptic_txs_edgelist.csv      # 边列表
└── elliptic_txs_classes.csv       # 节点标签
```

#### 其他数据集（可选）

**IEEE-CIS Fraud Detection**
```bash
# 下载：https://www.kaggle.com/c/ieee-cis-fraud-detection/data
# 解压到：e:\FraudLens\backend\data\datasets\ieee_cis\
```

**Credit Card Fraud Detection**
```bash
# 下载：https://www.kaggle.com/mlg-ulb/creditcardfraud
# 解压到：e:\FraudLens\backend\data\datasets\credit_card\
```

### 2. 运行训练

```bash
# 进入项目目录
cd e:\FraudLens\backend

# 使用 Elliptic 数据集训练
python gnn\train_han.py --dataset elliptic --epochs 100

# 使用 IEEE-CIS 数据集训练
python gnn\train_han.py --dataset ieee_cis --epochs 100

# 使用 Credit Card 数据集训练
python gnn\train_han.py --dataset credit_card --epochs 100
```

### 3. 查看训练结果

训练完成后，模型保存在：
```
e:\FraudLens\backend\gnn\models\
├── best_han_model.pt           # 最佳模型
├── final_han_model.pt          # 最终模型
└── training_results.json       # 训练结果
```

## 数据集对比

| 数据集 | 节点数 | 边数 | 欺诈比例 | 适合场景 |
|--------|--------|------|----------|----------|
| Elliptic Bitcoin | 203,769 | 234,355 | 4.5% | 图结构学习 |
| IEEE-CIS | 590,000+ | 自建 | 3.5% | 大规模训练 |
| Credit Card | 284,807 | 自建 | 0.17% | 不平衡数据 |

**推荐**：先用 Elliptic Bitcoin，因为它是现成的图结构数据。

## 训练参数说明

```bash
python gnn\train_han.py --help
```

- `--dataset`: 数据集名称 (elliptic, ieee_cis, credit_card)
- `--epochs`: 训练轮数（默认100）
- `--lr`: 学习率（默认0.001）
- `--batch-size`: 批次大小（默认256）

## 常见问题

### Q1: 下载数据集需要翻墙吗？
A: Kaggle 需要科学上网，如果没有条件，可以找同学帮忙下载。

### Q2: 训练需要GPU吗？
A: Elliptic 数据集较小，CPU 也能训练（约30分钟）。如果有 GPU 会更快。

### Q3: 训练失败怎么办？
A: 检查：
1. 数据集是否正确解压到指定目录
2. 文件是否完整（检查文件大小）
3. 查看 `logs/app.log` 中的详细错误信息

### Q4: 训练完成后怎么使用？
A: 系统会自动加载训练好的模型。重启后端服务即可：
```bash
python -m uvicorn main:app --reload --port 5004
```

## 学习路径建议

### 第一步：跑通代码（1天）
1. 下载 Elliptic 数据集
2. 运行训练脚本
3. 观察训练过程和结果

### 第二步：理解代码（2-3天）
1. 阅读 `train_han.py`，理解数据加载流程
2. 阅读 `han_model.py`，理解 HAN 结构
3. 尝试修改参数，观察效果变化

### 第三步：深入理解（1周）
1. 学习 PyTorch 基础
2. 理解图神经网络原理
3. 理解注意力机制
4. 尝试修改模型结构

### 第四步：实验优化（持续）
1. 尝试不同的超参数
2. 对比不同数据集的效果
3. 分析模型的性能指标
4. 写实验报告

## 推荐学习资源

### 视频
- [PyTorch 官方教程](https://pytorch.org/tutorials/)
- [图神经网络入门](https://www.bilibili.com/video/BV1rv411v78M)
- [注意力机制详解](https://www.bilibili.com/video/BV1Kt411p7xH)

### 论文
- [HAN: Hierarchical Attention Networks](https://arxiv.org/abs/1707.08267)
- [Graph Attention Networks](https://arxiv.org/abs/1710.10903)

### 代码
- [PyTorch Geometric](https://pyg.org/) - 图神经网络库
- [DGL](https://www.dgl.ai/) - 深度学习图库

## 下一步

训练完成后，你可以：
1. 在前端查看团伙检测结果
2. 对比 HAN 和 GraphSAGE 的效果
3. 尝试用训练好的模型进行推理
4. 写论文时展示实验结果

祝学习顺利！
