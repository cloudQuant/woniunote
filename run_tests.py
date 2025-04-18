#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WoniuNote测试运行器

该脚本运行WoniuNote项目的所有测试用例，包括：
1. 单元测试
2. 功能测试 (卡片、待办事项)
3. 模型验证

使用：
    python run_tests.py [选项]

选项：
    --cards-only: 只运行卡片测试
    --todos-only: 只运行待办事项测试
    --unit-only: 只运行单元测试
    --model-only: 只运行模型验证
    --direct: 使用直接测试方式（不使用pytest）
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('woniunote_test_runner')

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行WoniuNote测试')
    parser.add_argument('--cards-only', action='store_true', help='只运行卡片测试')
    parser.add_argument('--todos-only', action='store_true', help='只运行待办事项测试')
    parser.add_argument('--unit-only', action='store_true', help='只运行单元测试')
    parser.add_argument('--model-only', action='store_true', help='只运行模型验证')
    parser.add_argument('--direct', action='store_true', help='使用直接测试方式（不使用pytest）')
    return parser.parse_args()

def run_tests(test_paths, description):
    """运行指定的测试路径"""
    logger.info(f"运行{description}...")
    
    success = True
    for test_path in test_paths:
        # 确保测试路径存在
        if not os.path.exists(test_path):
            logger.warning(f"测试路径不存在: {test_path}")
            continue
        
        logger.info(f"测试: {test_path}")
        
        # 构建pytest命令
        cmd = [
            sys.executable, "-m", "pytest", 
            test_path,
            "-v",  # 详细输出
            "--disable-warnings",  # 禁用警告
        ]
        
        # 运行测试
        try:
            # 添加环境变量以确保测试不尝试连接远程服务器
            env = os.environ.copy()
            env["TESTING"] = "1"
            env["WTF_CSRF_ENABLED"] = "0"
            env["SERVER_NAME"] = ""
            
            process = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,  # 即使测试失败也不抛出异常
                env=env  # 使用修改后的环境变量
            )
            
            # 输出测试结果
            if process.stdout:
                print(process.stdout)
            
            if process.stderr and len(process.stderr.strip()) > 0:
                logger.warning("测试过程中出现警告或错误:")
                print(process.stderr)
            
            if process.returncode != 0:
                success = False
                logger.error(f"测试失败: {test_path}")
            else:
                logger.info(f"✅ 测试通过: {test_path}")
                
        except Exception as e:
            success = False
            logger.error(f"运行测试时出错: {e}")
            import traceback
            traceback.print_exc()
    
    return success

def run_card_tests(direct=False):
    """运行卡片测试"""
    if direct:
        # 使用直接测试方式
        return run_direct_card_test()
    else:
        # 使用pytest方式
        test_paths = [
            # 简化版卡片测试文件
            os.path.join(PROJECT_ROOT, "tests", "functional", "cards", "test_cards_simplified.py"),
        ]
        return run_tests(test_paths, "卡片测试")

def run_direct_card_test():
    """直接运行卡片测试，不使用pytest"""
    logger.info("运行直接卡片测试...")
    
    test_script = os.path.join(PROJECT_ROOT, "tests", "card_minimal_test.py")
    if not os.path.exists(test_script):
        logger.error(f"测试脚本不存在: {test_script}")
        return False
    
    try:
        cmd = [sys.executable, test_script]
        process = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.stdout:
            print(process.stdout)
        
        if process.stderr and len(process.stderr.strip()) > 0:
            logger.warning("测试警告或错误:")
            print(process.stderr)
        
        if process.returncode == 0:
            logger.info("✅ 直接卡片测试通过!")
            return True
        else:
            logger.error(f"❌ 直接卡片测试失败! 退出代码: {process.returncode}")
            return False
    
    except Exception as e:
        logger.error(f"运行直接测试时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_todo_tests():
    """运行待办事项测试"""
    test_paths = [
        os.path.join(PROJECT_ROOT, "tests", "functional", "todos"),
    ]
    return run_tests(test_paths, "待办事项测试")

def run_unit_tests():
    """运行单元测试"""
    test_paths = [
        os.path.join(PROJECT_ROOT, "tests", "unit"),
    ]
    return run_tests(test_paths, "单元测试")

def run_model_verification():
    """运行模型验证"""
    logger.info("运行模型验证...")
    
    # 卡片模型验证
    card_model_script = os.path.join(PROJECT_ROOT, "tests", "verify_card_model_fixed.py")
    if os.path.exists(card_model_script):
        cmd = [sys.executable, card_model_script]
        
        try:
            process = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False
            )
            
            print(process.stdout)
            if process.stderr and "ERROR" in process.stderr:
                print("错误输出:")
                print(process.stderr)
            
            if process.returncode != 0:
                logger.error("卡片模型验证失败")
                return False
            
            logger.info("卡片模型验证成功")
            return True
        
        except Exception as e:
            logger.error(f"运行模型验证时出错: {e}")
            return False
    else:
        logger.warning(f"模型验证脚本不存在: {card_model_script}")
        return False

def run_all_tests(direct=False):
    """运行所有测试"""
    results = []
    
    # 运行单元测试
    unit_success = run_unit_tests()
    results.append(("单元测试", unit_success))
    
    # 运行卡片测试
    cards_success = run_card_tests(direct)
    results.append(("卡片测试", cards_success))
    
    # 运行待办事项测试
    todos_success = run_todo_tests()
    results.append(("待办事项测试", todos_success))
    
    # 运行模型验证
    model_success = run_model_verification()
    results.append(("模型验证", model_success))
    
    # 显示测试结果摘要
    logger.info("\n测试结果摘要:")
    all_success = True
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{name}: {status}")
        all_success = all_success and success
    
    return 0 if all_success else 1

if __name__ == "__main__":
    args = parse_args()
    
    # 确定是否使用直接测试模式
    direct_mode = args.direct
    
    if args.cards_only:
        success = run_card_tests(direct_mode)
    elif args.todos_only:
        success = run_todo_tests()
    elif args.unit_only:
        success = run_unit_tests()
    elif args.model_only:
        success = run_model_verification()
    else:
        success = run_all_tests(direct_mode) == 0
    
    sys.exit(0 if success else 1)
