"""
File upload/extract/OCR/import routes.
Smart routing: text→tools, complex images→multimodal vision model
"""
import os
import io
import tempfile
import re

from fastapi import APIRouter, UploadFile, File, Query, Depends
from fastapi.responses import JSONResponse

from .deps import get_current_user

router = APIRouter(prefix='/api', tags=['文件'])

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp')
TEXT_EXTENSIONS = ('.txt', '.csv')
DOC_EXTENSIONS = ('.docx',)
PDF_EXTENSIONS = ('.pdf',)

ALL_TEXT_EXTENSIONS = TEXT_EXTENSIONS + DOC_EXTENSIONS + PDF_EXTENSIONS

_llm_client = None
_llm_model = None


def _get_llm_client():
    """获取 LLM 客户端（用于文本后处理）"""
    global _llm_client, _llm_model
    if _llm_client is not None:
        return _llm_client, _llm_model
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    _llm_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if api_key and api_key != "mock-key":
        from openai import OpenAI
        _llm_client = OpenAI(api_key=api_key, base_url=base_url)
    return _llm_client, _llm_model


def _clean_chat_text(raw_text: str) -> str:
    """
    AI 后处理：对 OCR/视觉提取的文字进行清洗，
    区分嫌疑人（骗子）与受害人发言（聊天记录截图场景）。
    如果 LLM 不可用则返回原始文本。
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    client, model = _get_llm_client()
    if not client:
        return raw_text

    prompt = (
        "你是一位反诈分析助手。以下是从图片中提取的原始文字（可能包含 OCR 识别错误），"
        "请进行以下处理：\n\n"
        "1. **清洗与纠错**：修正 OCR 识别错误，恢复正确的标点和分段\n"
        "2. **角色区分**：如果内容看起来是聊天记录或对话，请区分发言者角色：\n"
        "   - **[嫌疑人/骗子]**：冒充客服、公检法等身份，诱导转账、索要验证码等\n"
        "   - **[受害人]**：被诱导的受害人发言\n"
        "3. **内容归类**：按以下类别整理信息：\n"
        "   - 📞 通话/聊天内容（区分角色）\n"
        "   - 💳 资金信息（金额、账号、转账记录）\n"
        "   - 👤 人员信息（姓名、电话、身份证号）\n"
        "   - 📅 时间线信息\n"
        "4. **结构化输出**：如果内容较少，保留原始格式但添加角色标注\n\n"
        "请输出处理后的文本，保持原意不变，不要编造不存在的信息。\n\n"
        "原始文字：\n"
        f"{raw_text}"
    )

    try:
        from tools.response import logger
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
            timeout=30
        )
        cleaned = response.choices[0].message.content
        if cleaned and cleaned.strip():
            logger.info(f"[TextClean] AI 文本清洗完成，{len(raw_text)}→{len(cleaned)} 字符")
            return cleaned
    except Exception as e:
        from tools.response import logger
        logger.warning(f"[TextClean] AI 清洗失败（{e}），返回原始文本")

    return raw_text


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
async def api_extract_text(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
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
async def api_ocr_image(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
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
    mode: str = Query('auto', description='auto: 自动选择, ocr: 强制OCR, vision: 强制多模态'),
    clean: str = Query('auto', description='auto: 图片结果自动AI清洗, off: 不清洗'),
    current_user: dict = Depends(get_current_user)
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
    - clean=auto → 图片结果自动 AI 清洗（区分嫌疑人/受害人）
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
                raw_text = result.get("text", "")
                cleaned_text = _clean_chat_text(raw_text) if clean == 'auto' and raw_text else raw_text
                return {
                    "success": True,
                    "text": cleaned_text,
                    "raw_text": raw_text if cleaned_text != raw_text else "",
                    "filename": filename,
                    "method": result.get("model", "vision"),
                    "route": "vision",
                    "cleaned": cleaned_text != raw_text
                }
            else:
                from tools.ocr import ocr_image as ocr_fn
                text = ocr_fn(content)
                cleaned_text = _clean_chat_text(text) if clean == 'auto' and text else text
                return {
                    "success": True,
                    "text": cleaned_text,
                    "raw_text": text if cleaned_text != text else "",
                    "filename": filename,
                    "method": "ocr",
                    "route": "image",
                    "cleaned": cleaned_text != text
                }
    
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
    prompt: str = Query('请详细描述这张图片的内容', description='分析提示词'),
    clean: str = Query('auto', description='auto: 自动AI清洗结果, off: 不清洗'),
    current_user: dict = Depends(get_current_user)
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
        raw_text = result.get("text", "")
        cleaned_text = _clean_chat_text(raw_text) if clean == 'auto' and raw_text else raw_text
        return {
            "success": True,
            "text": cleaned_text,
            "raw_text": raw_text if cleaned_text != raw_text else "",
            "filename": filename,
            "model": result.get("model", "unknown"),
            "note": result.get("note", ""),
            "cleaned": cleaned_text != raw_text
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})