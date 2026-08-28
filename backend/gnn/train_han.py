"""
HAN 异构图注意力网络训练脚本
使用开源欺诈检测数据集进行训练
"""
import os
import sys
import json
import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gnn.han_model import FraudHAN, GraphCLTrainer
from gnn.graph_builder import FraudGraphBuilder
from core.logger import logger


class DatasetLoader:
    """数据集加载器"""
    
    @staticmethod
    def load_elliptic_bitcoin(data_dir: str) -> Tuple[Dict, Dict]:
        """
        加载 Elliptic Bitcoin 数据集
        
        数据集结构：
        - elliptic_txs_features.csv: 节点特征
        - elliptic_txs_edgelist.csv: 边列表
        - elliptic_txs_classes.csv: 节点标签
        
        Args:
            data_dir: 数据目录
            
        Returns:
            nodes: 节点信息字典
            edges: 边信息字典
        """
        logger.info("Loading Elliptic Bitcoin dataset", data_dir=data_dir)
        
        # 加载特征
        features_path = os.path.join(data_dir, "elliptic_txs_features.csv")
        features_df = pd.read_csv(features_path, header=None)
        
        # 第一列是txId，后面是特征
        node_ids = features_df[0].tolist()
        features = features_df.iloc[:, 1:].values
        
        # 加载边
        edges_path = os.path.join(data_dir, "elliptic_txs_edgelist.csv")
        edges_df = pd.read_csv(edges_path, header=None)
        edges_list = list(zip(edges_df[0].tolist(), edges_df[1].tolist()))
        
        # 加载标签
        classes_path = os.path.join(data_dir, "elliptic_txs_classes.csv")
        classes_df = pd.read_csv(classes_path)
        
        # 创建节点字典
        nodes = {}
        for i, tx_id in enumerate(node_ids):
            tx_id_str = str(tx_id)
            label_row = classes_df[classes_df['txId'] == tx_id]
            
            if len(label_row) > 0:
                label = label_row.iloc[0]['class']
                # 2:  illicit (欺诈)
                # 1:  licit (合法)
                # unknown: 未知
                is_fraud = (label == '2')
            else:
                is_fraud = False
            
            nodes[tx_id_str] = {
                'id': tx_id_str,
                'type': 'transaction',
                'features': features[i].tolist(),
                'is_fraud': is_fraud,
                'amount': float(features[i][0]) if len(features[i]) > 0 else 0.0,
                'timestamp': int(features[i][1]) if len(features[i]) > 1 else 0
            }
        
        # 创建边字典
        edges = {}
        for i, (src, dst) in enumerate(edges_list):
            edge_id = f"edge_{i}"
            edges[edge_id] = {
                'id': edge_id,
                'source': str(src),
                'target': str(dst),
                'type': 'transfer',
                'weight': 1.0
            }
        
        logger.info(
            "Dataset loaded",
            nodes=len(nodes),
            edges=len(edges),
            fraud_count=sum(1 for n in nodes.values() if n['is_fraud'])
        )
        
        return nodes, edges
    
    @staticmethod
    def load_ieee_cis(data_dir: str) -> Tuple[Dict, Dict]:
        """
        加载 IEEE-CIS Fraud Detection 数据集
        
        需要先将数据转换为图结构
        
        Args:
            data_dir: 数据目录
            
        Returns:
            nodes: 节点信息字典
            edges: 边信息字典
        """
        logger.info("Loading IEEE-CIS dataset", data_dir=data_dir)
        
        # 加载交易数据
        train_path = os.path.join(data_dir, "train_transaction.csv")
        test_path = os.path.join(data_dir, "test_transaction.csv")
        
        if os.path.exists(train_path):
            train_df = pd.read_csv(train_path)
        else:
            raise FileNotFoundError(f"Training data not found: {train_path}")
        
        if os.path.exists(test_path):
            test_df = pd.read_csv(test_path)
            # 合并训练和测试数据
            df = pd.concat([train_df, test_df], ignore_index=True)
        else:
            df = train_df
        
        # 创建节点（交易）
        nodes = {}
        for _, row in df.iterrows():
            tx_id = str(row['TransactionID'])
            nodes[tx_id] = {
                'id': tx_id,
                'type': 'transaction',
                'features': row.drop(['TransactionID', 'isFraud']).fillna(0).tolist(),
                'is_fraud': bool(row.get('isFraud', 0)),
                'amount': float(row.get('TransactionAmt', 0)),
                'timestamp': int(row.get('TransactionDT', 0))
            }
        
        # 创建边（基于共同属性）
        edges = {}
        edge_count = 0
        
        # 基于相同ProductCD创建边
        product_groups = df.groupby('ProductCD')
        for product, group in product_groups:
            if len(group) > 1:
                tx_ids = group['TransactionID'].tolist()
                for i in range(len(tx_ids) - 1):
                    edge_id = f"edge_{edge_count}"
                    edges[edge_id] = {
                        'id': edge_id,
                        'source': str(tx_ids[i]),
                        'target': str(tx_ids[i + 1]),
                        'type': 'same_product',
                        'weight': 1.0
                    }
                    edge_count += 1
        
        logger.info(
            "Dataset loaded",
            nodes=len(nodes),
            edges=len(edges),
            fraud_count=sum(1 for n in nodes.values() if n['is_fraud'])
        )
        
        return nodes, edges
    
    @staticmethod
    def load_credit_card(data_path: str) -> Tuple[Dict, Dict]:
        """
        加载 Credit Card Fraud Detection 数据集
        
        需要转换为图结构
        
        Args:
            data_path: CSV文件路径
            
        Returns:
            nodes: 节点信息字典
            edges: 边信息字典
        """
        logger.info("Loading Credit Card dataset", data_path=data_path)
        
        df = pd.read_csv(data_path)
        
        # 创建节点（交易）
        nodes = {}
        for _, row in df.iterrows():
            tx_id = str(row['Time']) + "_" + str(row.index)
            nodes[tx_id] = {
                'id': tx_id,
                'type': 'transaction',
                'features': row.drop(['Time', 'Class']).tolist(),
                'is_fraud': bool(row['Class']),
                'amount': float(row['Amount']),
                'timestamp': int(row['Time'])
            }
        
        # 创建边（基于时间接近性）
        edges = {}
        edge_count = 0
        
        # 按时间排序
        sorted_nodes = sorted(nodes.items(), key=lambda x: x[1]['timestamp'])
        
        # 连接时间接近的交易
        for i in range(len(sorted_nodes) - 1):
            tx1_id, tx1_data = sorted_nodes[i]
            tx2_id, tx2_data = sorted_nodes[i + 1]
            
            # 如果时间差小于阈值，创建边
            time_diff = abs(tx2_data['timestamp'] - tx1_data['timestamp'])
            if time_diff < 3600:  # 1小时内
                edge_id = f"edge_{edge_count}"
                edges[edge_id] = {
                    'id': edge_id,
                    'source': tx1_id,
                    'target': tx2_id,
                    'type': 'temporal',
                    'weight': 1.0 / (time_diff + 1)
                }
                edge_count += 1
        
        logger.info(
            "Dataset loaded",
            nodes=len(nodes),
            edges=len(edges),
            fraud_count=sum(1 for n in nodes.values() if n['is_fraud'])
        )
        
        return nodes, edges


class HANTrainer:
    """HAN 训练器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化训练器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "datasets"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.model_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models"
        )
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.graph_builder = FraudGraphBuilder()
        self.han_model = None
        self.trainer = None
        
    def train(
        self,
        dataset_name: str,
        epochs: int = 100,
        lr: float = 0.001,
        batch_size: int = 256
    ) -> Dict:
        """
        训练 HAN 模型
        
        Args:
            dataset_name: 数据集名称 (elliptic, ieee_cis, credit_card)
            epochs: 训练轮数
            lr: 学习率
            batch_size: 批次大小
            
        Returns:
            训练结果字典
        """
        logger.info("Starting HAN training", dataset=dataset_name, epochs=epochs)
        
        # 1. 加载数据集
        nodes, edges = self._load_dataset(dataset_name)
        
        if len(nodes) == 0:
            raise ValueError("No nodes loaded from dataset")
        
        # 2. 构建异构图
        logger.info("Building heterogeneous graph")
        cases = self._nodes_to_cases(nodes, edges)
        graph = self.graph_builder.build_graph(cases)
        
        if len(graph.nodes) == 0:
            raise ValueError("Graph has no nodes after building")
        
        # 3. 准备训练数据
        features = self.graph_builder.get_node_features()
        adj = self.graph_builder.get_adjacency_matrix()
        
        if features is None or len(features) == 0:
            raise ValueError("No features extracted from graph")
        
        features_tensor = torch.FloatTensor(features)
        adj_tensor = torch.FloatTensor(adj)
        
        # 4. 创建标签（用于监督训练）
        labels = self._extract_labels(nodes, graph)
        labels_tensor = torch.LongTensor(labels)
        
        # 5. 创建并训练 HAN 模型
        logger.info("Creating HAN model")
        in_dim = features.shape[1]
        
        self.han_model = FraudHAN(
            in_dim=in_dim,
            hidden_dim=128,
            out_dim=64,
            num_heads=4,
            num_classes=2,  # 二分类：欺诈/合法
            dropout=0.3
        )
        
        # 6. 训练
        logger.info("Starting training")
        self.trainer = GraphCLTrainer(
            model=self.han_model,
            lr=lr,
            weight_decay=1e-5
        )
        
        # 划分训练集和测试集
        num_nodes = len(labels)
        indices = torch.randperm(num_nodes)
        train_size = int(0.8 * num_nodes)
        train_idx = indices[:train_size]
        test_idx = indices[train_size:]
        
        # 训练循环
        best_val_acc = 0.0
        train_losses = []
        val_accs = []
        
        for epoch in range(epochs):
            # 训练
            self.han_model.train()
            self.trainer.optimizer.zero_grad()
            
            # 前向传播
            embeddings = self.han_model(features_tensor, {"default": adj_tensor})
            logits = self.han_model.classifier(embeddings)
            
            # 计算训练损失
            train_loss = torch.nn.functional.cross_entropy(
                logits[train_idx],
                labels_tensor[train_idx]
            )
            
            train_loss.backward()
            self.trainer.optimizer.step()
            
            train_losses.append(train_loss.item())
            
            # 验证
            self.han_model.eval()
            with torch.no_grad():
                val_embeddings = self.han_model(features_tensor, {"default": adj_tensor})
                val_logits = self.han_model.classifier(val_embeddings)
                val_preds = val_logits.argmax(dim=1)
                val_acc = (val_preds[test_idx] == labels_tensor[test_idx]).float().mean().item()
            
            val_accs.append(val_acc)
            
            # 保存最佳模型
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                self._save_model("best_han_model.pt")
            
            # 打印进度
            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs}",
                    train_loss=f"{train_loss.item():.4f}",
                    val_acc=f"{val_acc:.4f}",
                    best_val_acc=f"{best_val_acc:.4f}"
                )
        
        # 7. 保存最终模型
        self._save_model("final_han_model.pt")
        
        # 8. 返回训练结果
        results = {
            "dataset": dataset_name,
            "epochs": epochs,
            "num_nodes": num_nodes,
            "num_edges": len(edges),
            "num_fraud": sum(labels),
            "best_val_acc": best_val_acc,
            "final_val_acc": val_accs[-1] if val_accs else 0.0,
            "train_losses": train_losses,
            "val_accs": val_accs,
            "model_path": os.path.join(self.model_dir, "best_han_model.pt")
        }
        
        logger.info("Training completed", results=results)
        
        # 保存训练结果
        results_path = os.path.join(self.model_dir, "training_results.json")
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return results
    
    def _load_dataset(self, dataset_name: str) -> Tuple[Dict, Dict]:
        """加载数据集"""
        loader = DatasetLoader()
        
        if dataset_name == "elliptic":
            data_dir = os.path.join(self.data_dir, "elliptic")
            if not os.path.exists(data_dir):
                raise FileNotFoundError(
                    f"Elliptic dataset not found. Please download from "
                    f"https://www.kaggle.com/datasets/ellipticco/elliptic-data-set "
                    f"and extract to {data_dir}"
                )
            return loader.load_elliptic_bitcoin(data_dir)
        
        elif dataset_name == "ieee_cis":
            data_dir = os.path.join(self.data_dir, "ieee_cis")
            if not os.path.exists(data_dir):
                raise FileNotFoundError(
                    f"IEEE-CIS dataset not found. Please download from "
                    f"https://www.kaggle.com/c/ieee-cis-fraud-detection/data "
                    f"and extract to {data_dir}"
                )
            return loader.load_ieee_cis(data_dir)
        
        elif dataset_name == "credit_card":
            data_path = os.path.join(self.data_dir, "credit_card", "creditcard.csv")
            if not os.path.exists(data_path):
                raise FileNotFoundError(
                    f"Credit Card dataset not found. Please download from "
                    f"https://www.kaggle.com/mlg-ulb/creditcardfraud "
                    f"and extract to {os.path.dirname(data_path)}"
                )
            return loader.load_credit_card(data_path)
        
        else:
            raise ValueError(f"Unknown dataset: {dataset_name}")
    
    def _nodes_to_cases(self, nodes: Dict, edges: Dict) -> List[Dict]:
        """将节点和边转换为案件格式"""
        cases = []
        
        for node_id, node_data in nodes.items():
            case = {
                'id': node_id,
                'title': f"Transaction {node_id}",
                'description': f"Transaction with amount {node_data.get('amount', 0)}",
                'type': 'transaction',
                'amount': node_data.get('amount', 0),
                'victimName': f"User_{node_id}",
                'victimPhone': f"phone_{node_id}",
                'date': datetime.fromtimestamp(node_data.get('timestamp', 0)).strftime('%Y-%m-%d'),
                'status': '已立案',
                'scam_type': '欺诈' if node_data.get('is_fraud') else '合法',
                'risk_level': '高' if node_data.get('is_fraud') else '低',
                'ai_report': '',
                'evidence': [],
                'related_cases': []
            }
            cases.append(case)
        
        return cases
    
    def _extract_labels(self, nodes: Dict, graph) -> List[int]:
        """提取节点标签"""
        labels = []
        
        for node_id in graph.nodes():
            if node_id in nodes:
                labels.append(1 if nodes[node_id].get('is_fraud') else 0)
            else:
                labels.append(0)
        
        return labels
    
    def _save_model(self, filename: str):
        """保存模型"""
        model_path = os.path.join(self.model_dir, filename)
        torch.save({
            'model_state_dict': self.han_model.state_dict(),
            'model_config': {
                'in_dim': self.han_model.in_dim,
                'hidden_dim': self.han_model.hidden_dim,
                'out_dim': self.han_model.out_dim,
                'num_heads': self.han_model.num_heads,
                'num_classes': self.han_model.num_classes
            }
        }, model_path)
        logger.info("Model saved", path=model_path)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train HAN for fraud detection")
    parser.add_argument(
        "--dataset",
        type=str,
        default="elliptic",
        choices=["elliptic", "ieee_cis", "credit_card"],
        help="Dataset name"
    )
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("HAN 异构图注意力网络训练")
    print("=" * 60)
    print(f"数据集: {args.dataset}")
    print(f"训练轮数: {args.epochs}")
    print(f"学习率: {args.lr}")
    print("=" * 60)
    
    trainer = HANTrainer()
    
    try:
        results = trainer.train(
            dataset_name=args.dataset,
            epochs=args.epochs,
            lr=args.lr,
            batch_size=args.batch_size
        )
        
        print("\n" + "=" * 60)
        print("训练完成！")
        print("=" * 60)
        print(f"节点数: {results['num_nodes']}")
        print(f"边数: {results['num_edges']}")
        print(f"欺诈样本: {results['num_fraud']}")
        print(f"最佳验证准确率: {results['best_val_acc']:.4f}")
        print(f"最终验证准确率: {results['final_val_acc']:.4f}")
        print(f"模型保存路径: {results['model_path']}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n训练失败: {str(e)}")
        logger.error("Training failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
