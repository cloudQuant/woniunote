---
title: 'Login Success Redis Timeout Fix'
type: 'bugfix'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-personal-center-stuck-and-category-entry-fix.md'
---

# Login Success Redis Timeout Fix

## Intent

**Problem:** Login validation could succeed but never return a response when Redis failed to answer the best-effort `refresh_jti` write, making the UI appear unable to log in.

**Approach:** Guard `storeRefreshJti` with a one-shot completion flag and a 1 second timeout so login/refresh can continue when Redis is slow or unavailable.

## Suggested Review Order

**Login Success Path**

- `storeRefreshJti` timeout and single-callback guard: [backend_cpp/controllers/AuthController.cc](../../backend_cpp/controllers/AuthController.cc)

**Verification Evidence**

- Valid refresh token request now returns `200` with new access/refresh tokens after the Redis write timeout path.
- Invalid login request returns a normal API error instead of hanging behind rate limiting.
