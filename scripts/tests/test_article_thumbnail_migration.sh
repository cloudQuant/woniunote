#!/usr/bin/env bash

# Exercise only the run-owned disposable MySQL instance created by the Iteration
# 21 integration runner. This script never falls back to a host/default server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATION="$PROJECT_DIR/scripts/sql/migrations/2026-10-24_article_thumbnail.sql"
FRESH_SCHEMA="$PROJECT_DIR/scripts/sql/02_article.sql"

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
      "$DB_USER" != root || -z "$DB_PASSWORD" ]]; then
    printf 'ERROR: database target does not match the isolated harness contract.\n' >&2
    exit 2
fi
DB_PORT_NUMBER=$((10#$DB_PORT))
if (( DB_PORT_NUMBER < 1024 || DB_PORT_NUMBER > 65535 )); then
    printf 'ERROR: database target port is outside the isolated harness range.\n' >&2
    exit 2
fi
EXPECTED_DB="woniunote_test_${RUN_ID//-/}"
if [[ "$DB_NAME" != "$EXPECTED_DB" ]]; then
    printf 'ERROR: schema name does not belong to the supplied harness run.\n' >&2
    exit 2
fi
if [[ ! -f "$MIGRATION" || ! -f "$FRESH_SCHEMA" ]]; then
    printf 'ERROR: required thumbnail migration or fresh schema file is unavailable.\n' >&2
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
if [[ "$mapped_port" != "127.0.0.1:${DB_PORT_NUMBER}" ]]; then
    printf 'ERROR: MySQL port mapping does not match the explicit harness target.\n' >&2
    exit 2
fi

mysql_common() {
    docker exec -i -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" mysql \
        --protocol=tcp --host=127.0.0.1 --connect-timeout=5 \
        --default-character-set=utf8mb4 --user="$DB_USER" "$@"
}

mysql_common_no_backslash() {
    docker exec -i -e "MYSQL_PWD=$DB_PASSWORD" "$MYSQL_CONTAINER_ID" mysql \
        --protocol=tcp --host=127.0.0.1 --connect-timeout=5 \
        --default-character-set=utf8mb4 \
        --init-command="SET SESSION sql_mode=CONCAT(@@SESSION.sql_mode, ',NO_BACKSLASH_ESCAPES')" \
        --user="$DB_USER" "$@"
}

mysql_query() {
    local database="$1"
    local query="$2"
    mysql_common --database="$database" --batch --raw --skip-column-names --execute="$query"
}

mysql_query_no_backslash() {
    local database="$1"
    local query="$2"
    mysql_common_no_backslash --database="$database" --batch --raw --skip-column-names --execute="$query"
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_equal() {
    local expected="$1"
    local actual="$2"
    local label="$3"
    [[ "$actual" == "$expected" ]] || fail "$label"
}

signature_query="SELECT CONCAT(DATA_TYPE, '|', CHARACTER_MAXIMUM_LENGTH, '|', IS_NULLABLE, '|', CHARACTER_SET_NAME, '|', COLLATION_NAME) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'thumbnail'"
column_signature() {
    mysql_query "$1" "$signature_query"
}
column_comment_default() {
    mysql_query "$1" "SELECT CONCAT(COLUMN_DEFAULT IS NULL, '|', HEX(COLUMN_COMMENT)) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'thumbnail'"
}

target_schema_count="$(mysql_query information_schema \
    "SELECT COUNT(*) FROM schemata WHERE schema_name = '$DB_NAME'")"
assert_equal '1' "$target_schema_count" 'runner-owned target schema is unavailable'

RUN_TOKEN="${RUN_ID//[^a-zA-Z0-9]/}"
TEST_SUFFIX="${RUN_TOKEN:0:12}_$$_$(date +%s)"
OLD_DB="i21_thumb_old_${TEST_SUFFIX}"
FRESH_DB="i21_thumb_fresh_${TEST_SUFFIX}"
NO_BACKSLASH_DB="i21_thumb_no_backslash_${TEST_SUFFIX}"
UNSUPPORTED_DB="i21_thumb_bad_${TEST_SUFFIX}"
COMMENT_TEXT="legacy thumbnail 'quoted' \\ path"
COMMENT_HEX="$(printf '%s' "$COMMENT_TEXT" | od -An -tx1 | tr -d ' \n' | tr '[:lower:]' '[:upper:]')"
CREATED_DATABASES=()

cleanup() {
    local status=$?
    local cleanup_failed=0 database
    trap - EXIT
    set +e
    for database in "${CREATED_DATABASES[@]}"; do
        if ! mysql_common --execute="DROP DATABASE \`$database\`" >/dev/null 2>&1; then
            cleanup_failed=1
        fi
    done
    if [[ "$status" == 0 && "$cleanup_failed" == 1 ]]; then
        status=1
        printf 'FAIL: could not remove one or more run-scoped scratch schemas.\n' >&2
    fi
    exit "$status"
}
trap cleanup EXIT

target_shape="$(mysql_query information_schema "SELECT COUNT(*) FROM schemata WHERE schema_name = '$DB_NAME'")"
assert_equal '1' "$target_shape" 'runner-owned target schema changed before test setup'

mysql_common --execute="CREATE DATABASE \`$OLD_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
CREATED_DATABASES+=("$OLD_DB")
mysql_common --execute="CREATE DATABASE \`$FRESH_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
CREATED_DATABASES+=("$FRESH_DB")
mysql_common --execute="CREATE DATABASE \`$NO_BACKSLASH_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
CREATED_DATABASES+=("$NO_BACKSLASH_DB")
mysql_common --execute="CREATE DATABASE \`$UNSUPPORTED_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
CREATED_DATABASES+=("$UNSUPPORTED_DB")

# Existing 30-character column uses a distinct character set and collation so
# the migration must preserve both instead of inheriting the table default.
mysql_query "$OLD_DB" "
CREATE TABLE article (
  articleid INT NOT NULL PRIMARY KEY,
  thumbnail VARCHAR(30) CHARACTER SET latin1 COLLATE latin1_bin DEFAULT NULL COMMENT 'legacy thumbnail ''quoted'' \\\\ path'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
INSERT INTO article (articleid, thumbnail) VALUES
  (1, NULL), (2, ''), (3, 'cover_legacy.png');
"
old_before="$(column_signature "$OLD_DB")"
assert_equal 'varchar|30|YES|latin1|latin1_bin' "$old_before" 'legacy schema seed shape'
legacy_comment_default_before="$(column_comment_default "$OLD_DB")"
assert_equal "1|$COMMENT_HEX" "$legacy_comment_default_before" 'legacy comment/default seed values'
legacy_values_before="$(mysql_query "$OLD_DB" "SELECT CONCAT((SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=1), '|', (SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=2), '|', (SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=3))")"
assert_equal '<NULL>||cover_legacy.png' "$legacy_values_before" 'legacy schema seed values'

mysql_common --database="$OLD_DB" < "$MIGRATION"
migrated_signature="$(column_signature "$OLD_DB")"
assert_equal 'varchar|512|YES|latin1|latin1_bin' "$migrated_signature" '30 to 512 migration and charset/collation preservation'
assert_equal "$legacy_comment_default_before" "$(column_comment_default "$OLD_DB")" 'legacy comment/default changed during migration'
legacy_values_after="$(mysql_query "$OLD_DB" "SELECT CONCAT((SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=1), '|', (SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=2), '|', (SELECT IF(thumbnail IS NULL, '<NULL>', thumbnail) FROM article WHERE articleid=3))")"
assert_equal "$legacy_values_before" "$legacy_values_after" 'legacy thumbnail values changed during migration'

# Exercise migration quoting in a separate connection whose SQL mode treats
# backslashes literally. Apostrophes still have to be doubled in SQL literals.
mysql_query_no_backslash "$NO_BACKSLASH_DB" "CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, thumbnail VARCHAR(30) CHARACTER SET latin1 COLLATE latin1_bin DEFAULT NULL COMMENT 'legacy thumbnail ''quoted'' \ path') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
no_backslash_comment_before="$(mysql_query_no_backslash "$NO_BACKSLASH_DB" "SELECT CONCAT(COLUMN_DEFAULT IS NULL, '|', HEX(COLUMN_COMMENT)) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'thumbnail'")"
assert_equal "1|$COMMENT_HEX" "$no_backslash_comment_before" 'NO_BACKSLASH_ESCAPES comment seed'
mysql_common_no_backslash --database="$NO_BACKSLASH_DB" < "$MIGRATION"
assert_equal 'varchar|512|YES|latin1|latin1_bin' "$(column_signature "$NO_BACKSLASH_DB")" 'NO_BACKSLASH_ESCAPES migration shape'
assert_equal "$no_backslash_comment_before" "$(mysql_query_no_backslash "$NO_BACKSLASH_DB" "SELECT CONCAT(COLUMN_DEFAULT IS NULL, '|', HEX(COLUMN_COMMENT)) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'article' AND column_name = 'thumbnail'")" 'NO_BACKSLASH_ESCAPES migration changed comment/default'

LONG_FILENAME="cover_$(printf '%*s' 180 '' | tr ' ' 'a').png"
LONG_URL="/uploads/uploads/images/2026/10/$LONG_FILENAME"
mysql_query "$OLD_DB" "INSERT INTO article (articleid, thumbnail) VALUES (4, '$LONG_URL')"
long_url_state="$(mysql_query "$OLD_DB" "SELECT CONCAT(CHAR_LENGTH(thumbnail) > 30, '|', CHAR_LENGTH(thumbnail) <= 512, '|', LEFT(thumbnail, CHAR_LENGTH('/uploads/uploads/images/2026/10/')) = '/uploads/uploads/images/2026/10/', '|', RIGHT(thumbnail, 4) = '.png') FROM article WHERE articleid=4")"
assert_equal '1|1|1|1' "$long_url_state" 'long uploaded-image URL did not fit'
assert_equal "$LONG_URL" "$(mysql_query "$OLD_DB" 'SELECT thumbnail FROM article WHERE articleid=4')" 'canonical upload URL string changed'
assert_equal '1' "$(mysql_query "$OLD_DB" "SELECT BINARY thumbnail = BINARY '$LONG_URL' FROM article WHERE articleid=4")" 'canonical upload URL bytes changed'
values_before_repeat="$(mysql_query "$OLD_DB" "SELECT GROUP_CONCAT(CONCAT(articleid, '=', IFNULL(thumbnail, '<NULL>')) ORDER BY articleid SEPARATOR '|') FROM article")"
table_before_repeat="$(mysql_query "$OLD_DB" 'SHOW CREATE TABLE article')"
mysql_common --database="$OLD_DB" < "$MIGRATION"
assert_equal "$migrated_signature" "$(column_signature "$OLD_DB")" 'repeat migration changed thumbnail shape'
assert_equal "$values_before_repeat" "$(mysql_query "$OLD_DB" "SELECT GROUP_CONCAT(CONCAT(articleid, '=', IFNULL(thumbnail, '<NULL>')) ORDER BY articleid SEPARATOR '|') FROM article")" 'repeat migration changed existing values'
assert_equal "$table_before_repeat" "$(mysql_query "$OLD_DB" 'SHOW CREATE TABLE article')" 'repeat migration changed table DDL'

# Load the actual fresh schema. It must converge on the same application shape.
mysql_query "$FRESH_DB" "CREATE TABLE users (userid INT NOT NULL AUTO_INCREMENT PRIMARY KEY) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
mysql_common --database="$FRESH_DB" < "$FRESH_SCHEMA"
fresh_signature="$(column_signature "$FRESH_DB")"
assert_equal 'varchar|512|YES|utf8mb4|utf8mb4_unicode_ci' "$fresh_signature" 'fresh article schema shape'
fresh_before_migration="$(mysql_query "$FRESH_DB" 'SHOW CREATE TABLE article')"
mysql_common --database="$FRESH_DB" < "$MIGRATION"
assert_equal "$fresh_signature" "$(column_signature "$FRESH_DB")" 'fresh-schema migration changed column shape'
assert_equal "$fresh_before_migration" "$(mysql_query "$FRESH_DB" 'SHOW CREATE TABLE article')" 'fresh-schema migration was not a no-op'
assert_equal "$(cut -d '|' -f1-3 <<< "$migrated_signature")" \
    "$(cut -d '|' -f1-3 <<< "$fresh_signature")" 'fresh and migrated application schemas differ'

# Unknown types, widths, and missing columns must be rejected without changing
# the sentinel value or silently repairing the schema.
mysql_query "$UNSUPPORTED_DB" "CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, thumbnail TEXT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; INSERT INTO article VALUES (1, 'keep-type-value')"
type_before="$(column_signature "$UNSUPPORTED_DB")"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted an unsupported thumbnail type'
fi
assert_equal "$type_before" "$(column_signature "$UNSUPPORTED_DB")" 'unsupported type schema changed'
assert_equal 'keep-type-value' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT thumbnail FROM article WHERE articleid=1')" 'unsupported type value changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, thumbnail VARCHAR(120) NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; INSERT INTO article VALUES (2, 'keep-width-value')"
width_before="$(column_signature "$UNSUPPORTED_DB")"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted an unsupported thumbnail width'
fi
assert_equal "$width_before" "$(column_signature "$UNSUPPORTED_DB")" 'unsupported width schema changed'
assert_equal 'keep-width-value' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT thumbnail FROM article WHERE articleid=2')" 'unsupported width value changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, headline VARCHAR(40) NOT NULL) ENGINE=InnoDB; INSERT INTO article VALUES (3, 'keep-missing-column-row')"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted a missing thumbnail column'
fi
assert_equal '0' "$(mysql_query information_schema "SELECT COUNT(*) FROM columns WHERE table_schema = '$UNSUPPORTED_DB' AND table_name = 'article' AND column_name = 'thumbnail'")" 'missing thumbnail column was added'
assert_equal 'keep-missing-column-row' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT headline FROM article WHERE articleid=3')" 'missing-column sentinel row changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, thumbnail VARCHAR(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL) ENGINE=InnoDB; INSERT INTO article VALUES (4, 'keep-not-null-value')"
not_null_before="$(column_signature "$UNSUPPORTED_DB")"
not_null_ddl_before="$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted a non-nullable thumbnail column'
fi
assert_equal "$not_null_before" "$(column_signature "$UNSUPPORTED_DB")" 'non-nullable thumbnail shape changed'
assert_equal 'keep-not-null-value' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT thumbnail FROM article WHERE articleid=4')" 'non-nullable thumbnail value changed'
assert_equal "$not_null_ddl_before" "$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')" 'non-nullable thumbnail DDL changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, thumbnail VARCHAR(30) NULL DEFAULT 'default-thumb.png') ENGINE=InnoDB; INSERT INTO article VALUES (5, 'keep-default-value')"
default_before="$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted a thumbnail column with a non-NULL default'
fi
assert_equal "$default_before" "$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')" 'non-NULL default thumbnail DDL changed'
assert_equal 'keep-default-value' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT thumbnail FROM article WHERE articleid=5')" 'non-NULL default thumbnail value changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE article (articleid INT NOT NULL PRIMARY KEY, title VARCHAR(40) NOT NULL, thumbnail VARCHAR(30) GENERATED ALWAYS AS (title) VIRTUAL) ENGINE=InnoDB; INSERT INTO article (articleid, title) VALUES (6, 'generated-sentinel')"
generated_before="$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted a generated thumbnail column'
fi
assert_equal "$generated_before" "$(mysql_query "$UNSUPPORTED_DB" 'SHOW CREATE TABLE article')" 'generated thumbnail DDL changed'
assert_equal 'generated-sentinel' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT thumbnail FROM article WHERE articleid=6')" 'generated thumbnail value changed'

mysql_query "$UNSUPPORTED_DB" "DROP TABLE article; CREATE TABLE migration_sentinel (id INT NOT NULL PRIMARY KEY, value VARCHAR(40) NOT NULL); INSERT INTO migration_sentinel VALUES (1, 'keep-article-absent-row')"
if mysql_common --database="$UNSUPPORTED_DB" < "$MIGRATION" >/dev/null 2>&1; then
    fail 'migration accepted a missing article table'
fi
assert_equal '0' "$(mysql_query information_schema "SELECT COUNT(*) FROM tables WHERE table_schema = '$UNSUPPORTED_DB' AND table_name = 'article'")" 'missing article table was created'
assert_equal 'keep-article-absent-row' "$(mysql_query "$UNSUPPORTED_DB" 'SELECT value FROM migration_sentinel WHERE id=1')" 'article-absent sentinel row changed'

printf '{"status":"PASS","run_id":"%s","legacy_values_preserved":true,"comment_default_preserved":true,"no_backslash_escapes_supported":true,"nullable_varchar_512":true,"repeat_migration_noop":true,"long_url_stored":true,"charset_collation_preserved":true,"fresh02_compatible":true,"unsupported_shapes_rejected_unchanged":true}\n' "$RUN_ID"
