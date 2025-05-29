@echo off
REM 快速测试运行脚本 - Windows版本
REM 使用方法: run_fast_tests.bat [测试文件/目录] [选项]

setlocal enabledelayedexpansion

echo 🚀 WoniuNote 快速测试运行器
echo.

REM 设置快速模式环境变量
set PYTEST_FAST_MODE=1
set SKIP_DB_INIT=1
set DISABLE_LOGGING=1

REM 检查是否传入了测试路径参数
set "TEST_PATH=%~1"
if "%TEST_PATH%"=="" (
    set "TEST_PATH=tests/"
    echo 📁 运行所有测试文件
) else (
    echo 📁 运行测试: %TEST_PATH%
)

REM 移除第一个参数，保留其他选项
shift
set "EXTRA_ARGS="
:parse_args
if "%~1"=="" goto :run_tests
set "EXTRA_ARGS=%EXTRA_ARGS% %~1"
shift
goto :parse_args

:run_tests
echo.
echo ⏱️  开始时间: %time%
echo.

REM 根据不同场景选择运行方式

REM 1. 只运行单元测试（最快）
if "%EXTRA_ARGS:unit-only=%" neq "%EXTRA_ARGS%" (
    echo 🎯 运行模式: 仅单元测试
    python tests/run_tests_fast.py %TEST_PATH% --unit-only %EXTRA_ARGS%
    goto :end
)

REM 2. 跳过数据库初始化的快速测试
if "%EXTRA_ARGS:no-db=%" neq "%EXTRA_ARGS%" (
    echo 🎯 运行模式: 跳过数据库初始化
    python tests/run_tests_fast.py %TEST_PATH% --no-db %EXTRA_ARGS%
    goto :end
)

REM 3. 并行测试（默认）
echo 🎯 运行模式: 并行测试
python tests/run_tests_fast.py %TEST_PATH% --workers 4 %EXTRA_ARGS%

:end
echo.
echo ⏱️  结束时间: %time%
echo 🎉 测试完成！

REM 常用命令提示
echo.
echo 💡 常用快速测试命令:
echo    run_fast_tests.bat --unit-only          # 只运行单元测试
echo    run_fast_tests.bat --no-db              # 跳过数据库初始化
echo    run_fast_tests.bat tests/test_basic_app.py  # 运行特定文件
echo    run_fast_tests.bat --workers 8          # 使用8个并行worker
echo    run_fast_tests.bat --fail-fast          # 遇到失败立即停止
echo.

pause 