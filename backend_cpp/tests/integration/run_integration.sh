#!/usr/bin/env bash
#
# Run backend HTTP integration tests against an isolated test database.
#
# Steps:
#   1. Create + seed the `woniunote_test` schema (idempotent).
#   2. Render config.integration.json from the template using env values.
#   3. Start the built backend on a test port with a strong JWT secret.
#   4. Wait for /health, run pytest, then stop the server.
#
# Never touches the production/dev database. Safe to run locally and in CI.

set -euo pipefail

# --- Resolve paths ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"   # backend_cpp/
REPO_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"

# --- Config (overridable via env) ------------------------------------------
DB_HOST="${WONIUNOTE_TEST_DB_HOST:-127.0.0.1}"
DB_PORT="${WONIUNOTE_TEST_DB_PORT:-3306}"
DB_USER="${WONIUNOTE_TEST_DB_USER:-root}"
DB_PASSWORD="${WONIUNOTE_TEST_DB_PASSWORD:-}"
DB_NAME="${WONIUNOTE_TEST_DB_NAME:-woniunote_test}"
REDIS_HOST="${WONIUNOTE_TEST_REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${WONIUNOTE_TEST_REDIS_PORT:-6379}"
TEST_PORT="${WONIUNOTE_TEST_PORT:-5273}"
RATE_LIMIT="${WONIUNOTE_TEST_RATE_LIMIT:-60}"
BACKEND_BIN="${WONIUNOTE_BACKEND_BIN:-$BACKEND_DIR/build/woniunote_backend}"
# Interpreter used for the runner's own Python helpers (Redis preflight,
# config rendering). PYTEST_CMD only covers the pytest invocation itself.
PYTHON_CMD="${WONIUNOTE_TEST_PYTHON:-python3}"
# Strict mode (release/CI): no skips — a rate-limit case that cannot observe a
# real 429 must fail the run instead of being silently skipped.
STRICT="${WONIUNOTE_TEST_STRICT:-0}"

# Optional: run the suite against an already-running test instance. When set,
# the runner does not create/seed the schema and does not start a backend.
EXTERNAL_BASE_URL="${WONIUNOTE_TEST_BASE_URL:-}"
BASE_URL="${EXTERNAL_BASE_URL:-http://127.0.0.1:${TEST_PORT}}"

echo "==> WoniuNote backend integration tests"
echo "    DB:    ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "    Redis: ${REDIS_HOST}:${REDIS_PORT} (db 1)"
echo "    URL:   ${BASE_URL}"
echo "    Mode:  $([ "$STRICT" = "1" ] && echo strict || echo local)"
[ -n "$EXTERNAL_BASE_URL" ] && echo "    Using external instance: no DB setup, no server start"

# --- Isolation guard -------------------------------------------------------
# The suite creates rows and hammers the rate limiter; it must never point at a
# development or production schema. Test database names must look like test
# schemas (e.g. woniunote_test), and the API port must not be the dev port.
case "$DB_NAME" in
  *_test | *_test_* | test_* | *Test) ;;
  *)
    echo "ERROR: refusing to run against non-test database '${DB_NAME}'." >&2
    echo "       Use a dedicated test schema (default: woniunote_test)." >&2
    exit 1
    ;;
esac

if [ -z "$EXTERNAL_BASE_URL" ] && [ "$TEST_PORT" = "5173" ]; then
  echo "ERROR: WONIUNOTE_TEST_PORT=5173 is the development backend port." >&2
  echo "       Pick a dedicated test port (default: 5273)." >&2
  exit 1
fi

# --- External-instance mode ------------------------------------------------
# WONIUNOTE_TEST_BASE_URL points the suite at an already-running test backend.
# This mode deliberately skips schema setup and server management: the caller
# owns the instance, its schema and its lifecycle (README documents this).
if [ -n "$EXTERNAL_BASE_URL" ]; then
  echo "==> Running against external instance ${BASE_URL} (no DB setup, no server start)"
  export WONIUNOTE_TEST_BASE_URL="$BASE_URL"
  export WONIUNOTE_TEST_RATE_LIMIT="$RATE_LIMIT"
  export WONIUNOTE_TEST_STRICT="$STRICT"
  PYTEST_CMD="${PYTEST_CMD:-$PYTHON_CMD -m pytest}"
  # shellcheck disable=SC2086
  $PYTEST_CMD "$SCRIPT_DIR/test_api_integration.py" -v
  exit $?
fi

print_preflight_help() {
  cat >&2 <<EOF

Integration test prerequisites:
  - Built backend binary: ${BACKEND_BIN}
  - MySQL reachable at ${DB_HOST}:${DB_PORT}
  - Redis reachable at ${REDIS_HOST}:${REDIS_PORT}

Override local credentials with:
  export WONIUNOTE_TEST_DB_HOST=127.0.0.1
  export WONIUNOTE_TEST_DB_PORT=3306
  export WONIUNOTE_TEST_DB_USER=root
  export WONIUNOTE_TEST_DB_PASSWORD='<password-if-needed>'
  export WONIUNOTE_TEST_DB_NAME=woniunote_test
  export WONIUNOTE_TEST_REDIS_HOST=127.0.0.1
  export WONIUNOTE_TEST_REDIS_PORT=6379

To use an already prepared schema:
  export WONIUNOTE_TEST_SKIP_DB_SETUP=1
EOF
}

if [ ! -x "$BACKEND_BIN" ]; then
  echo "ERROR: backend binary not found/executable at $BACKEND_BIN" >&2
  echo "       Build it first: cmake --build build" >&2
  print_preflight_help
  exit 1
fi

for required_cmd in mysql curl "$PYTHON_CMD"; do
  if ! command -v "$required_cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $required_cmd" >&2
    echo "       Override the Python interpreter with WONIUNOTE_TEST_PYTHON." >&2
    print_preflight_help
    exit 1
  fi
done

# --- mysql client helper ---------------------------------------------------
mysql_cmd() {
  if [ -n "$DB_PASSWORD" ]; then
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$@"
  else
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$@"
  fi
}

# --- Preflight -------------------------------------------------------------
echo "==> Checking local integration prerequisites"
if ! mysql_cmd -e "SELECT 1" >/dev/null 2>&1; then
  echo "ERROR: cannot connect to MySQL as ${DB_USER}@${DB_HOST}:${DB_PORT}." >&2
  echo "       No database was created or modified." >&2
  print_preflight_help
  exit 1
fi

# Redis preflight: speak the protocol (PING/PONG), not just TCP connect. A
# listening-but-broken Redis would otherwise let the rate-limit case skip
# silently while looking healthy.
if ! "$PYTHON_CMD" - "$REDIS_HOST" "$REDIS_PORT" <<'PY' >/dev/null 2>&1
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.create_connection((host, port), timeout=2) as sock:
    sock.settimeout(2)
    sock.sendall(b"PING\r\n")
    if not sock.recv(64).startswith(b"+PONG"):
        raise SystemExit("unexpected Redis reply to PING")
PY
then
  echo "ERROR: Redis at ${REDIS_HOST}:${REDIS_PORT} did not answer PING." >&2
  echo "       Start Redis or override WONIUNOTE_TEST_REDIS_HOST/PORT." >&2
  print_preflight_help
  exit 1
fi

# --- 1. Create + seed test schema -----------------------------------------
if [ "${WONIUNOTE_TEST_SKIP_DB_SETUP:-0}" = "1" ]; then
  echo "==> Skipping DB create/seed (WONIUNOTE_TEST_SKIP_DB_SETUP=1); using existing ${DB_NAME}"
else
  echo "==> Creating test database ${DB_NAME}"
  mysql_cmd -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

  echo "==> Loading schema into ${DB_NAME}"
  for f in "$REPO_ROOT"/scripts/sql/*.sql; do
    echo "    - $(basename "$f")"
    mysql_cmd "$DB_NAME" < "$f"
  done
fi

# Stable articles for the public article-detail navigation contract. The IDs
# deliberately leave hidden, draft and other-type records between published
# neighbours so the black-box test proves all selection predicates.
echo "==> Seeding article-navigation integration fixtures"
mysql_cmd "$DB_NAME" <<'SQL'
INSERT INTO users (userid, username, password, nickname, role, credit, createtime, updatetime)
VALUES (15001, 'itest_navigation_fixture', 'not-used-by-this-test', 'Navigation Fixture', 'user', 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE nickname = VALUES(nickname), updatetime = NOW();

INSERT INTO article (
  articleid, userid, type, headline, content, thumbnail, credit, readcount,
  replycount, recommended, hidden, drafted, checked, createtime, updatetime
) VALUES
  (15001, 15001, 915, '导航序号-第一篇', '<p>first</p>', NULL, 0, 0, 0, 0, 0, 0, 1, NOW(), NOW()),
  (15002, 15001, 915, '导航序号-隐藏文章', '<p>hidden</p>', NULL, 0, 0, 0, 0, 1, 0, 1, NOW(), NOW()),
  (15003, 15001, 915, '导航序号-草稿文章', '<p>draft</p>', NULL, 0, 0, 0, 0, 0, 1, 1, NOW(), NOW()),
  (15004, 15001, 915, '导航序号-中间篇', '<p>middle</p>', NULL, 0, 0, 0, 0, 0, 0, 1, NOW(), NOW()),
  (15005, 15001, 916, '导航序号-其他分类', '<p>other type</p>', NULL, 0, 0, 0, 0, 0, 0, 1, NOW(), NOW()),
  (15006, 15001, 915, '导航序号-最后篇', '<p>last</p>', NULL, 0, 0, 0, 0, 0, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  userid = VALUES(userid), type = VALUES(type), headline = VALUES(headline),
  content = VALUES(content), hidden = VALUES(hidden), drafted = VALUES(drafted),
  checked = VALUES(checked), updatetime = NOW();
SQL

# --- 2. Render integration config -----------------------------------------
CONFIG_OUT="$BACKEND_DIR/config.integration.json"
echo "==> Writing $CONFIG_OUT"
"$PYTHON_CMD" - "$SCRIPT_DIR/config.integration.template.json" "$CONFIG_OUT" \
  "$TEST_PORT" "$DB_HOST" "$DB_PORT" "$DB_NAME" "$DB_USER" "$DB_PASSWORD" \
  "$REDIS_HOST" "$REDIS_PORT" "$RATE_LIMIT" <<'PY'
import sys
from pathlib import Path

template = Path(sys.argv[1]).read_text()
replacements = {
    "__PORT__": sys.argv[3],
    "__DB_HOST__": sys.argv[4],
    "__DB_PORT__": sys.argv[5],
    "__DB_NAME__": sys.argv[6],
    "__DB_USER__": sys.argv[7],
    "__DB_PASSWORD__": sys.argv[8],
    "__REDIS_HOST__": sys.argv[9],
    "__REDIS_PORT__": sys.argv[10],
    "__RATE_LIMIT__": sys.argv[11],
}
for key, value in replacements.items():
    template = template.replace(key, value)
Path(sys.argv[2]).write_text(template)
PY

# --- 3. Start backend ------------------------------------------------------
# A real (non-placeholder) secret so the server starts; 'test' mode is not
# production, so this is only belt-and-braces.
export WONIUNOTE_ENV="test"
export WONIUNOTE_JWT_SECRET="integration-test-$(date +%s)-$RANDOM-strongsecret"

SERVER_PID=""
# Per-run log name so concurrent runs do not overwrite each other's evidence.
SERVER_LOG="${TMPDIR:-/tmp}/woniunote_itest_server.$$.log"
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "==> Stopping backend (pid $SERVER_PID)"
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$CONFIG_OUT"
}
# EXIT covers normal termination and failures; INT/TERM cover Ctrl-C and
# signals from CI cancellation, so no orphaned backend or temp config remains.
trap cleanup EXIT INT TERM

echo "==> Starting backend on port ${TEST_PORT}"
(
  cd "$BACKEND_DIR"
  exec "$BACKEND_BIN" "$CONFIG_OUT" >"$SERVER_LOG" 2>&1
) &
SERVER_PID=$!

# --- Wait for /health ------------------------------------------------------
echo "==> Waiting for backend to come up"
ATTEMPTS=0
until curl -sf "${BASE_URL}/health" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: backend process exited early. Server log:" >&2
    cat "$SERVER_LOG" >&2 || true
    exit 1
  fi
  if [ "$ATTEMPTS" -ge 60 ]; then
    echo "ERROR: backend did not become healthy in time. Server log:" >&2
    cat "$SERVER_LOG" >&2 || true
    exit 1
  fi
  sleep 0.5
done
echo "    backend healthy after ${ATTEMPTS} checks"

# --- 4. Run pytest ---------------------------------------------------------
echo "==> Running integration tests"
export WONIUNOTE_TEST_BASE_URL="$BASE_URL"
export WONIUNOTE_TEST_RATE_LIMIT="$RATE_LIMIT"
export WONIUNOTE_TEST_STRICT="$STRICT"

# PYTEST_CMD may contain args (e.g. "python3 -m pytest"); default to module form
# with the configured interpreter.
PYTEST_CMD="${PYTEST_CMD:-$PYTHON_CMD -m pytest}"
# shellcheck disable=SC2086
$PYTEST_CMD "$SCRIPT_DIR/test_api_integration.py" -v
RESULT=$?

exit $RESULT
