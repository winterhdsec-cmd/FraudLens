"""
DeepSeek / OpenAI 多模态视觉分析模块
支持 DeepSeek VL2、Qwen-VL 等 OpenAI 兼容的视觉语言模型
"""
import os
import base64
import io
from typing import Optional, Dict, Any, List
from tools.response import logger
from core.llm_client import mask_messages  # G2 脱敏


VISION_MODELS = ['deepseek-vl2', 'deepseek-vl', 'gpt-4o', 'gpt-4-vision-preview', 'qwen-vl-plus', 'qwen-vl-max']


class VisionAnalyzer:
    """多模态图像分析器"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        vl_model = os.getenv("DEEPSEEK_VL_MODEL", "")
        if model:
            self.model = model
        elif vl_model:
            self.model = vl_model
        else:
            # 统一走配置出口，避免换服务商后仍请求旧模型名（404 → 静默降级）
            from core.llm_client import get_llm_model

            self.model = get_llm_model()
        self._client = None
        self._vision_client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _get_vision_client(self):
        vl_base = os.getenv("DEEPSEEK_VL_BASE_URL", self.base_url)
        if self._vision_client is None:
            from openai import OpenAI
            self._vision_client = OpenAI(api_key=self.api_key, base_url=vl_base)
        return self._vision_client

    def _is_vision_model(self):
        base = self.model.lower()
        return any(vm in base for vm in VISION_MODELS)

    def _encode_image(self, image_data: bytes, format: str = "png") -> str:
        return base64.b64encode(image_data).decode("utf-8")

    def _build_content(self, image_data: bytes, prompt: str, format: str = "png") -> List[Dict[str, Any]]:
        b64 = self._encode_image(image_data, format)
        data_uri = f"data:image/{format};base64,{b64}"
        return [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_uri}}
        ]

    def analyze(self, image_data: bytes, prompt: str, format: str = "png",
                temperature: float = 0.1, max_tokens: int = 2048) -> Dict[str, Any]:
        # G2 出域门禁：图片同样受 DISABLE_CLOUD_LLM 管控。
        # 历史缺陷：本方法自建 OpenAI client，只校验 api_key，不校验云端开关，
        # 且 mask_messages 只处理文本、对 image_url 原样透传 →
        # 一旦关闭云端，文本路径已降级，图片却仍会把原始截图 base64 发出域。
        # 这里补上门禁：关闭云端时直接走本地 OCR 降级，绝不出域。
        from core.llm_client import cloud_llm_enabled

        if not cloud_llm_enabled():
            logger.info("[Vision] 云端 LLM 已关闭（DISABLE_CLOUD_LLM=1），图片不出域，降级本地 OCR")
            fallback_text, method = self._try_fallback(image_data, prompt, format)
            return {"success": True, "text": fallback_text, "model": "ocr_local",
                    "note": "cloud_llm_disabled"}

        if not self.api_key or self.api_key == "mock-key":
            logger.warning("[Vision] 未配置 API Key，使用模拟模式")
            return self._mock_analyze(prompt)

        models_to_try = []
        if self._is_vision_model():
            models_to_try.append((self.model, self.client))
        else:
            models_to_try.append((self.model, self.client))
            for vm in ['deepseek-vl2', 'gpt-4o']:
                if vm != self.model.lower():
                    models_to_try.append((vm, self._get_vision_client()))

        last_error = ""
        for model_name, client in models_to_try:
            try:
                content = self._build_content(image_data, prompt, format)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=mask_messages([{"role": "user", "content": content}]),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30
                )
                result = response.choices[0].message.content
                logger.info(f"[Vision] 分析完成，模型: {model_name}, 耗时: {response.usage.total_tokens} tokens")
                return {"success": True, "text": result, "model": model_name}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Vision] 模型 {model_name} 调用失败: {e}，尝试下一个...")
                continue

        logger.error(f"[Vision] 所有视觉模型调用失败: {last_error}")
        fallback_text, method = self._try_fallback(image_data, prompt, format)
        return {"success": True, "text": fallback_text, "model": "ocr_fallback", "note": last_error}

    def _try_fallback(self, image_data: bytes, prompt: str, format: str = "png") -> tuple:
        try:
            from tools.ocr import ocr_image
            ocr_text = ocr_image(image_data)
        except Exception as e:
            logger.warning(f"[Vision] 本地 OCR 降级失败: {e}")
            ocr_text = ""
        if not ocr_text or not ocr_text.strip():
            return ("【图像识别不可用】当前已关闭云端大模型（数据不出域），"
                    "且本地 OCR 未能提取到文字。如需图像理解，请在授权环境下临时开启云端 LLM。",
                    "ocr")
        return f"【OCR文字识别结果】\n{ocr_text}\n\n【识别方式】OCR识别（视觉模型不可用，降级为文字识别）", "ocr"

    def _mock_analyze(self, prompt: str) -> Dict[str, Any]:
        return {
            "success": True,
            "text": f"【模拟视觉分析】\n根据图像分析请求: {prompt[:50]}...\n（当前为模拟模式，配置真实 API Key 后可获取实际分析结果）",
            "model": "mock"
        }

    def is_available(self) -> bool:
        """可用性判断：必须同时满足「云端开关已打开」+「配置了真实密钥」。"""
        if not self.api_key or self.api_key == "mock-key":
            return False
        try:
            from core.llm_client import cloud_llm_enabled
            return cloud_llm_enabled()
        except Exception:
            return False


def classify_image_complexity(image_data: bytes) -> str:
    """
    简单判断图片复杂度
    返回: 'simple' - 纯文字图片, 适合 OCR
          'complex' - 复杂图片（截图/表格等）, 适合多模态
    """
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_data))
        w, h = img.size
        aspect = w / h if h > 0 else 1
        area = w * h

        if area > 2000 * 2000:
            return "complex"
        if aspect < 0.4 or aspect > 2.5:
            return "complex"
        if img.mode == 'RGBA':
            return "complex"

        gray = img.convert('L')
        pixels = list(gray.getdata())
        total = len(pixels)
        whites = sum(1 for p in pixels if p > 230)
        white_ratio = whites / total if total > 0 else 0
        unique_colors = len(set(pixels[i] for i in range(0, total, max(total // 100, 1))))

        if white_ratio > 0.6 and unique_colors < 30:
            return "simple"
        return "complex"
    except Exception:
        return "simple"