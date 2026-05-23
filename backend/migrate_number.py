"""迁移: 添加number字段并回填"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'key.env'))

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
DB_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

engine = create_engine(DB_URI)
with engine.connect() as conn:
    for table in ['cases', 'gangs']:
        columns = [c['name'] for c in inspect(engine).get_columns(table)]
        if 'number' not in columns:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN number INTEGER DEFAULT 0'))
            print(f'已添加 number 列到 {table}')
    
    conn.execute(text('SET @row_num = 0'))
    conn.execute(text('UPDATE cases SET number = (@row_num := @row_num + 1) ORDER BY id'))
    r = conn.execute(text('SELECT COUNT(*) FROM cases')).scalar()
    print(f'已回填 {r} 条案件编号')
    
    conn.execute(text('SET @row_num = 0'))
    conn.execute(text('UPDATE gangs SET number = (@row_num := @row_num + 1) ORDER BY id'))
    r = conn.execute(text('SELECT COUNT(*) FROM gangs')).scalar()
    print(f'已回填 {r} 条团伙编号')
    
    conn.commit()
print('迁移完成')