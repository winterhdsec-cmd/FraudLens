import os
import sys
import numpy as np
import hdbscan
import json
import re
import warnings
from typing import Dict, Any, List
from collections import defaultdict
from sklearn.metrics import silhouette_score, davies_bouldin_score
from .base import BaseAgent, AgentConfig, AgentContext

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import engine


class ClusterAgent(BaseAgent):
    """团伙发现智能体（v2 - 接入 UMAP 降维 + 聚类质量评估）"""

    # UMAP 超参数（可根据数据规模动态调整）
    UMAP_CONFIG = {
        'n_neighbors': 15,
        'n_components': 30,
        'min_dist': 0.0,
        'metric': 'cosine'
    }

    def __init__(self, config: AgentConfig, llm_analyze=None):
        super().__init__(config)
        self.llm_analyze = llm_analyze
        self.clusterer = None
        self.umap_reducer = None
        self.gang_centroids = {}
        self._initialize_model()

    def _initialize_model(self):
        if engine is None:
            raise RuntimeError("BGE 引擎未初始化，请检查模型文件")
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=2,
            min_samples=1,
            cluster_selection_epsilon=0.5,
            metric='euclidean',
            prediction_data=True
        )
        self.umap_reducer = None
        print("[ClusterAgent] 共享 BGE 引擎就绪")

    def _encode(self, texts):
        return engine.encode(texts)

    def _init_umap(self):
        """延迟初始化 UMAP 安装延迟初始化解版本兼容问题）"""
        if self.umap_reducer is not None:
            return
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from umap import UMAP
            self.umap_reducer = UMAP(
                n_neighbors=self.UMAP_CONFIG['n_neighbors'],
                n_components=self.UMAP_CONFIG['n_components'],
                min_dist=self.UMAP_CONFIG['min_dist'],
                metric=self.UMAP_CONFIG['metric'],
                random_state=42
            )
            print("✅ UMAP 加载成功")
        except Exception as e:
            print(f"⚠️ UMAP 加载失败（将使用原始维度聚类）: {e}")
            self.umap_reducer = None

    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        执行团伙发现聚类（v2-stage聚类（BGE → UMAP → HDBSCAN）
        """
        cases = payload.get('cases', [])
        self._log("INFO", f"开始对 {len(cases)} 个案件进行智能团伙聚类", context)

        if len(cases) < 2:
            self._log("INFO", "案件数量不足2，无法进行有效聚类", context)
            gangs = self._create_single_case_gangs(cases)
            return {"gangs": gangs, "cluster_quality": {"info": "案件数量不足，无法聚类评估"}}

        # 1. 提取语义指纹
        fingerprint_texts = self.extract_semantic_fingerprint(cases)
        self._log("INFO", f"已生成 {len(fingerprint_texts)} 个语义指纹", context)

        # 2. BGE 语义向量编码
        self._log("INFO", "正在进行 BGE 语义向量编码", context)
        try:
            embeddings_1024 = self._encode(fingerprint_texts)
            self._log("INFO", f"BGE 编码完成，维度: {embeddings_1024.shape}", context)
        except Exception as e:
            self._log("ERROR", f"语义向量编码失败: {e}", context)
            gangs = self._fallback_to_rule_based_clustering(cases, context)
            return {"gangs": gangs, "cluster_quality": {"error": str(e)}}

        # 3. UMAP 降维（1024维 → 30维）
        self._log("INFO", f"正在执行 UMAP 降维 (1024→{self.UMAP_CONFIG['n_components']}维)...", context)
        self._init_umap()
        if self.umap_reducer is not None:
            try:
                embeddings_30d = self.umap_reducer.fit_transform(embeddings_1024)
                self._log("INFO", f"UMAP 降维完成，降维后维度: {embeddings_30d.shape}", context)
            except Exception as e:
                self._log("WARNING", f"UMAP 降维失败，回退到原始维度聚类: {e}", context)
                embeddings_30d = embeddings_1024
        else:
            self._log("INFO", "UMAP 不可用，使用原始 1024 维向量进行聚类", context)
            embeddings_30d = embeddings_1024

        # 4. HDBSCAN 无监督聚类（在降维后的空间进行）
        self._log("INFO", "正在执行 HDBSCAN 无监督聚类", context)
        cluster_labels = self.clusterer.fit_predict(embeddings_30d)

        unique_labels = set(cluster_labels)
        noise_count = list(cluster_labels).count(-1)
        gang_count = len(unique_labels) - (1 if -1 in unique_labels else 0)
        self._log("INFO", f"聚类完成。发现 {gang_count} 个潜在团伙，{noise_count} 个独立案件", context)

        # 5. 计算聚类质量指标
        self._log("INFO", "正在计算聚类质量指标", context)
        cluster_quality = self._evaluate_cluster_quality(embeddings_30d, cluster_labels, gang_count)

        # 6. 组织案件到团伙
        gangs_map = {}
        for idx, label in enumerate(cluster_labels):
            if label not in gangs_map:
                gangs_map[label] = []
            gangs_map[label].append(cases[idx])

        # 7. 为每个团伙生成智能画像
        self._log("INFO", "正在为各团伙生成智能画像", context)
        final_gangs = []
        for label, case_list in gangs_map.items():
            if label == -1:
                for case in case_list:
                    solo_gang = self._create_solo_case_gang(case)
                    final_gangs.append(solo_gang)
            else:
                gang_profile = self._generate_gang_profile(label, case_list, context)
                final_gangs.append(gang_profile)

        self._log("INFO", f"聚类完成，共生成 {len(final_gangs)} 个团伙/独立案件单元", context)

        self._update_gang_centroids(final_gangs)

        return {
            "gangs": final_gangs,
            "cluster_quality": cluster_quality
        }

    def _evaluate_cluster_quality(self, embeddings, labels, gang_count):
        """评估聚类质量，返回多维度指标"""
        quality = {
            "total_samples": len(labels),
            "gang_count": gang_count,
            "noise_count": int(list(labels).count(-1)),
            "noise_ratio": round(float(list(labels).count(-1)) / len(labels), 3) if len(labels) > 0 else 0
        }

        if gang_count > 1:
            try:
                mask = labels != -1
                if np.sum(mask) > 1 and len(set(labels[mask])) > 1:
                    sil = silhouette_score(embeddings[mask], labels[mask])
                    db = davies_bouldin_score(embeddings[mask], labels[mask])
                    quality["silhouette_score"] = round(float(sil), 4)
                    quality["davies_bouldin_score"] = round(float(db), 4)
                    if sil > 0.5:
                        quality["quality_label"] = "优秀"
                    elif sil > 0.25:
                        quality["quality_label"] = "良好"
                    elif sil > 0.1:
                        quality["quality_label"] = "一般"
                    else:
                        quality["quality_label"] = "需人工复核"
                else:
                    quality["silhouette_score"] = None
                    quality["davies_bouldin_score"] = None
                    quality["quality_label"] = "单簇或样本不足"
            except Exception as e:
                quality["error"] = str(e)
                quality["quality_label"] = "计算异常"
        else:
            quality["silhouette_score"] = None
            quality["davies_bouldin_score"] = None
            quality["quality_label"] = "无有效聚类"

        return quality

    async def incremental_cluster(self, new_cases: list, existing_gangs: list, context: AgentContext) -> dict:
        """
        增量聚类：将新案件动态归入已有团伙
        """
        self._log("INFO", f"开始增量聚类，{len(new_cases)}个新案件，{len(existing_gangs)}个现有团伙", context)
        
        # 如果没有现有团伙，直接返回新案件作为独立案件
        if not existing_gangs:
            self._log("INFO", "无现有团伙，新案件作为独立案件处理", context)
            solo_gangs = []
            for case in new_cases:
                solo_gangs.append(self._create_solo_case_gang(case))
            return {"gangs": solo_gangs}
        
        # 确保中心向量已初始化
        if not self.gang_centroids:
            self._update_gang_centroids(existing_gangs)
        
        # 生成新案件的语义向量
        fingerprints = self.extract_semantic_fingerprint(new_cases)
        new_embeddings = self._encode(fingerprints)
        
        # 为每个新案件寻找最相似的团伙
        updated_gangs = existing_gangs.copy()
        new_gang_id = max(int(g['gang_id'].split('_')[-1]) for g in existing_gangs) + 1
        
        for idx, case in enumerate(new_cases):
            case_embedding = new_embeddings[idx]
            max_similarity = 0.0
            target_gang_id = None
            
            # 计算与每个现有团伙的相似度
            for gang_id, centroid in self.gang_centroids.items():
                similarity = self._cosine_similarity(case_embedding, centroid)
                if similarity > max_similarity:
                    max_similarity = similarity
                    target_gang_id = gang_id
            
            if max_similarity > 0.75 and target_gang_id:
                # 归入现有团伙
                for gang in updated_gangs:
                    if gang['gang_id'] == target_gang_id:
                        gang['related_cases'].append({
                            'case_id': case.get('case_id', f'CASE_{new_gang_id}'),
                            'victim': case.get('victim', '未知'),
                            'amount': case.get('amount', '未知金额'),
                            'snippet': (case.get('ai_report', '')[:60] + '...') if case.get('ai_report') else '无详细片段',
                            'risk_level': case.get('risk_level', 'LOW')
                        })
                        gang['total_cases'] += 1
                        # 更新金额
                        gang['total_amount_involved'] = self._update_total_amount(gang, case)
                        self._log("INFO", f"新案件{case.get('case_id')}归入团伙{target_gang_id}，相似度={max_similarity:.2f}", context)
                        break
            else:
                # 创建新团伙
                new_gang = self._create_solo_case_gang(case)
                new_gang['gang_id'] = f'GANG_INC_{new_gang_id:03d}'
                new_gang['gang_name'] = f'增量识别团伙{new_gang_id}'
                updated_gangs.append(new_gang)
                new_gang_id += 1
                self._log("INFO", f"新案件{case.get('case_id')}创建新团伙，相似度={max_similarity:.2f}", context)
        
        # 更新中心向量
        self._update_gang_centroids(updated_gangs)
        
        self._log("INFO", f"增量聚类完成，共{len(updated_gangs)}个团伙", context)
        return {"gangs": updated_gangs}

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _update_gang_centroids(self, gangs: list) -> None:
        """更新团伙中心向量"""
        for gang in gangs:
            # 生成该团伙所有案件的语义指纹并计算中心
            cases = gang.get('related_cases', [])
            if cases:
                fingerprints = []
                for case in cases:
                    scam_type = case.get('scam_type', '未知类型')
                    keywords = case.get('keywords', [])
                    snippet = case.get('snippet', '')
                    fingerprint = f"诈骗类型：{scam_type}。关键词：{' '.join(keywords)}。摘要：{snippet}"
                    fingerprints.append(fingerprint)
                
                embeddings = self._encode(fingerprints)
                centroid = np.mean(embeddings, axis=0)
                self.gang_centroids[gang['gang_id']] = centroid

    def _update_total_amount(self, gang: dict, new_case: dict) -> str:
        """更新团伙总金额"""
        current_amount = gang.get('total_amount_involved', '0元')
        new_amount = new_case.get('amount', '0元')
        
        def parse_amount(s: str) -> float:
            match = re.search(r'(\d+(?:\.\d+)?)', s)
            if match:
                num = float(match.group(1))
                if '万' in s:
                    num *= 10000
                return num
            return 0.0
        
        total = parse_amount(current_amount) + parse_amount(new_amount)
        if total >= 10000:
            return f'{total / 10000:.1f}万元'
        return f'{int(total)}元'

    def extract_semantic_fingerprint(self, cases):
        """
        提取"电诈话术语义指纹"
        融合案件的多维信息，生成用于向量化的文本表征
        """
        fingerprints = []
        for case in cases:
            # 提取关键文本信息
            scam_type = case.get('scam_type', '未知类型')
            keywords = ' '.join(case.get('keywords', []))[:100]
            steps = ' '.join(case.get('steps', []))[:150]
            ai_report = case.get('ai_report', '')[:200]

            # 构建语义指纹文本（聚类质量的关键）
            fingerprint_text = (
                f"诈骗类型：{scam_type}。"
                f"关键词：{keywords}。"
                f"作案步骤：{steps}。"
                f"案情摘要：{ai_report}"
            )
            fingerprints.append(fingerprint_text)
        return fingerprints

    def _generate_gang_profile(self, gang_label, case_list, context):
        """
        生成团伙画像
        """
        if self.llm_analyze:
            return self._generate_gang_profile_via_llm(gang_label, case_list, context)
        else:
            return self._create_fallback_gang_profile(gang_label, case_list)

    def _generate_gang_profile_via_llm(self, gang_label, case_list, context):
        """
        调用大语言模型，分析团伙内案件的共性，生成智能画像
        """
        # 准备给LLM的上下文
        case_summaries = []
        for case in case_list:
            summary = (f"案件ID: {case.get('case_id', 'N/A')}, "
                       f"类型: {case.get('scam_type', '未知')}, "
                       f"风险: {case.get('risk_level', 'LOW')}, "
                       f"金额: {case.get('amount', '未知')}, "
                       f"关键词: {', '.join(case.get('keywords', ['无']))[:50]}")
            case_summaries.append(summary)

        cases_context = "\n".join(case_summaries)

        # 构建给LLM的提示词
        prompt = f"""你是一个资深反诈串并案专家。请分析以下 {len(case_list)} 个高度关联的诈骗案件，它们已被算法初步判定为同一团伙所为。

【案件列表】
{cases_context}

【任务】
请基于上述案件信息，为该犯罪团伙生成一份精准的"数字画像"：

1. **团伙代号**：起一个贴切、专业、易记的代号（例如"夜枭"、"幻影客服团"、"多卡宝洗钱组"）。请避免使用"团伙A"、"组1"这类无意义名称。
2. **核心特征**：提炼该团伙2-4个最显著的行为、技术或话术特征（例如："擅长利用屏幕共享软件远程操控"、"话术迭代快，每周更新剧本"、"使用虚拟货币结算，资金追踪难"）。
3. **主要诈骗类型**：总结其主要作案手法（例如："冒充金融平台客服注销贷款类"、"兼职刷单返利类"）。
4. **团伙整体风险等级**：综合所有案件的风险，给出整体评级（HIGH, MEDIUM, LOW）。
5. **简要描述**：用一两句话概括该团伙的作案模式。

请以严格的JSON格式输出，键名如下：gang_name, characteristics, primary_scam_type, risk_level, description。
不要输出任何其他解释性文字。
"""

        try:
            self._log("INFO", f"调用LLM生成团伙 {gang_label} 智能画像", context)
            response = self.llm_analyze.invoke(prompt)

            # 解析LLM返回的JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                llm_result = json.loads(json_match.group())
            else:
                # 如果LLM没返回纯JSON，尝试直接解析整个响应
                llm_result = json.loads(response)

            # 计算团伙的统计信息
            total_amount_yuan = 0
            highest_risk = 'LOW'
            for case in case_list:
                # 金额解析
                amount_str = case.get('amount', '0元')
                match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
                if match:
                    num = float(match.group(1))
                    if '万' in amount_str:
                        num *= 10000
                    total_amount_yuan += num
                # 风险等级
                case_risk = case.get('risk_level', 'LOW')
                if case_risk == 'HIGH':
                    highest_risk = 'HIGH'
                elif case_risk == 'MEDIUM' and highest_risk != 'HIGH':
                    highest_risk = 'MEDIUM'

            total_amount_wan = f'{total_amount_yuan / 10000:.1f}万元' if total_amount_yuan > 0 else '未知'
            risk_label = '高风险' if highest_risk == 'HIGH' else ('中风险' if highest_risk == 'MEDIUM' else '低风险')
            risk_type = 'danger' if highest_risk == 'HIGH' else ('warning' if highest_risk == 'MEDIUM' else 'info')

            # 成员规模估算
            member_estimate = '5-8 人'
            if total_amount_yuan > 200000:
                member_estimate = '15-20 人'
            elif total_amount_yuan > 50000:
                member_estimate = '10-15 人'
            if len(case_list) > 10:
                member_estimate = f'{member_estimate.split("-")[0]}+ 人'

            # 构建与前端兼容的gang对象
            gang_obj = {
                'gang_id': f'GANG_AI_{gang_label:03d}',
                'gang_name': llm_result.get('gang_name', f'智能识别团伙{gang_label}'),
                'risk_level': llm_result.get('risk_level', highest_risk),
                'risk_type': risk_type,
                'risk_label': risk_label,
                'confidence': min(95, 70 + len(case_list) * 3),
                'member_count_estimate': member_estimate,
                'active_time': '需进一步分析',
                'tech_level': '中',
                'script_type': llm_result.get('primary_scam_type', '混合型诈骗'),
                'total_cases': len(case_list),
                'total_amount_involved': total_amount_wan,
                'related_cases': [{
                    'case_id': c.get('case_id', f'CASE_{idx}'),
                    'victim': c.get('victim', '未知'),
                    'amount': c.get('amount', '未知金额'),
                    'snippet': (c.get('ai_report', '')[:60] + '...') if c.get('ai_report') else '无详细片段',
                    'risk_level': c.get('risk_level', 'LOW')
                } for idx, c in enumerate(case_list, 1)],
                'fingerprint': llm_result.get('characteristics', ['特征分析中']),
                'steps': case_list[0].get('steps', []) if case_list else [],
                'description': llm_result.get('description', ''),
                'network_nodes': self._generate_gang_network_nodes(gang_label, case_list, total_amount_yuan)
            }

            return gang_obj

        except Exception as e:
            self._log("ERROR", f"LLM生成团伙画像时出错: {e}", context)
            return self._create_fallback_gang_profile(gang_label, case_list)

    def _generate_gang_network_nodes(self, gang_label, case_list, total_amount):
        """为团伙生成网络节点数据"""
        network_nodes = []
        # 添加团伙中心节点
        network_nodes.append({
            'id': f'GANG_AI_{gang_label:03d}',
            'name': f'团伙{gang_label}',
            'type': 'gang',
            'value': total_amount,
            'risk_level': 'HIGH' if total_amount > 100000 else ('MEDIUM' if total_amount > 30000 else 'LOW')
        })
        # 添加关联的案件节点
        for case in case_list:
            amount_str = case.get('amount', '0元')
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            case_value = 0
            if match:
                case_value = float(match.group(1))
                if '万' in amount_str:
                    case_value *= 10000

            network_nodes.append({
                'id': case.get('case_id', f'UNKNOWN_{gang_label}'),
                'name': f"{case.get('case_id', '案件')}\n{case.get('victim', '未知')}",
                'type': 'case',
                'value': case_value,
                'gang_id': f'GANG_AI_{gang_label:03d}',
                'risk_level': case.get('risk_level', 'LOW')
            })

        return network_nodes

    def _create_solo_case_gang(self, case):
        """为独立案件（噪声点）创建一个虚拟的'团伙'，以便前端统一展示"""
        return {
            'gang_id': f'SOLO_{case.get("case_id", "UNKNOWN")}',
            'gang_name': f'独立案件 - {case.get("scam_type", "未知类型")}',
            'risk_level': case.get('risk_level', 'LOW'),
            'risk_type': 'danger' if case.get('risk_level') == 'HIGH' else (
                'warning' if case.get('risk_level') == 'MEDIUM' else 'info'),
            'risk_label': '高风险' if case.get('risk_level') == 'HIGH' else (
                '中风险' if case.get('risk_level') == 'MEDIUM' else '低风险'),
            'confidence': 60,
            'member_count_estimate': '1 人',
            'active_time': '未知',
            'tech_level': '未知',
            'script_type': case.get('scam_type', '未知'),
            'total_cases': 1,
            'total_amount_involved': case.get('amount', '未知金额'),
            'related_cases': [{
                'case_id': case.get('case_id', 'UNKNOWN'),
                'victim': case.get('victim', '未知'),
                'amount': case.get('amount', '未知金额'),
                'snippet': (case.get('ai_report', '')[:60] + '...') if case.get('ai_report') else '无详细片段',
                'risk_level': case.get('risk_level', 'LOW')
            }],
            'fingerprint': case.get('keywords', []),
            'steps': case.get('steps', []),
            'description': '此案件为独立个案，未与其他案件形成明显团伙模式。',
            'network_nodes': self._generate_solo_network_nodes(case)
        }

    def _generate_solo_network_nodes(self, case):
        """为独立案件生成网络节点数据"""
        amount_str = case.get('amount', '0元')
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        case_value = 0
        if match:
            case_value = float(match.group(1))
            if '万' in amount_str:
                case_value *= 10000

        return [{
            'id': case.get('case_id', 'UNKNOWN'),
            'name': f"独立案件\n{case.get('victim', '未知')}",
            'type': 'case',
            'value': case_value,
            'gang_id': f'SOLO_{case.get("case_id", "UNKNOWN")}',
            'risk_level': case.get('risk_level', 'LOW')
        }]

    def _create_fallback_gang_profile(self, gang_label, case_list):
        """LLM调用失败时，使用规则生成团伙画像的备用方案"""
        scam_types = [c.get('scam_type', '未知').split(' - ')[0] for c in case_list]
        primary_type = max(set(scam_types), key=scam_types.count) if scam_types else '未知类型'

        # 简单的命名规则
        gang_name_map = {
            '冒充电商': '幻影客服团',
            '刷单': '夜枭刷单组',
            '冒充公检法': '黑面判官团',
            '网络贷款': '伪金流水军',
            '投资理财': '杀猪盘狩猎者'
        }
        gang_name = gang_name_map.get(primary_type, f'{primary_type}犯罪团伙')

        # 计算统计信息
        total_amount_yuan = 0
        highest_risk = 'LOW'
        for case in case_list:
            amount_str = case.get('amount', '0元')
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            if match:
                num = float(match.group(1))
                if '万' in amount_str:
                    num *= 10000
                total_amount_yuan += num

            case_risk = case.get('risk_level', 'LOW')
            if case_risk == 'HIGH':
                highest_risk = 'HIGH'
            elif case_risk == 'MEDIUM' and highest_risk != 'HIGH':
                highest_risk = 'MEDIUM'

        total_amount_wan = f'{total_amount_yuan / 10000:.1f}万元' if total_amount_yuan > 0 else '未知'
        risk_label = '高风险' if highest_risk == 'HIGH' else ('中风险' if highest_risk == 'MEDIUM' else '低风险')
        risk_type = 'danger' if highest_risk == 'HIGH' else ('warning' if highest_risk == 'MEDIUM' else 'info')

        # 构建团伙对象
        return {
            'gang_id': f'GANG_FB_{gang_label:03d}',
            'gang_name': gang_name,
            'risk_level': highest_risk,
            'risk_type': risk_type,
            'risk_label': risk_label,
            'confidence': 75,
            'member_count_estimate': '5-8 人',
            'active_time': '需进一步分析',
            'tech_level': '中',
            'script_type': primary_type,
            'total_cases': len(case_list),
            'total_amount_involved': total_amount_wan,
            'related_cases': [{
                'case_id': c.get('case_id', f'CASE_{idx}'),
                'victim': c.get('victim', '未知'),
                'amount': c.get('amount', '未知金额'),
                'snippet': (c.get('ai_report', '')[:60] + '...') if c.get('ai_report') else '无详细片段',
                'risk_level': c.get('risk_level', 'LOW')
            } for idx, c in enumerate(case_list, 1)],
            'fingerprint': [f'擅长{primary_type}诈骗', '话术标准化'],
            'steps': case_list[0].get('steps', []) if case_list else [],
            'description': f'基于{primary_type}诈骗手法识别的犯罪团伙',
            'network_nodes': self._generate_gang_network_nodes(gang_label, case_list, total_amount_yuan)
        }

    def _fallback_to_rule_based_clustering(self, cases, context=None):
        """当智能聚类失败时，回退到基于规则（诈骗主类型）的聚类方法"""
        if context:
            self._log("INFO", "回退至基于规则的聚类", context)
        groups = defaultdict(list)
        for case in cases:
            main_type = case.get('scam_type', '未知类型').split(' - ')[0]
            groups[main_type].append(case)

        final_gangs = []
        for idx, (scam_type, case_list) in enumerate(groups.items()):
            final_gangs.append(self._create_fallback_gang_profile(idx, case_list))
        return final_gangs

    def _create_single_case_gangs(self, cases):
        """处理只有单个案件的情况"""
        if not cases:
            return []
        elif len(cases) == 1:
            return [self._create_solo_case_gang(cases[0])]
        else:
            # 理论上不会走到这里
            return []
