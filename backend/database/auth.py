from flask import request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from datetime import timedelta, datetime
from . import db
from .models import User, OperationLog

jwt = JWTManager()
BLACKLIST = set()


def init_auth(app):
    app.config['JWT_SECRET_KEY'] = 'fraudlens-jwt-secret-key-2024'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    jwt.init_app(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in BLACKLIST


def log_operation(user_id, username, action, target_type='', target_id='', detail=None):
    log = OperationLog(
        user_id=user_id,
        username=username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
        ip_address=request.remote_addr or ''
    )
    db.session.add(log)
    db.session.commit()
    return log


def register_routes(app):

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        display_name = data.get('display_name', '')

        if not username or not password:
            return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
        if len(password) < 6:
            return jsonify({"success": False, "error": "密码长度至少6位"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"success": False, "error": "用户名已存在"}), 409

        user = User(
            username=username,
            display_name=display_name or username,
            role=data.get('role', 'police'),
            department=data.get('department', ''),
            phone=data.get('phone', '')
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({"success": True, "message": "注册成功", "user": user.to_dict()}), 201

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"success": False, "error": "用户名或密码错误"}), 401
        if not user.is_active:
            return jsonify({"success": False, "error": "账号已被禁用"}), 403

        user.last_login = datetime.utcnow()
        db.session.commit()

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'role': user.role,
                'display_name': user.display_name
            }
        )
        refresh_token = create_refresh_token(identity=str(user.id))

        log_operation(user.id, user.username, 'login')

        return jsonify({
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        })

    @app.route('/api/auth/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "用户不存在"}), 404

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'role': user.role,
                'name': user.display_name
            }
        )
        return jsonify({"success": True, "access_token": access_token})

    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_me():
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        return jsonify({"success": True, "user": user.to_dict()})

    @app.route('/api/auth/logout', methods=['POST'])
    @jwt_required()
    def logout():
        jti = get_jwt()['jti']
        BLACKLIST.add(jti)
        return jsonify({"success": True, "message": "已退出登录"})

    @app.route('/api/auth/users', methods=['GET'])
    @jwt_required()
    def list_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify({"success": True, "users": [u.to_dict() for u in users]})

    @app.route('/api/auth/logs', methods=['GET'])
    @jwt_required()
    def get_logs():
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).limit(100).all()
        return jsonify({
            "success": True,
            "logs": [{
                'id': l.id,
                'username': l.username,
                'action': l.action,
                'target': f"{l.target_type}/{l.target_id}",
                'detail': l.detail,
                'ip_address': l.ip_address,
                'created_at': l.created_at.isoformat() if l.created_at else None
            } for l in logs]
        })