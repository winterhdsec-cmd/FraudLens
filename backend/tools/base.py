"""
工具基类和注册中心
"""
from typing import Dict, Any, Optional, Callable, Type
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import json


class ToolInput(BaseModel):
    """工具输入基类"""
    pass


class ToolOutput(BaseModel):
    """工具输出基类"""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Tool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    input_schema: Type[ToolInput] = ToolInput
    
    def __init__(self):
        if not self.name:
            self.name = self.__class__.__name__
        if not self.description:
            self.description = self.__doc__ or ""
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolOutput:
        """执行工具"""
        pass
    
    def __call__(self, **kwargs) -> ToolOutput:
        """调用工具"""
        try:
            # 验证输入
            if self.input_schema != ToolInput:
                validated_input = self.input_schema(**kwargs)
                kwargs = validated_input.dict()
            
            # 执行
            return self.execute(**kwargs)
        except Exception as e:
            return ToolOutput(
                success=False,
                error=str(e)
            )
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI Function Calling 格式"""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        if self.input_schema != ToolInput:
            # 从 Pydantic 模型提取 schema
            input_schema_dict = self.input_schema.schema()
            schema["function"]["parameters"]["properties"] = input_schema_dict.get("properties", {})
            schema["function"]["parameters"]["required"] = input_schema_dict.get("required", [])
        
        return schema


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """注册工具"""
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool)}")
        self._tools[tool.name] = tool
    
    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, Tool]:
        """列出所有工具"""
        return self._tools.copy()
    
    def to_openai_schemas(self) -> list:
        """转换为 OpenAI Function Calling 格式列表"""
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def execute(self, name: str, **kwargs) -> ToolOutput:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            return ToolOutput(
                success=False,
                error=f"Tool '{name}' not found"
            )
        return tool(**kwargs)


# 全局工具注册中心
global_registry = ToolRegistry()
