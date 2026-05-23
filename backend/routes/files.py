"""
File upload/extract/OCR/import routes.
Smart routing: text→tools, complex images→multimodal vision model
"""
import os
import io
import tempfile
import re

from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix='/api', tags=['文件'])

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp')
TEXT_EXTENSIONS = ('.txt', '.csv')
DOC_EXTENSIONS = ('.docx',)
PDF_EXTENSIONS = ('.pdf',)

ALL_TEXT_EXTENSIONS = TEXT_EXTENSIONS + DOC_EXTENSIONS + PDF_EXTENSIONS


def _extract_docx(content: bytes) -> str:
    """提取 DOCX 段落 + 表格数据"""
    from docx import Document
    doc = Document(io.BytesIO(content))
    parts = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for i, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(' | '.join(cells))
        parts.append(f'\n[表格 {i + 1}]\n' + '\n'.join(rows))
    return '\n'.join(parts)


def _extract_pdf_text(content: bytes) -> tuple:
    """
    提取 PDF 文字
    返回: (text, scanned)
    scanned=True 表示无文字层，需走 OCR/视觉通道
    """
    import pypdfium2 as pdfium
    pdf_doc = pdfium.PdfDocument(content)
    pages = []
    for i in range(len(pdf_doc)):
        page = pdf_doc[i]
        tp = page.get_textpage()
        text_page = tp.get_text_range()
        if text_page:
            pages.append(text_page.strip())
        tp.close()
    pdf_doc.close()
    total_text = '\n'.join(pages).strip()
    is_scanned = len(total_text) < 20 and len(pages) > 0
    return total_text, is_scanned


def _extract_pdf_content(file_bytes: bytes) -> str:
    """
    智能 PDF 提取: 有文字层直接提取, 无文字层转图片 OCR
    """
    text, is_scanned = _extract_pdf_text(file_bytes)
    if not is_scanned:
        return text
    from tools.ocr import ocr_image, ocr_image_file
    pages = _pdf_to_images(file_bytes)
    parts = []
    for i, img_bytes in enumerate(pages):
        ocr_result = ocr_image(img_bytes)
        if ocr_result.strip():
            parts.append(f'[第{i + 1}页]\n{ocr_result}')
    return '\n\n'.join(parts) if parts else ''


def _pdf_to_images(file_bytes: bytes) -> list:
    """PDF 每页转为 PNG 字节流列表"""
    import pypdfium2 as pdfium
    from PIL import Image
    pdf_doc = pdfium.PdfDocument(file_bytes)
    images = []
    for i in range(len(pdf_doc)):
        page = pdf_doc[i]
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format='PNG')
        images.append(buf.getvalue())
    pdf_doc.close()
    return images


# ──────────────────────────────────────────────
#  端点1: 传统文字提取（纯文字文档）
# ──────────────────────────────────────────────
@router.post('/extract-text')
async def api_extract_text(file: UploadFile = File(...)):
    try:
        filename = file.filename or ''
        ext = os.path.splitext(filename)[1].lower()
        content = await file.read()
        text = ''
        source = 'direct'
        if ext in TEXT_EXTENSIONS:
            text = content.decode('utf-8', errors='ignore')
        elif ext == '.docx':
            text = _extract_docx(content)
        elif ext == '.pdf':
            text = _extract_pdf_content(content)
            source = 'pdf_ocr' if len(text) > 0 else 'direct'
        else:
            return JSONResponse(status_code=400, content={
                "success": False, "error": f"不支持的文件格式: {ext}"
            })
        return {"success": True, "text": text, "filename": filename, "source": source}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ──────────────────────────────────────────────
#  端点2: OCR 文字识别（纯图片）
# ──────────────────────────────────────────────
@router.post('/ocr')
async def api_ocr(file: UploadFile = File(...)):
    try:
        filename = file.filename or ''
        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            return JSONResponse(status_code=400, content={
                "success": False, "error": f"OCR 仅支持图片格式, 不支持: {ext}"
            })
        from tools.ocr import ocr_image
        content = await file.read()
        text = ocr_image(content)
        return {"success": True, "text": text, "filename": file.filename, "source": "ocr"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ──────────────────────────────────────────────
#  端点3: 智能文件分析（核心改进 - 混合路由）
# ──────────────────────────────────────────────
@router.post('/analyze-file')
async def api_analyze_file(
    file: UploadFile = File(...),
    mode: str = Query('auto', description='auto: 自动选择, ocr: 强制OCR, vision: 强制多模态')
):
    """
    智能文件分析端点 - 自动选择最佳处理路径

    路由规则:
    - TXT/CSV/DOCX → 传统工具提取文字
    - PDF → 先检测是否有文字层 → 有则直接提取，无则转图片
    - 图片 → 根据复杂度自动选择:
        - 简单图片(白底文字) → EasyOCR (快)
        - 复杂图片(截图/表格) → DeepSeek VL2 多模态 (理解力强)
    - 强制 mode=ocr → 全部走 OCR
    - 强制 mode=vision → 图片走多模态
    """
    try:
        filename = file.filename or ''
        ext = os.path.splitext(filename)[1].lower()
        content = await file.read()

        # ── 纯文字文档 ──
        if ext in TEXT_EXTENSIONS:
            text = content.decode('utf-8', errors='ignore')
            return {"success": True, "text": text, "filename": filename, "method": "direct", "route": "text"}

        if ext == '.docx':
            text = _extract_docx(content)
            return {"success": True, "text": text, "filename": filename, "method": "docx", "route": "text"}

        # ── PDF ──
        if ext == '.pdf':
            text, is_scanned = _extract_pdf_text(content)
            if not is_scanned:
                return {"success": True, "text": text, "filename": filename, "method": "pdf_text", "route": "text"}
            pages = _pdf_to_images(content)
            parts = []
            for i, img_bytes in enumerate(pages):
                from tools.ocr import ocr_image as ocr_fn
                ocr_text = ocr_fn(img_bytes)
                if ocr_text.strip():
                    parts.append(f'[第{i + 1}页]\n{ocr_text}')
            result_text = '\n\n'.join(parts) if parts else ''
            return {"success": True, "text": result_text, "filename": filename, "method": "pdf_ocr", "route": "image"}

        # ── 图片 ──
        if ext in IMAGE_EXTENSIONS:
            use_vision = False
            if mode == 'vision':
                use_vision = True
            elif mode == 'auto':
                from tools.vision import classify_image_complexity
                complexity = classify_image_complexity(content)
                use_vision = (complexity == 'complex')
            else:
                use_vision = False

            if use_vision:
                from tools.vision import VisionAnalyzer
                analyzer = VisionAnalyzer()
                prompt = (
                    "请分析这张图片，提取所有与诈骗案件相关的信息，包括但不限于：\n"
                    "1. 涉及的人员信息（姓名、电话、账号等）\n"
                    "2. 资金信息（金额、转账记录、银行等）\n"
                    "3. 诈骗类型和手法描述\n"
                    "4. 时间线信息\n"
                    "5. 其他所有可见的文字内容和关键信息\n\n"
                    "请以结构化文字形式完整输出所有可识别的信息。"
                )
                result = analyzer.analyze(content, prompt, format=ext.lstrip('.'))
                return {
                    "success": True,
                    "text": result.get("text", ""),
                    "filename": filename,
                    "method": result.get("model", "vision"),
                    "route": "vision"
                }
            else:
                from tools.ocr import ocr_image as ocr_fn
                text = ocr_fn(content)
                return {"success": True, "text": text, "filename": filename, "method": "ocr", "route": "image"}
    
        return JSONResponse(status_code=400, content={
            "success": False, "error": f"不支持的文件格式: {ext}"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ──────────────────────────────────────────────
#  端点4: 视觉分析（纯多模态，不降级）
# ──────────────────────────────────────────────
@router.post('/vision-analyze')
async def api_vision_analyze(
    file: UploadFile = File(...),
    prompt: str = Query('请详细描述这张图片的内容', description='分析提示词')
):
    """完全使用多模态大模型分析图片，适合复杂截图/表格"""
    try:
        filename = file.filename or ''
        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            return JSONResponse(status_code=400, content={
                "success": False, "error": f"视觉分析仅支持图片格式, 不支持: {ext}"
            })
        from tools.vision import VisionAnalyzer
        content = await file.read()
        analyzer = VisionAnalyzer()
        result = analyzer.analyze(content, prompt, format=ext.lstrip('.'))
        return {
            "success": True,
            "text": result.get("text", ""),
            "filename": filename,
            "model": result.get("model", "unknown"),
            "note": result.get("note", "")
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})