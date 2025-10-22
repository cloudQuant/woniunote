@echo off
chcp 65001 >nul
title WoniuNote Redis 安装工具

echo ================================================================
echo                    WoniuNote Redis 安装工具
echo ================================================================
echo.
echo 此工具将自动安装和配置Redis环境，解决缓存功能不可用的问题
echo.
echo 安装内容:
echo   - Redis Server 5.0.14.1
echo   - Redis Windows 服务
echo   - 自动配置和启动
echo   - 环境变量设置
echo.
echo 注意: 需要管理员权限才能安装Windows服务
echo.

pause

echo.
echo 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python环境检查通过
echo.

echo 开始安装Redis...
echo.

REM 切换到脚本目录
cd /d "%~dp0"

REM 运行Python安装脚本
python install_redis_windows.py

if errorlevel 1 (
    echo.
    echo 安装过程中出现错误
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo ================================================================
echo                        安装完成
echo ================================================================
echo.
echo Redis已成功安装到系统中
echo 现在可以在WoniuNote项目中使用Redis缓存功能了
echo.
echo 管理Redis服务:
echo   启动: sc start Redis
echo   停止: sc stop Redis
echo   状态: sc query Redis
echo.
echo 测试连接:
echo   redis-cli ping
echo.

pause
