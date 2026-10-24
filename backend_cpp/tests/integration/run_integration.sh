#!/usr/bin/env bash
# Per-run isolated backend integration harness. External targets are fail-closed.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

if [[ -n "${WONIUNOTE_TEST_BASE_URL-}" ]]; then
  echo "ERROR: external backend targets are disabled; no external writes were made." >&2
  exit 2
fi
for variable in WONIUNOTE_TEST_DB_HOST WONIUNOTE_TEST_DB_PORT WONIUNOTE_TEST_DB_NAME \
  WONIUNOTE_TEST_REDIS_HOST WONIUNOTE_TEST_REDIS_PORT WONIUNOTE_TEST_SKIP_DB_SETUP; do
  if [[ -n "$(printenv "$variable" 2>/dev/null || true)" ]]; then
    echo "ERROR: $variable is not accepted; this runner creates disposable services." >&2
    exit 2
  fi
done

if [[ -n "${WONIUNOTE_TEST_PYTHON-}" ]]; then
  PYTHON_RUN=("$WONIUNOTE_TEST_PYTHON")
elif [[ -x /Users/yunjinqi/opt/anaconda3/bin/conda ]]; then
  PYTHON_RUN=(/Users/yunjinqi/opt/anaconda3/bin/conda run --no-capture-output -n base python)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_RUN=("$(command -v python3)")
else
  echo "ERROR: Python missing; set WONIUNOTE_TEST_PYTHON to an executable path." >&2
  exit 2
fi
if [[ -n "${WONIUNOTE_TEST_PYTHON-}" && ! -x "$WONIUNOTE_TEST_PYTHON" ]]; then
  echo "ERROR: WONIUNOTE_TEST_PYTHON must be one executable path." >&2
  exit 2
fi
if ! "${PYTHON_RUN[@]}" -c 'import pytest, requests, pymysql, redis' >/dev/null 2>&1; then
  echo "ERROR: pytest, requests, pymysql, and redis are required in the selected environment." >&2
  exit 2
fi
for required in docker curl realpath rg pgrep ps; do
  command -v "$required" >/dev/null 2>&1 || { echo "ERROR: missing $required" >&2; exit 2; }
done
docker info >/dev/null 2>&1 || { echo "ERROR: Docker daemon unavailable; no data changed." >&2; exit 2; }

BACKEND_BIN="${WONIUNOTE_BACKEND_BIN:-$BACKEND_DIR/build/woniunote_backend}"
[[ -x "$BACKEND_BIN" ]] || { echo "ERROR: backend binary missing: $BACKEND_BIN" >&2; exit 2; }
MYSQL_IMAGE="${WONIUNOTE_TEST_MYSQL_IMAGE:-mysql@sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b}"
REDIS_IMAGE="${WONIUNOTE_TEST_REDIS_IMAGE:-redis@sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85}"
REAL_E2E="${WONIUNOTE_TEST_REAL_E2E:-0}"
KEEP_SERVICES="${WONIUNOTE_TEST_KEEP_SERVICES:-0}"
STRICT="${WONIUNOTE_TEST_STRICT:-1}"
SCENARIO="${WONIUNOTE_TEST_SCENARIO:-functional}"
if [[ "$SCENARIO" == rate-limit ]]; then
  RATE_LIMIT="${WONIUNOTE_TEST_RATE_LIMIT:-60}"
  [[ "$RATE_LIMIT" == 60 ]] || { echo "ERROR: rate-limit scenario must use the product default of 60/minute." >&2; exit 2; }
else
  RATE_LIMIT="${WONIUNOTE_TEST_RATE_LIMIT:-1000}"
fi
[[ "$SCENARIO" == functional || "$SCENARIO" == rate-limit ]] || {
  echo "ERROR: test scenario must be functional or rate-limit." >&2
  exit 2
}
export WN_I21_SCENARIO="$SCENARIO" WN_I21_CONFIGURED_RATE_LIMIT="$RATE_LIMIT"
[[ "$REAL_E2E" == 0 || "$REAL_E2E" == 1 ]] || { echo "ERROR: REAL_E2E must be 0 or 1." >&2; exit 2; }
[[ "$KEEP_SERVICES" == 0 || "$KEEP_SERVICES" == 1 ]] || { echo "ERROR: KEEP_SERVICES must be 0 or 1." >&2; exit 2; }
if [[ "$REAL_E2E" == 1 ]]; then
  [[ "$SCENARIO" == functional ]] || { echo "ERROR: real E2E requires the functional scenario." >&2; exit 2; }
  [[ -x "$FRONTEND_DIR/node_modules/.bin/playwright" ]] || { echo "ERROR: frontend Playwright dependencies missing." >&2; exit 2; }
  NODE_VERSION="$(node --version 2>/dev/null || true)"
  [[ "$NODE_VERSION" == v22.13.0 ]] || { echo "ERROR: real E2E requires Node v22.13.0 (found ${NODE_VERSION:-missing})." >&2; exit 2; }
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')"
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]] || { echo "ERROR: invalid generated run ID." >&2; exit 2; }
RUN_ROOT="${TMPDIR:-/tmp}/woniunote-iter21"
RUN_DIR="$RUN_ROOT/$RUN_ID"
RESULT_ROOT="${WONIUNOTE_TEST_ARTIFACT_ROOT:-$RUN_ROOT/results}"
RESULT_DIR="$RESULT_ROOT/$RUN_ID"
mkdir -p "$RUN_ROOT"
mkdir -m 700 "$RUN_DIR" || { echo "ERROR: refusing to reuse runtime directory." >&2; exit 2; }
chmod 700 "$RUN_ROOT"
mkdir -m 700 "$RUN_DIR/logs" "$RUN_DIR/uploads" "$RUN_DIR/evidence" "$RUN_DIR/backend-runtime"

MYSQL_NAME="woniunote-i21-$RUN_ID-mysql"
REDIS_NAME="woniunote-i21-$RUN_ID-redis"
MYSQL_VOLUME_NAME="woniunote-i21-$RUN_ID-mysql-data"
DB_NAME="woniunote_test_${RUN_ID//-/}"
DB_USER=root
# The double quote exercises JSON escaping. Keep SQL-safe punctuation only:
# mysql:8.0's entrypoint interpolates this value into a SQL string literal.
DB_PASSWORD="i21-$RUN_ID-quote\"-slash-db"
REDIS_PASSWORD="i21-$RUN_ID-quote\"-slash\\-redis"
TEST_PORT="${WONIUNOTE_TEST_PORT-}"
FRONTEND_PORT="${WONIUNOTE_TEST_FRONTEND_PORT-}"
MYSQL_CONTAINER_ID=""
REDIS_CONTAINER_ID=""
MYSQL_PORT=""
REDIS_PORT=""
MYSQL_VOLUME_DRIVER=""
MYSQL_VOLUME_STATUS="not-created"
MYSQL_CONTAINER_STATUS="not-started"
MYSQL_CONTAINER_EXIT_CODE=""
MYSQL_IMAGE_ID=""
MYSQL_IMAGE_VERSION=""
MYSQL_TLS_STATUS="not-verified"
REDIS_CONTAINER_STATUS="not-started"
REDIS_CONTAINER_EXIT_CODE=""
REDIS_IMAGE_ID=""
REDIS_IMAGE_VERSION=""
SERVER_PID=""
ACTIVE_CHILD_PID=""
CONFIG_OUT="$RUN_DIR/config.integration.json"
SERVER_LOG="$RUN_DIR/logs/backend.log"
BACKEND_CWD="$RUN_DIR/backend-runtime"
BASE_URL=""
FRONTEND_URL=""
SERVICES_READY=0
RUN_COMPLETED=0
BACKEND_SHUTDOWN_TERM_SENT=0
BACKEND_SHUTDOWN_WAIT_EXIT_CODE=""
BACKEND_SHUTDOWN_FORCED_KILL=0
BACKEND_SHUTDOWN_RESULT="not_started"
BACKEND_SHUTDOWN_ABNORMAL=0
SERVER_LOG_INDEX_REFERENCE=""

choose_port() {
  "${PYTHON_RUN[@]}" - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}
choose_distinct_port() {
  local candidate excluded
  for _ in $(seq 1 32); do
    candidate="$(choose_port)"
    local is_excluded=0
    for excluded in "$@"; do
      if [[ "$candidate" == "$excluded" ]]; then
        is_excluded=1
        break
      fi
    done
    [[ "$is_excluded" == 0 ]] || continue
    if check_port_free "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}
check_port_free() {
  "${PYTHON_RUN[@]}" - "$1" <<'PY'
import socket
import sys
with socket.socket() as sock:
    sock.settimeout(0.2)
    raise SystemExit(1 if sock.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 0)
PY
}

write_phase_summary() {
  local filename="$1"
  local suite="$2"
  printf '{"run_id":"%s","suite":"%s","result":"passed"}\n' \
    "$RUN_ID" "$suite" > "$RUN_DIR/evidence/$filename"
  chmod 600 "$RUN_DIR/evidence/$filename"
}

write_manifest() {
  export WN_I21_MANIFEST_PATH="$RUN_DIR/run.json"
  export WN_I21_RUN_ID="$RUN_ID" WN_I21_RUN_DIR="$RUN_DIR"
  export WN_I21_MYSQL_NAME="$MYSQL_NAME" WN_I21_REDIS_NAME="$REDIS_NAME"
  export WN_I21_MYSQL_VOLUME_NAME="$MYSQL_VOLUME_NAME"
  export WN_I21_MYSQL_VOLUME_DRIVER="$MYSQL_VOLUME_DRIVER"
  export WN_I21_MYSQL_VOLUME_STATUS="$MYSQL_VOLUME_STATUS"
  export WN_I21_BACKEND_SHUTDOWN_TERM_SENT="$BACKEND_SHUTDOWN_TERM_SENT"
  export WN_I21_BACKEND_SHUTDOWN_WAIT_EXIT_CODE="$BACKEND_SHUTDOWN_WAIT_EXIT_CODE"
  export WN_I21_BACKEND_SHUTDOWN_FORCED_KILL="$BACKEND_SHUTDOWN_FORCED_KILL"
  export WN_I21_BACKEND_SHUTDOWN_RESULT="$BACKEND_SHUTDOWN_RESULT"
  export WN_I21_BACKEND_SHUTDOWN_ABNORMAL="$BACKEND_SHUTDOWN_ABNORMAL"
  export WN_I21_SERVER_LOG="$SERVER_LOG"
  export WN_I21_SERVER_LOG_INDEX_REFERENCE="$SERVER_LOG_INDEX_REFERENCE"
  export WN_I21_MYSQL_ID="$MYSQL_CONTAINER_ID" WN_I21_REDIS_ID="$REDIS_CONTAINER_ID"
  export WN_I21_MYSQL_PORT="$MYSQL_PORT" WN_I21_REDIS_PORT="$REDIS_PORT"
  export WN_I21_TEST_PORT="$TEST_PORT" WN_I21_FRONTEND_PORT="$FRONTEND_PORT"
  export WN_I21_BASE_URL="$BASE_URL" WN_I21_FRONTEND_URL="$FRONTEND_URL"
  export WN_I21_DB_NAME="$DB_NAME" WN_I21_BACKEND_BIN="$BACKEND_BIN"
  export WN_I21_SERVER_PID="$SERVER_PID"
  export WN_I21_MYSQL_IMAGE="$MYSQL_IMAGE" WN_I21_REDIS_IMAGE="$REDIS_IMAGE"
  export WN_I21_MYSQL_CONTAINER_STATUS="$MYSQL_CONTAINER_STATUS"
  export WN_I21_MYSQL_CONTAINER_EXIT_CODE="$MYSQL_CONTAINER_EXIT_CODE"
  export WN_I21_MYSQL_TLS_STATUS="$MYSQL_TLS_STATUS"
  export WN_I21_MYSQL_IMAGE_ID="$MYSQL_IMAGE_ID" WN_I21_MYSQL_IMAGE_VERSION="$MYSQL_IMAGE_VERSION"
  export WN_I21_REDIS_CONTAINER_STATUS="$REDIS_CONTAINER_STATUS"
  export WN_I21_REDIS_CONTAINER_EXIT_CODE="$REDIS_CONTAINER_EXIT_CODE"
  export WN_I21_REDIS_IMAGE_ID="$REDIS_IMAGE_ID" WN_I21_REDIS_IMAGE_VERSION="$REDIS_IMAGE_VERSION"
  "${PYTHON_RUN[@]}" - <<'PY'
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

def classify_backend_log(server_log_data):
    categories = {
        "assertion_failure": False,
        "terminate_called": False,
        "allocator_double_free": False,
        "allocator_corruption": False,
        "resource_deadlock_avoided": False,
        "ubsan_runtime_error": False,
    }
    exception_type = None
    asan_error_type = None
    asan_frames = []
    ubsan_location = None
    if server_log_data is None:
        return categories, exception_type, asan_error_type, asan_frames, ubsan_location

    lowered_log = server_log_data.lower()
    categories.update({
        "assertion_failure": re.search(
            rb"\bassertion\b[^\n]{0,512}\bfailed\b", server_log_data, re.IGNORECASE,
        ) is not None,
        "terminate_called": b"terminate called" in lowered_log,
        "allocator_double_free": b"double free" in lowered_log,
        "allocator_corruption": any(
            marker in lowered_log for marker in
            (b"corruption", b"corrupted", b"invalid pointer", b"heap corruption")
        ),
        "resource_deadlock_avoided": b"resource deadlock avoided" in lowered_log,
        "ubsan_runtime_error": b"runtime error:" in lowered_log,
    })
    exception_match = re.search(
        rb"""terminate called after throwing an instance of ['"](std::[A-Za-z_]{1,64})['"]""",
        server_log_data,
    )
    exception_value = exception_match.group(1) if exception_match else b""
    if re.fullmatch(rb"std::[A-Za-z_]{1,64}", exception_value):
        exception_type = exception_value.decode("ascii")

    asan_error_prefixes = (
        (b"attempting free on address which was not malloc()-ed", "invalid_free"),
        (b"attempting double-free", "double_free"),
        (b"heap-use-after-free", "heap_use_after_free"),
        (b"stack-use-after-return", "stack_use_after_return"),
        (b"stack-use-after-scope", "stack_use_after_scope"),
        (b"heap-buffer-overflow", "heap_buffer_overflow"),
        (b"stack-buffer-overflow", "stack_buffer_overflow"),
        (b"global-buffer-overflow", "global_buffer_overflow"),
        (b"use-after-poison", "use_after_poison"),
        (b"alloc-dealloc-mismatch", "alloc_dealloc_mismatch"),
        (b"new-delete-type-mismatch", "new_delete_type_mismatch"),
        (b"container-overflow", "container_overflow"),
        (b"stack-overflow", "stack_overflow"),
        (b"odr-violation", "odr_violation"),
        (b"initialization-order-fiasco", "initialization_order_fiasco"),
        (b"negative-size-param", "negative_size_param"),
        (b"memcpy-param-overlap", "memcpy_param_overlap"),
        (b"allocation-size-too-big", "allocation_size_too_big"),
        (b"unknown-crash", "unknown_crash"),
    )
    asan_header = re.compile(
        rb"^(?:==[0-9]+==)?ERROR: AddressSanitizer: ([^\r\n]+)$"
    )
    source_location = re.compile(
        rb"(?P<path>(?:/[A-Za-z0-9_./+-]+|(?:\.\.?/)?[A-Za-z0-9_./+-]+))"
        rb":(?P<line>[0-9]{1,10})(?::[0-9]{1,10})?$"
    )
    ubsan_header = re.compile(
        rb"^(?P<path>(?:/[A-Za-z0-9_./+-]+|(?:\.\.?/)?[A-Za-z0-9_./+-]+))"
        rb":(?P<line>[0-9]{1,10}):(?P<column>[0-9]{1,10}): runtime error: [^\r\n]+$"
    )
    module_location = re.compile(
        rb"(?P<path>(?:/[A-Za-z0-9_./+-]+|[A-Za-z0-9_./+-]+))"
        rb"\+0x(?P<offset>[0-9a-fA-F]{1,16})"
    )
    frame_line = re.compile(
        rb"^\s*#(?P<index>[0-9]{1,6})\s+0x[0-9a-fA-F]{1,16}\s+"
        rb"(?P<body>.{1,4096}?)\s*$"
    )
    phase = None
    report_active = False
    for line in server_log_data.splitlines():
        header = asan_header.fullmatch(line)
        if header:
            report_active = True
            phase = "error"
            header_text = header.group(1)
            for prefix, enum_value in asan_error_prefixes:
                if header_text.startswith(prefix):
                    asan_error_type = enum_value
                    break
            continue
        if re.fullmatch(
            rb"(?:==[0-9]+==)?(?:SUMMARY: AddressSanitizer:.*|==[0-9]+==ABORTING)",
            line,
        ):
            report_active = False
            phase = None
            continue
        if report_active and re.fullmatch(rb"\s*freed by thread T[0-9]+ here:\s*", line):
            phase = "freed"
            continue
        if report_active and re.fullmatch(
            rb"\s*(?:previously )?allocated by thread T[0-9]+ here:\s*", line,
        ):
            phase = "allocated"
            continue
        if report_active and re.fullmatch(
            rb"\s*Thread T[0-9]+ created by T[0-9]+ here:\s*", line,
        ):
            phase = "thread_created"
            continue
        if ubsan_location is None:
            ubsan_match = ubsan_header.fullmatch(line)
            if ubsan_match:
                basename = ubsan_match.group("path").rsplit(b"/", 1)[-1]
                if re.fullmatch(rb"[A-Za-z0-9_.+-]{1,128}", basename):
                    ubsan_location = {
                        "basename": basename.decode("ascii"),
                        "line": int(ubsan_match.group("line")),
                        "column": int(ubsan_match.group("column")),
                    }
        if phase is None or len(asan_frames) >= 32:
            continue
        frame = frame_line.fullmatch(line)
        if not frame:
            continue

        body = frame.group("body").strip()
        has_symbol_section = body.startswith(b"in ")
        location_text = body[3:].strip() if has_symbol_section else body
        location_text = re.sub(
            rb"\s+\(BuildId: [0-9a-fA-F]{1,128}\)$", b"", location_text,
        )
        location_match = source_location.search(location_text)
        location_kind = None
        location_value = None
        if location_match:
            path = location_match.group("path")
            basename = path.rsplit(b"/", 1)[-1]
            if not re.fullmatch(rb"[A-Za-z0-9_.+-]{1,128}", basename):
                continue
            location_kind = "source"
            location_value = {
                "basename": basename.decode("ascii"),
                "line": int(location_match.group("line")),
            }
            symbol_text = location_text[:location_match.start()].rstrip()
        else:
            final_token = location_text.rsplit(None, 1)[-1]
            if final_token.startswith(b"(") and final_token.endswith(b")"):
                final_token = final_token[1:-1]
            module_match = module_location.fullmatch(final_token)
            if not module_match:
                continue
            path = module_match.group("path")
            basename = path.rsplit(b"/", 1)[-1]
            if not re.fullmatch(rb"[A-Za-z0-9_.+-]{1,128}", basename):
                continue
            location_kind = "module"
            location_value = {
                "basename": basename.decode("ascii"),
                "offset": "0x" + module_match.group("offset").decode("ascii").lower(),
            }
            module_start = location_text.rfind(final_token)
            symbol_text = location_text[:module_start].rstrip().rstrip(b"(").rstrip()

        record = {"phase": phase, "index": int(frame.group("index"))}
        symbol_match = re.match(rb"([A-Za-z0-9_:~]{1,128})", symbol_text)
        if has_symbol_section and symbol_match:
            record["symbol"] = symbol_match.group(1).decode("ascii")
        record[location_kind] = location_value
        asan_frames.append(record)

    return categories, exception_type, asan_error_type, asan_frames, ubsan_location

def image_metadata(image, version_variable):
    try:
        raw = subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}|{{json .RepoDigests}}|{{range .Config.Env}}{{println .}}{{end}}", image],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        image_id, repo_digests, env_block = raw.split("|", 2)
        version = next(
            (line.split("=", 1)[1] for line in env_block.splitlines()
             if line.startswith(version_variable + "=")),
            None,
        )
        return {"id": image_id, "repo_digests": json.loads(repo_digests), "version": version}
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return {"id": None, "repo_digests": [], "version": None}

def optional_int(name):
    value = os.environ.get(name, "")
    return int(value) if value.isdecimal() else None

mysql_image = image_metadata(os.environ["WN_I21_MYSQL_IMAGE"], "MYSQL_VERSION")
redis_image = image_metadata(os.environ["WN_I21_REDIS_IMAGE"], "REDIS_VERSION")
mysql_tls_status = os.environ.get("WN_I21_MYSQL_TLS_STATUS")
server_log_path = Path(os.environ["WN_I21_SERVER_LOG"])
try:
    server_log_data = server_log_path.read_bytes()
except OSError:
    server_log_data = None

diagnostic_categories, exception_type, asan_error_type, asan_frames, ubsan_location = classify_backend_log(
    server_log_data,
)

if server_log_data is None:
    server_log_digest = {"sha256": None, "bytes": None, "reference": None}
elif os.environ.get("WN_I21_SERVER_LOG_INDEX_REFERENCE"):
    server_log_digest = {
        "sha256": None,
        "bytes": None,
        "reference": {
            "index": os.environ["WN_I21_SERVER_LOG_INDEX_REFERENCE"],
            "entry": server_log_path.name,
        },
    }
else:
    server_log_digest = {
        "sha256": hashlib.sha256(server_log_data).hexdigest(),
        "bytes": len(server_log_data),
        "reference": None,
    }

manifest = {
    "run_id": os.environ["WN_I21_RUN_ID"],
    "runtime_dir": os.environ["WN_I21_RUN_DIR"] if os.environ.get("WN_I21_RUNTIME_RETAINED") == "1" else None,
    "runtime_retained": os.environ.get("WN_I21_RUNTIME_RETAINED") == "1",
    "restricted_runtime_has_raw_diagnostics": os.environ.get("WN_I21_RUNTIME_RETAINED") == "1",
    "evidence_policy": "sanitized summaries and content-free metadata; raw logs and browser attachments stay in the restricted runtime",
    "artifact_dir": os.environ.get("WN_I21_ARTIFACT_DIR") or None,
    "backend_url": os.environ["WN_I21_BASE_URL"],
    "frontend_url": os.environ["WN_I21_FRONTEND_URL"] or None,
    "database": os.environ["WN_I21_DB_NAME"],
    "scenario": os.environ["WN_I21_SCENARIO"],
    "rate_limit_per_minute": int(os.environ["WN_I21_CONFIGURED_RATE_LIMIT"]),
    "mysql": {
        "container_name": os.environ["WN_I21_MYSQL_NAME"],
        "container_id": os.environ["WN_I21_MYSQL_ID"] or None,
        "host": "127.0.0.1",
        "port": int(os.environ["WN_I21_MYSQL_PORT"]) if os.environ["WN_I21_MYSQL_PORT"] else None,
        "image": os.environ["WN_I21_MYSQL_IMAGE"],
        "image_id": os.environ.get("WN_I21_MYSQL_IMAGE_ID") or mysql_image["id"],
        "image_version": os.environ.get("WN_I21_MYSQL_IMAGE_VERSION") or mysql_image["version"],
        "repo_digests": mysql_image["repo_digests"],
        "container_status": os.environ.get("WN_I21_MYSQL_CONTAINER_STATUS"),
        "container_exit_code": optional_int("WN_I21_MYSQL_CONTAINER_EXIT_CODE"),
        "transport_tls": {
            "enabled": False if mysql_tls_status == "DISABLED" else
                       True if mysql_tls_status in ("YES", "ON") else None,
            "server_have_ssl": mysql_tls_status,
            "scope": "run-owned disposable integration container only",
            "client_policy": "plaintext fallback enabled only in owned backend and test subprocesses",
        },
        "data_volume": {
            "name": os.environ.get("WN_I21_MYSQL_VOLUME_NAME") or None,
            "driver": os.environ.get("WN_I21_MYSQL_VOLUME_DRIVER") or None,
            "identity": {
                "run_id": os.environ["WN_I21_RUN_ID"],
                "service": "mysql",
            },
            "status": os.environ.get("WN_I21_MYSQL_VOLUME_STATUS"),
        },
    },
    "redis": {
        "container_name": os.environ["WN_I21_REDIS_NAME"],
        "container_id": os.environ["WN_I21_REDIS_ID"] or None,
        "host": "127.0.0.1",
        "port": int(os.environ["WN_I21_REDIS_PORT"]) if os.environ["WN_I21_REDIS_PORT"] else None,
        "image": os.environ["WN_I21_REDIS_IMAGE"],
        "image_id": os.environ.get("WN_I21_REDIS_IMAGE_ID") or redis_image["id"],
        "image_version": os.environ.get("WN_I21_REDIS_IMAGE_VERSION") or redis_image["version"],
        "repo_digests": redis_image["repo_digests"],
        "container_status": os.environ.get("WN_I21_REDIS_CONTAINER_STATUS"),
        "container_exit_code": optional_int("WN_I21_REDIS_CONTAINER_EXIT_CODE"),
    },
    "backend_binary": os.environ["WN_I21_BACKEND_BIN"],
    "backend_pid": int(os.environ["WN_I21_SERVER_PID"]) if os.environ["WN_I21_SERVER_PID"] else None,
    "backend_shutdown": {
        "term_sent": os.environ["WN_I21_BACKEND_SHUTDOWN_TERM_SENT"] == "1",
        "wait_exit_code": optional_int("WN_I21_BACKEND_SHUTDOWN_WAIT_EXIT_CODE"),
        "forced_kill": os.environ["WN_I21_BACKEND_SHUTDOWN_FORCED_KILL"] == "1",
        "result": os.environ["WN_I21_BACKEND_SHUTDOWN_RESULT"],
        "abnormal": os.environ["WN_I21_BACKEND_SHUTDOWN_ABNORMAL"] == "1",
    },
    "backend_log_diagnostics": {
        "stream": "combined_stdout_stderr",
        "available": server_log_data is not None,
        "digest": server_log_digest,
        "categories": diagnostic_categories,
        "exception_type": exception_type,
        "asan_error_type": asan_error_type,
        "asan_frames": asan_frames,
        "ubsan_location": ubsan_location,
    },
    "credentials_included": False,
}
path = Path(os.environ["WN_I21_MANIFEST_PATH"])
path.write_text(json.dumps(manifest, indent=2) + "\n")
path.chmod(0o600)
if manifest["backend_shutdown"]["abnormal"]:
    console_diagnostics = dict(diagnostic_categories)
    console_diagnostics["exception_type"] = exception_type
    console_diagnostics["asan_error_type"] = asan_error_type
    console_diagnostics["asan_frames"] = asan_frames
    console_diagnostics["ubsan_location"] = ubsan_location
    print("Backend diagnostic categories: " + json.dumps(
        console_diagnostics, sort_keys=True, separators=(",", ":"),
    ))
PY
}

terminate_registered_child() {
  local pid_file="$1"
  local identity_pattern="$2"
  shift 2
  [[ -f "$pid_file" ]] || return 0
  local child_pid command_line
  read -r child_pid < "$pid_file"
  [[ "$child_pid" =~ ^[0-9]+$ ]] || return 0
  kill -0 "$child_pid" 2>/dev/null || return 0
  command_line="$(ps -p "$child_pid" -o command= 2>/dev/null || true)"
  [[ "$command_line" == *"$identity_pattern"* ]] || return 0
  for expected_arg in "$@"; do
    [[ "$command_line" == *"$expected_arg"* ]] || return 0
  done
  kill -TERM "$child_pid" 2>/dev/null
  for _ in $(seq 1 40); do
    kill -0 "$child_pid" 2>/dev/null || break
    sleep 0.25
  done
  if kill -0 "$child_pid" 2>/dev/null; then kill -KILL "$child_pid" 2>/dev/null; fi
  wait "$child_pid" 2>/dev/null || true
}

bounded_command() {
  local output_path="$1"
  shift
  local command_pid
  "$@" > "$output_path" 2>&1 &
  command_pid=$!
  for _ in $(seq 1 32); do
    if ! kill -0 "$command_pid" 2>/dev/null; then
      wait "$command_pid" 2>/dev/null
      return $?
    fi
    sleep 0.25
  done
  kill -TERM "$command_pid" 2>/dev/null || true
  for _ in $(seq 1 8); do
    kill -0 "$command_pid" 2>/dev/null || break
    sleep 0.25
  done
  if kill -0 "$command_pid" 2>/dev/null; then
    kill -KILL "$command_pid" 2>/dev/null || true
  fi
  wait "$command_pid" 2>/dev/null || true
  return 124
}

append_tracked_descendants() {
  local parent_pid="$1"
  local child_pid
  local children
  children="$(pgrep -P "$parent_pid" 2>/dev/null || true)"
  while IFS= read -r child_pid; do
    [[ "$child_pid" =~ ^[0-9]+$ ]] || continue
    append_tracked_descendants "$child_pid"
    case " $ACTIVE_CHILD_TREE " in
      *" $child_pid "*) ;;
      *) ACTIVE_CHILD_TREE="${ACTIVE_CHILD_TREE:+$ACTIVE_CHILD_TREE }$child_pid" ;;
    esac
  done <<< "$children"
}

tracked_process_alive() {
  local tracked_pid="$1"
  local process_state
  kill -0 "$tracked_pid" 2>/dev/null || return 1
  process_state="$(ps -p "$tracked_pid" -o stat= 2>/dev/null | tr -d '[:space:]')"
  [[ -n "$process_state" && "${process_state:0:1}" != Z ]]
}

stop_active_child() {
  [[ -n "$ACTIVE_CHILD_PID" ]] || return 0
  local root_pid="$ACTIVE_CHILD_PID"
  local tracked_pid alive
  local ACTIVE_CHILD_TREE=""

  append_tracked_descendants "$root_pid"
  ACTIVE_CHILD_TREE="${ACTIVE_CHILD_TREE:+$ACTIVE_CHILD_TREE }$root_pid"
  for tracked_pid in $ACTIVE_CHILD_TREE; do
    kill -TERM "$tracked_pid" 2>/dev/null || true
  done

  for _ in $(seq 1 12); do
    # Include descendants that appeared while TERM was being delivered.
    append_tracked_descendants "$root_pid"
    alive=0
    for tracked_pid in $ACTIVE_CHILD_TREE; do
      if tracked_process_alive "$tracked_pid"; then
        alive=1
        kill -TERM "$tracked_pid" 2>/dev/null || true
      fi
    done
    [[ "$alive" == 1 ]] || break
    sleep 0.25
  done
  for tracked_pid in $ACTIVE_CHILD_TREE; do
    if tracked_process_alive "$tracked_pid"; then
      kill -KILL "$tracked_pid" 2>/dev/null || true
    fi
  done
  wait "$root_pid" 2>/dev/null || true
  ACTIVE_CHILD_PID=""
}

run_tracked() {
  "$@" &
  local child_pid=$!
  local status=0
  ACTIVE_CHILD_PID="$child_pid"
  wait "$child_pid" || status=$?
  ACTIVE_CHILD_PID=""
  return "$status"
}

run_tracked_logged() {
  local log_path="$1"
  shift
  run_tracked bash -c 'set -Eeuo pipefail; log_path=$1; shift; "$@" 2>&1 | tee "$log_path"' \
    _ "$log_path" "$@"
}

handle_signal() {
  local exit_status="$1"
  trap - INT TERM
  stop_active_child
  exit "$exit_status"
}

collect_and_cleanup_owned_backend_containers() {
  local cidfile candidate instance expected_name identity
  local actual_id actual_name actual_run actual_service actual_instance state
  for cidfile in "$RUN_DIR"/linux-runtime/*/backend-container.id; do
    [[ -f "$cidfile" ]] || continue
    candidate="$(tr -d '\r\n' < "$cidfile")"
    [[ "$candidate" =~ ^[0-9a-f]{64}$ ]] || continue
    instance="$(basename "$(dirname "$cidfile")")"
    if [[ "$instance" != primary && "$instance" != secondary &&
          ! "$instance" =~ ^secondary-[0-9a-f]{12}$ ]]; then
      continue
    fi
    expected_name="woniunote-i21-$RUN_ID-backend-$instance"
    identity="$(docker inspect --format \
      '{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|{{index .Config.Labels "org.woniunote.iter21.service"}}|{{index .Config.Labels "org.woniunote.iter21.instance"}}' \
      "$candidate" 2>/dev/null || true)"
    IFS='|' read -r actual_id actual_name actual_run actual_service actual_instance <<< "$identity"
    if [[ "$actual_id" != "$candidate" || "$actual_name" != "/$expected_name" ||
          "$actual_run" != "$RUN_ID" || "$actual_service" != backend ||
          "$actual_instance" != "$instance" ]]; then
      continue
    fi

    local log_path="$RUN_DIR/logs/backend-container-$instance.log"
    bounded_command "$log_path" docker logs "$candidate" || true
    chmod 600 "$log_path" 2>/dev/null || true

    bounded_command /dev/null docker stop --time 5 "$candidate" || true
    identity="$(docker inspect --format \
      '{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|{{index .Config.Labels "org.woniunote.iter21.service"}}|{{index .Config.Labels "org.woniunote.iter21.instance"}}|{{.State.Status}}' \
      "$candidate" 2>/dev/null || true)"
    IFS='|' read -r actual_id actual_name actual_run actual_service actual_instance state <<< "$identity"
    if [[ "$actual_id" == "$candidate" && "$actual_name" == "/$expected_name" &&
          "$actual_run" == "$RUN_ID" && "$actual_service" == backend &&
          "$actual_instance" == "$instance" ]]; then
      if [[ "$state" == running ]]; then
        bounded_command /dev/null docker kill "$candidate" || true
      fi
      identity="$(docker inspect --format \
        '{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|{{index .Config.Labels "org.woniunote.iter21.service"}}|{{index .Config.Labels "org.woniunote.iter21.instance"}}' \
        "$candidate" 2>/dev/null || true)"
      IFS='|' read -r actual_id actual_name actual_run actual_service actual_instance <<< "$identity"
      if [[ "$actual_id" == "$candidate" && "$actual_name" == "/$expected_name" &&
            "$actual_run" == "$RUN_ID" && "$actual_service" == backend &&
            "$actual_instance" == "$instance" ]]; then
        bounded_command /dev/null docker rm -f "$candidate" || true
      fi
    fi
  done
}

collect_and_cleanup_owned_container() {
  local requested_id="$1"
  local expected_name="$2"
  local expected_service="$3"
  local expected_image="$4"
  local candidates candidate identity actual_id actual_name actual_run actual_service
  local state exit_code image_id version_variable image_version log_path
  if [[ -n "$requested_id" ]]; then
    candidates="$requested_id"
  else
    # docker run can create a stopped container and still fail before printing
    # its ID. Recover only an exact name+label match for this generated run.
    candidates="$(docker ps -aq --no-trunc \
      --filter "name=^/${expected_name}$" \
      --filter "label=org.woniunote.iter21.run-id=$RUN_ID" \
      --filter "label=org.woniunote.iter21.service=$expected_service" 2>/dev/null || true)"
  fi
  while IFS= read -r candidate; do
    [[ "$candidate" =~ ^[0-9a-f]{64}$ ]] || continue
    identity="$(docker inspect --format \
      '{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|{{index .Config.Labels "org.woniunote.iter21.service"}}' \
      "$candidate" 2>/dev/null || true)"
    IFS='|' read -r actual_id actual_name actual_run actual_service <<< "$identity"
    if [[ "$actual_id" == "$candidate" && "$actual_name" == "/$expected_name" &&
          "$actual_run" == "$RUN_ID" && "$actual_service" == "$expected_service" ]]; then
      state="$(docker inspect --format '{{.State.Status}}' "$candidate" 2>/dev/null || echo unavailable)"
      exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$candidate" 2>/dev/null || true)"
      [[ "$state" == running ]] && exit_code=""
      image_id="$(docker inspect --format '{{.Image}}' "$candidate" 2>/dev/null || true)"
      case "$expected_service" in
        mysql) version_variable=MYSQL_VERSION ;;
        redis) version_variable=REDIS_VERSION ;;
      esac
      image_version="$(docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
        "$expected_image" 2>/dev/null | sed -n -E "s/^${version_variable}=//p" | head -n 1)"
      log_path="$RUN_DIR/logs/${expected_service}-container.log"
      docker logs "$candidate" > "$log_path" 2>&1 || true
      chmod 600 "$log_path" 2>/dev/null || true
      case "$expected_service" in
        mysql)
          MYSQL_CONTAINER_STATUS="$state"
          MYSQL_CONTAINER_EXIT_CODE="$exit_code"
          MYSQL_IMAGE_ID="$image_id"
          MYSQL_IMAGE_VERSION="$image_version"
          ;;
        redis)
          REDIS_CONTAINER_STATUS="$state"
          REDIS_CONTAINER_EXIT_CODE="$exit_code"
          REDIS_IMAGE_ID="$image_id"
          REDIS_IMAGE_VERSION="$image_version"
          ;;
      esac
      docker rm -f "$actual_id" >/dev/null 2>&1 || true
    fi
  done <<< "$candidates"
}

collect_and_cleanup_owned_volume() {
  local requested_name="$1"
  local expected_name="$2"
  local expected_service="$3"
  local candidates candidate identity actual_name actual_run actual_service driver
  if [[ -n "$requested_name" ]]; then
    candidates="$requested_name"
  else
    candidates="$(docker volume ls -q \
      --filter "name=^${expected_name}$" \
      --filter "label=org.woniunote.iter21.run-id=$RUN_ID" \
      --filter "label=org.woniunote.iter21.service=$expected_service" 2>/dev/null || true)"
  fi
  while IFS= read -r candidate; do
    [[ "$candidate" == "$expected_name" ]] || continue
    identity="$(docker volume inspect --format \
      '{{.Name}}|{{.Driver}}|{{index .Labels "org.woniunote.iter21.run-id"}}|{{index .Labels "org.woniunote.iter21.service"}}' \
      "$candidate" 2>/dev/null || true)"
    IFS='|' read -r actual_name driver actual_run actual_service <<< "$identity"
    if [[ "$actual_name" == "$expected_name" && "$actual_run" == "$RUN_ID" &&
          "$actual_service" == "$expected_service" ]]; then
      MYSQL_VOLUME_DRIVER="$driver"
      if docker volume rm "$candidate" >/dev/null 2>&1; then
        MYSQL_VOLUME_STATUS=removed
      else
        MYSQL_VOLUME_STATUS=cleanup_failed
        echo "WARNING: could not remove run-owned MySQL volume $candidate after verifying its labels." >&2
      fi
    fi
  done <<< "$candidates"
}

stop_backend_process() {
  local child_pid="$1"
  local process_state wait_status
  BACKEND_SHUTDOWN_TERM_SENT=0
  BACKEND_SHUTDOWN_WAIT_EXIT_CODE=""
  BACKEND_SHUTDOWN_FORCED_KILL=0
  BACKEND_SHUTDOWN_RESULT="not_started"
  BACKEND_SHUTDOWN_ABNORMAL=0
  [[ "$child_pid" =~ ^[0-9]+$ ]] || return 0

  process_state="$(ps -p "$child_pid" -o stat= 2>/dev/null | tr -d '[:space:]')"
  if [[ -n "$process_state" && "${process_state:0:1}" != Z ]]; then
    if kill -TERM "$child_pid" 2>/dev/null; then
      BACKEND_SHUTDOWN_TERM_SENT=1
    fi
    for _ in $(seq 1 40); do
      process_state="$(ps -p "$child_pid" -o stat= 2>/dev/null | tr -d '[:space:]')"
      [[ -n "$process_state" && "${process_state:0:1}" != Z ]] || break
      sleep 0.25
    done
    process_state="$(ps -p "$child_pid" -o stat= 2>/dev/null | tr -d '[:space:]')"
    if [[ -n "$process_state" && "${process_state:0:1}" != Z ]] &&
        kill -KILL "$child_pid" 2>/dev/null; then
      BACKEND_SHUTDOWN_FORCED_KILL=1
    fi
  fi

  if wait "$child_pid" 2>/dev/null; then
    wait_status=0
  else
    wait_status=$?
  fi
  BACKEND_SHUTDOWN_WAIT_EXIT_CODE="$wait_status"

  if [[ "$BACKEND_SHUTDOWN_FORCED_KILL" == 1 ]]; then
    BACKEND_SHUTDOWN_RESULT="forced_kill"
    BACKEND_SHUTDOWN_ABNORMAL=1
  elif [[ "$BACKEND_SHUTDOWN_TERM_SENT" == 1 && "$wait_status" == 0 ]]; then
    BACKEND_SHUTDOWN_RESULT="term_exit_0"
  elif [[ "$BACKEND_SHUTDOWN_TERM_SENT" == 1 && "$wait_status" == 143 ]]; then
    BACKEND_SHUTDOWN_RESULT="term_exit_143"
  elif [[ "$BACKEND_SHUTDOWN_TERM_SENT" == 0 && "$wait_status" == 0 ]]; then
    BACKEND_SHUTDOWN_RESULT="already_exited_0"
  else
    BACKEND_SHUTDOWN_RESULT="unexpected_exit"
    BACKEND_SHUTDOWN_ABNORMAL=1
  fi
  echo "Backend shutdown: result=$BACKEND_SHUTDOWN_RESULT term_sent=$BACKEND_SHUTDOWN_TERM_SENT wait_exit_code=$BACKEND_SHUTDOWN_WAIT_EXIT_CODE forced_kill=$BACKEND_SHUTDOWN_FORCED_KILL" >&2
}

mark_backend_shutdown_failure() {
  if [[ "$status" == 0 && "$RUN_COMPLETED" == 1 && "$BACKEND_SHUTDOWN_ABNORMAL" == 1 ]]; then
    echo "ERROR: backend exited abnormally during a completed integration run (result=$BACKEND_SHUTDOWN_RESULT, wait_exit_code=$BACKEND_SHUTDOWN_WAIT_EXIT_CODE)." >&2
    status=1
  fi
}

cleanup() {
  status=$?
  trap - EXIT INT TERM
  set +e
  if [[ "$status" == 0 && "$RUN_COMPLETED" != 1 ]]; then
    echo "ERROR: runner exited before all required phases completed; not a passing run." >&2
    status=2
  fi
  if [[ "$KEEP_SERVICES" == 1 && "$SERVICES_READY" == 1 && "$RUN_COMPLETED" == 1 && "$status" == 0 ]]; then
    BACKEND_SHUTDOWN_RESULT="services_kept"
    SERVER_LOG_INDEX_REFERENCE=""
    chmod -R go-rwx "$RUN_DIR"
    export WN_I21_RUNTIME_RETAINED=1 WN_I21_ARTIFACT_DIR=""
    write_manifest
    echo "RUN_MANIFEST=$RUN_DIR/run.json"
    echo "RUN_ID=$RUN_ID BACKEND_URL=$BASE_URL FRONTEND_URL=${FRONTEND_URL:-none}"
    echo "Owned containers: $MYSQL_NAME ($MYSQL_CONTAINER_ID), $REDIS_NAME ($REDIS_CONTAINER_ID)"
    echo "Backend PID: $SERVER_PID; manifest excludes credentials."
    exit 0
  fi

  if [[ -n "$SERVER_PID" ]]; then
    stop_backend_process "$SERVER_PID"
    mark_backend_shutdown_failure
  fi
  terminate_registered_child "$RUN_DIR/fault-proxy-runtime/backend.pid" "$BACKEND_BIN" \
    "$RUN_DIR/fault-proxy-runtime/config/config.json"
  terminate_registered_child "$RUN_DIR/fault-proxy-runtime/proxy.pid" \
    "$SCRIPT_DIR/iter21_fault_proxy.py" "$RUN_DIR/fault-proxy-runtime"
  collect_and_cleanup_owned_backend_containers
  collect_and_cleanup_owned_container "$MYSQL_CONTAINER_ID" "$MYSQL_NAME" mysql "$MYSQL_IMAGE"
  collect_and_cleanup_owned_volume "$MYSQL_VOLUME_NAME" "$MYSQL_VOLUME_NAME" mysql
  collect_and_cleanup_owned_container "$REDIS_CONTAINER_ID" "$REDIS_NAME" redis "$REDIS_IMAGE"
  find "$RUN_DIR" -type f \( -name 'config.json' -o -name 'config.integration.json' \) -delete 2>/dev/null
  rm -rf "$RUN_DIR/uploads"
  rm -rf "$BACKEND_CWD"
  export WN_I21_RUNTIME_RETAINED=0 WN_I21_ARTIFACT_DIR="$RESULT_DIR"
  SERVER_LOG_INDEX_REFERENCE=""
  if [[ -f "$SERVER_LOG" && ! -e "$RESULT_DIR" && ! -L "$RESULT_DIR" ]]; then
    SERVER_LOG_INDEX_REFERENCE="log-index.json"
  fi
  if [[ "$status" != 0 ]]; then WN_I21_RUNTIME_RETAINED=1; export WN_I21_RUNTIME_RETAINED; fi
  write_manifest
  mkdir -p "$RESULT_ROOT"
  mkdir -m 700 "$RESULT_DIR" || { echo "ERROR: refusing to reuse evidence directory $RESULT_DIR" >&2; exit 2; }
  cp "$RUN_DIR/run.json" "$RESULT_DIR/run.json"
  if [[ -f "$RUN_DIR/evidence/pytest.xml" ]]; then
    export WN_I21_JUNIT_PATH="$RUN_DIR/evidence/pytest.xml"
    export WN_I21_SUMMARY_PATH="$RESULT_DIR/test-summary.json"
    "${PYTHON_RUN[@]}" - <<'PY'
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

report = {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "cases": []}
try:
    root = ET.parse(os.environ["WN_I21_JUNIT_PATH"]).getroot()
    for case in root.iter("testcase"):
        report["tests"] += 1
        if case.find("failure") is not None or case.find("error") is not None:
            result = "failed"
            report["failed"] += 1
        elif case.find("skipped") is not None:
            result = "skipped"
            report["skipped"] += 1
        else:
            result = "passed"
            report["passed"] += 1
        report["cases"].append({
            "class": case.get("classname", ""),
            "name": case.get("name", ""),
            "result": result,
        })
except (OSError, ET.ParseError):
    report["summary_unavailable"] = True
report["failure_details"] = "restricted to the per-run runtime"
output = Path(os.environ["WN_I21_SUMMARY_PATH"])
output.write_text(json.dumps(report, indent=2) + "\n")
output.chmod(0o600)
PY
  fi
  for summary_file in math-training-migration-summary.json comment-vote-migration-summary.json \
      comment-vote-migration-live-summary.json article-thumbnail-migration-summary.json \
      real-browser-summary.json; do
    if [[ -f "$RUN_DIR/evidence/$summary_file" ]]; then
      cp "$RUN_DIR/evidence/$summary_file" "$RESULT_DIR/$summary_file"
      chmod 600 "$RESULT_DIR/$summary_file"
    fi
  done
  for transport_evidence in "$RUN_DIR"/evidence/iter21-transport-*.json; do
    if [[ -f "$transport_evidence" ]]; then
      cp "$transport_evidence" "$RESULT_DIR/"
      chmod 600 "$RESULT_DIR/$(basename "$transport_evidence")"
    fi
  done
  if ! "${PYTHON_RUN[@]}" "$SCRIPT_DIR/sanitize_backend_runtime.py" \
      "$RUN_DIR/evidence" "$RESULT_DIR" "$RUN_ID"; then
    echo "ERROR: could not safely export Linux backend runtime metadata; run is incomplete." >&2
    status=2
    WN_I21_RUNTIME_RETAINED=1
    export WN_I21_RUNTIME_RETAINED
    write_manifest
    cp "$RUN_DIR/run.json" "$RESULT_DIR/run.json"
  fi
  if [[ -f "$SERVER_LOG" ]]; then
    export WN_I21_SERVER_LOG="$SERVER_LOG" WN_I21_LOG_INDEX="$RESULT_DIR/log-index.json"
    "${PYTHON_RUN[@]}" - <<'PY'
import hashlib
import json
import os
from pathlib import Path
log = Path(os.environ["WN_I21_SERVER_LOG"])
entry = {"file": log.name, "bytes": log.stat().st_size,
         "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
         "contents_included": False}
Path(os.environ["WN_I21_LOG_INDEX"]).write_text(json.dumps([entry], indent=2) + "\n")
PY
  fi
  chmod -R go-rwx "$RUN_DIR" "$RESULT_DIR"
  if [[ "$status" == 0 ]]; then
    echo "RUN_ID=$RUN_ID completed; owned backend, containers and runtime were cleaned."
    echo "Sanitized test summaries and content-free metadata: $RESULT_DIR"
    rm -rf "$RUN_DIR"
  else
    echo "RUN_ID=$RUN_ID failed; owned services and uploads were cleaned."
    echo "Restricted diagnostics retained at $RUN_DIR (mode 700); sanitized summaries: $RESULT_DIR."
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM

if [[ -z "$TEST_PORT" ]]; then TEST_PORT="$(choose_port)"; fi
if [[ ! "$TEST_PORT" =~ ^[0-9]{1,5}$ ]] || (( TEST_PORT < 1024 || TEST_PORT > 65535 )); then
  echo "ERROR: test backend port must be an unprivileged TCP port." >&2
  exit 2
fi
if [[ "$TEST_PORT" == 5173 || "$TEST_PORT" == 8888 || "$TEST_PORT" == 3306 || "$TEST_PORT" == 6379 ]]; then
  echo "ERROR: backend test port conflicts with a development/standard service port." >&2
  exit 2
fi
if ! check_port_free "$TEST_PORT"; then
  echo "ERROR: test backend port $TEST_PORT is occupied; no business writes were made." >&2
  exit 2
fi
if [[ "$REAL_E2E" == 1 ]]; then
  if [[ -z "$FRONTEND_PORT" ]]; then FRONTEND_PORT="$(choose_port)"; fi
  if [[ ! "$FRONTEND_PORT" =~ ^[0-9]{1,5}$ ]] || (( FRONTEND_PORT < 1024 || FRONTEND_PORT > 65535 )); then
    echo "ERROR: real E2E frontend port must be an unprivileged TCP port." >&2
    exit 2
  fi
  if [[ "$FRONTEND_PORT" == "$TEST_PORT" || "$FRONTEND_PORT" == 5173 || "$FRONTEND_PORT" == 8888 ||
        "$FRONTEND_PORT" == 3306 || "$FRONTEND_PORT" == 6379 ]]; then
    echo "ERROR: frontend test port conflicts with a test or development port." >&2
    exit 2
  fi
  if ! check_port_free "$FRONTEND_PORT"; then
    echo "ERROR: frontend test port $FRONTEND_PORT is occupied; no business writes were made." >&2
    exit 2
  fi
  if [[ -n "${WONIUNOTE_API_PROXY_TARGET-}" && "$WONIUNOTE_API_PROXY_TARGET" =~ :5173/?$ ]]; then
    echo "ERROR: real E2E refuses the development backend proxy on port 5173." >&2
    exit 2
  fi
fi

MYSQL_PORT="$(choose_distinct_port "$TEST_PORT" "$FRONTEND_PORT" 5173 8888 3306 6379)" || {
  echo "ERROR: could not select a free MySQL loopback port distinct from HTTP/frontend ports." >&2
  exit 2
}
REDIS_PORT="$(choose_distinct_port "$TEST_PORT" "$FRONTEND_PORT" "$MYSQL_PORT" 5173 8888 3306 6379)" || {
  echo "ERROR: could not select a free Redis loopback port distinct from other listeners." >&2
  exit 2
}
for service_port in "$TEST_PORT" "$MYSQL_PORT" "$REDIS_PORT"; do
  if [[ -n "$FRONTEND_PORT" && "$service_port" == "$FRONTEND_PORT" ]]; then
    echo "ERROR: selected HTTP, frontend, MySQL, and Redis ports must all be distinct." >&2
    exit 2
  fi
  if ! check_port_free "$service_port"; then
    echo "ERROR: selected service port $service_port is occupied; no business writes were made." >&2
    exit 2
  fi
done
BASE_URL="http://127.0.0.1:$TEST_PORT"
if [[ "$REAL_E2E" == 1 ]]; then FRONTEND_URL="http://127.0.0.1:$FRONTEND_PORT"; fi

echo "==> Iteration 21 isolated backend integration"
echo "    run id: $RUN_ID"
echo "    scenario: $SCENARIO (rate limit: $RATE_LIMIT/minute)"
echo "    runtime: $RUN_DIR"
echo "    backend: $BASE_URL"
echo "    services: unique Docker containers; no host MySQL/Redis connections"

MYSQL_VOLUME_CREATED="$(docker volume create \
  --label "org.woniunote.iter21.run-id=$RUN_ID" \
  --label org.woniunote.iter21.service=mysql \
  "$MYSQL_VOLUME_NAME")"
[[ "$MYSQL_VOLUME_CREATED" == "$MYSQL_VOLUME_NAME" ]] || {
  echo "ERROR: Docker did not create the expected run-owned MySQL volume." >&2
  exit 2
}
MYSQL_VOLUME_STATUS=created
MYSQL_VOLUME_IDENTITY="$(docker volume inspect --format \
  '{{.Name}}|{{.Driver}}|{{index .Labels "org.woniunote.iter21.run-id"}}|{{index .Labels "org.woniunote.iter21.service"}}' \
  "$MYSQL_VOLUME_NAME")"
IFS='|' read -r volume_name MYSQL_VOLUME_DRIVER volume_run_id volume_service <<< "$MYSQL_VOLUME_IDENTITY"
if [[ "$volume_name" != "$MYSQL_VOLUME_NAME" || "$volume_run_id" != "$RUN_ID" ||
      "$volume_service" != mysql || -z "$MYSQL_VOLUME_DRIVER" ]]; then
  echo "ERROR: created MySQL volume identity did not match this run." >&2
  exit 2
fi

MYSQL_CONTAINER_ID="$(docker run --detach \
  --name "$MYSQL_NAME" \
  --label "org.woniunote.iter21.run-id=$RUN_ID" \
  --label "org.woniunote.iter21.service=mysql" \
  --publish "127.0.0.1:$MYSQL_PORT:3306" \
  --mount "type=volume,source=$MYSQL_VOLUME_NAME,target=/var/lib/mysql" \
  --env "MYSQL_ROOT_PASSWORD=$DB_PASSWORD" \
  --env MYSQL_ROOT_HOST=% \
  "$MYSQL_IMAGE" \
  --default-authentication-plugin=mysql_native_password \
  --bind-address=0.0.0.0 \
  --ssl=OFF)"
MYSQL_MAPPING="$(docker port "$MYSQL_CONTAINER_ID" 3306/tcp | tr -d '\r')"
[[ "$MYSQL_MAPPING" == "127.0.0.1:$MYSQL_PORT" ]] || {
  echo "ERROR: owned MySQL mapping differs from the preselected loopback endpoint; no schema or business writes were made." >&2
  exit 2
}

REDIS_CONTAINER_ID="$(docker run --detach \
  --name "$REDIS_NAME" \
  --label "org.woniunote.iter21.run-id=$RUN_ID" \
  --label "org.woniunote.iter21.service=redis" \
  --publish "127.0.0.1:$REDIS_PORT:6379" \
  --tmpfs /data:rw,noexec,nosuid,size=64m \
  "$REDIS_IMAGE" \
  redis-server --appendonly no --save "" --requirepass "$REDIS_PASSWORD" --bind 0.0.0.0)"
REDIS_MAPPING="$(docker port "$REDIS_CONTAINER_ID" 6379/tcp | tr -d '\r')"
[[ "$REDIS_MAPPING" == "127.0.0.1:$REDIS_PORT" ]] || {
  echo "ERROR: owned Redis mapping differs from the preselected loopback endpoint; no schema or business writes were made." >&2
  exit 2
}

# Make all verified owned endpoints available before the backend launcher starts.
export WN_I21_RUN_ID="$RUN_ID" WN_I21_RUN_DIR="$RUN_DIR"
export WN_I21_MYSQL_NAME="$MYSQL_NAME" WN_I21_REDIS_NAME="$REDIS_NAME"
export WN_I21_MYSQL_ID="$MYSQL_CONTAINER_ID" WN_I21_REDIS_ID="$REDIS_CONTAINER_ID"
export WN_I21_DB_HOST=127.0.0.1 WN_I21_DB_PORT="$MYSQL_PORT"
export WN_I21_DB_NAME="$DB_NAME" WN_I21_DB_USER="$DB_USER" WN_I21_DB_PASSWORD="$DB_PASSWORD"
export WN_I21_REDIS_HOST=127.0.0.1 WN_I21_REDIS_PORT="$REDIS_PORT"
export WN_I21_REDIS_PASSWORD="$REDIS_PASSWORD" WN_I21_TEST_PORT="$TEST_PORT"
export WONIUNOTE_TEST_RUN_ID="$RUN_ID" WONIUNOTE_TEST_RUNTIME_DIR="$RUN_DIR"
export WONIUNOTE_TEST_DB_HOST=127.0.0.1 WONIUNOTE_TEST_DB_PORT="$MYSQL_PORT"
export WONIUNOTE_TEST_DB_NAME="$DB_NAME" WONIUNOTE_TEST_DB_USER="$DB_USER"
export WONIUNOTE_TEST_DB_PASSWORD="$DB_PASSWORD"
export WONIUNOTE_TEST_REDIS_HOST=127.0.0.1 WONIUNOTE_TEST_REDIS_PORT="$REDIS_PORT"
export WONIUNOTE_TEST_REDIS_PASSWORD="$REDIS_PASSWORD"
export WONIUNOTE_TEST_MYSQL_CONTAINER="$MYSQL_CONTAINER_ID"
export WONIUNOTE_TEST_MYSQL_CONTAINER_ID="$MYSQL_CONTAINER_ID"
export WONIUNOTE_TEST_REDIS_CONTAINER="$REDIS_CONTAINER_ID"
export WONIUNOTE_TEST_REDIS_CONTAINER_ID="$REDIS_CONTAINER_ID"

echo "==> Waiting for owned MySQL and Redis"
MYSQL_READY=0
REDIS_READY=0
for attempt in $(seq 1 60); do
  mysql_state="$(docker inspect --format '{{.State.Status}}' "$MYSQL_CONTAINER_ID" 2>/dev/null || echo unavailable)"
  if [[ "$mysql_state" != running ]]; then
    mysql_exit="$(docker inspect --format '{{.State.ExitCode}}' "$MYSQL_CONTAINER_ID" 2>/dev/null || echo unknown)"
    echo "ERROR: owned MySQL exited during startup (state=$mysql_state, exit=$mysql_exit); raw logs stay in the restricted run directory." >&2
    exit 2
  fi
  redis_state="$(docker inspect --format '{{.State.Status}}' "$REDIS_CONTAINER_ID" 2>/dev/null || echo unavailable)"
  if [[ "$redis_state" != running ]]; then
    redis_exit="$(docker inspect --format '{{.State.ExitCode}}' "$REDIS_CONTAINER_ID" 2>/dev/null || echo unknown)"
    echo "ERROR: owned Redis exited during startup (state=$redis_state, exit=$redis_exit); raw logs stay in the restricted run directory." >&2
    exit 2
  fi
  if [[ "$MYSQL_READY" == 0 ]] && docker exec -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" \
    mysqladmin ping --silent -h 127.0.0.1 -uroot >/dev/null 2>&1; then
    MYSQL_READY=1
  fi
  if [[ "$REDIS_READY" == 0 ]] && docker exec -e "REDISCLI_AUTH=$REDIS_PASSWORD" "$REDIS_CONTAINER_ID" \
    redis-cli ping 2>/dev/null | rg -q '^PONG$'; then
    REDIS_READY=1
  fi
  if [[ "$MYSQL_READY" == 1 && "$REDIS_READY" == 1 ]]; then break; fi
  sleep 1
done
if [[ "$MYSQL_READY" != 1 || "$REDIS_READY" != 1 ]]; then
  echo "ERROR: owned services failed protocol checks; schema was not created." >&2
  exit 2
fi
MYSQL_TLS_STATUS="$(docker exec -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" \
  mysql -uroot -Nse 'SELECT @@GLOBAL.have_ssl')"
if [[ "$MYSQL_TLS_STATUS" != DISABLED ]]; then
  echo "ERROR: owned MySQL must report @@GLOBAL.have_ssl=DISABLED for byte-level COMMIT acknowledgement testing; no schema was created." >&2
  exit 2
fi
export WN_I21_MYSQL_TLS_STATUS="$MYSQL_TLS_STATUS"
echo "    owned MySQL TLS: disabled for byte-level transport-fault tests only (server readback: $MYSQL_TLS_STATUS)"
MYSQL_CONTAINER_STATUS=running
REDIS_CONTAINER_STATUS=running
MYSQL_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$MYSQL_CONTAINER_ID")"
REDIS_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$REDIS_CONTAINER_ID")"
MYSQL_IMAGE_VERSION="$(docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
  "$MYSQL_IMAGE" | sed -n -E 's/^MYSQL_VERSION=//p' | head -n 1)"
REDIS_IMAGE_VERSION="$(docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
  "$REDIS_IMAGE" | sed -n -E 's/^REDIS_VERSION=//p' | head -n 1)"

echo "==> Creating unique schema and loading repository SQL"
MYSQL_CLIENT_CHARSET="$(docker exec -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" \
  mysql --default-character-set=utf8mb4 -uroot -Nse 'SELECT @@character_set_client')"
if [[ "$MYSQL_CLIENT_CHARSET" != utf8mb4 ]]; then
  echo "ERROR: isolated MySQL client charset check failed before schema creation." >&2
  exit 2
fi
echo "    isolated MySQL client charset: $MYSQL_CLIENT_CHARSET"
docker exec -i -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" mysql \
  --default-character-set=utf8mb4 -uroot -e \
  "CREATE DATABASE \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
for schema_file in "$REPO_ROOT"/scripts/sql/*.sql; do
  [[ -f "$schema_file" ]] || continue
  docker exec -i -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" mysql \
    --default-character-set=utf8mb4 -uroot "$DB_NAME" < "$schema_file"
done

export WN_I21_TEMPLATE="$SCRIPT_DIR/config.integration.template.json"
export WN_I21_CONFIG="$CONFIG_OUT" WN_I21_RUN_DIR="$RUN_DIR" WN_I21_RUN_ID="$RUN_ID"
export WN_I21_DB_HOST=127.0.0.1 WN_I21_DB_PORT="$MYSQL_PORT"
export WN_I21_DB_NAME="$DB_NAME" WN_I21_DB_USER="$DB_USER" WN_I21_DB_PASSWORD="$DB_PASSWORD"
export WN_I21_REDIS_HOST=127.0.0.1 WN_I21_REDIS_PORT="$REDIS_PORT"
export WN_I21_REDIS_PASSWORD="$REDIS_PASSWORD" WN_I21_TEST_PORT="$TEST_PORT"
export WN_I21_RATE_LIMIT="$RATE_LIMIT" WN_I21_FRONTEND_ORIGIN="$FRONTEND_URL"
"${PYTHON_RUN[@]}" - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["WN_I21_TEMPLATE"]).read_text())
config["listeners"] = [{"address": "127.0.0.1", "port": int(os.environ["WN_I21_TEST_PORT"]), "https": False}]
app = config.setdefault("app", {})
run_dir = Path(os.environ["WN_I21_RUN_DIR"]).resolve()
document_root = run_dir / "uploads"
upload_root = document_root / "uploads"
app["document_root"] = str(document_root)
app["upload_path"] = str(upload_root)
assert Path(app["document_root"]) == run_dir / "uploads"
assert Path(app["upload_path"]).parent == Path(app["document_root"])
app["log"] = {
    "log_path": str(run_dir / "logs"),
    "logfile_base_name": "backend",
    "log_level": "WARN",
}
db = config["db_clients"][0]
db.update({
    "host": os.environ["WN_I21_DB_HOST"],
    "port": int(os.environ["WN_I21_DB_PORT"]),
    "dbname": os.environ["WN_I21_DB_NAME"],
    "user": os.environ["WN_I21_DB_USER"],
    "passwd": os.environ["WN_I21_DB_PASSWORD"],
    "number_of_connections": 4,
    "timeout": 5.0,
})
redis = config["redis_clients"][0]
redis.update({
    "host": os.environ["WN_I21_REDIS_HOST"],
    "port": int(os.environ["WN_I21_REDIS_PORT"]),
    "passwd": os.environ["WN_I21_REDIS_PASSWORD"],
    "db": 0,
    "number_of_connections": 2,
    "timeout": 5.0,
})
custom = config["custom_config"]
custom.update({
    "app_name": "WoniuNote-Iteration21-Test",
    "app_mode": "test",
    "jwt_secret": "iteration21-test-" + os.environ["WN_I21_RUN_ID"] + "-local-only",
    "rate_limit_per_minute": int(os.environ["WN_I21_RATE_LIMIT"]),
    "rate_limit_fail_closed": True,
    "test_run_id": os.environ["WN_I21_RUN_ID"],
    "cors_origins": [os.environ["WN_I21_FRONTEND_ORIGIN"]] if os.environ["WN_I21_FRONTEND_ORIGIN"] else [],
})
output = Path(os.environ["WN_I21_CONFIG"])
output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
output.chmod(0o600)
rendered = json.loads(output.read_text())
assert Path(rendered["app"]["document_root"]) == run_dir / "uploads"
assert Path(rendered["app"]["upload_path"]) == run_dir / "uploads" / "uploads"
assert Path(rendered["app"]["upload_path"]).parent == Path(rendered["app"]["document_root"])
assert rendered["db_clients"][0]["passwd"] == os.environ["WN_I21_DB_PASSWORD"]
assert rendered["redis_clients"][0]["passwd"] == os.environ["WN_I21_REDIS_PASSWORD"]
PY

echo "==> Starting backend in the owned runtime directory"
(
  cd "$BACKEND_CWD"
  export WONIUNOTE_ENV=test
  export WONIUNOTE_TEST_RUN_ID="$RUN_ID"
  # vcpkg's MariaDB Connector/C build requires verified TLS by default. The
  # isolated MySQL server was read back as TLS-disabled above, so allow this
  # owned backend process to fall back to plaintext on the run-owned loopback
  # endpoint. This does not affect the caller, product config, or formal runs.
  export MARIADB_TLS_DISABLE_PEER_VERIFICATION=1
  exec "$BACKEND_BIN" "$CONFIG_OUT" >"$SERVER_LOG" 2>&1
) &
SERVER_PID=$!

echo "==> Waiting for backend and test-only challenge"
BACKEND_READY=0
for attempt in $(seq 1 60); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then break; fi
  if curl --silent --show-error --fail --max-time 1 "$BASE_URL/health" >/dev/null 2>&1; then
    BACKEND_READY=1
    break
  fi
  sleep 1
done
if [[ "$BACKEND_READY" != 1 ]]; then
  echo "ERROR: isolated backend did not become healthy; restricted log: $SERVER_LOG" >&2
  exit 2
fi

CHALLENGE_PROBE="$RUN_DIR/challenge-probe.json"
CHALLENGE_STATUS="$(curl --silent --show-error --max-time 2 \
  -H "X-Woniunote-Test-Run: $RUN_ID" \
  -H 'Content-Type: application/json' -d '{}' \
  -o "$CHALLENGE_PROBE" -w '%{http_code}' \
  "$BASE_URL/api/captcha/test/challenge" || true)"
if [[ "$CHALLENGE_STATUS" != 200 ]] || ! "${PYTHON_RUN[@]}" - "$CHALLENGE_PROBE" <<'PY'
import json
import sys
from pathlib import Path
try:
    body = json.loads(Path(sys.argv[1]).read_text())
    data = body.get("data") or {}
    ok = bool(data.get("captcha_id")) and bool(data.get("captcha_code"))
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
then
  rm -f "$CHALLENGE_PROBE"
  echo "ERROR: challenge test hook unavailable or malformed; no business tests ran." >&2
  echo "       Build separately with WONIUNOTE_ENABLE_TEST_CHALLENGE=ON." >&2
  exit 2
fi
rm -f "$CHALLENGE_PROBE"
if [[ "$KEEP_SERVICES" != 1 ]]; then
  rm -f "$CONFIG_OUT"
fi
SERVICES_READY=1

AUTH_PROBE="$RUN_DIR/auth-transaction-probe.json"
AUTH_PROBE_STATUS="$(curl --silent --show-error --max-time 5 \
  -H "X-Woniunote-Test-Run: $RUN_ID" \
  -H 'Content-Type: application/json' -d '{}' \
  -o "$AUTH_PROBE" -w '%{http_code}' \
  "$BASE_URL/api/auth/test/empty-transaction" || true)"
if [[ "$AUTH_PROBE_STATUS" != 200 ]] || ! "${PYTHON_RUN[@]}" - "$AUTH_PROBE" <<'PY'
import json
import sys
from pathlib import Path
try:
    body = json.loads(Path(sys.argv[1]).read_text())
    ok = body.get("code") == 200
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
then
  chmod 600 "$AUTH_PROBE" 2>/dev/null || true
  echo "ERROR: auth transaction test hook unavailable (HTTP $AUTH_PROBE_STATUS); response retained only in the mode-700 run directory: $AUTH_PROBE." >&2
  echo "       Build separately with WONIUNOTE_ENABLE_TEST_AUTH_FAULTS=ON." >&2
  exit 2
fi
rm -f "$AUTH_PROBE"

export WONIUNOTE_TEST_BASE_URL="$BASE_URL"
export WONIUNOTE_TEST_STRICT="$STRICT" WONIUNOTE_TEST_RATE_LIMIT="$RATE_LIMIT"
export WONIUNOTE_TEST_SCENARIO="$SCENARIO"
export WONIUNOTE_TEST_RUN_ID="$RUN_ID" WONIUNOTE_TEST_EVIDENCE_DIR="$RUN_DIR/evidence"
export WONIUNOTE_TEST_DB_HOST=127.0.0.1 WONIUNOTE_TEST_DB_PORT="$MYSQL_PORT"
export WONIUNOTE_TEST_DB_NAME="$DB_NAME" WONIUNOTE_TEST_DB_USER="$DB_USER"
export WONIUNOTE_TEST_DB_PASSWORD="$DB_PASSWORD"
export WONIUNOTE_TEST_REDIS_HOST=127.0.0.1 WONIUNOTE_TEST_REDIS_PORT="$REDIS_PORT"
export WONIUNOTE_TEST_REDIS_PASSWORD="$REDIS_PASSWORD"
export WONIUNOTE_TEST_REDIS_CONTAINER="$REDIS_CONTAINER_ID"
export WONIUNOTE_TEST_REDIS_CONTAINER_ID="$REDIS_CONTAINER_ID"
export WONIUNOTE_TEST_MYSQL_CONTAINER="$MYSQL_CONTAINER_ID"
export WONIUNOTE_TEST_MYSQL_CONTAINER_ID="$MYSQL_CONTAINER_ID"
export WN_I21_MYSQL_NAME="$MYSQL_NAME" WN_I21_REDIS_NAME="$REDIS_NAME"
export WN_I21_MYSQL_ID="$MYSQL_CONTAINER_ID" WN_I21_REDIS_ID="$REDIS_CONTAINER_ID"
export WONIUNOTE_TEST_BACKEND_BIN="$BACKEND_BIN"
export WONIUNOTE_TEST_CONFIG_TEMPLATE="$SCRIPT_DIR/config.integration.template.json"
export WONIUNOTE_TEST_RUNTIME_DIR="$RUN_DIR"
echo "==> Running strict HTTP integration tests"
if [[ -n "${PYTEST_CMD-}" ]]; then
  read -r -a PYTEST_ARGS <<< "$PYTEST_CMD"
  JUNIT_ARGS=(--junitxml "$RUN_DIR/evidence/pytest.xml")
  if [[ "$SCENARIO" == rate-limit ]]; then
    run_tracked env MARIADB_TLS_DISABLE_PEER_VERIFICATION=1 "${PYTEST_ARGS[@]}" \
      -c "$SCRIPT_DIR/pytest.ini" "${JUNIT_ARGS[@]}" "$SCRIPT_DIR/test_z_rate_limit.py"
  else
    run_tracked env MARIADB_TLS_DISABLE_PEER_VERIFICATION=1 "${PYTEST_ARGS[@]}" \
      -c "$SCRIPT_DIR/pytest.ini" "${JUNIT_ARGS[@]}" "$SCRIPT_DIR" \
      --ignore="$SCRIPT_DIR/test_z_rate_limit.py"
  fi
else
  if [[ "$SCENARIO" == rate-limit ]]; then
    run_tracked env MARIADB_TLS_DISABLE_PEER_VERIFICATION=1 "${PYTHON_RUN[@]}" \
      -m pytest -c "$SCRIPT_DIR/pytest.ini" --junitxml "$RUN_DIR/evidence/pytest.xml" \
      "$SCRIPT_DIR/test_z_rate_limit.py"
  else
    run_tracked env MARIADB_TLS_DISABLE_PEER_VERIFICATION=1 "${PYTHON_RUN[@]}" \
      -m pytest -c "$SCRIPT_DIR/pytest.ini" --junitxml "$RUN_DIR/evidence/pytest.xml" \
      "$SCRIPT_DIR" --ignore="$SCRIPT_DIR/test_z_rate_limit.py"
  fi
fi

if [[ "$SCENARIO" == functional ]]; then
  echo "==> Running math migration checks against run-owned disposable schemas"
  run_tracked_logged "$RUN_DIR/evidence/math-training-migration.log" \
    bash "$REPO_ROOT/scripts/tests/test_math_training_migration.sh"
  write_phase_summary math-training-migration-summary.json math-answer-column-migration

  echo "==> Running comment-vote migration unit tests"
  run_tracked_logged "$RUN_DIR/evidence/comment-vote-migration-unit.log" \
    bash -c 'cd "$1"; shift; exec "$@"' _ "$REPO_ROOT" \
    "${PYTHON_RUN[@]}" -m unittest scripts.tests.test_migrate_comment_votes
  write_phase_summary comment-vote-migration-summary.json comment-vote-migration-unit

  echo "==> Running comment-vote migration live checks against the run-owned MySQL container"
  run_tracked_logged "$RUN_DIR/evidence/comment-vote-migration-live.log" \
    bash -c 'cd "$1"; export PYTHONPATH="$2${PYTHONPATH:+:$PYTHONPATH}"; shift 2; exec "$@"' \
    _ "$REPO_ROOT" "$SCRIPT_DIR" "${PYTHON_RUN[@]}" \
    "$REPO_ROOT/scripts/tests/iter21_comment_migration_live.py"
  write_phase_summary comment-vote-migration-live-summary.json comment-vote-migration-live

  echo "==> Running article-thumbnail migration checks against the run-owned MySQL container"
  run_tracked_logged "$RUN_DIR/evidence/article-thumbnail-migration.log" \
    bash "$REPO_ROOT/scripts/tests/test_article_thumbnail_migration.sh"
  write_phase_summary article-thumbnail-migration-summary.json article-thumbnail-migration
fi

if [[ "$REAL_E2E" == 1 ]]; then
  echo "==> Running unmocked real Chromium UI suite"
  run_tracked env \
    WONIUNOTE_REAL_E2E=1 \
    WONIUNOTE_API_PROXY_TARGET="$BASE_URL" \
    WONIUNOTE_REAL_E2E_URL="$FRONTEND_URL" \
    WONIUNOTE_TEST_EVIDENCE_DIR="$RUN_DIR/evidence" \
    WONIUNOTE_TEST_RUN_ID="$RUN_ID" \
    bash -c 'cd "$1"; exec npm run test:e2e:real' _ "$FRONTEND_DIR"
  write_phase_summary real-browser-summary.json real-chromium-auth-and-business-suite
fi

write_manifest
SERVICES_READY=1
RUN_COMPLETED=1
echo "==> HTTP tests and requested browser suite complete"
echo "Manifest (credentials omitted): $RUN_DIR/run.json"
