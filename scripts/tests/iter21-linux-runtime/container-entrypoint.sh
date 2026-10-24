#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" != 2 ]]; then
  echo "runtime entrypoint requires <http-port> <config-path>" >&2
  exit 64
fi

port="$1"
config_path="$2"
if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || (( port < 1024 || port > 65535 )); then
  echo "runtime entrypoint received an invalid HTTP port" >&2
  exit 64
fi
if [[ "$config_path" != /* || ! -f "$config_path" ]]; then
  echo "runtime entrypoint received an invalid config path" >&2
  exit 64
fi

mapfile -t eth0_addresses < <(/sbin/ip -4 -o addr show dev eth0 scope global | awk '{sub(/\/.*/, "", $4); print $4}')
if [[ "${#eth0_addresses[@]}" != 1 || ! "${eth0_addresses[0]}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "runtime entrypoint could not identify one global IPv4 address on eth0" >&2
  exit 70
fi
eth0_address="${eth0_addresses[0]}"

/opt/woniunote_backend "$config_path" &
backend_pid=$!
/usr/bin/socat \
  "TCP4-LISTEN:${port},bind=${eth0_address},reuseaddr,fork" \
  "TCP4:127.0.0.1:${port}" &
forwarder_pid=$!

cleanup() {
  local pid
  trap - EXIT INT TERM
  for pid in "$forwarder_pid" "$backend_pid"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for _ in $(seq 1 50); do
    local remaining=0
    for pid in "$forwarder_pid" "$backend_pid"; do
      if kill -0 "$pid" 2>/dev/null; then remaining=1; fi
    done
    [[ "$remaining" == 0 ]] && break
    sleep 0.1
  done
  for pid in "$forwarder_pid" "$backend_pid"; do
    kill -KILL "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

set +e
wait -n "$backend_pid" "$forwarder_pid"
status=$?
set -e
exit "$status"
