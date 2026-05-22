"""OCR module using EasyOCR for Chinese text extraction."""
import os
import tempfile
import numpy as np
from PIL import Image
import io
from tools.response import logger

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr
        logger.info("正在加载 EasyOCR 引擎（首次加载需下载模型，约100MB）...")
        _reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        logger.info("EasyOCR 引擎就绪")
    return _reader


def ocr_image(image_bytes):
    """Run OCR on image bytes, return extracted text."""
    reader = get_reader()
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img)
        result = reader.readtext(img_array)
        lines = []
        for bbox, text, confidence in result:
            text = text.strip()
            if text and confidence >= 0.3:
                lines.append(text)
        return '\n'.join(lines)
    except Exception as e:
        logger.error(f"OCR 识别失败: {e}")
        return ''


def ocr_image_file(filepath):
    """Run OCR on image file path, return extracted text."""
    with open(filepath, 'rb') as f:
        return ocr_image(f.read())
