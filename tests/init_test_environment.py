#!/usr/bin/env python3
"""
WoniuNote 测试环境初始化脚本
用于设置完整的测试环境和测试数据
"""

import os
import sys
import shutil
import sqlite3
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_test_directories():
    """创建测试目录结构"""
    print("📁 创建测试目录结构...")

    test_dirs = [
        'tests/test_db',
        'tests/test_uploads',
        'tests/test_sessions',
        'tests/test_logs',
        'htmlcov',
        'test_reports'
    ]

    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  [SUCCESS] {dir_path}")

def setup_test_database():
    """设置测试数据库"""
    print("\n🗄️ 设置测试数据库...")

    # 检查是否使用SQLite
    test_db_path = Path('tests/test_db/woniunote_test.db')

    if test_db_path.exists():
        test_db_path.unlink()
        print("  🗑️ 删除旧的测试数据库")

    # 创建SQLite测试数据库
    conn = sqlite3.connect(str(test_db_path))
    conn.close()

    print(f"  [SUCCESS] SQLite测试数据库创建完成: {test_db_path}")

    # 设置环境变量
    os.environ['DATABASE_URL'] = f'sqlite:///{test_db_path}'
    os.environ['TEST_DATABASE_URL'] = f'sqlite:///{test_db_path}'

def create_test_data():
    """创建测试数据"""
    print("\n📝 创建测试数据...")

    # 导入必要的模块
    try:
        from woniunote.common.database import get_db
        from woniunote.models.card import Card
        from woniunote.models.todo import Todo
        import datetime

        # 创建测试数据
        db = get_db()

        # 创建测试卡片
        test_cards = [
            Card(
                title=f'测试卡片 {i}',
                content=f'这是测试卡片 {i} 的内容',
                user_id=1,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            ) for i in range(1, 6)
        ]

        # 创建测试待办事项
        test_todos = [
            Todo(
                title=f'测试待办事项 {i}',
                content=f'这是测试待办事项 {i} 的内容',
                user_id=1,
                status='pending' if i % 2 == 0 else 'completed',
                priority=['low', 'medium', 'high'][i % 3],
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            ) for i in range(1, 4)
        ]

        # 添加到数据库
        for card in test_cards:
            db.add(card)
        for todo in test_todos:
            db.add(todo)

        db.commit()

        print(f"  [SUCCESS] 创建了 {len(test_cards)} 个测试卡片")
        print(f"  [SUCCESS] 创建了 {len(test_todos)} 个测试待办事项")

    except Exception as e:
        print(f"  [WARN]️ 创建测试数据失败: {e}")
        print("  [TIP] 这不会影响测试运行")

def setup_test_config():
    """设置测试配置文件"""
    print("\n⚙️ 设置测试配置...")

    # 复制配置文件
    config_files = [
        ('configs/user_password_config.yaml', 'tests/configs/user_password_config.yaml'),
        ('configs/article_type_config.yaml', 'tests/configs/article_type_config.yaml')
    ]

    for src, dst in config_files:
        if Path(src).exists():
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  [SUCCESS] 复制配置文件: {src} -> {dst}")
        else:
            print(f"  [WARN]️ 源配置文件不存在: {src}")

def validate_test_environment():
    """验证测试环境"""
    print("\n[SEARCH] 验证测试环境...")

    # 检查关键模块导入
    critical_modules = [
        'woniunote',
        'woniunote.common.utils',
        'woniunote.common.database',
        'woniunote.models.card',
        'woniunote.models.todo',
        'pytest',
        'flask'
    ]

    success_count = 0
    for module in critical_modules:
        try:
            __import__(module)
            print(f"  [SUCCESS] {module}")
            success_count += 1
        except ImportError as e:
            print(f"  [ERROR] {module}: {e}")

    success_rate = (success_count / len(critical_modules)) * 100
    print(f"  [REPORT] 模块导入成功率: {success_rate:.1f}%")
    if success_rate >= 80:
        print("  [GREAT] 测试环境验证通过！")
        return True
    else:
        print("  [WARN]️ 部分模块导入失败，请检查依赖安装")
        return False

def collect_test_statistics():
    """收集测试统计信息"""
    print("\n[STATS] 收集测试统计信息...")

    # 统计测试文件数量
    test_files = list(Path('tests').rglob('test_*.py'))
    unit_tests = list(Path('tests/unit').glob('test_*.py'))
    integration_tests = [f for f in test_files if 'integration' in str(f).lower() or 'comprehensive' in str(f).lower()]

    print(f"  📁 总测试文件数: {len(test_files)}")
    print(f"  [FIX] 单元测试文件: {len(unit_tests)}")
    print(f"  🔗 集成测试文件: {len(integration_tests)}")

    # 尝试收集测试用例数量
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', '--collect-only', '-q'],
            capture_output=True, text=True, cwd=project_root
        )

        if result.returncode == 0:
            lines = result.stdout.split('\n')
            collected_count = sum(1 for line in lines if '::' in line and ('test_' in line or 'Test' in line))
            print(f"  📋 收集到的测试用例: {collected_count}")
    except Exception as e:
        print(f"  [WARN]️ 无法收集测试用例统计: {e}")

def main():
    """主函数"""
    print("[START] WoniuNote 测试环境初始化开始")
    print("=" * 60)

    try:
        # 执行各个设置步骤
        setup_test_directories()
        setup_test_database()
        setup_test_config()
        create_test_data()

        # 验证环境
        if validate_test_environment():
            collect_test_statistics()

            print("\n" + "=" * 60)
            print("[GREAT] 测试环境初始化完成！")
            print("\n📋 现在可以运行以下命令：")
            print("  • python -m pytest tests/ -v                    # 运行所有测试")
            print("  • python -m pytest --cov=woniunote              # 覆盖率测试")
            print("  • python -m pytest tests/unit/ -v               # 单元测试")
            print("  • python -m pytest tests/ -k 'comprehensive'    # 综合测试")
            print("  • open htmlcov/index.html                       # 查看覆盖率报告")
            print("\n📁 测试文件位置：")
            print("  • 测试数据库: tests/test_db/woniunote_test.db")
            print("  • 覆盖率报告: htmlcov/")
            print("  • 测试配置: tests/configs/")
            return True
        else:
            print("\n[ERROR] 测试环境初始化失败，请检查错误信息")
            return False

    except Exception as e:
        print(f"\n[ERROR] 初始化过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
