from .base import BaseAgent, AgentConfig, AgentContext
import re
from typing import Dict, Any, List

# 预定义诈骗关键词列表
SCAM_KEYWORDS = [
    '安全账户', '刷单', '公检法', '验证码', '转账', '银行卡', '密码',
    '贷款', '征信', '退款', '客服', '保证金', '解冻', '资金核查',
    '内幕消息', '高收益', '投资', '提现', '充值', 'VIP', '会员',
    '手续费', '押金', '中奖', '领奖', '快递', '包裹', '货到付款'
]


class PreprocessAgent(BaseAgent):
    """数据预处理智能体"""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def process(self, payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        处理原始消息和平台数据
        """
        self._log("INFO", "开始数据预处理", context)
        
        raw_messages = payload.get('messages', [])
        platform_data = payload.get('platform_data', {})
        
        # 标准化消息格式
        standardized_messages = self.standardize_message_format(raw_messages)
        
        # 脱敏处理
        desensitized_messages = self.desensitize_messages(standardized_messages)
        
        # 提取平台关键线索
        platform_clues = self.extract_key_info_from_platform(platform_data)
        
        # 如果有平台线索，添加到消息中
        if platform_clues:
            desensitized_messages.append({
                "content": "\n".join(platform_clues),
                "sender": "system",
                "timestamp": None
            })
        
        # 计算数据质量评分
        data_quality = self._calculate_data_quality(raw_messages, desensitized_messages, platform_clues, context)
        
        self._log("INFO", f"预处理完成，处理了{len(desensitized_messages)}条消息", context)
        
        return {
            "standardized_messages": desensitized_messages,
            "platform_clues": platform_clues,
            "text_messages": [msg['content'] for msg in desensitized_messages],
            "data_quality": data_quality
        }

    def clean_text(self, text: str) -> str:
        """清理文本中的冗余字符和格式"""
        if not isinstance(text, str):
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        return text

    def standardize_message_format(self, raw_messages: List[Any]) -> List[Dict[str, Any]]:
        """标准化消息格式，统一为 {content, sender, timestamp} 结构"""
        standardized = []
        for msg in raw_messages:
            if isinstance(msg, str):
                content = self.clean_text(msg)
                if content:
                    standardized.append({"content": content, "sender": "unknown", "timestamp": None})
            elif isinstance(msg, dict):
                content = msg.get('content', msg.get('text', ''))
                content = self.clean_text(content)
                if content:
                    sender = msg.get('sender', msg.get('role', 'unknown'))
                    timestamp = msg.get('time', msg.get('timestamp', None))
                    standardized.append({"content": content, "sender": sender, "timestamp": timestamp})
            elif isinstance(msg, dict) and msg.get('type') == 'image':
                ocr_text = "【图片内容】检测到转账或验证码信息"
                standardized.append({"content": ocr_text, "sender": "unknown", "timestamp": None})
        return standardized

    def desensitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """脱敏处理，保护个人隐私信息"""
        desensitized = []
        for msg in messages:
            content = msg['content']
            # 脱敏手机号
            content = re.sub(r'(1[3-9]\d{9})', '138****8888', content)
            # 脱敏身份证号
            content = re.sub(r'(\d{6})\d{8}(\d{4})', '\1********\2', content)
            # 脱敏银行卡号
            content = re.sub(r'(\d{4})\d{8,12}(\d{4})', '\1****\2', content)
            # 脱敏姓名
            content = re.sub(r'([张王李赵刘陈杨黄周吴]\w{1,2})', '**', content)
            
            desensitized.append({
                **msg,
                "content": content
            })
        return desensitized

    def extract_key_info_from_platform(self, data: Dict[str, Any]) -> List[str]:
        """从平台数据中提取关键线索（诈骗电话、APP、网址等）"""
        platform_info = []
        fields_to_extract = [
            ('诈骗类型', 'scam_type'),
            ('诈骗电话', 'phone'),
            ('APP 应用程序', 'app_name'),
            ('诈骗网址', 'url'),
            ('诈骗交易账户', 'account')
        ]
        for label, key in fields_to_extract:
            value = data.get(key)
            if value and value not in ['请选择', '请填写', '']:
                # 脱敏处理
                if key == 'phone':
                    value = re.sub(r'(1[3-9]\d{9})', '138****8888', value)
                elif key == 'account':
                    value = re.sub(r'(\d{4})\d{8,12}(\d{4})', '\1****\2', value)
                platform_info.append(f"【平台关键线索】{label}: {value}")
        return platform_info

    def _calculate_data_quality(self, raw_messages: List[Any], cleaned_messages: List[Dict[str, Any]], 
                                platform_clues: List[str], context: AgentContext) -> Dict[str, Any]:
        """
        计算数据质量评分
        """
        total_raw_count = len(raw_messages)
        valid_clean_count = len(cleaned_messages)
        
        # 完整性：有效消息数/总消息数
        if total_raw_count > 0:
            completeness = valid_clean_count / total_raw_count
        else:
            completeness = 0.0
        
        # 可疑度：命中诈骗关键词的消息数/总消息数
        suspicious_count = 0
        for msg in cleaned_messages:
            content = msg.get('content', '')
            for keyword in SCAM_KEYWORDS:
                if keyword in content:
                    suspicious_count += 1
                    break
        
        if valid_clean_count > 0:
            suspiciousness = suspicious_count / valid_clean_count
        else:
            suspiciousness = 0.0
        
        # 是否有平台线索
        has_platform_clues = len(platform_clues) > 0
        
        # 综合评分
        overall_score = (completeness + suspiciousness) / 2
        
        data_quality = {
            "completeness": round(completeness, 2),
            "suspiciousness": round(suspiciousness, 2),
            "has_platform_clues": has_platform_clues,
            "overall_score": round(overall_score, 2),
            "valid_message_count": valid_clean_count,
            "total_message_count": total_raw_count,
            "suspicious_message_count": suspicious_count
        }
        
        # 记录日志
        self._log("INFO", f"数据质量评分完成: 完整性={completeness:.2f}, 可疑度={suspiciousness:.2f}, 综合评分={overall_score:.2f}", context)
        
        return data_quality
