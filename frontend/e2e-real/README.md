# Real Chromium business E2E

`business.real.spec.js` supplements `auth.real.spec.js` with database-backed UI
flows for Iteration 21 AC21-18. The tests use the isolated runner's disposable
MySQL, Redis, backend, upload directory, and Chromium preview server. They do
not import the mock API helpers or intercept application requests.

The first scenario registers one unique user through the browser, signs in at
the standalone page, creates a draft with a real PNG upload, checks its private
read through an authenticated GET and its 404 through a new anonymous browser
context, then signs in through the header modal and publishes the same draft.
The anonymous context confirms the published body is nonempty and matches the
saved content. It then reads persisted comments over HTTP after a UI comment,
checks the committed vote count after a UI vote, and signs out through the UI.
The upload assertion checks the same-origin root-relative
`/uploads/uploads/images/YYYY/MM/<timestamp>_<four-digit-random>.png` contract,
including the calendar month and returned filename. It then retrieves the
uploaded bytes from the backend and checks the HTTP status, image MIME type,
and exact PNG bytes. The article response must retain the uploaded filename as
its thumbnail.
The flow does not claim that `/api/thumb/<filename>` serves those same upload
bytes: the current thumbnail JSON contract reduces the upload URL to a
basename, while the thumbnail endpoint reads its static thumbnail directory
and can return its fallback image. Exact public-card image mapping remains an
uncovered product check.

The second scenario registers a separate user, logs in through the standalone
page, skips one displayed arithmetic question, solves the next question from
its visible operands, and ends the session through the UI. It verifies the
saved record count and summary, then reads the record detail and checks that
the skipped answer persisted as JSON `null`.

Both scenarios wait for the real UI write response before an independent HTTP
GET checks the persisted result. Unknown or missing write responses fail the
test; no write request is retried. The real Playwright config sets retries to
zero and stores first-run traces, screenshots, and reports in the isolated
runner's mode-700 evidence directory. Those raw artifacts can contain login
credentials or tokens and must stay in that private directory.

Run from the repository root with the isolated test-challenge backend build,
Node 22.13.0 on `PATH`, installed frontend dependencies, and Chromium:

```bash
WONIUNOTE_TEST_REAL_E2E=1 \
  WONIUNOTE_BACKEND_BIN="$PWD/backend_cpp/build-iter21-http/woniunote_backend" \
  bash backend_cpp/tests/integration/run_integration.sh
```

The runner supplies `WONIUNOTE_REAL_E2E`, `WONIUNOTE_TEST_RUN_ID`,
`WONIUNOTE_API_PROXY_TARGET`, `WONIUNOTE_REAL_E2E_URL`, and
`WONIUNOTE_TEST_EVIDENCE_DIR` for each owned run. Do not invoke the suite
against a shared, development, production, or externally supplied backend.
