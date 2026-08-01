#!/usr/bin/env bash

# Contract test for scripts/database_transfer.sh.  It uses fake mysql clients
# so no developer or production database is read, written, or deleted.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TRANSFER_SCRIPT="$PROJECT_DIR/scripts/database_transfer.sh"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/woniunote-db-transfer-test.XXXXXX")"
BIN_DIR="$TMP_DIR/bin"
OUTPUT_DIR="$TMP_DIR/backups"
CONFIG_FILE="$TMP_DIR/config.json"
MYSQL_LOG="$TMP_DIR/mysql.log"
DUMP_LOG="$TMP_DIR/mysqldump.log"
IMPORT_LOG="$TMP_DIR/import.sql"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

assert_file() {
    [[ -f "$1" ]] || fail "expected file not found: $1"
}

assert_contains() {
    local expected="$1"
    local file="$2"
    grep -F -- "$expected" "$file" >/dev/null || fail "expected '$expected' in $file"
}

mkdir -p "$BIN_DIR"

cat > "$CONFIG_FILE" <<'EOF'
{
  "db_clients": [
    {
      "name": "mysql",
      "rdbms": "mysql",
      "host": "migration-db.example.test",
      "port": 3307,
      "dbname": "woniunote_transfer_test",
      "user": "migration_user",
      "passwd": "test-only-password"
    }
  ]
}
EOF

cat > "$BIN_DIR/mysqldump" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$DUMP_LOG"
if [[ "${1:-}" == "--version" ]]; then
    printf 'mysqldump fake 1.0\n'
    exit 0
fi
cat <<'SQL'
CREATE DATABASE /*!32312 IF NOT EXISTS*/ `woniunote_transfer_test` /*!40100 DEFAULT CHARACTER SET utf8mb4 */;
USE `woniunote_transfer_test`;
DROP TABLE IF EXISTS `article`;
CREATE TABLE `article` (`articleid` bigint NOT NULL);
INSERT INTO `article` VALUES (1);
SQL
EOF

cat > "$BIN_DIR/mysql" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
arguments="$*"
printf '%s\n' "$arguments" >> "$MYSQL_LOG"
if [[ "$arguments" == *"information_schema.schemata"* ]]; then
    printf '%s\n' "${FAKE_SCHEMA_EXISTS:-1}"
elif [[ "$arguments" == *"information_schema.tables"* ]]; then
    printf '%s\n' "${FAKE_TABLE_COUNT:-3}"
elif [[ "$arguments" != *"--execute"* ]]; then
    cat >> "$IMPORT_LOG"
fi
EOF

chmod +x "$BIN_DIR/mysql" "$BIN_DIR/mysqldump"

export DUMP_LOG MYSQL_LOG IMPORT_LOG
export WONIUNOTE_DB_CONFIG="$CONFIG_FILE"
export WONIUNOTE_MYSQL_BIN="$BIN_DIR/mysql"
export WONIUNOTE_MYSQLDUMP_BIN="$BIN_DIR/mysqldump"

bash "$TRANSFER_SCRIPT" export --output-dir "$OUTPUT_DIR"

ARCHIVE="$(find "$OUTPUT_DIR" -maxdepth 1 -name '*.sql.gz' -print -quit)"
[[ -n "$ARCHIVE" ]] || fail "export did not create a .sql.gz archive"
assert_file "$ARCHIVE"
assert_file "${ARCHIVE}.sha256"
assert_file "${ARCHIVE}.metadata"
gzip -t "$ARCHIVE"
gzip -cd "$ARCHIVE" | grep -F 'CREATE DATABASE' >/dev/null || fail "archive has no database DDL"
assert_contains '--single-transaction' "$DUMP_LOG"
assert_contains '--routines' "$DUMP_LOG"
assert_contains '--events' "$DUMP_LOG"
assert_contains 'database=woniunote_transfer_test' "${ARCHIVE}.metadata"
if grep -F 'test-only-password' "${ARCHIVE}.metadata" "${ARCHIVE}.sha256"; then
    fail "backup metadata must not contain the database password"
fi

if bash "$TRANSFER_SCRIPT" import "$ARCHIVE" >"$TMP_DIR/import-without-replace.out" 2>&1; then
    fail "import should refuse to replace a non-empty database without --replace"
fi
assert_contains '--replace' "$TMP_DIR/import-without-replace.out"
[[ ! -s "$IMPORT_LOG" ]] || fail "refused import unexpectedly streamed SQL"

bash "$TRANSFER_SCRIPT" import --replace "$ARCHIVE"
assert_contains 'DROP DATABASE IF EXISTS' "$MYSQL_LOG"
assert_contains 'CREATE DATABASE' "$IMPORT_LOG"

printf 'PASS: database export/import contract verified with isolated fake MySQL clients.\n'
