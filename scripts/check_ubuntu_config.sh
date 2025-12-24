#!/bin/bash

# WoniuNote Ubuntu 服务器配置诊断脚本
# 用于排查外部无法访问服务的问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_check() { echo -e "${BLUE}[检查]${NC} $1"; }
log_tip() { echo -e "${CYAN}[建议]${NC} $1"; }

echo ""
echo "========================================"
echo "  WoniuNote 服务器配置诊断工具"
echo "  $(date)"
echo "========================================"
echo ""

ISSUES_FOUND=0

# ============================================
# 1. 检查服务状态
# ============================================
echo "========== 1. 服务状态检查 =========="
echo ""

log_check "检查后端服务 (端口 8888)..."
if pgrep -f "woniunote_backend" > /dev/null 2>&1; then
    log_info "后端进程正在运行"
    PID=$(pgrep -f "woniunote_backend" | head -1)
    echo "      PID: $PID"
else
    log_error "后端进程未运行"
    ((ISSUES_FOUND++))
fi

log_check "检查前端服务 (端口 5173)..."
if pgrep -f "vite" > /dev/null 2>&1 || pgrep -f "node.*frontend" > /dev/null 2>&1; then
    log_info "前端进程正在运行"
else
    log_warn "前端开发服务器未运行 (生产环境可能使用 nginx 静态文件)"
fi

echo ""

# ============================================
# 2. 检查端口监听状态 (关键!)
# ============================================
echo "========== 2. 端口监听状态 (关键) =========="
echo ""

log_check "检查 8888 端口监听地址..."
LISTEN_8888=$(ss -tlnp 2>/dev/null | grep ":8888" || netstat -tlnp 2>/dev/null | grep ":8888" || echo "")

if [ -z "$LISTEN_8888" ]; then
    log_error "端口 8888 没有任何服务监听"
    ((ISSUES_FOUND++))
else
    echo "$LISTEN_8888"
    
    # 检查是否绑定到 127.0.0.1
    if echo "$LISTEN_8888" | grep -q "127.0.0.1:8888"; then
        log_error "端口 8888 只绑定到 127.0.0.1 (本地回环地址)"
        log_tip "这是最常见的问题! 需要修改配置让服务监听 0.0.0.0:8888"
        log_tip "修改 backend_cpp/config.json 中的 host 为 \"0.0.0.0\""
        ((ISSUES_FOUND++))
    elif echo "$LISTEN_8888" | grep -qE "0\.0\.0\.0:8888|\*:8888|:::8888"; then
        log_info "端口 8888 正确绑定到所有网络接口 (0.0.0.0)"
    else
        log_warn "端口 8888 绑定状态需要确认"
    fi
fi

echo ""
log_check "检查 5173 端口 (前端开发服务器)..."
LISTEN_5173=$(ss -tlnp 2>/dev/null | grep ":5173" || echo "")
if [ -n "$LISTEN_5173" ]; then
    echo "$LISTEN_5173"
    if echo "$LISTEN_5173" | grep -q "127.0.0.1:5173"; then
        log_warn "前端开发服务器只绑定到 127.0.0.1"
        log_tip "运行 vite 时使用: npm run dev -- --host 0.0.0.0"
    fi
fi

echo ""
log_check "检查 80/443 端口 (Nginx)..."
LISTEN_80=$(ss -tlnp 2>/dev/null | grep ":80 " || echo "无")
LISTEN_443=$(ss -tlnp 2>/dev/null | grep ":443 " || echo "无")
echo "  端口 80:  $LISTEN_80"
echo "  端口 443: $LISTEN_443"

echo ""

# ============================================
# 3. 检查防火墙状态
# ============================================
echo "========== 3. 防火墙状态 =========="
echo ""

# UFW 防火墙
log_check "检查 UFW 防火墙..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null || echo "无法获取状态")
    if echo "$UFW_STATUS" | grep -q "Status: active"; then
        log_warn "UFW 防火墙已启用"
        echo ""
        echo "  当前规则:"
        ufw status numbered 2>/dev/null | head -20
        echo ""
        
        # 检查 8888 端口是否开放
        if ufw status | grep -q "8888"; then
            log_info "端口 8888 已在 UFW 中开放"
        else
            log_error "端口 8888 未在 UFW 中开放"
            log_tip "运行: sudo ufw allow 8888/tcp"
            ((ISSUES_FOUND++))
        fi
    else
        log_info "UFW 防火墙未启用或已禁用"
    fi
else
    log_info "UFW 未安装"
fi

echo ""

# iptables 防火墙
log_check "检查 iptables 规则..."
IPTABLES_DROP=$(iptables -L INPUT -n 2>/dev/null | grep -i "drop\|reject" | head -5 || echo "")
if [ -n "$IPTABLES_DROP" ]; then
    log_warn "iptables 存在 DROP/REJECT 规则:"
    echo "$IPTABLES_DROP"
    log_tip "检查是否阻止了 8888 端口: sudo iptables -L INPUT -n | grep 8888"
else
    log_info "iptables 无明显阻止规则"
fi

echo ""

# ============================================
# 4. 检查云服务商安全组 (提示)
# ============================================
echo "========== 4. 云服务商安全组 =========="
echo ""

log_check "检测云服务商..."
# 检查是否为云服务器
CLOUD_PROVIDER=""
if curl -s --connect-timeout 1 http://100.100.100.200/latest/meta-data/ &>/dev/null; then
    CLOUD_PROVIDER="阿里云 (Alibaba Cloud)"
elif curl -s --connect-timeout 1 http://metadata.tencentyun.com/latest/meta-data/ &>/dev/null; then
    CLOUD_PROVIDER="腾讯云 (Tencent Cloud)"
elif curl -s --connect-timeout 1 http://169.254.169.254/latest/meta-data/ &>/dev/null; then
    CLOUD_PROVIDER="AWS / 其他云服务商"
fi

if [ -n "$CLOUD_PROVIDER" ]; then
    log_warn "检测到云服务器: $CLOUD_PROVIDER"
    log_tip "请检查云服务商控制台的安全组规则，确保开放以下端口:"
    echo "      - TCP 8888 (后端API)"
    echo "      - TCP 5173 (前端开发服务器，如需要)"
    echo "      - TCP 80/443 (HTTP/HTTPS，如使用 Nginx)"
    echo ""
    log_tip "安全组配置位置:"
    echo "      - 阿里云: 云服务器ECS -> 安全组 -> 配置规则"
    echo "      - 腾讯云: 云服务器 -> 安全组 -> 入站规则"
    echo "      - AWS: EC2 -> Security Groups -> Inbound rules"
else
    log_info "未检测到常见云服务商元数据服务 (可能是物理机或其他环境)"
fi

echo ""

# ============================================
# 5. 检查 Nginx 配置
# ============================================
echo "========== 5. Nginx 配置 =========="
echo ""

log_check "检查 Nginx 状态..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    log_info "Nginx 服务正在运行"
    
    # 检查配置
    log_check "检查 Nginx 配置..."
    if nginx -t 2>&1 | grep -q "successful"; then
        log_info "Nginx 配置语法正确"
    else
        log_error "Nginx 配置有语法错误"
        nginx -t 2>&1
        ((ISSUES_FOUND++))
    fi
    
    # 检查 woniunote 站点配置
    if [ -f "/etc/nginx/sites-enabled/woniunote" ]; then
        log_info "WoniuNote Nginx 站点配置已启用"
        echo ""
        echo "  代理配置预览:"
        grep -A2 "proxy_pass" /etc/nginx/sites-enabled/woniunote 2>/dev/null | head -10 || echo "  未找到 proxy_pass 配置"
    else
        log_warn "WoniuNote Nginx 站点配置未启用"
    fi
else
    log_warn "Nginx 服务未运行"
fi

echo ""

# ============================================
# 6. 检查后端配置文件
# ============================================
echo "========== 6. 后端配置检查 =========="
echo ""

# 查找配置文件
CONFIG_FILES=(
    "/var/www/woniunote/backend_cpp/config.json"
    "/var/www/woniunote/backend_cpp/config.prod.json"
    "$HOME/woniunote/backend_cpp/config.json"
    "./backend_cpp/config.json"
)

for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        log_check "检查配置文件: $config"
        
        # 检查 host 配置
        HOST_VALUE=$(grep -o '"host"[[:space:]]*:[[:space:]]*"[^"]*"' "$config" 2>/dev/null | head -1 || echo "")
        if [ -n "$HOST_VALUE" ]; then
            echo "  $HOST_VALUE"
            if echo "$HOST_VALUE" | grep -q "127.0.0.1\|localhost"; then
                log_error "配置文件中 host 设置为本地地址!"
                log_tip "将 \"host\": \"127.0.0.1\" 改为 \"host\": \"0.0.0.0\""
                ((ISSUES_FOUND++))
            elif echo "$HOST_VALUE" | grep -q "0.0.0.0"; then
                log_info "host 配置正确 (0.0.0.0)"
            fi
        fi
        
        # 检查 port 配置
        PORT_VALUE=$(grep -o '"port"[[:space:]]*:[[:space:]]*[0-9]*' "$config" 2>/dev/null | head -1 || echo "")
        if [ -n "$PORT_VALUE" ]; then
            echo "  $PORT_VALUE"
        fi
        break
    fi
done

echo ""

# ============================================
# 7. 网络连通性测试
# ============================================
echo "========== 7. 网络连通性测试 =========="
echo ""

# 获取服务器 IP
log_check "获取服务器 IP 地址..."
INTERNAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -1)
EXTERNAL_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 icanhazip.com 2>/dev/null || echo "无法获取")

echo "  内网 IP: ${INTERNAL_IP:-未知}"
echo "  外网 IP: ${EXTERNAL_IP:-未知}"
echo ""

# 本地连接测试
log_check "测试本地连接 (localhost:8888)..."
if curl -s --connect-timeout 3 http://localhost:8888/api/system/status &>/dev/null || \
   curl -s --connect-timeout 3 http://localhost:8888/ &>/dev/null; then
    log_info "本地连接成功"
else
    log_warn "本地连接失败或超时"
fi

# 内网 IP 连接测试
if [ -n "$INTERNAL_IP" ]; then
    log_check "测试内网 IP 连接 ($INTERNAL_IP:8888)..."
    if curl -s --connect-timeout 3 http://$INTERNAL_IP:8888/ &>/dev/null; then
        log_info "内网 IP 连接成功"
    else
        log_warn "内网 IP 连接失败 - 可能是绑定地址问题"
    fi
fi

echo ""

# ============================================
# 8. 诊断总结
# ============================================
echo "========================================"
echo "  诊断总结"
echo "========================================"
echo ""

if [ $ISSUES_FOUND -eq 0 ]; then
    log_info "未发现明显配置问题"
    echo ""
    echo "如果外部仍无法访问，请检查:"
    echo "  1. 云服务商安全组是否开放 8888 端口"
    echo "  2. 本地网络/路由器防火墙"
    echo "  3. ISP 是否封锁该端口"
else
    log_error "发现 $ISSUES_FOUND 个潜在问题"
    echo ""
    echo "常见修复步骤:"
    echo ""
    echo "  1. 修改后端监听地址 (最常见问题):"
    echo "     编辑 backend_cpp/config.json"
    echo "     将 \"host\": \"127.0.0.1\" 改为 \"host\": \"0.0.0.0\""
    echo "     重启服务: bash restart_app.sh"
    echo ""
    echo "  2. 开放防火墙端口:"
    echo "     sudo ufw allow 8888/tcp"
    echo "     sudo ufw reload"
    echo ""
    echo "  3. 检查云服务商安全组 (如适用)"
fi

echo ""
echo "========================================"
echo "  诊断完成"
echo "========================================"
