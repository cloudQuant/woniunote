@echo off
chcp 65001 >nul
title Redis 环境检查工具

echo ================================================================
echo                    Redis 环境检查工具
echo ================================================================
echo.

REM 切换到脚本目录
cd /d "%~dp0"

echo 正在检查Redis环境...
echo.

REM 运行Python检查脚本
python quick_redis_setup.py

echo.
echo 检查完成
pause
