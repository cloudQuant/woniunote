#!/bin/bash

# WoniuNote 数据库状态检查脚本
# 检查数据库是否正常，显示表数量和每个表的行数

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 数据库配置
DB_NAME="${DB_NAME:-woniunote}"
DB_USER="${DB_USER:-woniunote}"
DB_PASS="${DB_PASS:-woniunote_password}"
DB_HOST="${DB_HOST:-localhost}"

echo "========================================"
echo "  WoniuNote 数据库状态检查"
echo "========================================"
echo ""

# 检查 MySQL 服务
echo -n "MySQL 服务状态: "
if systemctl is-active --quiet mysql 2>/dev/null; then
    echo -e "${GREEN}运行中${NC}"
else
    echo -e "${RED}未运行${NC}"
    log_error "MySQL 服务未运行，请先启动: sudo systemctl start mysql"
    exit 1
fi

# 检查数据库连接
echo -n "数据库连接: "
if mysql -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" -e "SELECT 1" &>/dev/null; then
    echo -e "${GREEN}正常${NC}"
    MYSQL_CMD="mysql -u$DB_USER -p$DB_PASS -h$DB_HOST"
elif sudo mysql -e "SELECT 1" &>/dev/null; then
    echo -e "${GREEN}正常 (使用 root)${NC}"
    MYSQL_CMD="sudo mysql"
else
    echo -e "${RED}失败${NC}"
    log_error "无法连接到 MySQL"
    exit 1
fi

# 检查数据库是否存在
echo -n "数据库 $DB_NAME: "
if $MYSQL_CMD -e "USE $DB_NAME" &>/dev/null; then
    echo -e "${GREEN}存在${NC}"
else
    echo -e "${RED}不存在${NC}"
    log_error "数据库 $DB_NAME 不存在"
    exit 1
fi

echo ""
echo "========================================"
echo "  表统计信息"
echo "========================================"
echo ""

# 获取表列表
TABLES=$($MYSQL_CMD -N -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null)
TABLE_COUNT=$(echo "$TABLES" | wc -l)

if [ -z "$TABLES" ]; then
    log_warn "数据库中没有表"
    exit 0
fi

log_info "数据库共有 ${CYAN}$TABLE_COUNT${NC} 个表"
echo ""

# 表头
printf "%-35s %10s\n" "表名" "行数"
printf "%-35s %10s\n" "-----------------------------------" "----------"

TOTAL_ROWS=0

# 遍历每个表，获取行数
for table in $TABLES; do
    ROW_COUNT=$($MYSQL_CMD -N -e "SELECT COUNT(*) FROM $DB_NAME.$table;" 2>/dev/null)
    if [ -z "$ROW_COUNT" ]; then
        ROW_COUNT="错误"
    else
        TOTAL_ROWS=$((TOTAL_ROWS + ROW_COUNT))
    fi
    printf "%-35s %10s\n" "$table" "$ROW_COUNT"
done

echo ""
printf "%-35s %10s\n" "-----------------------------------" "----------"
printf "%-35s ${CYAN}%10s${NC}\n" "总计" "$TOTAL_ROWS"

echo ""
echo "========================================"
echo "  检查完成"
echo "========================================"
