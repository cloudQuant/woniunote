#!/bin/bash

# WoniuNote 启动脚本 - 仅使用 C++ 后端

echo "========================================"
echo "  WoniuNote 应用启动脚本"
echo "  后端: C++ (Drogon)"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查并关闭占用端口5173的进程（后端）
echo "[1/5] 检查后端端口 5173..."
PID_5173=$(lsof -ti:5173 2>/dev/null)
if [ -n "$PID_5173" ]; then
    echo "     发现进程 $PID_5173 占用端口 5173，正在关闭..."
    kill -9 $PID_5173 2>/dev/null
    sleep 1
fi
echo "     端口 5173 已清理"

# 检查并关闭占用端口8888的进程（前端）
echo "[2/5] 检查前端端口 8888..."
PID_8888=$(lsof -ti:8888 2>/dev/null)
if [ -n "$PID_8888" ]; then
    echo "     发现进程 $PID_8888 占用端口 8888，正在关闭..."
    kill -9 $PID_8888 2>/dev/null
    sleep 1
fi
echo "     端口 8888 已清理"

# 等待端口释放
sleep 1

# 生成缩略图
echo "[3/5] 生成文章缩略图..."
if [ -f "$SCRIPT_DIR/backend_cpp/scripts/generate_thumbs.py" ]; then
    python3 "$SCRIPT_DIR/backend_cpp/scripts/generate_thumbs.py" > /dev/null 2>&1
    echo "     缩略图生成完成"
else
    echo "     跳过缩略图生成（脚本不存在）"
fi

# 启动C++后端
echo "[4/5] 启动后端服务..."

# 先自动编译
echo "     正在编译C++后端..."
cd "$SCRIPT_DIR/backend_cpp"
if [ ! -d "build" ]; then
    mkdir build
fi
cd build
if [ ! -f "Makefile" ] && [ ! -f "build.ninja" ]; then
    cmake .. -DCMAKE_TOOLCHAIN_FILE="$HOME/vcpkg/scripts/buildsystems/vcpkg.cmake" -DCMAKE_BUILD_TYPE=Release
fi
cmake --build . --config Release -j8 2>&1 | tail -5
cd "$SCRIPT_DIR"

# 查找可执行文件
CPP_DIR=""
CPP_EXE=""
if [ -f "$SCRIPT_DIR/backend_cpp/build/woniunote_backend" ]; then
    CPP_DIR="$SCRIPT_DIR/backend_cpp/build"
    CPP_EXE="woniunote_backend"
elif [ -f "$SCRIPT_DIR/backend_cpp/build/Release/woniunote_backend" ]; then
    CPP_DIR="$SCRIPT_DIR/backend_cpp/build/Release"
    CPP_EXE="woniunote_backend"
else
    echo "[错误] C++后端编译失败"
    exit 1
fi

echo "     启动C++后端从: $CPP_DIR"
# 切换到可执行文件目录以便找到config.json
cd "$CPP_DIR"
nohup "./$CPP_EXE" >> "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "     后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 3

# 检查后端是否成功启动
if ! lsof -ti:5173 >/dev/null 2>&1; then
    echo "[警告] 后端可能未成功启动，请检查 backend.log"
fi

# 启动前端
echo "[5/5] 启动前端服务..."
cd "$SCRIPT_DIR/frontend"
if [ ! -f "package.json" ]; then
    echo "[错误] 未找到前端配置文件 frontend/package.json"
    exit 1
fi

nohup npm run dev >> ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "     前端服务已启动 (PID: $FRONTEND_PID)"

# 等待前端启动
sleep 5

# 检查前端是否成功启动
if ! lsof -ti:8888 >/dev/null 2>&1; then
    echo "[警告] 前端可能未成功启动，请检查 frontend.log"
fi

echo ""
echo "========================================"
echo "  启动成功!"
echo "========================================"
echo "  后端地址: http://localhost:5173"
echo "  前端地址: http://localhost:8888"
echo "========================================"
echo "  日志文件:"
echo "  - backend.log  (后端日志)"
echo "  - frontend.log (前端日志)"
echo "========================================"
echo "  进程ID:"
echo "  - 后端: $BACKEND_PID"
echo "  - 前端: $FRONTEND_PID"
echo "========================================"

cd "$SCRIPT_DIR"
exit 0
