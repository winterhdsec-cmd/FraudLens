from flask_sqlalchemy import SQLAlchemy
from tools.response import logger

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        from . import models
        db.create_all()
        logger.info("数据库表已创建")