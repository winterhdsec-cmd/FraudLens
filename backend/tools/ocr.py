"""OCR module using EasyOCR for Chinese text extraction."""
import os
import tempfile

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr
        print("📷 正在加载 OCR 引擎...")
        _reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        print("✅ OCR 引擎就绪")
    return _reader


def ocr_image(image_bytes):
    """Run OCR on image bytes, return extracted text."""
    reader = get_reader()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    tmp.write(image_bytes)
    tmp.close()
    try:
        result = reader.readtext(tmp.name, detail=0)
        text = '\n'.join(result)
        return text
    finally:
        os.unlink(tmp.name)


def ocr_image_file(filepath):
    """Run OCR on image file path, return extracted text."""
    reader = get_reader()
    result = reader.readtext(filepath, detail=0)
    return '\n'.join(result)