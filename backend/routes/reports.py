"""
Report routes.
"""
import os

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, FileResponse

router = APIRouter(prefix='/api/reports', tags=['报告'])


@router.get('/case/{case_id}')
async def api_case_report(case_id: str, format: str = Query('pdf', alias='format')):
    try:
        from database.report import generate_case_report, export_case_docx
        filepath = export_case_docx(case_id) if format == 'docx' else generate_case_report(case_id)
        filename = os.path.basename(filepath)
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/gang/{gang_id}')
async def api_gang_report(gang_id: str):
    try:
        from database.report import generate_gang_report
        filepath = generate_gang_report(gang_id)
        filename = os.path.basename(filepath)
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/download/{filename}')
async def api_download_report(filename: str):
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        filepath = os.path.join(reports_dir, filename)
        if not os.path.exists(filepath):
            return JSONResponse(status_code=404, content={"success": False, "error": "文件不存在"})
        return FileResponse(filepath, filename=filename)
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})