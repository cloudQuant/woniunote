#!/usr/bin/env bash
# Production restart is a frozen-SHA deployment. Development restart is locked
# for both stop and start so it cannot overlap a release transaction.
MODE="$1"
[ -n "$MODE" ] || MODE=prod
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$MODE" != prod ] && [ "$MODE" != dev ]; then
    echo "用法: bash restart_app.sh [prod|dev]" >&2
    exit 2
fi

if [ "$MODE" = prod ]; then
    exec bash "$SCRIPT_DIR/scripts/deploy_release.sh" deploy --sha HEAD
fi

if [ "$2" != --locked ]; then
    exec bash "$SCRIPT_DIR/scripts/deploy_release.sh" run-locked bash "$0" dev --locked
fi

bash "$SCRIPT_DIR/stop_app.sh" dev --locked
bash "$SCRIPT_DIR/start_app.sh" dev --locked
