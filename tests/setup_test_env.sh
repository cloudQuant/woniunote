#!/bin/bash
# WoniuNote 测试环境设置脚本
# 使用方法: source tests/setup_test_env.sh

echo "🚀 设置 WoniuNote 测试环境..."

# 读取MySQL配置
TEST_CONFIG_FILE="tests/configs/user_password_config.yaml"
if [ -f "$TEST_CONFIG_FILE" ]; then
    echo "📋 读取测试配置文件: $TEST_CONFIG_FILE"
    # 从YAML文件中提取MySQL连接字符串
    MYSQL_URI=$(grep "SQLALCHEMY_DATABASE_URI:" "$TEST_CONFIG_FILE" | cut -d':' -f2- | xargs)
    
    if [[ "$MYSQL_URI" == mysql* ]]; then
        echo "🗄️  使用MySQL测试数据库"
        export DATABASE_URL="$MYSQL_URI"
        export TEST_DATABASE_URL="$MYSQL_URI"
        DB_TYPE="MySQL"
        DB_HOST=$(echo "$MYSQL_URI" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_NAME=$(echo "$MYSQL_URI" | sed -n 's/.*\/\([^?]*\).*/\1/p')
        echo "   主机: $DB_HOST"
        echo "   数据库: $DB_NAME"
    else
        echo "⚠️  配置文件中未找到MySQL配置，使用SQLite"
        export DATABASE_URL=sqlite:///test_woniunote.db
        export TEST_DATABASE_URL=sqlite:///test_woniunote.db
        DB_TYPE="SQLite"
    fi
else
    echo "⚠️  测试配置文件不存在，使用默认SQLite配置"
    export DATABASE_URL=sqlite:///test_woniunote.db
    export TEST_DATABASE_URL=sqlite:///test_woniunote.db
    DB_TYPE="SQLite"
fi

# 设置其他测试环境变量
export TESTING=True
export FLASK_ENV=testing
export SECRET_KEY=test-secret-key-woniunote-2025
export SKIP_APP_INIT=True
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PYTEST_TIMEOUT=10

# 检查项目包是否已安装
if ! python -c "import woniunote" 2>/dev/null; then
    echo "📦 安装项目包..."
    pip install -e .
else
    echo "✅ 项目包已安装"
fi

# 数据库连接测试
echo ""
echo "🔍 测试数据库连接..."
if [[ "$DB_TYPE" == "MySQL" ]]; then
    # 测试MySQL连接
    python -c "
import pymysql
import sys
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

try:
    db_url = '$DATABASE_URL'
    # 解析数据库连接URL
    parsed = urlparse(db_url.replace('mysql://', 'mysql+pymysql://'))
    
    # 创建引擎测试连接
    engine = create_engine(db_url.replace('mysql://', 'mysql+pymysql://'))
    with engine.connect() as conn:
        result = conn.execute(text('SELECT VERSION()'))
        version = result.fetchone()[0]
        print(f'✅ MySQL连接成功 - 版本: {version}')
        
        # 测试数据库是否存在
        db_name = parsed.path[1:]  # 移除开头的/
        result = conn.execute(text('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db_name'), {'db_name': db_name})
        if result.fetchone():
            print(f'✅ 数据库 {db_name} 存在')
        else:
            print(f'⚠️  数据库 {db_name} 不存在，可能需要创建')
    
except Exception as e:
    print(f'❌ MySQL连接失败: {str(e)}')
    print('💡 请检查：')
    print('   1. MySQL服务是否运行')
    print('   2. 数据库用户名密码是否正确')
    print('   3. 数据库是否存在')
    print('   4. 是否安装了pymysql: pip install pymysql')
    sys.exit(1)
" 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "❌ MySQL连接测试失败"
        echo "💡 建议解决方案："
        echo "   1. 启动MySQL服务: brew services start mysql 或 systemctl start mysql"
        echo "   2. 创建测试数据库: CREATE DATABASE woniunote;"
        echo "   3. 创建用户并授权: GRANT ALL ON woniunote.* TO 'woniunote_user'@'localhost';"
        echo "   4. 安装依赖: pip install pymysql mysqlclient"
        echo ""
        echo "🔄 如果MySQL不可用，可以修改配置文件使用SQLite"
        echo "   编辑 tests/configs/user_password_config.yaml"
        echo "   将SQLALCHEMY_DATABASE_URI改为: sqlite:///test_woniunote.db"
        return 1
    fi
else
    # SQLite连接测试
    echo "✅ 使用SQLite数据库，无需连接测试"
    # 创建测试数据库目录
    mkdir -p instance 2>/dev/null
fi

echo ""
echo "✅ 测试环境设置完成！"
echo ""
echo "📋 环境配置:"
echo "   数据库类型: $DB_TYPE"
echo "   TESTING = $TESTING"
echo "   FLASK_ENV = $FLASK_ENV"
echo "   DATABASE_URL = $DATABASE_URL"
echo ""
echo "🧪 现在可以运行测试了："
echo "   python -m pytest tests/unit/ -v                   # 单元测试"
echo "   python -m pytest tests/ -k comprehensive -v       # 综合测试"
echo "   python -m pytest tests/ --cov=woniunote -v        # 覆盖率测试"
echo ""
echo "🔧 高级选项："
echo "   python -m pytest tests/test_simple_working.py -v   # 快速验证"
echo "   python -m pytest tests/ --cov=woniunote --cov-report=html # HTML覆盖率报告"
