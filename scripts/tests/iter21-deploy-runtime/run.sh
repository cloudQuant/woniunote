#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EVIDENCE_ROOT=/tmp/woniunote-iter21-evidence/deploy-runtime
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$-$RANDOM"
RUN_DIR="$EVIDENCE_ROOT/$RUN_ID"
RUNTIME_TAG="woniunote.iter21/deploy-runtime:$RUN_ID"
BASE_IMAGE=woniunote.iter21/system-libs:ubuntu22.04
BASE_ID=""
IMAGE_ID=""
CONTAINER_IDS=""
CREATED_CID=""
ACTIVE_CID=""
SYSTEMD_MODE=unknown
RUN_INPUT="$RUN_DIR/input"

mkdir -p "$RUN_DIR"
chmod 0700 "$EVIDENCE_ROOT" "$RUN_DIR"
exec > >(tee -a "$RUN_DIR/run.log") 2>&1
mkdir -m 0700 "$RUN_INPUT"
cp "$REPO_ROOT/scripts/deploy_release.sh" "$RUN_INPUT/deploy_release.sh"
cp "$REPO_ROOT/scripts/release_run_backend.sh" "$RUN_INPUT/release_run_backend.sh"
cp "$REPO_ROOT/configs/woniunote_nginx_prod.conf" "$RUN_INPUT/woniunote_nginx_prod.conf"
chmod 0600 "$RUN_INPUT"/*

record() {
    printf '%s\n' "$*" | tee -a "$RUN_DIR/manifest.txt"
}

cleanup() {
    local cid
    set +e
    for cid in $CONTAINER_IDS; do
        if docker container inspect "$cid" >/dev/null 2>&1; then
            if docker container rm -f "$cid"; then record "container_cleanup[$cid]=removed"; else record "container_cleanup[$cid]=FAILED"; fi
        else
            record "container_cleanup[$cid]=already-absent"
        fi
    done
    if [ -n "$IMAGE_ID" ]; then
        if docker image rm "$IMAGE_ID"; then record "image_cleanup[$IMAGE_ID]=removed"; else record "image_cleanup[$IMAGE_ID]=FAILED"; fi
    fi
    record "cleanup=done"
}
trap cleanup EXIT

record "run_id=$RUN_ID"
record "repo_root=$REPO_ROOT"
record "docker=$(docker version --format '{{.Client.Version}}/{{.Server.Version}}')"
record "platform=$(docker info --format '{{.OSType}}/{{.Architecture}} cgroup={{.CgroupVersion}}')"
BASE_ID="$(docker image inspect "$BASE_IMAGE" --format '{{.Id}}')"
record "base_image=$BASE_IMAGE"
record "base_image_id=$BASE_ID"
if docker image inspect "$RUNTIME_TAG" >/dev/null 2>&1; then
    printf 'Refusing to replace pre-existing runtime tag %s\n' "$RUNTIME_TAG" >&2
    exit 2
fi

record "nginx_template_sha256=$(shasum -a 256 "$RUN_INPUT/woniunote_nginx_prod.conf" | awk '{print $1}')"
record "deploy_script_sha256=$(shasum -a 256 "$RUN_INPUT/deploy_release.sh" | awk '{print $1}')"
record "release_launcher_sha256=$(shasum -a 256 "$RUN_INPUT/release_run_backend.sh" | awk '{print $1}')"
record 'image_build_cpu_limit=unavailable in this Docker buildx CLI; apt package-only build, no dependency compilation; runtime=2 CPUs'

docker build --pull=false \
    --build-arg "BASE_IMAGE=$BASE_IMAGE" \
    --build-arg "RUN_ID=$RUN_ID" \
    --tag "$RUNTIME_TAG" \
    "$SCRIPT_DIR"
IMAGE_ID="$(docker image inspect "$RUNTIME_TAG" --format '{{.Id}}')"
record "runtime_image=$RUNTIME_TAG"
record "runtime_image_id=$IMAGE_ID"
docker image inspect "$IMAGE_ID" --format '{{json .Config.Labels}}' | tee -a "$RUN_DIR/manifest.txt"

create_container() {
    local service="$1" cid name
    name="iter21-${RUN_ID}-${service}"
    if [ "$service" = nginx-adapter ]; then
        cid="$(docker create --name "$name" \
            --label "org.woniunote.iter21.run-id=$RUN_ID" \
            --label "org.woniunote.iter21.service=$service" \
            --cpus=2 --network none --cgroupns=private --cap-add SYS_ADMIN \
            --tmpfs /run:rw,nosuid,nodev,size=16m,mode=0755 \
            --tmpfs /run/lock:rw,nosuid,nodev,size=4m,mode=0755 \
            --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 \
            --tmpfs /var/lib/woniunote-iter21-state:rw,exec,nosuid,nodev,size=64m,mode=0755 \
            --entrypoint /bin/bash "$IMAGE_ID" -lc 'exec sleep infinity')"
    else
        cid="$(docker create --name "$name" \
            --label "org.woniunote.iter21.run-id=$RUN_ID" \
            --label "org.woniunote.iter21.service=$service" \
            --cpus=2 --network none --cgroupns=private --cap-add SYS_ADMIN \
            --tmpfs /run:rw,nosuid,nodev,size=16m,mode=0755 \
            --tmpfs /run/lock:rw,nosuid,nodev,size=4m,mode=0755 \
            --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 \
            --tmpfs /var/lib/woniunote-iter21-state:rw,exec,nosuid,nodev,size=64m,mode=0755 \
            "$IMAGE_ID")"
    fi
    CONTAINER_IDS="$CONTAINER_IDS $cid"
    CREATED_CID="$cid"
    record "container_id[$service]=$cid"
    docker container inspect "$cid" --format '{{json .Config.Labels}}' | tee -a "$RUN_DIR/manifest.txt"
    docker container inspect "$cid" --format '{{range .Mounts}}{{println .Type .Destination}}{{end}}' | tee -a "$RUN_DIR/mounts-$service.txt"
    if rg -q '^bind[[:space:]]' "$RUN_DIR/mounts-$service.txt"; then
        printf 'A host bind mount was detected; refusing to continue\n' >&2
        exit 3
    fi
}

create_container systemd-nginx-deploy
PRIMARY_CID="$CREATED_CID"
docker start "$PRIMARY_CID"
sleep 2
if [ "$(docker inspect --format '{{.State.Running}}' "$PRIMARY_CID" 2>/dev/null || true)" = true ] && \
   docker exec "$PRIMARY_CID" /bin/bash -lc \
     'test "$(cat /proc/1/comm)" = systemd || exit 1; for attempt in $(seq 1 15); do state="$(timeout 10s /usr/bin/systemctl is-system-running 2>&1 || true)"; { test "$state" = running || test "$state" = degraded; } && exit 0; sleep 1; done; exit 1'; then
    SYSTEMD_MODE=real
    ACTIVE_CID="$PRIMARY_CID"
    record 'systemd_mode=real (systemd PID 1 and systemctl manager responsive; no host mounts)'
else
    SYSTEMD_MODE=adapter
    record 'systemd_mode=adapter (systemd could not be verified under private cgroup/no-host-mount constraints)'
    docker container inspect "$PRIMARY_CID" --format '{{json .State}}' | tee -a "$RUN_DIR/systemd-container.log" || true
    docker logs "$PRIMARY_CID" >> "$RUN_DIR/systemd-container.log" 2>&1 || true
    docker container rm -f "$PRIMARY_CID" >/dev/null 2>&1 || true
    create_container nginx-adapter
    ACTIVE_CID="$CREATED_CID"
    docker start "$ACTIVE_CID"
fi

record "nginx_package=$(docker exec "$ACTIVE_CID" dpkg-query -W -f='${Version}' nginx)"
docker cp "$RUN_INPUT/deploy_release.sh" "$ACTIVE_CID:/opt/woniunote-iter21-runtime/input/deploy_release.sh"
docker cp "$RUN_INPUT/release_run_backend.sh" "$ACTIVE_CID:/opt/woniunote-iter21-runtime/input/release_run_backend.sh"
docker cp "$RUN_INPUT/woniunote_nginx_prod.conf" "$ACTIVE_CID:/opt/woniunote-iter21-runtime/input/woniunote_nginx_prod.conf"

set +e
docker exec "$ACTIVE_CID" /bin/bash /opt/woniunote-iter21-runtime/run_runtime.sh "$SYSTEMD_MODE" "$RUN_ID"
RUNTIME_RC=$?
set -e
record "runtime_probe_exit=$RUNTIME_RC"
mkdir -p "$RUN_DIR/container-evidence"
chmod 0700 "$RUN_DIR/container-evidence"
docker cp "$ACTIVE_CID:/var/lib/woniunote-iter21-data/evidence/." "$RUN_DIR/container-evidence/" 2>/dev/null || true
docker cp "$ACTIVE_CID:/var/lib/woniunote-iter21-data/fixture-repo/fixture-meta.txt" "$RUN_DIR/fixture-meta.txt" 2>/dev/null || true

if [ "$RUNTIME_RC" -ne 0 ]; then
    record 'result=FAIL'
    exit "$RUNTIME_RC"
fi
record "result=PASS (isolated fixture only; D04 business compatibility=NOT_RUN; systemd_mode=$SYSTEMD_MODE)"
