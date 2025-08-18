@echo off
chcp 65001 >nul
echo 🚀 开始同时推送到Gitee和GitHub...
echo 时间: %date% %time%

REM 获取提交信息
set commit_message=%*
if "%commit_message%"=="" (
    set commit_message=Auto commit at %date% %time%
)

echo 提交信息: %commit_message%

REM 添加所有文件
echo.
echo 🔄 添加文件到暂存区...
git add .
if errorlevel 1 (
    echo ❌ 添加文件失败
    pause
    exit /b 1
)
echo ✅ 添加文件成功

REM 提交更改
echo.
echo 🔄 提交更改...
git commit -m "%commit_message%"
if errorlevel 1 (
    echo ❌ 提交失败
    pause
    exit /b 1
)
echo ✅ 提交成功

REM 推送到Gitee
echo.
echo 🔄 推送到Gitee...
git push gitee
if errorlevel 1 (
    echo ⚠️  Gitee推送失败，但继续尝试GitHub...
) else (
    echo ✅ Gitee推送成功
)

REM 推送到GitHub
echo.
echo 🔄 推送到GitHub...
git push github
if errorlevel 1 (
    echo ⚠️  GitHub推送失败
) else (
    echo ✅ GitHub推送成功
)

echo.
echo 🎉 推送操作完成！
echo 📊 推送结果:
echo    - Gitee: https://gitee.com/yunjinqi/woniunote
echo    - GitHub: https://github.com/cloudQuant/woniunote
pause
