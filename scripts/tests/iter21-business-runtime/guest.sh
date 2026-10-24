#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

BUSINESS=/var/lib/woniunote-iter21-business
DATA=/var/lib/woniunote-iter21-data
STATE="$BUSINESS/release-state"
CONFIG="$DATA/runtime-config.json"
SERVICE=woniunote
NGINX_SERVICE=nginx
MYSQL_CNF=/root/.config/woniunote-iter21/mysql-client.cnf
API_HOST=yunjinqi.top
NODE_BIN=/opt/woniunote-iter21-node/bin
ORIGINAL="$BUSINESS/original-v2"
ORIGINAL_BIN="$ORIGINAL/backend_cpp/build/woniunote_backend"
ORIGINAL_DIST="$ORIGINAL/frontend/dist"
ORIGINAL_RUNTIME="$BUSINESS/original-v2-runtime"
ORIGINAL_CONFIG="$ORIGINAL_RUNTIME/runtime-config.json"
ORIGINAL_SERVICE=woniunote-iter21-business-original
ORIGINAL_NGINX_SERVICE=woniunote-iter21-business-original-nginx
ORIGINAL_SQL_COMMIT=fefab0570c370bebd796df9c683343805d850d18
ORIGINAL_BIN_SHA=1935a00eda4f4b61e2728637fbe5d170c5ab78b1e3889185367a7a3eeb32021f
# SHA-256 of ordered tab-separated seed rows from ORIGINAL_SQL_COMMIT; MySQL prints SQL NULL as "NULL".
ORIGINAL_CATEGORY_SEED_SHA=033bcd12e448bd305c38a75ef5cc43f255ca6f693bc372f3e5de77023ef39f90
ORIGINAL_CARDCATEGORY_SEED_SHA=6d80a8de88b5c6f9c6347b0b8ce627e14b037f2316bc18c12d3cec0cab30b511
ORIGINAL_ARTICLE_CATEGORY_SEED_SHA=d4a00978abc2bc4b4cf67e32159e202ff1459b4beaf721993d8ad79b91c7460e

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
hash_file() { sha256sum "$1" | awk '{print $1}'; }
valid_label() { [[ "$1" = candidate-2 || "$1" = candidate-3 || "$1" = candidate-4 || "$1" = candidate-5 ]]; }
valid_sha() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }
valid_hash() { [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }
require_root() { [ "$(id -u)" -eq 0 ] || fail "guest helper requires root"; }
require_release_config() {
    [ -f "$CONFIG" ] && [ ! -L "$CONFIG" ] || fail "runtime config is missing or not a regular file"
    [ "$(stat -c '%a' "$CONFIG")" = 600 ] || fail "runtime config mode is not 0600"
}
repo_path() {
    valid_label "$1" || fail "unsupported candidate label"
    printf '%s/%s\n' "$BUSINESS" "$1"
}
verify_repo() {
    local repo="$1" expected="$2" actual
    valid_sha "$expected" || fail "expected source SHA is invalid"
    [ -d "$repo/.git" ] || fail "candidate Git metadata is missing"
    actual="$(git -C "$repo" rev-parse --verify HEAD)"
    [ "$actual" = "$expected" ] || fail "candidate HEAD does not match expected source SHA"
    [ -z "$(git -C "$repo" status --porcelain --untracked-files=all)" ] || fail "candidate source tree is dirty"
    [ -x "$repo/scripts/deploy_release.sh" ] || fail "release manager is missing or not executable"
}
current_source_sha() {
    local release
    [ -L "$STATE/current" ] || return 1
    release="$(readlink -f "$STATE/current")"
    [ -f "$release/source.sha" ] || return 1
    cat "$release/source.sha"
}
rollback_source_sha() {
    local release
    [ -L "$STATE/rollback" ] || return 1
    release="$(readlink -f "$STATE/rollback")"
    [ -f "$release/source.sha" ] || return 1
    cat "$release/source.sha"
}
rollback_manager_repo_for_sha() {
    local expected_sha="$1" candidate repo matched=""
    valid_sha "$expected_sha" || fail "rollback current source SHA is invalid"
    for candidate in candidate-2 candidate-3 candidate-4 candidate-5; do
        repo="$(repo_path "$candidate")"
        if [ -d "$repo/.git" ] && [ "$(git -C "$repo" rev-parse --verify HEAD)" = "$expected_sha" ]; then
            [ -z "$matched" ] || fail "current source SHA matches multiple candidate repositories; refusing implicit selection"
            verify_repo "$repo" "$expected_sha"
            matched="$repo"
        fi
    done
    [ -n "$matched" ] || fail "current source SHA does not match an explicitly staged candidate repository"
    printf '%s\n' "$matched"
}
listener_pids() {
    ss -H -ltnp 'sport = :5173' 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u
}
assert_single_service_owner() {
    local expected_sha="$1" main_pid pids listener_pid actual_sha
    systemctl is-active --quiet "$SERVICE" || fail "$SERVICE service is not active"
    main_pid="$(systemctl show -p MainPID --value "$SERVICE")"
    [[ "$main_pid" =~ ^[1-9][0-9]*$ ]] || fail "$SERVICE has no valid MainPID"
    pids="$(listener_pids)"
    [ -n "$pids" ] || fail "port 5173 has no listener"
    [ "$(printf '%s\n' "$pids" | wc -l | tr -d ' ')" = 1 ] || fail "port 5173 has multiple listener processes"
    listener_pid="$pids"
    [ "$listener_pid" = "$main_pid" ] || fail "port 5173 listener is not the systemd MainPID"
    [ -r "/proc/$listener_pid/exe" ] || fail "cannot inspect listener executable"
    actual_sha="$(hash_file "/proc/$listener_pid/exe")"
    [ "$actual_sha" = "$expected_sha" ] || fail "listener executable SHA does not match expected owned binary"
    printf 'service_main_pid=%s\n' "$main_pid"
    printf 'listener_pid=%s\n' "$listener_pid"
    printf 'listener_binary_sha256=%s\n' "$actual_sha"
}
original_listener_pids() {
    ss -H -ltnp 'sport = :5173' 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u
}
assert_original_service_owner() {
    local expected_sha="$1" main_pid pids actual_sha
    systemctl is-active --quiet "$ORIGINAL_SERVICE.service" || fail "$ORIGINAL_SERVICE.service is not active"
    main_pid="$(systemctl show -p MainPID --value "$ORIGINAL_SERVICE.service")"
    [[ "$main_pid" =~ ^[1-9][0-9]*$ ]] || fail "original-v2 service has no valid MainPID"
    pids="$(original_listener_pids)"
    [ -n "$pids" ] || fail "original-v2 backend port 5173 has no listener"
    [ "$(printf '%s\n' "$pids" | wc -l | tr -d ' ')" = 1 ] || \
        fail "original-v2 backend port 5173 has multiple listener processes"
    [ "$pids" = "$main_pid" ] || fail "original-v2 listener is not the dedicated systemd MainPID"
    [ -r "/proc/$main_pid/exe" ] || fail "cannot inspect original-v2 listener executable"
    actual_sha="$(hash_file "/proc/$main_pid/exe")"
    [ "$actual_sha" = "$expected_sha" ] || fail "original-v2 listener SHA differs from expected pinned binary"
    printf 'original_service_main_pid=%s\n' "$main_pid"
    printf 'original_listener_pid=%s\n' "$pids"
    printf 'original_listener_binary_sha256=%s\n' "$actual_sha"
}
assert_original_nginx_owner() {
    local main_pid cgroup pids pid pid_cgroup actual_sha nginx_sha
    systemctl is-active --quiet "$ORIGINAL_NGINX_SERVICE.service" || fail "$ORIGINAL_NGINX_SERVICE.service is not active"
    main_pid="$(systemctl show -p MainPID --value "$ORIGINAL_NGINX_SERVICE.service")"
    [[ "$main_pid" =~ ^[1-9][0-9]*$ ]] || fail "original-v2 Nginx service has no valid MainPID"
    nginx_sha="$(hash_file /usr/sbin/nginx)"
    [ "$(hash_file "/proc/$main_pid/exe")" = "$nginx_sha" ] || \
        fail "original-v2 Nginx MainPID is not the system Nginx binary"
    cgroup="$(systemctl show -p ControlGroup --value "$ORIGINAL_NGINX_SERVICE.service")"
    [ -n "$cgroup" ] || fail "original-v2 Nginx systemd cgroup is unavailable"
    pids="$(ss -H -ltnp 'sport = :8443' 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u)"
    [ -n "$pids" ] || fail "original-v2 HTTPS port 8443 has no listener"
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        pid_cgroup="$(awk -F: '$1 == "0" {print $3}' "/proc/$pid/cgroup" 2>/dev/null || true)"
        [[ "$pid_cgroup" = "$cgroup" || "$pid_cgroup" = "$cgroup"/* ]] || \
            fail "port 8443 listener PID $pid is outside the dedicated Nginx systemd cgroup"
        actual_sha="$(hash_file "/proc/$pid/exe")"
        [ "$actual_sha" = "$nginx_sha" ] || \
            fail "port 8443 listener PID $pid is not the system Nginx binary"
    done <<< "$pids"
    printf 'original_nginx_main_pid=%s\n' "$main_pid"
    printf 'original_nginx_listener_pids=%s\n' "$(printf '%s' "$pids" | tr '\n' ',')"
    printf 'original_nginx_binary_sha256=%s\n' "$nginx_sha"
}
ensure_original_data_upload_root() {
    [ -d "$DATA" ] && [ ! -L "$DATA" ] && [ "$(stat -c '%u' "$DATA")" = 0 ] || \
        fail "persistent data root is missing, symlinked, or not owned by root"
    if [ -e "$DATA/uploads" ] || [ -L "$DATA/uploads" ]; then
        [ -d "$DATA/uploads" ] && [ ! -L "$DATA/uploads" ] && \
            [ "$(stat -c '%u' "$DATA/uploads")" = 0 ] || \
            fail "persistent uploads target is not a root-owned real directory"
    else
        install -d -o root -g root -m 0700 "$DATA/uploads"
    fi
}
preflight_original_upload_layout() {
    local data_target higher_priority runtime_upload
    [ -d "$BUSINESS" ] && [ ! -L "$BUSINESS" ] && [ "$(stat -c '%u' "$BUSINESS")" = 0 ] || \
        fail "D04 business root is missing, symlinked, or not owned by root"
    [ -d "$ORIGINAL_RUNTIME" ] && [ ! -L "$ORIGINAL_RUNTIME" ] && \
        [ "$(stat -c '%u' "$ORIGINAL_RUNTIME")" = 0 ] && \
        [ "$(stat -c '%a' "$ORIGINAL_RUNTIME")" = 700 ] || \
        fail "original runtime is not the expected root-owned 0700 directory"
    [ -d "$DATA/uploads" ] && [ ! -L "$DATA/uploads" ] && \
        [ "$(stat -c '%u' "$DATA/uploads")" = 0 ] || \
        fail "persistent uploads target is not a root-owned real directory"
    data_target="$(readlink -f -- "$DATA/uploads")"
    [ -n "$data_target" ] || fail "cannot resolve the persistent uploads target"

    # UEditor checks ../uploads before ./uploads from ORIGINAL_RUNTIME.
    higher_priority="$BUSINESS/uploads"
    if [ -e "$higher_priority" ] || [ -L "$higher_priority" ]; then
        [ -L "$higher_priority" ] || \
            fail "higher-priority ../uploads exists as data; refusing to shadow or move it"
        [ "$(readlink -f -- "$higher_priority" 2>/dev/null || true)" = "$data_target" ] || \
            fail "higher-priority ../uploads points somewhere other than persistent uploads"
        printf 'original_upload_higher_priority_candidate=verified_persistent_target\n'
    else
        printf 'original_upload_higher_priority_candidate=absent\n'
    fi

    runtime_upload="$ORIGINAL_RUNTIME/uploads"
    if [ -e "$runtime_upload" ] || [ -L "$runtime_upload" ]; then
        [ -L "$runtime_upload" ] && [ "$(readlink -- "$runtime_upload")" = "$DATA/uploads" ] && \
            [ "$(stat -c '%u' -- "$runtime_upload")" = 0 ] && \
            [ "$(readlink -f -- "$runtime_upload" 2>/dev/null || true)" = "$data_target" ] || \
            fail "original runtime uploads path is not the run-owned persistent-data symlink"
    fi
}
ensure_original_runtime_upload_link() {
    local runtime_upload="$ORIGINAL_RUNTIME/uploads"
    preflight_original_upload_layout
    if [ ! -e "$runtime_upload" ] && [ ! -L "$runtime_upload" ]; then
        ln -s -- "$DATA/uploads" "$runtime_upload" || \
            fail "could not create the original runtime persistent-upload symlink"
        printf 'original_runtime_upload_link=created\n'
    else
        printf 'original_runtime_upload_link=already_correct\n'
    fi
    printf 'original_runtime_upload_link_target=%s\n' "$DATA/uploads"
}
repair_original_upload_config() {
    /usr/bin/python3 - "$ORIGINAL_CONFIG" "$DATA/uploads" "$DATA/uploads/uploads" <<'PY'
import hashlib
import json
import os
import stat
import tempfile
import sys

target, expected_document_root, expected_upload_path = sys.argv[1:]
if os.path.islink(target):
    raise SystemExit("original runtime config must not be a symlink")
original_stat = os.stat(target, follow_symlinks=False)
if not stat.S_ISREG(original_stat.st_mode) or original_stat.st_uid != 0:
    raise SystemExit("original runtime config is not a root-owned regular file")
if stat.S_IMODE(original_stat.st_mode) != 0o600:
    raise SystemExit("original runtime config mode is not 0600")
with open(target, "r", encoding="utf-8") as stream:
    config = json.load(stream)
if not isinstance(config, dict):
    raise SystemExit("original runtime config is not a JSON object")
app = config.get("app")
if not isinstance(app, dict):
    raise SystemExit("original runtime config has no app object")
custom = config.get("custom_config")
if not isinstance(custom, dict) or custom.get("app_name") != "WoniuNote original-v2 Iteration 21 rehearsal":
    raise SystemExit("runtime config is not the dedicated original-v2 rehearsal config")
listeners = config.get("listeners")
if not isinstance(listeners, list) or len(listeners) != 1:
    raise SystemExit("original runtime config has an unexpected listener set")
if listeners[0].get("address") != "127.0.0.1" or listeners[0].get("port") != 5173:
    raise SystemExit("original runtime config does not own the expected loopback listener")
if app.get("document_root") != expected_document_root:
    raise SystemExit("original runtime config document_root is unexpected")
if app.get("upload_path") not in {expected_document_root, expected_upload_path}:
    raise SystemExit("original runtime config upload_path is unexpected")

def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def app_field_spans(text):
    spans = {}

    def skip_space(position):
        while position < len(text) and text[position] in " \t\r\n":
            position += 1
        return position

    def scan_string(position):
        if position >= len(text) or text[position] != '"':
            raise ValueError("expected JSON string")
        position += 1
        while position < len(text):
            if text[position] == "\\":
                position += 2
            elif text[position] == '"':
                return position + 1
            else:
                position += 1
        raise ValueError("unterminated JSON string")

    def scan_value(position, path):
        position = skip_space(position)
        if position >= len(text):
            raise ValueError("missing JSON value")
        if text[position] == '"':
            return scan_string(position)
        if text[position] == "{":
            position = skip_space(position + 1)
            if position < len(text) and text[position] == "}":
                return position + 1
            while True:
                key_start = position
                key_end = scan_string(key_start)
                key = json.loads(text[key_start:key_end])
                position = skip_space(key_end)
                if position >= len(text) or text[position] != ":":
                    raise ValueError("invalid JSON object separator")
                value_start = skip_space(position + 1)
                value_end = scan_value(value_start, path + (key,))
                if path == ("app",) and key in {"document_root", "upload_path"}:
                    if key in spans:
                        raise ValueError(f"duplicate app field: {key}")
                    spans[key] = (value_start, value_end)
                position = skip_space(value_end)
                if position < len(text) and text[position] == ",":
                    position = skip_space(position + 1)
                    continue
                if position < len(text) and text[position] == "}":
                    return position + 1
                raise ValueError("invalid JSON object terminator")
        if text[position] == "[":
            position = skip_space(position + 1)
            if position < len(text) and text[position] == "]":
                return position + 1
            item_index = 0
            while True:
                value_end = scan_value(position, path + (item_index,))
                position = skip_space(value_end)
                if position < len(text) and text[position] == ",":
                    position = skip_space(position + 1)
                    item_index += 1
                    continue
                if position < len(text) and text[position] == "]":
                    return position + 1
                raise ValueError("invalid JSON array terminator")
        end = position
        while end < len(text) and text[end] not in ",]} \t\r\n":
            end += 1
        if end == position:
            raise ValueError("invalid JSON primitive")
        return end

    end = scan_value(0, ())
    if text[skip_space(end):]:
        raise ValueError("trailing content after JSON config")
    return spans

with open(target, "r", encoding="utf-8") as stream:
    original_text = stream.read()
spans = app_field_spans(original_text)
if set(spans) != {"document_root", "upload_path"}:
    raise SystemExit("original runtime config app path fields are missing or ambiguous")
for field, (start, end) in spans.items():
    if json.loads(original_text[start:end]) != app[field]:
        raise SystemExit(f"original runtime config {field} changed during upload-layout repair")

before_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
changed = app["upload_path"] != expected_upload_path
if changed:
    replacements = {
        "document_root": json.dumps(expected_document_root, ensure_ascii=False),
        "upload_path": json.dumps(expected_upload_path, ensure_ascii=False),
    }
    repaired_text = original_text
    for field, (start, end) in sorted(spans.items(), key=lambda item: item[1][0], reverse=True):
        if not isinstance(json.loads(original_text[start:end]), str):
            raise SystemExit(f"original runtime config {field} is not a JSON string")
        repaired_text = repaired_text[:start] + replacements[field] + repaired_text[end:]
    fd, temp_path = tempfile.mkstemp(prefix=".runtime-config-upload-fix.", dir=os.path.dirname(target))
    try:
        os.fchown(fd, original_stat.st_uid, original_stat.st_gid)
        os.fchmod(fd, stat.S_IMODE(original_stat.st_mode))
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(repaired_text)
            stream.flush()
            os.fsync(stream.fileno())
        current_stat = os.stat(target, follow_symlinks=False)
        if (current_stat.st_dev, current_stat.st_ino) != (original_stat.st_dev, original_stat.st_ino):
            raise SystemExit("original runtime config changed during upload-layout repair")
        if file_hash(target) != before_hash:
            raise SystemExit("original runtime config contents changed during upload-layout repair")
        os.replace(temp_path, target)
        directory_fd = os.open(os.path.dirname(target), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

after_hash = file_hash(target)
print(f"original_runtime_upload_config={'updated' if changed else 'already_correct'}")
print(f"original_runtime_config_before_sha256={before_hash}")
print(f"original_runtime_config_after_sha256={after_hash}")
print(f"original_app_document_root={expected_document_root}")
print(f"original_app_upload_path={expected_upload_path}")
PY
}
repair_original_upload_layout() {
    local expected_unit="/etc/systemd/system/$ORIGINAL_SERVICE.service" state nginx_state main_pid fragment working
    [ -d "$ORIGINAL" ] && [ ! -L "$ORIGINAL" ] || fail "original-v2 application directory is missing or symlinked"
    [ -f "$ORIGINAL_BIN" ] && [ ! -L "$ORIGINAL_BIN" ] && [ -x "$ORIGINAL_BIN" ] && \
        [ "$(hash_file "$ORIGINAL_BIN")" = "$ORIGINAL_BIN_SHA" ] || \
        fail "original-v2 binary does not match the pinned full SHA-256"
    [ -f "$ORIGINAL_CONFIG" ] && [ ! -L "$ORIGINAL_CONFIG" ] && \
        [ "$(stat -c '%u:%a' "$ORIGINAL_CONFIG")" = 0:600 ] || \
        fail "original-v2 runtime config is not a root-owned regular 0600 file"
    [ -f "$expected_unit" ] && [ ! -L "$expected_unit" ] && \
        [ "$(stat -c '%u' "$expected_unit")" = 0 ] || \
        fail "dedicated original-v2 systemd unit is missing or not root-owned"
    fragment="$(systemctl show -p FragmentPath --value "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    working="$(systemctl show -p WorkingDirectory --value "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    [ "$fragment" = "$expected_unit" ] && [ "$working" = "$ORIGINAL_RUNTIME" ] || \
        fail "loaded original-v2 systemd unit does not own the expected runtime directory"
    grep -Fxq "ExecStart=/usr/bin/env WONIUNOTE_ENV=production $ORIGINAL_BIN $ORIGINAL_CONFIG" "$expected_unit" || \
        fail "dedicated original-v2 systemd unit does not start the pinned binary and config"
    grep -Fxq "WorkingDirectory=$ORIGINAL_RUNTIME" "$expected_unit" || \
        fail "dedicated original-v2 systemd unit has an unexpected working directory"
    state="$(systemctl is-active "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    [ "$state" = inactive ] || \
        fail "original-v2 backend must be explicitly stopped and inactive before upload-layout repair (state=$state)"
    nginx_state="$(systemctl is-active "$ORIGINAL_NGINX_SERVICE.service" 2>/dev/null || true)"
    [ "$nginx_state" = inactive ] || \
        fail "dedicated original-v2 HTTPS unit must be inactive before upload-layout repair (state=$nginx_state)"
    main_pid="$(systemctl show -p MainPID --value "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    [ "$main_pid" = 0 ] || fail "dedicated original-v2 backend still has a systemd MainPID"
    assert_no_listener
    [ -z "$(ss -H -ltn 'sport = :8443' 2>/dev/null)" ] || \
        fail "dedicated original-v2 HTTPS port 8443 remains bound after explicit stop"
    preflight_original_upload_layout
    ensure_original_runtime_upload_link
    repair_original_upload_config
    printf 'original_service_state_before_repair=%s\n' "${state:-unknown}"
    printf 'original_nginx_service_state_before_repair=%s\n' "${nginx_state:-unknown}"
    printf 'original_service_action=NOT_RUN (repair does not stop, start, reload, or restart services)\n'
    printf 'original_upload_business_files=moved=NO copied=NO\n'
}
assert_no_listener() {
    local pids
    pids="$(listener_pids)"
    [ -z "$pids" ] || fail "port 5173 remains occupied by PID(s): $pids"
}
assert_handoff() {
    [ "${WONIUNOTE_ITER21_D04_HANDOFF:-}" = received ] || fail "D04 VM handoff marker missing"
}
with_remote_lock() {
    exec 9>/run/lock/woniunote-iter21-business-runtime.lock
    flock -n 9 || fail "another D04 business runtime operation holds the VM lock"
}
safe_api_probe() {
    local body http bytes digest
    body="$(mktemp /run/woniunote-iter21-d04-api.XXXXXX)"
    chmod 0600 "$body"
    http="$(curl --silent --show-error --max-time 5 --max-redirs 0 -k \
        --resolve "$API_HOST:443:127.0.0.1" -o "$body" -w '%{http_code}' \
        "https://$API_HOST/api/articles/types")" || fail "read-only category API request failed"
    [ "$http" = 200 ] || fail "read-only category API returned HTTP $http"
    bytes="$(wc -c < "$body" | tr -d ' ')"
    digest="$(hash_file "$body")"
    /usr/bin/python3 - "$body" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as stream:
    response = json.load(stream)
if response.get("code") != 200:
    raise SystemExit("category API envelope code is not 200")
data = response.get("data")
flat = data.get("flat") if isinstance(data, dict) else None
if not isinstance(flat, list) or not flat:
    raise SystemExit("category API returned no visible categories")
print(f"api_category_count={len(flat)}")
PY
    rm -f "$body"
    printf 'api_category_http=%s\n' "$http"
    printf 'api_category_body_bytes=%s\n' "$bytes"
    printf 'api_category_body_sha256=%s\n' "$digest"
}
capture_schema() {
    local selected
    if [ ! -f "$MYSQL_CNF" ] || [ "$(stat -c '%a' "$MYSQL_CNF")" != 600 ]; then
        printf 'database_schema=NOT_RUN (root-only mysql client file missing or not 0600)\n'
        return 0
    fi
    selected="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT COALESCE(DATABASE(), "")' 2>/dev/null)" || {
        printf 'database_schema=NOT_RUN (credentialed read-only connection failed)\n'
        return 0
    }
    if [ -z "$selected" ]; then
        printf 'database_schema=NOT_RUN (mysql client config selects no schema)\n'
        return 0
    fi
    [[ "$selected" =~ ^[A-Za-z0-9_]+$ ]] || fail "selected database name has an unexpected format"
    printf 'database_selected_schema=%s\n' "$selected"
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
        -e 'SELECT TABLE_NAME, ENGINE, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME' \
        | while IFS=$'\t' read -r table engine rows; do
            printf 'database_table=%s engine=%s estimated_rows=%s\n' "$table" "$engine" "$rows"
        done
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
        -e 'SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION' \
        | while IFS=$'\t' read -r table column type nullable; do
            printf 'database_column=%s.%s type=%s nullable=%s\n' "$table" "$column" "$type" "$nullable"
        done
}
original_schema_identity() {
    local identity
    [ -f "$MYSQL_CNF" ] && [ ! -L "$MYSQL_CNF" ] || fail "root-only MySQL client file is missing"
    [ "$(stat -c '%a' "$MYSQL_CNF")" = 600 ] || fail "MySQL client file mode is not 0600"
    identity="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT DATABASE(), SUBSTRING_INDEX(CURRENT_USER(), "@", 1)' 2>/dev/null)" || \
        fail "read-only MySQL identity query failed"
    IFS=$'\t' read -r ORIGINAL_SCHEMA ORIGINAL_DB_USER <<< "$identity"
    [[ "$ORIGINAL_SCHEMA" =~ ^woniunote_iter21_[A-Za-z0-9_]+$ ]] || \
        fail "selected database is not an isolated Iteration 21 schema"
    [[ "$ORIGINAL_DB_USER" =~ ^wni21_[A-Za-z0-9_]+$ ]] || \
        fail "database identity is not the dedicated Iteration 21 user"
    printf 'database_schema=%s\n' "$ORIGINAL_SCHEMA"
    printf 'database_user=%s\n' "$ORIGINAL_DB_USER"
}
original_schema_summary() {
    local table
    printf 'schema_summary_format=iter21-d04-schema-v1\n'
    original_schema_identity
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
        -e 'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME' \
        | while IFS=$'\t' read -r table engine; do
            local rows
            rows="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
                -e "SELECT COUNT(*) FROM \`$table\`")"
            printf 'table=%s engine=%s exact_rows=%s\n' "$table" "$engine" "$rows"
        done
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
        -e 'SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION' \
        | while IFS=$'\t' read -r table column type nullable; do
            printf 'column=%s.%s type=%s nullable=%s\n' "$table" "$column" "$type" "$nullable"
        done
}
original_expected_tables() {
    cat <<'EOF'
article
article_category
card
cardcategory
category
comment
comment_votes
credit
favorite
item
math_training_records
math_training_wrong_answers
users
EOF
}
original_business_tables() {
    cat <<'EOF'
users
article
comment
comment_votes
favorite
credit
card
item
math_training_records
math_training_wrong_answers
EOF
}
original_seed_digest() {
    local table="$1" query
    case "$table" in
        category) query='SELECT id, name FROM category ORDER BY id' ;;
        cardcategory) query='SELECT id, name FROM cardcategory ORDER BY id' ;;
        article_category) query='SELECT id, parent_id, name, sort_order, visible FROM article_category ORDER BY id' ;;
        *) fail "unsupported original seed table: $table" ;;
    esac
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names -e "$query" | sha256sum | awk '{print $1}'
}
validate_original_seed_baseline() {
    local table expected actual row_count
    for table in category cardcategory article_category; do
        case "$table" in
            category) expected="$ORIGINAL_CATEGORY_SEED_SHA" ;;
            cardcategory) expected="$ORIGINAL_CARDCATEGORY_SEED_SHA" ;;
            article_category) expected="$ORIGINAL_ARTICLE_CATEGORY_SEED_SHA" ;;
        esac
        actual="$(original_seed_digest "$table")"
        row_count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e "SELECT COUNT(*) FROM \`$table\`")"
        if [ "$actual" = "$expected" ]; then
            printf 'seed_table=%s exact_rows=%s content_sha256=%s result=PASS\n' "$table" "$row_count" "$actual"
        else
            printf 'seed_table=%s exact_rows=%s expected_sha256=%s actual_sha256=%s result=GAP\n' \
                "$table" "$row_count" "$expected" "$actual"
            fail "original-v2 seed contents differ from pinned SQL in $table"
        fi
    done
}
audit_original_schema() {
    local selected_schema schema_names schema_count actual_tables expected_tables table count
    local math_type math_nullable marker reset_safe=1
    printf 'original_schema_audit_format=iter21-d04-original-schema-v1\n'
    original_schema_identity
    selected_schema="$ORIGINAL_SCHEMA"
    schema_names="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE LEFT(SCHEMA_NAME, 17) = "woniunote_iter21_" ORDER BY SCHEMA_NAME')"
    schema_count="$(printf '%s\n' "$schema_names" | sed '/^$/d' | wc -l | tr -d ' ')"
    printf 'd04_prefixed_schema_count=%s\n' "$schema_count"
    if [ "$schema_count" = 1 ] && [ "$schema_names" = "$selected_schema" ]; then
        printf 'selected_schema_is_only_d04_schema=PASS\n'
    else
        printf 'selected_schema_is_only_d04_schema=GAP\n'
        reset_safe=0
    fi
    actual_tables="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME')"
    expected_tables="$(original_expected_tables)"
    if [ "$actual_tables" = "$expected_tables" ]; then
        printf 'original_table_set=PASS\n'
    else
        printf 'original_table_set=GAP (unexpected or missing tables; refusing schema reset)\n'
        return 1
    fi
    for table in users article comment comment_votes favorite credit card item math_training_records math_training_wrong_answers; do
        count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e "SELECT COUNT(*) FROM \`$table\`")"
        printf 'business_table=%s exact_rows=%s\n' "$table" "$count"
        [ "$count" = 0 ] || reset_safe=0
    done
    validate_original_seed_baseline
    math_type="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    math_nullable="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    printf 'math_training_wrong_answers.user_answer=%s nullable=%s\n' "$math_type" "$math_nullable"
    [ "$math_type" = int ] && [ "$math_nullable" = NO ] || \
        printf 'original_v2_math_column_baseline=GAP (the pinned SQL reset is required before UI rehearsal)\n'
    marker="$ORIGINAL_RUNTIME/schema-baseline.meta"
    if [ -f "$marker" ] && [ ! -L "$marker" ] && grep -qx 'schema_baseline=original-v2' "$marker"; then
        printf 'schema_baseline_marker=present_original_v2\n'
    else
        printf 'schema_baseline_marker=not_present\n'
    fi
    if [ "$reset_safe" = 1 ]; then
        printf 'schema_reset_preconditions=PASS (only the selected Iteration 21 schema; exact original seeds; every business table empty)\n'
        return 0
    fi
    printf 'schema_reset_preconditions=GAP (no schema reset or original UI startup allowed)\n'
    return 1
}
validate_original_schema_baseline() {
    local actual expected user_answer_type user_answer_nullable category_rows card_rows article_category_rows
    actual="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME')"
    expected="$(original_expected_tables)"
    [ "$actual" = "$expected" ] || fail "isolated schema table set differs from pinned original-v2 baseline"
    user_answer_type="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    user_answer_nullable="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    [ "$user_answer_type" = int ] && [ "$user_answer_nullable" = NO ] || \
        fail "math_training_wrong_answers.user_answer is not original-v2 INT NOT NULL"
    category_rows="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM category')"
    card_rows="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM cardcategory')"
    article_category_rows="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM article_category')"
    [ "$category_rows" = 10 ] && [ "$card_rows" = 19 ] && [ "$article_category_rows" = 70 ] || \
        fail "original-v2 category seed row counts differ from pinned SQL"
    validate_original_seed_baseline
    printf 'schema_baseline=PASS\n'
    printf 'math_training_wrong_answers.user_answer=%s nullable=%s (pinned original-v2 SQL definition)\n' \
        "$user_answer_type" "$user_answer_nullable"
    printf 'category_seed_rows=category:%s cardcategory:%s article_category:%s\n' \
        "$category_rows" "$card_rows" "$article_category_rows"
}
restore_original_business_schema() {
    local schema_backup="$1"
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names <<'SQL' >/dev/null
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS `math_training_wrong_answers`, `math_training_records`, `comment_votes`, `comment`, `favorite`, `credit`, `article`, `item`, `card`, `users`;
SET FOREIGN_KEY_CHECKS=1;
SQL
    mysql --defaults-extra-file="$MYSQL_CNF" "$ORIGINAL_SCHEMA" < "$schema_backup"
}
install_exact_file() {
    local source="$1" target="$2" mode="$3"
    if [ -e "$target" ] || [ -L "$target" ]; then
        [ -f "$target" ] && [ ! -L "$target" ] && cmp -s "$source" "$target" || \
            fail "owned runtime file already exists with unexpected contents: $target"
        rm -f "$source"
    else
        install -m "$mode" "$source" "$target"
        rm -f "$source"
    fi
}
probe_formal_hooks_with_env() (
    set -Eeuo pipefail
    local probe_dir probe_config probe_log probe_pid health challenge_status auth_status
    probe_dir="$(mktemp -d /run/woniunote-iter21-d04-hooks.XXXXXX)"
    chmod 0700 "$probe_dir"
    cleanup_probe() {
        if [ -n "${probe_pid:-}" ] && kill -0 "$probe_pid" 2>/dev/null; then
            kill -TERM "$probe_pid" 2>/dev/null || true
            for _ in $(seq 1 30); do
                kill -0 "$probe_pid" 2>/dev/null || break
                sleep 0.2
            done
            kill -KILL "$probe_pid" 2>/dev/null || true
            wait "$probe_pid" 2>/dev/null || true
        fi
        rm -rf "$probe_dir"
    }
    trap cleanup_probe EXIT
    if strings "$ORIGINAL_BIN" | grep -Fq '/api/captcha/test/challenge' || \
       strings "$ORIGINAL_BIN" | grep -Fq '/api/auth/test/empty-transaction'; then
        printf 'formal_hooks_negative=NOT_RUN (a test-route literal exists; refusing to invoke it)\n'
        return 0
    fi
    /usr/bin/python3 - "$ORIGINAL_CONFIG" "$probe_dir/config.json" "$probe_dir/logs" <<'PY'
import json
import os
import sys

source, target, log_path = sys.argv[1:]
with open(source, "r", encoding="utf-8") as stream:
    config = json.load(stream)
config["listeners"] = [{"address": "127.0.0.1", "port": 5174, "https": False}]
config.setdefault("app", {}).setdefault("log", {})["log_path"] = log_path
config["app"]["log"]["logfile_base_name"] = "hook-probe"
os.makedirs(log_path, mode=0o700, exist_ok=True)
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    json.dump(config, stream, ensure_ascii=False, separators=(",", ":"))
    stream.write("\n")
PY
    if ss -H -ltn 'sport = :5174' | grep -q .; then
        printf 'formal_hooks_negative=NOT_RUN (probe port 5174 is already occupied)\n'
        return 0
    fi
    WONIUNOTE_ENABLE_TEST_CHALLENGE=ON WONIUNOTE_ENABLE_TEST_AUTH_FAULTS=ON \
        "$ORIGINAL_BIN" "$probe_dir/config.json" > "$probe_dir/backend.log" 2>&1 &
    probe_pid=$!
    health=000
    for _ in $(seq 1 40); do
        if ! kill -0 "$probe_pid" 2>/dev/null; then break; fi
        health="$(curl --silent --max-time 1 -o /dev/null -w '%{http_code}' \
            http://127.0.0.1:5174/health 2>/dev/null || true)"
        [ "$health" = 200 ] && break
        sleep 0.25
    done
    if [ "$health" != 200 ]; then
        printf 'formal_hooks_negative=NOT_RUN (env-injected probe backend health=%s)\n' "$health"
        return 0
    fi
    challenge_status="$(curl --silent --max-time 3 -o "$probe_dir/challenge.body" -w '%{http_code}' \
        -X POST -H 'Content-Type: application/json' --data '{}' \
        http://127.0.0.1:5174/api/captcha/test/challenge 2>/dev/null || true)"
    auth_status="$(curl --silent --max-time 3 -o "$probe_dir/auth.body" -w '%{http_code}' \
        -X POST -H 'Content-Type: application/json' --data '{}' \
        http://127.0.0.1:5174/api/auth/test/empty-transaction 2>/dev/null || true)"
    printf 'formal_hook_env_injection=WONIUNOTE_ENABLE_TEST_CHALLENGE:ON,WONIUNOTE_ENABLE_TEST_AUTH_FAULTS:ON\n'
    printf 'formal_hook_challenge_http=%s\n' "$challenge_status"
    printf 'formal_hook_auth_transaction_http=%s\n' "$auth_status"
    if [ "$challenge_status" = 404 ] && [ "$auth_status" = 404 ]; then
        printf 'formal_hooks_negative=PASS (both test routes absent under environment injection)\n'
    else
        printf 'formal_hooks_negative=GAP (expected HTTP 404 for both test routes)\n'
    fi
)
rebuild_original_schema() (
    set -Eeuo pipefail
    local source_dir="$1" archive="$2" before_summary before_hash schema_backup schema_backup_tmp mysql_dump_cnf archive_source temp_extract
    local actual_tables expected_tables table count category_count card_count article_category_count
    local math_type math_nullable source_manifest after_summary after_hash
    local schema_rebuild_started=0 schema_rebuild_complete=0
    recover_schema_rebuild() {
        local rc=$?
        trap - EXIT
        if [ "$schema_rebuild_started" = 1 ] && [ "$schema_rebuild_complete" != 1 ]; then
            if restore_original_business_schema "$schema_backup"; then
                printf 'schema_rebuild_recovery=PASS (pre-reset empty business-table DDL restored)\n' >&2
            else
                printf 'schema_rebuild_recovery=FAILED; preserve the owned schema and inspect %s\n' "$schema_backup" >&2
                rc=1
            fi
        fi
        [ -z "${schema_backup_tmp:-}" ] || rm -f -- "$schema_backup_tmp"
        [ -z "${mysql_dump_cnf:-}" ] || rm -f -- "$mysql_dump_cnf"
        exit "$rc"
    }
    trap recover_schema_rebuild EXIT
    original_schema_identity >/dev/null
    local baseline_marker="$ORIGINAL_RUNTIME/schema-baseline.meta"
    if [ -e "$baseline_marker" ] || [ -L "$baseline_marker" ]; then
        [ -f "$baseline_marker" ] && [ ! -L "$baseline_marker" ] && \
            [ "$(stat -c '%a' "$baseline_marker")" = 600 ] && \
            [ "$(stat -c '%u' "$baseline_marker")" = 0 ] || \
            fail "existing original-v2 schema marker is not a root-owned regular 0600 file"
        grep -qx 'schema_baseline=original-v2' "$baseline_marker" || fail "existing schema marker has an unexpected baseline"
        grep -qx "sql_commit=$ORIGINAL_SQL_COMMIT" "$baseline_marker" || fail "existing schema marker has an unexpected SQL commit"
        validate_original_schema_baseline
        printf 'schema_rebuild=NOT_RUN (existing baseline marker prevents any later rebuild)\n'
        printf 'schema_baseline_marker=%s\n' "$baseline_marker"
        return 0
    fi
    [ ! -e "$ORIGINAL_CONFIG" ] || fail "runtime config exists without a baseline marker; refusing schema reset"
    audit_original_schema
    actual_tables="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME')"
    expected_tables="$(original_expected_tables)"
    [ "$actual_tables" = "$expected_tables" ] || fail "D04 schema contains unexpected or missing tables; no data changed"
    for table in users article comment comment_votes favorite credit card item math_training_records math_training_wrong_answers; do
        count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e "SELECT COUNT(*) FROM \`$table\`")"
        [ "$count" = 0 ] || fail "business table $table contains $count row(s); refusing schema reset"
        printf 'pre_reset_business_rows=%s:%s\n' "$table" "$count"
    done
    category_count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM category')"
    card_count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM cardcategory')"
    article_category_count="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names -e 'SELECT COUNT(*) FROM article_category')"
    [ "$category_count" = 10 ] && [ "$card_count" = 19 ] && [ "$article_category_count" = 70 ] || \
        fail "category seed counts do not match the known D04 initialization; no data changed"
    math_type="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    math_nullable="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
        -e 'SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "math_training_wrong_answers" AND COLUMN_NAME = "user_answer"')"
    printf 'pre_reset_math_user_answer=%s nullable=%s\n' "$math_type" "$math_nullable"
    before_summary="$ORIGINAL_RUNTIME/schema-before.meta"
    original_schema_summary > "$before_summary"
    chmod 0600 "$before_summary"
    before_hash="$(hash_file "$before_summary")"
    schema_backup="$ORIGINAL_RUNTIME/business-schema-before.sql"
    if [ -e "$schema_backup" ] || [ -L "$schema_backup" ]; then
        [ -f "$schema_backup" ] && [ ! -L "$schema_backup" ] && \
            [ "$(stat -c '%u' "$schema_backup")" = 0 ] && [ "$(stat -c '%a' "$schema_backup")" = 600 ] || \
            fail "existing pre-reset schema backup is not a root-owned regular 0600 file"
    fi
    mysql_dump_cnf="$(mktemp "$ORIGINAL_RUNTIME/.mysql-dump-defaults.XXXXXX")"
    schema_backup_tmp="$(mktemp "$ORIGINAL_RUNTIME/.business-schema-before.XXXXXX")"
    chmod 0600 "$mysql_dump_cnf" "$schema_backup_tmp"
    /usr/bin/python3 - "$MYSQL_CNF" "$mysql_dump_cnf" <<'PY'
import configparser
import os
import stat
import sys

source, target = sys.argv[1:]
if os.path.islink(source) or os.path.islink(target):
    raise SystemExit("MySQL defaults files must not be symlinks")
parser = configparser.ConfigParser(interpolation=None)
if not parser.read(source) or "client" not in parser:
    raise SystemExit("root-only MySQL client file lacks a [client] section")
parser["client"].pop("database", None)
info = os.stat(target, follow_symlinks=False)
if not stat.S_ISREG(info.st_mode) or info.st_uid != 0:
    raise SystemExit("temporary mysqldump defaults file is not root-owned and regular")
with open(target, "w", encoding="utf-8") as stream:
    parser.write(stream, space_around_delimiters=True)
os.chmod(target, 0o600)
PY
    mysqldump --defaults-extra-file="$mysql_dump_cnf" --no-data --skip-comments --skip-lock-tables --no-tablespaces \
        "$ORIGINAL_SCHEMA" users article comment comment_votes favorite credit card item \
        math_training_records math_training_wrong_answers > "$schema_backup_tmp"
    chmod 0600 "$schema_backup_tmp"
    [ -s "$schema_backup_tmp" ] || fail "pre-reset DDL backup is empty; no schema changed"
    mv -f -- "$schema_backup_tmp" "$schema_backup"
    schema_backup_tmp=""
    rm -f -- "$mysql_dump_cnf"
    mysql_dump_cnf=""
    chmod 0600 "$schema_backup"
    printf 'pre_reset_ddl_backup_sha256=%s\n' "$(hash_file "$schema_backup")"
    schema_rebuild_started=1
    mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names <<'SQL' >/dev/null
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS `math_training_wrong_answers`, `math_training_records`, `comment_votes`, `comment`, `favorite`, `credit`, `article`, `item`, `card`, `users`;
SET FOREIGN_KEY_CHECKS=1;
SQL
    for name in 01_users.sql 02_article.sql 03_comment.sql 04_favorite.sql 05_credit.sql \
                06_category.sql 07_card_item.sql 08_math_training.sql 09_article_category.sql; do
        [ -f "$source_dir/$name" ] && [ ! -L "$source_dir/$name" ] || fail "pinned SQL file is missing: $name"
        mysql --defaults-extra-file="$MYSQL_CNF" "$ORIGINAL_SCHEMA" < "$source_dir/$name"
    done
    validate_original_schema_baseline
    after_summary="$ORIGINAL_RUNTIME/schema-after.meta"
    original_schema_summary > "$after_summary"
    chmod 0600 "$after_summary"
    after_hash="$(hash_file "$after_summary")"
    local marker_tmp
    marker_tmp="$(mktemp "$ORIGINAL_RUNTIME/.schema-baseline.XXXXXX")"
    cat > "$marker_tmp" <<EOF
schema_baseline=original-v2
sql_commit=$ORIGINAL_SQL_COMMIT
sql_archive_sha256=$archive
before_summary_sha256=$before_hash
after_summary_sha256=$after_hash
math_training_wrong_answers.user_answer=int NOT NULL
category_seed_rows=category:10 cardcategory:19 article_category:70
EOF
    chmod 0600 "$marker_tmp"
    chown root:root "$marker_tmp"
    mv -f -- "$marker_tmp" "$baseline_marker"
    schema_rebuild_complete=1
    printf 'schema_rebuild=PASS (only isolated Iteration 21 schema; category seed tables preserved)\n'
    printf 'schema_before_summary=%s sha256=%s\n' "$before_summary" "$before_hash"
    printf 'schema_after_summary=%s sha256=%s\n' "$after_summary" "$after_hash"
    printf 'schema_baseline_marker=%s\n' "$baseline_marker"
)
write_original_runtime_config() {
    install -d -o root -g root -m 0700 "$ORIGINAL_RUNTIME" "$ORIGINAL_RUNTIME/logs"
    ensure_original_data_upload_root
    /usr/bin/python3 - "$MYSQL_CNF" "$ORIGINAL_CONFIG" "$DATA/uploads" "$DATA/uploads/uploads" "$ORIGINAL_RUNTIME/logs" <<'PY'
import configparser
import json
import os
import secrets
import stat
import sys

client_path, target, document_root, upload_path, logs = sys.argv[1:]
if os.path.islink(target):
    raise SystemExit("original runtime config must not be a symlink")
parser = configparser.ConfigParser(interpolation=None)
if not parser.read(client_path) or "client" not in parser:
    raise SystemExit("root-only MySQL client file lacks a [client] section")
client = parser["client"]
host = client.get("host", "localhost")
port = int(client.get("port", "3306"))
database = client.get("database", "")
user = client.get("user", "")
password = client.get("password", "")
if host not in {"127.0.0.1", "localhost"} or port != 3306:
    raise SystemExit("MySQL connection is not bound to the isolated local service")
if not database.startswith("woniunote_iter21_") or not user.startswith("wni21_") or not password:
    raise SystemExit("MySQL client identity is not the expected dedicated D04 account")
config = {
    "listeners": [{"address": "127.0.0.1", "port": 5173, "https": False}],
    "app": {
        "threads_num": 2,
        "enable_session": True,
        "session_timeout": 3600,
        "document_root": document_root,
        "upload_path": upload_path,
        "client_max_body_size": "16M",
        "client_max_memory_body_size": "16M",
        "log": {"log_path": logs, "logfile_base_name": "original-v2", "log_level": "INFO", "use_local_time": False},
        "run_as_daemon": False,
        "relaunch_on_error": False,
    },
    "db_clients": [{
        "name": "mysql", "rdbms": "mysql", "host": host, "port": port,
        "dbname": database, "user": user, "passwd": password,
        "number_of_connections": 5, "is_fast": False, "client_encoding": "utf8mb4", "timeout": 10.0,
    }],
    "redis_clients": [{
        "name": "default", "host": "127.0.0.1", "port": 6379, "passwd": "",
        "db": 0, "number_of_connections": 3, "is_fast": False, "timeout": 10.0,
    }],
    "custom_config": {
        "app_name": "WoniuNote original-v2 Iteration 21 rehearsal",
        "app_mode": "production",
        "jwt_secret": secrets.token_urlsafe(48),
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 120,
        "refresh_token_expire_days": 7,
        "cors_origins": ["https://localhost:18443"],
        "rate_limit_per_minute": 60,
        "rate_limit_fail_closed": False,
    },
}
if os.path.exists(target):
    info = os.stat(target, follow_symlinks=False)
    if stat.S_IMODE(info.st_mode) != 0o600 or not stat.S_ISREG(info.st_mode) or info.st_uid != 0:
        raise SystemExit("existing original runtime config is not a root-owned regular 0600 file")
    with open(target, "r", encoding="utf-8") as stream:
        existing = json.load(stream)
    existing_db = existing.get("db_clients", [{}])[0]
    expected_db = config["db_clients"][0]
    if any(existing_db.get(key) != expected_db[key] for key in ("host", "port", "dbname", "user", "passwd")):
        raise SystemExit("existing original runtime config points to a different DB identity")
    listener = existing.get("listeners", [{}])[0]
    if listener.get("address") != "127.0.0.1" or listener.get("port") != 5173:
        raise SystemExit("existing original runtime config has an unexpected listener")
    print("original_runtime_config=reused_verified_0600 (secret values withheld)")
else:
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(config, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
    os.chown(target, 0, 0)
    os.chmod(target, 0o600)
    print("original_runtime_config=created_root_only_0600 (secret values withheld)")
PY
}
safe_original_api_probe() (
    set -Eeuo pipefail
    local body http bytes digest
    body="$(mktemp /run/woniunote-iter21-d04-original-api.XXXXXX)"
    chmod 0600 "$body"
    trap 'rm -f "$body"' EXIT
    http="$(curl --silent --max-time 5 --max-redirs 0 -k \
        -o "$body" -w '%{http_code}' \
        https://127.0.0.1:8443/api/articles/types 2>/dev/null || true)"
    [ "$http" = 200 ] || fail "original-v2 category API returned HTTP ${http:-unknown}"
    bytes="$(wc -c < "$body" | tr -d ' ')"
    digest="$(hash_file "$body")"
    /usr/bin/python3 - "$body" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as stream:
    response = json.load(stream)
if not isinstance(response, dict):
    raise SystemExit("original-v2 category API did not return a JSON object")
if response.get("code") != 200:
    raise SystemExit("original-v2 category API envelope code is not 200")
data = response.get("data")
if isinstance(data, list):
    count = len(data)
elif isinstance(data, dict):
    collections = [data.get(k) for k in ("flat", "types", "tree", "list", "categories")]
    candidates = [len(item) for item in collections if isinstance(item, list)]
    count = max(candidates) if candidates else 0
else:
    count = 0
if count <= 0:
    raise SystemExit("original-v2 category API returned no categories")
print(f"original_api_category_collection_count={count}")
PY
    printf 'original_api_category_http=%s\n' "$http"
    printf 'original_api_category_body_bytes=%s\n' "$bytes"
    printf 'original_api_category_body_sha256=%s\n' "$digest"
)
prepare_original_ui() {
    local archive="$1" archive_sha="$2" source_commit="$3" source_root="$ORIGINAL_RUNTIME/schema-source/$ORIGINAL_SQL_COMMIT"
    local temp_extract archive_member relative source_manifest existing_service config_sha binary_sha dist_index_sha
    local nginx_tmp backend_unit_tmp nginx_unit_tmp backend_pid nginx_pid backend_http frontend_http
    [ "$source_commit" = "$ORIGINAL_SQL_COMMIT" ] || fail "schema reset accepts only the pinned original-v2 SQL commit"
    valid_hash "$archive_sha" || fail "original-v2 SQL archive hash format is invalid"
    case "$archive" in /tmp/iter21-d04-original-sql-*.tar.gz) ;; *) fail "SQL archive is outside the D04 temporary namespace" ;; esac
    [ -f "$archive" ] && [ ! -L "$archive" ] || fail "pinned original-v2 SQL archive is missing"
    [ "$(hash_file "$archive")" = "$archive_sha" ] || fail "pinned SQL archive hash mismatch"
    [ -d "$ORIGINAL" ] && [ ! -L "$ORIGINAL" ] || fail "original-v2 application directory is missing or is a symlink"
    [ -f "$ORIGINAL_BIN" ] && [ ! -L "$ORIGINAL_BIN" ] && [ -x "$ORIGINAL_BIN" ] && \
        [ "$(hash_file "$ORIGINAL_BIN")" = "$ORIGINAL_BIN_SHA" ] || \
        fail "original-v2 backend binary does not match the pinned full SHA-256"
    [ -d "$ORIGINAL_DIST" ] && [ ! -L "$ORIGINAL_DIST" ] && \
        [ -f "$ORIGINAL_DIST/index.html" ] && [ ! -L "$ORIGINAL_DIST/index.html" ] || \
        fail "original-v2 frontend dist is missing or is not a regular built directory"
    [ -z "$(find "$ORIGINAL_DIST" -type l -print -quit)" ] || fail "original-v2 frontend dist contains symlinked assets"
    [ -x /usr/sbin/nginx ] && [ -f /etc/nginx/mime.types ] || fail "system Nginx binary or mime types are unavailable"
    command -v mysqldump >/dev/null 2>&1 || fail "mysqldump is unavailable for the pre-reset schema backup"
    command -v openssl >/dev/null 2>&1 || fail "openssl is unavailable for local HTTPS"
    [ "$(systemctl is-active mysql.service 2>/dev/null || true)" = active ] || fail "MySQL service is not active"
    [ "$(systemctl is-active redis-server.service 2>/dev/null || true)" = active ] || fail "Redis service is not active"
    [ "$(systemctl is-active "$SERVICE" 2>/dev/null || true)" != active ] || fail "main $SERVICE is active; refusing to replace service ownership"
    [ "$(systemctl is-active nginx.service 2>/dev/null || true)" != active ] || fail "global nginx.service is active; refusing packaged Nginx changes"
    [ "$(systemctl is-active "$ORIGINAL_SERVICE" 2>/dev/null || true)" != active ] || {
        local active_marker="$ORIGINAL_RUNTIME/schema-baseline.meta"
        [ -f "$active_marker" ] || fail "original-v2 service is active without a baseline marker"
        assert_original_service_owner "$ORIGINAL_BIN_SHA"
        assert_original_nginx_owner
        printf 'original_ui=already_active\n'
        printf 'original_backend_binary_sha256=%s\n' "$ORIGINAL_BIN_SHA"
        safe_original_api_probe
        return 0
    }
    [ -z "$(listener_pids)" ] || fail "backend port 5173 is occupied; refusing to claim it"
    [ ! -L "$ORIGINAL_RUNTIME" ] || fail "original-v2 runtime directory must not be a symlink"
    if [ -e "$ORIGINAL_RUNTIME" ]; then
        [ -d "$ORIGINAL_RUNTIME" ] && [ "$(stat -c '%u' "$ORIGINAL_RUNTIME")" = 0 ] && \
            [ "$(stat -c '%a' "$ORIGINAL_RUNTIME")" = 700 ] || \
            fail "existing original-v2 runtime directory is not a root-owned 0700 directory"
    fi
    install -d -o root -g root -m 0700 "$ORIGINAL_RUNTIME"
    ensure_original_data_upload_root
    preflight_original_upload_layout
    install -d -o root -g root -m 0700 "$ORIGINAL_RUNTIME/schema-source"
    temp_extract="$(mktemp -d "$ORIGINAL_RUNTIME/.schema-source.XXXXXX")"
    while IFS= read -r archive_member; do
        case "$archive_member" in
            scripts/|scripts/sql/) ;;
            scripts/sql/01_users.sql|scripts/sql/02_article.sql|scripts/sql/03_comment.sql|scripts/sql/04_favorite.sql|scripts/sql/05_credit.sql|scripts/sql/06_category.sql|scripts/sql/07_card_item.sql|scripts/sql/08_math_training.sql|scripts/sql/09_article_category.sql) ;;
            *) rm -rf "$temp_extract"; fail "unexpected member in pinned SQL archive" ;;
        esac
    done < <(tar -tzf "$archive")
    tar -xzf "$archive" -C "$temp_extract"
    for relative in scripts/sql/01_users.sql scripts/sql/02_article.sql scripts/sql/03_comment.sql \
                    scripts/sql/04_favorite.sql scripts/sql/05_credit.sql scripts/sql/06_category.sql \
                    scripts/sql/07_card_item.sql scripts/sql/08_math_training.sql scripts/sql/09_article_category.sql; do
        [ -f "$temp_extract/$relative" ] && [ ! -L "$temp_extract/$relative" ] || {
            rm -rf "$temp_extract"; fail "pinned SQL archive omitted $relative";
        }
    done
    source_manifest="$temp_extract/SQL-SHA256SUMS"
    (cd "$temp_extract" && sha256sum scripts/sql/*.sql > "$source_manifest")
    chmod 0600 "$source_manifest"
    if [ -e "$source_root" ]; then
        [ -d "$source_root" ] && [ ! -L "$source_root" ] || { rm -rf "$temp_extract"; fail "pinned SQL source path is not a directory"; }
        cmp -s "$source_manifest" "$source_root/SQL-SHA256SUMS" || { rm -rf "$temp_extract"; fail "pinned SQL source already exists with a different manifest"; }
        rm -rf "$temp_extract"
    else
        mv "$temp_extract" "$source_root"
        chown -R root:root "$source_root"
        chmod 0700 "$source_root"
    fi
    rm -f "$archive"
    printf 'original_sql_commit=%s\n' "$ORIGINAL_SQL_COMMIT"
    printf 'original_sql_archive_sha256=%s\n' "$archive_sha"
    printf 'original_sql_manifest_sha256=%s\n' "$(hash_file "$source_root/SQL-SHA256SUMS")"
    rebuild_original_schema "$source_root/scripts/sql" "$archive_sha"
    existing_service="$(systemctl is-active "$ORIGINAL_SERVICE" 2>/dev/null || true)"
    [ "$existing_service" != active ] || fail "original-v2 service became active during schema preparation"
    local ldd_result
    ldd_result="$(ldd "$ORIGINAL_BIN" 2>&1)"
    [[ "$ldd_result" != *"not found"* ]] || fail "original-v2 binary has unresolved runtime libraries"
    write_original_runtime_config
    ensure_original_runtime_upload_link
    repair_original_upload_config
    if redis-cli -h 127.0.0.1 -p 6379 PING 2>/dev/null | grep -qx PONG; then
        printf 'redis_local_noauth_ping=PONG\n'
    else
        fail "local Redis requires unavailable auth or is not responding; no Redis config was guessed"
    fi
    if [ -e "$ORIGINAL_RUNTIME/localhost.crt" ] || [ -e "$ORIGINAL_RUNTIME/localhost.key" ]; then
        [ -f "$ORIGINAL_RUNTIME/localhost.crt" ] && [ -f "$ORIGINAL_RUNTIME/localhost.key" ] && \
            [ ! -L "$ORIGINAL_RUNTIME/localhost.crt" ] && [ ! -L "$ORIGINAL_RUNTIME/localhost.key" ] || \
            fail "local TLS certificate/key pair is incomplete or not regular files"
        openssl x509 -in "$ORIGINAL_RUNTIME/localhost.crt" -noout -checkend 3600 >/dev/null || \
            fail "existing localhost TLS certificate is expired or near expiry"
        chmod 0600 "$ORIGINAL_RUNTIME/localhost.key"
        printf 'local_tls_certificate=reused\n'
    else
        openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
            -keyout "$ORIGINAL_RUNTIME/localhost.key" -out "$ORIGINAL_RUNTIME/localhost.crt" \
            -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' >/dev/null 2>&1
        chmod 0600 "$ORIGINAL_RUNTIME/localhost.key"
        chmod 0644 "$ORIGINAL_RUNTIME/localhost.crt"
        printf 'local_tls_certificate=created_self_signed_loopback_only\n'
    fi
    nginx_tmp="$(mktemp "$ORIGINAL_RUNTIME/.nginx.conf.XXXXXX")"
    cat > "$nginx_tmp" <<EOF
pid $ORIGINAL_RUNTIME/nginx.pid;
error_log $ORIGINAL_RUNTIME/nginx-error.log warn;
events { worker_connections 128; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log off;
    client_body_temp_path $ORIGINAL_RUNTIME/client-body;
    proxy_temp_path $ORIGINAL_RUNTIME/proxy-temp;
    server {
        listen 127.0.0.1:8443 ssl;
        server_name localhost;
        ssl_certificate $ORIGINAL_RUNTIME/localhost.crt;
        ssl_certificate_key $ORIGINAL_RUNTIME/localhost.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        client_max_body_size 16m;
        root $ORIGINAL_DIST;
        index index.html;
        location = /api { proxy_pass http://127.0.0.1:5173; include /etc/nginx/proxy_params; }
        location ^~ /api/ { proxy_pass http://127.0.0.1:5173; include /etc/nginx/proxy_params; }
        location = /uploads { proxy_pass http://127.0.0.1:5173; include /etc/nginx/proxy_params; }
        location ^~ /uploads/ { proxy_pass http://127.0.0.1:5173; include /etc/nginx/proxy_params; }
        location / { try_files \$uri \$uri/ /index.html; }
    }
}
EOF
    chmod 0600 "$nginx_tmp"
    install_exact_file "$nginx_tmp" "$ORIGINAL_RUNTIME/nginx.conf" 0600
    install -d -o root -g root -m 0700 "$ORIGINAL_RUNTIME/client-body" "$ORIGINAL_RUNTIME/proxy-temp"
    /usr/sbin/nginx -t -p "$ORIGINAL_RUNTIME/" -c "$ORIGINAL_RUNTIME/nginx.conf"
    [ -z "$(ss -H -ltn 'sport = :8443' 2>/dev/null)" ] || fail "loopback HTTPS port 8443 is already occupied"
    backend_unit_tmp="$(mktemp "$ORIGINAL_RUNTIME/.backend-unit.XXXXXX")"
    cat > "$backend_unit_tmp" <<EOF
[Unit]
Description=WoniuNote Iteration 21 original-v2 business rehearsal backend
After=network.target mysql.service redis-server.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$ORIGINAL_RUNTIME
Environment=WONIUNOTE_ENV=production
ExecStart=/usr/bin/env WONIUNOTE_ENV=production $ORIGINAL_BIN $ORIGINAL_CONFIG
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
    chmod 0600 "$backend_unit_tmp"
    install_exact_file "$backend_unit_tmp" "/etc/systemd/system/$ORIGINAL_SERVICE.service" 0644
    nginx_unit_tmp="$(mktemp "$ORIGINAL_RUNTIME/.nginx-unit.XXXXXX")"
    cat > "$nginx_unit_tmp" <<EOF
[Unit]
Description=WoniuNote Iteration 21 original-v2 loopback HTTPS frontend
After=$ORIGINAL_SERVICE.service
Requires=$ORIGINAL_SERVICE.service

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/sbin/nginx -g "daemon off;" -p $ORIGINAL_RUNTIME/ -c $ORIGINAL_RUNTIME/nginx.conf
ExecReload=/bin/kill -HUP \$MAINPID
ExecStop=/bin/kill -QUIT \$MAINPID
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
    chmod 0600 "$nginx_unit_tmp"
    install_exact_file "$nginx_unit_tmp" "/etc/systemd/system/$ORIGINAL_NGINX_SERVICE.service" 0644
    systemctl daemon-reload
    systemctl start "$ORIGINAL_SERVICE.service"
    backend_http=000
    for _ in $(seq 1 40); do
        backend_http="$(curl --silent --max-time 1 -o /dev/null -w '%{http_code}' \
            http://127.0.0.1:5173/health 2>/dev/null || true)"
        [ "$backend_http" = 200 ] && break
        sleep 0.25
    done
    [ "$backend_http" = 200 ] || fail "original-v2 backend failed health check (HTTP $backend_http)"
    assert_original_service_owner "$ORIGINAL_BIN_SHA"
    systemctl start "$ORIGINAL_NGINX_SERVICE.service"
    frontend_http=000
    for _ in $(seq 1 40); do
        frontend_http="$(curl --silent --max-time 1 --max-redirs 0 -k -o /dev/null -w '%{http_code}' \
            https://127.0.0.1:8443/ 2>/dev/null || true)"
        [ "$frontend_http" = 200 ] && break
        sleep 0.25
    done
    [ "$frontend_http" = 200 ] || fail "original-v2 frontend failed local HTTPS check (HTTP $frontend_http)"
    [ "$(systemctl is-active "$ORIGINAL_NGINX_SERVICE" 2>/dev/null || true)" = active ] || fail "dedicated original-v2 Nginx service is not active"
    [ -z "$(ss -H -ltn 'sport = :8443' | awk '$4 !~ /^127\.0\.0\.1:8443$/ {print}')" ] || \
        fail "dedicated HTTPS port is not loopback-only"
    assert_original_nginx_owner
    safe_original_api_probe
    probe_formal_hooks_with_env
    config_sha="$(hash_file "$ORIGINAL_CONFIG")"
    binary_sha="$(hash_file "$ORIGINAL_BIN")"
    dist_index_sha="$(hash_file "$ORIGINAL_DIST/index.html")"
    printf 'original_ui=READY (not logged in; no browser state injected)\n'
    printf 'original_backend_service=%s.service state=%s\n' "$ORIGINAL_SERVICE" \
        "$(systemctl is-active "$ORIGINAL_SERVICE.service")"
    printf 'original_nginx_service=%s.service state=%s\n' "$ORIGINAL_NGINX_SERVICE" \
        "$(systemctl is-active "$ORIGINAL_NGINX_SERVICE.service")"
    printf 'original_backend_binary=%s\n' "$ORIGINAL_BIN"
    printf 'original_backend_binary_sha256=%s\n' "$binary_sha"
    printf 'original_runtime_config=%s mode=%s sha256=%s (secret values withheld)\n' \
        "$ORIGINAL_CONFIG" "$(stat -c '%a' "$ORIGINAL_CONFIG")" "$config_sha"
    printf 'original_frontend_dist=%s index_sha256=%s file_count=%s total_bytes=%s\n' \
        "$ORIGINAL_DIST" "$dist_index_sha" \
        "$(find "$ORIGINAL_DIST" -type f | wc -l | tr -d ' ')" \
        "$(du -sb "$ORIGINAL_DIST" | awk '{print $1}')"
    printf 'original_frontend_dist_manifest_sha256=%s\n' \
        "$(cd "$ORIGINAL_DIST" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
    printf 'original_backend_unit=%s sha256=%s\n' \
        "/etc/systemd/system/$ORIGINAL_SERVICE.service" \
        "$(hash_file "/etc/systemd/system/$ORIGINAL_SERVICE.service")"
    printf 'original_nginx_unit=%s sha256=%s\n' \
        "/etc/systemd/system/$ORIGINAL_NGINX_SERVICE.service" \
        "$(hash_file "/etc/systemd/system/$ORIGINAL_NGINX_SERVICE.service")"
    printf 'original_nginx_config=%s sha256=%s\n' \
        "$ORIGINAL_RUNTIME/nginx.conf" "$(hash_file "$ORIGINAL_RUNTIME/nginx.conf")"
    printf 'original_https_bind=127.0.0.1:8443 self_signed_cert_sha256=%s\n' \
        "$(hash_file "$ORIGINAL_RUNTIME/localhost.crt")"
    printf 'original_https_get_http=%s\n' "$frontend_http"
    printf 'browser_entry_host_tunnel=https://localhost:18443/\n'
    printf 'browser_tunnel=ssh -F /Users/yunjinqi/.lima/woniunote-iter21-systemd-20261024t0028z/ssh.config -N -L 127.0.0.1:18443:127.0.0.1:8443 -o HostName=127.0.0.1 -o ExitOnForwardFailure=yes -o BatchMode=yes lima-woniunote-iter21-systemd-20261024t0028z\n'
    printf 'browser_register_path=/register; use a fresh browser context and an email-shaped test username; create the account in the UI; no credentials are preloaded\n'
    printf 'database_migrations=NOT_RUN (schema prepared only from pinned original-v2 SQL01..09)\n'
    printf 'candidate_switch=NOT_RUN (root must first capture saved/exported draft and close old editor)\n'
}
capture_state() {
    local label="$1" active main_pid pid sha current rollback current_release_path config_sha original_active original_pid
    printf 'evidence_format=iter21-d04-business-runtime-v1\n'
    printf 'captured_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'host_os=%s\n' "$(. /etc/os-release; printf '%s-%s' "$ID" "$VERSION_ID")"
    printf 'kernel=%s\n' "$(uname -sr)"
    printf 'capture_label=%s\n' "$label"
    printf 'instance=%s\n' woniunote-iter21-systemd-20261024t0028z
    active="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
    printf 'backend_service_state=%s\n' "$active"
    main_pid="$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null || true)"
    printf 'backend_main_pid=%s\n' "${main_pid:-unknown}"
    if [ -n "$main_pid" ] && [[ "$main_pid" =~ ^[1-9][0-9]*$ ]] && [ -r "/proc/$main_pid/exe" ]; then
        sha="$(hash_file "/proc/$main_pid/exe")"
        printf 'backend_main_exe_sha256=%s\n' "$sha"
        printf 'backend_main_exe_path=%s\n' "$(readlink "/proc/$main_pid/exe" || true)"
    fi
    while IFS= read -r pid; do printf 'backend_port_5173_pid=%s\n' "$pid"; done < <(listener_pids)
    printf 'nginx_service_state=%s\n' "$(systemctl is-active "$NGINX_SERVICE" 2>/dev/null || true)"
    printf 'nginx_config_sha256=%s\n' "$(hash_file /etc/nginx/nginx.conf 2>/dev/null || printf missing)"
    printf 'runtime_config_path=%s\n' "$CONFIG"
    if [ -f "$CONFIG" ]; then
        printf 'runtime_config_mode=%s\n' "$(stat -c '%a' "$CONFIG")"
        config_sha="$(hash_file "$CONFIG")"
        printf 'runtime_config_sha256=%s\n' "$config_sha"
    else
        printf 'runtime_config=missing\n'
    fi
    printf 'manager_state_path=%s\n' "$STATE"
    current="$(current_source_sha 2>/dev/null || true)"
    rollback="$(rollback_source_sha 2>/dev/null || true)"
    printf 'manager_current_source_sha=%s\n' "${current:-none}"
    printf 'manager_rollback_source_sha=%s\n' "${rollback:-none}"
    if [ -n "$current" ]; then
        current_release_path="$(readlink -f "$STATE/current")"
        printf 'manager_current_release_path=%s\n' "$current_release_path"
        [ -x "$current_release_path/backend_cpp/build/woniunote_backend" ] && \
            printf 'manager_current_binary_sha256=%s\n' "$(hash_file "$current_release_path/backend_cpp/build/woniunote_backend")"
        [ -f "$current_release_path/frontend/dist/index.html" ] && \
            printf 'manager_current_index_sha256=%s\n' "$(hash_file "$current_release_path/frontend/dist/index.html")"
    fi
    original_active="$(systemctl is-active "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    printf 'original_backend_service_state=%s\n' "${original_active:-not-installed}"
    original_pid="$(systemctl show -p MainPID --value "$ORIGINAL_SERVICE.service" 2>/dev/null || true)"
    printf 'original_backend_main_pid=%s\n' "${original_pid:-unknown}"
    if [ -n "$original_pid" ] && [[ "$original_pid" =~ ^[1-9][0-9]*$ ]] && [ -r "/proc/$original_pid/exe" ]; then
        printf 'original_backend_main_exe_sha256=%s\n' "$(hash_file "/proc/$original_pid/exe")"
        printf 'original_backend_main_exe_path=%s\n' "$(readlink "/proc/$original_pid/exe" || true)"
    fi
    printf 'original_frontend_service_state=%s\n' \
        "$(systemctl is-active "$ORIGINAL_NGINX_SERVICE.service" 2>/dev/null || printf not-installed)"
    if [ -f "$ORIGINAL_CONFIG" ] && [ ! -L "$ORIGINAL_CONFIG" ]; then
        printf 'original_runtime_config_mode=%s\n' "$(stat -c '%a' "$ORIGINAL_CONFIG")"
        printf 'original_runtime_config_sha256=%s\n' "$(hash_file "$ORIGINAL_CONFIG")"
    else
        printf 'original_runtime_config=missing\n'
    fi
    if [ -f "$ORIGINAL_RUNTIME/localhost.crt" ] && [ ! -L "$ORIGINAL_RUNTIME/localhost.crt" ]; then
        printf 'original_tls_certificate_sha256=%s\n' "$(hash_file "$ORIGINAL_RUNTIME/localhost.crt")"
    else
        printf 'original_tls_certificate=missing\n'
    fi
    if [ -f "$ORIGINAL_BIN" ] && [ ! -L "$ORIGINAL_BIN" ]; then
        printf 'original_pinned_binary_sha256=%s\n' "$(hash_file "$ORIGINAL_BIN")"
    else
        printf 'original_pinned_binary=missing\n'
    fi
    if [ -d "$ORIGINAL_DIST" ] && [ ! -L "$ORIGINAL_DIST" ] && \
       [ -f "$ORIGINAL_DIST/index.html" ] && [ ! -L "$ORIGINAL_DIST/index.html" ]; then
        printf 'original_frontend_dist_path=%s\n' "$ORIGINAL_DIST"
        printf 'original_frontend_dist_index_sha256=%s\n' "$(hash_file "$ORIGINAL_DIST/index.html")"
        printf 'original_frontend_dist_file_count=%s\n' "$(find "$ORIGINAL_DIST" -type f | wc -l | tr -d ' ')"
        printf 'original_frontend_dist_total_bytes=%s\n' "$(du -sb "$ORIGINAL_DIST" | awk '{print $1}')"
        printf 'original_frontend_dist_symlink_count=%s\n' "$(find "$ORIGINAL_DIST" -type l | wc -l | tr -d ' ')"
        printf 'original_frontend_dist_manifest_sha256=%s\n' \
            "$(cd "$ORIGINAL_DIST" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
    else
        printf 'original_frontend_dist=missing_or_invalid\n'
    fi
    capture_schema
    if [ "$active" = active ]; then
        safe_api_probe
    else
        printf 'read_only_api=NOT_RUN (backend service inactive)\n'
    fi
    if [ "$original_active" = active ]; then
        assert_original_service_owner "$ORIGINAL_BIN_SHA"
        if [ "$(systemctl is-active "$ORIGINAL_NGINX_SERVICE.service" 2>/dev/null || true)" = active ]; then
            assert_original_nginx_owner
            safe_original_api_probe
        else
            printf 'original_read_only_api=NOT_RUN (dedicated original-v2 frontend service inactive)\n'
        fi
    else
        printf 'original_read_only_api=NOT_RUN (original-v2 backend service inactive)\n'
    fi
    printf 'formal_hooks=NOT_INFERRED_FROM_RUNTIME; verify frozen CMake/build evidence separately\n'
    printf 'browser_captcha_login=NOT_RUN; root performs visual CAPTCHA and user-flow checks\n'
}
initial_install_record_value() {
    local file="$1" key="$2"
    awk -F= -v wanted="$key" '$1 == wanted { sub(/^[^=]*=/, ""); print; exit }' "$file"
}
verify_initial_install_record() {
    local record="$1" target="$2" evidence expected uid perms canonical
    [ -n "$record" ] && [ -f "$record" ] && [ ! -L "$record" ] || fail "首次维护安装需要显式审阅记录文件"
    [[ "$record" = "$BUSINESS/evidence/"* && "$record" != *$'\n'* && "$record" != */../* && "$record" != */.. ]] || \
        fail "首次维护审阅记录必须位于隔离 evidence 目录"
    canonical="$(realpath "$record")"
    [ "$canonical" = "$record" ] || fail "首次维护审阅记录路径包含符号链接或非规范路径"
    uid="$(stat -c '%u' "$record")"; perms="$(stat -c '%a' "$record")"
    [ "$uid" = 0 ] && [ "$perms" = 600 ] || fail "首次维护审阅记录必须是 root-owned 0600 普通文件"
    awk -F= '
        NF < 2 || $1 !~ /^[A-Z0-9_]+$/ || seen[$1]++ { exit 1 }
        $1 !~ /^(TO_SHA|MODE|REVIEWED|EVIDENCE|EVIDENCE_SHA256|EDITOR_HANDOFF|WRITE_FREEZE|BACKUP_RESTORE|SCHEMA|FRESH_INSTANCE)$/ { exit 1 }
    ' "$record" || fail "首次维护审阅记录字段格式无效或含重复/未知字段"
    [ "$(initial_install_record_value "$record" TO_SHA)" = "$target" ] || fail "首次维护审阅记录未绑定目标完整 SHA"
    [ "$(initial_install_record_value "$record" MODE)" = maintenance ] || fail "deploy-first 只接受 MODE=maintenance 记录"
    [ "$(initial_install_record_value "$record" REVIEWED)" = PASS ] || fail "首次维护审阅记录缺少 REVIEWED=PASS"
    [ "$(initial_install_record_value "$record" EDITOR_HANDOFF)" = PASS ] && \
        [ "$(initial_install_record_value "$record" WRITE_FREEZE)" = PASS ] && \
        [ "$(initial_install_record_value "$record" BACKUP_RESTORE)" = PASS ] && \
        [ "$(initial_install_record_value "$record" SCHEMA)" = PASS ] || \
        fail "首次维护记录没有完整的编辑器交接、写入冻结、备份恢复和 schema 通过状态"
    evidence="$(initial_install_record_value "$record" EVIDENCE)"
    expected="$(initial_install_record_value "$record" EVIDENCE_SHA256)"
    [[ "$evidence" = "$BUSINESS/evidence/first-maintenance/"*"/manifest.txt" ]] || \
        fail "首次维护记录必须绑定 first-maintenance manifest.txt"
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail "首次维护 manifest SHA-256 格式无效"
    [ -f "$evidence" ] && [ ! -L "$evidence" ] || fail "首次维护 manifest 缺失或不是普通文件"
    canonical="$(realpath "$evidence")"
    [ "$canonical" = "$evidence" ] || fail "首次维护 manifest 路径包含符号链接或非规范路径"
    [ "$(hash_file "$evidence")" = "$expected" ] || fail "首次维护 manifest SHA-256 不匹配"
}
run_manager() {
    local candidate="$1" source_sha="$2" compatibility_file="$3" thumb_url="$4"
    local upload_url="$5" upload_file="$6" upload_sha="$7" action="$8" repo initial_record
    repo="$(repo_path "$candidate")"
    verify_repo "$repo" "$source_sha"
    require_release_config
    [ -f "$upload_file" ] && [ ! -L "$upload_file" ] || fail "smoke upload sample is missing or not a regular file"
    case "$upload_file" in "$DATA"/*) ;; *) fail "smoke upload sample must be under shared persistent data" ;; esac
    [ "$(hash_file "$upload_file")" = "$upload_sha" ] || fail "smoke upload sample SHA does not match"
    [ -f "$DATA/runtime-config.json" ] && [ "$(stat -c '%a' "$DATA/runtime-config.json")" = 600 ] || fail "runtime config must exist with mode 0600"
    export PATH="$NODE_BIN:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export WONIUNOTE_PROJECT_DIR="$repo"
    export WONIUNOTE_STATE_DIR="$STATE"
    export WONIUNOTE_DATA_DIR="$DATA"
    export WONIUNOTE_RUNTIME_CONFIG="$CONFIG"
    export WONIUNOTE_NGINX_CONFIG=/etc/nginx/nginx.conf
    export WONIUNOTE_SYSTEMD_UNIT=/etc/systemd/system/woniunote.service
    export WONIUNOTE_SERVICE_NAME="$SERVICE"
    export WONIUNOTE_NGINX_SERVICE_NAME="$NGINX_SERVICE"
    export WONIUNOTE_BUILD_JOBS=2
    export WONIUNOTE_SMOKE_HOST="$API_HOST"
    export WONIUNOTE_SMOKE_SCHEME=https
    export WONIUNOTE_SMOKE_PORT=443
    export WONIUNOTE_SMOKE_READONLY_API=/api/articles/types
    export WONIUNOTE_SMOKE_THUMB_PATH="$thumb_url"
    export WONIUNOTE_SMOKE_UPLOAD_PATH="$upload_url"
    export WONIUNOTE_SMOKE_UPLOAD_FILE="$upload_file"
    export WONIUNOTE_SMOKE_UPLOAD_SHA256="$upload_sha"
    export WONIUNOTE_STOP_TIMEOUT_SECONDS=10
    export WONIUNOTE_START_TIMEOUT_SECONDS=10
    export WONIUNOTE_HEALTH_TIMEOUT_SECONDS=14
    export WONIUNOTE_RECOVERY_BUDGET_SECONDS=60
    if [ "$action" = deploy-first ]; then
        [ ! -e "$STATE/current" ] && [ ! -e "$STATE/rollback" ] || fail "first install requires a fresh empty D04 manager state"
        if [ -e "$STATE" ] && [ -n "$(find "$STATE" -mindepth 1 -print -quit)" ]; then
            fail "first install requires an empty D04 manager state directory"
        fi
        [ "$(systemctl is-active "$SERVICE" 2>/dev/null || true)" != active ] || fail "stop the verified original service before first install"
        assert_no_listener
        initial_record="${WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD:-}"
        verify_initial_install_record "$initial_record" "$source_sha"
        unset WONIUNOTE_COMPATIBILITY_RECORD WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD
        export WONIUNOTE_INITIAL_INSTALL_RECORD="$initial_record"
        "$repo/scripts/deploy_release.sh" deploy --sha "$source_sha"
    elif [ "$action" = deploy ]; then
        local current
        current="$(current_source_sha)" || fail "candidate 2 must already be the managed current release"
        [ -f "$compatibility_file" ] && [ ! -L "$compatibility_file" ] || fail "compatibility record file is missing"
        export WONIUNOTE_COMPATIBILITY_RECORD="$compatibility_file"
        export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$BUSINESS/evidence/compat-${source_sha}-to-${current}.env"
        assert_single_service_owner "$(hash_file "$(readlink -f "$STATE/current")/backend_cpp/build/woniunote_backend")" >/dev/null
        "$repo/scripts/deploy_release.sh" deploy --sha "$source_sha"
    else
        fail "internal manager action is invalid"
    fi
}

require_root
command_name="${1:-}"
[ -n "$command_name" ] || fail "operation is required"
shift

case "$command_name" in
    inspect)
        [ "$#" -eq 0 ] || fail "inspect takes no arguments"
        capture_state read-only
        ;;
    capture)
        [ "$#" -eq 1 ] || fail "capture needs one label"
        [[ "$1" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || fail "capture label is invalid"
        capture_state "$1"
        ;;
    api)
        [ "$#" -eq 0 ] || fail "api takes no arguments"
        systemctl is-active --quiet "$SERVICE" || fail "$SERVICE service is not active"
        safe_api_probe
        ;;
    audit-original-schema)
        [ "$#" -eq 0 ] || fail "audit-original-schema takes no arguments"
        with_remote_lock
        audit_original_schema
        ;;
    assert-original-sql-path-free)
        [ "$#" -eq 1 ] || fail "SQL archive path is required"
        case "$1" in /tmp/iter21-d04-original-sql-*.tar.gz) ;; *) fail "SQL archive path is outside the D04 temporary namespace" ;; esac
        [ ! -e "$1" ] && [ ! -L "$1" ] || fail "SQL archive destination already exists"
        ;;
    prepare-original-ui)
        [ "$#" -eq 3 ] || fail "prepare-original-ui needs archive path, archive SHA and pinned commit"
        assert_handoff
        with_remote_lock
        prepare_original_ui "$1" "$2" "$3"
        ;;
    repair-original-upload-layout)
        [ "$#" -eq 0 ] || fail "repair-original-upload-layout takes no arguments"
        assert_handoff
        with_remote_lock
        repair_original_upload_layout
        ;;
    assert-stage-path-free)
        [ "$#" -eq 1 ] || fail "stage path is required"
        case "$1" in /tmp/iter21-d04-candidate-2-*|/tmp/iter21-d04-candidate-3-*|/tmp/iter21-d04-candidate-4-*|/tmp/iter21-d04-candidate-5-*) ;; *) fail "staging path is outside the owned temporary namespace" ;; esac
        [ ! -e "$1" ] || fail "staging path already exists"
        ;;
    install-candidate)
        [ "$#" -eq 3 ] || fail "install-candidate needs label, SHA and staging path"
        assert_handoff
        with_remote_lock
        candidate="$1"; expected="$2"; staged="$3"
        label="$(basename "$candidate")"
        valid_label "$candidate" || fail "unsupported candidate label"
        valid_sha "$expected" || fail "expected source SHA is invalid"
        case "$staged" in /tmp/iter21-d04-"$candidate"-*) ;; *) fail "staging path is outside the owned temporary namespace" ;; esac
        [ -d "$staged" ] && [ -d "$staged/.git" ] || fail "staged Git repository is missing"
        [ "$(git -C "$staged" rev-parse --verify HEAD)" = "$expected" ] || fail "staged Git commit mismatch"
        [ -z "$(git -C "$staged" status --porcelain --untracked-files=all)" ] || fail "staged repository is dirty"
        target="$(repo_path "$candidate")"
        [ ! -e "$target" ] || fail "candidate destination exists; refusing overwrite"
        chown -R root:root "$staged"
        mv -- "$staged" "$target"
        verify_repo "$target" "$expected"
        printf 'staged_candidate=%s\n' "$candidate"
        printf 'staged_candidate_sha=%s\n' "$expected"
        ;;
    stop-original)
        [ "$#" -eq 1 ] || fail "stop-original needs expected binary SHA"
        assert_handoff
        with_remote_lock
        expected="$1"
        valid_hash "$expected" || fail "expected original binary SHA is invalid"
        original="$BUSINESS/original-v2/backend_cpp/build/woniunote_backend"
        [ -x "$original" ] && [ "$(hash_file "$original")" = "$expected" ] || fail "original-v2 binary does not match expected SHA"
        printf 'stop_original_expected_binary_sha256=%s\n' "$expected"
        assert_original_service_owner "$expected"
        timeout 12s systemctl stop "$ORIGINAL_SERVICE.service"
        systemctl is-active --quiet "$ORIGINAL_SERVICE.service" && fail "dedicated original-v2 service remains active after stop"
        assert_no_listener
        printf 'original_service_stop=PASS; dedicated original-v2 backend stopped and port 5173 is unbound; global services and database were not stopped\n'
        ;;
    deploy-first)
        [ "$#" -eq 6 ] || fail "deploy-first needs candidate, SHA and four smoke values"
        assert_handoff
        with_remote_lock
        candidate="$1"; source_sha="$2"; thumb_url="$3"; upload_url="$4"; upload_file="$5"; upload_sha="$6"
        [ "$candidate" = candidate-2 ] || fail "first maintenance deployment is fixed to candidate-2"
        valid_sha "$source_sha" || fail "source SHA is invalid"
        valid_hash "$upload_sha" || fail "upload SHA is invalid"
        run_manager "$candidate" "$source_sha" "" "$thumb_url" "$upload_url" "$upload_file" "$upload_sha" deploy-first
        printf 'first_install_state=current=candidate-2; rollback=none (expected for explicit maintenance transition)\n'
        ;;
    deploy)
        [ "$#" -eq 7 ] || fail "deploy needs candidate, SHA, compatibility record and four smoke values"
        assert_handoff
        with_remote_lock
        candidate="$1"; source_sha="$2"; compatibility_file="$3"; thumb_url="$4"; upload_url="$5"; upload_file="$6"; upload_sha="$7"
        valid_label "$candidate" || fail "unsupported candidate label"
        valid_sha "$source_sha" || fail "source SHA is invalid"
        valid_hash "$upload_sha" || fail "upload SHA is invalid"
        run_manager "$candidate" "$source_sha" "$compatibility_file" "$thumb_url" "$upload_url" "$upload_file" "$upload_sha" deploy
        ;;
    rollback)
        [ "$#" -eq 7 ] || fail "rollback needs current SHA, target SHA, compatibility record and four smoke values"
        assert_handoff
        with_remote_lock
        current_expected="$1"; target_expected="$2"; compatibility_file="$3"; thumb_url="$4"; upload_url="$5"; upload_file="$6"; upload_sha="$7"
        valid_sha "$current_expected" && valid_sha "$target_expected" || fail "current or target SHA is invalid"
        valid_hash "$upload_sha" || fail "upload SHA is invalid"
        [ "$(current_source_sha)" = "$current_expected" ] || fail "current release is not the expected SHA"
        [ "$(rollback_source_sha)" = "$target_expected" ] || fail "rollback pointer does not target the expected SHA"
        [ -f "$compatibility_file" ] && [ ! -L "$compatibility_file" ] || fail "reverse compatibility record is missing"
        current_release_path="$(readlink -f "$STATE/current")"
        target_release_path="$(readlink -f "$STATE/rollback")"
        current_binary_sha="$(hash_file "$current_release_path/backend_cpp/build/woniunote_backend")"
        assert_single_service_owner "$current_binary_sha" >/dev/null
        manager_repo=""
        manager_repo="$(rollback_manager_repo_for_sha "$current_expected")"
        export PATH="$NODE_BIN:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        export WONIUNOTE_PROJECT_DIR="$manager_repo"
        export WONIUNOTE_STATE_DIR="$STATE"
        export WONIUNOTE_DATA_DIR="$DATA"
        export WONIUNOTE_RUNTIME_CONFIG="$CONFIG"
        export WONIUNOTE_NGINX_CONFIG=/etc/nginx/nginx.conf
        export WONIUNOTE_SYSTEMD_UNIT=/etc/systemd/system/woniunote.service
        export WONIUNOTE_SERVICE_NAME="$SERVICE" WONIUNOTE_NGINX_SERVICE_NAME="$NGINX_SERVICE"
        export WONIUNOTE_SMOKE_HOST="$API_HOST" WONIUNOTE_SMOKE_SCHEME=https WONIUNOTE_SMOKE_PORT=443
        export WONIUNOTE_SMOKE_READONLY_API=/api/articles/types
        export WONIUNOTE_SMOKE_THUMB_PATH="$thumb_url" WONIUNOTE_SMOKE_UPLOAD_PATH="$upload_url"
        export WONIUNOTE_SMOKE_UPLOAD_FILE="$upload_file" WONIUNOTE_SMOKE_UPLOAD_SHA256="$upload_sha"
        export WONIUNOTE_STOP_TIMEOUT_SECONDS=10 WONIUNOTE_START_TIMEOUT_SECONDS=10
        export WONIUNOTE_HEALTH_TIMEOUT_SECONDS=14 WONIUNOTE_RECOVERY_BUDGET_SECONDS=60
        export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$compatibility_file"
        printf 'rollback_from_sha=%s\nrollback_to_sha=%s\n' "$current_expected" "$target_expected"
        printf 'rollback_target_binary_sha256=%s\n' "$(hash_file "$target_release_path/backend_cpp/build/woniunote_backend")"
        "$manager_repo/scripts/deploy_release.sh" rollback
        ;;
    *) fail "unsupported operation: $command_name" ;;
esac
