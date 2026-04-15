#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CERT_DIR="$PROJECT_DIR/configs/yunjinqi.top_nginx"
CERTBOT_WEBROOT="/root/woniunote/frontend/dist"
DOMAIN="yunjinqi.top"
WWW_DOMAIN="www.yunjinqi.top"
EMAIL="admin@yunjinqi.top"
LOG_FILE="/var/log/certbot-renew.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "[错误] $1"
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error_exit "请使用 sudo 运行此脚本"
    fi
}

install_certbot() {
    log "安装 certbot..."
    if command -v certbot &> /dev/null; then
        log "certbot 已安装: $(certbot --version)"
    else
        apt-get update && apt-get install -y certbot python3-certbot-nginx
        log "certbot 安装完成"
    fi
}

check_nginx() {
    if systemctl is-active --quiet nginx; then
        log "Nginx 正在运行"
        return 0
    else
        log "Nginx 未运行"
        return 1
    fi
}

check_webroot() {
    if [ ! -d "$CERTBOT_WEBROOT/.well-known" ]; then
        mkdir -p "$CERTBOT_WEBROOT/.well-known"
    fi
}

renew_certificate() {
    log "申请/续订 SSL 证书 (HTTP-01 验证)..."

    certbot certonly \
        --webroot \
        --webroot-path "$CERTBOT_WEBROOT" \
        --domain "$DOMAIN" \
        --domain "$WWW_DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive \
        --keep-until-expiring \
        || error_exit "证书申请失败"

    log "证书申请/续订完成"
}

copy_certificates() {
    log "复制证书到项目配置目录..."

    mkdir -p "$CERT_DIR"

    local CERT_SOURCE="/etc/letsencrypt/live/$DOMAIN"
    if [ ! -d "$CERT_SOURCE" ]; then
        error_exit "证书目录不存在: $CERT_SOURCE"
    fi

    cp "$CERT_SOURCE/fullchain.pem" "$CERT_DIR/yunjinqi.top_bundle.pem"
    cp "$CERT_SOURCE/privkey.pem" "$CERT_DIR/yunjinqi.top.key"

    log "证书已复制到: $CERT_DIR"
}

reload_nginx() {
    log "重载 Nginx..."
    systemctl reload nginx || error_exit "重载 Nginx 失败"
    sleep 2
    log "Nginx 已重载"
}

verify_certificate() {
    log "验证证书..."
    certbot certificates 2>/dev/null || true

    if [ -f "$CERT_DIR/yunjinqi.top_bundle.pem" ]; then
        log "证书过期日期检查:"
        openssl x509 -in "$CERT_DIR/yunjinqi.top_bundle.pem" -noout -dates 2>/dev/null || true
    fi
}

setup_cron() {
    log "设置自动续订 cron 任务..."

    local CRON_JOB="0 3 1 */2 * root $SCRIPT_DIR/renew_ssl.sh renew >> $LOG_FILE 2>&1"

    (crontab -l 2>/dev/null | grep -v "renew_ssl.sh"; echo "$CRON_JOB") | crontab -

    log "Cron 任务已添加: 每两个月1号凌晨3点自动续订"
}

remove_cron() {
    log "移除自动续订 cron 任务..."
    crontab -l 2>/dev/null | grep -v "renew_ssl.sh" | crontab - || true
    log "Cron 任务已移除"
}

show_status() {
    log "当前证书状态:"
    certbot certificates 2>/dev/null || log "无法获取证书状态"
}

usage() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  renew      续订证书（默认）"
    echo "  install   安装 certbot 并设置自动续订"
    echo "  status     查看证书状态"
    echo "  uninstall  移除自动续订"
    echo ""
    echo "示例:"
    echo "  sudo $0 install  # 安装并设置每两个月自动续订"
    echo "  sudo $0 renew    # 手动续订证书"
}

main() {
    case "${1:-renew}" in
        renew)
            check_root
            check_webroot
            renew_certificate
            copy_certificates
            reload_nginx
            verify_certificate
            log "证书更新完成!"
            ;;
        install)
            check_root
            install_certbot
            check_webroot
            renew_certificate
            copy_certificates
            reload_nginx
            verify_certificate
            setup_cron
            log "安装完成!"
            ;;
        status)
            show_status
            ;;
        uninstall)
            check_root
            remove_cron
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"