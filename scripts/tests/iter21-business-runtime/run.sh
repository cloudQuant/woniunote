#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTANCE="woniunote-iter21-systemd-20261024t0028z"
EVIDENCE_ROOT=/tmp/woniunote-iter21-evidence/deploy-business-runtime
ORIGINAL_SQL_COMMIT=fefab0570c370bebd796df9c683343805d850d18
LIMACTL="${LIMACTL:-$(command -v limactl || true)}"

usage() {
    cat >&2 <<'EOF'
用法:
  run.sh inspect
  run.sh capture LABEL
  run.sh api
  run.sh audit-original-schema
  run.sh prepare-original-ui --confirm-d04-mutation
  run.sh repair-original-upload-layout --confirm-d04-mutation
  run.sh stage CANDIDATE LOCAL_REPO EXPECTED_COMMIT --confirm-d04-mutation
  run.sh stop-original EXPECTED_BINARY_SHA --confirm-d04-mutation
  WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD=/var/lib/woniunote-iter21-business/evidence/first-maintenance/RUN_ID/initial-install.env run.sh deploy-first CANDIDATE EXPECTED_COMMIT THUMB_URL UPLOAD_URL UPLOAD_FILE UPLOAD_SHA first-install-after-maintenance --confirm-d04-mutation
  run.sh deploy CANDIDATE EXPECTED_COMMIT COMPAT_RECORD THUMB_URL UPLOAD_URL UPLOAD_FILE UPLOAD_SHA compatibility-preflight-reviewed --confirm-d04-mutation
  run.sh rollback CURRENT_SHA TARGET_SHA COMPAT_RECORD THUMB_URL UPLOAD_URL UPLOAD_FILE UPLOAD_SHA compatibility-preflight-reviewed rollback-target-reviewed --confirm-d04-mutation

Mutations require both --confirm-d04-mutation and
WONIUNOTE_ITER21_D04_HANDOFF=approved. The Lima guest is never auto-started.
EOF
    exit 2
}

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
valid_label() { [[ "$1" = candidate-2 || "$1" = candidate-3 || "$1" = candidate-4 || "$1" = candidate-5 ]]; }
valid_sha() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }
valid_hash() { [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }
valid_url_path() { [[ "$1" = /api/thumb/* && "$1" != *$'\n'* ]]; }
valid_upload_url() { [[ "$1" = /api/uploads/* || "$1" = /uploads/* ]]; }
valid_initial_record_path() {
    [[ "$1" = /var/lib/woniunote-iter21-business/evidence/* && "$1" != *$'\n'* &&
       "$1" != */../* && "$1" != */.. && "$1" != *//* ]]
}

require_lima() {
    [ -n "$LIMACTL" ] && [ -x "$LIMACTL" ] || fail "找不到 limactl"
}
require_target_instance() {
    local target_row
    target_row="$("$LIMACTL" list | awk -v instance="$INSTANCE" \
        '$1 == instance { printf "%s\t%s", $2, $3 }')"
    [ "$target_row" = $'Running\t127.0.0.1:61808' ] || \
        fail "目标 Lima 实例必须已在预期名称和 SSH 端口上运行；拒绝自动启动或操作其他 VM"
}
require_mutation_confirmation() {
    [ "${WONIUNOTE_ITER21_D04_HANDOFF:-}" = approved ] || \
        fail "缺少 root 的 D04 VM handoff 环境确认"
    [ "${1:-}" = --confirm-d04-mutation ] || \
        fail "VM 写操作必须显式提供 --confirm-d04-mutation"
}
run_guest() {
    local -a guest_env
    require_target_instance
    if [ "${WONIUNOTE_ITER21_D04_HANDOFF:-}" = approved ]; then
        guest_env=(WONIUNOTE_ITER21_D04_HANDOFF=received)
        if [ "${1:-}" = deploy-first ]; then
            valid_initial_record_path "${WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD:-}" || \
                fail "deploy-first requires an explicit guest evidence record path under the isolated evidence directory"
            guest_env+=("WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD=$WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD")
        fi
        "$LIMACTL" -y shell "$INSTANCE" -- sudo -n env \
            "${guest_env[@]}" /bin/bash -s -- "$@" < "$SCRIPT_DIR/guest.sh"
    else
        "$LIMACTL" -y shell "$INSTANCE" -- sudo -n /bin/bash -s -- "$@" < "$SCRIPT_DIR/guest.sh"
    fi
}
capture_guest() {
    local label="$1" operation="${2:-capture}" run_id run_dir rc
    [[ "$label" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || fail "capture label 格式无效"
    run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id-$label"
    mkdir -p "$run_dir"
    chmod 0700 "$EVIDENCE_ROOT" "$run_dir"
    {
        printf 'run_id=%s\n' "$run_id"
        printf 'instance=%s\n' "$INSTANCE"
        printf 'capture_label=%s\n' "$label"
        printf 'capture_scope=metadata_and_read_only_api; no credentials or response bodies\n'
    } > "$run_dir/manifest.txt"
    chmod 0600 "$run_dir/manifest.txt"
    set +e
    if [ "$operation" = capture ]; then
        run_guest capture "$label" > "$run_dir/guest-evidence.txt" 2>&1
    elif [ "$operation" = audit-original-schema ]; then
        run_guest "$operation" > "$run_dir/guest-evidence.txt" 2>&1
    else
        fail "unsupported evidence capture operation"
    fi
    rc=$?
    set -e
    chmod 0600 "$run_dir/guest-evidence.txt"
    printf 'capture_exit=%s\n' "$rc" >> "$run_dir/manifest.txt"
    printf 'guest_evidence_sha256=%s\n' "$(hash_file "$run_dir/guest-evidence.txt")" >> "$run_dir/manifest.txt"
    printf 'evidence_dir=%s\n' "$run_dir"
    cat "$run_dir/guest-evidence.txt"
    return "$rc"
}
capture_mutation_guest() {
    local label="$1" run_id run_dir rc
    shift
    [[ "$label" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || fail "mutation evidence label 格式无效"
    run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id-$label"
    mkdir -p "$run_dir"
    chmod 0700 "$EVIDENCE_ROOT" "$run_dir"
    {
        printf 'run_id=%s\n' "$run_id"
        printf 'instance=%s\n' "$INSTANCE"
        printf 'operation=%s\n' "$label"
        printf 'capture_scope=service_and_schema_metadata; no credentials or response bodies\n'
    } > "$run_dir/manifest.txt"
    chmod 0600 "$run_dir/manifest.txt"
    set +e
    run_guest "$@" > "$run_dir/guest-evidence.txt" 2>&1
    rc=$?
    set -e
    chmod 0600 "$run_dir/guest-evidence.txt"
    printf 'operation_exit=%s\n' "$rc" >> "$run_dir/manifest.txt"
    printf 'guest_evidence_sha256=%s\n' "$(hash_file "$run_dir/guest-evidence.txt")" >> "$run_dir/manifest.txt"
    printf 'evidence_dir=%s\n' "$run_dir"
    cat "$run_dir/guest-evidence.txt"
    return "$rc"
}

[ "$#" -ge 1 ] || usage
require_lima
command_name="$1"
shift

case "$command_name" in
    inspect)
        [ "$#" -eq 0 ] || usage
        run_guest inspect
        ;;
    capture)
        [ "$#" -eq 1 ] || usage
        capture_guest "$1"
        ;;
    api)
        [ "$#" -eq 0 ] || usage
        run_guest api
        ;;
    audit-original-schema)
        [ "$#" -eq 0 ] || usage
        capture_guest before-original-v2-schema-audit audit-original-schema
        ;;
    prepare-original-ui)
        [ "$#" -eq 1 ] || usage
        require_mutation_confirmation "$1"
        repo_root="$(cd "$SCRIPT_DIR/../../.." && pwd)"
        [ "$(git -C "$repo_root" rev-parse --verify "$ORIGINAL_SQL_COMMIT^{commit}")" = "$ORIGINAL_SQL_COMMIT" ] || \
            fail "pinned original-v2 SQL commit is unavailable or mismatched"
        sql_archive_dir="$(mktemp -d /tmp/woniunote-iter21-d04-sql.XXXXXX)"
        trap 'rm -rf "$sql_archive_dir"' EXIT
        sql_archive="$sql_archive_dir/original-v2-sql.tar.gz"
        git -C "$repo_root" archive --format=tar "$ORIGINAL_SQL_COMMIT" \
            scripts/sql/01_users.sql scripts/sql/02_article.sql scripts/sql/03_comment.sql \
            scripts/sql/04_favorite.sql scripts/sql/05_credit.sql scripts/sql/06_category.sql \
            scripts/sql/07_card_item.sql scripts/sql/08_math_training.sql \
            scripts/sql/09_article_category.sql | gzip -n > "$sql_archive"
        sql_archive_sha="$(hash_file "$sql_archive")"
        remote_archive="/tmp/iter21-d04-original-sql-$(date -u +%Y%m%dT%H%M%SZ)-$$.tar.gz"
        run_guest assert-original-sql-path-free "$remote_archive"
        require_target_instance
        "$LIMACTL" copy --backend=scp "$sql_archive" "$INSTANCE:$remote_archive"
        capture_mutation_guest original-ui-and-schema prepare-original-ui \
            "$remote_archive" "$sql_archive_sha" "$ORIGINAL_SQL_COMMIT"
        ;;
    stage)
        [ "$#" -eq 4 ] || usage
        candidate="$1"; source_repo="$2"; expected_commit="$3"; confirmation="$4"
        require_mutation_confirmation "$confirmation"
        valid_label "$candidate" || fail "只允许 candidate-2、candidate-3、candidate-4 或 candidate-5"
        valid_sha "$expected_commit" || fail "expected commit 必须是完整 40 位 SHA"
        source_repo="$(cd "$source_repo" && pwd)" || fail "源码目录不存在"
        [ -d "$source_repo/.git" ] || fail "候选目录必须是 Git 仓库"
        actual_commit="$(git -C "$source_repo" rev-parse --verify HEAD)"
        [ "$actual_commit" = "$expected_commit" ] || fail "候选 HEAD 与预期 commit 不一致"
        [ -z "$(git -C "$source_repo" status --porcelain --untracked-files=all)" ] || \
            fail "候选源码工作树不干净，拒绝传输"
        run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
        remote_stage="/tmp/iter21-d04-$candidate-$run_id"
        run_guest assert-stage-path-free "$remote_stage"
        require_target_instance
        "$LIMACTL" copy --backend=scp -r "$source_repo" "$INSTANCE:$remote_stage"
        run_guest install-candidate "$candidate" "$expected_commit" "$remote_stage"
        ;;
    stop-original)
        [ "$#" -eq 2 ] || usage
        expected_binary_sha="$1"; confirmation="$2"
        require_mutation_confirmation "$confirmation"
        valid_hash "$expected_binary_sha" || fail "旧二进制 SHA-256 格式无效"
        run_guest stop-original "$expected_binary_sha"
        ;;
    repair-original-upload-layout)
        [ "$#" -eq 1 ] || usage
        require_mutation_confirmation "$1"
        capture_mutation_guest original-upload-layout repair-original-upload-layout
        ;;
    deploy-first)
        [ "$#" -eq 8 ] || usage
        candidate="$1"; expected_commit="$2"; thumb_url="$3"; upload_url="$4"
        upload_file="$5"; upload_sha="$6"; confirmation="$7"; deploy_confirmation="$8"
        require_mutation_confirmation "$deploy_confirmation"
        [ "$confirmation" = first-install-after-maintenance ] || fail "首次维护安装需显式写 first-install-after-maintenance"
        valid_label "$candidate" || fail "首次候选只允许 candidate-2"
        [ "$candidate" = candidate-2 ] || fail "首次维护过渡固定使用 candidate-2"
        valid_sha "$expected_commit" || fail "expected commit 必须是完整 40 位 SHA"
        valid_url_path "$thumb_url" || fail "缩略图 URL 必须是 /api/thumb/..."
        valid_upload_url "$upload_url" || fail "上传 URL 必须是 /api/uploads/... 或 /uploads/..."
        valid_hash "$upload_sha" || fail "上传样例 SHA-256 格式无效"
        [[ "$upload_file" = /* ]] || fail "上传样例文件必须是 guest 绝对路径"
        run_guest deploy-first "$candidate" "$expected_commit" "$thumb_url" "$upload_url" "$upload_file" "$upload_sha"
        ;;
    deploy)
        [ "$#" -eq 9 ] || usage
        candidate="$1"; expected_commit="$2"; compat_record="$3"; thumb_url="$4"; upload_url="$5"
        upload_file="$6"; upload_sha="$7"; confirmation="$8"; deploy_confirmation="$9"
        require_mutation_confirmation "$deploy_confirmation"
        [ "$confirmation" = compatibility-preflight-reviewed ] || fail "部署前须显式确认兼容预检已由 root 审阅"
        valid_label "$candidate" || fail "只允许 candidate-2、candidate-3、candidate-4 或 candidate-5"
        valid_sha "$expected_commit" || fail "expected commit 必须是完整 40 位 SHA"
        [[ "$compat_record" = /* ]] || fail "兼容记录必须是 guest 绝对路径"
        valid_url_path "$thumb_url" || fail "缩略图 URL 必须是 /api/thumb/..."
        valid_upload_url "$upload_url" || fail "上传 URL 必须是 /api/uploads/... 或 /uploads/..."
        valid_hash "$upload_sha" || fail "上传样例 SHA-256 格式无效"
        [[ "$upload_file" = /* ]] || fail "上传样例文件必须是 guest 绝对路径"
        run_guest deploy "$candidate" "$expected_commit" "$compat_record" "$thumb_url" "$upload_url" "$upload_file" "$upload_sha"
        ;;
    rollback)
        [ "$#" -eq 10 ] || usage
        current_sha="$1"; target_sha="$2"; compat_record="$3"; thumb_url="$4"; upload_url="$5"
        upload_file="$6"; upload_sha="$7"; confirmation="$8"; rollback_confirmation="$9"; extra="${10}"
        require_mutation_confirmation "$extra"
        [ "$confirmation" = compatibility-preflight-reviewed ] || fail "回滚前须显式确认逆向兼容预检已由 root 审阅"
        [ "$rollback_confirmation" = rollback-target-reviewed ] || fail "必须显式确认回滚目标 SHA"
        valid_sha "$current_sha" && valid_sha "$target_sha" || fail "当前/目标 SHA 必须为完整 commit SHA"
        [[ "$compat_record" = /* ]] || fail "回滚兼容记录必须是 guest 绝对路径"
        valid_url_path "$thumb_url" || fail "缩略图 URL 必须是 /api/thumb/..."
        valid_upload_url "$upload_url" || fail "上传 URL 必须是 /api/uploads/... 或 /uploads/..."
        valid_hash "$upload_sha" || fail "上传样例 SHA-256 格式无效"
        [[ "$upload_file" = /* ]] || fail "上传样例文件必须是 guest 绝对路径"
        run_guest rollback "$current_sha" "$target_sha" "$compat_record" "$thumb_url" "$upload_url" "$upload_file" "$upload_sha"
        ;;
    *) usage ;;
esac
