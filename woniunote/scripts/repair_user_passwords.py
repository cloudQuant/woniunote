#!/usr/bin/env python3
import os
import sys
import hashlib
import logging
import yaml
from woniunote.common.utils import parse_db_uri, get_db_connection

def _read_db_uri():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidates = [
        os.path.join(repo_root, 'configs', 'user_password_config.yaml'),
        os.path.join(repo_root, 'woniunote', 'configs', 'user_password_config.yaml'),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
                return cfg['database']['SQLALCHEMY_DATABASE_URI']
    return os.environ.get('SQLALCHEMY_DATABASE_URI', '')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_passwords():
    db_info = parse_db_uri(_read_db_uri())
    conn = get_db_connection(db_info)
    cur = conn.cursor()
    try:
        cur.execute('SET SESSION sql_mode=""')
    except Exception:
        pass
    try:
        cur.execute("SELECT userid, username, password FROM users")
        rows = cur.fetchall()
        updates = 0
        for r in rows:
            userid, username, password = (r['userid'], r['username'], r['password']) if isinstance(r, dict) else r
            if password and len(password) != 32:
                newpwd = hashlib.md5(password.encode()).hexdigest()
                cur.execute("UPDATE users SET password=%s WHERE userid=%s", (newpwd, userid))
                updates += 1
        conn.commit()
        logger.info(f"Repaired {updates} password rows")
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    repair_passwords()
