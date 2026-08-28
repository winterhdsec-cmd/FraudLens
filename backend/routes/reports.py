"""
Report routes.
"""
import os

from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse, FileResponse

from .deps import get_current_user, db_retry, log_operation

router = APIRouter(prefix='/api/reports', tags=['报告'])


@router.get('/case/{case_id}')
@db_retry()
async def api_case_report(case_id: str, format: str = Query('pdf', alias='format'), current_user: dict = Depends(get_current_user)):
    try:
        from database.report import generate_case_report, export_case_docx
        from core.object_store import put_object, is_enabled
        from pathlib import Path
        filepath = export_case_docx(case_id) if format == 'docx' else generate_case_report(case_id)
        filename = os.path.basename(filepath)
        # G7 审计：导出案件报告留痕
        try:
            log_operation(current_user['id'], current_user.get('username', ''),
                'export_case_report', 'case', case_id, {'format': format}, ip_address='')
        except Exception:
            pass
        # A4.1 (#C13): 报告存 minio，返回 presigned URL；minio 不可用时退回本地 download
        object_key = f"reports/{filename}"
        if is_enabled() and put_object(object_key, Path(filepath).read_bytes(),
                                       content_type="application/octet-stream"):
            return {"success": True, "file_path": f"/api/reports/download/{filename}",
                    "object_key": object_key, "object_url": f"/api/object/{object_key}"}
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/gang/{gang_id}')
async def api_gang_report(gang_id: str, current_user: dict = Depends(get_current_user)):
    try:
        # G7 审计：导出团伙报告留痕
        try:
            log_operation(current_user['id'], current_user.get('username', ''),
                'export_gang_report', 'gang', gang_id, {}, ip_address='')
        except Exception:
            pass
        from database.report import generate_gang_report
        from core.object_store import put_object, is_enabled
        from pathlib import Path
        filepath = generate_gang_report(gang_id)
        filename = os.path.basename(filepath)
        # A4.1 (#C13): 报告存 minio，返回 presigned URL；minio 不可用时退回本地 download
        object_key = f"reports/{filename}"
        if is_enabled() and put_object(object_key, Path(filepath).read_bytes(),
                                       content_type="application/octet-stream"):
            return {"success": True, "file_path": f"/api/reports/download/{filename}",
                    "object_key": object_key, "object_url": f"/api/object/{object_key}"}
        return {"success": True, "file_path": f"/api/reports/download/{filename}"}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/download/{filename}')
async def api_download_report(filename: str, current_user: dict = Depends(get_current_user)):
    try:
        # 路径穿越防护：仅允许纯文件名（不含路径分隔符/相对路径），防止 ../ 逃逸读任意文件
        if os.path.basename(filename) != filename or '..' in filename:
            return JSONResponse(status_code=400, content={"success": False, "error": "非法文件名"})
        # G7 审计：下载报告留痕
        try:
            log_operation(current_user['id'], current_user.get('username', ''),
                'download_report', 'file', filename, {}, ip_address='')
        except Exception:
            pass
        reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))
        filepath = os.path.abspath(os.path.join(reports_dir, filename))
        # 双重校验：最终路径必须仍在 reports 目录内
        if os.path.commonpath([reports_dir, filepath]) != reports_dir:
            return JSONResponse(status_code=400, content={"success": False, "error": "非法文件名"})
        if not os.path.exists(filepath):
            return JSONResponse(status_code=404, content={"success": False, "error": "文件不存在"})
        return FileResponse(filepath, filename=filename)
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})