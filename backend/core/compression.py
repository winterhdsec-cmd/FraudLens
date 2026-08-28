"""
HTTP 压缩中间件
支持 gzip 和 deflate 压缩，减少网络传输
"""
import gzip
import zlib
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import io
from core.logger import logger
from core.config import settings


class CompressionMiddleware(BaseHTTPMiddleware):
    """HTTP 压缩中间件"""
    
    def __init__(self, app, minimum_size: int = 500, compress_level: int = 6):
        """
        初始化压缩中间件
        
        Args:
            app: FastAPI 应用
            minimum_size: 最小压缩大小（字节），小于此值不压缩
            compress_level: 压缩级别（1-9），6 是默认值
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compress_level = compress_level
        
        logger.info(
            "CompressionMiddleware initialized",
            minimum_size=minimum_size,
            compress_level=compress_level
        )
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 检查客户端是否支持压缩
        accept_encoding = request.headers.get("accept-encoding", "")
        
        # 处理请求
        response = await call_next(request)
        
        # 检查是否需要压缩
        if not self._should_compress(response, accept_encoding):
            return response
        
        # 选择压缩算法
        if "gzip" in accept_encoding:
            return await self._compress_gzip(response)
        elif "deflate" in accept_encoding:
            return await self._compress_deflate(response)
        
        return response
    
    def _should_compress(self, response: Response, accept_encoding: str) -> bool:
        """检查是否应该压缩响应"""
        # 检查 Content-Type
        content_type = response.headers.get("content-type", "")
        if not any(ct in content_type for ct in [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/xhtml+xml"
        ]):
            return False
        
        # 检查是否已经压缩
        if "content-encoding" in response.headers:
            return False
        
        # 检查响应大小
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return False
        
        return True
    
    async def _compress_gzip(self, response: Response) -> Response:
        """使用 gzip 压缩响应"""
        try:
            # 读取响应内容
            body = await self._get_response_body(response)
            
            if len(body) < self.minimum_size:
                return response
            
            # 压缩
            compressed = gzip.compress(body, compresslevel=self.compress_level)
            
            # 创建新响应
            new_response = Response(
                content=compressed,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # 更新头部
            new_response.headers["content-encoding"] = "gzip"
            new_response.headers["content-length"] = str(len(compressed))
            new_response.headers["vary"] = "Accept-Encoding"
            
            logger.debug(
                "Response compressed with gzip",
                original_size=len(body),
                compressed_size=len(compressed),
                ratio=f"{len(compressed)/len(body)*100:.1f}%"
            )
            
            return new_response
            
        except Exception as e:
            logger.error("Gzip compression failed", error=str(e))
            return response
    
    async def _compress_deflate(self, response: Response) -> Response:
        """使用 deflate 压缩响应"""
        try:
            # 读取响应内容
            body = await self._get_response_body(response)
            
            if len(body) < self.minimum_size:
                return response
            
            # 压缩
            compressed = zlib.compress(body, self.compress_level)
            
            # 创建新响应
            new_response = Response(
                content=compressed,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # 更新头部
            new_response.headers["content-encoding"] = "deflate"
            new_response.headers["content-length"] = str(len(compressed))
            new_response.headers["vary"] = "Accept-Encoding"
            
            logger.debug(
                "Response compressed with deflate",
                original_size=len(body),
                compressed_size=len(compressed),
                ratio=f"{len(compressed)/len(body)*100:.1f}%"
            )
            
            return new_response
            
        except Exception as e:
            logger.error("Deflate compression failed", error=str(e))
            return response
    
    async def _get_response_body(self, response: Response) -> bytes:
        """获取响应内容"""
        if isinstance(response, StreamingResponse):
            # 流式响应需要收集所有数据
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body += chunk.encode("utf-8")
                else:
                    body += chunk
            return body
        else:
            return response.body


class RequestDecompressionMiddleware(BaseHTTPMiddleware):
    """请求解压缩中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 检查是否有压缩
        content_encoding = request.headers.get("content-encoding", "")
        
        if content_encoding in ["gzip", "deflate"]:
            # 读取并解压请求体
            body = await request.body()
            
            try:
                if content_encoding == "gzip":
                    decompressed = gzip.decompress(body)
                elif content_encoding == "deflate":
                    decompressed = zlib.decompress(body)
                else:
                    decompressed = body
                
                # 创建新的请求作用域
                async def receive():
                    return {
                        "type": "http.request",
                        "body": decompressed,
                        "more_body": False
                    }
                
                # 更新请求
                request._receive = receive
                
            except Exception as e:
                logger.error("Request decompression failed", error=str(e))
                return Response(
                    content=f"Failed to decompress request: {str(e)}",
                    status_code=400
                )
        
        return await call_next(request)


def add_compression_middleware(app, minimum_size: int = 500, compress_level: int = 6):
    """添加压缩中间件到应用"""
    app.add_middleware(CompressionMiddleware, minimum_size=minimum_size, compress_level=compress_level)
    app.add_middleware(RequestDecompressionMiddleware)
    
    logger.info("Compression middleware added to application")
