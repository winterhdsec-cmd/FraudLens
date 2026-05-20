"""
File upload/extract/OCR/import routes.
"""
import os
import tempfile

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

router = APIRouter(prefix='/api', tags=['文件'])


@router.post('/extract-text')
async def api_extract_text(file: UploadFile = File(...)):
    try:
        filename = file.filename or ''
        ext = os.path.splitext(filename)[1].lower()
        content = await file.read()
        text = ''
        if ext in ('.txt', '.csv'):
            text = content.decode('utf-8', errors='ignore')
        elif ext == '.docx':
            import io
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = '\n'.join(p.text for p in doc.paragraphs)
        else:
            return JSONResponse(status_code=400, content={
                "success": False, "error": f"不支持的文件格式: {ext}"
            })
        return {"success": True, "text": text, "filename": filename}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/ocr')
async def api_ocr(file: UploadFile = File(...)):
    try:
        from tools.ocr import ocr_image
        content = await file.read()
        text = ocr_image(content)
        return {"success": True, "text": text, "filename": file.filename}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/import/csv')
async def api_import_csv(file: UploadFile = File(...)):
    try:
        from database.importer import import_from_csv
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        content = await file.read()
        tmp.write(content)
        tmp.close()
        result = import_from_csv(tmp.name)
        os.unlink(tmp.name)
        return {"success": True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/import/excel')
async def api_import_excel(file: UploadFile = File(...)):
    try:
        from database.importer import import_from_excel
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        content = await file.read()
        tmp.write(content)
        tmp.close()
        result = import_from_excel(tmp.name)
        os.unlink(tmp.name)
        return {"success": True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})