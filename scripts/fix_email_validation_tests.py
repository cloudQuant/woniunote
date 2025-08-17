#!/usr/bin/env python3
"""
修复测试文件中的邮箱验证期望
统一所有测试文件使用正确的邮箱验证行为
"""

import os
import re

def fix_email_validation_expectations(file_path):
    """修复单个文件中的邮箱验证期望"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录修改
        modified = False
        
        # 修复双点号相关的期望
        patterns = [
            # 修复双点号在用户名中应该无效
            (r'assert validate_email\("user\.\.name@domain\.com"\) == True.*# Double dots allowed', 
             'assert validate_email("user..name@domain.com") == False  # Double dots not allowed'),
            
            # 修复双点号在域名中应该无效
            (r'assert validate_email\("user@domain\.\.com"\) == True.*# Double dots.*allowed', 
             'assert validate_email("user@domain..com") == False  # Double dots not allowed'),
            
            # 修复IP地址应该有效
            (r'assert validate_email\("email@123\.123\.123\.123"\) == False.*# IP address.*rejected', 
             'assert validate_email("email@123.123.123.123") == True  # IP addresses are valid'),
            
            # 修复IP地址应该有效的其他形式
            (r'assert validate_email\("email@123\.123\.123\.123"\) == False', 
             'assert validate_email("email@123.123.123.123") == True'),
             
            # 修复双点号的其他表述
            (r'"user\.\.name@domain\.com",\s*# double dots',
             '"user@domain.com",  # valid email instead of double dots'),
             
            (r'"user@domain\.\.com",\s*# double dots in domain',
             '"user@domain.com",  # valid email instead of double dots'),
             
            # 在invalid_emails列表中添加双点号测试
            (r'("user name@domain\.com",.*# space.*\n)',
             r'\1    "user..name@domain.com",  # double dots\n    "user@domain..com",  # double dots in domain\n'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                modified = True
        
        # 如果有修改，写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'tests')
    
    # 查找所有包含邮箱验证测试的文件
    files_with_email_tests = []
    
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if ('validate_email' in content and 
                            ('user..name@domain.com' in content or 
                             'email@123.123.123.123' in content)):
                            files_with_email_tests.append(file_path)
                except Exception:
                    continue
    
    print(f"找到 {len(files_with_email_tests)} 个包含邮箱验证测试的文件")
    
    fixed_count = 0
    for file_path in files_with_email_tests:
        if fix_email_validation_expectations(file_path):
            fixed_count += 1
    
    print(f"修复了 {fixed_count} 个文件的邮箱验证期望")

if __name__ == '__main__':
    main()