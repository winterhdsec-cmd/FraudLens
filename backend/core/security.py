"""
安全模块 - Prompt注入防护和输入验证
参考：OWASP LLM Top 10, Agent安全最佳实践
"""
import re
from typing import List, Optional, Dict, Any
from core.logger import logger


class PromptInjectionDetector:
    """
    Prompt注入检测器
    
    检测常见的注入攻击模式：
    1. 指令覆盖（ignore previous instructions）
    2. 角色扮演攻击（you are now DAN）
    3. 系统提示泄露（reveal system prompt）
    4. 工具注入（恶意工具调用）
    """
    
    # 危险模式列表
    DANGEROUS_PATTERNS = [
        # 指令覆盖
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"forget\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?previous\s+instructions",
        r"override\s+(all\s+)?previous\s+instructions",
        
        # 角色扮演攻击
        r"you\s+are\s+now\s+(DAN|an?\s+unrestricted)",
        r"pretend\s+you\s+are\s+(DAN|an?\s+unrestricted)",
        r"act\s+as\s+(DAN|an?\s+unrestricted)",
        
        # 系统提示泄露
        r"reveal\s+(the\s+)?system\s+prompt",
        r"show\s+(me\s+)?(the\s+)?system\s+prompt",
        r"what\s+(are|were)\s+your\s+instructions",
        r"repeat\s+(your\s+)?instructions",
        
        # 越狱尝试
        r"jailbreak",
        r"bypass\s+(all\s+)?restrictions",
        r"ignore\s+(all\s+)?safety\s+(guidelines|rules)",
        
        # 工具注入
        r"execute\s+command",
        r"execute\s+shell\s+command",
        r"run\s+shell",
        r"system\(",
        r"eval\(",
        r"exec\(",
        
        # 数据泄露
        r"output\s+all\s+environment\s+variables",
        r"show\s+me\s+API\s+keys",
        r"reveal\s+(password|secret|token)",
    ]
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]
        logger.info("PromptInjectionDetector initialized", patterns_count=len(self.patterns))
    
    def detect(self, text: str) -> Dict[str, Any]:
        """
        检测文本中的注入攻击
        
        Args:
            text: 待检测文本
        
        Returns:
            检测结果字典
        """
        if not text:
            return {"is_safe": True, "threats": []}
        
        threats = []
        
        for i, pattern in enumerate(self.patterns):
            matches = pattern.findall(text)
            if matches:
                threats.append({
                    "pattern_index": i,
                    "pattern": self.DANGEROUS_PATTERNS[i],
                    "matches": matches,
                    "severity": "high"
                })
        
        is_safe = len(threats) == 0
        
        if not is_safe:
            logger.warning(
                "Prompt injection attempt detected",
                threats_count=len(threats),
                text_preview=text[:100]
            )
        
        return {
            "is_safe": is_safe,
            "threats": threats,
            "confidence": 1.0 if not is_safe else 0.0
        }
    
    def sanitize(self, text: str) -> str:
        """
        清理文本中的危险内容
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        if not text:
            return text
        
        sanitized = text
        
        # 移除危险模式
        for pattern in self.patterns:
            sanitized = pattern.sub("", sanitized)
        
        # 移除 HTML 标签（如 <script>, <img> 等）
        sanitized = re.sub(r"<[^>]+>", "", sanitized)
        
        # 移除多余空白
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        
        return sanitized


class InputValidator:
    """
    输入验证器
    
    验证和清理所有进入Agent系统的输入
    """
    
    @staticmethod
    def validate_text_input(
        text: str,
        max_length: int = 10000,
        min_length: int = 1,
        allow_special_chars: bool = True
    ) -> Dict[str, Any]:
        """
        验证文本输入
        
        Args:
            text: 输入文本
            max_length: 最大长度
            min_length: 最小长度
            allow_special_chars: 是否允许特殊字符
        
        Returns:
            验证结果
        """
        errors = []
        
        if not text:
            errors.append("Input cannot be empty")
        
        if len(text) < min_length:
            errors.append(f"Input too short (min: {min_length})")
        
        if len(text) > max_length:
            errors.append(f"Input too long (max: {max_length})")
        
        if not allow_special_chars:
            # 检查是否包含危险特殊字符
            dangerous_chars = ["<", ">", "{", "}", "|", "\\", "^", "~", "`"]
            for char in dangerous_chars:
                if char in text:
                    errors.append(f"Dangerous character not allowed: {char}")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "sanitized": text.strip() if is_valid else None
        }
    
    @staticmethod
    def validate_tool_input(tool_input: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具输入参数
        
        Args:
            tool_input: 工具输入参数
            schema: 参数schema定义
        
        Returns:
            验证结果
        """
        errors = []
        
        # 检查必需参数
        required_params = schema.get("required", [])
        for param in required_params:
            if param not in tool_input:
                errors.append(f"Missing required parameter: {param}")
        
        # 检查参数类型
        properties = schema.get("properties", {})
        for param, value in tool_input.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type and not InputValidator._check_type(value, expected_type):
                    errors.append(f"Invalid type for {param}: expected {expected_type}")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors
        }
    
    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """检查值类型是否匹配"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # 未知类型，跳过检查
        
        return isinstance(value, expected)
    
    def sanitize_input(self, text: str) -> str:
        """
        清理输入文本
        
        Args:
            text: 输入文本
        
        Returns:
            清理后的文本
        """
        if not text:
            return text
        
        # 移除HTML标签
        sanitized = re.sub(r"<[^>]+>", "", text)
        
        # 移除SQL注入常见模式
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
            r"(--|;|/\*|\*/)",
        ]
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
        
        # 移除多余空白
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        
        return sanitized


class ToolCallValidator:
    """
    工具调用验证器
    
    验证工具调用的安全性和合法性
    """
    
    # 危险工具名称模式
    DANGEROUS_TOOL_PATTERNS = [
        r"shell",
        r"exec",
        r"eval",
        r"system",
        r"os\.",
        r"subprocess",
        r"delete_file",
        r"drop_table",
        r"rm\s+-rf",
    ]
    
    def __init__(self, allowed_tools: Optional[List[str]] = None):
        """
        初始化工具调用验证器
        
        Args:
            allowed_tools: 允许的工具列表（白名单）
        """
        self.allowed_tools = set(allowed_tools) if allowed_tools else None
        self.dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_TOOL_PATTERNS
        ]
        
        logger.info(
            "ToolCallValidator initialized",
            allowed_tools=allowed_tools,
            dangerous_patterns=len(self.dangerous_patterns)
        )
    
    def validate_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具调用
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
        
        Returns:
            验证结果
        """
        errors = []
        
        # 1. 检查工具名称是否在白名单中
        if self.allowed_tools and tool_name not in self.allowed_tools:
            errors.append(f"Tool not in allowed list: {tool_name}")
        
        # 2. 检查工具名称是否包含危险模式
        for pattern in self.dangerous_patterns:
            if pattern.search(tool_name):
                errors.append(f"Dangerous tool name pattern detected: {tool_name}")
        
        # 3. 检查输入参数中的危险内容
        input_str = str(tool_input)
        for pattern in self.dangerous_patterns:
            if pattern.search(input_str):
                errors.append(f"Dangerous pattern in tool input: {pattern.pattern}")
        
        is_safe = len(errors) == 0
        
        if not is_safe:
            logger.warning(
                "Unsafe tool call detected",
                tool_name=tool_name,
                errors=errors
            )
        
        return {
            "is_safe": is_safe,
            "errors": errors,
            "tool_name": tool_name
        }
    
    def add_allowed_tool(self, tool_name: str):
        """添加允许的工具"""
        if self.allowed_tools is None:
            self.allowed_tools = set()
        self.allowed_tools.add(tool_name)
    
    def remove_allowed_tool(self, tool_name: str):
        """移除允许的工具"""
        if self.allowed_tools and tool_name in self.allowed_tools:
            self.allowed_tools.remove(tool_name)


# 全局安全组件实例
_prompt_injection_detector: Optional[PromptInjectionDetector] = None
_input_validator: Optional[InputValidator] = None
_tool_call_validator: Optional[ToolCallValidator] = None


def get_prompt_injection_detector() -> PromptInjectionDetector:
    """获取Prompt注入检测器实例"""
    global _prompt_injection_detector
    if _prompt_injection_detector is None:
        _prompt_injection_detector = PromptInjectionDetector()
    return _prompt_injection_detector


def get_input_validator() -> InputValidator:
    """获取输入验证器实例"""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator


def get_tool_call_validator(allowed_tools: Optional[List[str]] = None) -> ToolCallValidator:
    """获取工具调用验证器实例"""
    global _tool_call_validator
    if _tool_call_validator is None:
        _tool_call_validator = ToolCallValidator(allowed_tools)
    return _tool_call_validator
