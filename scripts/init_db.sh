#!/bin/bash

# WoniuNote 数据库初始化脚本
# 用于创建或更新数据库表结构

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SQL_DIR="$SCRIPT_DIR/sql"

# 数据库配置 (可通过环境变量覆盖)
DB_NAME="${DB_NAME:-woniunote}"
DB_USER="${DB_USER:-}"
DB_PASS="${DB_PASS:-}"
DB_HOST="${DB_HOST:-localhost}"

echo "========================================"
echo "  WoniuNote 数据库初始化脚本"
echo "========================================"
echo ""

# 构建 MySQL 连接命令
build_mysql_cmd() {
    local cmd="mysql"
    if [ -n "$DB_USER" ]; then
        cmd="$cmd -u $DB_USER"
        if [ -n "$DB_PASS" ]; then
            cmd="$cmd -p$DB_PASS"
        fi
    fi
    if [ "$DB_HOST" != "localhost" ]; then
        cmd="$cmd -h $DB_HOST"
    fi
    echo "$cmd"
}

MYSQL_CMD=$(build_mysql_cmd)

# 检查数据库连接
log_info "检查数据库连接..."
if ! $MYSQL_CMD -e "SELECT 1" >/dev/null 2>&1; then
    log_error "无法连接到 MySQL 服务器"
    log_error "请确保 MySQL 服务正在运行，或设置正确的环境变量:"
    log_error "  DB_USER=用户名 DB_PASS=密码 DB_HOST=主机 bash $0"
    exit 1
fi

# 检查数据库是否存在
log_info "检查数据库 $DB_NAME..."
if ! $MYSQL_CMD -e "USE $DB_NAME" 2>/dev/null; then
    log_warn "数据库 $DB_NAME 不存在，正在创建..."
    $MYSQL_CMD -e "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    log_info "数据库 $DB_NAME 创建成功"
fi

# 执行 SQL 文件
log_info "执行 SQL 初始化脚本..."
if [ -d "$SQL_DIR" ]; then
    for sql_file in "$SQL_DIR"/*.sql; do
        if [ -f "$sql_file" ]; then
            filename=$(basename "$sql_file")
            log_info "  执行: $filename"
            if $MYSQL_CMD "$DB_NAME" < "$sql_file" 2>/dev/null; then
                log_info "  ✓ $filename 执行成功"
            else
                log_warn "  ⚠ $filename 执行时有警告 (可能表已存在)"
            fi
        fi
    done
else
    log_error "SQL 目录不存在: $SQL_DIR"
    exit 1
fi

echo ""
log_info "数据库初始化完成!"
echo ""

# 显示当前表
log_info "当前数据库表:"
$MYSQL_CMD -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null | tail -n +2 | while read table; do
    echo "  - $table"
done

echo ""
echo "========================================"
