#!/usr/bin/env bash
# Production stop shares the deployment lock. Development servers use the same
# lock and are stopped gracefully before an optional bounded SIGKILL.
MODE="$1"
[ -n "$MODE" ] || MODE=prod
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$MODE" = prod ]; then
    exec bash "$SCRIPT_DIR/scripts/deploy_release.sh" stop
fi
if [ "$MODE" != dev ]; then
    echo "用法: bash stop_app.sh [prod|dev]" >&2
    exit 2
fi
if [ "$2" != --locked ]; then
    exec bash "$SCRIPT_DIR/scripts/deploy_release.sh" run-locked bash "$0" dev --locked
fi

stop_port() {
    local port="$1" pids pid elapsed
    if ! command -v lsof >/dev/null 2>&1; then
        echo "[错误] dev 停止需要 lsof" >&2
        return 1
    fi
    pids="$(lsof -ti:"$port" 2>/dev/null || true)"
    [ -n "$pids" ] || return 0
    for pid in $pids; do kill -TERM "$pid" 2>/dev/null || true; done
    elapsed=0
    while [ "$elapsed" -lt 10 ]; do
        if ! lsof -ti:"$port" >/dev/null 2>&1; then return 0; fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    pids="$(lsof -ti:"$port" 2>/dev/null || true)"
    for pid in $pids; do kill -KILL "$pid" 2>/dev/null || true; done
    sleep 1
    ! lsof -ti:"$port" >/dev/null 2>&1
}

stop_port 5173 || exit 1
stop_port 8888 || exit 1
echo "dev 后端和前端已停止"
