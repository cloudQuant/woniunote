#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BASE_IMAGE="${WONIUNOTE_LINUX_BASE_IMAGE:-woniunote.iter21/system-libs:ubuntu22.04}"
RUNTIME_IMAGE="${WONIUNOTE_LINUX_RUNTIME_IMAGE:-woniunote.iter21/backend-runtime:ubuntu22.04-iter21}"
RUNTIME_SPEC_SHA256="$(cat "$SCRIPT_DIR/Dockerfile" <(printf '\n--ENTRYPOINT--\n') \
  "$SCRIPT_DIR/container-entrypoint.sh" | shasum -a 256 | awk '{print $1}')"

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required." >&2; exit 2; }
command -v shasum >/dev/null 2>&1 || { echo "ERROR: shasum is required." >&2; exit 2; }
docker info >/dev/null 2>&1 || { echo "ERROR: Docker daemon unavailable." >&2; exit 2; }

base_metadata="$(docker image inspect --format \
  '{{.Id}}|{{index .Config.Labels "com.woniunote.iteration"}}|{{index .Config.Labels "com.woniunote.purpose"}}|{{index .Config.Labels "com.woniunote.builder"}}' \
  "$BASE_IMAGE" 2>/dev/null || true)"
IFS='|' read -r base_id base_iteration base_purpose base_builder <<<"$base_metadata"
if [[ ! "$base_id" =~ ^sha256:[0-9a-f]{64}$ || "$base_iteration" != 21 ||
      "$base_purpose" != linux-builder || "$base_builder" != system-libs ]]; then
  echo "ERROR: base image is not the labeled Iteration 21 system-libs builder image." >&2
  exit 2
fi

runtime_metadata="$(docker image inspect --format \
  '{{.Id}}|{{index .Config.Labels "com.woniunote.iteration"}}|{{index .Config.Labels "com.woniunote.purpose"}}|{{index .Config.Labels "com.woniunote.runtime.base-image"}}|{{index .Config.Labels "com.woniunote.runtime.base-image-id"}}|{{index .Config.Labels "com.woniunote.runtime.spec-sha256"}}' \
  "$RUNTIME_IMAGE" 2>/dev/null || true)"
if [[ -n "$runtime_metadata" ]]; then
  IFS='|' read -r runtime_id runtime_iteration runtime_purpose runtime_base runtime_base_id runtime_spec <<<"$runtime_metadata"
  if [[ ! "$runtime_id" =~ ^sha256:[0-9a-f]{64}$ || "$runtime_iteration" != 21 ||
        "$runtime_purpose" != backend-runtime || "$runtime_base" != "$BASE_IMAGE" ||
        "$runtime_base_id" != "$base_id" || "$runtime_spec" != "$RUNTIME_SPEC_SHA256" ]]; then
    echo "ERROR: refusing to reuse or overwrite an unrelated runtime image tag." >&2
    exit 2
  fi
  echo "Validated existing runtime image ID: $runtime_id"
  exit 0
fi

docker build --pull=false \
  --build-arg "SYSTEM_LIBS_IMAGE=$BASE_IMAGE" \
  --build-arg "SYSTEM_LIBS_IMAGE_ID=$base_id" \
  --build-arg "RUNTIME_SPEC_SHA256=$RUNTIME_SPEC_SHA256" \
  --tag "$RUNTIME_IMAGE" \
  "$SCRIPT_DIR"

runtime_metadata="$(docker image inspect --format \
  '{{.Id}}|{{index .Config.Labels "com.woniunote.iteration"}}|{{index .Config.Labels "com.woniunote.purpose"}}|{{index .Config.Labels "com.woniunote.runtime.base-image"}}|{{index .Config.Labels "com.woniunote.runtime.base-image-id"}}|{{index .Config.Labels "com.woniunote.runtime.spec-sha256"}}' \
  "$RUNTIME_IMAGE" 2>/dev/null || true)"
IFS='|' read -r runtime_id runtime_iteration runtime_purpose runtime_base runtime_base_id runtime_spec <<<"$runtime_metadata"
if [[ ! "$runtime_id" =~ ^sha256:[0-9a-f]{64}$ || "$runtime_iteration" != 21 ||
      "$runtime_purpose" != backend-runtime || "$runtime_base" != "$BASE_IMAGE" ||
      "$runtime_base_id" != "$base_id" || "$runtime_spec" != "$RUNTIME_SPEC_SHA256" ]]; then
  echo "ERROR: built runtime image did not retain the expected ownership metadata." >&2
  exit 2
fi
echo "Built runtime image ID: $runtime_id"
