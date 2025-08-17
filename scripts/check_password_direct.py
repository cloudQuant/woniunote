#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Direct database connection to check password hash."""

import pymysql
import yaml
import os
from urllib.parse import urlparse

# Read database configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs', 'user_password_config.yaml')

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    # Parse SQLAlchemy URI
    db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
    # Remove the mysql+pymysql:// prefix to parse properly
    if db_uri.startswith('mysql+pymysql://'):
        db_uri = db_uri.replace('mysql+pymysql://', 'mysql://')
    
    parsed = urlparse(db_uri)
    
    db_config = {
        'host': parsed.hostname,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
        'port': parsed.port or 3306
    }
    
    # Connect to database
    conn = pymysql.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        port=db_config.get('port', 3306),
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # Query user
    email = "yunjinqi@qq.com"
    cursor.execute("SELECT username, password FROM users WHERE email = %s", (email,))
    result = cursor.fetchone()
    
    if result:
        username, password_hash = result
        print(f"User found: {username} ({email})")
        print(f"Password hash: {password_hash}")
        print(f"Hash length: {len(password_hash)}")
        
        # Check hash format
        if password_hash.startswith('$2b$'):
            print("Hash format: bcrypt")
            parts = password_hash.split('$')
            if len(parts) >= 4:
                print(f"Algorithm: {parts[1]}")
                print(f"Cost factor: {parts[2]}")
        elif password_hash.startswith('pbkdf2:'):
            print("Hash format: PBKDF2 (Werkzeug)")
            parts = password_hash.split(':')
            if len(parts) >= 3:
                print(f"Algorithm: {parts[0]}")
                print(f"Hash method: {parts[1]}")
                if '$' in parts[2]:
                    iterations_part = parts[2].split('$')[0]
                    print(f"Iterations: {iterations_part}")
        elif password_hash.startswith('scrypt:'):
            print("Hash format: scrypt (Werkzeug)")
        elif len(password_hash) == 32:
            print("Hash format: Possibly MD5 (32 characters)")
        elif len(password_hash) == 40:
            print("Hash format: Possibly SHA-1 (40 characters)")
        elif len(password_hash) == 64:
            print("Hash format: Possibly SHA-256 (64 characters)")
        else:
            print("Hash format: Unknown")
            
        # Show first and last few characters
        if len(password_hash) > 20:
            print(f"Hash preview: {password_hash[:30]}...{password_hash[-20:]}")
        else:
            print(f"Full hash: {password_hash}")
    else:
        print(f"User with email {email} not found.")
        
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()