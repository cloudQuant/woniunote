# WoniuNote 部署指南

## 📋 概述

本指南提供WoniuNote项目在不同环境下的完整部署方案，包括开发环境、测试环境和生产环境的配置方法。

---

## 🎯 部署架构

### 生产环境架构图

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │    (Nginx)      │
                    └─────────┬───────┘
                              │
                    ┌─────────┴───────┐
                    │   Reverse Proxy │
                    │    (Nginx)      │
                    └─────────┬───────┘
                              │
                    ┌─────────┴───────┐
                    │  Application    │
                    │   (Gunicorn)    │
                    └─────────┬───────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────┴────────┐ ┌─────┴──────┐ ┌───────┴────────┐
    │   MySQL DB     │ │   Redis    │ │  File Storage  │
    │   (Primary)    │ │  (Cache)   │ │    (Local)     │
    └────────────────┘ └────────────┘ └────────────────┘
```

### 服务组件
- **Web服务器**: Nginx (反向代理 + 静态文件)
- **应用服务器**: Gunicorn (WSGI服务器)
- **数据库**: MySQL 5.7+ (主数据库)
- **缓存**: Redis 5.0+ (会话 + 应用缓存)
- **监控**: 系统监控 + 应用监控

---

## 🛠️ 环境要求

### 最低硬件要求

| 环境 | CPU | 内存 | 磁盘 | 网络 |
|------|-----|------|------|------|
| 开发环境 | 2核 | 4GB | 20GB | 10Mbps |
| 测试环境 | 2核 | 8GB | 50GB | 100Mbps |
| 生产环境 | 4核 | 16GB | 100GB | 1Gbps |

### 软件依赖

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.8+ | 应用运行环境 |
| MySQL | 5.7+ | 主数据库 |
| Redis | 5.0+ | 缓存服务 |
| Nginx | 1.18+ | Web服务器 |
| Git | 2.25+ | 代码管理 |
| Certbot | 1.0+ | SSL证书管理 |

---

## 🏠 开发环境部署

### 1. 环境准备

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3.8 python3.8-venv python3.8-dev
sudo apt install -y mysql-server redis-server
sudo apt install -y build-essential libmysqlclient-dev
sudo apt install -y git curl wget vim
```

### 2. 项目设置

```bash
# 克隆项目
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# 创建虚拟环境
python3.8 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装Python依赖
pip install -r requirements.txt
pip install -e .
```

### 3. 数据库配置

```bash
# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 登录MySQL
sudo mysql -u root -p

# 创建数据库和用户
CREATE DATABASE woniunote_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'woniunote'@'localhost' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON woniunote_dev.* TO 'woniunote'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. 配置文件设置

```bash
# 复制配置文件模板
cp configs/user_password_config_example.yaml configs/user_password_config.yaml

# 编辑配置文件
vim configs/user_password_config.yaml
```

**开发环境配置** (`configs/user_password_config.yaml`):
```yaml
database:
  host: localhost
  port: 3306
  user: woniunote
  password: dev_password
  database: woniunote_dev

admin:
  username: admin
  password: admin123
  email: admin@localhost
  nickname: 管理员

redis:
  host: localhost
  port: 6379
  db: 0
  password: null

development:
  debug: true
  secret_key: "dev-secret-key-change-in-production"
  log_level: DEBUG
```

### 5. 数据库初始化

```bash
# 设置环境变量
export FLASK_ENV=development
export DATABASE_URL=mysql+pymysql://woniunote:dev_password@localhost/woniunote_dev

# 初始化数据库
python scripts/init_db_direct.py

# 验证数据库
mysql -u woniunote -p woniunote_dev -e "SHOW TABLES;"
```

### 6. 启动开发服务器

```bash
# 启动Redis
sudo systemctl start redis

# 启动应用
python scripts/start_server.py --debug --host 0.0.0.0 --port 5000

# 或者使用Flask内置服务器
export FLASK_APP=woniunote.app:app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### 7. 验证部署

```bash
# 检查服务状态
curl http://localhost:5000/

# 运行测试
python tests/run_all_tests.py --fast

# 检查日志
tail -f simple_logs/$(date +%Y-%m)/app.log
```

---

## 🧪 测试环境部署

### 1. 环境准备

测试环境配置与开发环境类似，但使用不同的数据库和配置：

```bash
# 创建测试数据库
mysql -u root -p << EOF
CREATE DATABASE woniunote_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON woniunote_test.* TO 'woniunote'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 2. 测试环境配置

```yaml
# configs/user_password_config_test.yaml
database:
  host: localhost
  port: 3306
  user: woniunote
  password: test_password
  database: woniunote_test

testing:
  debug: false
  secret_key: "test-secret-key"
  log_level: INFO
  csrf_enabled: false
```

### 3. 测试环境启动

```bash
# 设置测试环境变量
export FLASK_ENV=testing
export TESTING=True
export DATABASE_URL=mysql+pymysql://woniunote:test_password@localhost/woniunote_test

# 初始化测试数据库
python scripts/init_db_direct.py

# 运行完整测试套件
python tests/run_all_tests.py

# 启动测试服务器
python scripts/start_server.py --host 0.0.0.0 --port 5001
```

---

## 🚀 生产环境部署

### 1. 服务器准备

```bash
# 创建系统用户
sudo useradd -m -s /bin/bash woniunote
sudo usermod -aG sudo woniunote

# 切换到应用用户
sudo su - woniunote

# 创建应用目录
mkdir -p ~/app ~/logs ~/backup
```

### 2. 系统依赖安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装系统依赖
sudo apt install -y python3.8 python3.8-venv python3.8-dev
sudo apt install -y mysql-server redis-server nginx
sudo apt install -y build-essential libmysqlclient-dev
sudo apt install -y certbot python3-certbot-nginx
sudo apt install -y htop iotop nethogs supervisor
```

### 3. 应用部署

```bash
# 克隆生产代码
cd ~/app
git clone -b master https://github.com/cloudQuant/woniunote.git .

# 创建虚拟环境
python3.8 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn[gevent]
pip install -e .
```

### 4. 生产数据库配置

```bash
# 配置MySQL安全设置
sudo mysql_secure_installation

# 创建生产数据库
sudo mysql -u root -p << EOF
CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'woniunote'@'localhost' IDENTIFIED BY '$(openssl rand -base64 32)';
GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 5. 生产配置文件

```bash
# 生成安全密钥
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex())')
export DB_PASSWORD=$(openssl rand -base64 32)

# 创建环境配置文件
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=mysql+pymysql://woniunote:${DB_PASSWORD}@localhost/woniunote
REDIS_URL=redis://localhost:6379/0

# 安全配置
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
WTF_CSRF_ENABLED=True

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/home/woniunote/logs/app.log

# 邮件配置
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
EOF

# 设置文件权限
chmod 600 .env
```

### 6. 数据库初始化

```bash
# 加载环境变量
source .env

# 初始化生产数据库
python scripts/init_db_direct.py

# 创建管理员账户
python scripts/create_admin.py
```

### 7. Gunicorn配置

```bash
# 创建Gunicorn配置文件
cat > gunicorn.conf.py << 'EOF'
# Gunicorn配置文件
import multiprocessing
import os

# 服务器配置
bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000

# 进程配置
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 30
keepalive = 2

# 日志配置
accesslog = "/home/woniunote/logs/gunicorn_access.log"
errorlog = "/home/woniunote/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程管理
user = "woniunote"
group = "woniunote"
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
EOF
```

### 8. Systemd服务配置

```bash
# 创建systemd服务文件
sudo tee /etc/systemd/system/woniunote.service << 'EOF'
[Unit]
Description=WoniuNote Flask Application
After=network.target mysql.service redis.service
Requires=mysql.service redis.service

[Service]
Type=notify
User=woniunote
Group=woniunote
RuntimeDirectory=woniunote
WorkingDirectory=/home/woniunote/app
Environment=PATH=/home/woniunote/app/venv/bin
EnvironmentFile=/home/woniunote/app/.env
ExecStart=/home/woniunote/app/venv/bin/gunicorn \
    --config /home/woniunote/app/gunicorn.conf.py \
    woniunote.app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd配置
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable woniunote
sudo systemctl start woniunote

# 检查服务状态
sudo systemctl status woniunote
```

### 9. Nginx配置

```bash
# 创建Nginx站点配置
sudo tee /etc/nginx/sites-available/woniunote << 'EOF'
# WoniuNote Nginx配置
upstream woniunote_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS主站点
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL配置
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # 安全头
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 文件上传大小限制
    client_max_body_size 10M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # 日志配置
    access_log /var/log/nginx/woniunote_access.log;
    error_log /var/log/nginx/woniunote_error.log;

    # 静态文件处理
    location /static {
        alias /home/woniunote/app/woniunote/resource;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # Gzip压缩
        gzip on;
        gzip_vary on;
        gzip_types
            text/css
            text/javascript
            text/xml
            text/plain
            application/javascript
            application/xml+rss
            application/json;
    }

    # 上传文件处理
    location /uploads {
        alias /home/woniunote/app/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 应用代理
    location / {
        proxy_pass http://woniunote_app;
        proxy_redirect off;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API速率限制
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://woniunote_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        access_log off;
        proxy_pass http://woniunote_app;
    }
}
EOF

# 创建速率限制配置
sudo tee /etc/nginx/conf.d/rate_limit.conf << 'EOF'
# API请求速率限制
limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# 连接数限制
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
limit_conn conn_limit_per_ip 20;
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/woniunote /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
sudo nginx -t

# 启动Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 10. SSL证书配置

```bash
# 使用Certbot获取Let's Encrypt证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 设置证书自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 11. 防火墙配置

```bash
# 配置UFW防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# 检查防火墙状态
sudo ufw status verbose
```

---

## 🔧 配置优化

### MySQL性能优化

```bash
# 编辑MySQL配置
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf

# 添加性能优化配置
[mysqld]
# 内存配置
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_log_buffer_size = 64M
query_cache_size = 128M
query_cache_limit = 2M

# 连接配置
max_connections = 200
thread_cache_size = 16
table_open_cache = 2000

# InnoDB配置
innodb_file_per_table = 1
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# 重启MySQL
sudo systemctl restart mysql
```

### Redis性能优化

```bash
# 编辑Redis配置
sudo vim /etc/redis/redis.conf

# 优化配置
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0

# 重启Redis
sudo systemctl restart redis
```

### 应用性能监控

```bash
# 安装监控工具
pip install psutil redis-py-cluster

# 创建监控脚本
cat > ~/scripts/monitor.py << 'EOF'
#!/usr/bin/env python3
import psutil
import time
import logging
from datetime import datetime

logging.basicConfig(
    filename='/home/woniunote/logs/monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def monitor_system():
    """监控系统资源"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    logging.info(f"CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%")
    
    # 警告阈值
    if cpu_percent > 80:
        logging.warning(f"High CPU usage: {cpu_percent}%")
    if memory.percent > 80:
        logging.warning(f"High memory usage: {memory.percent}%")
    if disk.percent > 80:
        logging.warning(f"High disk usage: {disk.percent}%")

if __name__ == "__main__":
    monitor_system()
EOF

# 设置定时监控
crontab -e
# 添加：*/5 * * * * /home/woniunote/app/venv/bin/python /home/woniunote/scripts/monitor.py
```

---

## 🔄 部署自动化

### 自动化部署脚本

```bash
# 创建部署脚本
cat > ~/scripts/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "开始部署WoniuNote..."

# 1. 备份当前版本
BACKUP_DIR="/home/woniunote/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r /home/woniunote/app $BACKUP_DIR/

# 2. 拉取最新代码
cd /home/woniunote/app
git fetch origin
git checkout master
git pull origin master

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 更新依赖
pip install -r requirements.txt

# 5. 数据库迁移
python scripts/migrate_db.py

# 6. 收集静态文件
python scripts/collect_static.py

# 7. 重启服务
sudo systemctl restart woniunote
sudo systemctl reload nginx

# 8. 健康检查
sleep 10
if curl -f http://localhost:8000/health; then
    echo "部署成功！"
else
    echo "部署失败，正在回滚..."
    sudo systemctl stop woniunote
    rm -rf /home/woniunote/app
    mv $BACKUP_DIR/app /home/woniunote/
    sudo systemctl start woniunote
    exit 1
fi

echo "部署完成！"
EOF

chmod +x ~/scripts/deploy.sh
```

### CI/CD集成（GitHub Actions）

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ master ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /home/woniunote
          ./scripts/deploy.sh
```

---

## 📊 监控与维护

### 系统监控

```bash
# 安装监控工具
sudo apt install -y prometheus node-exporter grafana

# 配置Prometheus
sudo vim /etc/prometheus/prometheus.yml

# 添加监控目标
scrape_configs:
  - job_name: 'woniunote'
    static_configs:
      - targets: ['localhost:8000']
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### 日志管理

```bash
# 配置日志轮转
sudo vim /etc/logrotate.d/woniunote

/home/woniunote/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 0644 woniunote woniunote
    postrotate
        systemctl reload woniunote
    endscript
}
```

### 备份策略

```bash
# 数据库备份脚本
cat > ~/scripts/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/woniunote/backup/db"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="woniunote"

mkdir -p $BACKUP_DIR

# 数据库备份
mysqldump -u woniunote -p$DB_PASSWORD $DB_NAME | gzip > $BACKUP_DIR/woniunote_$DATE.sql.gz

# 删除30天前的备份
find $BACKUP_DIR -name "woniunote_*.sql.gz" -mtime +30 -delete

echo "数据库备份完成: woniunote_$DATE.sql.gz"
EOF

# 设置定时备份
crontab -e
# 添加：0 2 * * * /home/woniunote/scripts/backup_db.sh
```

---

## 🚨 故障排除

### 常见问题及解决方案

#### 1. 应用无法启动
```bash
# 检查服务状态
sudo systemctl status woniunote

# 查看错误日志
sudo journalctl -u woniunote -f

# 检查配置文件
python -c "from woniunote.app import create_app; create_app()"
```

#### 2. 数据库连接失败
```bash
# 检查MySQL状态
sudo systemctl status mysql

# 测试连接
mysql -u woniunote -p woniunote

# 检查权限
mysql -u root -p -e "SHOW GRANTS FOR 'woniunote'@'localhost';"
```

#### 3. Redis连接问题
```bash
# 检查Redis状态
sudo systemctl status redis

# 测试连接
redis-cli ping

# 查看Redis日志
sudo tail -f /var/log/redis/redis-server.log
```

#### 4. Nginx配置问题
```bash
# 测试配置
sudo nginx -t

# 重新加载配置
sudo systemctl reload nginx

# 查看错误日志
sudo tail -f /var/log/nginx/error.log
```

#### 5. SSL证书问题
```bash
# 检查证书状态
sudo certbot certificates

# 手动续期
sudo certbot renew --dry-run

# 强制续期
sudo certbot renew --force-renewal
```

---

## 📈 性能优化

### 应用层优化

```python
# 缓存优化配置
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/1',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'woniunote:',
}

# 数据库连接池优化
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 0
}
```

### 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_articles_user_time ON articles(userid, createtime);
CREATE INDEX idx_articles_type_status ON articles(type, hidden, checked);
CREATE INDEX idx_comments_article ON comments(articleid, createtime);

-- 分析表统计信息
ANALYZE TABLE articles, users, comments, cards;

-- 优化查询
EXPLAIN SELECT * FROM articles WHERE hidden=0 ORDER BY createtime DESC LIMIT 20;
```

---

## 🔒 安全加固

### 系统安全

```bash
# 禁用不必要的服务
sudo systemctl disable bluetooth
sudo systemctl disable cups

# 配置fail2ban
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# 编辑fail2ban配置
sudo vim /etc/fail2ban/jail.local

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
```

### 应用安全

```python
# 安全配置
SECURITY_CONFIG = {
    # CSRF保护
    'WTF_CSRF_ENABLED': True,
    'WTF_CSRF_TIME_LIMIT': 3600,
    
    # 会话安全
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    
    # 密码安全
    'BCRYPT_LOG_ROUNDS': 12,
    'PASSWORD_MIN_LENGTH': 8,
    
    # 文件上传安全
    'MAX_CONTENT_LENGTH': 10 * 1024 * 1024,  # 10MB
    'UPLOAD_ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'pdf'},
}
```

---

## 📝 部署检查清单

### 部署前检查
- [ ] 服务器资源充足（CPU、内存、磁盘）
- [ ] 所有依赖软件已安装
- [ ] 数据库已创建并配置
- [ ] SSL证书已申请
- [ ] 防火墙规则已配置
- [ ] 备份策略已制定

### 部署后验证
- [ ] 应用服务正常启动
- [ ] 数据库连接正常
- [ ] Redis缓存工作正常
- [ ] Nginx反向代理配置正确
- [ ] SSL证书配置有效
- [ ] 所有测试用例通过
- [ ] 监控系统正常运行
- [ ] 日志记录正常

### 性能验证
- [ ] 首页加载时间 < 2秒
- [ ] API响应时间 < 500ms
- [ ] 数据库查询优化
- [ ] 静态资源缓存生效
- [ ] 压力测试通过

---

*部署指南最后更新: 2024年1月15日*