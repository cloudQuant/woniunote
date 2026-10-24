#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

MODE="${1:?real or adapter required}"
RUN_ID="${2:?run id required}"
ROOT=/opt/woniunote-iter21-runtime
STATE=/var/lib/woniunote-iter21-state
DATA=/var/lib/woniunote-iter21-data
EVIDENCE="$DATA/evidence"
FIXTURE="$DATA/fixture-repo"
TOOLS="$ROOT/bin"
mkdir -p "$DATA" "$DATA/uploads" "$EVIDENCE" "$TOOLS"
exec > >(tee -a "$EVIDENCE/runtime.log") 2>&1

record() { printf '%s\n' "$*" | tee -a "$EVIDENCE/manifest.txt"; }
require() { command -v "$1" >/dev/null 2>&1 || { record "FAIL missing command: $1"; exit 20; }; }

record "run_id=$RUN_ID"
record "mode=$MODE"
record "nginx_version=$(nginx -v 2>&1)"
record "nginx_package=$(dpkg-query -W -f='${Version}' nginx)"
record "systemd_pid1=$(cat /proc/1/comm)"
record "nginx_template_sha256=$(sha256sum "$ROOT/input/woniunote_nginx_prod.conf" | awk '{print $1}')"
record "deploy_script_sha256=$(sha256sum "$ROOT/input/deploy_release.sh" | awk '{print $1}')"
record 'fixture_scope=synthetic HTTP backend and frontend; D04 business compatibility NOT_RUN'

require git
require curl
require openssl
require sha256sum
require /usr/bin/node
require /usr/bin/python3
require findmnt
record "entry_asset_parser_node=$(/usr/bin/node --version) (real runtime Node.js; fixture shim delegates parser stdin)"

if [ "$MODE" = real ]; then
    [ "$(cat /proc/1/comm)" = systemd ] || { record 'FAIL systemd is not PID 1'; exit 21; }
    /usr/bin/systemctl is-system-running >/dev/null 2>&1 || {
        state="$(/usr/bin/systemctl is-system-running 2>&1 || true)"
        case "$state" in degraded|running) ;; *) record "FAIL systemd manager state=$state"; exit 22 ;; esac
    }
    /usr/bin/systemctl start nginx
    /usr/bin/systemctl is-active --quiet nginx
    record 'systemd_nginx_start=PASS (real systemctl and nginx.service)'
elif [ "$MODE" = adapter ]; then
    [ "$(cat /proc/1/comm)" != systemd ] || { record 'FAIL adapter requested with systemd PID 1'; exit 23; }
    record 'systemd=GAP (private container systemd did not start); deploy systemctl calls use explicit fixture adapter'
else
    record "FAIL unknown mode=$MODE"
    exit 24
fi

mkdir -p /etc/ssl/woniunote
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/ssl/woniunote/fixture.key \
    -out /etc/ssl/woniunote/fixture.crt \
    -subj '/CN=yunjinqi.top' >/dev/null 2>&1
chmod 0600 /etc/ssl/woniunote/fixture.key

/bin/bash "$ROOT/prepare_fixture.sh" "$FIXTURE" "$STATE" "$DATA" "$ROOT/input"
state_mount_options="$(findmnt -n -o OPTIONS -T "$STATE")"
case ",$state_mount_options," in
    *,noexec,*) record "FAIL state tmpfs is not executable: $state_mount_options"; exit 25 ;;
    *) record "state_tmpfs_exec=PASS ($state_mount_options; no noexec flag)" ;;
esac
export ITER21_STATE="$STATE" ITER21_DATA="$DATA" ITER21_EVIDENCE="$EVIDENCE"
export ITER21_REAL_SYSTEMD="$MODE"
export PATH="$TOOLS:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

install -m 0755 "$ROOT/systemctl-pause-wrapper.sh" "$TOOLS/systemctl"

export WONIUNOTE_PROJECT_DIR="$FIXTURE"
export WONIUNOTE_STATE_DIR="$STATE"
export WONIUNOTE_DATA_DIR="$DATA"
export WONIUNOTE_RUNTIME_CONFIG="$DATA/runtime-config.json"
export WONIUNOTE_NGINX_CONFIG=/etc/nginx/nginx.conf
export WONIUNOTE_SSL_CERT=/etc/ssl/woniunote/fixture.crt
export WONIUNOTE_SSL_KEY=/etc/ssl/woniunote/fixture.key
export WONIUNOTE_SYSTEMD_UNIT=/etc/systemd/system/woniunote.service
export WONIUNOTE_SERVICE_NAME=woniunote
export WONIUNOTE_NGINX_SERVICE_NAME=nginx
export WONIUNOTE_SMOKE_UPLOAD_PATH=/api/uploads/smoke.bin
export WONIUNOTE_SMOKE_UPLOAD_FILE="$DATA/uploads/smoke.bin"
export WONIUNOTE_SMOKE_UPLOAD_SHA256="$(sha256sum "$DATA/uploads/smoke.bin" | awk '{print $1}')"
export WONIUNOTE_SMOKE_HOST=yunjinqi.top
export WONIUNOTE_SMOKE_SCHEME=https
export WONIUNOTE_SMOKE_PORT=443
export WONIUNOTE_SMOKE_READONLY_API=/api/articles/types
export WONIUNOTE_SMOKE_THUMB_PATH=/api/thumb/fixture-12345678.png
export WONIUNOTE_RECOVERY_BUDGET_SECONDS=60
export WONIUNOTE_DEPLOY_TESTING=1
export WONIUNOTE_BUILD_JOBS=2
export WONIUNOTE_STOP_TIMEOUT_SECONDS=10
export WONIUNOTE_START_TIMEOUT_SECONDS=10
export WONIUNOTE_HEALTH_TIMEOUT_SECONDS=14
export WONIUNOTE_SMOKE_TIMEOUT_SECONDS=2
export WONIUNOTE_FAIL_AT=
export WONIUNOTE_COMPATIBILITY_RECORD="$DATA/compatibility.env"
export WONIUNOTE_ROLLBACK_COMPATIBILITY_RECORD="$DATA/compatibility.env"

if [ "$MODE" = adapter ]; then
    "$TOOLS/systemctl" start nginx
    record 'nginx_start=PASS (real nginx binary started through explicitly named systemctl adapter)'
fi

DEPLOY="$FIXTURE/scripts/deploy_release.sh"
META="$DATA/fixture-meta.txt"
V1="$(awk -F= '$1 == "v1" {print $2}' "$META")"
V2="$(awk -F= '$1 == "v2" {print $2}' "$META")"
V3="$(awk -F= '$1 == "v3" {print $2}' "$META")"
V4="$(awk -F= '$1 == "v4" {print $2}' "$META")"
BASE_TIME=1900000000

write_compat() {
    local from="$1" to="$2" note="$DATA/fixture-compat-evidence.txt" evidence_hash
    cat > "$note" <<EOF
FIXTURE_ONLY synthetic contract record for $from -> $to.
No real frontend/backend API, session, schema, or user-data compatibility was measured.
D04 business compatibility remains NOT_RUN.
EOF
    evidence_hash="$(sha256sum "$note" | awk '{print $1}')"
    cat > "$WONIUNOTE_COMPATIBILITY_RECORD" <<EOF
FIXTURE_ONLY=1
SCOPE=temporary synthetic deployment fixture; D04 business compatibility NOT_RUN
FROM_SHA=$from
TO_SHA=$to
API=PASS
SESSION=PASS
SCHEMA=PASS
OLD_FRONTEND_NEW_BACKEND=PASS
NEW_FRONTEND_OLD_BACKEND=PASS
EVIDENCE=$note
EVIDENCE_SHA256=$evidence_hash
EOF
    record "fixture_compat_validator_input=$from->$to sha256=$evidence_hash; D04=NOT_RUN"
}

write_initial_install_record() {
    local to="$1" evidence="$EVIDENCE/initial-install-evidence.txt" record_file="$EVIDENCE/initial-install.env" evidence_hash
    cat > "$evidence" <<EOF
FIXTURE_ONLY=1
MODE=fresh
Reviewed isolated runtime fixture admission for target $to.
The dedicated test tmpfs has no prior current release or user data.
FRESH_INSTANCE=PASS applies only to this synthetic empty fixture; D04 business compatibility remains NOT_RUN.
EOF
    evidence_hash="$(sha256sum "$evidence" | awk '{print $1}')"
    cat > "$record_file" <<EOF
TO_SHA=$to
MODE=fresh
REVIEWED=PASS
FRESH_INSTANCE=PASS
EVIDENCE=$evidence
EVIDENCE_SHA256=$evidence_hash
EOF
    chmod 0600 "$evidence" "$record_file"
    export WONIUNOTE_INITIAL_INSTALL_RECORD="$record_file"
    record "fixture_initial_install_record=FIXTURE_ONLY mode=fresh target=$to evidence_sha256=$evidence_hash; D04=NOT_RUN"
}

run_deploy() {
    local label="$1" now="$2" sha="$3" rc
    shift 3
    export WONIUNOTE_TEST_NOW="$now"
    export WONIUNOTE_TEST_PID_FILE="$DATA/test-pid-$label"
    record "COMMAND $label: deploy --sha $sha (fixture source SHA)"
    set +e
    bash "$DEPLOY" deploy --sha "$sha" "$@" 2>&1 | tee -a "$EVIDENCE/$label.log"
    rc=${PIPESTATUS[0]}
    set -e
    record "EXIT $label=$rc"
    return "$rc"
}

run_gc() {
    local label="$1" now="$2" rc
    export WONIUNOTE_TEST_NOW="$now"
    export WONIUNOTE_TEST_PID_FILE="$DATA/test-pid-$label"
    record "COMMAND $label: gc"
    set +e
    bash "$DEPLOY" gc 2>&1 | tee -a "$EVIDENCE/$label.log"
    rc=${PIPESTATUS[0]}
    set -e
    record "EXIT $label=$rc"
    return "$rc"
}

run_rollback() {
    local label="$1" now="$2" from="$3" to="$4" rc
    write_compat "$from" "$to"
    export WONIUNOTE_TEST_NOW="$now"
    export WONIUNOTE_TEST_PID_FILE="$DATA/test-pid-$label"
    record "COMMAND $label: rollback (fixture $from -> $to)"
    set +e
    bash "$DEPLOY" rollback 2>&1 | tee -a "$EVIDENCE/$label.log"
    rc=${PIPESTATUS[0]}
    set -e
    record "EXIT $label=$rc"
    return "$rc"
}

assert_current_sha() {
    local expected="$1" actual
    actual="$(cat "$STATE/current/source.sha")"
    [ "$actual" = "$expected" ] || { record "FAIL current source SHA=$actual expected=$expected"; return 1; }
    record "current_sha=$actual"
}

probe_version() {
    local version="$1"
    record "COMMAND http-probe expected=$version"
    /usr/bin/python3 "$ROOT/http_probe.py" "$version" 2>&1 | tee -a "$EVIDENCE/http-$version.log"
}

asset_path_for_version() {
    local version="$1" asset
    asset="$(awk -F= -v wanted="$version" '$1 == wanted {print $2; exit}' "$DATA/asset-paths.env")"
    [ -n "$asset" ] || { record "FAIL fixture asset path for $version was not recorded"; return 1; }
    printf '%s\n' "$asset"
}

remember_asset() {
    local version="$1" asset css_asset
    asset="$(grep -Eo '/assets/[^\" ]+\.js' "$STATE/current/frontend/dist/index.html" | head -1)"
    [ -n "$asset" ] || { record "FAIL active index has no hashed asset for $version"; return 1; }
    css_asset="$(grep -Eo '/assets/[^\" ]+\.css' "$STATE/current/frontend/dist/index.html" | head -1)"
    [ -n "$css_asset" ] || { record "FAIL active index has no hashed CSS entry asset for $version"; return 1; }
    awk -F= -v wanted="$version" '$1 != wanted && $1 != wanted "-css"' "$DATA/asset-paths.env" 2>/dev/null > "$DATA/asset-paths.env.tmp" || true
    printf '%s=%s\n' "$version" "$asset" >> "$DATA/asset-paths.env.tmp"
    printf '%s-css=%s\n' "$version" "$css_asset" >> "$DATA/asset-paths.env.tmp"
    mv -f "$DATA/asset-paths.env.tmp" "$DATA/asset-paths.env"
    record "asset_paths[$version]=$asset,$css_asset"
}

probe_asset() {
    local version="$1" expected_status="$2" path status
    path="$(asset_path_for_version "$version")"
    status="$(/usr/bin/python3 "$ROOT/http_probe.py" --asset-status "$path" 2>&1)" || {
        record "FAIL asset probe $version expected HTTP $expected_status: $status"; return 1;
    }
    [ "$status" = "$expected_status" ] || { record "FAIL asset $version status=$status expected=$expected_status"; return 1; }
    record "asset[$version]=$status path=$path"
}

check_real_reload() {
    local before="$1" after='' mode_label
    if [ "$MODE" = real ]; then mode_label=systemd; else mode_label='real nginx behind systemctl adapter'; fi
    for _ in $(seq 1 50); do
        after="$(nginx_worker_pids)"
        [ -n "$after" ] && [ "$after" != "$before" ] && break
        sleep 0.1
    done
    [ -n "$after" ] && [ "$after" != "$before" ] || {
        record "FAIL nginx reload did not replace worker pids before=$before after=$after"; return 1;
    }
    record "nginx_reload=PASS old_workers='$before' new_workers='$after' via $mode_label"
}

nginx_worker_pids() {
    local master
    [ -s /run/nginx.pid ] || return 0
    master="$(cat /run/nginx.pid)"
    ps -o pid= --ppid "$master" | awk '{$1=$1; print}' | sort -n | tr '\n' ' '
}

fill_state_to_enospc() {
    local result
    record 'COMMAND fill dedicated 64 MiB tmpfs past capacity to force kernel ENOSPC'
    df -Pk "$STATE" | tee -a "$EVIDENCE/enospc-df-before.txt"
    set +e
    dd if=/dev/zero of="$STATE/.iter21-enospc-filler" bs=1M count=96 conv=fsync status=none 2> "$EVIDENCE/enospc.stderr"
    result=$?
    set -e
    [ "$result" -ne 0 ] && grep -q 'No space left on device' "$EVIDENCE/enospc.stderr" || {
        record "FAIL expected kernel ENOSPC, exit=$result stderr=$(cat "$EVIDENCE/enospc.stderr")"; return 1;
    }
    [ "$(findmnt -n -o FSTYPE -T "$STATE")" = tmpfs ] || { record 'FAIL deploy state is not on tmpfs'; return 1; }
    record "enospc=PASS (dd exit=$result; kernel returned ENOSPC on tmpfs; mount=$(findmnt -n -o FSTYPE,SIZE -T "$STATE"))"
}

recover_enospc() {
    local current_before="$1"
    rm -f "$STATE/.iter21-enospc-filler"
    printf 'recovered\n' > "$STATE/.iter21-recovery-probe"
    [ "$(cat "$STATE/.iter21-recovery-probe")" = recovered ] || { record 'FAIL tmpfs remained unwritable after freeing space'; return 1; }
    [ "$(readlink "$STATE/current")" = "$current_before" ] || { record 'FAIL current symlink changed after ENOSPC'; return 1; }
    /usr/bin/systemctl is-active --quiet nginx || [ "$MODE" = adapter ]
    record 'enospc_recovery=PASS state writable and prior release pointer preserved'
}

pause_and_sigkill_v4() {
    local now="$1" old_workers="$2" deploy_pid pgid phase pidfile
    write_compat "$V3" "$V4"
    export WONIUNOTE_TEST_NOW="$now"
    export WONIUNOTE_TEST_PID_FILE="$DATA/test-pid-sigkill"
    export ITER21_PAUSE_BEFORE_CANDIDATE_START=1
    export ITER21_PAUSE_MARKER="$DATA/candidate-start-reached"
    rm -f "$ITER21_PAUSE_MARKER"
    record "COMMAND sigkill-deploy-v4: deploy --sha $V4 (pause after real nginx reload, before candidate service start)"
    setsid bash -c 'exec bash "$1" deploy --sha "$2"' _ "$DEPLOY" "$V4" > "$EVIDENCE/sigkill-deploy-v4.log" 2>&1 &
    deploy_pid=$!
    printf '%s\n' "$deploy_pid" > "$DATA/deploy-group-leader"
    for _ in $(seq 1 300); do
        [ -f "$ITER21_PAUSE_MARKER" ] && break
        kill -0 "$deploy_pid" 2>/dev/null || break
        sleep 0.1
    done
    if [ ! -f "$ITER21_PAUSE_MARKER" ]; then
        record "FAIL deploy never reached post-reload pause; pid=$deploy_pid"
        return 1
    fi
    pidfile="$WONIUNOTE_TEST_PID_FILE"
    [ -s "$pidfile" ] || { record 'FAIL deploy test PID file missing'; return 1; }
    deploy_pid="$(cat "$pidfile")"
    pgid="$(ps -o pgid= -p "$deploy_pid" | tr -d '[:space:]')"
    [ -n "$pgid" ] || { record 'FAIL deploy process group could not be identified'; return 1; }
    phase="$(cat "$STATE/active-transaction")"
    [ "$(cat "$STATE/transactions/$phase/phase")" = nginx-installed ] || {
        record "FAIL SIGKILL cut phase=$(cat "$STATE/transactions/$phase/phase") expected=nginx-installed"; return 1;
    }
    record "sigkill_cut=real nginx reload returned; active_transaction=$phase phase=nginx-installed pid=$deploy_pid pgid=$pgid"
    kill -KILL -- "-$pgid"
    set +e
    wait "$deploy_pid" 2>/dev/null
    set -e
    unset ITER21_PAUSE_BEFORE_CANDIDATE_START ITER21_PAUSE_MARKER
    [ -f "$STATE/active-transaction" ] || { record 'FAIL SIGKILL did not leave active transaction for recovery'; return 1; }
    [ "$(readlink "$STATE/current")" != "$(cat "$STATE/transactions/$phase/old-release")" ] || {
        record 'FAIL SIGKILL happened before candidate entry switch'; return 1;
    }
    export WONIUNOTE_TEST_NOW="$now"
    record 'COMMAND sigkill-recovery: deploy_release.sh gc (must recover active transaction first)'
    bash "$DEPLOY" gc 2>&1 | tee -a "$EVIDENCE/sigkill-recovery.log"
    [ ! -f "$STATE/active-transaction" ] || { record 'FAIL active transaction survived recovery'; return 1; }
    [ "$(readlink "$STATE/current")" = "$(cat "$STATE/transactions/$phase/old-release")" ] || {
        record 'FAIL recovery did not restore prior current release'; return 1;
    }
    assert_current_sha "$V3"
    /usr/bin/systemctl is-active --quiet nginx || [ "$MODE" = adapter ]
    /usr/bin/systemctl is-active --quiet woniunote || [ "$MODE" = adapter ]
    probe_version v3
    probe_asset v1 200
    probe_asset v3 200
    probe_asset v1-css 200
    probe_asset v3-css 200
    check_real_reload "$old_workers"
    record 'sigkill_recovery=PASS prior release/config restored, real Nginx reloaded, prior backend smoke passed'
}

# First install and inspect the Nginx template through a real nginx.service.
record "fixture_sha[v1]=$V1"
record "fixture_sha[v2]=$V2"
record "fixture_sha[v3]=$V3"
record "fixture_sha[v4]=$V4"
write_initial_install_record "$V1"
export WONIUNOTE_TEST_NOW="$BASE_TIME"
export WONIUNOTE_TEST_PID_FILE="$DATA/test-pid-v1"
record "COMMAND deploy-v1: deploy --sha $V1"
bash "$DEPLOY" deploy --sha "$V1" 2>&1 | tee -a "$EVIDENCE/deploy-v1.log"
if [ -s "$EVIDENCE/locked-entry.log" ] && grep -Eq 'FLOCK[[:space:]]+ADVISORY[[:space:]]+WRITE' "$EVIDENCE/locked-entry.log"; then
    record 'lock_owner_ancestry=PASS Linux deploy_release.sh __locked entered with captured FLOCK WRITE owner and /proc status; deploy proceeded to build'
else
    record 'FAIL Linux __locked owner ancestry evidence was not captured'
    exit 26
fi
assert_current_sha "$V1"
remember_asset v1
probe_version v1
probe_asset v1 200
probe_asset v1-css 200

# Exercise real index parsing and missing-entry rejection before switching.
write_compat "$V1" "$V2"
export ITER21_FIXTURE_MISSING_CSS_FILE=1
if run_deploy missing-entry-css "$((BASE_TIME + 1))" "$V2"; then
    record 'FAIL missing CSS entry unexpectedly deployed'
    exit 27
fi
unset ITER21_FIXTURE_MISSING_CSS_FILE
grep -q 'index.html 引用的入口文件缺失' "$EVIDENCE/missing-entry-css.log" || {
    record 'FAIL missing CSS entry did not fail the frozen candidate asset check'; exit 28;
}
assert_current_sha "$V1"
probe_version v1
record 'missing_entry_css=PASS candidate rejected before release switch; old frontend remains served'

# The wrapper corrupts the candidate CSS in the shared hash store before the
# candidate service starts; Nginx returns that actual HTML body with HTTP 200.
write_compat "$V1" "$V2"
export ITER21_FIXTURE_WRONG_CSS_BODY_ONCE=1
if run_deploy wrong-http-css-body "$((BASE_TIME + 2))" "$V2"; then
    record 'FAIL wrong CSS HTTP body unexpectedly deployed'
    exit 29
fi
unset ITER21_FIXTURE_WRONG_CSS_BODY_ONCE
grep -q 'HTTP JS/CSS 入口响应内容与冻结候选不一致' "$EVIDENCE/wrong-http-css-body.log" || {
    record 'FAIL wrong CSS HTTP body did not fail the frozen candidate body check'; exit 30;
}
[ -s "$DATA/wrong-css-body-path" ] && [ -s "$DATA/wrong-css-body-original" ] || {
    record 'FAIL real Nginx wrong-body injection did not capture restoration data'; exit 31;
}
wrong_css_file="$(cat "$DATA/wrong-css-body-path")"
cp -p "$DATA/wrong-css-body-original" "$wrong_css_file"
assert_current_sha "$V1"
probe_version v1
probe_asset v1-css 200
record 'wrong_http_css_body=PASS real Nginx served injected HTML body; hash smoke rejected candidate and restored v1'

# Fill only this container's bounded tmpfs and observe a kernel ENOSPC error.
write_compat "$V1" "$V2"
fill_state_to_enospc
current_before="$(readlink "$STATE/current")"
if run_deploy deploy-v2-enospc "$((BASE_TIME + 1))" "$V2"; then
    record 'FAIL deployment unexpectedly succeeded while the state tmpfs was full'
    exit 31
else
    record 'deploy_v2_enospc=PASS expected non-zero exit while tmpfs returned ENOSPC'
fi
grep -q 'No space left on device' "$EVIDENCE/deploy-v2-enospc.log" || {
    record 'FAIL deploy attempt did not surface the full-filesystem error'; exit 32;
}
recover_enospc "$current_before"
assert_current_sha "$V1"
probe_version v1

# Normal release/rollback cycles use only fixture compatibility records.
old_workers="$(nginx_worker_pids)"
write_compat "$V1" "$V2"
run_deploy deploy-v2 "$((BASE_TIME + 2))" "$V2"
assert_current_sha "$V2"
remember_asset v2
probe_version v2
probe_asset v1 200
probe_asset v2 200
probe_asset v1-css 200
probe_asset v2-css 200
check_real_reload "$old_workers"

run_rollback rollback-v1 "$((BASE_TIME + 3))" "$V2" "$V1"
assert_current_sha "$V1"
remember_asset v1
probe_version v1
probe_asset v2 200
probe_asset v2-css 200

old_workers="$(nginx_worker_pids)"
write_compat "$V1" "$V3"
run_deploy deploy-v3 "$((BASE_TIME + 4))" "$V3"
assert_current_sha "$V3"
remember_asset v3
probe_version v3
probe_asset v1 200
probe_asset v2 200
probe_asset v3 200
probe_asset v1-css 200
probe_asset v2-css 200
probe_asset v3-css 200
check_real_reload "$old_workers"

run_rollback rollback-v1-again "$((BASE_TIME + 5))" "$V3" "$V1"
assert_current_sha "$V1"
remember_asset v1
probe_version v1
probe_asset v3 200
probe_asset v3-css 200

# A second deploy makes v3 the rollback target; all three releases fall within
# the seven-day window and their content-addressed assets remain reachable.
write_compat "$V1" "$V3"
run_deploy deploy-v3-again "$((BASE_TIME + 6))" "$V3"
assert_current_sha "$V3"
remember_asset v3
probe_version v3
probe_asset v1 200
probe_asset v2 200
probe_asset v3 200
probe_asset v1-css 200
probe_asset v2-css 200
probe_asset v3-css 200

run_gc gc-within-seven-day-window "$((BASE_TIME + 3 + 604799))"
probe_asset v1 200
probe_asset v2 200
probe_asset v3 200

run_gc gc-after-retention-window "$((BASE_TIME + 3 + 604801))"
probe_asset v1 200
probe_asset v3 200
probe_asset v2 404
probe_asset v1-css 200
probe_asset v3-css 200
probe_asset v2-css 404
assert_current_sha "$V3"

old_workers="$(nginx_worker_pids)"
pause_and_sigkill_v4 "$((BASE_TIME + 8 + 604800))" "$old_workers"

record 'result=PASS (isolated fixture runtime only; D04 business compatibility NOT_RUN)'
