#!/bin/bash

# Nginx SSL 证书更新脚本
# 带备份和回滚功能

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 获取脚本和项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 配置
CERT_SOURCE_DIR="$PROJECT_DIR/configs/yunjinqi.top_nginx"
SSL_DEST_DIR="/etc/ssl/woniunote"
NGINX_CONF_SRC="$PROJECT_DIR/configs/woniunote_nginx_prod.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/woniunote"
BACKUP_DIR="$PROJECT_DIR/backups/nginx_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/update.log"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

echo "========================================"
echo "  Nginx SSL 证书更新脚本"
echo "========================================"
echo ""

# 创建备份目录
log_info "创建备份目录: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# 初始化日志
{
    echo "=========================================="
    echo "Nginx SSL 证书更新日志"
    echo "时间: $(date)"
    echo "=========================================="
    echo ""
} > "$LOG_FILE"

# 函数: 记录操作
log_action() {
    echo "[$(date '+%H:%M:%S')] $1" >> "$LOG_FILE"
    log_info "$1"
}

# 函数: 回滚
rollback() {
    log_error "发生错误，开始回滚..."
    echo "[ROLLBACK] 开始回滚操作" >> "$LOG_FILE"
    
    if [ -f "$BACKUP_DIR/woniunote.conf.bak" ]; then
        cp "$BACKUP_DIR/woniunote.conf.bak" "$NGINX_CONF_DEST"
        echo "[ROLLBACK] 恢复 Nginx 配置" >> "$LOG_FILE"
    fi
    
    if [ -d "$BACKUP_DIR/ssl_certs" ]; then
        cp -r "$BACKUP_DIR/ssl_certs"/* "$SSL_DEST_DIR/" 2>/dev/null || true
        echo "[ROLLBACK] 恢复 SSL 证书" >> "$LOG_FILE"
    fi
    
    nginx -t && systemctl reload nginx
    log_info "回滚完成"
    exit 1
}

# 设置错误处理
trap rollback ERR

# 步骤 1: 检查源文件
log_action "检查源文件..."
echo "" >> "$LOG_FILE"
echo "源文件检查:" >> "$LOG_FILE"

if [ ! -d "$CERT_SOURCE_DIR" ]; then
    log_error "证书源目录不存在: $CERT_SOURCE_DIR"
    exit 1
fi

ls -la "$CERT_SOURCE_DIR" >> "$LOG_FILE"

# 检查必需的证书文件
CERT_FILE=""
KEY_FILE=""

if [ -f "$CERT_SOURCE_DIR/yunjinqi.top_bundle.crt" ]; then
    CERT_FILE="$CERT_SOURCE_DIR/yunjinqi.top_bundle.crt"
elif [ -f "$CERT_SOURCE_DIR/yunjinqi.top_bundle.pem" ]; then
    CERT_FILE="$CERT_SOURCE_DIR/yunjinqi.top_bundle.pem"
fi

if [ -f "$CERT_SOURCE_DIR/yunjinqi.top.key" ]; then
    KEY_FILE="$CERT_SOURCE_DIR/yunjinqi.top.key"
fi

if [ -z "$CERT_FILE" ] || [ -z "$KEY_FILE" ]; then
    log_error "未找到证书文件或密钥文件"
    exit 1
fi

log_action "证书文件: $CERT_FILE"
log_action "密钥文件: $KEY_FILE"

# 步骤 2: 备份当前配置
log_action "备份当前配置..."
echo "" >> "$LOG_FILE"
echo "备份操作:" >> "$LOG_FILE"

if [ -f "$NGINX_CONF_DEST" ]; then
    cp "$NGINX_CONF_DEST" "$BACKUP_DIR/woniunote.conf.bak"
    echo "  备份: $NGINX_CONF_DEST -> $BACKUP_DIR/woniunote.conf.bak" >> "$LOG_FILE"
fi

if [ -d "$SSL_DEST_DIR" ]; then
    mkdir -p "$BACKUP_DIR/ssl_certs"
    cp -r "$SSL_DEST_DIR"/* "$BACKUP_DIR/ssl_certs/" 2>/dev/null || true
    echo "  备份: $SSL_DEST_DIR -> $BACKUP_DIR/ssl_certs/" >> "$LOG_FILE"
fi

# 步骤 3: 检查当前 Nginx 配置
log_action "检查当前 Nginx 配置..."
echo "" >> "$LOG_FILE"
echo "当前 Nginx 配置:" >> "$LOG_FILE"

if [ -f "$NGINX_CONF_DEST" ]; then
    grep -E "ssl_certificate|root|server_name" "$NGINX_CONF_DEST" >> "$LOG_FILE" 2>/dev/null || true
else
    echo "  配置文件不存在" >> "$LOG_FILE"
fi

# 步骤 4: 安装 SSL 证书
log_action "安装 SSL 证书..."
mkdir -p "$SSL_DEST_DIR"

cp "$CERT_FILE" "$SSL_DEST_DIR/fullchain.pem"
cp "$KEY_FILE" "$SSL_DEST_DIR/privkey.pem"
chmod 644 "$SSL_DEST_DIR/fullchain.pem"
chmod 600 "$SSL_DEST_DIR/privkey.pem"

echo "  安装: $CERT_FILE -> $SSL_DEST_DIR/fullchain.pem" >> "$LOG_FILE"
echo "  安装: $KEY_FILE -> $SSL_DEST_DIR/privkey.pem" >> "$LOG_FILE"

# 步骤 5: 更新 Nginx 配置
log_action "更新 Nginx 配置..."

# 复制配置文件
cp "$NGINX_CONF_SRC" "$NGINX_CONF_DEST"

# 更新证书路径
sed -i "s|/etc/letsencrypt/live/yunjinqi.top/fullchain.pem|$SSL_DEST_DIR/fullchain.pem|g" "$NGINX_CONF_DEST"
sed -i "s|/etc/letsencrypt/live/yunjinqi.top/privkey.pem|$SSL_DEST_DIR/privkey.pem|g" "$NGINX_CONF_DEST"

# 更新项目路径为实际部署目录
sed -i "s|/var/www/woniunote|$PROJECT_DIR|g" "$NGINX_CONF_DEST"

echo "  更新证书路径" >> "$LOG_FILE"
echo "  更新项目路径: $PROJECT_DIR" >> "$LOG_FILE"

# 步骤 6: 删除默认站点
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# 创建软链接
ln -sf "$NGINX_CONF_DEST" /etc/nginx/sites-enabled/woniunote

# 步骤 7: 测试 Nginx 配置
log_action "测试 Nginx 配置..."
if nginx -t 2>&1 | tee -a "$LOG_FILE"; then
    log_action "Nginx 配置测试通过"
else
    log_error "Nginx 配置测试失败"
    rollback
fi

# 步骤 8: 重载 Nginx
log_action "重载 Nginx..."
systemctl reload nginx

# 步骤 9: 验证
log_action "验证配置..."
echo "" >> "$LOG_FILE"
echo "最终配置:" >> "$LOG_FILE"
grep -E "ssl_certificate|root|server_name" "$NGINX_CONF_DEST" >> "$LOG_FILE" 2>/dev/null || true

echo ""
echo "========================================"
echo "  更新完成"
echo "========================================"
echo ""
log_info "备份目录: $BACKUP_DIR"
log_info "日志文件: $LOG_FILE"
echo ""
log_info "如需回滚，执行:"
echo "  sudo cp $BACKUP_DIR/woniunote.conf.bak $NGINX_CONF_DEST"
echo "  sudo cp $BACKUP_DIR/ssl_certs/* $SSL_DEST_DIR/"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""

# 显示当前配置摘要
echo "当前配置摘要:"
grep -E "ssl_certificate|root|server_name" "$NGINX_CONF_DEST" 2>/dev/null | head -10
