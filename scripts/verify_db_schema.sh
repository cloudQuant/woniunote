#!/bin/bash

# WoniuNote 数据库表结构核对脚本
# Database Schema Verification Script
# 用于检查现有数据库表结构与预期schema的差异

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_diff() { echo -e "${BLUE}[DIFF]${NC} $1"; }

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/db_schema_verify_$(date +%Y%m%d_%H%M%S).log"

# 数据库配置 (可通过环境变量覆盖)
DB_NAME="${DB_NAME:-woniunote}"
DB_USER="${DB_USER:-}"
DB_PASS="${DB_PASS:-}"
DB_HOST="${DB_HOST:-localhost}"

# 预期的表结构定义
declare -A EXPECTED_TABLES
EXPECTED_TABLES=(
    ["users"]="userid,username,password,nickname,avatar,qq,role,credit,createtime,updatetime"
    ["article"]="articleid,userid,type,headline,content,thumbnail,credit,readcount,replycount,recommended,hidden,drafted,checked,createtime,updatetime"
    ["comment"]="commentid,userid,articleid,content,ipaddr,replyid,agreecount,opposecount,hidden,createtime,updatetime"
    ["favorite"]="favoriteid,userid,articleid,canceled,createtime,updatetime"
    ["credit"]="creditid,userid,category,target,credit,createtime,updatetime"
    ["article_category"]="id,parent_id,name,sort_order,visible,createtime,updatetime"
    ["category"]="id,name"
    ["cardcategory"]="id,name"
    ["card"]="id,type,headline,content,createtime,updatetime,donetime,usedtime,begintime,endtime,cardcategory_id"
    ["item"]="id,body,category_id"
    ["math_training_records"]="id,user_id,difficulty,total_questions,correct_count,wrong_count,accuracy,start_time,end_time,duration_seconds,created_at"
    ["math_training_wrong_answers"]="id,record_id,user_id,question,correct_answer,user_answer,operation,difficulty,created_at"
    ["comment_votes"]="id,commentid,userid,vote_type,createtime"
)

# 预期的索引定义
declare -A EXPECTED_INDEXES
EXPECTED_INDEXES=(
    ["users"]="PRIMARY,uk_username,idx_role"
    ["article"]="PRIMARY,idx_userid,idx_type,idx_createtime,idx_recommended,idx_hidden_drafted,fk_article_user"
    ["comment"]="PRIMARY,idx_userid,idx_articleid,idx_replyid,idx_createtime"
    ["favorite"]="PRIMARY,uk_user_article,idx_userid,idx_articleid"
    ["credit"]="PRIMARY,idx_userid,idx_category,idx_createtime"
    ["article_category"]="PRIMARY,idx_parent_sort,idx_visible_sort"
    ["math_training_records"]="PRIMARY,idx_user_id,idx_difficulty,idx_created_at"
    ["math_training_wrong_answers"]="PRIMARY,idx_record_id,idx_user_id,idx_difficulty,idx_operation,idx_created_at"
)

echo "========================================"
echo "  WoniuNote 数据库表结构核对工具"
echo "========================================"
echo ""

# 创建日志目录
mkdir -p "$LOG_DIR"

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
    exit 1
fi

# 检查数据库是否存在
if ! $MYSQL_CMD -e "USE $DB_NAME" 2>/dev/null; then
    log_error "数据库 $DB_NAME 不存在"
    exit 1
fi

log_info "连接到数据库: $DB_NAME"
log_info "日志文件: $LOG_FILE"
echo ""

# 写入日志头
{
    echo "=========================================="
    echo "WoniuNote 数据库表结构核对报告"
    echo "时间: $(date)"
    echo "数据库: $DB_NAME"
    echo "=========================================="
    echo ""
} > "$LOG_FILE"

TOTAL_ISSUES=0
MISSING_TABLES=0
EXTRA_COLUMNS=0
MISSING_COLUMNS=0
INDEX_ISSUES=0

# 获取数据库中的所有表
ACTUAL_TABLES=$($MYSQL_CMD -N -e "USE $DB_NAME; SHOW TABLES;" 2>/dev/null)

# 检查每个预期表
log_info "开始核对表结构..."
echo ""

for table in "${!EXPECTED_TABLES[@]}"; do
    echo -n "检查表 $table... "
    
    # 检查表是否存在
    if ! echo "$ACTUAL_TABLES" | grep -q "^${table}$"; then
        log_warn "表不存在: $table"
        echo "[表不存在] $table" >> "$LOG_FILE"
        ((MISSING_TABLES++))
        ((TOTAL_ISSUES++))
        continue
    fi
    
    # 获取实际列
    ACTUAL_COLUMNS=$($MYSQL_CMD -N -e "USE $DB_NAME; SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='$table' ORDER BY ORDINAL_POSITION;" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    
    # 预期列
    EXPECTED_COLUMNS="${EXPECTED_TABLES[$table]}"
    
    # 转换为数组进行比较
    IFS=',' read -ra EXPECTED_ARR <<< "$EXPECTED_COLUMNS"
    IFS=',' read -ra ACTUAL_ARR <<< "$ACTUAL_COLUMNS"
    
    TABLE_ISSUES=0
    
    # 检查缺失的列
    for col in "${EXPECTED_ARR[@]}"; do
        if [[ ! " ${ACTUAL_ARR[*]} " =~ " ${col} " ]]; then
            echo "[缺失列] $table.$col" >> "$LOG_FILE"
            ((MISSING_COLUMNS++))
            ((TABLE_ISSUES++))
        fi
    done
    
    # 检查多余的列 (可能是自定义扩展，仅记录)
    for col in "${ACTUAL_ARR[@]}"; do
        if [[ ! " ${EXPECTED_ARR[*]} " =~ " ${col} " ]]; then
            echo "[额外列] $table.$col (可能是自定义扩展)" >> "$LOG_FILE"
            ((EXTRA_COLUMNS++))
        fi
    done
    
    # 检查索引 (如果有定义)
    if [ -n "${EXPECTED_INDEXES[$table]}" ]; then
        ACTUAL_INDEXES=$($MYSQL_CMD -N -e "USE $DB_NAME; SELECT DISTINCT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='$table';" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        
        IFS=',' read -ra EXPECTED_IDX_ARR <<< "${EXPECTED_INDEXES[$table]}"
        IFS=',' read -ra ACTUAL_IDX_ARR <<< "$ACTUAL_INDEXES"
        
        for idx in "${EXPECTED_IDX_ARR[@]}"; do
            if [[ ! " ${ACTUAL_IDX_ARR[*]} " =~ " ${idx} " ]]; then
                echo "[缺失索引] $table.$idx" >> "$LOG_FILE"
                ((INDEX_ISSUES++))
                ((TABLE_ISSUES++))
            fi
        done
    fi
    
    if [ $TABLE_ISSUES -eq 0 ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}有 $TABLE_ISSUES 个问题${NC}"
        ((TOTAL_ISSUES += TABLE_ISSUES))
    fi
done

echo ""
echo "========================================"
echo "  核对结果摘要"
echo "========================================"
echo ""

if [ $TOTAL_ISSUES -eq 0 ]; then
    log_info "所有表结构核对通过！"
else
    log_warn "发现 $TOTAL_ISSUES 个问题:"
    [ $MISSING_TABLES -gt 0 ] && echo "  - 缺失表: $MISSING_TABLES"
    [ $MISSING_COLUMNS -gt 0 ] && echo "  - 缺失列: $MISSING_COLUMNS"
    [ $EXTRA_COLUMNS -gt 0 ] && echo "  - 额外列: $EXTRA_COLUMNS (仅记录，可能是自定义扩展)"
    [ $INDEX_ISSUES -gt 0 ] && echo "  - 缺失索引: $INDEX_ISSUES"
fi

# 写入日志摘要
{
    echo ""
    echo "=========================================="
    echo "摘要"
    echo "=========================================="
    echo "总问题数: $TOTAL_ISSUES"
    echo "缺失表: $MISSING_TABLES"
    echo "缺失列: $MISSING_COLUMNS"
    echo "额外列: $EXTRA_COLUMNS"
    echo "缺失索引: $INDEX_ISSUES"
} >> "$LOG_FILE"

echo ""
log_info "详细日志已保存到: $LOG_FILE"
echo ""

exit $TOTAL_ISSUES
