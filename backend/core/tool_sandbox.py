"""
工具调用沙箱 - 安全执行工具调用
提供隔离环境和资源限制
"""
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager
from core.logger import logger


class ToolSandbox:
    """
    工具执行沙箱
    
    提供：
    1. 超时控制
    2. 资源限制
    3. 异常隔离
    4. 执行监控
    """
    
    def __init__(
        self,
        timeout: float = 30.0,
        max_memory_mb: int = 512,
        max_retries: int = 2
    ):
        """
        初始化沙箱
        
        Args:
            timeout: 执行超时时间（秒）
            max_memory_mb: 最大内存使用（MB）
            max_retries: 最大重试次数
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_retries = max_retries
        
        logger.info(
            "ToolSandbox initialized",
            timeout=timeout,
            max_memory_mb=max_memory_mb,
            max_retries=max_retries
        )
    
    async def execute(
        self,
        tool_func: Callable,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        在沙箱中执行工具
        
        Args:
            tool_func: 工具函数
            tool_input: 工具输入参数
            context: 执行上下文
        
        Returns:
            执行结果
        """
        start_time = time.time()
        execution_id = f"exec_{int(start_time * 1000)}"
        
        logger.info(
            "Tool execution started",
            execution_id=execution_id,
            tool_name=getattr(tool_func, '__name__', 'unknown'),
            timeout=self.timeout
        )
        
        # 重试循环
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # 带超时的执行
                result = await asyncio.wait_for(
                    self._execute_with_monitoring(tool_func, tool_input, context),
                    timeout=self.timeout
                )
                
                execution_time = time.time() - start_time
                
                logger.info(
                    "Tool execution completed",
                    execution_id=execution_id,
                    attempt=attempt,
                    execution_time=execution_time,
                    success=True
                )
                
                return {
                    "success": True,
                    "result": result,
                    "execution_id": execution_id,
                    "execution_time": execution_time,
                    "attempts": attempt
                }
            
            except asyncio.TimeoutError:
                last_error = f"Tool execution timeout after {self.timeout}s"
                logger.error(
                    "Tool execution timeout",
                    execution_id=execution_id,
                    attempt=attempt,
                    timeout=self.timeout
                )
            
            except MemoryError:
                last_error = f"Tool exceeded memory limit: {self.max_memory_mb}MB"
                logger.error(
                    "Tool memory limit exceeded",
                    execution_id=execution_id,
                    attempt=attempt,
                    max_memory_mb=self.max_memory_mb
                )
                break  # 内存错误不重试
            
            except Exception as e:
                last_error = str(e)
                logger.error(
                    "Tool execution failed",
                    execution_id=execution_id,
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__
                )
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 指数退避
                logger.info(
                    "Retrying tool execution",
                    execution_id=execution_id,
                    attempt=attempt + 1,
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)
        
        # 所有重试都失败
        execution_time = time.time() - start_time
        logger.error(
            "Tool execution failed after all retries",
            execution_id=execution_id,
            attempts=self.max_retries,
            execution_time=execution_time,
            last_error=last_error
        )
        
        return {
            "success": False,
            "error": last_error,
            "execution_id": execution_id,
            "execution_time": execution_time,
            "attempts": self.max_retries
        }
    
    async def _execute_with_monitoring(
        self,
        tool_func: Callable,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        带监控的工具执行
        
        Args:
            tool_func: 工具函数
            tool_input: 工具输入参数
            context: 执行上下文
        
        Returns:
            工具执行结果
        """
        # 如果是异步函数，直接调用
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**tool_input)
        else:
            # 同步函数，在线程池中执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: tool_func(**tool_input)
            )
    
    @asynccontextmanager
    async def resource_limit(self):
        """
        资源限制上下文管理器
        
        注意：Python中精确的资源限制比较困难，
        这里提供基本的超时和内存监控框架
        """
        # 这里可以添加更精细的资源限制
        # 例如使用 resource 模块（Unix）或 psutil
        try:
            yield
        finally:
            # 清理资源
            pass


class ToolRegistry:
    """
    工具注册表
    
    管理所有可用工具，提供安全的工具调用接口
    """
    
    def __init__(self, sandbox: Optional[ToolSandbox] = None):
        """
        初始化工具注册表
        
        Args:
            sandbox: 工具执行沙箱
        """
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.sandbox = sandbox or ToolSandbox()
        
        logger.info("ToolRegistry initialized")
    
    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False
    ):
        """
        注册工具
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            parameters: 参数schema
            requires_approval: 是否需要人工审批
        """
        self.tools[name] = func
        self.tool_metadata[name] = {
            "description": description,
            "parameters": parameters or {},
            "requires_approval": requires_approval,
            "registered_at": time.time()
        }
        
        logger.info("Tool registered", tool_name=name, description=description)
    
    def unregister(self, name: str):
        """
        注销工具
        
        Args:
            name: 工具名称
        """
        if name in self.tools:
            del self.tools[name]
            del self.tool_metadata[name]
            logger.info("Tool unregistered", tool_name=name)
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        获取工具
        
        Args:
            name: 工具名称
        
        Returns:
            工具函数
        """
        return self.tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有工具
        
        Returns:
            工具元数据字典
        """
        return self.tool_metadata.copy()
    
    async def call_tool(
        self,
        name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用工具（通过沙箱）
        
        Args:
            name: 工具名称
            tool_input: 工具输入参数
            context: 执行上下文
        
        Returns:
            执行结果
        """
        tool_func = self.get_tool(name)
        
        if not tool_func:
            logger.error("Tool not found", tool_name=name)
            return {
                "success": False,
                "error": f"Tool not found: {name}"
            }
        
        # 检查是否需要审批
        metadata = self.tool_metadata.get(name, {})
        if metadata.get("requires_approval"):
            logger.warning(
                "Tool requires approval",
                tool_name=name,
                tool_input=tool_input
            )
            # 这里可以添加审批逻辑
            # 暂时直接拒绝
            return {
                "success": False,
                "error": "Tool requires human approval"
            }
        
        # 在沙箱中执行
        return await self.sandbox.execute(tool_func, tool_input, context)


# 全局工具注册表
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
