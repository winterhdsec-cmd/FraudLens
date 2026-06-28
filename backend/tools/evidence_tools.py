"""
证据提取和验证工具
"""
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from .base import Tool, ToolInput, ToolOutput


class ExtractEvidenceInput(ToolInput):
    """提取证据输入"""
    text: str = Field(..., description="需要提取证据的文本")
    evidence_types: List[str] = Field(
        default=["bank_account", "phone", "id_card", "ip_address", "qq", "wechat"],
        description="要提取的证据类型"
    )


class ValidateEvidenceInput(ToolInput):
    """验证证据输入"""
    evidence_type: str = Field(..., description="证据类型")
    evidence_value: str = Field(..., description="证据值")


class ExtractEvidenceTool(Tool):
    """从文本中提取关键证据"""
    
    name = "extract_evidence"
    description = "从案件描述中提取关键证据，包括银行卡号、手机号、身份证号、IP地址、QQ号、微信号等"
    input_schema = ExtractEvidenceInput
    
    # 证据提取正则
    PATTERNS = {
        "bank_account": {
            "pattern": r'(?<!\d)\d{16,19}(?!\d)',
            "description": "银行卡号（16-19位数字）"
        },
        "phone": {
            "pattern": r'(?<!\d)1[3-9]\d{9}(?!\d)',
            "description": "手机号（11位）"
        },
        "id_card": {
            "pattern": r'(?<!\d)\d{17}[\dXx](?!\d)',
            "description": "身份证号（18位）"
        },
        "ip_address": {
            "pattern": r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)',
            "description": "IP地址"
        },
        "qq": {
            "pattern": r'(?<!\d)[1-9]\d{4,10}(?!\d)',
            "description": "QQ号（5-11位数字）"
        },
        "wechat": {
            "pattern": r'(?<![a-zA-Z0-9])[a-zA-Z][a-zA-Z0-9_-]{5,19}(?![a-zA-Z0-9])',
            "description": "微信号（6-20位，字母开头）"
        },
        "email": {
            "pattern": r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
            "description": "邮箱地址"
        },
        "url": {
            "pattern": r'https?://[^\s<>"]+|www\.[^\s<>"]+',
            "description": "URL链接"
        }
    }
    
    def execute(self, text: str, evidence_types: List[str] = None) -> ToolOutput:
        """执行提取"""
        try:
            if evidence_types is None:
                evidence_types = list(self.PATTERNS.keys())
            
            extracted = {}
            
            for evidence_type in evidence_types:
                if evidence_type not in self.PATTERNS:
                    continue
                
                pattern_info = self.PATTERNS[evidence_type]
                pattern = pattern_info["pattern"]
                
                matches = re.findall(pattern, text)
                
                # 去重
                unique_matches = list(set(matches))
                
                if unique_matches:
                    extracted[evidence_type] = {
                        "count": len(unique_matches),
                        "values": unique_matches,
                        "description": pattern_info["description"]
                    }
            
            result = {
                "extracted_evidence": extracted,
                "total_count": sum(len(v["values"]) for v in extracted.values())
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))


class ValidateEvidenceTool(Tool):
    """验证证据的有效性"""
    
    name = "validate_evidence"
    description = "验证提取的证据是否有效，例如检查银行卡号校验位、手机号格式等"
    input_schema = ValidateEvidenceInput
    
    def execute(self, evidence_type: str, evidence_value: str) -> ToolOutput:
        """执行验证"""
        try:
            validators = {
                "bank_account": self._validate_bank_account,
                "phone": self._validate_phone,
                "id_card": self._validate_id_card,
                "ip_address": self._validate_ip
            }
            
            validator = validators.get(evidence_type)
            
            if not validator:
                return ToolOutput(
                    success=True,
                    data={
                        "evidence_type": evidence_type,
                        "evidence_value": evidence_value,
                        "is_valid": True,
                        "message": "无验证规则，默认有效"
                    }
                )
            
            is_valid, message = validator(evidence_value)
            
            result = {
                "evidence_type": evidence_type,
                "evidence_value": evidence_value,
                "is_valid": is_valid,
                "message": message
            }
            
            return ToolOutput(success=True, data=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
    
    def _validate_bank_account(self, account: str) -> tuple:
        """验证银行卡号（Luhn算法）"""
        if not account.isdigit():
            return False, "银行卡号必须全是数字"
        
        if len(account) < 16 or len(account) > 19:
            return False, "银行卡号长度应为16-19位"
        
        # Luhn 校验
        total = 0
        reverse_digits = account[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        is_valid = total % 10 == 0
        message = "银行卡号校验通过" if is_valid else "银行卡号校验失败（Luhn算法）"
        return is_valid, message
    
    def _validate_phone(self, phone: str) -> tuple:
        """验证手机号"""
        if not phone.isdigit():
            return False, "手机号必须全是数字"
        
        if len(phone) != 11:
            return False, "手机号应为11位"
        
        if not phone.startswith("1"):
            return False, "手机号应以1开头"
        
        valid_prefixes = ["13", "14", "15", "16", "17", "18", "19"]
        if phone[:2] not in valid_prefixes:
            return False, f"手机号前缀无效，有效前缀: {', '.join(valid_prefixes)}"
        
        return True, "手机号格式正确"
    
    def _validate_id_card(self, id_card: str) -> tuple:
        """验证身份证号"""
        if len(id_card) != 18:
            return False, "身份证号应为18位"
        
        # 简单的格式验证
        if not id_card[:17].isdigit():
            return False, "身份证号前17位必须全是数字"
        
        if id_card[-1].upper() not in "0123456789X":
            return False, "身份证号最后一位必须是数字或X"
        
        return True, "身份证号格式正确"
    
    def _validate_ip(self, ip: str) -> tuple:
        """验证IP地址"""
        parts = ip.split(".")
        if len(parts) != 4:
            return False, "IP地址应有4段"
        
        for part in parts:
            if not part.isdigit():
                return False, "IP地址每段必须是数字"
            num = int(part)
            if num < 0 or num > 255:
                return False, "IP地址每段应在0-255之间"
        
        return True, "IP地址格式正确"
