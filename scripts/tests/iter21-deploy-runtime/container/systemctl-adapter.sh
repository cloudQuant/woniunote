#!/usr/bin/env bash
set -Eeuo pipefail

STATE="${ITER21_STATE:?adapter state path missing}"
DATA="${ITER21_DATA:?adapter data path missing}"
PID_FILE="$DATA/woniunote.pid"
command="${1:-}"
shift || true
while [ "${1:-}" = --quiet ] || [ "${1:-}" = --no-block ]; do shift; done
service="${1:-}"

case "$command:$service" in
    daemon-reload:)
        exit 0
        ;;
    start:nginx)
        if [ -s /run/nginx.pid ] && kill -0 "$(cat /run/nginx.pid)" 2>/dev/null; then exit 0; fi
        exec /usr/sbin/nginx -c /etc/nginx/nginx.conf
        ;;
    reload:nginx)
        exec /usr/sbin/nginx -c /etc/nginx/nginx.conf -s reload
        ;;
    is-active:nginx)
        [ -s /run/nginx.pid ] && kill -0 "$(cat /run/nginx.pid)" 2>/dev/null
        ;;
    stop:woniunote)
        if [ -s "$PID_FILE" ]; then
            pid="$(cat "$PID_FILE")"
            kill -TERM "$pid" 2>/dev/null || true
            for _ in $(seq 1 50); do kill -0 "$pid" 2>/dev/null || break; sleep 0.1; done
            kill -KILL "$pid" 2>/dev/null || true
            rm -f "$PID_FILE"
        fi
        ;;
    start:woniunote)
        [ -L "$STATE/current" ] || { printf 'fixture current release missing\n' >&2; exit 1; }
        nohup bash "$STATE/current/backend_cpp/release_run_backend.sh" "$STATE/current" \
            > "$DATA/woniunote-adapter.log" 2>&1 < /dev/null &
        printf '%s\n' "$!" > "$PID_FILE"
        for _ in $(seq 1 50); do
            curl -fsS --max-time 1 http://127.0.0.1:5173/health >/dev/null 2>&1 && exit 0
            sleep 0.1
        done
        exit 1
        ;;
    is-active:woniunote)
        [ -s "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null &&
            curl -fsS --max-time 1 http://127.0.0.1:5173/health >/dev/null 2>&1
        ;;
    *)
        printf 'systemctl adapter unsupported command: %s %s\n' "$command" "$service" >&2
        exit 64
        ;;
esac
