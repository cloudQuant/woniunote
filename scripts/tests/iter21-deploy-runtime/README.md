# Iteration 21 isolated deploy runtime

This harness runs the checked-in Nginx template and deploy entry point in an
Ubuntu 22.04 container derived from `woniunote.iter21/system-libs:ubuntu22.04`.
The Docker build context is only this directory. Nginx comes from the image's
official Ubuntu apt sources. Runtime containers have no host bind mounts, no
published ports, no network, a 2 CPU limit, and a bounded tmpfs for deploy
state. The runner captures Docker image/container IDs and removes only those
IDs when it exits.

Run it from any directory with:

```bash
bash scripts/tests/iter21-deploy-runtime/run.sh
```

Host evidence is written with mode 0700 under
`/tmp/woniunote-iter21-evidence/deploy-runtime/<run-id>/`. The run log records
the source image ID, derived image ID, container IDs and labels, Nginx package
version, test results, and cleanup result. No host Python is used. Python
inside the Linux container is invoked as `/usr/bin/python3`.

The fixture repository is a temporary Git repository inside the container with
three committed frontend versions. `node`, `npm`, and `cmake` are explicit
fixture shims so the test exercises deployment state transitions without
rebuilding the application or claiming a real application build. Its backend
is a small Python HTTP fixture used only for health, read-only API, thumbnail,
upload, and injected 404/500 responses. The compatibility records exist only
to exercise the deploy script's record validator; they are labeled
`FIXTURE_ONLY`, and D04 business/API/session/schema compatibility remains
`NOT_RUN`.

The runner first tries systemd as PID 1 using a private cgroup namespace and
`CAP_SYS_ADMIN`, without a host mount or privileged mode. If systemd cannot run
under those constraints, the harness recreates its own labeled container and
uses a clearly named systemctl adapter for the deploy script. Nginx remains the
real Ubuntu package in either mode. The final report must preserve the adapter
limitation and must not describe it as systemd evidence.

The runtime probe checks actual Nginx cache headers, MIME, conditional 304,
missing-resource 404, upstream 500, API/upload proxy precedence, multiple
version entry switches and hash-asset retention, a real tmpfs ENOSPC event,
recovery after freeing space, and SIGKILL after a real Nginx reload but before
candidate service start, followed by the deploy script's journaled recovery
path. These are isolated fixture
results, not production deployment or D04 acceptance.
