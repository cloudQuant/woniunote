---
title: 'User Article Category Pagination and Access'
type: 'feature'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
---

# User Article Category Pagination and Access

## Intent

**Problem:** `/user/articles` category management could still load every personal article at once, and the category-management entry was tied to administrator-only access.

**Approach:** Add server-side pagination and category filtering to `/api/articles/my`, route the personal-center category manager through user-owned article APIs by default, and allow authenticated users to access category management.

## Suggested Review Order

**Backend Paging and Access**

- Review personal article paging, clamping, type filtering, and total response fields.
  [`ArticleController.cc:317`](../../backend_cpp/controllers/ArticleController.cc#L317)

- Confirm category CRUD routes now require login rather than administrator role.
  [`AdminController.h:31`](../../backend_cpp/controllers/AdminController.h#L31)

**Personal Center Flow**

- Confirm `/user/articles` always shows the category-management tab.
  [`MyArticles.vue:1`](../../frontend/src/views/user/MyArticles.vue#L1)

- Check the embedded manager uses the personal article scope.
  [`MyArticles.vue:73`](../../frontend/src/views/user/MyArticles.vue#L73)

- Review the category manager's default user-owned article API selection.
  [`ArticleCategoryCenter.vue:118`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L118)

- Verify single and batch category changes use owner-scoped APIs by default.
  [`ArticleCategoryCenter.vue:233`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L233)

**Verification**

- Review unit coverage for paged personal article loading and owner-scoped updates.
  [`ArticleCategoryCenter.spec.js:87`](../../frontend/src/views/user/ArticleCategoryCenter.spec.js#L87)

- Review router coverage for regular-user category management access.
  [`index.spec.js:71`](../../frontend/src/router/index.spec.js#L71)

- Review e2e coverage for regular-user pagination on `/user/articles`.
  [`user-center.spec.js:36`](../../frontend/e2e/user-center.spec.js#L36)
