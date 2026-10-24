#!/usr/bin/env bash
set -eEo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULTS="$APP_DIR/.woniunote-deploy.env"
if [ -f "$DEFAULTS" ]; then
    while IFS='=' read -r key value; do
        case "$key" in
            WONIUNOTE_PROJECT_DIR) [ -n "$WONIUNOTE_PROJECT_DIR" ] || WONIUNOTE_PROJECT_DIR="$value" ;;
            WONIUNOTE_STATE_DIR) [ -n "$WONIUNOTE_STATE_DIR" ] || WONIUNOTE_STATE_DIR="$value" ;;
            WONIUNOTE_DATA_DIR) [ -n "$WONIUNOTE_DATA_DIR" ] || WONIUNOTE_DATA_DIR="$value" ;;
            WONIUNOTE_RUNTIME_CONFIG) [ -n "$WONIUNOTE_RUNTIME_CONFIG" ] || WONIUNOTE_RUNTIME_CONFIG="$value" ;;
            WONIUNOTE_NGINX_CONFIG) [ -n "$WONIUNOTE_NGINX_CONFIG" ] || WONIUNOTE_NGINX_CONFIG="$value" ;;
            WONIUNOTE_SSL_CERT) [ -n "$WONIUNOTE_SSL_CERT" ] || WONIUNOTE_SSL_CERT="$value" ;;
            WONIUNOTE_SSL_KEY) [ -n "$WONIUNOTE_SSL_KEY" ] || WONIUNOTE_SSL_KEY="$value" ;;
            WONIUNOTE_SMOKE_UPLOAD_PATH) [ -n "$WONIUNOTE_SMOKE_UPLOAD_PATH" ] || WONIUNOTE_SMOKE_UPLOAD_PATH="$value" ;;
            WONIUNOTE_SMOKE_UPLOAD_FILE) [ -n "$WONIUNOTE_SMOKE_UPLOAD_FILE" ] || WONIUNOTE_SMOKE_UPLOAD_FILE="$value" ;;
            WONIUNOTE_SMOKE_UPLOAD_SHA256) [ -n "$WONIUNOTE_SMOKE_UPLOAD_SHA256" ] || WONIUNOTE_SMOKE_UPLOAD_SHA256="$value" ;;
            WONIUNOTE_SMOKE_HOST) [ -n "$WONIUNOTE_SMOKE_HOST" ] || WONIUNOTE_SMOKE_HOST="$value" ;;
            WONIUNOTE_SMOKE_SCHEME) [ -n "$WONIUNOTE_SMOKE_SCHEME" ] || WONIUNOTE_SMOKE_SCHEME="$value" ;;
            WONIUNOTE_SMOKE_PORT) [ -n "$WONIUNOTE_SMOKE_PORT" ] || WONIUNOTE_SMOKE_PORT="$value" ;;
            WONIUNOTE_SMOKE_READONLY_API) [ -n "$WONIUNOTE_SMOKE_READONLY_API" ] || WONIUNOTE_SMOKE_READONLY_API="$value" ;;
            WONIUNOTE_SMOKE_THUMB_PATH) [ -n "$WONIUNOTE_SMOKE_THUMB_PATH" ] || WONIUNOTE_SMOKE_THUMB_PATH="$value" ;;
            WONIUNOTE_COMPATIBILITY_RECORD) [ -n "$WONIUNOTE_COMPATIBILITY_RECORD" ] || WONIUNOTE_COMPATIBILITY_RECORD="$value" ;;
            WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD) [ -n "$WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD" ] || WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$value" ;;
        esac
    done < "$DEFAULTS"
fi
export WONIUNOTE_PROJECT_DIR WONIUNOTE_STATE_DIR WONIUNOTE_DATA_DIR WONIUNOTE_RUNTIME_CONFIG
export WONIUNOTE_NGINX_CONFIG WONIUNOTE_SSL_CERT WONIUNOTE_SSL_KEY
export WONIUNOTE_SMOKE_UPLOAD_PATH WONIUNOTE_SMOKE_UPLOAD_FILE WONIUNOTE_SMOKE_UPLOAD_SHA256
export WONIUNOTE_SMOKE_HOST WONIUNOTE_SMOKE_SCHEME WONIUNOTE_SMOKE_PORT
export WONIUNOTE_SMOKE_READONLY_API WONIUNOTE_SMOKE_THUMB_PATH
export WONIUNOTE_COMPATIBILITY_RECORD WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD
PROJECT_DIR="$WONIUNOTE_PROJECT_DIR"
[ -n "$PROJECT_DIR" ] || PROJECT_DIR="$APP_DIR"
if [ ! -e "$PROJECT_DIR/.git" ] && [ -f "$APP_DIR/.woniunote-source-repo" ]; then IFS= read -r PROJECT_DIR < "$APP_DIR/.woniunote-source-repo"; fi
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
STATE="$WONIUNOTE_STATE_DIR"
if [ -z "$STATE" ]; then
    if [ "$EUID" -eq 0 ]; then STATE=/var/lib/woniunote
    else
        project_lock_id="$(printf '%s' "$PROJECT_DIR" | shasum -a 256 | cut -c1-12)"
        STATE="${TMPDIR:-/tmp}/woniunote-$UID-$project_lock_id"
    fi
fi
DATA="$WONIUNOTE_DATA_DIR"; [ -n "$DATA" ] || DATA="$PROJECT_DIR/backend_cpp"
CONFIG_REVISIONS="$DATA/config-revisions"
CONFIG="$WONIUNOTE_RUNTIME_CONFIG"
if [ -z "$CONFIG" ]; then
    if [ -f "$PROJECT_DIR/backend_cpp/config.local.json" ]; then CONFIG="$PROJECT_DIR/backend_cpp/config.local.json"
    elif [ -f /etc/woniunote/config.json ]; then CONFIG=/etc/woniunote/config.json
    else CONFIG="$PROJECT_DIR/backend_cpp/config.prod.json"; fi
fi
NGINX_CONF="$WONIUNOTE_NGINX_CONFIG"; [ -n "$NGINX_CONF" ] || NGINX_CONF=/etc/nginx/nginx.conf
UNIT="$WONIUNOTE_SYSTEMD_UNIT"; [ -n "$UNIT" ] || UNIT=/etc/systemd/system/woniunote.service
SERVICE="$WONIUNOTE_SERVICE_NAME"; [ -n "$SERVICE" ] || SERVICE=woniunote
NGINX_SERVICE="$WONIUNOTE_NGINX_SERVICE_NAME"; [ -n "$NGINX_SERVICE" ] || NGINX_SERVICE=nginx
BUILD_JOBS="$WONIUNOTE_BUILD_JOBS"; [ -n "$BUILD_JOBS" ] || BUILD_JOBS=4
STOP_SECONDS="$WONIUNOTE_STOP_TIMEOUT_SECONDS"; [ -n "$STOP_SECONDS" ] || STOP_SECONDS=10
START_SECONDS="$WONIUNOTE_START_TIMEOUT_SECONDS"; [ -n "$START_SECONDS" ] || START_SECONDS=10
HEALTH_SECONDS="$WONIUNOTE_HEALTH_TIMEOUT_SECONDS"; [ -n "$HEALTH_SECONDS" ] || HEALTH_SECONDS=14
SMOKE_SECONDS="$WONIUNOTE_SMOKE_TIMEOUT_SECONDS"; [ -n "$SMOKE_SECONDS" ] || SMOKE_SECONDS=2
RECOVERY_SECONDS="$WONIUNOTE_RECOVERY_BUDGET_SECONDS"; [ -n "$RECOVERY_SECONDS" ] || RECOVERY_SECONDS=60
RETENTION=$((7 * 86400)); CURRENT="$STATE/current"; ROLLBACK="$STATE/rollback"
RELEASES="$STATE/releases"; ASSETS="$STATE/assets"; META="$STATE/metadata"
TXNS="$STATE/transactions"; LOCK="$STATE/deploy.lock"; ACTIVE_TX="$STATE/active-transaction"

for bounded_value in "$STOP_SECONDS:10:stop" "$START_SECONDS:30:start" "$HEALTH_SECONDS:30:health" "$SMOKE_SECONDS:30:smoke" "$RECOVERY_SECONDS:60:recovery"; do
    IFS=: read -r bounded_seconds bounded_max bounded_name <<EOF
$bounded_value
EOF
    [[ "$bounded_seconds" =~ ^[0-9]+$ ]] && [ "$bounded_seconds" -ge 1 ] && [ "$bounded_seconds" -le "$bounded_max" ] || {
        printf '[deploy] ERROR: %s timeout must be 1..%s seconds.\n' "$bounded_name" "$bounded_max" >&2
        exit 2
    }
done
FAILURE_TRIGGER_SECONDS=30
TRANSITION_DEADLINE=0
RECOVERY_DEADLINE=0
IN_RECOVERY=no

# util-linux flock holds the lock in its parent process and closes the lock FD
# in the command it starts. This avoids both the mkdir/owner-file race and
# leaking a lock descriptor into long-lived backend processes.
lock_owner_is_ancestor() {
    local dev_hex dev_num major minor dev_key inode owner parent proc_parent
    if [ -r /proc/locks ] && [ -d "/proc/$$" ]; then
        dev_hex="$(stat -Lc '%D' "$LOCK" 2>/dev/null)" || return 1
        inode="$(stat -Lc '%i' "$LOCK" 2>/dev/null)" || return 1
        [[ "$dev_hex" =~ ^[0-9a-fA-F]+$ && "$inode" =~ ^[0-9]+$ ]] || return 1
        dev_num=$((16#$dev_hex))
        major=$((((dev_num >> 8) & 0xfff) | ((dev_num >> 32) & 0xfffff000)))
        minor=$(((dev_num & 0xff) | ((dev_num >> 12) & 0xffffff00)))
        dev_key="$(printf '%02x:%02x' "$major" "$minor")"
        while IFS= read -r owner; do
            [[ "$owner" =~ ^[0-9]+$ ]] || continue
            parent="$PPID"
            while [[ "$parent" =~ ^[0-9]+$ ]] && [ "$parent" -gt 1 ]; do
                [ "$parent" = "$owner" ] && return 0
                [ -r "/proc/$parent/status" ] || break
                proc_parent="$(awk '$1 == "PPid:" {print $2}' "/proc/$parent/status")"
                [ -n "$proc_parent" ] || break
                parent="$proc_parent"
            done
        done < <(awk -v dev="$dev_key" -v inode="$inode" '
            $2 == "FLOCK" && $4 == "WRITE" {
                split($6, identity, ":")
                if (tolower(identity[1] ":" identity[2]) == tolower(dev) && identity[3] == inode) print $5
            }' /proc/locks)
        return 1
    fi
    # The macOS unit harness has no /proc/locks. Its fake flock exports a proof
    # only to the child while holding this fixture-local lock directory.
    if [ "$WONIUNOTE_DEPLOY_TESTING" = 1 ] &&
       [ "$WONIUNOTE_TEST_LOCK_PROOF" = "$LOCK.mock-lock" ] && [ -d "$LOCK.mock-lock" ]; then
        case "$STATE" in */woniunote-deploy-test.*/state) return 0 ;; esac
    fi
    return 1
}
if [ "$1" = "__locked" ]; then
    shift
    if ! lock_owner_is_ancestor; then
        printf '[deploy] ERROR: 内部锁入口没有可验证的 flock 持锁祖先进程。\n' >&2
        exit 1
    fi
    LOCK_HELD=yes
elif [ "$1" = "assert-locked" ]; then
    lock_owner_is_ancestor || { printf '[deploy] ERROR: 没有可验证的部署锁祖先进程。\n' >&2; exit 1; }
    LOCK_HELD=yes
elif [ "$1" != status ]; then
    mkdir -p "$STATE"
    if [ "$EUID" -ne 0 ]; then chmod 0700 "$STATE"; fi
    command -v flock >/dev/null 2>&1 || { printf '[deploy] ERROR: 需要 util-linux flock，拒绝无锁部署。\n' >&2; exit 1; }
    if lock_owner_is_ancestor; then
        LOCK_HELD=yes
    else
        if flock -n -E 75 -o "$LOCK" bash "$SCRIPT_DIR/deploy_release.sh" __locked "$@"; then
            exit 0
        else
            lock_status=$?
            if [ "$lock_status" -eq 75 ]; then printf '[deploy] ERROR: 部署锁已被其他任务持有。\n' >&2; fi
            exit "$lock_status"
        fi
    fi
fi
if [ "$LOCK_HELD" = yes ] && [ "$WONIUNOTE_DEPLOY_TESTING" = 1 ] && [ -n "$WONIUNOTE_TEST_PID_FILE" ]; then
    printf '%s\n' "$$" > "$WONIUNOTE_TEST_PID_FILE"
fi

fail() { printf '[deploy] ERROR: %s\n' "$*" >&2; return 1; }
hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
with_budget() {
    local limit="$1" deadline remaining
    shift
    deadline="$TRANSITION_DEADLINE"
    [ "$RECOVERY_DEADLINE" -le 0 ] || deadline="$RECOVERY_DEADLINE"
    if [ "$deadline" -gt 0 ]; then
        remaining=$((deadline - SECONDS))
        [ "$remaining" -gt 0 ] || return 124
        [ "$limit" -le "$remaining" ] || limit="$remaining"
    fi
    timeout "${limit}s" "$@"
}
check_transition_deadline() {
    [ "$TRANSITION_DEADLINE" -le 0 ] || [ "$SECONDS" -lt "$TRANSITION_DEADLINE" ] || {
        fail "30 秒部署切换预算已耗尽"; return 1;
    }
}
now() {
    if [ "$WONIUNOTE_DEPLOY_TESTING" = 1 ] && [ -n "$WONIUNOTE_TEST_NOW" ]; then printf '%s\n' "$WONIUNOTE_TEST_NOW"
    else date +%s; fi
}
root_only() {
    if [ "$EUID" -ne 0 ] && [ "$WONIUNOTE_DEPLOY_TESTING" != 1 ]; then
        fail "生产切换需要 root 权限；请使用 sudo bash $APP_DIR/start_app.sh prod"; exit 1
    fi
}
replace_file() {
    if mv -Tf "$1" "$2" 2>/dev/null; then return 0; fi
    mv -fh "$1" "$2"
}
unlock() { :; }
trap ':' EXIT
lock_target() { [ "$LOCK_HELD" = yes ] || { fail "命令未持有部署锁"; return 1; }; }
active() { timeout 2s systemctl is-active --quiet "$SERVICE" >/dev/null 2>&1; }
wait_health() {
    local max="$1" deadline=$((SECONDS + $1)) n=0
    if [ "$TRANSITION_DEADLINE" -gt 0 ] && [ "$TRANSITION_DEADLINE" -lt "$deadline" ]; then deadline="$TRANSITION_DEADLINE"; fi
    if [ "$RECOVERY_DEADLINE" -gt 0 ] && [ "$RECOVERY_DEADLINE" -lt "$deadline" ]; then deadline="$RECOVERY_DEADLINE"; fi
    while [ "$SECONDS" -lt "$deadline" ]; do
        with_budget 1 curl -fsS --max-time 1 http://127.0.0.1:5173/health >/dev/null 2>&1 && return 0
        sleep 0.2; n=$((n + 1))
    done
    return 1
}
smoke() {
    local release="$1" dir="$2" host scheme port base api thumb upload expected asset i recorded
    host="$WONIUNOTE_SMOKE_HOST"; [ -n "$host" ] || host=yunjinqi.top
    scheme="$WONIUNOTE_SMOKE_SCHEME"; [ -n "$scheme" ] || scheme=https
    port="$WONIUNOTE_SMOKE_PORT"
    if [ -z "$port" ]; then [ "$scheme" = https ] && port=443 || port=80; fi
    if [ -n "$WONIUNOTE_SMOKE_PORT" ]; then base="$scheme://$host:$port"; else base="$scheme://$host"; fi
    validate_frontend_assets "$release/frontend/dist" "$release/assets.manifest" "$dir/entry-assets.refs" || return 1
    with_budget "$SMOKE_SECONDS" curl -kfsS --max-time "$SMOKE_SECONDS" --resolve "$host:$port:127.0.0.1" -o "$dir/index.body" "$base/" || { fail "首页 HTTP 冒烟失败"; return 1; }
    [ -s "$dir/index.body" ] || { fail "首页响应体为空"; return 1; }
    [ "$(hash_file "$dir/index.body")" = "$(hash_file "$release/frontend/dist/index.html")" ] || {
        fail "首页响应内容与冻结候选 index.html 不一致"; return 1;
    }
    i=0
    while IFS= read -r asset; do
        i=$((i + 1)); expected="$dir/entry-asset-$i.body"
        with_budget "$SMOKE_SECONDS" curl -kfsS --max-time "$SMOKE_SECONDS" --resolve "$host:$port:127.0.0.1" \
            -o "$expected" "$base/$asset" || { fail "候选 JS/CSS 入口资源 HTTP 请求失败: $asset"; return 1; }
        [ -s "$expected" ] || { fail "候选 JS/CSS 入口资源响应体为空: $asset"; return 1; }
        recorded="$(manifest_asset_sha "$release/assets.manifest" "$asset")" || {
            fail "候选 JS/CSS 入口资源 manifest 记录无效: $asset"; return 1;
        }
        [ "$(hash_file "$expected")" = "$recorded" ] || {
            fail "HTTP JS/CSS 入口响应内容与冻结候选不一致: $asset"; return 1;
        }
    done < "$dir/entry-assets.refs"
    api="$WONIUNOTE_SMOKE_READONLY_API"; [ -n "$api" ] || api=/api/articles/types
    with_budget "$SMOKE_SECONDS" curl -kfsS --max-time "$SMOKE_SECONDS" --resolve "$host:$port:127.0.0.1" -o "$dir/api.body" "$base$api" || { fail "只读 API 冒烟请求失败"; return 1; }
    [ -s "$dir/api.body" ] && grep -Eq '"code"[[:space:]]*:[[:space:]]*200' "$dir/api.body" || { fail "只读 API 冒烟响应无成功码"; return 1; }
    thumb="$WONIUNOTE_SMOKE_THUMB_PATH"; [ -n "$thumb" ] || thumb=/api/thumb/1.png
    with_budget "$SMOKE_SECONDS" curl -kfsS --max-time "$SMOKE_SECONDS" --resolve "$host:$port:127.0.0.1" -o "$dir/thumb.body" "$base$thumb" || { fail "缩略图冒烟请求失败"; return 1; }
    [ -s "$dir/thumb.body" ] || { fail "缩略图响应体为空"; return 1; }
    upload="$WONIUNOTE_SMOKE_UPLOAD_PATH"
    [ -n "$upload" ] || { fail "必须配置一个已存在的持久上传文件用于 smoke"; return 1; }
    case "$upload" in /api/uploads/*|/uploads/*) ;; *) fail "上传冒烟路径必须是 /api/uploads/... 或 /uploads/..."; return 1 ;; esac
    expected="$WONIUNOTE_SMOKE_UPLOAD_SHA256"
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { fail "必须配置持久上传样例的 SHA-256"; return 1; }
    upload="$base$upload"
    with_budget "$SMOKE_SECONDS" curl -kfsS --max-time "$SMOKE_SECONDS" --resolve "$host:$port:127.0.0.1" -o "$dir/upload.body" "$upload" || { fail "持久上传冒烟请求失败"; return 1; }
    [ -s "$dir/upload.body" ] && [ "$(hash_file "$dir/upload.body")" = "$expected" ] || { fail "持久上传样例缺失或内容 SHA-256 不匹配"; return 1; }
}
validate_smoke_upload() {
    local upload file expected data_root resolved
    upload="$WONIUNOTE_SMOKE_UPLOAD_PATH"
    file="$WONIUNOTE_SMOKE_UPLOAD_FILE"
    expected="$WONIUNOTE_SMOKE_UPLOAD_SHA256"
    [ -n "$upload" ] && [ -n "$file" ] && [ -n "$expected" ] || {
        fail "必须配置持久上传冒烟的 URL、服务器文件路径和 SHA-256"; return 1;
    }
    case "$upload" in /api/uploads/*|/uploads/*) ;; *) fail "上传冒烟路径必须是 /api/uploads/... 或 /uploads/..."; return 1 ;; esac
    case "$file" in /*) ;; *) fail "上传冒烟文件必须使用绝对路径"; return 1 ;; esac
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { fail "持久上传样例 SHA-256 格式错误"; return 1; }
    [ -f "$file" ] || { fail "持久上传样例文件不存在"; return 1; }
    data_root="$(realpath -m "$DATA")"; resolved="$(realpath "$file")"
    case "$resolved" in "$data_root"/*) ;; *) fail "上传冒烟文件必须位于共享持久数据目录"; return 1 ;; esac
    [ "$(hash_file "$resolved")" = "$expected" ] || { fail "持久上传样例文件 SHA-256 不匹配"; return 1; }
}
render_nginx() {
    local template="$1" output="$2" static="$CURRENT/frontend/dist" root="$STATE" cert="$WONIUNOTE_SSL_CERT" key="$WONIUNOTE_SSL_KEY"
    [ -n "$cert" ] || cert=/etc/ssl/woniunote/fullchain.pem
    [ -n "$key" ] || key=/etc/ssl/woniunote/privkey.pem
    static="$(printf '%s' "$static" | sed 's/[&|]/\\&/g')"
    root="$(printf '%s' "$root" | sed 's/[&|]/\\&/g')"
    cert="$(printf '%s' "$cert" | sed 's/[&|]/\\&/g')"
    key="$(printf '%s' "$key" | sed 's/[&|]/\\&/g')"
    sed -e "s|@@WONIUNOTE_STATIC_ROOT@@|$static|g" -e "s|@@WONIUNOTE_ASSET_ROOT@@|$root|g" \
        -e "s|@@WONIUNOTE_SSL_CERT@@|$cert|g" -e "s|@@WONIUNOTE_SSL_KEY@@|$key|g" "$template" > "$output"
    if grep -Eq '@@WONIUNOTE_[A-Z_]+@@' "$output"; then fail "Nginx 模板含未替换占位符"; return 1; fi
}
snapshot_legacy_nginx() {
    local source="$1" output="$2" legacy_release="$3" project_static="$PROJECT_DIR/frontend/dist"
    # A copied legacy config is only a rollback snapshot when every file root
    # it serves is either the old project dist (which is pinned below) or
    # persistent shared data. Includes and unknown roots could still resolve
    # through mutable paths, so refuse the first migration instead of claiming
    # that an incomplete snapshot is immutable.
    awk '
        {
            line = $0
            sub(/[[:space:]]*#.*/, "", line)
            if (line ~ /(^|[[:space:];{}])(include|root|alias)[[:space:]]+/) {
                if (line ~ /^[[:space:]]*include[[:space:]]+/) {
                    path = line
                    sub(/^[[:space:]]*include[[:space:]]+/, "", path)
                    sub(/[[:space:]]*;.*/, "", path)
                    if (path != "/etc/nginx/mime.types" || line !~ /^[[:space:]]*include[[:space:]]+[^;]+;[[:space:]]*$/)
                        unsupported_directive = 1
                } else if (line !~ /^[[:space:]]*(root|alias)[[:space:]]+[^;]+;[[:space:]]*$/) {
                    # This line has an inline or repeated file-serving directive.
                    # Refuse to snapshot a config we cannot fully classify.
                    unsupported_directive = 1
                }
            }
        }
        END { if (unsupported_directive) exit 42 }
    ' "$source" || { fail "旧 Nginx 配置含无法完整解析的 include/root/alias，拒绝创建不完整 legacy 回滚版"; return 1; }
    awk -v old="$project_static" -v data="$DATA" -v legacy="$legacy_release" '
        function strip_quotes(value) {
            if (substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"")
                return substr(value, 2, length(value) - 2)
            return value
        }
        function normalize_path(value) {
            gsub(/\/\/+/, "/", value)
            if (length(value) > 1) sub(/\/+$/, "", value)
            return value
        }
        function replace_first(line, needle, replacement, position) {
            position = index(line, needle)
            if (position == 0) return line
            return substr(line, 1, position - 1) replacement substr(line, position + length(needle))
        }
        {
            original = $0
            code = original
            sub(/[[:space:]]*#.*/, "", code)
            if (code ~ /^[[:space:]]*(root|alias)[[:space:]]/) {
                path = code
                sub(/^[[:space:]]*(root|alias)[[:space:]]+/, "", path)
                sub(/[[:space:]]*;.*/, "", path)
                path = strip_quotes(path)
                normalized = normalize_path(path)
                old_normalized = normalize_path(old)
                data_normalized = normalize_path(data)
                if (normalized == old_normalized || index(normalized, old_normalized "/") == 1) {
                    pinned++
                    suffix = substr(normalized, length(old_normalized) + 1)
                    original = replace_first(original, path, legacy "/frontend/dist" suffix)
                } else if (normalized == data_normalized || index(normalized, data_normalized "/") == 1) {
                    persistent++
                } else {
                    unknown++
                }
            }
            print original
        }
        END {
            if (pinned == 0 || unknown > 0) {
                printf "legacy Nginx root classification: pinned=%d unknown=%d\n", pinned, unknown > "/dev/stderr"
                exit 42
            }
        }
    ' "$source" > "$output" || {
        rm -f "$output"
        fail "旧 Nginx root/alias 无法完整绑定到 legacy dist 或共享数据目录，拒绝迁移"
        return 1
    }
    [ -d "$legacy_release/frontend/dist" ] || {
        rm -f "$output"
        fail "legacy frontend/dist 快照缺失，拒绝绑定旧 Nginx root"
        return 1
    }
    timeout 5s nginx -t -c "$output" >/dev/null || {
        rm -f "$output"
        fail "冻结后的 legacy Nginx 配置未通过真实 nginx -t"
        return 1
    }
}
hashed_asset() { [[ "$1" =~ -[A-Za-z0-9_-]{8,}\.(js|mjs|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ ]]; }
register_assets() {
    local dist="$1" release="$2" file name stored_name sha old tmp
    mkdir -p "$ASSETS"; : > "$release/assets.manifest"
    while IFS= read -r -d '' file; do
        name="$(printf '%s' "$file" | sed "s|^$dist/||")"; hashed_asset "$name" || continue
        [[ "$name" != *"/../"* && "$name" != ../* && "$name" != */.. ]] || { fail "资源路径越界"; return 1; }
        [[ "$name" = assets/* ]] || { fail "构建资源路径不是 /assets/: $name"; return 1; }
        stored_name="${name#assets/}"
        sha="$(hash_file "$file")"; mkdir -p "$ASSETS/$(dirname "$stored_name")"
        if [ -e "$ASSETS/$stored_name" ]; then
            old="$(hash_file "$ASSETS/$stored_name")"; [ "$old" = "$sha" ] || { fail "hash 资源同名异内容: $name"; return 1; }
        else
            tmp="$ASSETS/.asset.$$.$RANDOM"; cp "$file" "$tmp"; chmod 0644 "$tmp"; replace_file "$tmp" "$ASSETS/$stored_name"
        fi
        printf '%s  %s\n' "$sha" "$name" >> "$release/assets.manifest"
    done < <(find "$dist/assets" -type f -print0 2>/dev/null || true)
    sort -u "$release/assets.manifest" -o "$release/assets.manifest"
}
entry_asset_refs() {
    local index_file="$1" output="$2"
    node - "$index_file" > "$output" <<'NODE'
const fs = require('fs');
const file = process.argv[2];
const html = fs.readFileSync(file, 'utf8').replace(/<!--[\s\S]*?-->/g, '');
const refs = new Set();
const tagPattern = /<(script|link)\b((?:[^"'<>]|"[^"]*"|'[^']*')*)>/gi;
let match;
while ((match = tagPattern.exec(html)) !== null) {
  const tagName = match[1].toLowerCase();
  const attrs = Object.create(null);
  const attrPattern = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let attr;
  while ((attr = attrPattern.exec(match[2])) !== null) {
    attrs[attr[1].toLowerCase()] = typeof attr[2] === 'string' ? attr[2] :
      typeof attr[3] === 'string' ? attr[3] : typeof attr[4] === 'string' ? attr[4] : '';
  }
  const value = tagName === 'script' ? attrs.src : attrs.href;
  if (typeof value !== 'string' || !value.startsWith('/assets/')) continue;
  const path = value.split(/[?#]/, 1)[0];
  if (!/\.(?:m?js|css)$/.test(path)) continue;
  if (!/^\/assets\/[A-Za-z0-9._/-]+$/.test(path) || path.includes('//') ||
      path.split('/').some(part => part === '.' || part === '..')) {
    throw new Error(`unsafe local entry asset path: ${path}`);
  }
  refs.add(path.slice(1));
}
const sorted = [...refs].sort();
if (!sorted.some(path => /\.m?js$/.test(path))) {
  throw new Error('index.html has no local JavaScript entry asset');
}
process.stdout.write(sorted.join('\n') + '\n');
NODE
}
manifest_asset_sha() {
    local manifest="$1" path="$2"
    awk -v wanted="$path" '$2 == wanted { if (length($1) == 64 && $1 ~ /^[0-9a-f]+$/) { print $1; found++ } else exit 2 } END { if (found != 1) exit 1 }' "$manifest"
}
validate_frontend_assets() {
    local dist="$1" manifest="$2" refs="$3" asset file sha recorded
    [ -f "$dist/index.html" ] && [ ! -L "$dist/index.html" ] || { fail "候选前端 index.html 缺失或不是普通文件"; return 1; }
    [ -f "$manifest" ] && [ ! -L "$manifest" ] || { fail "候选前端 hash 资源 manifest 缺失"; return 1; }
    entry_asset_refs "$dist/index.html" "$refs" || { fail "index.html 的本地 JS/CSS 入口引用无法安全解析"; return 1; }
    [ -s "$refs" ] || { fail "index.html 未引用本地 JS/CSS 入口资源"; return 1; }
    while IFS= read -r asset; do
        [[ "$asset" = assets/* && "$asset" != *$'\t'* && "$asset" != *$'\n'* ]] || {
            fail "index.html 入口资源路径无效"; return 1;
        }
        hashed_asset "${asset#assets/}" || { fail "index.html 入口不是内容 hash 资源: $asset"; return 1; }
        file="$dist/$asset"
        [ -f "$file" ] && [ ! -L "$file" ] || { fail "index.html 引用的入口文件缺失或不是普通文件: $asset"; return 1; }
        sha="$(hash_file "$file")" || { fail "入口资源摘要计算失败: $asset"; return 1; }
        recorded="$(manifest_asset_sha "$manifest" "$asset")" || {
            fail "入口资源未以唯一有效记录绑定到 hash manifest: $asset"; return 1;
        }
        [ "$sha" = "$recorded" ] || { fail "入口资源内容与 hash manifest 不一致: $asset"; return 1; }
    done < "$refs"
}
link_persistent() {
    local backend="$1" rel target link file relative copied
    for target in "$DATA/build/logs" "$DATA/build/uploads" "$DATA/uploads" "$DATA/resource/thumb"; do mkdir -p "$target"; done
    mkdir -p "$backend/build" "$backend/resource"
    while IFS=: read -r rel target; do
        link="$backend/$rel"; mkdir -p "$(dirname "$link")" "$target"
        if [ -e "$link" ] && [ ! -L "$link" ]; then
            [ -d "$link" ] || { fail "候选持久路径不是目录: $link"; return 1; }
            [ -z "$(find "$link" -type l -print -quit)" ] || { fail "候选持久目录含符号链接: $link"; return 1; }
            [ -z "$(find "$link" ! -type d ! -type f -print -quit)" ] || { fail "候选持久目录含特殊文件: $link"; return 1; }
            while IFS= read -r -d '' file; do
                relative="${file#"$link"/}"; copied="$target/$relative"
                mkdir -p "$(dirname "$copied")" || { fail "无法创建持久目标目录: $copied"; return 1; }
                if [ -e "$copied" ] || [ -L "$copied" ]; then
                    [ -f "$copied" ] && [ ! -L "$copied" ] && [ "$(hash_file "$file")" = "$(hash_file "$copied")" ] || {
                        fail "持久数据与候选同名异内容: $relative"; return 1;
                    }
                else
                    cp -p "$file" "$copied" || { fail "候选持久文件复制失败: $relative"; return 1; }
                fi
                [ -f "$copied" ] && [ ! -L "$copied" ] && [ "$(hash_file "$file")" = "$(hash_file "$copied")" ] || {
                    fail "候选持久文件复制核验失败: $relative"; return 1;
                }
            done < <(find "$link" -type f -print0)
            rm -rf -- "$link" || { fail "已核验候选持久目录无法移除: $link"; return 1; }
        fi
        if [ -L "$link" ] && [ "$(readlink "$link")" != "$target" ]; then rm -f "$link"; fi
        [ -e "$link" ] || ln -s "$target" "$link"
    done <<EOF
build/logs:$DATA/build/logs
build/uploads:$DATA/build/uploads
uploads:$DATA/uploads
resource/thumb:$DATA/resource/thumb
EOF
}
value() { [ -f "$1" ] || return 0; awk -F= -v key="$2" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$1"; }
verify_compat() {
    local from="$1" to="$2" record="$3" evidence expected
    [ -f "$record" ] || { fail "缺少 D04 兼容性记录"; return 1; }
    [ "$(value "$record" FROM_SHA)" = "$from" ] && [ "$(value "$record" TO_SHA)" = "$to" ] && \
        [ "$(value "$record" API)" = PASS ] && [ "$(value "$record" SESSION)" = PASS ] && [ "$(value "$record" SCHEMA)" = PASS ] && \
        [ "$(value "$record" OLD_FRONTEND_NEW_BACKEND)" = PASS ] && [ "$(value "$record" NEW_FRONTEND_OLD_BACKEND)" = PASS ] || {
            fail "D04 记录未绑定当前 SHA 或兼容维度未通过"; return 1;
        }
    evidence="$(value "$record" EVIDENCE)"; expected="$(value "$record" EVIDENCE_SHA256)"
    case "$evidence" in /*) ;; *) evidence="$PROJECT_DIR/$evidence" ;; esac
    [ -f "$evidence" ] && [ "$(hash_file "$evidence")" = "$expected" ] || { fail "D04 证据缺失或 SHA-256 不匹配"; return 1; }
}
verify_initial_install() {
    local to="$1" record="${WONIUNOTE_INITIAL_INSTALL_RECORD:-}" mode reviewed evidence expected uid perms
    [ -n "$record" ] && [ -f "$record" ] && [ ! -L "$record" ] || {
        fail "没有当前 release 且服务未运行；首次安装需要显式证据记录"; return 1;
    }
    perms="$(stat -c '%a' "$record" 2>/dev/null || stat -f '%Lp' "$record" 2>/dev/null)" || {
        fail "首次安装记录权限不可验证"; return 1;
    }
    [ "$perms" = 600 ] || { fail "首次安装记录必须是 0600 文件"; return 1; }
    if [ "$WONIUNOTE_DEPLOY_TESTING" != 1 ]; then
        uid="$(stat -c '%u' "$record" 2>/dev/null || stat -f '%u' "$record" 2>/dev/null)" || {
            fail "首次安装记录所有者不可验证"; return 1;
        }
        [ "$uid" = 0 ] || { fail "首次安装记录必须由 root 持有"; return 1; }
    fi
    awk -F= '
        NF < 2 || $1 !~ /^[A-Z0-9_]+$/ || seen[$1]++ { exit 1 }
        $1 !~ /^(TO_SHA|MODE|REVIEWED|EVIDENCE|EVIDENCE_SHA256|EDITOR_HANDOFF|WRITE_FREEZE|BACKUP_RESTORE|SCHEMA|FRESH_INSTANCE)$/ { exit 1 }
    ' "$record" || { fail "首次安装记录字段格式无效或含重复/未知字段"; return 1; }
    [ "$(value "$record" TO_SHA)" = "$to" ] || { fail "首次安装记录未绑定候选完整 SHA"; return 1; }
    mode="$(value "$record" MODE)"; reviewed="$(value "$record" REVIEWED)"
    [ "$reviewed" = PASS ] || { fail "首次安装记录缺少显式 REVIEWED=PASS"; return 1; }
    evidence="$(value "$record" EVIDENCE)"; expected="$(value "$record" EVIDENCE_SHA256)"
    [[ "$evidence" = /* && "$expected" =~ ^[0-9a-f]{64}$ ]] || {
        fail "首次安装证据必须使用绝对路径并绑定 SHA-256"; return 1;
    }
    [ -f "$evidence" ] && [ ! -L "$evidence" ] || { fail "首次安装审阅证据缺失或不是普通文件"; return 1; }
    [ "$(hash_file "$evidence")" = "$expected" ] || { fail "首次安装审阅证据 SHA-256 不匹配"; return 1; }
    case "$mode" in
        fresh)
            [ "$(value "$record" FRESH_INSTANCE)" = PASS ] &&
                [ -z "$(value "$record" EDITOR_HANDOFF)" ] &&
                [ -z "$(value "$record" WRITE_FREEZE)" ] &&
                [ -z "$(value "$record" BACKUP_RESTORE)" ] &&
                [ -z "$(value "$record" SCHEMA)" ] || {
                fail "fresh 首次安装记录的模式专属状态无效"; return 1;
            }
            ;;
        maintenance)
            [ "$(value "$record" EDITOR_HANDOFF)" = PASS ] &&
                [ "$(value "$record" WRITE_FREEZE)" = PASS ] &&
                [ "$(value "$record" BACKUP_RESTORE)" = PASS ] &&
                [ "$(value "$record" SCHEMA)" = PASS ] &&
                [ -z "$(value "$record" FRESH_INSTANCE)" ] || {
                    fail "maintenance 首次安装记录未绑定编辑器交接、写入冻结、备份恢复和 schema 检查"; return 1;
                }
            ;;
        *) fail "首次安装记录 MODE 必须是 fresh 或 maintenance"; return 1 ;;
    esac
}
write_unit() {
    cat > "$1" <<EOF
[Unit]
Description=WoniuNote C++ Backend Service
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service
[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT/backend_cpp/build
ExecStart=/bin/bash $CURRENT/backend_cpp/release_run_backend.sh $CURRENT
KillSignal=SIGTERM
TimeoutStopSec=10
SendSIGKILL=yes
Restart=on-failure
RestartSec=2
Environment=LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/lib
StandardOutput=append:$DATA/build/logs/backend.log
StandardError=append:$DATA/build/logs/backend-error.log
[Install]
WantedBy=multi-user.target
EOF
    chmod 0644 "$1"
}
pointer() {
    local link="$1" target="$2" tmp="$STATE/.$(basename "$link").next.$$"
    rm -f "$tmp"
    if [ -n "$target" ]; then ln -s "$target" "$tmp" && replace_file "$tmp" "$link"; else rm -f "$link"; fi
}
phase() { local tmp="$1/phase.tmp.$$"; printf '%s\n' "$2" > "$tmp"; replace_file "$tmp" "$1/phase"; }
state_write() {
    local file="$META/$(basename "$1").env" tmp="$META/.meta.$$.$RANDOM"
    mkdir -p "$META"; printf 'retired_at=%s\n' "$2" > "$tmp"; replace_file "$tmp" "$file"
}
retired() { local file="$META/$(basename "$1").env"; [ -f "$file" ] && sed -n 's/^retired_at=//p' "$file" | head -1 || printf '0\n'; }
verify_release_config() {
    local release="$1" expected config_path mode
    [ -f "$release/runtime-config.ref" ] && [ -f "$release/runtime-config.sha256" ] || { fail "release runtime config 引用缺失"; return 1; }
    expected="$(cat "$release/runtime-config.sha256")"
    IFS= read -r config_path < "$release/runtime-config.ref"
    [ "$config_path" = "$CONFIG_REVISIONS/$expected.json" ] || { fail "release runtime config 引用无效"; return 1; }
    if stat -c '%a' "$config_path" >/dev/null 2>&1; then mode="$(stat -c '%a' "$config_path")"
    else mode="$(stat -f '%Lp' "$config_path" 2>/dev/null || true)"; fi
    [ -f "$config_path" ] && [ ! -L "$config_path" ] && [ "$mode" = 600 ] && [[ "$expected" =~ ^[0-9a-f]{64}$ ]] &&
        [ "$(hash_file "$config_path")" = "$expected" ] || { fail "共享 runtime config 摘要不匹配"; return 1; }
}
store_config_revision() {
    local expected="$1" source="${2:-$CONFIG}" target="$CONFIG_REVISIONS/$1.json" tmp
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { fail "运行配置 SHA-256 格式错误"; return 1; }
    [ ! -L "$CONFIG_REVISIONS" ] || { fail "共享 runtime config 目录不能是符号链接"; return 1; }
    mkdir -p "$CONFIG_REVISIONS" && chmod 0700 "$CONFIG_REVISIONS" || { fail "无法保护共享 runtime config 目录"; return 1; }
    local directory_mode
    if stat -c '%a' "$CONFIG_REVISIONS" >/dev/null 2>&1; then directory_mode="$(stat -c '%a' "$CONFIG_REVISIONS")"
    else directory_mode="$(stat -f '%Lp' "$CONFIG_REVISIONS" 2>/dev/null || true)"; fi
    [ "$directory_mode" = 700 ] || { fail "共享 runtime config 目录权限必须为 0700"; return 1; }
    if [ -e "$target" ] || [ -L "$target" ]; then
        [ -f "$target" ] && [ ! -L "$target" ] && [ "$(hash_file "$target")" = "$expected" ] || {
            fail "已存在的 config revision 内容不匹配"; return 1;
        }
        chmod 0600 "$target" || { fail "无法保护已有 config revision"; return 1; }
        return 0
    fi
    tmp="$CONFIG_REVISIONS/.config.$$.$RANDOM"
    cp "$source" "$tmp" && chmod 0600 "$tmp" || { rm -f "$tmp"; fail "运行配置快照写入失败"; return 1; }
    [ "$(hash_file "$tmp")" = "$expected" ] || { rm -f "$tmp"; fail "运行配置在快照期间发生变化"; return 1; }
    ln "$tmp" "$target" && rm -f "$tmp" || { rm -f "$tmp"; fail "不能原子登记共享 config revision"; return 1; }
    chmod 0600 "$target" || { fail "无法保护新 config revision"; return 1; }
}
restore_file() {
    local dst="$1" saved="$2" exists="$3" tmp
    if [ "$exists" = yes ]; then
        tmp="$(dirname "$dst")/.restore.$$.$RANDOM"
        cp -a "$saved" "$tmp" || return 1
        replace_file "$tmp" "$dst" || return 1
    else rm -f "$dst"; fi
}
gc() {
    local timestamp="$1" cutoff keep="" sorted="" files="" remove=""
    local cur="" prev="" r age f name stored_name expected actual grep_status
    cutoff=$((timestamp - RETENTION))
    # Prepare and verify every temporary list before deleting releases or assets.
    # If ENOSPC interrupts any write, collection fails closed and leaves the
    # current/rollback asset store untouched.
    keep="$(mktemp "$STATE/assets.keep.XXXXXX")" || { fail "GC 无法创建资源保留清单，跳过清理"; return 1; }
    sorted="$(mktemp "$STATE/assets.sorted.XXXXXX")" || {
        rm -f -- "$keep"; fail "GC 无法创建排序清单，跳过清理"; return 1;
    }
    files="$(mktemp "$STATE/assets.files.XXXXXX")" || {
        rm -f -- "$keep" "$sorted"; fail "GC 无法创建资源文件清单，跳过清理"; return 1;
    }
    remove="$(mktemp "$STATE/assets.remove.XXXXXX")" || {
        rm -f -- "$keep" "$sorted" "$files"; fail "GC 无法创建待删除清单，跳过清理"; return 1;
    }
    if [ -L "$CURRENT" ]; then cur="$(readlink "$CURRENT")" || {
        rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法读取 current 指针，跳过清理"; return 1;
    }; fi
    if [ -L "$ROLLBACK" ]; then prev="$(readlink "$ROLLBACK")" || {
        rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法读取 rollback 指针，跳过清理"; return 1;
    }; fi

    for r in "$RELEASES"/*; do
        [ -d "$r" ] || continue
        age="$(retired "$r")" || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法读取版本保留状态，跳过清理"; return 1;
        }
        if [ "$r" = "$cur" ] || [ "$r" = "$prev" ] || { [[ "$age" =~ ^[0-9]+$ ]] && [ "$age" -ge "$cutoff" ]; }; then
            [ -f "$r/assets.manifest" ] && [ -r "$r/assets.manifest" ] || {
                rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 保留版本缺少可读资源清单，跳过清理"; return 1;
            }
            awk 'NF != 2 { exit 2 } { print $2 }' "$r/assets.manifest" >> "$keep" || {
                rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 资源保留清单写入失败，跳过清理"; return 1;
            }
        fi
    done
    sort -u "$keep" > "$sorted" || {
        rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 资源保留清单排序失败，跳过清理"; return 1;
    }
    while IFS= read -r name; do
        [ -n "$name" ] || continue
        [[ "$name" == assets/* && "$name" != *"/../"* && "$name" != ../* && "$name" != */.. ]] &&
            hashed_asset "$name" || {
                rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 发现无效资源清单项，跳过清理"; return 1;
            }
        stored_name="${name#assets/}"; f="$ASSETS/$stored_name"
        [ -f "$f" ] && [ ! -L "$f" ] || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 保留资源缺失或无效，跳过清理"; return 1;
        }
    done < "$sorted"
    find "$ASSETS" -type f -print0 > "$files" || {
        rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法枚举资源文件，跳过清理"; return 1;
    }
    while IFS= read -r -d '' f; do
        stored_name="${f#"$ASSETS"/}"; name="assets/$stored_name"
        hashed_asset "$name" || continue
        if grep -Fxq -- "$name" "$sorted"; then continue; else grep_status=$?; fi
        [ "$grep_status" -eq 1 ] || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法查询资源保留清单，跳过清理"; return 1;
        }
        printf '%s\0' "$f" >> "$remove" || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 待删除清单写入失败，跳过清理"; return 1;
        }
    done < "$files"

    # All keep and remove lists are complete and readable before destructive work.
    for r in "$RELEASES"/*; do
        [ -d "$r" ] || continue; age="$(retired "$r")"
        if [ "$r" = "$cur" ] || [ "$r" = "$prev" ] || { [[ "$age" =~ ^[0-9]+$ ]] && [ "$age" -ge "$cutoff" ]; }; then
            continue
        fi
        rm -rf -- "$r" || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法移除过期版本"; return 1;
        }
        rm -f -- "$META/$(basename "$r").env" || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法移除过期版本元数据"; return 1;
        }
    done
    while IFS= read -r -d '' f; do
        [ -f "$f" ] || continue
        rm -f -- "$f" || {
            rm -f -- "$keep" "$sorted" "$files" "$remove"; fail "GC 无法移除过期 hash 资源"; return 1;
        }
    done < "$remove"
    find "$ASSETS" -mindepth 1 -type d -empty -delete 2>/dev/null || true
    rm -f -- "$keep" "$sorted" "$files" "$remove"
}
snapshot() {
    local tx="$1" old="$2"
    mkdir -p "$tx"
    if [ -f "$NGINX_CONF" ]; then cp -a "$NGINX_CONF" "$tx/nginx.old"; echo yes > "$tx/nginx-existed"; else : > "$tx/nginx.old"; echo no > "$tx/nginx-existed"; fi
    if [ -e "$UNIT" ] || [ -L "$UNIT" ]; then cp -a "$UNIT" "$tx/unit.old"; echo yes > "$tx/unit-existed"; else : > "$tx/unit.old"; echo no > "$tx/unit-existed"; fi
    printf '%s\n' "$old" > "$tx/old-release"; active && echo yes > "$tx/old-running" || echo no > "$tx/old-running"
    if [ -L "$ROLLBACK" ]; then
        readlink "$ROLLBACK" > "$tx/rollback.old"; echo yes > "$tx/rollback-existed"
    elif [ -e "$ROLLBACK" ]; then
        fail "rollback 不是符号链接，拒绝开始事务"; return 1
    else
        : > "$tx/rollback.old"; echo no > "$tx/rollback-existed"
    fi
    phase "$tx" prepared || return 1
    local active_tmp="$STATE/.active-transaction.$$"
    printf '%s\n' "$(basename "$tx")" > "$active_tmp" && replace_file "$active_tmp" "$ACTIVE_TX"
}
recover() {
    local id="$1" tx="$TXNS/$1" old running current_phase started elapsed timestamp
    [ "$IN_RECOVERY" = no ] || { fail "检测到重入恢复，保留 active transaction"; return 1; }
    IN_RECOVERY=yes; TRANSITION_DEADLINE=0; RECOVERY_DEADLINE=$((SECONDS + RECOVERY_SECONDS))
    [ -d "$tx" ] && [ -f "$tx/phase" ] && [ -f "$tx/old-release" ] && [ -f "$tx/old-running" ] &&
        [ -f "$tx/unit-existed" ] && [ -f "$tx/nginx-existed" ] && [ -f "$tx/rollback-existed" ] || {
            fail "恢复事务清单不完整"; return 1;
        }
    current_phase="$(cat "$tx/phase")"; old="$(cat "$tx/old-release")"; running="$(cat "$tx/old-running")"
    started="$SECONDS"; timestamp="$(now)"; printf '[deploy] 恢复事务 %s，阶段 %s\n' "$id" "$current_phase"
    if [ "$current_phase" = committed ] || [ "$current_phase" = recovered ]; then
        rm -f "$ACTIVE_TX" || { fail "无法清理已完成事务标记"; return 1; }
        gc "$timestamp" || { fail "已完成事务的版本清理失败"; return 1; }
        IN_RECOVERY=no; RECOVERY_DEADLINE=0
        return 0
    fi
    if [ "$current_phase" = prepared ]; then
        restore_file "$UNIT" "$tx/unit.old" "$(cat "$tx/unit-existed")" || { fail "恢复旧 unit 文件失败"; return 1; }
        with_budget 5 systemctl daemon-reload >/dev/null 2>&1 || { fail "恢复旧 unit 后 daemon-reload 失败"; return 1; }
        if [ "$(cat "$tx/rollback-existed")" = yes ]; then pointer "$ROLLBACK" "$(cat "$tx/rollback.old")" || { fail "恢复旧 rollback 指针失败"; return 1; }
        else pointer "$ROLLBACK" "" || { fail "清理 rollback 指针失败"; return 1; }; fi
        rm -f "$ACTIVE_TX" || { fail "无法清理已恢复事务标记"; return 1; }
        IN_RECOVERY=no; RECOVERY_DEADLINE=0
        return 0
    fi
    with_budget "$STOP_SECONDS" systemctl stop "$SERVICE" >/dev/null 2>&1 || { fail "候选服务未在停止时限内退出，保留事务供重试恢复"; return 1; }
    pointer "$CURRENT" "$old" || { fail "恢复 current 指针失败"; return 1; }
    restore_file "$NGINX_CONF" "$tx/nginx.old" "$(cat "$tx/nginx-existed")" || { fail "恢复旧 Nginx 配置文件失败"; return 1; }
    restore_file "$UNIT" "$tx/unit.old" "$(cat "$tx/unit-existed")" || { fail "恢复旧 unit 文件失败"; return 1; }
    with_budget 5 systemctl daemon-reload >/dev/null 2>&1 || { fail "恢复旧 unit 后 daemon-reload 失败"; return 1; }
    if [ "$(cat "$tx/rollback-existed")" = yes ]; then pointer "$ROLLBACK" "$(cat "$tx/rollback.old")" || { fail "恢复旧 rollback 指针失败"; return 1; }
    else pointer "$ROLLBACK" "" || { fail "清理 rollback 指针失败"; return 1; }; fi
    if [ "$(cat "$tx/nginx-existed")" = yes ]; then
        with_budget 5 nginx -t -c "$NGINX_CONF" >/dev/null 2>&1 || { fail "旧 Nginx 配置验证失败"; return 1; }
        with_budget 5 systemctl reload "$NGINX_SERVICE" >/dev/null 2>&1 || { fail "旧 Nginx reload 失败"; return 1; }
    fi
    if [ "$running" = yes ]; then
        with_budget "$START_SECONDS" systemctl start "$SERVICE" >/dev/null 2>&1 || { fail "旧服务启动失败"; return 1; }
        wait_health "$HEALTH_SECONDS" || { fail "旧服务健康检查失败"; return 1; }
        if [ -n "$old" ] && [ -f "$old/frontend/dist/index.html" ]; then smoke "$old" "$tx" || { fail "旧入口冒烟失败"; return 1; }; fi
    fi
    elapsed=$((SECONDS - started)); [ "$elapsed" -le "$RECOVERY_SECONDS" ] || { fail "恢复超出 60 秒预算"; return 1; }
    phase "$tx" recovered || { fail "恢复阶段清单写入失败"; return 1; }
    rm -f "$ACTIVE_TX" || { fail "无法清理已恢复事务标记"; return 1; }
    gc "$timestamp" || { fail "恢复后的版本清理失败"; return 1; }
    IN_RECOVERY=no; RECOVERY_DEADLINE=0
    printf '[deploy] 旧版恢复完成，用时 %ss\n' "$elapsed"
}
recover_pending() { [ -f "$ACTIVE_TX" ] || return 0; recover "$(cat "$ACTIVE_TX")"; }
handle_error() {
    local status="$1"
    trap - ERR INT TERM
    if [ "$LOCK_HELD" = yes ] && [ "$IN_RECOVERY" = no ] && [ -f "$ACTIVE_TX" ]; then
        set +e
        recover_pending || printf '[deploy] ERROR: 自动恢复失败，保留事务供下一次入口重试。\n' >&2
    fi
    exit "$status"
}
handle_signal() {
    local status="$1"
    trap - ERR INT TERM
    if [ "$LOCK_HELD" = yes ] && [ "$IN_RECOVERY" = no ] && [ -f "$ACTIVE_TX" ]; then
        set +e
        recover_pending || printf '[deploy] ERROR: 信号后恢复失败，保留事务供下一次入口重试。\n' >&2
    fi
    exit "$status"
}
trap 'handle_error "$?"' ERR
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM
build() {
    local sha="$1" stage="$2" src="$stage/src" bundle="$stage/bundle" exe archive="$stage/source.tar"
    mkdir -p "$src" "$bundle"
    git -C "$PROJECT_DIR" archive --format=tar "$sha" > "$archive" || { fail "候选源码 Git archive 失败: $sha"; return 1; }
    tar -xf "$archive" -C "$src" || { fail "候选源码 tar 解包失败: $archive"; return 1; }
    [ -f "$src/frontend/package.json" ] && [ -f "$src/frontend/package-lock.json" ] || { fail "前端 package 文件/锁文件缺失"; return 1; }
    [ -f "$src/backend_cpp/CMakeLists.txt" ] && [ -f "$src/configs/woniunote_nginx_prod.conf" ] &&
        [ -f "$src/scripts/release_run_backend.sh" ] || { fail "后端、Nginx 模板或 release launcher 缺失"; return 1; }
    [ "$WONIUNOTE_FAIL_AT" != npm-install ] || { fail "故障注入 npm-install"; return 1; }
    (cd "$src/frontend" && node scripts/check-node-version.mjs && npm ci) || { fail "Node 版本检查或 npm ci 失败"; return 1; }
    [ "$WONIUNOTE_FAIL_AT" != frontend-build ] || { fail "故障注入 frontend-build"; return 1; }
    (cd "$src/frontend" && npm run build) || { fail "前端构建失败"; return 1; }
    [ -f "$src/frontend/dist/index.html" ] && [ -d "$src/frontend/dist/assets" ] || { fail "前端产物不完整"; return 1; }
    if [ "$WONIUNOTE_FAIL_AT" = missing-artifact ]; then rm -f "$src/frontend/dist/index.html"; fail "故障注入 missing-artifact"; return 1; fi
    [ "$WONIUNOTE_FAIL_AT" != backend-build ] || { fail "故障注入 backend-build"; return 1; }
    cmake -S "$src/backend_cpp" -B "$src/backend_cpp/build" -DCMAKE_BUILD_TYPE=Release -DUSE_SYSTEM_LIBS=ON || { fail "后端 CMake 配置失败"; return 1; }
    cmake --build "$src/backend_cpp/build" --config Release -j"$BUILD_JOBS" || { fail "后端编译失败"; return 1; }
    exe="$src/backend_cpp/build/woniunote_backend"; [ -x "$exe" ] || { fail "后端二进制缺失"; return 1; }
    mkdir -p "$bundle/backend_cpp/build" "$bundle/frontend"
    cp "$exe" "$bundle/backend_cpp/build/woniunote_backend" && chmod 0755 "$bundle/backend_cpp/build/woniunote_backend" || { fail "后端产物打包失败"; return 1; }
    mkdir -p "$bundle/backend_cpp/resource" || { fail "候选资源目录创建失败"; return 1; }
    if [ -d "$src/backend_cpp/resource" ]; then
        cp -a "$src/backend_cpp/resource/." "$bundle/backend_cpp/resource/" || { fail "候选后端资源打包失败"; return 1; }
    fi
    cp -a "$src/frontend/dist" "$bundle/frontend/dist" || { fail "候选前端静态文件打包失败"; return 1; }
    [ "$WONIUNOTE_FAIL_AT" != disk-full ] || { fail "故障注入 disk-full：候选构建阶段空间不足"; return 1; }
    printf '%s\n' "$sha" > "$bundle/source.sha"
    store_config_revision "$3" || return 1
    printf '%s\n' "$CONFIG_REVISIONS/$3.json" > "$bundle/runtime-config.ref"
    printf '%s\n' "$3" > "$bundle/runtime-config.sha256"
    printf '%s\n' "$DATA" > "$bundle/data-dir.ref"
    cp "$src/scripts/release_run_backend.sh" "$bundle/backend_cpp/release_run_backend.sh" || { fail "release backend launcher 缺失"; return 1; }
    link_persistent "$bundle/backend_cpp" && register_assets "$bundle/frontend/dist" "$bundle" || { fail "持久目录或 hash 资源准备失败"; return 1; }
    validate_frontend_assets "$bundle/frontend/dist" "$bundle/assets.manifest" "$stage/entry-assets.refs" || {
        fail "候选前端入口资源未完整登记到冻结 hash manifest"; return 1;
    }
    render_nginx "$src/configs/woniunote_nginx_prod.conf" "$bundle/nginx.conf" || return 1
    printf 'sha=%s\nbackend=%s\nindex=%s\nnginx=%s\nruntime_config=%s\n' "$sha" "$(hash_file "$bundle/backend_cpp/build/woniunote_backend")" "$(hash_file "$bundle/frontend/dist/index.html")" "$(hash_file "$bundle/nginx.conf")" "$3" > "$bundle/release.manifest"
    [ "$WONIUNOTE_FAIL_AT" != nginx-test ] || { fail "故障注入 nginx-test"; return 1; }
    timeout 5s nginx -t -c "$bundle/nginx.conf" || { fail "候选 Nginx 配置检查失败"; return 1; }
}
current_release() {
    if [ -L "$CURRENT" ]; then readlink "$CURRENT"
    elif [ -e "$CURRENT" ]; then fail "current 不是符号链接"; return 1
    else printf '\n'; fi
}
deploy() {
    local ref="$1" sha timestamp retired_at id stage bundle release old from record tx unit nginx_tmp legacy config_hash legacy_config legacy_hash
    root_only; mkdir -p "$STATE" "$RELEASES" "$META" "$ASSETS" "$TXNS" "$STATE/staging"
    lock_target; recover_pending; sha="$(git -C "$PROJECT_DIR" rev-parse --verify "$ref^{commit}")" || { fail "候选 SHA 无法解析"; return 1; }
    [ -f "$CONFIG" ] || { fail "运行配置不存在"; return 1; }
    if grep -Eq 'YOUR_SECURE_|CHANGE_ME_' "$CONFIG"; then fail "运行配置含占位凭据"; return 1; fi
    config_hash="$(hash_file "$CONFIG")" || { fail "运行配置摘要计算失败"; return 1; }
    old="$(current_release)"
    if [ -n "$old" ]; then
        [ -d "$old" ] || { fail "current release 不存在"; return 1; }
        verify_release_config "$old" || return 1
        [ "$(cat "$old/data-dir.ref")" = "$DATA" ] || { fail "持久数据目录改变"; return 1; }
        from="$(cat "$old/source.sha")"; verify_compat "$from" "$sha" "$WONIUNOTE_COMPATIBILITY_RECORD"
    elif active; then
        [ -x "$PROJECT_DIR/backend_cpp/build/woniunote_backend" ] && [ -f "$PROJECT_DIR/frontend/dist/index.html" ] && [ -f "$NGINX_CONF" ] || { fail "旧服务没有完整回退基线"; return 1; }
        from="$(value "$WONIUNOTE_COMPATIBILITY_RECORD" FROM_SHA)"; [ -n "$from" ] || { fail "首次升级记录须绑定旧完整 SHA"; return 1; }
        verify_compat "$from" "$sha" "$WONIUNOTE_COMPATIBILITY_RECORD"
        if [ -f "$PROJECT_DIR/backend_cpp/build/config.local.json" ]; then
            legacy_config="$PROJECT_DIR/backend_cpp/build/config.local.json"
        elif [ -f "$PROJECT_DIR/backend_cpp/build/config.json" ]; then
            legacy_config="$PROJECT_DIR/backend_cpp/build/config.json"
        else
            fail "无法证明旧进程的运行配置，拒绝创建不完整回滚基线"; return 1
        fi
        legacy_hash="$(hash_file "$legacy_config")"
    else
        verify_initial_install "$sha" || return 1
    fi
    if command -v lsof >/dev/null 2>&1 && lsof -ti:5173 >/dev/null 2>&1 && ! active; then fail "发现未由 systemd 管理的后端进程"; return 1; fi
    validate_smoke_upload || return 1
    timestamp="$(now)"; id="$(printf '%s' "$sha" | cut -c1-12)-$timestamp-$$"; stage="$STATE/staging/$id"
    bundle="$stage/bundle"; release="$RELEASES/$id"; [ ! -e "$release" ] || { fail "release 不可覆盖"; return 1; }
    mkdir -p "$stage" || { fail "无法创建候选构建目录"; return 1; }
    build "$sha" "$stage" "$config_hash" || { rm -rf "$stage"; gc "$timestamp" || true; return 1; }
    [ "$(hash_file "$CONFIG")" = "$config_hash" ] && [ "$(cat "$bundle/runtime-config.sha256")" = "$config_hash" ] || {
        fail "运行配置在构建期间发生变化，候选不会切换"; rm -rf "$stage"; gc "$timestamp" || true; return 1;
    }
    mv "$bundle" "$release"; rm -rf "$stage"; state_write "$release" 0
    verify_release_config "$release" || return 1
    if [ -z "$old" ] && active; then
        legacy="$RELEASES/legacy-$(printf '%s' "$from" | cut -c1-12)-$timestamp"; old="$legacy"
        mkdir -p "$legacy/backend_cpp/build" "$legacy/frontend" || { fail "无法创建旧版回退快照"; return 1; }
        cp "$PROJECT_DIR/backend_cpp/build/woniunote_backend" "$legacy/backend_cpp/build/woniunote_backend" &&
            chmod 0755 "$legacy/backend_cpp/build/woniunote_backend" &&
        cp -a "$PROJECT_DIR/frontend/dist" "$legacy/frontend/dist" &&
            snapshot_legacy_nginx "$NGINX_CONF" "$legacy/nginx.conf" "$legacy" ||
            { fail "无法复制/冻结完整旧版回退快照"; rm -rf "$legacy"; return 1; }
        printf '%s\n' "$from" > "$legacy/source.sha" &&
            store_config_revision "$legacy_hash" "$legacy_config" &&
            printf '%s\n' "$CONFIG_REVISIONS/$legacy_hash.json" > "$legacy/runtime-config.ref" &&
            printf '%s\n' "$legacy_hash" > "$legacy/runtime-config.sha256" &&
            printf '%s\n' "$DATA" > "$legacy/data-dir.ref" &&
            cp "$SCRIPT_DIR/release_run_backend.sh" "$legacy/backend_cpp/release_run_backend.sh" &&
            link_persistent "$legacy/backend_cpp" &&
            register_assets "$legacy/frontend/dist" "$legacy" &&
            validate_frontend_assets "$legacy/frontend/dist" "$legacy/assets.manifest" "$legacy/.entry-assets.refs" &&
            rm -f "$legacy/.entry-assets.refs" &&
            state_write "$legacy" 0 || { fail "旧版回退快照未完整登记"; rm -rf "$legacy"; return 1; }
    fi
    unit="$STATE/unit-candidate.$$.service"; write_unit "$unit"
    if command -v systemd-analyze >/dev/null 2>&1; then timeout 5s systemd-analyze verify "$unit" || { rm -f "$unit"; fail "候选 systemd unit 校验失败"; return 1; }; fi
    with_budget 5 systemctl start "$NGINX_SERVICE" || { fail "Nginx 管理进程未能在时限内启动"; return 1; }
    tx="$TXNS/$id"; snapshot "$tx" "$old"; TRANSITION_DEADLINE=$((SECONDS + FAILURE_TRIGGER_SECONDS))
    cp "$unit" "$UNIT.tmp.$$" && chmod 0644 "$UNIT.tmp.$$" && replace_file "$UNIT.tmp.$$" "$UNIT" || { fail "安装候选 unit 文件失败"; return 1; }
    with_budget 5 systemctl daemon-reload || { fail "systemd daemon-reload 失败"; return 1; }; phase "$tx" unit-installed
    with_budget "$STOP_SECONDS" systemctl stop "$SERVICE" || { fail "旧服务未在停止时限内退出"; return 1; }
    phase "$tx" old-stopped
    if [ "$WONIUNOTE_FAIL_AT" = after-stop ]; then fail "故障注入 after-stop"; return 1; fi
    pointer "$CURRENT" "$release"; phase "$tx" pointer-switched
    nginx_tmp="$(dirname "$NGINX_CONF")/.woniunote-nginx.$$.$RANDOM"
    cp "$release/nginx.conf" "$nginx_tmp" && chmod 0644 "$nginx_tmp" && replace_file "$nginx_tmp" "$NGINX_CONF" || { fail "安装候选 Nginx 配置失败"; return 1; }
    if [ "$WONIUNOTE_FAIL_AT" = nginx-reload ]; then fail "故障注入 nginx-reload"; return 1; fi
    with_budget 5 nginx -t -c "$NGINX_CONF" || { fail "候选 Nginx 配置检查失败"; return 1; }
    with_budget 5 systemctl reload "$NGINX_SERVICE" || { fail "Nginx reload 失败"; return 1; }
    phase "$tx" nginx-installed
    with_budget "$START_SECONDS" systemctl start "$SERVICE" || { fail "候选服务启动失败"; return 1; }
    if [ "$WONIUNOTE_FAIL_AT" = smoke ]; then fail "故障注入 smoke"; return 1; fi
    wait_health "$HEALTH_SECONDS" || { fail "候选健康检查失败"; return 1; }
    phase "$tx" candidate-started; smoke "$release" "$tx" || { fail "Nginx/index/API/thumbnail/upload 冒烟失败"; return 1; }
    [ "$(hash_file "$CONFIG")" = "$config_hash" ] && verify_release_config "$release" || { fail "运行配置或其不可变快照在切换期间发生变化"; return 1; }
    check_transition_deadline || return 1
    phase "$tx" verified
    retired_at="$(now)"
    if [ -n "$old" ]; then state_write "$old" "$retired_at"; pointer "$ROLLBACK" "$old"; else rm -f "$ROLLBACK"; fi
    state_write "$release" 0; phase "$tx" committed; rm -f "$ACTIVE_TX"; gc "$(now)"
    TRANSITION_DEADLINE=0
    printf '[deploy] PASS release=%s sha=%s\n' "$id" "$sha"
    [ -n "$old" ] || printf '[deploy] GAP: 首次安装没有既有版本可回滚。\n'
}
rollback_release() {
    local target old timestamp retired_at id tx unit nginx_tmp from to
    root_only; lock_target; recover_pending
    [ -L "$ROLLBACK" ] || { fail "没有可用 rollback release"; return 1; }
    target="$(readlink "$ROLLBACK")"; [ -d "$target" ] || { fail "rollback release 丢失"; return 1; }
    old="$(current_release)"; [ -n "$old" ] && [ -d "$old" ] || { fail "current release 不存在"; return 1; }
    verify_release_config "$target" && verify_release_config "$old" || return 1
    [ "$(cat "$target/data-dir.ref")" = "$DATA" ] && [ "$(cat "$old/data-dir.ref")" = "$DATA" ] || { fail "rollback 数据目录引用不一致"; return 1; }
    from="$(cat "$old/source.sha")"; to="$(cat "$target/source.sha")"; verify_compat "$from" "$to" "$WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD"
    validate_smoke_upload || return 1
    timestamp="$(now)"; id="rollback-$(basename "$target")-$timestamp-$$"; tx="$TXNS/$id"
    unit="$STATE/unit-candidate.$$.service"; write_unit "$unit"
    if command -v systemd-analyze >/dev/null 2>&1; then timeout 5s systemd-analyze verify "$unit" || { rm -f "$unit"; fail "rollback systemd unit 校验失败"; return 1; }; fi
    snapshot "$tx" "$old"; TRANSITION_DEADLINE=$((SECONDS + FAILURE_TRIGGER_SECONDS))
    cp "$unit" "$UNIT.tmp.$$" && chmod 0644 "$UNIT.tmp.$$" && replace_file "$UNIT.tmp.$$" "$UNIT" || { fail "安装 rollback unit 失败"; return 1; }
    with_budget 5 systemctl daemon-reload || { fail "rollback daemon-reload 失败"; return 1; }
    phase "$tx" unit-installed
    with_budget "$STOP_SECONDS" systemctl stop "$SERVICE" || { fail "当前服务停止失败"; return 1; }
    phase "$tx" old-stopped; pointer "$CURRENT" "$target"; phase "$tx" pointer-switched
    nginx_tmp="$(dirname "$NGINX_CONF")/.woniunote-nginx.$$.$RANDOM"; cp "$target/nginx.conf" "$nginx_tmp" && chmod 0644 "$nginx_tmp" && replace_file "$nginx_tmp" "$NGINX_CONF" || { fail "安装 rollback Nginx 配置失败"; return 1; }
    with_budget 5 nginx -t -c "$NGINX_CONF" && with_budget 5 systemctl reload "$NGINX_SERVICE" || { fail "rollback Nginx 失败"; return 1; }
    phase "$tx" nginx-installed
    with_budget "$START_SECONDS" systemctl start "$SERVICE" || { fail "rollback 服务启动失败"; return 1; }
    wait_health "$HEALTH_SECONDS" && smoke "$target" "$tx" || { fail "rollback 服务/入口冒烟失败"; return 1; }
    retired_at="$(now)"; state_write "$old" "$retired_at"; state_write "$target" 0; pointer "$ROLLBACK" "$old"
    phase "$tx" committed; rm -f "$ACTIVE_TX"; gc "$(now)"; TRANSITION_DEADLINE=0
    printf '[deploy] PASS rollback current=%s\n' "$(basename "$target")"
}
case "$1" in
    assert-locked)
        lock_owner_is_ancestor || { fail "没有可验证的部署锁祖先进程"; exit 1; }
        ;;
    setup)
        root_only; lock_target
        if [ -z "$(current_release)" ] && ! active; then
            setup_target="$(git -C "$PROJECT_DIR" rev-parse --verify 'HEAD^{commit}')" || {
                fail "setup 的首次候选 SHA 无法解析"; exit 1;
            }
            verify_initial_install "$setup_target" || exit 1
        fi
        setup_script="$WONIUNOTE_SETUP_SCRIPT"
        [ -n "$setup_script" ] || setup_script="$APP_DIR/scripts/setup_ubuntu.sh"
        [ -f "$setup_script" ] || { fail "setup 脚本不存在"; exit 1; }
        setup_script="$(cd "$(dirname "$setup_script")" && pwd)/$(basename "$setup_script")"
        case "$setup_script" in
            "$APP_DIR"/scripts/setup_ubuntu.sh|"$PROJECT_DIR"/scripts/setup_ubuntu.sh) ;;
            *) fail "拒绝执行部署目录之外的 setup 脚本"; exit 1 ;;
        esac
        WONIUNOTE_SETUP_LOCKED=yes bash "$setup_script"
        ;;
    deploy)
        shift; ref=HEAD
        while [ "$#" -gt 0 ]; do case "$1" in --sha) ref="$2"; shift 2 ;; *) fail "未知参数 $1"; exit 2 ;; esac; done
        deploy "$ref"
        ;;
    start)
        root_only; lock_target; recover_pending; current="$(current_release)"
        if [ -z "$current" ]; then unlock; deploy HEAD
        else
            verify_release_config "$current" || exit 1
            [ "$(cat "$current/data-dir.ref")" = "$DATA" ] || { fail "当前 release 持久数据目录引用不一致"; exit 1; }
            validate_smoke_upload || exit 1
            with_budget "$START_SECONDS" systemctl start "$SERVICE" || exit 1
            wait_health "$HEALTH_SECONDS" || exit 1
            mkdir -p "$STATE/start-smoke"; smoke "$current" "$STATE/start-smoke"
        fi
        ;;
    stop) root_only; lock_target; recover_pending; if active; then with_budget "$STOP_SECONDS" systemctl stop "$SERVICE"; else exit 0; fi ;;
    rollback) rollback_release ;;
    status)
        printf 'current=%s\n' "$(current_release)"
        if [ -L "$ROLLBACK" ]; then printf 'rollback=%s\n' "$(readlink "$ROLLBACK")"; else printf 'rollback=none\n'; fi
        if [ -f "$ACTIVE_TX" ]; then printf 'transaction=%s\n' "$(cat "$ACTIVE_TX")"; else printf 'transaction=none\n'; fi
        ;;
    gc) root_only; lock_target; recover_pending; gc "$(now)" ;;
    run-locked)
        lock_target; shift; [ "$#" -gt 0 ] || { fail "缺少命令"; exit 2; }
        if "$@"; then exit 0; else exit $?; fi
        ;;
    *) echo "用法: $0 {deploy [--sha SHA]|start|stop|rollback|status|gc|run-locked COMMAND...}" >&2; exit 2 ;;
esac
