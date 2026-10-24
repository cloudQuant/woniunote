# Iteration 21 real-backend integration suite

This harness starts the compiled Drogon backend against a fresh MySQL container
and a fresh Redis container for every invocation. It imports the repository SQL
schema into a run-specific database, writes a run-specific JSON config, and
binds all services to loopback on dynamically selected ports. MySQL and Redis
ports are selected and checked before container creation, explicitly published
on those ports, and read back to verify the mapping. MySQL uses a uniquely named,
run-labeled data volume so stop/start keeps the schema; Redis uses a disposable
`/data` tmpfs. Tests call the real HTTP API and inspect only the test-owned
database and Redis instances.
There is no external target mode, mock business API, localStorage login seed, or
reuse of an unknown backend process.

The run-owned MySQL server disables TLS only so the byte-level transport-fault
proxy can observe COMMIT and its acknowledgement. The runner checks
`@@GLOBAL.have_ssl` is `DISABLED` before schema setup and records that readback
in the private manifest. This setting applies only to the disposable test
container; it does not change product configuration or formal-runtime TLS.
Because the vcpkg MariaDB Connector/C build requires verified TLS by default,
the runner also sets `MARIADB_TLS_DISABLE_PEER_VERIFICATION=1` only for the
owned backend and test subprocess tree. With the server readback proving TLS is
disabled and the database endpoint bound to this run's loopback port, this lets
the client fall back to plaintext for that disposable test service. It is never
set for a user shell, an external endpoint, or a formal runtime.

## Build and run

The C++ binary used by the HTTP suite must be a test-only build because both
the real captcha cache hook and auth transaction probe are compiled out of
normal artifacts. Configure the backend with:

```bash
cmake -S backend_cpp -B backend_cpp/build \
  -DBUILD_TESTING=ON \
  -DWONIUNOTE_ENABLE_TEST_CHALLENGE=ON \
  -DWONIUNOTE_ENABLE_TEST_AUTH_FAULTS=ON
cmake --build backend_cpp/build -j8
```

Python dependencies in the selected environment are `pytest`, `requests`,
`pymysql`, and `redis`. On this workstation, the runner selects Anaconda base
through `conda run -n base python` automatically. Docker Desktop must be
running; a pre-existing host MySQL, Redis, or backend is not used.

Run the main correctness scenario, which configures a high but active rate
limit so the 100-user and business cases do not consume the limiter's separate
acceptance budget:

```bash
bash backend_cpp/tests/integration/run_integration.sh
```

The default scenario uses a separate fresh DB/Redis pair and the product
default of 60 requests/minute to verify a real HTTP 429 and `Retry-After`:

```bash
WONIUNOTE_TEST_SCENARIO=rate-limit \
  bash backend_cpp/tests/integration/run_integration.sh
```

The functional scenario also runs the math answer-column migration checks
against scratch schemas inside its verified run-owned MySQL container, then
runs the comment-vote migration's pure Python unit suite and its live migration
checks against uniquely named scratch schemas in the same label-verified,
run-owned MySQL container. The separate rate-limit scenario remains focused
on the real Redis-backed HTTP limiter.

For the real Chromium UI flow, install the lockfile-exact frontend packages
and Chromium, then run the functional scenario with Node 22.13.0 on `PATH`:

```bash
cd frontend
npm ci
npx playwright install chromium
cd ..
WONIUNOTE_TEST_REAL_E2E=1 \
  bash backend_cpp/tests/integration/run_integration.sh
```

The real Chromium suite exercises both the standalone login page and the
header modal with ordinary and email-style usernames, carries a protected-page
redirect through registration, and verifies real refresh/logout responses.
For browser captcha input it observes the challenge ID from the UI's real
`GET /api/captcha/generate` request, then uses the guarded test-only route to
peek at that existing cache entry. The route does not consume the challenge;
login still validates and consumes it through the production path. API tests
also use the hook's expired-challenge mode. The hook requires the run-specific
header and a loopback peer and is absent from ordinary builds.

## Isolation and retained evidence

The runner refuses externally supplied backend, DB, or Redis targets and
refuses standard/development ports. It writes unique config, uploads, logs, and
reports under a mode-700 per-run directory. Config files and uploads are
removed during cleanup; normal successful runs retain only a redacted manifest,
sanitized test names/statuses, migration outcome summaries, content-free
transport counters, allowlisted Linux backend runtime metadata, and a backend
log metadata index under
`/tmp/woniunote-iter21/results/<run-id>` (or the directory selected by
`WONIUNOTE_TEST_ARTIFACT_ROOT`). Raw JUnit details, Playwright HTML reports,
screenshots, traces, service logs, and backend logs are not copied to this
summary directory. Failed runs clean up only containers and the MySQL volume
whose exact run-id and service labels match this invocation; the manifest
records the MySQL volume name, driver, labels, and cleanup status. The runner
does not prune or guess at other Docker resources. Raw logs and browser
diagnostics remain inside the mode-700 runtime directory.
For upload-path parity with the application, `document_root` is
`<RUN_DIR>/uploads` and `upload_path` is its `uploads` child; both remain inside
the run-owned uploads tree that cleanup removes. Logs and generated config stay
outside that static document root.
Native backend processes run from the private `<RUN_DIR>/backend-runtime`
directory, so UEditor’s legacy `../uploads` probe resolves to this run’s
`<RUN_DIR>/uploads`. The Linux container launcher must use the same workdir
while binding `<RUN_DIR>` at the same path to preserve that isolation.
Linux backend metadata preserves only the instance, run ID, full backend
container ID, backend binary SHA-256, runtime/base image names and image IDs,
runtime-spec SHA-256, HTTP port, and `credentials_included: false`. The runner
validates these fields against the run and copies only that allowlist; it never
copies backend config or logs into the sanitized artifact directory.

Set `WONIUNOTE_TEST_KEEP_SERVICES=1` to keep a successful run's owned backend
and Docker services alive for the main thread's subsequent formal-binary
verification. The private run directory also retains `config.integration.json`
with mode 600 so that the formal binary can reuse the exact isolated DB/Redis
configuration. It is not copied to the sanitized artifact directory. The
manifest contains the run ID, dynamic loopback ports, container IDs, backend
PID, and scenario but no credentials. This retention only reports completion
of the requested runner phases; it does not count as a pass for later
formal-binary checks. After verification, stop the retained backend and remove
only the exact run-labeled containers and MySQL volume, verifying their names,
IDs, and labels first. Do not point tools at these ports after cleanup.

The harness accepts `WONIUNOTE_BACKEND_BIN` to select a different built
executable and `WONIUNOTE_TEST_ARTIFACT_ROOT` for a private evidence location.
It does not accept user-provided DB/Redis/backend URLs, skip-setup switches, or
port overrides that collide with 5173, 8888, 3306, or 6379.
