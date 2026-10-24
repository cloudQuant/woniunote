#!/usr/bin/env bash
set -euo pipefail

release_dir="${1:?release directory is required}"
config_ref="$release_dir/runtime-config.ref"
config_hash_file="$release_dir/runtime-config.sha256"
[ -f "$config_ref" ] && [ -f "$config_hash_file" ] || {
    echo "release runtime config reference is missing" >&2
    exit 1
}
IFS= read -r config_path < "$config_ref"
IFS= read -r expected_hash < "$config_hash_file"
[ -f "$config_path" ] && [ ! -L "$config_path" ] && [[ "$expected_hash" =~ ^[0-9a-f]{64}$ ]] || {
    echo "release runtime config is unavailable" >&2
    exit 1
}
if stat -c '%a' "$config_path" >/dev/null 2>&1; then
    config_mode="$(stat -c '%a' "$config_path")"
else
    config_mode="$(stat -f '%Lp' "$config_path")"
fi
[ "$config_mode" = 600 ] || {
    echo "release runtime config permissions are not 0600" >&2
    exit 1
}
if command -v sha256sum >/dev/null 2>&1; then
    actual_hash="$(sha256sum "$config_path" | awk '{print $1}')"
else
    actual_hash="$(shasum -a 256 "$config_path" | awk '{print $1}')"
fi
[ "$actual_hash" = "$expected_hash" ] || {
    echo "release runtime config digest mismatch" >&2
    exit 1
}
exec "$release_dir/backend_cpp/build/woniunote_backend" "$config_path"
