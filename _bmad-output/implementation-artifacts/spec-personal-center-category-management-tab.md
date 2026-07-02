---
title: 'Personal Center Category Management Tab'
type: 'feature'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
---

# Personal Center Category Management Tab

## Intent

**Problem:** Article category editing was embedded in the personal "My Articles" table, making category administration hard to discover and mixing content ownership with global taxonomy management.

**Approach:** Move category administration into a dedicated admin-only personal-center route under "My Articles", with separate tabs for article category reassignment and category CRUD while leaving "My Articles" as a read-only category display.

## Suggested Review Order

**Category Management Flow**

- Start with the new personal-center tab split and toolbar layout.
  [`ArticleCategoryCenter.vue:10`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L10)

- Review admin article loading and category filter parameter shaping.
  [`ArticleCategoryCenter.vue:186`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L186)

- Check single article category reassignment and failure rollback.
  [`ArticleCategoryCenter.vue:218`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L218)

- Check batch reassignment guards, update fan-out, and reload behavior.
  [`ArticleCategoryCenter.vue:238`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L238)

- Confirm existing category CRUD is reused inside the maintenance tab.
  [`ArticleCategoryCenter.vue:103`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L103)

**Navigation and Scope**

- Verify the admin-only entry now sits directly below "My Articles".
  [`UserCenter.vue:23`](../../frontend/src/views/UserCenter.vue#L23)

- Confirm the personal-center category route remains admin-guarded.
  [`index.js:110`](../../frontend/src/router/index.js#L110)

- Confirm the personal article list no longer edits category inline.
  [`MyArticles.vue:19`](../../frontend/src/views/user/MyArticles.vue#L19)

**Verification**

- Review focused unit coverage for load, filter, single update, batch update, and refresh.
  [`ArticleCategoryCenter.spec.js:75`](../../frontend/src/views/user/ArticleCategoryCenter.spec.js#L75)

- Review the new administrator e2e smoke coverage for the route and tabs.
  [`user-center.spec.js:36`](../../frontend/e2e/user-center.spec.js#L36)

- Confirm e2e mocks now cover admin article and category endpoints.
  [`mockApi.js:167`](../../frontend/e2e/support/mockApi.js#L167)
