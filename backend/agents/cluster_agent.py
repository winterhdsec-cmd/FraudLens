from .base import BaseAgent, AgentConfig, AgentContext
import numpy as np
import hdbscan
import json
import re
from typing import Dict, Any, List
from collections import defaultdict
from sentence_transformers import SentenceTransformer, models
from transformers import AutoTokenizer, AutoModel


class ClusterAgent(BaseAgent):
    """团伙发现智能体"""

    def __init__(self, config: AgentConfig, llm_analyze=None):
        super().__init__(config)
        self.llm_analyze = llm_analyze
        self.embedder = None
        self.clusterer = None
        self.gang_centroids = {}  # 存储团伙中心向量 {gang_id: np.array}
        self._initialize_model()

    def _initialize_model(self):
        """初始化语义编码模型"""
        import os
        
        # 使用默认模型路径
        embedding_model_name = r"C:\Users\hd\Desktop\FraudLens\backend\bge-large-zh-v1.5"
        
        print(f"[工具D] 正在加载语义编码模型: {embedding_model_name}...")

        try:
            # 加载 tokenizer 和模型
            tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
            transformer_model = AutoModel.from_pretrained(embedding_model_name)

            # 创建 SentenceTransformer
            word_embedding_model = models.Transformer(embedding_model_name)
            pooling_model = models.Pooling(
                word_embedding_model.get_word_embedding_dimension(),
                pooling_mode_mean_tokens=True
            )

            self.embedder = SentenceTransformer(
                modules=[word_embedding_model, pooling_model]
            )
            print("✅ 通过 Transformers 加载成功")

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

        # 验证模型
        try:
            test_embedding = self.embedder.encode(["测试"], normalize_embeddings=True)
            print(f"✅ 模型验证成功，维度: {test_embedding.shape}")
        except Exception as e:
            print(f"⚠️ 模型验证警告: {e}")

        # HDBSCAN配置
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=2,
            min_samples=1,
            cluster_selection_epsilon=0.5,
            metric='euclidean',
            prediction_data=True
        )

        print("[ClusterAgent] 模型加载完毕。")

    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        执行团伙发现聚类
        """
        cases = payload.get('cases', [])
        self._log("INFO", f"开始对 {len(cases)} 个案件进行智能团伙聚类", context)

        if len(cases) < 2:
            self._log("INFO", "案件数量不足2，无法进行有效聚类", context)
            gangs = self._create_single_case_gangs(cases)
            return {"gangs": gangs}

        # 1. 提取语义指纹
        fingerprint_texts = self.extract_semantic_fingerprint(cases)
        self._log("INFO", f"已生成 {len(fingerprint_texts)} 个语义指纹", context)

        # 2. 转换为高维语义向量
        self._log("INFO", "正在进行语义向量编码", context)
        try:
            embeddings = self.embedder.encode(
                fingerprint_texts,
                normalize_embeddings=True,  # 归一化，便于计算余弦相似度
                show_progress_bar=False
            )
            self._log("INFO", f"向量编码完成，维度: {embeddings.shape}", context)
        except Exception as e:
            self._log("ERROR", f"语义向量编码失败: {e}", context)
            gangs = self._fallback_to_rule_based_clustering(cases, context)
            return {"gangs": gangs}

        # 3. HDBSCAN无监督聚类
        self._log("INFO", "正在执行HDBSCAN无监督聚类", context)
        cluster_labels = self.clusterer.fit_predict(embeddings)
        # cluster_labels: -1 表示噪声点（独立案件），>=0 表示团伙ID
        unique_labels = set(cluster_labels)
        noise_count = list(cluster_labels).count(-1)
        self._log("INFO", f"聚类完成。发现 {len(unique_labels) - (1 if -1 in unique_labels else 0)} 个潜在团伙，{noise_count} 个独立案件", context)

        # 4. 组织案件到团伙
        gangs_map = {}
        for idx, label in enumerate(cluster_labels):
            if label not in gangs_map:
                gangs_map[label] = []
            gangs_map[label].append(cases[idx])

        # 5. 为每个团伙生成智能画像
        self._log("INFO", "正在为各团伙生成智能画像", context)
        final_gangs = []
        for label, case_list in gangs_map.items():
            if label == -1:
                # 噪声点（独立案件），每个单独作为一个"团伙"处理
                for case in case_list:
                    solo_gang = self._create_solo_case_gang(case)
                    final_gangs.append(solo_gang)
            else:
                # 真正的团伙簇
                gang_profile = self._generate_gang_profile(label, case_list, context)
                final_gangs.append(gang_profile)

        self._log("INFO", f"聚类完成，共生成 {len(final_gangs)} 个团伙/独立案件单元", context)
        
        # 更新团伙中心向量
        self._update_gang_centroids(final_gangs)
        
        return {"gangs": final_gangs}

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
        new_embeddings = self.embedder.encode(fingerprints, normalize_embeddings=True)
        
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
                
                embeddings = self.embedder.encode(fingerprints, normalize_embeddings=True)
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
