from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        from . import models
        db.create_all()
        print("✅ 数据库表已创建")