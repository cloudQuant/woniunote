#!/bin/bash

# 创建数学训练数据库表脚本
# 使用 woniunote 用户凭据

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 数据库配置
DB_NAME="${DB_NAME:-woniunote}"
DB_USER="${DB_USER:-woniunote}"
DB_PASS="${DB_PASS:-woniunote_password}"
DB_HOST="${DB_HOST:-localhost}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/sql/08_math_training.sql"

echo "========================================"
echo "  创建数学训练数据库表"
echo "========================================"
echo ""

log_info "数据库: $DB_NAME"
log_info "用户: $DB_USER"
echo ""

# 检查 SQL 文件
if [ ! -f "$SQL_FILE" ]; then
    log_error "SQL 文件不存在: $SQL_FILE"
    exit 1
fi

# 执行 SQL
log_info "执行 SQL 文件..."
if mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" "$DB_NAME" < "$SQL_FILE" 2>&1; then
    log_info "数学训练表创建成功!"
else
    log_warn "使用 woniunote 用户失败，尝试使用 root..."
    if sudo mysql "$DB_NAME" < "$SQL_FILE" 2>&1; then
        log_info "数学训练表创建成功! (使用 root)"
    else
        log_error "创建失败"
        exit 1
    fi
fi

# 验证表
echo ""
log_info "验证表是否存在:"
mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" -e "USE $DB_NAME; SHOW TABLES LIKE 'math%';" 2>/dev/null | tail -n +2 | while read table; do
    echo "  ✓ $table"
done

echo ""
echo "========================================"
echo "  完成"
echo "========================================"
