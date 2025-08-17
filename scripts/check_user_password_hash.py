#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check password hash format for a specific user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from woniunote.common.utils import get_db_connection, read_config

def check_password_hash_format(email):
    """Check the password hash format for a given user email."""
    # 读取数据库配置
    config = read_config()
    if not config or 'database' not in config:
        print("Error: Unable to read database configuration")
        return
    
    database_info = config['database']
    conn = get_db_connection(database_info)
    
    if not conn:
        print("Error: Unable to connect to database")
        return
        
    cursor = conn.cursor()
    
    try:
        # Query user by email
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
                    print(f"Salt + hash: {parts[3]}")
            elif password_hash.startswith('pbkdf2:'):
                print("Hash format: PBKDF2")
                parts = password_hash.split(':')
                if len(parts) >= 3:
                    print(f"Algorithm: {parts[0]}")
                    print(f"Hash method: {parts[1]}")
                    print(f"Iterations: {parts[2].split('$')[0] if '$' in parts[2] else 'N/A'}")
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
                print(f"Hash preview: {password_hash[:20]}...{password_hash[-10:]}")
            else:
                print(f"Full hash: {password_hash}")
                
        else:
            print(f"User with email {email} not found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    email = "yunjinqi@qq.com"
    check_password_hash_format(email)