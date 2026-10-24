#!/usr/bin/env bash

# Run the migration only in the exact disposable MySQL container created by the
# Iteration 21 integration harness. No host/default MySQL target is permitted.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATION="$PROJECT_DIR/scripts/sql/migrations/2026-10-23_math_answers.sql"
FRESH_SCHEMA="$PROJECT_DIR/scripts/sql/08_math_training.sql"

required_vars=(
    WONIUNOTE_TEST_RUN_ID
    WONIUNOTE_TEST_MYSQL_CONTAINER_ID
    WONIUNOTE_TEST_DB_NAME
    WONIUNOTE_TEST_DB_HOST
    WONIUNOTE_TEST_DB_PORT
    WONIUNOTE_TEST_DB_USER
    WONIUNOTE_TEST_DB_PASSWORD
)
for variable in "${required_vars[@]}"; do
    if [[ -z "${!variable-}" ]]; then
        printf 'ERROR: refusing database writes without %s.\n' "$variable" >&2
        exit 2
    fi
done

RUN_ID="$WONIUNOTE_TEST_RUN_ID"
MYSQL_CONTAINER_ID="$WONIUNOTE_TEST_MYSQL_CONTAINER_ID"
DB_NAME="$WONIUNOTE_TEST_DB_NAME"
DB_HOST="$WONIUNOTE_TEST_DB_HOST"
DB_PORT="$WONIUNOTE_TEST_DB_PORT"
DB_USER="$WONIUNOTE_TEST_DB_USER"
DB_PASSWORD="$WONIUNOTE_TEST_DB_PASSWORD"

if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]]; then
    printf 'ERROR: invalid harness run id; no database connection attempted.\n' >&2
    exit 2
fi
if [[ ! "$MYSQL_CONTAINER_ID" =~ ^[0-9a-f]{64}$ ]]; then
    printf 'ERROR: invalid Docker container identity; no database connection attempted.\n' >&2
    exit 2
fi
if [[ "$DB_HOST" != 127.0.0.1 || ! "$DB_PORT" =~ ^[0-9]{1,5}$ ||
      "$DB_PORT" -lt 1024 || "$DB_PORT" -gt 65535 || "$DB_USER" != root ]]; then
    printf 'ERROR: database target does not match the isolated harness contract.\n' >&2
    exit 2
fi
EXPECTED_DB="woniunote_test_${RUN_ID//-/}"
if [[ "$DB_NAME" != "$EXPECTED_DB" ]]; then
    printf 'ERROR: schema name does not belong to the supplied harness run.\n' >&2
    exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
    printf 'ERROR: Docker is required to verify the owned MySQL target.\n' >&2
    exit 2
fi

MYSQL_NAME="woniunote-i21-$RUN_ID-mysql"
inspect_template='{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|{{index .Config.Labels "org.woniunote.iter21.service"}}|{{.State.Running}}'
identity="$(docker inspect --format "$inspect_template" "$MYSQL_CONTAINER_ID" 2>/dev/null)" || {
    printf 'ERROR: owned MySQL container is unavailable; no database writes attempted.\n' >&2
    exit 2
}
IFS='|' read -r inspected_id inspected_name inspected_run inspected_service is_running <<< "$identity"
if [[ "$inspected_id" != "$MYSQL_CONTAINER_ID" || "$inspected_name" != "/$MYSQL_NAME" ||
      "$inspected_run" != "$RUN_ID" || "$inspected_service" != mysql ||
      "$is_running" != true ]]; then
    printf 'ERROR: Docker labels do not prove ownership by this harness run.\n' >&2
    exit 2
fi

mapped_port="$(docker port "$MYSQL_CONTAINER_ID" 3306/tcp 2>/dev/null)" || {
    printf 'ERROR: owned MySQL port is unavailable; no database writes attempted.\n' >&2
    exit 2
}
if [[ "$mapped_port" != "127.0.0.1:${DB_PORT}" ]]; then
    printf 'ERROR: MySQL port mapping does not match the explicit harness target.\n' >&2
    exit 2
fi

mysql_common() {
    docker exec -i -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" mysql \
        --protocol=tcp --host=127.0.0.1 --connect-timeout=5 \
        --default-character-set=utf8mb4 --user="$DB_USER" "$@"
}

mysql_query() {
    local database="$1"
    local query="$2"
    mysql_common --database="$database" --batch --raw --skip-column-names --execute="$query"
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

assert_equal() {
    local expected="$1"
    local actual="$2"
    local label="$3"
    [[ "$actual" == "$expected" ]] || fail "$label: expected '$expected', got '$actual'"
}

# Validate the anchor schema before creating any scratch schemas.
target_schema_count="$(mysql_query information_schema \
    "SELECT COUNT(*) FROM schemata WHERE schema_name = '$DB_NAME'")"
assert_equal '1' "$target_schema_count" 'runner-owned target schema exists'

RUN_TOKEN="${RUN_ID//[^a-zA-Z0-9]/}"
TEST_SUFFIX="${RUN_TOKEN:0:12}_$$-$(date +%s)"
UPGRADE_DB="math_answers_upg_${TEST_SUFFIX}"
FRESH_DB="math_answers_new_${TEST_SUFFIX}"
UNSUPPORTED_DB="math_answers_bad_${TEST_SUFFIX}"
UPGRADE_CREATED=0
FRESH_CREATED=0
UNSUPPORTED_CREATED=0

cleanup() {
    local status=$?
    trap - EXIT
    if [[ "$UPGRADE_CREATED" == 1 ]]; then
        mysql_common --execute="DROP DATABASE \`$UPGRADE_DB\`" >/dev/null 2>&1 || true
    fi
    if [[ "$FRESH_CREATED" == 1 ]]; then
        mysql_common --execute="DROP DATABASE \`$FRESH_DB\`" >/dev/null 2>&1 || true
    fi
    if [[ "$UNSUPPORTED_CREATED" == 1 ]]; then
        mysql_common --execute="DROP DATABASE \`$UNSUPPORTED_DB\`" >/dev/null 2>&1 || true
    fi
    exit "$status"
}
trap cleanup EXIT

mysql_common --execute="CREATE DATABASE \`$UPGRADE_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
UPGRADE_CREATED=1
mysql_common --execute="CREATE DATABASE \`$FRESH_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
FRESH_CREATED=1
mysql_common --execute="CREATE DATABASE \`$UNSUPPORTED_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
UNSUPPORTED_CREATED=1

# Model an existing legacy schema and verify old zero/non-zero integer values
# remain unchanged after conversion to DOUBLE NULL.
mysql_query "$UPGRADE_DB" "
CREATE TABLE users (userid INT NOT NULL PRIMARY KEY) ENGINE=InnoDB;
INSERT INTO users (userid) VALUES (1);
CREATE TABLE math_training_records (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL
) ENGINE=InnoDB;
INSERT INTO math_training_records (id, user_id) VALUES (1, 1);
CREATE TABLE math_training_wrong_answers (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  record_id BIGINT NOT NULL,
  user_id INT NOT NULL,
  question VARCHAR(100) NOT NULL,
  correct_answer INT NOT NULL,
  user_answer INT NOT NULL,
  operation VARCHAR(10) NOT NULL,
  difficulty INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_record_id (record_id),
  KEY idx_user_id (user_id),
  CONSTRAINT fk_math_answer_record FOREIGN KEY (record_id) REFERENCES math_training_records(id),
  CONSTRAINT fk_math_answer_user FOREIGN KEY (user_id) REFERENCES users(userid)
) ENGINE=InnoDB;
INSERT INTO math_training_wrong_answers
  (record_id, user_id, question, correct_answer, user_answer, operation, difficulty)
VALUES (1, 1, '1 + 1', 2, 0, '+', 1), (1, 1, '6 * 7', 42, 41, '*', 2);
"

mysql_common --database="$UPGRADE_DB" < "$FRESH_SCHEMA"
mysql_common --database="$UPGRADE_DB" < "$MIGRATION"
mysql_common --database="$UPGRADE_DB" < "$MIGRATION"

column_state="$(mysql_query "$UPGRADE_DB" "
SELECT CONCAT(DATA_TYPE, ':', IS_NULLABLE)
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'math_training_wrong_answers'
  AND column_name = 'user_answer'
")"
assert_equal 'double:YES' "$column_state" 'upgraded answer type/nullability'

preserved_answers="$(mysql_query "$UPGRADE_DB" "
SELECT GROUP_CONCAT(user_answer ORDER BY id SEPARATOR ',')
FROM math_training_wrong_answers
")"
assert_equal '0,41' "$preserved_answers" 'historical answer preservation'

mysql_query "$UPGRADE_DB" "
INSERT INTO math_training_wrong_answers
  (record_id, user_id, question, correct_answer, user_answer, operation, difficulty)
VALUES (1, 1, '2 / 3', 0, NULL, '/', 2), (1, 1, '1 / 2', 0, 1.5, '/', 2);
"
new_answer_state="$(mysql_query "$UPGRADE_DB" "
SELECT CONCAT(SUM(user_answer IS NULL), ':', SUM(user_answer = 1.5))
FROM math_training_wrong_answers
WHERE id > 2
")"
assert_equal '1:1' "$new_answer_state" 'nullable and decimal answers'

# Fresh schema and the migration must converge on the same column contract.
mysql_query "$FRESH_DB" "CREATE TABLE users (userid INT NOT NULL PRIMARY KEY) ENGINE=InnoDB"
mysql_common --database="$FRESH_DB" < "$FRESH_SCHEMA"
mysql_common --database="$FRESH_DB" < "$MIGRATION"
fresh_column_state="$(mysql_query "$FRESH_DB" "
SELECT CONCAT(DATA_TYPE, ':', IS_NULLABLE)
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'math_training_wrong_answers'
  AND column_name = 'user_answer'
")"
assert_equal 'double:YES' "$fresh_column_state" 'fresh schema answer type/nullability'

# An unsupported existing type must fail closed and remain untouched.
mysql_query "$UNSUPPORTED_DB" "
CREATE TABLE math_training_wrong_answers (
  id INT NOT NULL PRIMARY KEY,
  user_answer VARCHAR(20) NULL
) ENGINE=InnoDB;
"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration unexpectedly accepted an unsupported answer-column schema'
fi
unsupported_column_state="$(mysql_query "$UNSUPPORTED_DB" "
SELECT CONCAT(DATA_TYPE, ':', IS_NULLABLE)
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'math_training_wrong_answers'
  AND column_name = 'user_answer'
")"
assert_equal 'varchar:YES' "$unsupported_column_state" 'unsupported schema unchanged'

# A missing column is also an unknown schema and must not be repaired silently.
mysql_query "$UNSUPPORTED_DB" "ALTER TABLE math_training_wrong_answers DROP COLUMN user_answer"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration unexpectedly added a missing answer column'
fi
missing_column_count="$(mysql_query "$UNSUPPORTED_DB" "
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'math_training_wrong_answers'
  AND column_name = 'user_answer'
")"
assert_equal '0' "$missing_column_count" 'missing schema remains unchanged'

printf 'PASS: owned MySQL math-answer migration is idempotent and preserves legacy values.\n'
