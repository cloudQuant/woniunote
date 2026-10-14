# Backend integration tests (HTTP black-box)

These tests exercise the **real** C++ Drogon backend over HTTP against a
**dedicated test database** (`woniunote_test`) and a live Redis. They cover the
parts pure unit tests cannot reach: routing, filters (auth + rate limit),
the unified response envelope with correct HTTP status codes, and DB writes.

They never touch the production/dev database — the runner creates and seeds an
isolated `woniunote_test` schema and points the backend at it via a generated
`config.integration.json`.

## What is covered

- `GET /health` liveness
- Missing / malformed / non-bearer `Authorization` → 401 (AuthFilter)
- `GET /api/auth/me` without token → 401
- Register a fresh user → 200 with `{code,message,data}` envelope
- Register a duplicate username → 400 (and HTTP 400, not 200)
- Response envelope shape + HTTP status alignment
- Rate limiting → 429 once the per-minute limit is exceeded (needs Redis)

Login is not asserted end-to-end because it requires a server-generated
captcha (random, in-memory) that a black-box client cannot solve. Registration
+ auth-filter paths give us the meaningful DB + filter coverage instead.

## Prerequisites

- The backend built at `backend_cpp/build/woniunote_backend`
  (override with `WONIUNOTE_BACKEND_BIN`)
- MySQL reachable (default `127.0.0.1:3306`)
- Redis reachable **and answering PING** (default `127.0.0.1:6379`); the
  preflight speaks the Redis protocol, not just TCP
- Python deps: `pip install requests pytest`
- A Python interpreter with those deps: `WONIUNOTE_TEST_PYTHON` selects it
  (default `python3`; on this machine use
  `/Users/yunjinqi/opt/anaconda3/bin/conda run -n base python`). The same
  interpreter is used for the runner's own helpers and for pytest unless
  `PYTEST_CMD` overrides the latter.

## Isolation guard

The suite writes rows and hammers the rate limiter, so the runner refuses to
start unless the target looks like a test environment:

- `WONIUNOTE_TEST_DB_NAME` must match a test-schema pattern
  (`*_test`, `test_*`, …); pointing it at `woniunote` / a production name
  aborts before anything is created or modified.
- `WONIUNOTE_TEST_PORT` must not be the development backend port (5173).

## Run

```bash
# From repo root. Override DB creds via env as needed.
export WONIUNOTE_TEST_DB_HOST=127.0.0.1
export WONIUNOTE_TEST_DB_PORT=3306
export WONIUNOTE_TEST_DB_USER=root
export WONIUNOTE_TEST_DB_PASSWORD=yourpassword

bash backend_cpp/tests/integration/run_integration.sh
```

The runner: creates+seeds `woniunote_test`, writes `config.integration.json`,
starts the backend on a test port with a strong `WONIUNOTE_JWT_SECRET`, waits
for `/health`, runs pytest, then tears the server down (also on Ctrl-C/failure;
the per-run server log is named with the runner's PID).

### Strict mode (release / CI acceptance)

```bash
WONIUNOTE_TEST_STRICT=1 bash backend_cpp/tests/integration/run_integration.sh
```

In strict mode the rate-limit case **must** observe a real `429` with a
`Retry-After` header; if it cannot (Redis down, limiter disabled), the run
fails instead of skipping. Without strict mode it skips, which is only
acceptable for local debugging — a skipped rate-limit case is not release
evidence.

### External instance mode

```bash
WONIUNOTE_TEST_BASE_URL=http://127.0.0.1:5273 bash backend_cpp/tests/integration/run_integration.sh
```

When `WONIUNOTE_TEST_BASE_URL` is set the runner does **not** create/seed the
schema and does **not** start or stop a backend: it runs pytest against that
URL. The caller owns the instance, its schema and its lifecycle.

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `WONIUNOTE_TEST_DB_HOST` | `127.0.0.1` | MySQL host |
| `WONIUNOTE_TEST_DB_PORT` | `3306` | MySQL port |
| `WONIUNOTE_TEST_DB_USER` | `root` | MySQL admin user (to create test DB) |
| `WONIUNOTE_TEST_DB_PASSWORD` | (empty) | MySQL password |
| `WONIUNOTE_TEST_DB_NAME` | `woniunote_test` | Test database name (must look like a test schema) |
| `WONIUNOTE_TEST_REDIS_HOST` | `127.0.0.1` | Redis host |
| `WONIUNOTE_TEST_REDIS_PORT` | `6379` | Redis port |
| `WONIUNOTE_TEST_PORT` | `5273` | Backend test listen port |
| `WONIUNOTE_TEST_RATE_LIMIT` | `60` | Per-minute limit the suite expects |
| `WONIUNOTE_TEST_STRICT` | `0` | `1` = no skips; missing 429 fails the run |
| `WONIUNOTE_TEST_BASE_URL` | (unset) | If set, skip DB setup/server start and test this URL |
| `WONIUNOTE_TEST_SKIP_DB_SETUP` | `0` | `1` = reuse an existing prepared schema |
| `WONIUNOTE_TEST_SKIP_RATELIMIT` | `0` | `1` = disable the rate-limit case (local debug only) |
| `WONIUNOTE_TEST_PYTHON` | `python3` | Interpreter for the runner's helpers |
| `WONIUNOTE_BACKEND_BIN` | `backend_cpp/build/woniunote_backend` | Backend binary under test |
| `PYTEST_CMD` | `$WONIUNOTE_TEST_PYTHON -m pytest` | Full pytest invocation (may contain args) |
