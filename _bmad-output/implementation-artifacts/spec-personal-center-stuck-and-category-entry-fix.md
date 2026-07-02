---
title: 'Personal Center Stuck State And Category Entry Fix'
type: 'bugfix'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-personal-center-article-category-fix.md'
---

# Personal Center Stuck State And Category Entry Fix

## Intent

**Problem:** `/user/articles` and `/user/favorites` could still appear stuck when an expired access token triggered `/api/auth/refresh`, because Redis-backed rate limiting could hang without invoking the request chain. The personal center also did not expose the category management entry, so admins could not find where to add article types.

**Approach:** Add a fail-open timeout to the Redis rate-limit filter, add a frontend timeout to silent token refresh, and move the article category management entry into the personal center for admins while keeping per-article category switching in "My Articles".

## Suggested Review Order

**Backend Stuck-State Fix**

- Redis rate-limit timeout and single-callback guard: [backend_cpp/filters/RateLimitFilter.cc](../../backend_cpp/filters/RateLimitFilter.cc)

**Frontend Auth Recovery**

- Silent refresh now has a hard timeout, so protected pages can recover instead of waiting forever: [frontend/src/api/index.js](../../frontend/src/api/index.js)
- Refresh timeout expectation in interceptor tests: [frontend/src/api/index.spec.js](../../frontend/src/api/index.spec.js)

**Personal Center Category Entry**

- Admin-only `/user/categories` child route: [frontend/src/router/index.js](../../frontend/src/router/index.js)
- Admin route and route-table coverage: [frontend/src/router/index.spec.js](../../frontend/src/router/index.spec.js)
- Admin-only sidebar menu item for article category management: [frontend/src/views/UserCenter.vue](../../frontend/src/views/UserCenter.vue)
- Sidebar entry coverage: [frontend/src/views/UserCenter.spec.js](../../frontend/src/views/UserCenter.spec.js)
