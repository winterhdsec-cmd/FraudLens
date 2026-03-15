import os
import torch
import numpy as np
import hdbscan
from transformers import AutoTokenizer, AutoModel


class FraudAnalysisEngine:
    def __init__(self):
        # 【关键步骤 1】确定模型绝对路径
        # 假设模型文件夹和 tools.py 在同一级目录 (backend/bge-large-zh-v1.5)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_name = "bge-large-zh-v1.5"
        model_path = os.path.join(base_dir, model_name)

        print(f"🔍 正在检查模型路径: {model_path}")

        # 【关键步骤 2】严格检查文件是否存在，避免模糊报错
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"❌ 错误：找不到模型文件夹 '{model_path}'。\n"
                f"请确认：\n"
                f"1. 'bge-large-zh-v1.5' 文件夹是否在 backend 目录下？\n"
                f"2. 文件夹内是否有 'config.json' 和 'pytorch_model.bin' (或 .safetensors)？"
            )

        # 检查关键文件
        required_files = ['config.json', 'tokenizer.json']
        # 兼容 .bin 或 .safetensors
        has_weights = any(f for f in os.listdir(model_path) if f.endswith('.bin') or f.endswith('.safetensors'))

        if not all(os.path.exists(os.path.join(model_path, f)) for f in required_files) or not has_weights:
            raise FileNotFoundError(f"❌ 错误：模型文件夹不完整，缺少关键配置文件或权重文件。")

        print("✅ 路径检查通过，正在加载模型...")

        try:
            # 【关键步骤 3】加载 Tokenizer 和 Model
            # 使用 local_files_only=True 强制读取本地，防止联网尝试失败
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True
            )
            self.model = AutoModel.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.float32,  # 强制使用 float32 避免精度问题
                device_map="cpu"  # 明确指定用 CPU (如果有显卡可改为 'cuda')
            )
            self.model.eval()  # 设置为评估模式
            print("✅ 模型加载成功！引擎就绪。")

        except Exception as e:
            print(f"❌ 模型加载失败：{e}")
            print("💡 建议：尝试重新下载模型文件夹，确保文件未损坏。")
            raise e

    def encode(self, texts):
        """
        复用你 Demo 中的 Mean Pooling 逻辑
        """
        if not texts:
            return np.array([])

        # 编码
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512
        )

        # 移动到模型所在设备 (CPU)
        # 如果上面 device_map 用了 cuda，这里也要 .to('cuda')
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        # Mean Pooling (核心逻辑)
        attention_mask = inputs['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        mean_pooled = sum_embeddings / sum_mask

        # 转回 CPU 并转为 numpy
        return mean_pooled.cpu().numpy()

    def analyze(self, messages):
        """
        Web 接口调用的主函数
        """
        if not messages:
            return {"labels": [], "stats": {}}
        # 👇【新增】强制要求至少 10 条消息
        print(f"📝 正在处理 {len(messages)} 条消息...")
        if len(messages) < 10:
            print(f"⚠️ 消息数量不足 ({len(messages)} < 10)，拒绝分析")
            return {
                "labels": [],
                "stats": {
                    "error": f"请输入至少 10 条聊天记录才能进行分析（当前仅 {len(messages)} 条）"
                }
            }

        print(f"📝 正在处理 {len(messages)} 条消息...")

        # 1. 向量化
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

        print("🧠 正在进行 HDBSCAN 聚类...")
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


# 全局初始化
try:
    engine = FraudAnalysisEngine()
except Exception as e:
    print("=" * 50)
    print("⚠️  警告：反诈引擎初始化失败！")
    print(f"原因：{e}")
    print("请检查 backend/bge-large-zh-v1.5 文件夹是否正确。")
    print("=" * 50)
    engine = None