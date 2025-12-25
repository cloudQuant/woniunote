#!/bin/bash

# Nginx SSL 证书更新脚本
# 带备份和回滚功能
# 支持两种 Nginx 配置模式:
#   1. sites-available/sites-enabled 模式 (Ubuntu 默认)
#   2. 直接修改 nginx.conf 模式 (旧版配置)

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
BACKUP_DIR="$PROJECT_DIR/backups/nginx_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/update.log"
DOMAIN="www.yunjinqi.top"

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
    echo "项目目录: $PROJECT_DIR"
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
    
    # 恢复 nginx.conf
    if [ -f "$BACKUP_DIR/nginx.conf.bak" ]; then
        cp "$BACKUP_DIR/nginx.conf.bak" /etc/nginx/nginx.conf
        echo "[ROLLBACK] 恢复 /etc/nginx/nginx.conf" >> "$LOG_FILE"
    fi
    
    # 恢复 sites-available 配置
    if [ -f "$BACKUP_DIR/woniunote.conf.bak" ]; then
        cp "$BACKUP_DIR/woniunote.conf.bak" /etc/nginx/sites-available/woniunote
        echo "[ROLLBACK] 恢复 sites-available/woniunote" >> "$LOG_FILE"
    fi
    
    # 恢复 SSL 证书
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

# 步骤 1: 检查证书源文件
log_action "检查证书源文件..."
echo "" >> "$LOG_FILE"
echo "证书源目录: $CERT_SOURCE_DIR" >> "$LOG_FILE"

if [ ! -d "$CERT_SOURCE_DIR" ]; then
    log_error "证书源目录不存在: $CERT_SOURCE_DIR"
    log_error "请先将证书文件放到该目录"
    exit 1
fi

ls -la "$CERT_SOURCE_DIR" >> "$LOG_FILE"

# 检查必需的证书文件
CERT_FILE=""
KEY_FILE=""

# 支持多种证书文件名
for cert in "$CERT_SOURCE_DIR/yunjinqi.top_bundle.crt" \
            "$CERT_SOURCE_DIR/yunjinqi.top_bundle.pem" \
            "$CERT_SOURCE_DIR/fullchain.pem" \
            "$CERT_SOURCE_DIR/certificate.crt"; do
    if [ -f "$cert" ]; then
        CERT_FILE="$cert"
        break
    fi
done

for key in "$CERT_SOURCE_DIR/yunjinqi.top.key" \
           "$CERT_SOURCE_DIR/privkey.pem" \
           "$CERT_SOURCE_DIR/private.key"; do
    if [ -f "$key" ]; then
        KEY_FILE="$key"
        break
    fi
done

if [ -z "$CERT_FILE" ] || [ -z "$KEY_FILE" ]; then
    log_error "未找到证书文件或密钥文件"
    log_error "请确保目录中包含: *_bundle.crt/*.pem 和 *.key 文件"
    exit 1
fi

log_action "证书文件: $CERT_FILE"
log_action "密钥文件: $KEY_FILE"

# 步骤 2: 备份当前配置
log_action "备份当前 Nginx 配置..."
echo "" >> "$LOG_FILE"
echo "备份操作:" >> "$LOG_FILE"

# 备份 nginx.conf
if [ -f "/etc/nginx/nginx.conf" ]; then
    cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx.conf.bak"
    echo "  备份: /etc/nginx/nginx.conf" >> "$LOG_FILE"
fi

# 备份 sites-available 配置
if [ -f "/etc/nginx/sites-available/woniunote" ]; then
    cp /etc/nginx/sites-available/woniunote "$BACKUP_DIR/woniunote.conf.bak"
    echo "  备份: /etc/nginx/sites-available/woniunote" >> "$LOG_FILE"
fi

# 备份现有 SSL 证书
if [ -d "$SSL_DEST_DIR" ]; then
    mkdir -p "$BACKUP_DIR/ssl_certs"
    cp -r "$SSL_DEST_DIR"/* "$BACKUP_DIR/ssl_certs/" 2>/dev/null || true
    echo "  备份: $SSL_DEST_DIR" >> "$LOG_FILE"
fi

log_action "备份完成: $BACKUP_DIR"

# 步骤 3: 安装 SSL 证书到系统目录
log_action "安装 SSL 证书到 $SSL_DEST_DIR..."
mkdir -p "$SSL_DEST_DIR"

cp "$CERT_FILE" "$SSL_DEST_DIR/fullchain.pem"
cp "$KEY_FILE" "$SSL_DEST_DIR/privkey.pem"
chmod 644 "$SSL_DEST_DIR/fullchain.pem"
chmod 600 "$SSL_DEST_DIR/privkey.pem"

echo "  安装: $CERT_FILE -> $SSL_DEST_DIR/fullchain.pem" >> "$LOG_FILE"
echo "  安装: $KEY_FILE -> $SSL_DEST_DIR/privkey.pem" >> "$LOG_FILE"

# 步骤 4: 检测 Nginx 配置模式并更新
log_action "检测 Nginx 配置模式..."

# 检查是否使用 sites-available 模式
USE_SITES_AVAILABLE=false
if [ -d "/etc/nginx/sites-available" ] && [ -d "/etc/nginx/sites-enabled" ]; then
    USE_SITES_AVAILABLE=true
    log_action "使用 sites-available/sites-enabled 模式"
else
    log_action "使用 nginx.conf 直接配置模式"
fi

# 使用 configs/woniunote_nginx_config 作为模板
NGINX_CONFIG_TEMPLATE="$PROJECT_DIR/configs/woniunote_nginx_config"

if [ -f "$NGINX_CONFIG_TEMPLATE" ]; then
    log_action "使用项目配置模板: $NGINX_CONFIG_TEMPLATE"
    
    # 复制配置到 nginx.conf
    cp "$NGINX_CONFIG_TEMPLATE" /etc/nginx/nginx.conf
    
    # 更新证书路径为实际路径
    sed -i "s|/root/woniunote/configs/yunjinqi.top_nginx/yunjinqi.top_bundle.pem|$SSL_DEST_DIR/fullchain.pem|g" /etc/nginx/nginx.conf
    sed -i "s|/root/woniunote/configs/yunjinqi.top_nginx/yunjinqi.top.key|$SSL_DEST_DIR/privkey.pem|g" /etc/nginx/nginx.conf
    
    # 兼容其他可能的证书路径格式
    sed -i "s|$PROJECT_DIR/configs/yunjinqi.top_nginx/yunjinqi.top_bundle.pem|$SSL_DEST_DIR/fullchain.pem|g" /etc/nginx/nginx.conf
    sed -i "s|$PROJECT_DIR/configs/yunjinqi.top_nginx/yunjinqi.top.key|$SSL_DEST_DIR/privkey.pem|g" /etc/nginx/nginx.conf
    
    echo "  使用模板: $NGINX_CONFIG_TEMPLATE" >> "$LOG_FILE"
    echo "  更新证书路径: $SSL_DEST_DIR/" >> "$LOG_FILE"
else
    # 如果模板不存在，生成默认配置
    log_action "模板不存在，生成默认 Nginx 配置..."
    
    cat > /etc/nginx/nginx.conf << EOF
# WoniuNote Nginx 配置
# 自动生成于 $(date)

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    # HTTP -> HTTPS 重定向
    server {
        listen 80;
        listen [::]:80 ipv6only=on;
        server_name $DOMAIN;

        rewrite ^(.*)\$ https://\$host\$1 permanent;

        location / {
            index index.html index.htm;
        }
    }

    # HTTPS 服务器
    server {
        listen 443 ssl;
        server_name $DOMAIN;

        root html;
        index index.html index.htm;

        # SSL 证书
        ssl_certificate $SSL_DEST_DIR/fullchain.pem;
        ssl_certificate_key $SSL_DEST_DIR/privkey.pem;

        # SSL 配置
        ssl_session_timeout 5m;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;

        # 代理到前端服务
        location / {
            proxy_pass http://127.0.0.1:8888;
            proxy_redirect off;
            proxy_set_header Host \$http_host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF
fi

# 如果存在 sites-enabled，禁用默认站点避免冲突
if [ -d "/etc/nginx/sites-enabled" ]; then
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    rm -f /etc/nginx/sites-enabled/woniunote 2>/dev/null || true
fi

echo "  Nginx 配置已更新" >> "$LOG_FILE"

# 步骤 5: 测试 Nginx 配置
log_action "测试 Nginx 配置..."
if nginx -t 2>&1 | tee -a "$LOG_FILE"; then
    log_action "Nginx 配置测试通过"
else
    log_error "Nginx 配置测试失败"
    rollback
fi

# 步骤 6: 重载 Nginx
log_action "重载 Nginx..."
systemctl reload nginx

# 步骤 7: 验证 SSL 证书
log_action "验证 SSL 证书..."
echo "" >> "$LOG_FILE"
echo "SSL 证书信息:" >> "$LOG_FILE"
openssl x509 -in "$SSL_DEST_DIR/fullchain.pem" -noout -subject -dates 2>&1 | tee -a "$LOG_FILE"

echo ""
echo "========================================"
echo "  SSL 证书更新完成!"
echo "========================================"
echo ""
log_info "证书位置: $SSL_DEST_DIR/"
log_info "备份目录: $BACKUP_DIR"
log_info "日志文件: $LOG_FILE"
echo ""

# 显示证书有效期
echo "证书有效期:"
openssl x509 -in "$SSL_DEST_DIR/fullchain.pem" -noout -dates 2>/dev/null | sed 's/^/  /'

echo ""
log_info "如需回滚，执行:"
echo "  sudo cp $BACKUP_DIR/nginx.conf.bak /etc/nginx/nginx.conf"
echo "  sudo cp $BACKUP_DIR/ssl_certs/* $SSL_DEST_DIR/"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""

# 测试 HTTPS 连接
log_action "测试 HTTPS 连接..."
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$DOMAIN" 2>/dev/null | grep -q "200\|301\|302"; then
    log_info "HTTPS 连接测试成功!"
else
    log_warn "HTTPS 连接测试失败，请检查防火墙和域名解析"
fi
