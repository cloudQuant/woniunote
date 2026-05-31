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
- MySQL reachable (default `127.0.0.1:3306`)
- Redis reachable (default `127.0.0.1:6379`)
- Python deps: `pip install requests pymysql pytest`

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
for `/health`, runs pytest, then tears the server down.

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `WONIUNOTE_TEST_DB_HOST` | `127.0.0.1` | MySQL host |
| `WONIUNOTE_TEST_DB_PORT` | `3306` | MySQL port |
| `WONIUNOTE_TEST_DB_USER` | `root` | MySQL admin user (to create test DB) |
| `WONIUNOTE_TEST_DB_PASSWORD` | (empty) | MySQL password |
| `WONIUNOTE_TEST_DB_NAME` | `woniunote_test` | Test database name |
| `WONIUNOTE_TEST_REDIS_HOST` | `127.0.0.1` | Redis host |
| `WONIUNOTE_TEST_REDIS_PORT` | `6379` | Redis port |
| `WONIUNOTE_TEST_PORT` | `5273` | Backend test listen port |
| `WONIUNOTE_TEST_BASE_URL` | (unset) | If set, skip starting a server and test this URL |
