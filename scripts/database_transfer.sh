#!/usr/bin/env bash
#
# WoniuNote MySQL database transfer tool.
#
# Exports the active C++ backend database (schema, data, triggers, routines and
# events) to a compressed SQL archive, then restores the archive in another
# environment.  Credentials are read from the active backend configuration or
# from WONIUNOTE_DB_* environment variables and are never written to the dump.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_OUTPUT_DIR="$PROJECT_DIR/backups"

MYSQL_BIN="${WONIUNOTE_MYSQL_BIN:-mysql}"
MYSQLDUMP_BIN="${WONIUNOTE_MYSQLDUMP_BIN:-mysqldump}"
CONFIG_FILE=""
CLIENT_DEFAULTS_FILE=""

DB_HOST=""
DB_PORT=""
DB_NAME=""
DB_USER=""
DB_PASSWORD=""

usage() {
    cat <<'EOF'
用法:
  bash scripts/database_transfer.sh export [--output-dir 目录] [--config 配置文件]
  bash scripts/database_transfer.sh import [--replace] <备份文件.sql.gz> [--config 配置文件]

命令:
  export  导出当前 C++ 后端使用的 MySQL 数据库：表结构、全部表数据、触发器、
          存储过程和事件。默认写入 ./backups/，同时生成 SHA-256 校验文件和元数据。
  import  导入导出的 .sql.gz 备份。目标库不存在或为空时可直接导入；如果目标库
          已有表，必须额外传入 --replace 才会删除并重建该库。

连接配置优先级:
  1. WONIUNOTE_DB_HOST / PORT / NAME / USER / PASSWORD 环境变量
  2. --config 指定的 C++ Drogon 配置文件
  3. backend_cpp/config.local.json（存在时）或 backend_cpp/config.json

示例:
  bash scripts/database_transfer.sh export
  bash scripts/database_transfer.sh export --config backend_cpp/config.prod.json
  bash scripts/database_transfer.sh import backups/woniunote_20260801T120000Z.sql.gz
  bash scripts/database_transfer.sh import --replace backups/woniunote_20260801T120000Z.sql.gz

说明:
  - 导入端配置中的 dbname 必须与备份中的数据库名称一致，避免误恢复到错误的库。
  - 备份中不包含数据库密码；请在目标环境配置 config.local.json 或设置
    WONIUNOTE_DB_PASSWORD。
EOF
}

log_info() {
    printf '[INFO] %s\n' "$*"
}

log_error() {
    printf '[ERROR] %s\n' "$*" >&2
}

die() {
    log_error "$*"
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "未找到必需命令: $1"
}

cleanup() {
    if [[ -n "$CLIENT_DEFAULTS_FILE" ]]; then
        rm -f "$CLIENT_DEFAULTS_FILE"
    fi
}
trap cleanup EXIT

is_placeholder_password() {
    case "$1" in
        CHANGE_ME*|YOUR_*|*SET_VIA*|*SECURE_PASSWORD_HERE*) return 0 ;;
        *) return 1 ;;
    esac
}

validate_identifier() {
    local value="$1"
    local label="$2"

    [[ "$value" =~ ^[A-Za-z0-9_]+$ ]] || die "$label 只能包含字母、数字和下划线: $value"
}

# Extract a scalar from the first object in db_clients.  Drogon's JSON config
# is intentionally formatted this way; parsing only that object avoids taking
# the listener or Redis port by mistake, without introducing a jq dependency.
read_db_client_value() {
    local key="$1"
    local value_type="$2"

    awk -v wanted="$key" -v value_type="$value_type" '
        /"db_clients"[[:space:]]*:/ { in_clients = 1 }
        in_clients && !in_object && /{/ { in_object = 1; depth = 1; next }
        in_object {
            line = $0
            if (value_type == "string") {
                pattern = "^[[:space:]]*\\\"" wanted "\\\"[[:space:]]*:[[:space:]]*\\\""
                if (line ~ pattern) {
                    sub(pattern, "", line)
                    sub("\\\"[[:space:]]*,?[[:space:]]*$", "", line)
                    print line
                    exit
                }
            } else {
                pattern = "^[[:space:]]*\\\"" wanted "\\\"[[:space:]]*:[[:space:]]*"
                if (line ~ pattern) {
                    sub(pattern, "", line)
                    sub("[[:space:],]*$", "", line)
                    print line
                    exit
                }
            }

            open_line = $0
            close_line = $0
            opens = gsub(/{/, "", open_line)
            closes = gsub(/}/, "", close_line)
            depth += opens - closes
            if (depth <= 0) {
                exit
            }
        }
    ' "$CONFIG_FILE"
}

select_default_config() {
    if [[ -n "$CONFIG_FILE" ]]; then
        return
    elif [[ -n "${WONIUNOTE_DB_CONFIG:-}" ]]; then
        CONFIG_FILE="$WONIUNOTE_DB_CONFIG"
    elif [[ -f "$PROJECT_DIR/backend_cpp/config.local.json" ]]; then
        CONFIG_FILE="$PROJECT_DIR/backend_cpp/config.local.json"
    else
        CONFIG_FILE="$PROJECT_DIR/backend_cpp/config.json"
    fi
}

load_connection_config() {
    [[ -n "$CONFIG_FILE" ]] || select_default_config
    [[ -f "$CONFIG_FILE" ]] || die "C++ 后端数据库配置不存在: $CONFIG_FILE"

    local config_host config_port config_name config_user config_password
    config_host="$(read_db_client_value host string)"
    config_port="$(read_db_client_value port number)"
    config_name="$(read_db_client_value dbname string)"
    config_user="$(read_db_client_value user string)"
    config_password="$(read_db_client_value passwd string)"

    DB_HOST="${WONIUNOTE_DB_HOST:-$config_host}"
    DB_PORT="${WONIUNOTE_DB_PORT:-$config_port}"
    DB_NAME="${WONIUNOTE_DB_NAME:-$config_name}"
    DB_USER="${WONIUNOTE_DB_USER:-$config_user}"
    if [[ "${WONIUNOTE_DB_PASSWORD+x}" == "x" ]]; then
        DB_PASSWORD="$WONIUNOTE_DB_PASSWORD"
    else
        DB_PASSWORD="$config_password"
        is_placeholder_password "$DB_PASSWORD" && die "配置中的数据库密码是占位符；请设置 WONIUNOTE_DB_PASSWORD 或使用本地配置文件。"
    fi

    [[ -n "$DB_HOST" ]] || die "未读取到数据库主机，请设置 WONIUNOTE_DB_HOST。"
    [[ -n "$DB_PORT" ]] || die "未读取到数据库端口，请设置 WONIUNOTE_DB_PORT。"
    [[ -n "$DB_NAME" ]] || die "未读取到数据库名称，请设置 WONIUNOTE_DB_NAME。"
    [[ -n "$DB_USER" ]] || die "未读取到数据库用户，请设置 WONIUNOTE_DB_USER。"
    [[ "$DB_PORT" =~ ^[0-9]+$ ]] || die "数据库端口必须是数字: $DB_PORT"
    validate_identifier "$DB_NAME" "数据库名称"
}

create_client_defaults_file() {
    local previous_umask
    previous_umask="$(umask)"
    umask 077
    CLIENT_DEFAULTS_FILE="$(mktemp "${TMPDIR:-/tmp}/woniunote-db-transfer.XXXXXX")"
    umask "$previous_umask"

    {
        printf '[client]\n'
        printf 'host=%s\n' "$DB_HOST"
        printf 'port=%s\n' "$DB_PORT"
        printf 'user=%s\n' "$DB_USER"
        printf 'password=%s\n' "$DB_PASSWORD"
    } > "$CLIENT_DEFAULTS_FILE"
    chmod 600 "$CLIENT_DEFAULTS_FILE"
}

mysql_command() {
    "$MYSQL_BIN" --defaults-extra-file="$CLIENT_DEFAULTS_FILE" --protocol=TCP "$@"
}

mysql_scalar() {
    mysql_command --batch --skip-column-names --execute "$1" | tr -d '[:space:]'
}

database_exists() {
    local exists
    exists="$(mysql_scalar "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = '$DB_NAME';")"
    [[ "$exists" == "1" ]]
}

database_table_count() {
    mysql_scalar "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME' AND table_type = 'BASE TABLE';"
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        die "未找到 sha256sum 或 shasum，无法生成或校验备份校验值。"
    fi
}

write_metadata() {
    local archive="$1"
    local table_count="$2"
    local dump_version
    dump_version="$($MYSQLDUMP_BIN --version 2>/dev/null || printf 'unknown')"

    {
        printf 'database=%s\n' "$DB_NAME"
        printf 'host=%s\n' "$DB_HOST"
        printf 'port=%s\n' "$DB_PORT"
        printf 'tables=%s\n' "$table_count"
        printf 'exported_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf 'mysqldump_version=%s\n' "$dump_version"
    } > "${archive}.metadata"
    chmod 600 "${archive}.metadata"
}

read_metadata_value() {
    local metadata="$1"
    local key="$2"
    sed -n -E "s/^${key}=//p" "$metadata" | head -n 1
}

verify_archive_checksum() {
    local archive="$1"
    local checksum_file="${archive}.sha256"

    [[ -f "$checksum_file" ]] || {
        log_info "未发现 SHA-256 校验文件，跳过校验: $checksum_file"
        return
    }

    local expected actual
    expected="$(awk 'NR == 1 {print $1}' "$checksum_file")"
    actual="$(sha256_file "$archive")"
    [[ -n "$expected" && "$expected" == "$actual" ]] || die "备份 SHA-256 校验失败，已拒绝导入: $archive"
    log_info "SHA-256 校验通过"
}

archive_database_name() {
    local archive="$1"
    gzip -cd -- "$archive" | sed -n -E '/^CREATE DATABASE/ s/.*`([^`]+)`.*/\1/p' | sed -n '1p'
}

export_database() {
    local output_dir="$1"
    local timestamp archive table_count checksum

    database_exists || die "数据库不存在，无法导出: $DB_NAME"
    table_count="$(database_table_count)"

    local previous_umask
    previous_umask="$(umask)"
    umask 077
    mkdir -p "$output_dir"
    umask "$previous_umask"

    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    archive="$output_dir/${DB_NAME}_${timestamp}.sql.gz"

    log_info "正在导出 ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}（${table_count} 张表）"
    if ! "$MYSQLDUMP_BIN" \
        --defaults-extra-file="$CLIENT_DEFAULTS_FILE" \
        --protocol=TCP \
        --single-transaction \
        --routines \
        --events \
        --triggers \
        --hex-blob \
        --set-charset \
        --add-drop-table \
        --no-tablespaces \
        --databases "$DB_NAME" | gzip -c > "$archive"; then
        rm -f "$archive"
        die "数据库导出失败，未保留不完整文件。"
    fi
    chmod 600 "$archive"
    gzip -t "$archive" || {
        rm -f "$archive"
        die "导出的压缩文件校验失败，已删除。"
    }

    checksum="$(sha256_file "$archive")"
    printf '%s  %s\n' "$checksum" "$(basename "$archive")" > "${archive}.sha256"
    chmod 600 "${archive}.sha256"
    write_metadata "$archive" "$table_count"

    log_info "导出完成: $archive"
    log_info "校验文件: ${archive}.sha256"
    log_info "元数据: ${archive}.metadata"
}

import_database() {
    local archive="$1"
    local replace_existing="$2"
    local archived_name current_table_count expected_table_count actual_table_count

    [[ -f "$archive" ]] || die "备份文件不存在: $archive"
    gzip -t "$archive" || die "备份不是有效的 gzip 文件: $archive"
    verify_archive_checksum "$archive"

    archived_name="$(archive_database_name "$archive")"
    [[ -n "$archived_name" ]] || die "无法从备份中读取 CREATE DATABASE，文件不是本脚本生成的完整数据库备份。"
    [[ "$archived_name" == "$DB_NAME" ]] || die "备份数据库为 $archived_name，但目标配置为 $DB_NAME；请使用同名目标库配置后再导入。"

    if database_exists; then
        current_table_count="$(database_table_count)"
        if [[ "$current_table_count" != "0" ]]; then
            if [[ "$replace_existing" != "true" ]]; then
                die "目标数据库 $DB_NAME 已有 ${current_table_count} 张表；为防止覆盖数据，请在确认后追加 --replace。"
            fi
            log_info "--replace 已确认：将删除并重建目标数据库 $DB_NAME"
            mysql_command --execute "DROP DATABASE IF EXISTS \`$DB_NAME\`;"
        fi
    fi

    log_info "正在导入备份到 ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    gzip -cd -- "$archive" | mysql_command

    database_exists || die "导入后未找到数据库 $DB_NAME。"
    actual_table_count="$(database_table_count)"
    [[ "$actual_table_count" != "0" ]] || die "导入后数据库中没有数据表。"

    if [[ -f "${archive}.metadata" ]]; then
        expected_table_count="$(read_metadata_value "${archive}.metadata" tables)"
        if [[ "$expected_table_count" =~ ^[0-9]+$ && "$actual_table_count" != "$expected_table_count" ]]; then
            die "导入后表数量不一致：备份元数据为 ${expected_table_count}，实际为 ${actual_table_count}。"
        fi
    fi

    log_info "导入完成，已验证 $actual_table_count 张表。"
}

parse_export_arguments() {
    EXPORT_OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir)
                [[ $# -ge 2 ]] || die "--output-dir 需要目录参数。"
                EXPORT_OUTPUT_DIR="$2"
                shift 2
                ;;
            --config)
                [[ $# -ge 2 ]] || die "--config 需要文件路径。"
                CONFIG_FILE="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                die "export 不支持的参数: $1"
                ;;
        esac
    done
}

parse_import_arguments() {
    IMPORT_ARCHIVE=""
    IMPORT_REPLACE="false"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --replace)
                IMPORT_REPLACE="true"
                shift
                ;;
            --config)
                [[ $# -ge 2 ]] || die "--config 需要文件路径。"
                CONFIG_FILE="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                [[ -z "$IMPORT_ARCHIVE" ]] || die "import 只能接收一个备份文件。"
                IMPORT_ARCHIVE="$1"
                shift
                ;;
        esac
    done
    [[ -n "$IMPORT_ARCHIVE" ]] || die "import 需要指定备份文件。"
}

main() {
    local command="${1:-}"
    case "$command" in
        export)
            shift
            parse_export_arguments "$@"
            ;;
        import)
            shift
            parse_import_arguments "$@"
            ;;
        --help|-h|help|"")
            usage
            [[ -n "$command" ]] && exit 0
            exit 1
            ;;
        *)
            die "未知命令: $command"
            ;;
    esac

    select_default_config
    load_connection_config
    require_command "$MYSQL_BIN"
    require_command gzip
    require_command mktemp
    create_client_defaults_file

    case "$command" in
        export)
            require_command "$MYSQLDUMP_BIN"
            export_database "$EXPORT_OUTPUT_DIR"
            ;;
        import)
            import_database "$IMPORT_ARCHIVE" "$IMPORT_REPLACE"
            ;;
    esac
}

main "$@"
