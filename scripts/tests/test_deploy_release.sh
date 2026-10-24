#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REAL_AWK="$(command -v awk)"
REAL_NODE="$(command -v node)"
export REAL_AWK REAL_NODE
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/woniunote-deploy-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

die() { printf '[deploy-test] FAIL: %s\n' "$*" >&2; exit 1; }
ok() { printf '[deploy-test] PASS: %s\n' "$*"; }
hash_file() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi; }

FIXTURE="$TMP_ROOT/project"
STATE="$TMP_ROOT/state"
DATA="$TMP_ROOT/data"
BIN="$TMP_ROOT/bin"
ETC="$TMP_ROOT/etc"
mkdir -p "$FIXTURE/scripts" "$FIXTURE/configs" "$FIXTURE/frontend/scripts" \
    "$FIXTURE/backend_cpp/resource/thumb" "$STATE" "$DATA/uploads" "$DATA/build/uploads" \
    "$DATA/build/logs" "$DATA/resource/thumb" "$BIN" "$ETC"
cp "$REPO_ROOT/scripts/deploy_release.sh" "$FIXTURE/scripts/deploy_release.sh"
cp "$REPO_ROOT/scripts/release_run_backend.sh" "$FIXTURE/scripts/release_run_backend.sh"
cp "$REPO_ROOT/restart_app.sh" "$FIXTURE/restart_app.sh"
cp "$REPO_ROOT/configs/woniunote_nginx_prod.conf" "$FIXTURE/configs/woniunote_nginx_prod.conf"
cat > "$FIXTURE/frontend/package.json" <<'EOF'
{"name":"fixture","version":"1.0.0"}
EOF
cat > "$FIXTURE/frontend/package-lock.json" <<'EOF'
{"name":"fixture","lockfileVersion":3,"packages":{}}
EOF
cat > "$FIXTURE/frontend/scripts/check-node-version.mjs" <<'EOF'
process.exit(0)
EOF
cat > "$FIXTURE/backend_cpp/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.20)
project(fixture)
EOF
printf 'v1\n' > "$FIXTURE/VERSION"
printf 'v1\n' > "$FIXTURE/frontend/VERSION"
printf 'v1\n' > "$FIXTURE/backend_cpp/VERSION"
printf 'thumb-v1\n' > "$FIXTURE/backend_cpp/resource/thumb/persisted.png"
cp "$FIXTURE/backend_cpp/resource/thumb/persisted.png" "$DATA/resource/thumb/persisted.png"
printf 'old-log\n' > "$DATA/build/logs/backend.log"
printf 'old-upload\n' > "$DATA/build/uploads/keep.txt"
printf 'persisted-upload-bytes\n' > "$DATA/uploads/persisted.txt"
printf 'data-secret-marker\n' > "$DATA/secret.marker"
printf '{"custom_config":{"jwt_secret":"secret-one"}}\n' > "$TMP_ROOT/runtime.json"

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.name DeployTest
git -C "$FIXTURE" config user.email deploy-test@example.invalid
git -C "$FIXTURE" add .
git -C "$FIXTURE" commit -qm 'fixture v1'
SHA1="$(git -C "$FIXTURE" rev-parse HEAD)"

cat > "$BIN/node" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = - ]; then exec "$REAL_NODE" "$@"; fi
exit 0
EOF
cat > "$BIN/awk" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${MOCK_GC_KEEP_WRITE_FAIL:-}" = 1 ] && [ "${1:-}" = 'NF != 2 { exit 2 } { print $2 }' ]; then
    echo 'mock ENOSPC writing GC keep manifest' >&2
    exit 28
fi
exec "$REAL_AWK" "$@"
EOF
cat > "$BIN/npm" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = ci ]; then exit 0; fi
if [ "$1" = run ] && [ "$2" = build ]; then
    printf '%s\n' "$(cat VERSION)" >> "$MOCK_BUILD_LOG"
    if [ "${MOCK_NPM_FAIL_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/npm" ]; then
        touch "$MOCK_FAIL_DIR/npm"
        echo "mock npm build error" >&2
        exit 1
    fi
    version="$(cat VERSION)"
    asset_hash="$(printf '%s' "$version" | sha256sum | cut -c1-12)"
    mkdir -p dist/assets
    printf '<!doctype html><link rel="stylesheet" href="/assets/style-%s.css"><script type="module" src="/assets/app-%s.js"></script>\n' \
        "$asset_hash" "$asset_hash" > dist/index.html
    printf '%s\n' "$version" > "dist/assets/app-$asset_hash.js"
    if [ "${MOCK_MISSING_CSS:-}" != 1 ]; then printf 'body{--fixture-version:"%s"}\n' "$version" > "dist/assets/style-$asset_hash.css"; fi
    exit 0
fi
echo "unexpected npm args: $*" >&2
exit 2
EOF
cat > "$BIN/cmake" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = -S ]; then
    build=""
    while [ "$#" -gt 0 ]; do
        if [ "$1" = -B ]; then build="$2"; shift 2; else shift; fi
    done
    mkdir -p "$build"
    exit 0
fi
if [ "$1" = --build ]; then
    build="$2"
    if [ "${MOCK_CMAKE_FAIL_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/cmake" ]; then
        touch "$MOCK_FAIL_DIR/cmake"; exit 1
    fi
    version="$(cat "$(dirname "$build")/VERSION")"
    mkdir -p "$build"
    cat > "$build/woniunote_backend" <<'BACKEND'
#!/usr/bin/env bash
printf '%s\n' "$1"
BACKEND
    chmod 0755 "$build/woniunote_backend"
    exit 0
fi
echo "unexpected cmake args: $*" >&2
exit 2
EOF
cat > "$BIN/systemd-analyze" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = verify ]; then
    [ "$#" -ge 2 ] && case "$2" in *.service) ;; *) echo "verify input must end in .service" >&2; exit 64 ;; esac
    printf '%s\n' "$*" >> "$MOCK_SYSTEMD_ANALYZE_LOG"
fi
exit 0
EOF
cat > "$BIN/lsof" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat > "$BIN/flock" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
error_status=1
while [ "$#" -gt 0 ]; do
    case "$1" in
        -n) shift ;;
        -E) error_status="$2"; shift 2 ;;
        -o) shift ;;
        --) shift; break ;;
        -*) echo "unsupported fake flock option: $1" >&2; exit 2 ;;
        *) break ;;
    esac
done
lock_path="$1"; shift
lock_dir="$lock_path.mock-lock"
if ! mkdir "$lock_dir" 2>/dev/null; then exit "$error_status"; fi
cleanup() { rmdir "$lock_dir" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
WONIUNOTE_TEST_LOCK_PROOF="$lock_dir" "$@"
EOF
cat > "$BIN/realpath" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = -m ]; then
    input="$2"
    parent="$(dirname "$input")"
    name="$(basename "$input")"
    printf '%s/%s\n' "$(cd "$parent" && pwd -P)" "$name"
else
    exec /bin/realpath "$@"
fi
EOF
cat > "$BIN/nginx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
config=""
while [ "$#" -gt 0 ]; do
    if [ "$1" = -c ]; then config="$2"; shift 2; else shift; fi
done
if [ -n "$config" ] && grep -q 'server_name invalid-nginx' "$config"; then
    echo 'mock nginx config rejection' >&2
    exit 1
fi
if [ "${MOCK_NGINX_FAIL_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/nginx-test" ]; then
    touch "$MOCK_FAIL_DIR/nginx-test"
    exit 1
fi
[ -n "$config" ] && ! grep -Eq '@@WONIUNOTE_[A-Z_]+@@' "$config"
EOF
cat > "$BIN/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
command_name="$1"
shift
printf '%s %s\n' "$command_name" "$*" >> "$MOCK_SYSTEMCTL_LOG"
service_name="${1:-}"
case "$command_name" in
    is-active)
        [ "$(cat "$MOCK_SERVICE_STATE")" = active ]
        ;;
    daemon-reload)
        if [ "${MOCK_SLOW_DAEMON_RELOAD_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/daemon-reload" ]; then
            touch "$MOCK_FAIL_DIR/daemon-reload"; sleep 8
        fi
        ;;
    stop)
        [ "$service_name" = woniunote ] || exit 0
        if [ "${MOCK_SLOW_STOP_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/stop" ]; then
            touch "$MOCK_FAIL_DIR/stop"; sleep 12
        fi
        printf 'inactive\n' > "$MOCK_SERVICE_STATE"
        ;;
    start)
        [ "$service_name" = woniunote ] || exit 0
        if [ "${MOCK_FAIL_START_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/start" ]; then
            touch "$MOCK_FAIL_DIR/start"; exit 1
        fi
        printf 'active\n' > "$MOCK_SERVICE_STATE"
        ;;
    reload)
        if [ "${MOCK_FAIL_RELOAD_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/reload" ]; then
            touch "$MOCK_FAIL_DIR/reload"; exit 1
        fi
        if [ "${MOCK_SIGNAL_ON_RELOAD:-}" = TERM ] && [ ! -e "$MOCK_FAIL_DIR/signal" ]; then
            touch "$MOCK_FAIL_DIR/signal"
            kill -TERM "$(cat "$MOCK_DEPLOY_PID_FILE")"
            sleep 0.2
        fi
        if [ "${MOCK_SIGNAL_ON_RELOAD:-}" = KILL ] && [ ! -e "$MOCK_FAIL_DIR/kill" ]; then
            touch "$MOCK_FAIL_DIR/kill"
            kill -KILL "$(cat "$MOCK_DEPLOY_PID_FILE")"
            sleep 0.2
        fi
        ;;
    *) echo "unexpected systemctl command: $command_name $*" >&2; exit 2 ;;
esac
EOF
cat > "$BIN/mv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
destination="${!#}"
if [ "${MOCK_FAIL_CURRENT_POINTER_MV:-}" = 1 ] && [ "$destination" = "$MOCK_CURRENT" ]; then
    failures=0
    [ ! -f "$MOCK_CURRENT_MV_FAILURES" ] || failures="$(cat "$MOCK_CURRENT_MV_FAILURES")"
    if [ "$failures" -lt 2 ]; then
        printf '%s\n' "$((failures + 1))" > "$MOCK_CURRENT_MV_FAILURES"
        echo 'mock current pointer rename failure' >&2
        exit 1
    fi
fi
exec /bin/mv "$@"
EOF
cat > "$BIN/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
url=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o) out="$2"; shift 2 ;;
        --resolve|--max-time) shift 2 ;;
        -*) shift ;;
        *) url="$1"; shift ;;
    esac
done
printf '%s\n' "$url" >> "$MOCK_CURL_LOG"
case "$url" in
    *127.0.0.1:5173/health) exit 0 ;;
    *:18080/|*:18080/index.html)
        current="$(readlink "$MOCK_CURRENT")"
        cat "$current/frontend/dist/index.html" > "$out"
        ;;
    *:18080/assets/*)
        current="$(readlink "$MOCK_CURRENT")"
        asset_path="${url#*18080/}"
        asset_path="${asset_path%%\?*}"
        if [[ "$asset_path" = *.css && "${MOCK_WRONG_CSS_BODY_ONCE:-}" = 1 && ! -e "$MOCK_FAIL_DIR/wrong-css-body" ]]; then
            touch "$MOCK_FAIL_DIR/wrong-css-body"
            printf '<!doctype html><html><body>SPA fallback</body></html>\n' > "$out"
            exit 0
        fi
        [ -f "$current/frontend/dist/$asset_path" ] || { echo "missing fixture asset: $asset_path" >&2; exit 22; }
        cp "$current/frontend/dist/$asset_path" "$out"
        ;;
    */api/articles/types)
        printf '{"code":200,"data":[]}\n' > "$out"
        ;;
    */api/thumb/*)
        if [ -n "${MOCK_THUMB_FILE:-}" ]; then cp "$MOCK_THUMB_FILE" "$out"; else printf 'thumb-v1\n' > "$out"; fi
        ;;
    */api/uploads/*|*/uploads/*)
        if [ "${MOCK_FAIL_UPLOAD_ONCE:-}" = 1 ] && [ ! -e "$MOCK_FAIL_DIR/upload" ]; then
            touch "$MOCK_FAIL_DIR/upload"; exit 22
        fi
        cp "$MOCK_UPLOAD_FILE" "$out"
        ;;
    *) echo "unexpected smoke URL (custom port missing?): $url" >&2; exit 22 ;;
esac
EOF
chmod 0755 "$BIN"/*
printf 'inactive\n' > "$TMP_ROOT/service.state"
touch "$TMP_ROOT/systemctl.log" "$TMP_ROOT/curl.log" "$TMP_ROOT/systemd-analyze.log" "$TMP_ROOT/frontend-builds.log"

export PATH="$BIN:$PATH"
export WONIUNOTE_DEPLOY_TESTING=1
export WONIUNOTE_PROJECT_DIR="$FIXTURE"
export WONIUNOTE_STATE_DIR="$STATE"
export WONIUNOTE_DATA_DIR="$DATA"
export WONIUNOTE_RUNTIME_CONFIG="$TMP_ROOT/runtime.json"
export WONIUNOTE_NGINX_CONFIG="$ETC/nginx.conf"
export WONIUNOTE_SYSTEMD_UNIT="$ETC/woniunote.service"
export WONIUNOTE_SMOKE_HOST=test.example
export WONIUNOTE_SMOKE_SCHEME=http
export WONIUNOTE_SMOKE_PORT=18080
export WONIUNOTE_SMOKE_READONLY_API=/api/articles/types
export WONIUNOTE_SMOKE_THUMB_PATH=/api/thumb/persisted.png
export WONIUNOTE_SMOKE_UPLOAD_PATH=/api/uploads/persisted.txt
export WONIUNOTE_SMOKE_UPLOAD_FILE="$DATA/uploads/persisted.txt"
export WONIUNOTE_SMOKE_UPLOAD_SHA256="$(hash_file "$DATA/uploads/persisted.txt")"
export WONIUNOTE_BUILD_JOBS=1
export MOCK_FAIL_DIR="$TMP_ROOT/fail-once"
export MOCK_SERVICE_STATE="$TMP_ROOT/service.state"
export MOCK_SYSTEMCTL_LOG="$TMP_ROOT/systemctl.log"
export MOCK_CURL_LOG="$TMP_ROOT/curl.log"
export MOCK_SYSTEMD_ANALYZE_LOG="$TMP_ROOT/systemd-analyze.log"
export MOCK_BUILD_LOG="$TMP_ROOT/frontend-builds.log"
export MOCK_CURRENT="$STATE/current"
export MOCK_CURRENT_MV_FAILURES="$TMP_ROOT/current-mv-failures"
export MOCK_UPLOAD_FILE="$DATA/uploads/persisted.txt"
export MOCK_DEPLOY_PID_FILE="$TMP_ROOT/deploy.pid"
export WONIUNOTE_TEST_PID_FILE="$MOCK_DEPLOY_PID_FILE"
mkdir -p "$MOCK_FAIL_DIR"

write_record() {
    local path="$1" from="$2" to="$3" evidence="$TMP_ROOT/compat-evidence.txt"
    printf 'API/session/schema and mixed frontend/backend compatibility fixture %s %s\n' "$from" "$to" > "$evidence"
    cat > "$path" <<EOF
FROM_SHA=$from
TO_SHA=$to
API=PASS
SESSION=PASS
SCHEMA=PASS
OLD_FRONTEND_NEW_BACKEND=PASS
NEW_FRONTEND_OLD_BACKEND=PASS
EVIDENCE=$evidence
EVIDENCE_SHA256=$(hash_file "$evidence")
EOF
}
write_initial_record() {
    local path="$1" target="$2" mode="$3" evidence="${4:-${1%.env}.evidence}"
    printf 'reviewed synthetic initial-install evidence for manager gate tests\n' > "$evidence"
    chmod 0600 "$evidence"
    {
        printf 'TO_SHA=%s\nMODE=%s\nREVIEWED=PASS\n' "$target" "$mode"
        printf 'EVIDENCE=%s\nEVIDENCE_SHA256=%s\n' "$evidence" "$(hash_file "$evidence")"
        if [ "$mode" = maintenance ]; then
            printf 'EDITOR_HANDOFF=PASS\nWRITE_FREEZE=PASS\nBACKUP_RESTORE=PASS\nSCHEMA=PASS\n'
        elif [ "$mode" = fresh ]; then
            printf 'FRESH_INSTANCE=PASS\n'
        fi
    } > "$path"
    chmod 0600 "$path"
}
run_deploy() { bash "$FIXTURE/scripts/deploy_release.sh" deploy --sha "$1" > "$TMP_ROOT/last.log" 2>&1; }
expect_failed_deploy() {
    local sha="$1" label="$2"
    if run_deploy "$sha"; then die "$label unexpectedly succeeded"; fi
}
current_release() { readlink "$STATE/current"; }
assert_current() { [ "$(current_release)" = "$1" ] || die "current release mismatch: expected $1, got $(current_release)"; }

if [ "${WONIUNOTE_TEST_LEGACY_ONLY:-0}" != 1 ]; then
# The process lock is obtained before the transaction journal is created.
flock -n "$STATE/deploy.lock" bash -c 'touch "$1"; sleep 2' _ "$TMP_ROOT/lock-ready" &
lock_holder=$!
for _ in $(seq 1 100); do [ -f "$TMP_ROOT/lock-ready" ] && break; sleep 0.02; done
[ -f "$TMP_ROOT/lock-ready" ] || die "flock holder did not start"
if bash "$FIXTURE/scripts/deploy_release.sh" run-locked bash -c 'touch "$1"' _ "$TMP_ROOT/lock-child-ran" > "$TMP_ROOT/lock.log" 2>&1; then
    die "second process entered while flock was held"
else lock_status=$?; [ "$lock_status" -eq 75 ] || die "flock returned $lock_status, expected 75"; fi
[ ! -e "$STATE/active-transaction" ] && [ ! -e "$TMP_ROOT/lock-child-ran" ] || die "lock contention wrote transaction state"
wait "$lock_holder"
ok "flock contention blocks the second entry before transaction state"
if WONIUNOTE_SETUP_LOCKED=yes bash "$FIXTURE/scripts/deploy_release.sh" assert-locked > "$TMP_ROOT/lock-env-bypass.log" 2>&1; then
    die "an environment flag impersonated a locked setup parent"
fi
ok "an unlocked setup-locked environment flag is rejected"

cat > "$FIXTURE/scripts/setup-lock-probe.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
bash "$WONIUNOTE_PROJECT_DIR/scripts/deploy_release.sh" assert-locked
bash "$WONIUNOTE_PROJECT_DIR/scripts/deploy_release.sh" run-locked bash -c 'touch "$1"; sleep 2' _ "$MOCK_SETUP_NESTED_READY"
EOF
chmod 0755 "$FIXTURE/scripts/setup-lock-probe.sh"
export MOCK_SETUP_NESTED_READY="$TMP_ROOT/setup-nested-ready"
bash "$FIXTURE/scripts/deploy_release.sh" run-locked bash "$FIXTURE/scripts/setup-lock-probe.sh" \
    > "$TMP_ROOT/setup-lock.log" 2>&1 &
setup_lock_holder=$!
for _ in $(seq 1 100); do [ -f "$MOCK_SETUP_NESTED_READY" ] && break; sleep 0.02; done
[ -f "$MOCK_SETUP_NESTED_READY" ] || { cat "$TMP_ROOT/setup-lock.log" >&2; die "nested setup manager did not reuse its parent lock"; }
if bash "$FIXTURE/scripts/deploy_release.sh" run-locked touch "$TMP_ROOT/setup-bypass.txt" > "$TMP_ROOT/setup-contender.log" 2>&1; then
    die "competing setup/deploy entry bypassed active lock"
else lock_status=$?; [ "$lock_status" -eq 75 ] || die "setup lock contender returned $lock_status, expected 75"; fi
wait "$setup_lock_holder"
[ ! -e "$TMP_ROOT/setup-bypass.txt" ] || die "competing entry ran while setup lock was held"
ok "setup-like parent and nested deploy commands share one lock; an unrelated entry is rejected"

# Missing upload smoke configuration fails before building or stopping the old service.
if env -u WONIUNOTE_SMOKE_UPLOAD_PATH -u WONIUNOTE_SMOKE_UPLOAD_FILE -u WONIUNOTE_SMOKE_UPLOAD_SHA256 \
    bash "$FIXTURE/scripts/deploy_release.sh" deploy --sha "$SHA1" > "$TMP_ROOT/missing-upload.log" 2>&1; then
    die "deployment succeeded without required upload smoke"
fi
[ ! -e "$STATE/current" ] && ! grep -q '^stop ' "$MOCK_SYSTEMCTL_LOG" || die "missing upload preflight reached cutover"
ok "missing upload sample is a pre-build/pre-stop error"

export WONIUNOTE_TEST_NOW=1000000
initial_build_count="$(wc -l < "$MOCK_BUILD_LOG" | tr -d ' ')"
stops_before="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if env -u WONIUNOTE_INITIAL_INSTALL_RECORD bash "$FIXTURE/scripts/deploy_release.sh" deploy --sha "$SHA1" \
    > "$TMP_ROOT/initial-deploy-without-record.log" 2>&1; then
    die "initial deploy succeeded without an explicit admission record"
fi
if env -u WONIUNOTE_INITIAL_INSTALL_RECORD bash "$FIXTURE/scripts/deploy_release.sh" start \
    > "$TMP_ROOT/initial-start-without-record.log" 2>&1; then
    die "initial start succeeded without an explicit admission record"
fi
if env -u WONIUNOTE_INITIAL_INSTALL_RECORD bash "$FIXTURE/restart_app.sh" prod \
    > "$TMP_ROOT/initial-restart-without-record.log" 2>&1; then
    die "initial production restart succeeded without an explicit admission record"
fi
cat > "$FIXTURE/scripts/setup_ubuntu.sh" <<EOF
#!/usr/bin/env bash
touch "$TMP_ROOT/setup-was-run"
EOF
chmod 0755 "$FIXTURE/scripts/setup_ubuntu.sh"
if env -u WONIUNOTE_INITIAL_INSTALL_RECORD WONIUNOTE_SETUP_SCRIPT="$FIXTURE/scripts/setup_ubuntu.sh" \
    bash "$FIXTURE/scripts/deploy_release.sh" setup > "$TMP_ROOT/initial-setup-without-record.log" 2>&1; then
    die "initial setup succeeded without an explicit admission record"
fi
[ ! -e "$TMP_ROOT/setup-was-run" ] || die "setup script ran before initial-install admission"
[ "$(wc -l < "$MOCK_BUILD_LOG" | tr -d ' ')" = "$initial_build_count" ] || die "initial gate rejection reached frontend build"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$stops_before" ] || die "initial gate rejection stopped the service"
[ ! -e "$STATE/current" ] || die "initial gate rejection switched current release"
ok "deploy, start, restart and setup fail closed before build or service switch without initial-install evidence"

write_initial_record "$TMP_ROOT/initial-wrong-target.env" 0000000000000000000000000000000000000000 fresh
if WONIUNOTE_INITIAL_INSTALL_RECORD="$TMP_ROOT/initial-wrong-target.env" run_deploy "$SHA1"; then
    die "initial deploy accepted a record bound to another target SHA"
fi
[ "$(wc -l < "$MOCK_BUILD_LOG" | tr -d ' ')" = "$initial_build_count" ] || die "target-SHA mismatch reached frontend build"
write_initial_record "$TMP_ROOT/initial-maintenance.env" "$SHA1" maintenance
export WONIUNOTE_INITIAL_INSTALL_RECORD="$TMP_ROOT/initial-maintenance.env"
run_deploy "$SHA1" || { cat "$TMP_ROOT/last.log" >&2; die "initial isolated deployment failed"; }
RELEASE1="$(current_release)"
ASSET1="$(awk 'NR==1 {print $2}' "$RELEASE1/assets.manifest")"
[ -f "$STATE/${ASSET1#assets/}" ] || [ -f "$STATE/assets/${ASSET1#assets/}" ] || die "first content-hash asset not stored"
file_mode() {
    if stat -c '%a' "$1" >/dev/null 2>&1; then stat -c '%a' "$1"; else stat -f '%Lp' "$1"; fi
}
[ "$(file_mode "$DATA/config-revisions")" = 700 ] || die "config revision directory is not 0700"
CONFIG1_HASH="$(hash_file "$DATA/config-revisions"/*.json)"
[ "$(file_mode "$DATA/config-revisions/$CONFIG1_HASH.json")" = 600 ] || die "config revision file is not 0600"
if grep -R -q 'secret-one' "$RELEASE1"; then die "runtime secret copied into release"; fi
runner_config="$(bash "$RELEASE1/backend_cpp/release_run_backend.sh" "$RELEASE1")"
[ "$runner_config" = "$DATA/config-revisions/$CONFIG1_HASH.json" ] || die "release runner did not use its bound config revision"
grep -q 'http://test.example:18080/' "$MOCK_CURL_LOG" || die "custom smoke port was not included in URL"
for persisted in "$DATA/build/logs/backend.log" "$DATA/build/uploads/keep.txt" "$DATA/uploads/persisted.txt" "$DATA/resource/thumb/persisted.png" "$DATA/secret.marker"; do
    [ -f "$persisted" ] || die "deployment removed persistent path $persisted"
done
[ -L "$RELEASE1/backend_cpp/resource/thumb" ] && [ "$(readlink "$RELEASE1/backend_cpp/resource/thumb")" = "$DATA/resource/thumb" ] || die "nonempty candidate thumb directory was not replaced by the persistent link"
[ "$(hash_file "$DATA/resource/thumb/persisted.png")" = "$(hash_file "$FIXTURE/backend_cpp/resource/thumb/persisted.png")" ] || die "candidate thumbnail was not copied and verified in persistent storage"
grep -Eq '^verify .*/unit-candidate\.[0-9]+\.service$' "$MOCK_SYSTEMD_ANALYZE_LOG" || die "candidate systemd unit was not verified under a valid .service basename"
ASSET1_PATH="$STATE/assets/${ASSET1#assets/}"
ASSET1_HASH_BEFORE_GC_FAIL="$(hash_file "$ASSET1_PATH")"
if MOCK_GC_KEEP_WRITE_FAIL=1 bash "$FIXTURE/scripts/deploy_release.sh" gc > "$TMP_ROOT/gc-enospc.log" 2>&1; then
    die "GC succeeded after keep-manifest writing failed"
fi
[ -f "$ASSET1_PATH" ] && [ "$(hash_file "$ASSET1_PATH")" = "$ASSET1_HASH_BEFORE_GC_FAIL" ] ||
    die "GC removed or changed a current hash asset after keep-manifest failure"
assert_current "$RELEASE1"
ok "GC keep-manifest write failure leaves current hash assets and pointer untouched"
ok "initial publish binds protected runtime config, stores hashed assets and preserves persistent data"

# A production git archive omits ignored/local resource data. Packaging must
# still create resource/ so link_persistent can bind the shared thumbnail dir.
NO_RESOURCE_ROOT="$TMP_ROOT/woniunote-deploy-test.no-resource"
NO_RESOURCE_PROJECT="$NO_RESOURCE_ROOT/project"
NO_RESOURCE_STATE="$NO_RESOURCE_ROOT/state"
NO_RESOURCE_DATA="$NO_RESOURCE_ROOT/data"
NO_RESOURCE_ETC="$NO_RESOURCE_ROOT/etc"
mkdir -p "$NO_RESOURCE_ROOT" "$NO_RESOURCE_STATE" "$NO_RESOURCE_DATA/uploads" "$NO_RESOURCE_ETC"
git clone -q "$FIXTURE" "$NO_RESOURCE_PROJECT"
git -C "$NO_RESOURCE_PROJECT" rm -qr backend_cpp/resource
git -C "$NO_RESOURCE_PROJECT" commit -qm 'candidate without tracked backend resources'
NO_RESOURCE_SHA="$(git -C "$NO_RESOURCE_PROJECT" rev-parse HEAD)"
write_initial_record "$NO_RESOURCE_ROOT/initial-install.env" "$NO_RESOURCE_SHA" fresh "$NO_RESOURCE_ROOT/initial-install.evidence"
if git -C "$NO_RESOURCE_PROJECT" archive --format=tar "$NO_RESOURCE_SHA" | tar -tf - | grep -q '^backend_cpp/resource/'; then
    die "clean candidate archive unexpectedly contains ignored/local backend resources"
fi
printf '{"custom_config":{"jwt_secret":"no-resource-secret"}}\n' > "$NO_RESOURCE_ROOT/runtime.json"
printf 'persistent-upload-without-source-resource\n' > "$NO_RESOURCE_DATA/uploads/persisted.txt"
mkdir -p "$NO_RESOURCE_DATA/resource/thumb"
printf 'persistent-thumb-without-source-resource\n' > "$NO_RESOURCE_DATA/resource/thumb/persisted.png"
printf 'inactive\n' > "$NO_RESOURCE_ROOT/service.state"
touch "$NO_RESOURCE_ROOT/systemctl.log" "$NO_RESOURCE_ROOT/curl.log" "$NO_RESOURCE_ROOT/systemd-analyze.log"
mkdir -p "$NO_RESOURCE_ROOT/fail-once"
NO_RESOURCE_UPLOAD_HASH="$(hash_file "$NO_RESOURCE_DATA/uploads/persisted.txt")"
env -u WONIUNOTE_COMPATIBILITY_RECORD -u WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD \
    WONIUNOTE_PROJECT_DIR="$NO_RESOURCE_PROJECT" \
    WONIUNOTE_STATE_DIR="$NO_RESOURCE_STATE" \
    WONIUNOTE_DATA_DIR="$NO_RESOURCE_DATA" \
    WONIUNOTE_RUNTIME_CONFIG="$NO_RESOURCE_ROOT/runtime.json" \
    WONIUNOTE_NGINX_CONFIG="$NO_RESOURCE_ETC/nginx.conf" \
    WONIUNOTE_SYSTEMD_UNIT="$NO_RESOURCE_ETC/woniunote.service" \
    WONIUNOTE_SMOKE_UPLOAD_PATH=/api/uploads/persisted.txt \
    WONIUNOTE_SMOKE_UPLOAD_FILE="$NO_RESOURCE_DATA/uploads/persisted.txt" \
    WONIUNOTE_SMOKE_UPLOAD_SHA256="$NO_RESOURCE_UPLOAD_HASH" \
    WONIUNOTE_INITIAL_INSTALL_RECORD="$NO_RESOURCE_ROOT/initial-install.env" \
    WONIUNOTE_TEST_PID_FILE="$NO_RESOURCE_ROOT/deploy.pid" \
    MOCK_FAIL_DIR="$NO_RESOURCE_ROOT/fail-once" \
    MOCK_SERVICE_STATE="$NO_RESOURCE_ROOT/service.state" \
    MOCK_SYSTEMCTL_LOG="$NO_RESOURCE_ROOT/systemctl.log" \
    MOCK_CURL_LOG="$NO_RESOURCE_ROOT/curl.log" \
    MOCK_SYSTEMD_ANALYZE_LOG="$NO_RESOURCE_ROOT/systemd-analyze.log" \
    MOCK_CURRENT="$NO_RESOURCE_STATE/current" \
    MOCK_CURRENT_MV_FAILURES="$NO_RESOURCE_ROOT/current-mv-failures" \
    MOCK_UPLOAD_FILE="$NO_RESOURCE_DATA/uploads/persisted.txt" \
    MOCK_THUMB_FILE="$NO_RESOURCE_DATA/resource/thumb/persisted.png" \
    MOCK_DEPLOY_PID_FILE="$NO_RESOURCE_ROOT/deploy.pid" \
    bash "$NO_RESOURCE_PROJECT/scripts/deploy_release.sh" deploy --sha "$NO_RESOURCE_SHA" \
    > "$NO_RESOURCE_ROOT/deploy.log" 2>&1 || { cat "$NO_RESOURCE_ROOT/deploy.log" >&2; die "clean archive without backend_cpp/resource failed deployment"; }
NO_RESOURCE_RELEASE="$(readlink "$NO_RESOURCE_STATE/current")"
[ -d "$NO_RESOURCE_RELEASE/backend_cpp/resource" ] || die "bundle omitted resource directory for clean archive"
[ -L "$NO_RESOURCE_RELEASE/backend_cpp/resource/thumb" ] &&
    [ "$(readlink "$NO_RESOURCE_RELEASE/backend_cpp/resource/thumb")" = "$NO_RESOURCE_DATA/resource/thumb" ] ||
    die "resource/thumb was not linked to persistent data for clean archive"
[ "$(hash_file "$NO_RESOURCE_DATA/uploads/persisted.txt")" = "$NO_RESOURCE_UPLOAD_HASH" ] ||
    die "no-resource deployment changed persistent upload data"
[ -f "$NO_RESOURCE_DATA/resource/thumb/persisted.png" ] || die "no-resource deployment removed persistent thumbnail"
ok "clean Git archive without backend_cpp/resource creates bundle and links persistent thumbnails/uploads"

commit_version() {
    local version="$1" nginx_line="${2:-test.example;}"
    printf '%s\n' "$version" > "$FIXTURE/VERSION"
    printf '%s\n' "$version" > "$FIXTURE/frontend/VERSION"
    printf '%s\n' "$version" > "$FIXTURE/backend_cpp/VERSION"
    cat > "$FIXTURE/configs/woniunote_nginx_prod.conf" <<EOF
http {
    map "\$status:\$uri" \$woniunote_cache_control { default "no-cache, must-revalidate"; "~^(200|304):/assets/.+-[A-Za-z0-9_-]{8,}\\.(js|mjs|css)$" "public, immutable, max-age=31536000"; }
    root @@WONIUNOTE_STATIC_ROOT@@;
    location ~* "^/assets/.+-[A-Za-z0-9_-]{8,}\\.(js|mjs|css)$" { root @@WONIUNOTE_ASSET_ROOT@@; try_files \$uri =404; }
    location / { try_files \$uri /index.html; }
    location ^~ /api { proxy_pass http://127.0.0.1:5173; }
    server_name $nginx_line
    ssl_certificate @@WONIUNOTE_SSL_CERT@@;
    ssl_certificate_key @@WONIUNOTE_SSL_KEY@@;
}
EOF
    git -C "$FIXTURE" add .
    git -C "$FIXTURE" commit -qm "fixture $version"
    git -C "$FIXTURE" rev-parse HEAD
}

# Version 2: build failure leaves the currently served release untouched.
SHA2="$(commit_version v2)"
printf '{"custom_config":{"jwt_secret":"secret-two"}}\n' > "$TMP_ROOT/runtime.json"
CONFIG2_HASH="$(hash_file "$TMP_ROOT/runtime.json")"
write_record "$TMP_ROOT/compat-v1-v2.env" "$SHA1" "$SHA2"
export WONIUNOTE_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v1-v2.env"
BEFORE_CURRENT="$(current_release)"
before_stops="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if MOCK_MISSING_CSS=1 run_deploy "$SHA2"; then die "candidate with an index-referenced but missing CSS entry unexpectedly built"; fi
assert_current "$BEFORE_CURRENT"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$before_stops" ] || die "missing CSS entry stopped the old service"
ok "an index-referenced CSS entry missing from the build/manifest is rejected before service stop"

if MOCK_WRONG_CSS_BODY_ONCE=1 run_deploy "$SHA2"; then die "candidate with an HTML fallback CSS response unexpectedly passed smoke"; fi
assert_current "$BEFORE_CURRENT"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "old service was not restored after wrong CSS response body"
[ ! -e "$STATE/active-transaction" ] || die "wrong CSS response left transaction recovery pending"
grep -q 'HTTP JS/CSS 入口响应内容与冻结候选不一致' "$TMP_ROOT/last.log" || die "wrong CSS response did not fail the frozen-body check"
ok "HTML fallback body for a CSS entry fails candidate smoke and restores the previous release"

before_stops="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if MOCK_NPM_FAIL_ONCE=1 run_deploy "$SHA2"; then die "mock frontend build failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$before_stops" ] || die "old service stopped before candidate build failure"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "old service stopped on build failure"
ok "candidate build failure is rejected before service stop"

before_stops="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if MOCK_CMAKE_FAIL_ONCE=1 run_deploy "$SHA2"; then die "mock backend build failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$before_stops" ] || die "old service stopped before backend build failure"
ok "backend build failure is rejected before service stop"

before_stops="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if MOCK_NGINX_FAIL_ONCE=1 run_deploy "$SHA2"; then die "mock candidate nginx -t failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$before_stops" ] || die "old service stopped before candidate nginx -t failure"
ok "candidate Nginx configuration failure is rejected before service stop"

# A real mocked systemd start failure after pointer/config switch invokes journal recovery.
if MOCK_FAIL_START_ONCE=1 run_deploy "$SHA2"; then die "mock candidate start failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "old service not restarted after candidate start failure"
[ "$(sha256sum "$ETC/nginx.conf" | awk '{print $1}')" = "$(sha256sum "$RELEASE1/nginx.conf" | awk '{print $1}')" ] || die "old nginx config not restored after start failure"
[ ! -e "$STATE/active-transaction" ] || die "active transaction remains after successful recovery"
ok "candidate systemd start failure restored the old release, Nginx config and service"

# An unguarded pointer rename failure still reaches the ERR recovery trap.
rm -f "$MOCK_CURRENT_MV_FAILURES"
if MOCK_FAIL_CURRENT_POINTER_MV=1 run_deploy "$SHA2"; then die "current pointer rename failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "old service was not restarted after pointer rename failure"
[ ! -e "$STATE/active-transaction" ] || die "pointer rename failure left transaction recovery pending"
ok "current pointer rename failure reached the ERR recovery trap"

# Nginx reload failure after writing the new file must put the exact old config back.
if MOCK_FAIL_RELOAD_ONCE=1 run_deploy "$SHA2"; then die "mock Nginx reload failure unexpectedly deployed"; fi
assert_current "$BEFORE_CURRENT"
[ "$(sha256sum "$ETC/nginx.conf" | awk '{print $1}')" = "$(sha256sum "$RELEASE1/nginx.conf" | awk '{print $1}')" ] || die "old nginx config not restored after reload failure"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "old service not active after Nginx reload failure"
ok "Nginx reload failure restored and reloaded the old Nginx configuration"

# Version 2 succeeds; then publish v3 at day six, rollback and publish v4 after the old asset window.
export WONIUNOTE_TEST_NOW=1086400
run_deploy "$SHA2" || { cat "$TMP_ROOT/last.log" >&2; die "v2 deployment failed"; }
RELEASE2="$(current_release)"
ASSET2="$(awk 'NR==1 {print $2}' "$RELEASE2/assets.manifest")"
CONFIG1_HASH="$(basename "$(cat "$RELEASE1/runtime-config.ref")" .json)"
[ -f "$DATA/config-revisions/$CONFIG1_HASH.json" ] && [ -f "$DATA/config-revisions/$CONFIG2_HASH.json" ] || die "release config revision was removed or not stored"

SHA3="$(commit_version v3)"
printf '{"custom_config":{"jwt_secret":"secret-three"}}\n' > "$TMP_ROOT/runtime.json"
CONFIG3_HASH="$(hash_file "$TMP_ROOT/runtime.json")"
write_record "$TMP_ROOT/compat-v2-v3.env" "$SHA2" "$SHA3"
export WONIUNOTE_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v2-v3.env"
export WONIUNOTE_TEST_NOW=1518400
run_deploy "$SHA3" || { cat "$TMP_ROOT/last.log" >&2; die "v3 deployment failed"; }
RELEASE3="$(current_release)"
ASSET3="$(awk 'NR==1 {print $2}' "$RELEASE3/assets.manifest")"
for resource in "$ASSET1" "$ASSET2" "$ASSET3"; do
    [ -f "$STATE/assets/${resource#assets/}" ] || die "hash asset not reachable inside seven-day window: $resource"
done

write_record "$TMP_ROOT/compat-v3-v2.env" "$SHA3" "$SHA2"
export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v3-v2.env"
before_stops="$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)"
if env -u WONIUNOTE_SMOKE_UPLOAD_PATH -u WONIUNOTE_SMOKE_UPLOAD_FILE -u WONIUNOTE_SMOKE_UPLOAD_SHA256 \
    bash "$FIXTURE/scripts/deploy_release.sh" rollback > "$TMP_ROOT/rollback-no-upload.log" 2>&1; then
    die "rollback succeeded without required upload smoke"
fi
assert_current "$RELEASE3"
[ "$(grep -c '^stop ' "$MOCK_SYSTEMCTL_LOG" || true)" = "$before_stops" ] || die "rollback stopped current service before upload smoke preflight"
if MOCK_FAIL_UPLOAD_ONCE=1 bash "$FIXTURE/scripts/deploy_release.sh" rollback > "$TMP_ROOT/rollback-fail.log" 2>&1; then
    die "mock rollback smoke upload failure unexpectedly succeeded"
fi
assert_current "$RELEASE3"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "current v3 service not restored after rollback smoke failure"

# Successful rollback also starts the old config revision despite the external source config changing.
printf '{"custom_config":{"jwt_secret":"secret-four"}}\n' > "$TMP_ROOT/runtime.json"
# The source currently points at v3, so rollback to v2 is tested before another publish.
export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v3-v2.env"
if bash "$FIXTURE/scripts/deploy_release.sh" rollback > "$TMP_ROOT/rollback.log" 2>&1; then :; else cat "$TMP_ROOT/rollback.log" >&2; die "rollback failed"; fi
assert_current "$RELEASE2"
runner_config="$(bash "$RELEASE2/backend_cpp/release_run_backend.sh" "$RELEASE2")"
[ "$runner_config" = "$DATA/config-revisions/$CONFIG2_HASH.json" ] || die "rollback did not use v2 immutable config"
[ -f "$DATA/config-revisions/$CONFIG3_HASH.json" ] || die "shared config revision was garbage-collected"
ok "three versions, seven-day retention, rollback and immutable per-release configs verified with a controlled clock"

SHA4="$(commit_version v4)"
write_record "$TMP_ROOT/compat-v2-v4.env" "$SHA2" "$SHA4"
export WONIUNOTE_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v2-v4.env"
export WONIUNOTE_TEST_NOW=1691201
signal_deploy() {
    local signal="$1" sha="$2" pid status
    rm -f "$MOCK_DEPLOY_PID_FILE"
    MOCK_SIGNAL_ON_RELOAD="$signal" bash "$FIXTURE/scripts/deploy_release.sh" deploy --sha "$sha" > "$TMP_ROOT/signal-$signal.log" 2>&1 &
    pid=$!
    for _ in $(seq 1 200); do [ -s "$MOCK_DEPLOY_PID_FILE" ] && break; sleep 0.02; done
    [ -s "$MOCK_DEPLOY_PID_FILE" ] || { kill "$pid" 2>/dev/null || true; wait "$pid" || true; die "deploy manager did not publish test PID"; }
    if wait "$pid"; then status=0; else status=$?; fi
    [ "$status" -ne 0 ] || die "$signal interruption unexpectedly succeeded"
}
signal_deploy TERM "$SHA4"
assert_current "$RELEASE2"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "TERM handler did not restore old service"
ok "TERM during Nginx reload entered transaction recovery"

signal_deploy KILL "$SHA4"
[ -e "$STATE/active-transaction" ] || die "SIGKILL did not leave a recoverable journal"
bash "$FIXTURE/scripts/deploy_release.sh" gc > "$TMP_ROOT/post-kill-recovery.log" 2>&1 || {
    cat "$TMP_ROOT/post-kill-recovery.log" >&2; die "next locked entry failed to recover SIGKILL journal";
}
assert_current "$RELEASE2"
[ "$(cat "$MOCK_SERVICE_STATE")" = active ] || die "next invocation did not restart old service after SIGKILL"
ok "SIGKILL leaves a journal that the next locked entry recovers"

run_deploy "$SHA4" || { cat "$TMP_ROOT/last.log" >&2; die "v4 deployment after retention boundary failed"; }
RELEASE4="$(current_release)"
ASSET4="$(awk 'NR==1 {print $2}' "$RELEASE4/assets.manifest")"
[ ! -d "$RELEASE1" ] || die "release older than seven days was retained"
[ ! -f "$STATE/assets/${ASSET1#assets/}" ] || die "expired unreferenced hash asset was retained"
for resource in "$ASSET2" "$ASSET3" "$ASSET4"; do
    [ -f "$STATE/assets/${resource#assets/}" ] || die "current, rollback or recent hash asset was deleted: $resource"
done
for config_revision in "$CONFIG1_HASH" "$CONFIG2_HASH" "$CONFIG3_HASH"; do
    [ -f "$DATA/config-revisions/$config_revision.json" ] || die "GC removed shared config/secret revision $config_revision"
done
for persisted in "$DATA/build/logs/backend.log" "$DATA/build/uploads/keep.txt" "$DATA/uploads/persisted.txt" "$DATA/resource/thumb/persisted.png" "$DATA/secret.marker"; do
    [ -f "$persisted" ] || die "GC removed shared persistent state $persisted"
done
ok "expired release/assets are pruned while config revisions and uploads/thumbs/logs/secrets remain"

# A standalone GC invocation has no dynamically scoped deploy timestamp. Make
# v2 cease being the rollback target shortly before expiry, then advance only
# the controlled clock and verify the independent GC command removes it.
SHA5="$(commit_version v5)"
write_record "$TMP_ROOT/compat-v4-v5.env" "$SHA4" "$SHA5"
export WONIUNOTE_COMPATIBILITY_RECORD="$TMP_ROOT/compat-v4-v5.env"
export WONIUNOTE_TEST_NOW=2296000
run_deploy "$SHA5" || { cat "$TMP_ROOT/last.log" >&2; die "v5 deployment before v2 retention expiry failed"; }
RELEASE5="$(current_release)"
ASSET5="$(awk 'NR==1 {print $2}' "$RELEASE5/assets.manifest")"
[ -d "$RELEASE2" ] && [ -f "$STATE/assets/${ASSET2#assets/}" ] || die "recent unreferenced v2 release/asset was pruned early"
export WONIUNOTE_TEST_NOW=2296002
bash "$FIXTURE/scripts/deploy_release.sh" gc > "$TMP_ROOT/standalone-gc.log" 2>&1 || {
    cat "$TMP_ROOT/standalone-gc.log" >&2; die "standalone GC command failed after retention boundary";
}
[ ! -d "$RELEASE2" ] && [ ! -f "$STATE/assets/${ASSET2#assets/}" ] || die "standalone GC retained expired unreferenced v2 release/asset"
assert_current "$RELEASE5"
[ "$(readlink "$STATE/rollback")" = "$RELEASE4" ] || die "standalone GC changed the rollback pointer"
for resource in "$ASSET4" "$ASSET5"; do
    [ -f "$STATE/assets/${resource#assets/}" ] || die "standalone GC removed current/rollback hash asset: $resource"
done
ok "standalone GC expires an unreferenced release at seven days while preserving current and rollback assets"

# AC21-16 cache policy structural assertions. A live Nginx HTTP/cache-header check is reserved for Linux acceptance.
TEMPLATE="$REPO_ROOT/configs/woniunote_nginx_prod.conf"
grep -q 'no-cache, must-revalidate' "$TEMPLATE" || die "index/non-hash revalidation policy missing"
grep -q 'public, immutable, max-age=31536000' "$TEMPLATE" || die "immutable hash asset policy missing"
grep -Fq '"~^(2[0-9][0-9]|304):/assets/' "$TEMPLATE" || die "quoted immutable response status map missing"
grep -Fq 'add_header Cache-Control $woniunote_cache_control always;' "$TEMPLATE" || die "cache policy must apply to error responses"
grep -Fq 'location ~* "^/assets/' "$TEMPLATE" && grep -Fq 'try_files $uri =404' "$TEMPLATE" || die "quoted hash regex must keep missing assets at 404"
grep -q 'location \^~ /api' "$TEMPLATE" && grep -q 'location \^~ /uploads' "$TEMPLATE" || die "API/upload proxy precedence changed"
ok "Nginx template routes hash-only immutable cache and preserves API/upload precedence"
fi

# First migration from a mutable legacy install pins its known project dist.
# Mutating the original tree after commit must not change the rollback page.
LEGACY_FIXTURE="$TMP_ROOT/legacy-project"
LEGACY_TEST_ROOT="$TMP_ROOT/woniunote-deploy-test.legacy"
LEGACY_STATE="$LEGACY_TEST_ROOT/state"
LEGACY_DATA="$LEGACY_TEST_ROOT/data"
LEGACY_ETC="$LEGACY_TEST_ROOT/etc"
mkdir -p "$LEGACY_FIXTURE/scripts" "$LEGACY_FIXTURE/configs" "$LEGACY_FIXTURE/frontend/scripts" \
    "$LEGACY_FIXTURE/backend_cpp/resource" "$LEGACY_FIXTURE/backend_cpp/build" \
    "$LEGACY_STATE" "$LEGACY_DATA/uploads" "$LEGACY_ETC"
cp "$REPO_ROOT/scripts/deploy_release.sh" "$LEGACY_FIXTURE/scripts/deploy_release.sh"
cp "$REPO_ROOT/scripts/release_run_backend.sh" "$LEGACY_FIXTURE/scripts/release_run_backend.sh"
cp "$REPO_ROOT/configs/woniunote_nginx_prod.conf" "$LEGACY_FIXTURE/configs/woniunote_nginx_prod.conf"
cat > "$LEGACY_FIXTURE/.gitignore" <<'EOF'
frontend/dist/
backend_cpp/build/
backend_cpp/uploads/
backend_cpp/resource/thumb/
EOF
cat > "$LEGACY_FIXTURE/frontend/package.json" <<'EOF'
{"name":"legacy-fixture","version":"1.0.0"}
EOF
cat > "$LEGACY_FIXTURE/frontend/package-lock.json" <<'EOF'
{"name":"legacy-fixture","lockfileVersion":3,"packages":{}}
EOF
printf 'process.exit(0)\n' > "$LEGACY_FIXTURE/frontend/scripts/check-node-version.mjs"
cat > "$LEGACY_FIXTURE/backend_cpp/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.20)
project(legacy_fixture)
EOF
printf 'old\n' > "$LEGACY_FIXTURE/VERSION"
printf 'old\n' > "$LEGACY_FIXTURE/frontend/VERSION"
printf 'old\n' > "$LEGACY_FIXTURE/backend_cpp/VERSION"
printf 'fixture resource\n' > "$LEGACY_FIXTURE/backend_cpp/resource/fixture.txt"
git -C "$LEGACY_FIXTURE" init -q
git -C "$LEGACY_FIXTURE" config user.name DeployTest
git -C "$LEGACY_FIXTURE" config user.email deploy-test@example.invalid
git -C "$LEGACY_FIXTURE" add .
git -C "$LEGACY_FIXTURE" commit -qm 'legacy source v1'
LEGACY_SHA_OLD="$(git -C "$LEGACY_FIXTURE" rev-parse HEAD)"
mkdir -p "$LEGACY_FIXTURE/frontend/dist/assets"
LEGACY_ASSET_HASH="$(printf 'legacy-page' | sha256sum | cut -c1-12)"
printf '<!doctype html><link rel="stylesheet" href="/assets/legacy-%s.css"><script type="module" src="/assets/legacy-%s.js"></script><body>legacy-page-v1</body>\n' \
    "$LEGACY_ASSET_HASH" "$LEGACY_ASSET_HASH" > "$LEGACY_FIXTURE/frontend/dist/index.html"
printf 'legacy-asset\n' > "$LEGACY_FIXTURE/frontend/dist/assets/legacy-$LEGACY_ASSET_HASH.js"
printf 'body{color:#123}\n' > "$LEGACY_FIXTURE/frontend/dist/assets/legacy-$LEGACY_ASSET_HASH.css"
cat > "$LEGACY_FIXTURE/backend_cpp/build/woniunote_backend" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$1"
EOF
chmod 0755 "$LEGACY_FIXTURE/backend_cpp/build/woniunote_backend"
printf '{"custom_config":{"jwt_secret":"legacy-secret"}}\n' > "$LEGACY_FIXTURE/backend_cpp/build/config.local.json"
printf 'persistent-legacy-upload\n' > "$LEGACY_DATA/uploads/persisted.txt"
printf 'active\n' > "$LEGACY_TEST_ROOT/service.state"
cat > "$LEGACY_ETC/nginx.conf" <<EOF
events {}
http {
    include /etc/nginx/mime.types;
    server {
        listen 18080;
        root $LEGACY_FIXTURE/frontend/dist;
        location / { try_files \$uri /index.html; }
    }
}
EOF
printf 'new\n' > "$LEGACY_FIXTURE/VERSION"
printf 'new\n' > "$LEGACY_FIXTURE/frontend/VERSION"
printf 'new\n' > "$LEGACY_FIXTURE/backend_cpp/VERSION"
git -C "$LEGACY_FIXTURE" add VERSION frontend/VERSION backend_cpp/VERSION
git -C "$LEGACY_FIXTURE" commit -qm 'legacy source v2'
LEGACY_SHA_NEW="$(git -C "$LEGACY_FIXTURE" rev-parse HEAD)"
printf '{"custom_config":{"jwt_secret":"legacy-new-secret"}}\n' > "$LEGACY_TEST_ROOT/runtime.json"
printf 'FROM_SHA=%s\nTO_SHA=%s\nAPI=PASS\nSESSION=PASS\nSCHEMA=PASS\nOLD_FRONTEND_NEW_BACKEND=PASS\nNEW_FRONTEND_OLD_BACKEND=PASS\n' \
    "$LEGACY_SHA_OLD" "$LEGACY_SHA_NEW" > "$LEGACY_TEST_ROOT/compat.env"
printf 'fixture evidence\n' > "$LEGACY_TEST_ROOT/compat-evidence.txt"
printf 'EVIDENCE=%s\nEVIDENCE_SHA256=%s\n' "$LEGACY_TEST_ROOT/compat-evidence.txt" \
    "$(hash_file "$LEGACY_TEST_ROOT/compat-evidence.txt")" >> "$LEGACY_TEST_ROOT/compat.env"
export WONIUNOTE_PROJECT_DIR="$LEGACY_FIXTURE"
export WONIUNOTE_STATE_DIR="$LEGACY_STATE"
export WONIUNOTE_DATA_DIR="$LEGACY_DATA"
export WONIUNOTE_RUNTIME_CONFIG="$LEGACY_TEST_ROOT/runtime.json"
export WONIUNOTE_NGINX_CONFIG="$LEGACY_ETC/nginx.conf"
export WONIUNOTE_SYSTEMD_UNIT="$LEGACY_ETC/woniunote.service"
export WONIUNOTE_SMOKE_UPLOAD_FILE="$LEGACY_DATA/uploads/persisted.txt"
export WONIUNOTE_SMOKE_UPLOAD_SHA256="$(hash_file "$LEGACY_DATA/uploads/persisted.txt")"
export WONIUNOTE_COMPATIBILITY_RECORD="$LEGACY_TEST_ROOT/compat.env"
export WONIUNOTE_TEST_NOW=2000000
export MOCK_FAIL_DIR="$LEGACY_TEST_ROOT/fail-once"
export MOCK_SERVICE_STATE="$LEGACY_TEST_ROOT/service.state"
export MOCK_SYSTEMCTL_LOG="$LEGACY_TEST_ROOT/systemctl.log"
export MOCK_CURL_LOG="$LEGACY_TEST_ROOT/curl.log"
export MOCK_SYSTEMD_ANALYZE_LOG="$LEGACY_TEST_ROOT/systemd-analyze.log"
export MOCK_CURRENT="$LEGACY_STATE/current"
export MOCK_CURRENT_MV_FAILURES="$LEGACY_TEST_ROOT/current-mv-failures"
export MOCK_UPLOAD_FILE="$LEGACY_DATA/uploads/persisted.txt"
export MOCK_DEPLOY_PID_FILE="$LEGACY_TEST_ROOT/deploy.pid"
export WONIUNOTE_TEST_PID_FILE="$MOCK_DEPLOY_PID_FILE"
mkdir -p "$MOCK_FAIL_DIR"
touch "$LEGACY_TEST_ROOT/systemctl.log" "$LEGACY_TEST_ROOT/curl.log" "$LEGACY_TEST_ROOT/systemd-analyze.log"
LEGACY_MANAGER="$LEGACY_FIXTURE/scripts/deploy_release.sh"
cat > "$LEGACY_ETC/nginx.conf" <<EOF
events {}
http {
    server {
        listen 18080;
        root $LEGACY_FIXTURE/frontend/dist;
        location /other { alias $LEGACY_FIXTURE/frontend/dist/; }
    }
}
EOF
legacy_stops_before="$(grep -c '^stop woniunote' "$LEGACY_TEST_ROOT/systemctl.log" || true)"
if bash "$LEGACY_MANAGER" deploy --sha "$LEGACY_SHA_NEW" > "$LEGACY_TEST_ROOT/inline-alias.log" 2>&1; then
    die "legacy snapshot accepted an inline mutable alias beside a standard root"
fi
grep -q '无法完整解析的 include/root/alias' "$LEGACY_TEST_ROOT/inline-alias.log" || {
    cat "$LEGACY_TEST_ROOT/inline-alias.log" >&2
    die "legacy inline alias was not rejected by the fail-closed parser"
}
[ "$(grep -c '^stop woniunote' "$LEGACY_TEST_ROOT/systemctl.log" || true)" = "$legacy_stops_before" ] ||
    die "legacy Nginx alias rejection stopped the existing service"
ok "legacy snapshot rejects an inline mutable alias even beside a classifiable root"
cat > "$LEGACY_ETC/nginx.conf" <<EOF
events {}
http {
    include /etc/nginx/mime.types;
    server {
        listen 18080;
        root $LEGACY_FIXTURE/frontend/dist;
        location / { try_files \$uri /index.html; }
    }
}
EOF
bash "$LEGACY_MANAGER" deploy --sha "$LEGACY_SHA_NEW" > "$LEGACY_TEST_ROOT/deploy.log" 2>&1 || {
    cat "$LEGACY_TEST_ROOT/deploy.log" >&2
    die "legacy first migration did not complete"
}
LEGACY_RELEASE="$(readlink "$LEGACY_STATE/rollback")"
[ "$(basename "$LEGACY_RELEASE")" = "legacy-$(printf '%s' "$LEGACY_SHA_OLD" | cut -c1-12)-$WONIUNOTE_TEST_NOW" ] || {
    printf 'unexpected legacy rollback target: %s\n' "$LEGACY_RELEASE" >&2
    die "first migration did not install a distinct frozen legacy rollback release"
}
[ "$(cat "$LEGACY_RELEASE/source.sha")" = "$LEGACY_SHA_OLD" ] || die "legacy rollback release lost the original source SHA"
grep -Fq "$LEGACY_RELEASE/frontend/dist" "$LEGACY_RELEASE/nginx.conf" ||
    die "legacy Nginx static root was not pinned to its release snapshot"
if grep -Fq "$LEGACY_FIXTURE/frontend/dist" "$LEGACY_RELEASE/nginx.conf"; then
    die "legacy Nginx config retained a mutable project dist reference"
fi
printf '<!doctype html><body>mutated-project-page</body>\n' > "$LEGACY_FIXTURE/frontend/dist/index.html"
cat > "$LEGACY_TEST_ROOT/compat-reverse.env" <<EOF
FROM_SHA=$LEGACY_SHA_NEW
TO_SHA=$LEGACY_SHA_OLD
API=PASS
SESSION=PASS
SCHEMA=PASS
OLD_FRONTEND_NEW_BACKEND=PASS
NEW_FRONTEND_OLD_BACKEND=PASS
EVIDENCE=$LEGACY_TEST_ROOT/compat-evidence.txt
EVIDENCE_SHA256=$(hash_file "$LEGACY_TEST_ROOT/compat-evidence.txt")
EOF
export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$LEGACY_TEST_ROOT/compat-reverse.env"
bash "$LEGACY_MANAGER" rollback > "$LEGACY_TEST_ROOT/rollback.log" 2>&1 || {
    cat "$LEGACY_TEST_ROOT/rollback.log" >&2
    die "rollback to frozen legacy release failed"
}
[ "$(readlink "$LEGACY_STATE/current")" = "$LEGACY_RELEASE" ] || die "rollback did not select frozen legacy release"
legacy_rollback_tx="$(ls -dt "$LEGACY_STATE"/transactions/rollback-* | head -1)"
grep -Fq 'legacy-page-v1' "$legacy_rollback_tx/index.body" || die "rollback served the mutated project page instead of frozen legacy page"
grep -Fq "$LEGACY_RELEASE/frontend/dist" "$LEGACY_ETC/nginx.conf" || die "rollback Nginx config lost its frozen legacy root"
ok "legacy migration pins the project static root; rollback serves frozen page after source dist mutation"

# The host runtime wrapper forwards only the explicit first-install evidence
# path to the guest mutation. A fake Lima executable keeps this a local test.
RUNNER_TEST_ROOT="$TMP_ROOT/iter21-runner-forward"
RUNNER_FAKE_LIMA="$RUNNER_TEST_ROOT/fake-limactl"
RUNNER_ARGS="$RUNNER_TEST_ROOT/limactl-args.log"
RUNNER_SHELL_CALLS="$RUNNER_TEST_ROOT/shell-calls.log"
mkdir -p "$RUNNER_TEST_ROOT"
cat > "$RUNNER_FAKE_LIMA" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = list ]; then
    printf 'woniunote-iter21-systemd-20261024t0028z Running 127.0.0.1:61808\n'
    exit 0
fi
if [ "${1:-}" = -y ]; then
    printf 'shell\n' >> "$RUNNER_SHELL_CALLS"
    printf '%s\n' "$@" > "$RUNNER_ARGS"
    exit 0
fi
exit 2
EOF
chmod 0755 "$RUNNER_FAKE_LIMA"
RUNNER_RECORD_PATH=/var/lib/woniunote-iter21-business/evidence/first-maintenance/test/initial-install.env
env WONIUNOTE_ITER21_D04_HANDOFF=approved \
    WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD="$RUNNER_RECORD_PATH" \
    LIMACTL="$RUNNER_FAKE_LIMA" RUNNER_ARGS="$RUNNER_ARGS" RUNNER_SHELL_CALLS="$RUNNER_SHELL_CALLS" \
    bash "$REPO_ROOT/scripts/tests/iter21-business-runtime/run.sh" deploy-first candidate-2 \
    0000000000000000000000000000000000000000 /api/thumb/smoke.png /uploads/smoke.png \
    /tmp/persisted.png 0000000000000000000000000000000000000000000000000000000000000000 \
    first-install-after-maintenance --confirm-d04-mutation || die "deploy-first wrapper rejected the explicit guest evidence path"
grep -Fqx "WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD=$RUNNER_RECORD_PATH" "$RUNNER_ARGS" || \
    die "deploy-first wrapper did not allowlist-forward the guest evidence path"
shell_calls_before="$(wc -l < "$RUNNER_SHELL_CALLS" | tr -d ' ')"
if env WONIUNOTE_ITER21_D04_HANDOFF=approved \
    WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD=/tmp/outside.env \
    LIMACTL="$RUNNER_FAKE_LIMA" RUNNER_ARGS="$RUNNER_ARGS" RUNNER_SHELL_CALLS="$RUNNER_SHELL_CALLS" \
    bash "$REPO_ROOT/scripts/tests/iter21-business-runtime/run.sh" deploy-first candidate-2 \
    0000000000000000000000000000000000000000 /api/thumb/smoke.png /uploads/smoke.png \
    /tmp/persisted.png 0000000000000000000000000000000000000000000000000000000000000000 \
    first-install-after-maintenance --confirm-d04-mutation > "$RUNNER_TEST_ROOT/rejected-path.log" 2>&1; then
    die "deploy-first wrapper accepted evidence outside the isolated guest evidence directory"
fi
[ "$(wc -l < "$RUNNER_SHELL_CALLS" | tr -d ' ')" = "$shell_calls_before" ] || \
    die "invalid initial-install path reached the guest mutation"
ok "run.sh forwards only an allowlisted isolated evidence path for deploy-first"

if [ "${WONIUNOTE_TEST_LEGACY_ONLY:-0}" = 1 ]; then
    printf '[deploy-test] PASS isolated legacy migration test complete (mock systemd/Nginx/curl; not Linux production acceptance)\n'
else
    printf '[deploy-test] PASS isolated deployment transaction tests complete (mock systemd/Nginx/curl; not Linux production acceptance)\n'
fi
