#!/bin/bash

# WoniuNote 数据库导入脚本
# 导入 docs/others/woniunote_db.sql 到 MySQL 数据库

set -e

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

# 数据库配置 (与 setup_ubuntu.sh 保持一致)
DB_NAME="${DB_NAME:-woniunote}"
DB_USER="${DB_USER:-woniunote}"
DB_PASS="${DB_PASS:-woniunote_password}"
DB_HOST="${DB_HOST:-localhost}"

# SQL 文件路径
SQL_FILE="$PROJECT_DIR/docs/others/woniunote_db.sql"

echo "========================================"
echo "  WoniuNote 数据库导入脚本"
echo "========================================"
echo ""

# 检查 SQL 文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    log_error "SQL 文件不存在: $SQL_FILE"
    exit 1
fi

log_info "SQL 文件: $SQL_FILE"
log_info "数据库: $DB_NAME"
log_info "用户: $DB_USER"
echo ""

# 检查 MySQL 服务
log_info "检查 MySQL 服务..."
if ! systemctl is-active --quiet mysql 2>/dev/null; then
    log_warn "MySQL 服务未运行，尝试启动..."
    sudo systemctl start mysql || {
        log_error "无法启动 MySQL 服务"
        exit 1
    }
fi

# 检查数据库是否存在，不存在则创建
log_info "检查数据库..."
if ! mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" -e "USE $DB_NAME" 2>/dev/null; then
    log_info "数据库 $DB_NAME 不存在，尝试使用 root 创建..."
    
    # 尝试使用 root 创建数据库和用户
    sudo mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || {
        log_error "无法创建数据库，请手动创建"
        exit 1
    }
    
    sudo mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'$DB_HOST' IDENTIFIED BY '$DB_PASS';" 2>/dev/null || true
    sudo mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$DB_HOST';" 2>/dev/null
    sudo mysql -e "FLUSH PRIVILEGES;" 2>/dev/null
    
    log_info "数据库和用户创建成功"
fi

# 导入 SQL 文件
log_info "开始导入 SQL 文件..."
if mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" "$DB_NAME" < "$SQL_FILE" 2>&1; then
    log_info "SQL 文件导入成功!"
else
    log_warn "使用用户 $DB_USER 导入失败，尝试使用 root..."
    if sudo mysql "$DB_NAME" < "$SQL_FILE" 2>&1; then
        log_info "SQL 文件导入成功! (使用 root)"
    else
        log_error "SQL 文件导入失败"
        exit 1
    fi
fi

# 显示导入的表
echo ""
log_info "已导入的表:"
mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null | tail -n +2 | while read table; do
    echo "  - $table"
done

echo ""
echo "========================================"
echo "  数据库导入完成!"
echo "========================================"
