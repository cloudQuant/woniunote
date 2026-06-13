---
title: 'Iteration 14 Repo Governance and Quality Signals'
type: 'chore'
created: '2026-06-13'
status: 'done'
baseline_commit: 'c9330aba0525b5d3cc9cca7c810e9adcd08995ff'
context:
  - '{project-root}/_bmad-output/planning-artifacts/迭代14-仓库治理与质量信号收口方案.md'
  - '{project-root}/CLAUDE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Iteration 14 identified that the active C++/Vue project still has repo-tracked secrets, legacy CI and test assets, noisy frontend quality gates, weak local integration-test ergonomics, and stale docs that describe obsolete backend paths.

**Approach:** Implement the whole iteration as one governance hardening pass: remove sensitive/generated artifacts from version tracking, collapse CI around the active Drogon/Vue stack, reduce lint/audit/test noise, improve local integration-test preflight, and update root documentation to match the current architecture.

## Boundaries & Constraints

**Always:** Keep the active stack as C++ Drogon backend plus Vue 3 frontend. Preserve local secret/certificate files when removing them from Git tracking. Keep existing passing behavior intact. Run practical acceptance tests after edits.

**Ask First:** Rewriting Git history, rotating real production certificates, changing live infrastructure credentials, deleting local-only secret files from disk, or removing legacy Python assets beyond safe repo/CI/documentation scoping.

**Never:** Push to remote, touch production systems, expose secret values in logs/docs, or reintroduce Flask/FastAPI as the current backend path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sensitive files tracked | Git tracks certificates/private keys/backups | Files are removed from Git tracking and ignored while remaining locally available | History rewrite and real rotation are documented as manual follow-up |
| Legacy CI present | Old workflows reference Python Flask/PostgreSQL paths | Automatic CI focuses on active C++/Vue jobs | Legacy workflow content is removed or disabled, not silently mixed with active gates |
| Local integration deps missing | MySQL/Redis credentials absent or invalid | Script exits early with actionable env var guidance | No real database is modified accidentally |
| Frontend warnings/audit | Lint warnings, PostCSS advisory, noisy test output | CI lint warning budget tightens, audit passes, expected logs are suppressed | If upstream advisory cannot be fixed safely, document residual risk |

</frozen-after-approval>

## Code Map

- `.gitignore` -- repo hygiene rules for secrets, backups, generated data, and active tooling artifacts.
- `.github/workflows/cpp-vue-ci.yml` -- active CI gate for C++ backend, Vue frontend, E2E, and integration tests.
- `.github/workflows/ci.yml` / `.github/workflows/ci-cd.yml` -- legacy Flask-era workflow files to disable/remove.
- `frontend/package*.json`, `frontend/src/**`, `frontend/e2e/**`, `frontend/playwright.config.js` -- frontend lint/audit/test cleanup.
- `backend_cpp/tests/integration/run_integration.sh` -- local integration-test preflight and credential guidance.
- `README.md`, `CLAUDE.md`, `REFACTORING_GUIDE.md`, `tests/README.md` -- current-architecture documentation.

## Tasks & Acceptance

**Execution:**
- [x] `.gitignore` and tracked artifacts -- remove sensitive/generated files from Git tracking and extend ignore rules.
- [x] `.github/workflows/*` -- collapse automatic CI around the active C++/Vue workflow and remove legacy Flask CI confusion.
- [x] `frontend/` -- fix lint warnings, PostCSS audit, Vitest warning noise, and Playwright webServer reproducibility.
- [x] `backend_cpp/tests/integration/run_integration.sh` -- improve local preflight and safe defaults for MySQL/Redis credentials.
- [x] Documentation -- update root/test/refactoring docs to reflect current C++/Vue stack and legacy boundaries.
- [x] Verification -- run lint, frontend coverage, build, E2E, CTest, cppcheck, audit, and integration-script preflight checks.

**Acceptance Criteria:**
- Given the repository is scanned for tracked secrets, when `git ls-files '*.key' '*.pem' '*.crt' '*.csr'` is run, then no real certificate/private-key files are tracked.
- Given CI workflows are inspected, when old workflow files are opened, then they no longer define automatic Flask/PostgreSQL jobs.
- Given the frontend gate runs, when `npm run lint:ci` and `npm audit --omit=dev --audit-level=moderate` run, then both pass.
- Given E2E is run locally, when `npm run test:e2e` starts its own web server, then the Chromium suite passes without manual preview setup.
- Given integration preconditions are missing, when the backend integration script starts, then it fails early with explicit environment-variable guidance.

## Spec Change Log

## Design Notes

This is intentionally a governance pass, not a feature pass. The highest-risk item is secret handling: the code change can remove files from tracking, but safety also requires real-world key rotation if those files ever left the machine.

## Verification

**Commands:**
- `git status --short` -- expected: only intentional iteration 14 changes.
- `git ls-files '*.key' '*.pem' '*.crt' '*.csr'` -- expected: no tracked real cert/key files.
- `npm run lint:ci` in `frontend/` -- expected: 0 warnings/errors.
- `npm audit --omit=dev --audit-level=moderate` in `frontend/` -- expected: no vulnerabilities at or above moderate.
- `npm run test:coverage` in `frontend/` -- expected: all tests pass and thresholds remain satisfied.
- `npm run build` in `frontend/` -- expected: production build succeeds.
- `npm run test:e2e` in `frontend/` -- expected: Chromium suite passes through Playwright-managed webServer.
- `ctest --output-on-failure` in `backend_cpp/build` -- expected: all C++ tests pass.
- `cppcheck ... --error-exitcode=1` in `backend_cpp/` -- expected: no findings.
- `bash backend_cpp/tests/integration/run_integration.sh` -- expected: either tests pass or missing local prerequisites fail with actionable guidance.

## Suggested Review Order

**Implementation Record**

- Start with the final implementation summary and verification table.
  [`迭代14-仓库治理与质量信号收口方案.md:212`](../planning-artifacts/迭代14-仓库治理与质量信号收口方案.md#L212)

**Repository Hygiene**

- Ignore local credentials, certs, backups, and generated test artifacts.
  [`.gitignore:10`](../../.gitignore#L10)

- Block tracked secrets and generated artifacts before other CI jobs.
  [`cpp-vue-ci.yml:13`](../../.github/workflows/cpp-vue-ci.yml#L13)

- Keep old Flask CI visible but manual-only and inert.
  [`ci.yml:1`](../../.github/workflows/ci.yml#L1)

**Integration Test Safety**

- Print local prerequisite guidance before any database mutation.
  [`run_integration.sh:39`](../../backend_cpp/tests/integration/run_integration.sh#L39)

- Fail fast when MySQL or Redis is unavailable.
  [`run_integration.sh:85`](../../backend_cpp/tests/integration/run_integration.sh#L85)

- Render config through Python args to preserve special characters.
  [`run_integration.sh:124`](../../backend_cpp/tests/integration/run_integration.sh#L124)

**Frontend Gates**

- CI lint now enforces zero warnings.
  [`package.json:11`](../../frontend/package.json#L11)

- Shared test harness suppresses expected logs and covers missing EP stubs.
  [`harness.js:30`](../../frontend/src/test/harness.js#L30)

- Playwright webServer uses explicit IPv4 loopback.
  [`playwright.config.js:17`](../../frontend/playwright.config.js#L17)

- Vite filters only the known third-party annotation warning.
  [`vite.config.js:64`](../../frontend/vite.config.js#L64)

**Documentation**

- Root README points tests at the current C++/Vue gates.
  [`README.md:303`](../../README.md#L303)

- Refactoring guide now states Drogon/Vue as the current architecture.
  [`REFACTORING_GUIDE.md:3`](../../REFACTORING_GUIDE.md#L3)

- Legacy Python tests are explicitly non-gating.
  [`tests/README.md:1`](../../tests/README.md#L1)
