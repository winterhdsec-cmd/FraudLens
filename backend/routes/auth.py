"""
Auth routes: login, register, me, logout, refresh, change-password, admin users.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database import db
from .deps import (
    get_current_user, get_token_from_header, decode_token,
    create_token, create_refresh_token, log_operation,
    LoginRequest, RegisterRequest, RefreshRequest,
    _TOKEN_BLACKLIST
)

router = APIRouter(prefix='/api/auth', tags=['认证'])


@router.post('/login')
async def api_login(data: LoginRequest, request: Request):
    try:
        from database.models import User
        user = User.query.filter_by(username=data.username).first()
        if not user or not user.check_password(data.password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用")
        user.last_login = datetime.utcnow()
        db.session.commit()
        access_token = create_token(
            user.id,
            extra_claims={
                'username': user.username,
                'role': user.role,
                'display_name': user.display_name
            }
        )
        refresh_token = create_refresh_token(user.id)
        ip = request.client.host if request.client else ''
        log_operation(user.id, user.username, 'login', ip_address=ip)
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/demo-login')
async def api_demo_login(request: Request):
    try:
        from database.models import User
        demo_user = User.query.filter_by(username='admin').first()
        if not demo_user:
            demo_user = User(
                username='admin',
                display_name='系统管理员',
                role='admin',
                department='反诈中心'
            )
            demo_user.set_password('admin123')
            db.session.add(demo_user)
            db.session.commit()
        demo_user.last_login = datetime.utcnow()
        db.session.commit()
        access_token = create_token(
            demo_user.id,
            extra_claims={
                'username': demo_user.username,
                'role': demo_user.role,
                'display_name': demo_user.display_name
            }
        )
        refresh_token = create_refresh_token(demo_user.id)
        ip = request.client.host if request.client else ''
        log_operation(demo_user.id, demo_user.username, 'login', ip_address=ip)
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": demo_user.to_dict()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/register')
async def api_register(data: RegisterRequest, request: Request):
    try:
        if not data.username or not data.password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        from database.models import User
        if User.query.filter_by(username=data.username).first():
            raise HTTPException(status_code=409, detail="用户名已存在")
        user = User(
            username=data.username,
            display_name=data.display_name or data.username,
            role='analyst',
            department=data.department,
            phone=data.phone
        )
        user.set_password(data.password)
        db.session.add(user)
        db.session.commit()
        ip = request.client.host if request.client else ''
        log_operation(user.id, user.username, 'register', ip_address=ip)
        return JSONResponse(status_code=201, content={
            "success": True, "message": "注册成功", "user": user.to_dict()
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/me')
async def api_get_me(current_user: dict = Depends(get_current_user)):
    from database.models import User
    user = User.query.get(current_user['id'])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True, "user": user.to_dict()}


@router.post('/logout')
async def api_logout(request: Request):
    token = get_token_from_header(request)
    if token:
        payload = decode_token(token)
        if payload:
            from tools.redis_utils import blacklist_add, redis_available
            jti = payload.get('jti', token[-16:])
            _TOKEN_BLACKLIST.add(jti)
            if redis_available():
                blacklist_add(jti, ttl_seconds=86400)
    return {"success": True, "message": "已退出登录"}


@router.get('/users')
async def api_list_users(current_user: dict = Depends(get_current_user)):
    from database.models import User
    users = User.query.order_by(User.created_at.desc()).all()
    return {"success": True, "users": [u.to_dict() for u in users]}


@router.get('/logs')
async def api_get_auth_logs(current_user: dict = Depends(get_current_user)):
    from database.models import OperationLog
    logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(100).all()
    return {
        "success": True,
        "logs": [{
            'id': l.id, 'username': l.username, 'action': l.action,
            'target': f"{l.target_type}/{l.target_id}",
            'detail': l.detail, 'ip_address': l.ip_address,
            'created_at': l.created_at.isoformat() if l.created_at else None
        } for l in logs]
    }


@router.post('/refresh')
async def api_refresh(data: RefreshRequest):
    token = data.refresh_token
    payload = decode_token(token)
    if not payload or payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    user_id = int(payload['sub'])
    from database.models import User
    user = User.query.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    access_token = create_token(
        user.id,
        extra_claims={
            'username': user.username,
            'role': user.role,
            'display_name': user.display_name
        }
    )
    return {"success": True, "access_token": access_token}


@router.put('/change-password')
async def api_change_password(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        old_pw = body.get('old_password', '')
        new_pw = body.get('new_password', '')
        if not old_pw or not new_pw:
            raise HTTPException(status_code=400, detail="请提供旧密码和新密码")
        if len(new_pw) < 6:
            raise HTTPException(status_code=400, detail="新密码至少6位")
        from database.models import User
        user = User.query.get(current_user['id'])
        if not user or not user.check_password(old_pw):
            raise HTTPException(status_code=403, detail="旧密码错误")
        user.set_password(new_pw)
        db.session.commit()
        return {"success": True, "message": "密码已修改"}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/admin/users/{user_id}')
async def api_admin_user_put(user_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="无权限")
        from database.models import User
        target = User.query.get(user_id)
        if not target:
            raise HTTPException(status_code=404, detail="用户不存在")
        body = await request.json()
        if 'role' in body: target.role = body['role']
        if 'is_active' in body: target.is_active = body['is_active']
        if 'display_name' in body: target.display_name = body['display_name']
        if 'department' in body: target.department = body['department']
        if 'phone' in body: target.phone = body['phone']
        db.session.commit()
        return {"success": True, "user": target.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete('/admin/users/{user_id}')
async def api_admin_user_delete(user_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="无权限")
        from database.models import User
        target = User.query.get(user_id)
        if not target:
            raise HTTPException(status_code=404, detail="用户不存在")
        db.session.delete(target)
        db.session.commit()
        return {"success": True, "message": "用户已删除"}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})