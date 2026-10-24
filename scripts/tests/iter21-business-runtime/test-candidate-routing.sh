#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GUEST="$REPO_ROOT/scripts/tests/iter21-business-runtime/guest.sh"
RUNNER="$REPO_ROOT/scripts/tests/iter21-business-runtime/run.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/iter21-candidate-routing.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { printf '[candidate-routing] FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf '[candidate-routing] PASS: %s\n' "$*"; }

# Keep both entry points bounded to candidates 2-5, while deploy-first remains
# pinned to candidate-2 until the separate first-install transition is complete.
for script in "$RUNNER" "$GUEST"; do
    label_line="$(sed -n '/^valid_label() /p' "$script")"
    [[ "$label_line" == *'candidate-2'* && "$label_line" == *'candidate-3'* && "$label_line" == *'candidate-4'* && "$label_line" == *'candidate-5'* ]] || \
        fail "$script does not allow candidates 2, 3, 4, and 5"
    grep -Fq '[ "$candidate" = candidate-2 ] || fail' "$script" || \
        fail "$script no longer pins deploy-first to candidate-2"
done
grep -Fq '/tmp/iter21-d04-candidate-5-*' "$GUEST" || \
    fail 'guest staging namespace does not accept candidate-5 paths'
grep -Fq '[ ! -e "$target" ] || fail "candidate destination exists; refusing overwrite"' "$GUEST" || \
    fail 'candidate installation no longer refuses to overwrite an existing destination'
pass 'candidate-5 staging is allowed, existing destinations stay protected, and deploy-first remains candidate-2 only'

BUSINESS="$TMP_ROOT/business"
STATE="$BUSINESS/release-state"
mkdir -p "$BUSINESS" "$STATE"

# Load the actual routing and source-pointer helpers from guest.sh without
# invoking its privileged command dispatcher.
extract_function() {
    local name="$1"
    awk -v start="${name}() {" '
        $0 == start { copying=1 }
        copying { print }
        copying && $0 == "}" { exit }
    ' "$GUEST"
}

HELPERS="$TMP_ROOT/helpers.sh"
for name in valid_label valid_sha; do
    sed -n "/^${name}() /p" "$GUEST" >> "$HELPERS"
done
for name in repo_path verify_repo current_source_sha rollback_source_sha rollback_manager_repo_for_sha; do
    extract_function "$name" >> "$HELPERS"
done
source "$HELPERS"

make_candidate() {
    local label="$1" marker repo
    repo="$BUSINESS/$label"
    mkdir -p "$repo/scripts"
    printf '%s\n' "$label" > "$repo/source.marker"
    printf '#!/bin/sh\nexit 0\n' > "$repo/scripts/deploy_release.sh"
    chmod 0755 "$repo/scripts/deploy_release.sh"
    git -C "$repo" init -q
    git -C "$repo" config user.name CandidateRoutingTest
    git -C "$repo" config user.email candidate-routing@example.invalid
    git -C "$repo" add source.marker scripts/deploy_release.sh
    git -C "$repo" commit -qm "$label fixture"
    marker="$(git -C "$repo" rev-parse HEAD)"
    printf '%s\n' "$marker"
}

SHA3="$(make_candidate candidate-3)"
SHA4="$(make_candidate candidate-4)"
SHA5="$(make_candidate candidate-5)"
mkdir -p "$BUSINESS/releases/current4" "$BUSINESS/releases/rollback3"
printf '%s\n' "$SHA4" > "$BUSINESS/releases/current4/source.sha"
printf '%s\n' "$SHA3" > "$BUSINESS/releases/rollback3/source.sha"
ln -s "$BUSINESS/releases/current4" "$STATE/current"
ln -s "$BUSINESS/releases/rollback3" "$STATE/rollback"

[[ "$(current_source_sha)" = "$SHA4" ]] || fail 'current pointer did not retain candidate-4 SHA'
[[ "$(rollback_source_sha)" = "$SHA3" ]] || fail 'rollback pointer did not retain explicit candidate-3 SHA'
[[ "$(rollback_manager_repo_for_sha "$SHA4")" = "$BUSINESS/candidate-4" ]] || \
    fail 'candidate-4 current SHA did not select its exact manager repository'
[[ "$(rollback_manager_repo_for_sha "$SHA3")" = "$BUSINESS/candidate-3" ]] || \
    fail 'candidate-3 rollback/source routing regressed'
pass 'current candidate-4 -> explicit candidate-3 rollback SHA resolves exact repositories'

mkdir -p "$BUSINESS/releases/current5" "$BUSINESS/releases/rollback4"
printf '%s\n' "$SHA5" > "$BUSINESS/releases/current5/source.sha"
printf '%s\n' "$SHA4" > "$BUSINESS/releases/rollback4/source.sha"
rm "$STATE/current" "$STATE/rollback"
ln -s "$BUSINESS/releases/current5" "$STATE/current"
ln -s "$BUSINESS/releases/rollback4" "$STATE/rollback"
[[ "$(current_source_sha)" = "$SHA5" ]] || fail 'current pointer did not retain candidate-5 SHA'
[[ "$(rollback_source_sha)" = "$SHA4" ]] || fail 'rollback pointer did not retain explicit candidate-4 SHA'
[[ "$(rollback_manager_repo_for_sha "$SHA5")" = "$BUSINESS/candidate-5" ]] || \
    fail 'candidate-5 current SHA did not select its exact manager repository'
[[ "$(rollback_manager_repo_for_sha "$SHA4")" = "$BUSINESS/candidate-4" ]] || \
    fail 'candidate-4 rollback/source routing regressed'
pass 'current candidate-5 -> explicit candidate-4 rollback SHA resolves exact repositories'

UNKNOWN_SHA='0000000000000000000000000000000000000000'
if output="$(rollback_manager_repo_for_sha "$UNKNOWN_SHA" 2>&1)"; then
    fail 'unknown current SHA was accepted'
fi
[[ "$output" == *'does not match an explicitly staged candidate repository'* ]] || \
    fail 'unknown current SHA failed for an unexpected reason'

git clone -q "$BUSINESS/candidate-4" "$BUSINESS/candidate-2"
if output="$(rollback_manager_repo_for_sha "$SHA4" 2>&1)"; then
    fail 'duplicate current SHA was implicitly routed to one candidate'
fi
[[ "$output" == *'matches multiple candidate repositories'* ]] || \
    fail 'duplicate current SHA failed for an unexpected reason'
pass 'unknown and ambiguous current SHAs fail closed'
