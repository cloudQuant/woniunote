#!/usr/bin/env bash
set -Eeuo pipefail

FIXTURE="${1:?fixture repo path required}"
STATE="${2:?state path required}"
DATA="${3:?data path required}"
INPUT="${4:?input path required}"

rm -rf "$FIXTURE"
mkdir -p "$FIXTURE/frontend/scripts" \
         "$FIXTURE/backend_cpp/resource" \
         "$FIXTURE/configs" \
         "$FIXTURE/scripts"
cp "$INPUT/deploy_release.sh" "$FIXTURE/scripts/deploy_release.sh"
cp "$INPUT/release_run_backend.sh" "$FIXTURE/scripts/release_run_backend.sh"
cp "$INPUT/woniunote_nginx_prod.conf" "$FIXTURE/configs/woniunote_nginx_prod.conf"
chmod 0755 "$FIXTURE/scripts/deploy_release.sh" "$FIXTURE/scripts/release_run_backend.sh"

cat > "$FIXTURE/frontend/package.json" <<'EOF'
{"name":"woniunote-iter21-runtime-fixture","private":true,"version":"1.0.0","scripts":{"build":"fixture-only"}}
EOF
cat > "$FIXTURE/frontend/package-lock.json" <<'EOF'
{"name":"woniunote-iter21-runtime-fixture","version":"1.0.0","lockfileVersion":3,"requires":true,"packages":{}}
EOF
cat > "$FIXTURE/frontend/scripts/check-node-version.mjs" <<'EOF'
// Fixture only. The PATH shim reports the required build version; node - ...
// delegates index parsing to the real Node.js installed in the runtime image.
EOF
cat > "$FIXTURE/backend_cpp/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.16)
project(woniunote_iter21_runtime_fixture LANGUAGES CXX)
EOF
printf 'synthetic resource fixture\n' > "$FIXTURE/backend_cpp/resource/fixture.txt"
printf '{"fixture_data_dir":"%s"}\n' "$DATA" > "$DATA/runtime-config.json"
chmod 0600 "$DATA/runtime-config.json"
printf 'iter21 persistent upload fixture\000\001\002\n' > "$DATA/uploads/smoke.bin"

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.name 'WoniuNote Iter21 Runtime Fixture'
git -C "$FIXTURE" config user.email 'iter21-runtime-fixture@example.invalid'
printf 'v1\n' > "$FIXTURE/frontend/fixture-version.txt"
printf 'v1\n' > "$FIXTURE/backend_cpp/fixture-version.txt"
git -C "$FIXTURE" add .
git -C "$FIXTURE" commit -q -m 'fixture v1'
printf 'v1=%s\n' "$(git -C "$FIXTURE" rev-parse HEAD)" > "$DATA/fixture-meta.txt"

for version in v2 v3 v4; do
    printf '%s\n' "$version" > "$FIXTURE/frontend/fixture-version.txt"
    printf '%s\n' "$version" > "$FIXTURE/backend_cpp/fixture-version.txt"
    git -C "$FIXTURE" add frontend/fixture-version.txt backend_cpp/fixture-version.txt
    git -C "$FIXTURE" commit -q -m "fixture $version"
    printf '%s=%s\n' "$version" "$(git -C "$FIXTURE" rev-parse HEAD)" >> "$DATA/fixture-meta.txt"
done

chmod 0600 "$DATA/fixture-meta.txt"
printf 'fixture_repository=%s\n' "$FIXTURE" >> "$DATA/fixture-meta.txt"
printf 'fixture_state_path=%s\n' "$STATE" >> "$DATA/fixture-meta.txt"
