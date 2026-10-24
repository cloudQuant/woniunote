# Iteration 21 Linux backend runtime

This directory provides a host-side launcher for a prebuilt Linux Iteration 21
backend. It keeps the Linux process inside a run-owned container while exposing
only the test HTTP port on host loopback. The app itself still listens on
`127.0.0.1` inside the container; a small `socat` forwarder binds the container's
single global IPv4 address on `eth0` and forwards to that loopback listener.

Build the derived runtime image from the locally prepared system-libs builder
image:

```sh
WONIUNOTE_LINUX_RUNTIME_IMAGE=woniunote.iter21/backend-runtime:ubuntu22.04-iter21 \
  scripts/tests/iter21-linux-runtime/build-runtime-image.sh
```

The runner invokes the executable as `launcher <config_path>`. Its environment
must provide `WONIUNOTE_LINUX_BACKEND_BINARY` (the already-built Linux binary)
and `WONIUNOTE_LINUX_RUNTIME_IMAGE`, plus the Iteration 21 run ID, runtime,
loopback DB and Redis endpoints, and credentials exported by the isolated test
harness. `WONIUNOTE_LINUX_BASE_IMAGE` may select another locally labeled
`iteration=21`, `purpose=linux-builder`, `builder=system-libs` image; the
default is `woniunote.iter21/system-libs:ubuntu22.04`.

The launcher accepts only the run's primary
`config.integration.json` or the transport test's
`fault-proxy-runtime/config/config.json`. For the latter it verifies that both
DB and Redis proxy ports have one IPv4-loopback listener owned by the active
pytest process ancestry. The secondary HTTP port must differ from the primary
port. Both service containers are resolved by this run's exact ownership
labels and checked against their loopback published ports before launch.

Each instance gets a private Linux config under
`$RUN_DIR/linux-runtime/<instance>/config/`. Its MySQL and Redis hosts change
to `host.docker.internal`; its `document_root`, `upload_path`, and `log_path`
are resolved to canonical paths inside the same run-owned directory. Other
config fields keep the test runner's values. The same run directory is mounted
at the same absolute path inside the container so uploads and logs remain in
the run-owned tree.

The harness creates `$RUN_DIR/backend-runtime` with mode `0700` and uses it as
the native test backend's working directory. Before starting the Linux
container, the launcher requires that exact canonical child directory to exist
as a private, non-symlink directory and sets it as the container working
directory. With the run directory mounted at the same path, relative
`../uploads` resolution stays at `$RUN_DIR/uploads`; the absolute config paths
remain unchanged.

Docker Desktop's built-in `host.docker.internal` name is used on the default
bridge without a manual host-gateway mapping. Repeated transport-fixture
launches use distinct `secondary-<12 hex>` instance directories, evidence names,
container names, and ownership labels; each attempt's evidence is retained.

For the isolated test backend only, the launcher requires the harness's
`WN_I21_MYSQL_TLS_STATUS=DISABLED` readback and passes
`MARIADB_TLS_DISABLE_PEER_VERIFICATION=1` into the backend container. The
harness sets that status only after checking TLS is disabled on this run's
owned disposable MySQL container; this does not change application config or
apply to production services.

The launcher records redacted image and binary identity metadata in the run's
`evidence` directory. Container labels include the run ID, `service=backend`,
and instance name. It tolerates a briefly empty or partially written Docker
cidfile within a bounded startup window and can recover the exact named
container only after checking its full ID and ownership labels. The cidfile is
retained while the container runs for the outer harness's exact-ID,
label-checked interruption cleanup. Normal shutdown uses a bounded
`docker stop`; no host MySQL/Redis endpoint is accepted.
