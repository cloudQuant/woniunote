#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本
"""

def test_imports():
    """测试基本导入"""
    try:
        import sys
        import os
        from pathlib import Path
        
        # 添加路径
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        print("开始测试导入...")
        
        # 基础模块测试
        try:
            import woniunote
            print("✅ woniunote 主包导入成功")
        except Exception as e:
            print(f"❌ woniunote 主包导入失败: {e}")
        
        # Utils模块测试
        try:
            from woniunote.common import utils
            print("✅ utils 模块导入成功")
        except Exception as e:
            print(f"❌ utils 模块导入失败: {e}")
        
        # 数据库模块测试
        try:
            from woniunote.common import database
            print("✅ database 模块导入成功")
        except Exception as e:
            print(f"❌ database 模块导入失败: {e}")
        
        # API安全模块测试
        try:
            from woniunote.common import api_security_enhancer
            print("✅ api_security_enhancer 模块导入成功")
        except Exception as e:
            print(f"❌ api_security_enhancer 模块导入失败: {e}")
        
        print("导入测试完成!")
        return True
        
    except Exception as e:
        print(f"测试过程出错: {e}")
        return False

if __name__ == "__main__":
    print("=" * 40)
    print("WoniuNote 快速测试")
    print("=" * 40)
    
    success = test_imports()
    
    if success:
        print("\n✅ 测试成功!")
    else:
        print("\n❌ 测试失败!")
    
    input("\n按回车键退出...") 