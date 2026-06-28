"""
初始化反诈知识库 - 注入反诈领域知识文档
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import logger
from rag.knowledge_base import get_knowledge_base


def seed_knowledge_base():
    """注入反诈领域初始知识"""
    kb = get_knowledge_base()

    # 检查是否已有文档
    stats = kb.get_stats()
    if stats["total_documents"] > 0:
        logger.info(f"Knowledge base already has {stats['total_documents']} documents, skipping seed")
        return

    # 加载预定义文档
    docs_path = os.path.join(os.path.dirname(__file__), "data", "knowledge_base", "anti_fraud_docs.json")

    if os.path.exists(docs_path):
        with open(docs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for doc in data.get("documents", []):
            kb.add_document(
                content=doc["content"],
                source=doc.get("source", "反诈知识库"),
                metadata=doc.get("metadata", {})
            )

        kb.save()
        logger.info(f"Knowledge base seeded with {len(data['documents'])} documents")
    else:
        # 如果没有预定义文档文件，使用内置文档
        builtin_docs = [
            {
                "content": "电信网络诈骗是指以非法占有为目的，利用电信网络技术手段，通过远程、非接触等方式，诈骗公私财物的行为。常见类型包括：冒充公检法诈骗、刷单诈骗、贷款诈骗、杀猪盘诈骗、冒充客服诈骗、虚假投资诈骗等。",
                "source": "反诈基础知识",
                "metadata": {"category": "基础知识", "type": "definition"}
            },
            {
                "content": "冒充公检法诈骗特征：1. 来电显示为境外号码或虚拟号码；2. 自称公安局、检察院、法院工作人员；3. 声称受害人涉嫌洗钱、诈骗等犯罪活动；4. 要求将资金转入'安全账户'进行审查；5. 要求保密，不得告诉家人朋友。防范要点：公检法机关不会通过电话要求转账汇款，不存在'安全账户'。",
                "source": "诈骗手法分析",
                "metadata": {"category": "诈骗手法", "type": "analysis"}
            },
            {
                "content": "刷单诈骗识别特征：1. 通过社交媒体、招聘网站发布兼职信息；2. 以'足不出户、日进斗金'等话术吸引受害人；3. 初期小额返利建立信任；4. 后期要求大额投入并以各种理由拒绝返现；5. 诱导受害人下载虚假APP进行操作。",
                "source": "诈骗手法分析",
                "metadata": {"category": "诈骗手法", "type": "analysis"}
            },
            {
                "content": "杀猪盘诈骗特征：1. 通过社交软件、婚恋网站建立感情关系；2. 日常嘘寒问暖获取信任；3. 诱导受害人参与虚假投资理财、网络赌博；4. 初期小额盈利引诱大额投入；5. 最终平台无法提现，对方消失。",
                "source": "诈骗手法分析",
                "metadata": {"category": "诈骗手法", "type": "analysis"}
            },
            {
                "content": "诈骗案件关联分析要素：1. 资金流向分析：追踪涉案银行账户、第三方支付平台的资金转移路径；2. 通讯信息关联：分析涉案电话号码、社交账号的关联关系；3. 作案手法相似度：比对不同案件的诈骗话术、流程特征；4. 时间空间关联：分析案件发生的时间规律和地域分布。",
                "source": "案件分析方法",
                "metadata": {"category": "分析方法", "type": "methodology"}
            },
            {
                "content": "诈骗团伙识别指标：1. 组织架构：存在明确的组织者、话务员、取款手等角色分工；2. 资金归集：多个案件的资金最终流向同一账户或关联账户；3. 作案工具：使用相同的诈骗平台、话术脚本、技术工具；4. 作案时间：案件发生时间呈现规律性或连续性；5. 地域聚集：团伙成员或作案窝点集中在特定区域。",
                "source": "团伙识别方法",
                "metadata": {"category": "分析方法", "type": "methodology"}
            },
            {
                "content": "反诈预警信号：1. 陌生来电要求转账汇款；2. 网络兼职要求先垫付资金；3. 投资理财承诺高额回报；4. 网购退款要求提供银行卡信息；5. 贷款要求支付前期费用；6. 公检法电话要求资金审查；7. 中奖信息要求缴纳手续费；8. 亲友紧急借钱但无法核实身份。",
                "source": "预警信号",
                "metadata": {"category": "预警", "type": "warning"}
            },
            {
                "content": "证据提取要点：1. 通话记录：保存来电号码、通话时间、通话时长；2. 聊天记录：截图保存完整的聊天对话；3. 转账记录：保存银行流水、第三方支付记录；4. 网站APP：保存诈骗网站URL、APP安装包；5. 短信邮件：保存诈骗短信、邮件内容；6. 其他证据：录音、视频等。",
                "source": "证据收集指南",
                "metadata": {"category": "取证", "type": "guide"}
            }
        ]

        for doc in builtin_docs:
            kb.add_document(
                content=doc["content"],
                source=doc.get("source", "反诈知识库"),
                metadata=doc.get("metadata", {})
            )

        kb.save()
        logger.info(f"Knowledge base seeded with {len(builtin_docs)} builtin documents")

    return kb.get_stats()


if __name__ == "__main__":
    stats = seed_knowledge_base()
    print(f"Knowledge base stats: {stats}")
