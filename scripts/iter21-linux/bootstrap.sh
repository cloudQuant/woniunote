#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel)"
BASELINE="e7b524242c8a5d718a7afa26794c3c19bb8b0c71"
SYSTEM_IMAGE="woniunote.iter21/system-libs:ubuntu22.04"
VCPKG_IMAGE="woniunote.iter21/vcpkg:ubuntu22.04"
DEFAULT_CACHE_ROOT="${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/woniunote-iter21"
DEFAULT_SNAPSHOT_ROOT="$DEFAULT_CACHE_ROOT/snapshots"
DEFAULT_OUTPUT_ROOT="$DEFAULT_CACHE_ROOT/builds"
SOURCE_MANIFEST_NAME="iter21-source-manifest.json"

host_conda="/Users/yunjinqi/opt/anaconda3/bin/conda"
if [[ ! -x "$host_conda" ]]; then
    host_conda="$(command -v conda || true)"
fi

host_python() {
    [[ -n "$host_conda" ]] || fail "Anaconda conda is required for source snapshot hashing"
    "$host_conda" run -n base python "$@"
}

usage() {
    cat <<'EOF'
Usage:
  bootstrap.sh images
  bootstrap.sh snapshot [--repo PATH] [--ref COMMIT] [--snapshot-root PATH]
  bootstrap.sh digest --snapshot PATH [--manifest PATH]
  bootstrap.sh prepare --builder system-libs|vcpkg --snapshot PATH [--snapshot-sha256 SHA256]
                       [--variant release|test] [--cmake-define NAME=VALUE ...]
                       [--vcpkg-installed-dir PATH]
                       [--output PATH] [--jobs N] [--cpus N]
  bootstrap.sh build   --builder system-libs|vcpkg --snapshot PATH [--snapshot-sha256 SHA256]
                       [--variant release|test] [--cmake-define NAME=VALUE ...]
                       [--vcpkg-installed-dir PATH]
                       [--output PATH] [--jobs N] [--cpus N]

"snapshot" exports only tracked files from a Git commit. It excludes secrets,
config.local files/directories, build output directories, and common generated
directories. "prepare" configures CMake (and installs the manifest dependencies
for the vcpkg builder); "build" compiles in the same output directory. A direct
snapshot directory requires an explicit digest from the "digest" command.
EOF
}

fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 2
}

source_tree_digest() {
    local source="$1"
    local manifest_path="${2:-}"
    local expected_sha="${3:-}"
    local -a args=(--root "$source")

    if [[ -n "$manifest_path" ]]; then
        args+=(--manifest "$manifest_path")
    fi
    if [[ -n "$expected_sha" ]]; then
        args+=(--expected "$expected_sha")
    fi
    host_python "$SCRIPT_DIR/snapshot_manifest.py" "${args[@]}"
}

require_cache_boolean() {
    local cache_file="$1"
    local name="$2"
    local expected="$3"

    grep -Fqx "$name:BOOL=$expected" "$cache_file" || \
        fail "prepared CMake cache does not match $name=$expected; run prepare with the same variant"
}

assert_owned_image_tag() {
    local image="$1"
    local iteration
    local purpose
    local builder
    local expected_builder

    if ! docker image inspect "$image" >/dev/null 2>&1; then
        return
    fi

    iteration="$(docker image inspect --format '{{ index .Config.Labels "com.woniunote.iteration" }}' "$image")"
    purpose="$(docker image inspect --format '{{ index .Config.Labels "com.woniunote.purpose" }}' "$image")"
    builder="$(docker image inspect --format '{{ index .Config.Labels "com.woniunote.builder" }}' "$image")"
    case "$image" in
        "$SYSTEM_IMAGE") expected_builder="system-libs" ;;
        "$VCPKG_IMAGE") expected_builder="vcpkg" ;;
        *) fail "refusing to update an image outside the Iteration 21 builder tags: $image" ;;
    esac
    if [[ "$iteration" != "21" || "$purpose" != "linux-builder" || "$builder" != "$expected_builder" ]]; then
        fail "refusing to replace an image that is not the owned Iteration 21 $expected_builder builder: $image"
    fi
}

build_images() {
    command -v docker >/dev/null 2>&1 || fail "docker is required"
    docker info >/dev/null 2>&1 || fail "Docker daemon is not available"
    assert_owned_image_tag "$SYSTEM_IMAGE"
    assert_owned_image_tag "$VCPKG_IMAGE"

    printf 'Building system-libs builder: %s\n' "$SYSTEM_IMAGE"
    docker build --progress=plain \
        --file "$SCRIPT_DIR/Dockerfile" \
        --target system-libs \
        --tag "$SYSTEM_IMAGE" \
        --build-arg "VCPKG_BASELINE=$BASELINE" \
        "$SCRIPT_DIR"

    printf 'Building vcpkg builder: %s\n' "$VCPKG_IMAGE"
    docker build --progress=plain \
        --file "$SCRIPT_DIR/Dockerfile" \
        --target vcpkg \
        --tag "$VCPKG_IMAGE" \
        --build-arg "VCPKG_BASELINE=$BASELINE" \
        "$SCRIPT_DIR"
}

path_is_excluded() {
    local path="$1"
    local component
    local basename
    local components=()
    local i

    IFS='/' read -r -a components <<< "$path"
    basename="${components[${#components[@]}-1]}"

    for ((i = 0; i < ${#components[@]} - 1; i++)); do
        component="${components[$i]}"
        case "$component" in
            .git|.env|.env.*|build|build-*|build_*|build.*|node_modules|dist|coverage|__pycache__|secret|secrets|.venv|venv|config.local|config.local.*)
                return 0
                ;;
        esac
    done

    case "$basename" in
        .env|.env.*|secret|secrets|config.local|config.local.*|*.local)
            return 0
            ;;
    esac

    return 1
}

make_snapshot() {
    local repo="$REPO_ROOT"
    local ref=HEAD
    local snapshot_root="$DEFAULT_SNAPSHOT_ROOT"
    local commit
    local short_commit
    local snapshot_dir
    local temporary_dir
    local snapshot_sha
    local recorded_sha
    local path
    local -a pathspecs=()

    while (($#)); do
        case "$1" in
            --repo)
                (($# >= 2)) || fail "--repo requires a path"
                repo="$2"
                shift 2
                ;;
            --ref)
                (($# >= 2)) || fail "--ref requires a Git commit or ref"
                ref="$2"
                shift 2
                ;;
            --snapshot-root)
                (($# >= 2)) || fail "--snapshot-root requires a path"
                snapshot_root="$2"
                shift 2
                ;;
            -h|--help)
                usage
                return
                ;;
            *)
                fail "unknown snapshot option: $1"
                ;;
        esac
    done

    [[ -d "$repo" ]] || fail "Git repository directory does not exist: $repo"
    repo="$(cd "$repo" && pwd -P)"
    git -C "$repo" rev-parse --show-toplevel >/dev/null 2>&1 || fail "--repo must be inside a Git repository"
    commit="$(git -C "$repo" rev-parse --verify "${ref}^{commit}")"
    short_commit="${commit:0:12}"

    mkdir -p "$snapshot_root"
    snapshot_root="$(cd "$snapshot_root" && pwd -P)"
    snapshot_dir="$snapshot_root/$commit"

    if [[ -e "$snapshot_dir" ]]; then
        [[ -f "$snapshot_dir/.woniunote-iter21-source" ]] || fail "snapshot path exists without a valid marker: $snapshot_dir"
        grep -Fxq "commit=$commit" "$snapshot_dir/.woniunote-iter21-source" || fail "snapshot marker does not match requested commit: $snapshot_dir"
        recorded_sha="$(sed -n 's/^snapshot_sha256=//p' "$snapshot_dir/.woniunote-iter21-source" | head -1)"
        snapshot_sha="$(source_tree_digest "$snapshot_dir")" || fail "failed to hash existing snapshot: $snapshot_dir"
        if [[ -n "$recorded_sha" && "$recorded_sha" != "$snapshot_sha" ]]; then
            fail "snapshot contents no longer match the marker digest: $snapshot_dir"
        fi
        if [[ -z "$recorded_sha" ]]; then
            printf 'snapshot_sha256=%s\n' "$snapshot_sha" >> "$snapshot_dir/.woniunote-iter21-source"
        fi
        printf '%s\n' "$snapshot_dir"
        return
    fi

    while IFS= read -r -d '' path; do
        if ! path_is_excluded "$path"; then
            pathspecs+=(":(literal)$path")
        fi
    done < <(git -C "$repo" ls-tree -r --name-only -z --full-tree "$commit")

    ((${#pathspecs[@]} > 0)) || fail "no tracked source files remain after snapshot exclusions"
    temporary_dir="$(mktemp -d "$snapshot_root/.iter21-snapshot.XXXXXXXX")"
    if ! git -C "$repo" archive --format=tar "$commit" -- "${pathspecs[@]}" | tar -xf - -C "$temporary_dir"; then
        rm -rf "$temporary_dir"
        fail "failed to export source snapshot for $commit"
    fi

    snapshot_sha="$(source_tree_digest "$temporary_dir")" || {
        rm -rf "$temporary_dir"
        fail "failed to hash exported source snapshot for $commit"
    }
    printf 'commit=%s\nsnapshot_sha256=%s\nsource_repo=%s\n' \
        "$commit" "$snapshot_sha" "$repo" > "$temporary_dir/.woniunote-iter21-source"
    if ! mv "$temporary_dir" "$snapshot_dir"; then
        rm -rf "$temporary_dir"
        fail "failed to place source snapshot at $snapshot_dir"
    fi

    printf 'Created frozen source snapshot %s (%s, sha256 %s); excluded secret/config.local/build/generated paths.\n' \
        "$snapshot_dir" "$short_commit" "$snapshot_sha" >&2
    printf '%s\n' "$snapshot_dir"
}

resolve_builder_image() {
    case "$1" in
        system-libs) printf '%s\n' "$SYSTEM_IMAGE" ;;
        vcpkg) printf '%s\n' "$VCPKG_IMAGE" ;;
        *) fail "builder must be system-libs or vcpkg" ;;
    esac
}

make_digest() {
    local snapshot=""
    local manifest_path=""

    while (($#)); do
        case "$1" in
            --snapshot)
                (($# >= 2)) || fail "--snapshot requires a directory"
                snapshot="$2"
                shift 2
                ;;
            --manifest)
                (($# >= 2)) || fail "--manifest requires an output path"
                manifest_path="$2"
                shift 2
                ;;
            -h|--help)
                usage
                return
                ;;
            *)
                fail "unknown digest option: $1"
                ;;
        esac
    done

    [[ -d "$snapshot" ]] || fail "snapshot directory does not exist: $snapshot"
    snapshot="$(cd "$snapshot" && pwd -P)"
    [[ -f "$snapshot/backend_cpp/CMakeLists.txt" ]] || fail "snapshot does not contain backend_cpp/CMakeLists.txt"
    if [[ -z "$manifest_path" ]]; then
        mkdir -p "$DEFAULT_CACHE_ROOT/manifests"
        manifest_path="$DEFAULT_CACHE_ROOT/manifests/$(basename "$snapshot").json"
    fi
    mkdir -p "$(dirname "$manifest_path")"
    manifest_path="$(cd "$(dirname "$manifest_path")" && pwd -P)/$(basename "$manifest_path")"
    local snapshot_sha
    snapshot_sha="$(source_tree_digest "$snapshot" "$manifest_path")" || fail "failed to hash snapshot"
    printf 'snapshot_sha256=%s\nmanifest=%s\n' "$snapshot_sha" "$manifest_path"
}

run_builder_action() {
    local action="$1"
    shift

    local builder=""
    local snapshot=""
    local snapshot_sha_arg=""
    local output=""
    local jobs="2"
    local cpus="2"
    local variant="release"
    local vcpkg_installed_arg=""
    local image
    local commit
    local recorded_sha=""
    local snapshot_sha
    local source_key
    local source_manifest
    local build_manifest
    local prepare_manifest
    local image_id
    local final_snapshot_sha
    local uid
    local gid
    local vcpkg_installed_dir=""
    local vcpkg_installed_mount=""
    local manifest_install_off=false
    local -a cmake_definitions=()
    local -a cmake_options=()
    local -a docker_args=()
    local -a action_args=()

    while (($#)); do
        case "$1" in
            --builder)
                (($# >= 2)) || fail "--builder requires system-libs or vcpkg"
                builder="$2"
                shift 2
                ;;
            --snapshot)
                (($# >= 2)) || fail "--snapshot requires a source snapshot path"
                snapshot="$2"
                shift 2
                ;;
            --snapshot-sha256)
                (($# >= 2)) || fail "--snapshot-sha256 requires a SHA-256 digest"
                snapshot_sha_arg="$2"
                shift 2
                ;;
            --variant)
                (($# >= 2)) || fail "--variant requires release or test"
                variant="$2"
                shift 2
                ;;
            --test-variant)
                variant="test"
                shift
                ;;
            --cmake-define)
                (($# >= 2)) || fail "--cmake-define requires NAME=VALUE"
                [[ "$2" == *=* ]] || fail "--cmake-define requires NAME=VALUE"
                [[ "${2%%=*}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || fail "invalid CMake definition name: ${2%%=*}"
                [[ -n "${2#*=}" ]] || fail "CMake definition value must not be empty"
                case "${2%%=*}" in
                    BUILD_TESTING|CMAKE_BUILD_TYPE|CMAKE_CXX_STANDARD|USE_SYSTEM_LIBS|WONIUNOTE_ENABLE_TEST_CHALLENGE|WONIUNOTE_ENABLE_TEST_AUTH_FAULTS)
                        fail "${2%%=*} is controlled by the builder variant and cannot be overridden"
                        ;;
                esac
                if [[ "$2" == "VCPKG_MANIFEST_INSTALL=OFF" ]]; then
                    manifest_install_off=true
                fi
                cmake_definitions+=("$2")
                shift 2
                ;;
            --vcpkg-installed-dir)
                (($# >= 2)) || fail "--vcpkg-installed-dir requires a prepared installed directory"
                vcpkg_installed_arg="$2"
                shift 2
                ;;
            --output)
                (($# >= 2)) || fail "--output requires a directory"
                output="$2"
                shift 2
                ;;
            --jobs)
                (($# >= 2)) || fail "--jobs requires a positive integer"
                jobs="$2"
                shift 2
                ;;
            --cpus)
                (($# >= 2)) || fail "--cpus requires a positive Docker CPU limit"
                cpus="$2"
                shift 2
                ;;
            -h|--help)
                usage
                return
                ;;
            *)
                fail "unknown $action option: $1"
                ;;
        esac
    done

    [[ -n "$builder" ]] || fail "--builder is required"
    [[ -n "$snapshot" ]] || fail "--snapshot is required"
    [[ "$variant" == "release" || "$variant" == "test" ]] || fail "--variant must be release or test"
    [[ "$jobs" =~ ^[1-9][0-9]*$ ]] || fail "--jobs must be a positive integer"
    [[ "$cpus" =~ ^[1-9][0-9]*(\.[0-9]+)?$ ]] || fail "--cpus must be a positive number"
    [[ -d "$snapshot" ]] || fail "source snapshot directory does not exist: $snapshot"
    snapshot="$(cd "$snapshot" && pwd -P)"
    [[ "$snapshot" != "$REPO_ROOT" ]] || fail "the mutable repository root cannot be used as a frozen snapshot"
    [[ -f "$snapshot/backend_cpp/CMakeLists.txt" ]] || fail "snapshot does not contain backend_cpp/CMakeLists.txt"
    [[ "$snapshot" != *,* ]] || fail "Docker bind-mount paths cannot contain commas: $snapshot"

    commit=""
    if [[ -f "$snapshot/.woniunote-iter21-source" ]]; then
        commit="$(sed -n 's/^commit=//p' "$snapshot/.woniunote-iter21-source" | head -1)"
        recorded_sha="$(sed -n 's/^snapshot_sha256=//p' "$snapshot/.woniunote-iter21-source" | head -1)"
        if [[ -n "$commit" && ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
            fail "source snapshot marker has an invalid commit SHA"
        fi
    elif [[ -z "$snapshot_sha_arg" ]]; then
        fail "direct snapshot directories require --snapshot-sha256 from the digest command"
    fi
    if [[ -n "$snapshot_sha_arg" && ! "$snapshot_sha_arg" =~ ^[0-9a-fA-F]{64}$ ]]; then
        fail "--snapshot-sha256 must contain 64 hexadecimal characters"
    fi
    if [[ -n "$recorded_sha" && ! "$recorded_sha" =~ ^[0-9a-fA-F]{64}$ ]]; then
        fail "source snapshot marker has an invalid snapshot_sha256"
    fi
    if [[ -z "$snapshot_sha_arg" && -z "$recorded_sha" ]]; then
        fail "snapshot has no recorded digest; pass --snapshot-sha256 from the digest command"
    fi

    image="$(resolve_builder_image "$builder")"
    docker image inspect "$image" >/dev/null 2>&1 || fail "builder image is missing; run '$0 images' first: $image"
    assert_owned_image_tag "$image"

    if [[ -z "$snapshot_sha_arg" ]]; then
        snapshot_sha_arg="$recorded_sha"
    fi
    snapshot_sha="$(source_tree_digest "$snapshot" "" "$snapshot_sha_arg")" || fail "snapshot digest verification failed"
    source_key="sha256-$snapshot_sha"

    if [[ -z "$output" ]]; then
        output="$DEFAULT_OUTPUT_ROOT/$source_key/$builder/$variant"
    fi
    mkdir -p "$output"
    output="$(cd "$output" && pwd -P)"
    [[ "$output" != "$snapshot" && "$output" != "$snapshot"/* ]] || fail "output directory must be outside the read-only source snapshot"
    [[ "$snapshot" != "$output" && "$snapshot" != "$output"/* ]] || fail "snapshot must be outside the build output directory"
    [[ "$output" != *,* ]] || fail "Docker bind-mount paths cannot contain commas: $output"
    source_manifest="$output/$SOURCE_MANIFEST_NAME"
    snapshot_sha="$(source_tree_digest "$snapshot" "$source_manifest" "$snapshot_sha")" || fail "snapshot digest verification failed"

    if [[ "$builder" == "vcpkg" ]]; then
        if [[ -n "$vcpkg_installed_arg" ]]; then
            [[ -d "$vcpkg_installed_arg" ]] || fail "vcpkg installed directory does not exist: $vcpkg_installed_arg"
            vcpkg_installed_dir="$(cd "$vcpkg_installed_arg" && pwd -P)"
            [[ "$vcpkg_installed_dir" != *,* ]] || fail "Docker bind-mount paths cannot contain commas: $vcpkg_installed_dir"
            [[ "$vcpkg_installed_dir" != "$snapshot" && "$vcpkg_installed_dir" != "$snapshot"/* ]] || fail "vcpkg installed directory must be outside the source snapshot"
            [[ "$vcpkg_installed_dir" != "$output" && "$vcpkg_installed_dir" != "$output"/* ]] || fail "shared vcpkg installed directory must be outside the current output directory"
            vcpkg_installed_mount="/workspace/shared-vcpkg-installed"
        else
            vcpkg_installed_dir="$output/vcpkg_installed"
            vcpkg_installed_mount="/workspace/output/vcpkg_installed"
        fi
    elif [[ -n "$vcpkg_installed_arg" ]]; then
        fail "--vcpkg-installed-dir is only valid for the vcpkg builder"
    fi

    uid="$(id -u)"
    gid="$(id -g)"
    image_id="$(docker image inspect --format '{{.Id}}' "$image")"
    docker_args=(run --rm --init --cpus "$cpus" --user "$uid:$gid"
        --label com.woniunote.iteration=21
        --label "com.woniunote.builder=$builder"
        --label "com.woniunote.snapshot-sha256=$snapshot_sha"
        --mount "type=bind,source=$snapshot,target=/workspace/source,readonly"
        --mount "type=bind,source=$output,target=/workspace/output"
    )

    if [[ "$action" == "prepare" ]]; then
        if [[ "$builder" == "system-libs" ]]; then
            cmake_options=(-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DUSE_SYSTEM_LIBS=ON -DBUILD_TESTING=ON)
        else
            mkdir -p "$output/vcpkg_buildtrees" "$output/vcpkg_downloads" "$output/vcpkg_packages"
            if [[ -z "$vcpkg_installed_arg" ]]; then
                mkdir -p "$output/vcpkg_installed"
            elif [[ "$manifest_install_off" != true ]]; then
                fail "a shared --vcpkg-installed-dir requires --cmake-define VCPKG_MANIFEST_INSTALL=OFF"
            fi
            cmake_options=(-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DUSE_SYSTEM_LIBS=OFF -DBUILD_TESTING=ON -DCMAKE_TOOLCHAIN_FILE=/opt/vcpkg/scripts/buildsystems/vcpkg.cmake -DVCPKG_MANIFEST_DIR=/workspace/source/backend_cpp "-DVCPKG_INSTALLED_DIR=$vcpkg_installed_mount" "-DVCPKG_INSTALL_OPTIONS=--x-buildtrees-root=/workspace/output/vcpkg_buildtrees;--x-packages-root=/workspace/output/vcpkg_packages;--downloads-root=/workspace/output/vcpkg_downloads")
        fi
        if [[ "$variant" == "test" ]]; then
            cmake_options+=(-DWONIUNOTE_ENABLE_TEST_CHALLENGE=ON -DWONIUNOTE_ENABLE_TEST_AUTH_FAULTS=ON)
        else
            cmake_options+=(-DWONIUNOTE_ENABLE_TEST_CHALLENGE=OFF -DWONIUNOTE_ENABLE_TEST_AUTH_FAULTS=OFF)
        fi
        for definition in "${cmake_definitions[@]-}"; do
            [[ -n "$definition" ]] || continue
            cmake_options+=("-D$definition")
        done
        action_args=(cmake -S /workspace/source/backend_cpp -B /workspace/output/cmake-build -G Ninja "${cmake_options[@]}")
        if [[ "$builder" == "vcpkg" ]]; then
            docker_args+=(--env VCPKG_ROOT=/opt/vcpkg --env VCPKG_DISABLE_METRICS=1
                --env "VCPKG_MAX_CONCURRENCY=$jobs"
                --env VCPKG_BUILDTREES_DIR=/workspace/output/vcpkg_buildtrees
                --env VCPKG_DOWNLOADS=/workspace/output/vcpkg_downloads
                --env VCPKG_PACKAGES_DIR=/workspace/output/vcpkg_packages)
            if [[ -n "$vcpkg_installed_arg" ]]; then
                docker_args+=(--mount "type=bind,source=$vcpkg_installed_dir,target=$vcpkg_installed_mount,readonly")
            fi
        fi
    else
        local cache_file="$output/cmake-build/CMakeCache.txt"
        [[ -f "$cache_file" ]] || fail "CMake was not prepared in $output; run the matching prepare command first"
        prepare_manifest="$output/iter21-$variant-prepare-manifest.json"
        [[ -f "$prepare_manifest" ]] || fail "prepare manifest is missing from $output; run prepare with the matching snapshot, builder, and variant first"
        require_cache_boolean "$cache_file" BUILD_TESTING ON
        if [[ "$variant" == "test" ]]; then
            require_cache_boolean "$cache_file" WONIUNOTE_ENABLE_TEST_CHALLENGE ON
            require_cache_boolean "$cache_file" WONIUNOTE_ENABLE_TEST_AUTH_FAULTS ON
        else
            require_cache_boolean "$cache_file" WONIUNOTE_ENABLE_TEST_CHALLENGE OFF
            require_cache_boolean "$cache_file" WONIUNOTE_ENABLE_TEST_AUTH_FAULTS OFF
        fi
        if [[ "$builder" == "system-libs" ]]; then
            require_cache_boolean "$cache_file" USE_SYSTEM_LIBS ON
        else
            require_cache_boolean "$cache_file" USE_SYSTEM_LIBS OFF
        fi
        if [[ "$builder" == "vcpkg" ]]; then
            [[ -d "$vcpkg_installed_arg" || -z "$vcpkg_installed_arg" ]] || fail "vcpkg installed directory does not exist: $vcpkg_installed_arg"
            if [[ -n "$vcpkg_installed_arg" ]]; then
                vcpkg_installed_dir="$(cd "$vcpkg_installed_arg" && pwd -P)"
                [[ "$vcpkg_installed_dir" != *,* ]] || fail "Docker bind-mount paths cannot contain commas: $vcpkg_installed_dir"
                [[ "$vcpkg_installed_dir" != "$snapshot" && "$vcpkg_installed_dir" != "$snapshot"/* ]] || fail "vcpkg installed directory must be outside the source snapshot"
                [[ "$vcpkg_installed_dir" != "$output" && "$vcpkg_installed_dir" != "$output"/* ]] || fail "shared vcpkg installed directory must be outside the current output directory"
                grep -Fqx 'VCPKG_INSTALLED_DIR:PATH=/workspace/shared-vcpkg-installed' "$cache_file" || \
                    fail "CMake cache was not prepared with the supplied shared vcpkg installed directory"
                vcpkg_installed_mount="/workspace/shared-vcpkg-installed"
                docker_args+=(--mount "type=bind,source=$vcpkg_installed_dir,target=$vcpkg_installed_mount,readonly")
            elif grep -Fqx 'VCPKG_INSTALLED_DIR:PATH=/workspace/shared-vcpkg-installed' "$cache_file"; then
                fail "prepared CMake cache uses a shared vcpkg directory; pass the same --vcpkg-installed-dir to build"
            else
                grep -Fqx 'VCPKG_INSTALLED_DIR:PATH=/workspace/output/vcpkg_installed' "$cache_file" || \
                    fail "prepared CMake cache does not use the output-local vcpkg installed directory"
                vcpkg_installed_dir="$output/vcpkg_installed"
            fi
            docker_args+=(--env VCPKG_ROOT=/opt/vcpkg --env VCPKG_DISABLE_METRICS=1
                --env "VCPKG_MAX_CONCURRENCY=$jobs"
                --env VCPKG_BUILDTREES_DIR=/workspace/output/vcpkg_buildtrees
                --env VCPKG_DOWNLOADS=/workspace/output/vcpkg_downloads
                --env VCPKG_PACKAGES_DIR=/workspace/output/vcpkg_packages)
        fi
        local -a verify_args=(
            --manifest "$prepare_manifest" --builder "$builder" --variant "$variant"
            --snapshot-sha256 "$snapshot_sha" --image-id "$image_id"
        )
        if [[ -n "$vcpkg_installed_dir" ]]; then
            verify_args+=(--vcpkg-installed-dir "$vcpkg_installed_dir")
        fi
        for definition in "${cmake_definitions[@]-}"; do
            [[ -n "$definition" ]] || continue
            verify_args+=(--cmake-definition "$definition")
        done
        host_python "$SCRIPT_DIR/verify_prepare_manifest.py" "${verify_args[@]}" || \
            fail "prepare manifest does not match this build; prepare the same snapshot, builder image, variant, and CMake definitions first"
        action_args=(cmake --build /workspace/output/cmake-build --config Release --parallel "$jobs")
    fi

    if [[ -n "$commit" ]]; then
        docker_args+=(--label "com.woniunote.source-commit=$commit")
    fi
    docker_args+=(--workdir /workspace/source/backend_cpp "$image")

    printf '%s builder %s (%s variant) for snapshot sha256 %s\n' "$action" "$builder" "$variant" "$snapshot_sha"
    printf 'Snapshot mount: %s (read-only)\nOutput mount: %s\n' "$snapshot" "$output"
    docker "${docker_args[@]}" "${action_args[@]}"
    final_snapshot_sha="$(source_tree_digest "$snapshot")" || fail "failed to re-check source snapshot after $action"
    [[ "$final_snapshot_sha" == "$snapshot_sha" ]] || fail "source snapshot changed while $action was running"

    build_manifest="$output/iter21-$variant-$action-manifest.json"
    local -a manifest_args=(
        --output "$build_manifest" --action "$action" --builder "$builder" --variant "$variant"
        --snapshot-dir "$snapshot" --snapshot-sha256 "$snapshot_sha"
        --source-manifest "$source_manifest" --image "$image" --image-id "$image_id"
        --output-dir "$output" --jobs "$jobs" --cpus "$cpus"
    )
    if [[ "$action" == "build" ]]; then
        manifest_args+=(--prepare-manifest "$prepare_manifest")
    fi
    if [[ -n "$commit" ]]; then
        manifest_args+=(--source-commit "$commit")
    fi
    if [[ -n "$vcpkg_installed_dir" ]]; then
        manifest_args+=(--vcpkg-installed-dir "$vcpkg_installed_dir")
    fi
    for definition in "${cmake_definitions[@]-}"; do
        [[ -n "$definition" ]] || continue
        manifest_args+=(--cmake-definition "$definition")
    done
    for option in "${cmake_options[@]-}"; do
        [[ -n "$option" ]] || continue
        manifest_args+=("--cmake-option=$option")
    done
    for option in "${action_args[@]}"; do
        manifest_args+=("--cmake-option=$option")
    done
    host_python "$SCRIPT_DIR/build_manifest.py" "${manifest_args[@]}"
    printf 'Manifest: %s\n' "$build_manifest"
}

main() {
    (($#)) || {
        usage
        exit 2
    }

    local command="$1"
    shift

    case "$command" in
        images)
            (($# == 0)) || fail "images takes no options"
            build_images
            ;;
        snapshot)
            make_snapshot "$@"
            ;;
        digest)
            make_digest "$@"
            ;;
        prepare|build)
            run_builder_action "$command" "$@"
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            usage >&2
            fail "unknown command: $command"
            ;;
    esac
}

main "$@"
