"""
查询改写模块 - 提升检索质量
支持 HyDE、Multi-Query、Step-back 等高级策略
"""
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from core.llm_client import wrap_messages, get_llm_model  # G2 脱敏 / 统一模型名出口
from core.logger import logger
from core.config import settings


class QueryRewriter:
    """
    查询改写器 - 多种策略提升检索效果
    
    策略：
    1. HyDE (Hypothetical Document Embeddings) - 生成假设性答案用于检索
    2. Multi-Query - 生成多个查询变体
    3. Step-back - 退一步思考，生成更抽象的查询
    """
    
    def __init__(self, llm_client: Optional[AsyncOpenAI] = None):
        """
        初始化改写器
        
        Args:
            llm_client: LLM 客户端（如果为 None，使用规则改写）
        """
        self.llm = llm_client
        
        logger.info("QueryRewriter initialized", has_llm=llm_client is not None)
    
    async def rewrite(
        self,
        query: str,
        strategy: str = "hyde",
        num_variants: int = 3
    ) -> List[str]:
        """
        查询改写
        
        Args:
            query: 原始查询
            strategy: 改写策略 - "hyde", "multi_query", "step_back", "rule_based"
            num_variants: 生成变体数量
        
        Returns:
            改写后的查询列表
        """
        if strategy == "hyde":
            return await self.hyde_rewrite(query)
        elif strategy == "multi_query":
            return await self.multi_query_rewrite(query, num_variants)
        elif strategy == "step_back":
            return await self.step_back_rewrite(query)
        elif strategy == "rule_based":
            return self.rule_based_rewrite(query)
        else:
            return [query]
    
    async def hyde_rewrite(self, query: str) -> List[str]:
        """
        HyDE 策略 - 生成假设性答案用于检索
        
        原理：让 LLM 先生成一个假设性答案，用答案做检索
        优势：答案的语义更接近文档内容
        """
        if not self.llm:
            return [query]
        
        try:
            prompt = f"""请根据以下问题，生成一个简短的假设性答案（2-3句话）。
即使你不确定确切答案，也请基于常识给出合理的推测。

问题：{query}

假设性答案："""
            
            response = await self.llm.chat.completions.create(
                model=get_llm_model(),
                messages=wrap_messages([{"role": "user", "content": prompt}]),
                temperature=0.7,
                max_tokens=200
            )
            
            hypothetical_answer = response.choices[0].message.content.strip()
            
            # 返回原始查询和假设性答案
            return [query, hypothetical_answer]
            
        except Exception as e:
            logger.warning("HyDE rewrite failed", error=str(e))
            return [query]
    
    async def multi_query_rewrite(self, query: str, num_variants: int = 3) -> List[str]:
        """
        Multi-Query 策略 - 生成多个查询变体
        
        原理：从不同角度重述查询，提高召回率
        """
        if not self.llm:
            return [query]
        
        try:
            prompt = f"""请将以下问题改写为 {num_variants} 个不同的版本，保持语义相同但表达方式不同。
每行一个版本，不要编号。

原始问题：{query}

改写版本："""
            
            response = await self.llm.chat.completions.create(
                model=get_llm_model(),
                messages=wrap_messages([{"role": "user", "content": prompt}]),
                temperature=0.8,
                max_tokens=300
            )
            
            variants_text = response.choices[0].message.content.strip()
            variants = [v.strip() for v in variants_text.split('\n') if v.strip()]
            
            # 确保包含原始查询
            if query not in variants:
                variants.insert(0, query)
            
            return variants[:num_variants + 1]
            
        except Exception as e:
            logger.warning("Multi-query rewrite failed", error=str(e))
            return [query]
    
    async def step_back_rewrite(self, query: str) -> List[str]:
        """
        Step-back 策略 - 退一步思考
        
        原理：生成更抽象、更宽泛的查询，捕捉更广泛的上下文
        """
        if not self.llm:
            return [query]
        
        try:
            prompt = f"""请将以下具体问题转化为一个更抽象、更宽泛的问题。
例如：
- 具体："Python 中如何实现快速排序？" → 抽象："排序算法的实现方法"
- 具体："React 的 useEffect 钩子怎么用？" → 抽象："React Hooks 的使用场景"

具体问题：{query}

抽象问题："""
            
            response = await self.llm.chat.completions.create(
                model=get_llm_model(),
                messages=wrap_messages([{"role": "user", "content": prompt}]),
                temperature=0.6,
                max_tokens=150
            )
            
            abstract_query = response.choices[0].message.content.strip()
            
            # 返回原始查询和抽象查询
            return [query, abstract_query]
            
        except Exception as e:
            logger.warning("Step-back rewrite failed", error=str(e))
            return [query]
    
    def rule_based_rewrite(self, query: str) -> List[str]:
        """
        规则改写策略（无 LLM 时使用）
        
        策略：
        1. 同义词替换
        2. 查询扩展
        3. 关键词提取
        """
        variants = [query]
        
        # 同义词替换
        synonyms = {
            "诈骗": ["欺诈", "骗局", "电信欺诈"],
            "案件": ["案例", "事件"],
            "团伙": ["团伙", "犯罪集团", "诈骗团伙"],
            "受害人": ["受害者", "被害人"],
            "金额": ["数额", "损失金额"]
        }
        
        for keyword, syns in synonyms.items():
            if keyword in query:
                for syn in syns[:2]:  # 最多替换前2个同义词
                    variant = query.replace(keyword, syn)
                    variants.append(variant)
        
        # 查询扩展（添加相关关键词）
        if "诈骗" in query and "类型" not in query:
            variants.append(query + " 类型 手法")
        
        if "团伙" in query and "特征" not in query:
            variants.append(query + " 特征 识别")
        
        # 去重
        variants = list(dict.fromkeys(variants))
        
        return variants[:5]  # 最多返回5个变体


async def rewrite_and_merge(
    query: str,
    knowledge_base,
    rewriter: QueryRewriter,
    strategy: str = "hyde",
    top_k: int = 5
) -> List:
    """
    改写查询并合并检索结果
    
    Args:
        query: 原始查询
        knowledge_base: 知识库实例
        rewriter: 查询改写器
        strategy: 改写策略
        top_k: 每个查询返回的结果数
    
    Returns:
        合并后的检索结果列表
    """
    # 改写查询
    query_variants = await rewriter.rewrite(query, strategy=strategy)
    
    logger.info("Query rewritten", original=query, variants=len(query_variants))
    
    # 对每个变体进行检索
    all_results = []
    seen_chunk_ids = set()
    
    for variant in query_variants:
        results = await knowledge_base.search_async(variant, top_k=top_k, strategy="hybrid")
        
        for result in results:
            chunk_id = result.document.chunk_id
            if chunk_id not in seen_chunk_ids:
                all_results.append(result)
                seen_chunk_ids.add(chunk_id)
    
    # 按分数排序
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    logger.info("Search results merged", total=len(all_results), unique=len(seen_chunk_ids))
    
    return all_results[:top_k]
