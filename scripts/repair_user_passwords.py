#!/usr/bin/env python3
import os
import hashlib
import logging
import yaml
import pymysql
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _find_config():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidates = [
        os.path.join(repo_root, 'configs', 'user_password_config.yaml'),
        os.path.join(repo_root, 'woniunote', 'configs', 'user_password_config.yaml'),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    return None

def _read_db_uri():
    cfg = _find_config()
    if cfg and 'database' in cfg:
        return cfg['database']['SQLALCHEMY_DATABASE_URI']
    return os.environ.get('SQLALCHEMY_DATABASE_URI', '')

def _parse_db_uri(db_uri):
    p = urlparse(db_uri)
    return {
        'host': p.hostname,
        'port': p.port or 3306,
        'user': p.username,
        'password': p.password,
        'database': p.path.lstrip('/')
    }

def _connect(db_info):
    return pymysql.connect(
        host=db_info['host'],
        port=db_info['port'],
        user=db_info['user'],
        password=db_info['password'],
        database=db_info['database'],
        charset='utf8mb4',
        autocommit=False
    )

def repair_passwords():
    cfg = _find_config() or {}
    db_info = _parse_db_uri(_read_db_uri())
    conn = _connect(db_info)
    cur = conn.cursor()
    try:
        cur.execute('SET SESSION sql_mode=""')
    except Exception:
        pass
    try:
        cur.execute("SELECT userid, username, password FROM users")
        rows = cur.fetchall()
        updates = 0
        # 1) 统一将非MD5的密码转为MD5
        for r in rows:
            userid, username, password = (r['userid'], r['username'], r['password']) if isinstance(r, dict) else r
            if password and len(password) != 32:
                newpwd = hashlib.md5(password.encode()).hexdigest()
                cur.execute("UPDATE users SET password=%s WHERE userid=%s", (newpwd, userid))
                updates += 1
        # 2) 强制重置管理员/编辑/用户为配置中的密码
        for role_key in ('admin', 'editor', 'user'):
            if role_key in cfg:
                uname = cfg[role_key].get('username')
                plain = cfg[role_key].get('password')
                if uname and plain:
                    md5pwd = hashlib.md5(plain.encode()).hexdigest()
                    cur.execute("UPDATE users SET password=%s WHERE username=%s", (md5pwd, uname))
        conn.commit()
        logger.info(f"Repaired {updates} password rows and reset configured accounts")
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def show_users():
    db_info = _parse_db_uri(_read_db_uri())
    conn = _connect(db_info)
    cur = conn.cursor()
    try:
        cur.execute("SELECT userid, username, role, LENGTH(password) AS plen FROM users ORDER BY userid")
        for row in cur.fetchall():
            userid, username, role, plen = row if not isinstance(row, dict) else (row['userid'], row['username'], row.get('role'), row['plen'])
            print(f"{userid}	{username}	{role}	len(password)={plen}")
    finally:
        cur.close(); conn.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Repair user passwords')
    parser.add_argument('--show', action='store_true', help='Show users and password lengths')
    parser.add_argument('--apply', action='store_true', help='Apply repairs/resets')
    args = parser.parse_args()
    if args.show:
        show_users()
    elif args.apply:
        repair_passwords()
    else:
        parser.print_help()
