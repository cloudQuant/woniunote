# Iteration 21 Linux builders

This directory defines two Ubuntu 22.04 C++17 builder images for a committed,
read-only WoniuNote source snapshot. The Docker build context contains only this
directory, so the repository, local credentials, and generated build files are
not sent to the Docker daemon while the images are built.

## Builder paths

| Builder | Dependency source | Pinned framework versions |
| --- | --- | --- |
| `system-libs` | Ubuntu 22.04 apt snapshot and upstream source archives | Drogon 1.9.8, Trantor 1.5.21, jwt-cpp 0.7.0; matches the values in `scripts/setup_ubuntu.sh` |
| `vcpkg` | vcpkg at baseline `e7b524242c8a5d718a7afa26794c3c19bb8b0c71`, plus `backend_cpp/vcpkg-overlay-ports` from the source snapshot | The manifest overlay currently selects Drogon 1.9.11 at that baseline; this path intentionally preserves the repository's vcpkg contract |

The image pins the Ubuntu 22.04 base image digest, Ubuntu apt snapshot timestamp,
vcpkg checkout, and SHA-256 of the three system-builder source archives. System
and application compilation default to two jobs and two Docker CPUs. To move
the apt package set, change `UBUNTU_APT_SNAPSHOT` in `Dockerfile` deliberately.
The apt snapshot is immutable and the expired metadata check is disabled only
for that historical snapshot. The base image has no CA bundle, so peer checking
is disabled only while bootstrapping `ca-certificates`; apt still verifies signed
repository metadata and package hashes. Normal HTTPS verification is enabled
after the CA bundle is installed.

## Build a frozen source snapshot

The snapshot command exports a Git commit, not the live working tree. It omits
uncommitted and untracked changes and excludes `.git`, secret directories,
`.env*`, `config.local*`, build output directories, `node_modules`, `dist`,
coverage output, and Python cache directories. Commit the intended source state
first, then pass its commit SHA explicitly:

```bash
SNAPSHOT="$(scripts/iter21-linux/bootstrap.sh snapshot --repo "$PWD" --ref <commit-sha>)"
```

Without `--snapshot-root`, the snapshot is stored outside the repository under
`${XDG_CACHE_HOME:-$HOME/.cache}/woniunote-iter21/snapshots/<full-commit-sha>`. Its marker records
the source commit. The build commands require this marker and mount the snapshot
read-only at `/workspace/source`.

For a separately prepared, non-Git frozen directory, compute its canonical tree
digest before building. The digest is SHA-256 over JSONL entries sorted by
relative path; regular files record mode and content SHA-256, while symlinks
record their target and are rejected if they resolve outside the snapshot. The
source marker and output manifest are not part of the digest. The scanner rejects
secret, `.env*`, `config.local*`, `.git`, and build/generated directories.

```bash
scripts/iter21-linux/bootstrap.sh digest \
  --snapshot /path/to/frozen-snapshot \
  --manifest /path/outside/snapshot/iter21-source-manifest.json
```

Pass the printed digest to both builder actions. A direct directory without a
script-created marker always requires `--snapshot-sha256`; the mutable repository
root is rejected.

## Build or reuse the images

```bash
scripts/iter21-linux/bootstrap.sh images
```

This creates or updates only these owned tags:

```text
woniunote.iter21/system-libs:ubuntu22.04
woniunote.iter21/vcpkg:ubuntu22.04
```

Both images carry `com.woniunote.iteration=21`,
`com.woniunote.purpose=linux-builder`, and a builder-kind label. The command
refuses to replace a pre-existing image at either tag unless all three labels
match that exact owned builder. It uses the locally cached base image when
available and does not remove or prune other Docker resources.

## Prepare and compile

`prepare` configures CMake. In the vcpkg path this also resolves and builds the
manifest dependencies into the output directory; it does not compile the
WoniuNote application. `build` compiles the already configured source. Both use
the same snapshot and output path, keep generated files outside the snapshot,
and leave the source mount read-only. The default `release` variant sets
`BUILD_TESTING=ON` with the test-only challenge and auth-fault hooks disabled.
Use `--variant test` (or `--test-variant`) to enable both
`WONIUNOTE_ENABLE_TEST_CHALLENGE` and `WONIUNOTE_ENABLE_TEST_AUTH_FAULTS`.
Repeat the same `--cmake-define NAME=VALUE` flags on both actions. `build`
requires the matching prepare manifest and checks the source digest, builder
image ID, variant, shared vcpkg install path, and definitions before compiling.

```bash
scripts/iter21-linux/bootstrap.sh prepare \
  --builder system-libs --snapshot "$SNAPSHOT" --variant release --jobs 2 --cpus 2
scripts/iter21-linux/bootstrap.sh build \
  --builder system-libs --snapshot "$SNAPSHOT" --variant release --jobs 2 --cpus 2

scripts/iter21-linux/bootstrap.sh prepare \
  --builder vcpkg --snapshot "$SNAPSHOT" --variant test --jobs 2 --cpus 2
scripts/iter21-linux/bootstrap.sh build \
  --builder vcpkg --snapshot "$SNAPSHOT" --variant test --jobs 2 --cpus 2
```

For an external frozen tree, add `--snapshot-sha256 <64-hex-digest>` to each
command. To reuse a completed vcpkg installation read-only while configuring a
different frozen source, pass `--vcpkg-installed-dir PATH` to `prepare` and
`build`, and add `--cmake-define VCPKG_MANIFEST_INSTALL=OFF` to `prepare`. Do not
run concurrent prepares against the same installed directory.

By default, output and vcpkg downloads/build trees are stored outside the
repository under `${XDG_CACHE_HOME:-$HOME/.cache}/woniunote-iter21/builds/<source-id>/<builder>/<variant>`.
Use `--output PATH` to choose another persistent output directory. Container
runs are removed on exit, and no named volumes are created.

Each successful action writes `iter21-<variant>-<action>-manifest.json` and
`iter21-source-manifest.json` in the output directory. They record the snapshot
digest, builder image ID, variant, CMake definitions, and resource limits; they
are build provenance only, not acceptance evidence.

To run a build without relying on the current working tree, use the same
snapshot and output directory for both `prepare` and `build`. A different
snapshot SHA gets an independent default output directory.
