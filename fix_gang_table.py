# -*- coding: utf-8 -*-
"""检查并修复 gang_case_relations 表缺失列（模型 vs 实际结构）"""
import sys
import pymysql

def log(msg):
    print(msg, flush=True)

try:
    pw = [l.split('=', 1)[1].strip() for l in open('.env', encoding='utf-8') if l.startswith('DB_PASSWORD=')][0]
    conn = pymysql.connect(host='localhost', user='root', password=pw, database='fraudlens')
    cur = conn.cursor()
    cur.execute('SHOW COLUMNS FROM gang_case_relations')
    cols = [r[0] for r in cur.fetchall()]
    log('实际列: ' + repr(cols))

    need = ['id', 'gang_id', 'case_id', 'similarity', 'relation_type', 'reason', 'matched_entities', 'added_at']
    missing = [c for c in need if c not in cols]
    log('缺失列: ' + repr(missing))

    ALTERS = {
        'relation_type': "ALTER TABLE gang_case_relations ADD COLUMN relation_type VARCHAR(30) DEFAULT 'gnn_cluster'",
        'reason': "ALTER TABLE gang_case_relations ADD COLUMN reason VARCHAR(500) DEFAULT ''",
        'matched_entities': 'ALTER TABLE gang_case_relations ADD COLUMN matched_entities TEXT',
        'added_at': 'ALTER TABLE gang_case_relations ADD COLUMN added_at DATETIME',
    }
    for c in missing:
        sql = ALTERS.get(c)
        log('PROCESSING column: ' + c + ' sql=' + (sql[:50] if sql else 'None'))
        if not sql:
            log('SKIP (no alter defined): ' + c)
            continue
        try:
            log('  executing...')
            cur.execute(sql)
            log('  committing...')
            conn.commit()
            log('OK added column: ' + c)
        except Exception as e:
            log('FAIL column ' + c + ': ' + repr(e))
            conn.rollback()
    conn.close()
    log('DONE')
except Exception as e:
    log('TOP-LEVEL ERROR: ' + repr(e))
    sys.exit(1)
