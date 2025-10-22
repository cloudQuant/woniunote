@echo off
title Redis Server
echo 启动Redis服务器...
echo 按Ctrl+C停止服务器
echo.
cd "C:\Program Files\Redis"
redis-server.exe redis.windows-service.conf

