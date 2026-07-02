---
title: 'Category Management Tab on My Articles'
type: 'feature'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
---

# Category Management Tab on My Articles

## Intent

**Problem:** The category management feature was available from a separate personal-center route, but administrators did not see a category-management tab when they opened `/user/articles`.

**Approach:** Embed the existing admin category-management experience inside the My Articles page as an admin-only "分类管理" tab, while keeping the normal article list as the default tab and preserving the standalone `/user/categories` route.

## Suggested Review Order

**User-Facing Entry**

- Confirm `/user/articles` now exposes the admin-only category tab.
  [`MyArticles.vue:2`](../../frontend/src/views/user/MyArticles.vue#L2)

- Check that the embedded category manager is rendered under the tab.
  [`MyArticles.vue:73`](../../frontend/src/views/user/MyArticles.vue#L73)

- Verify non-admin users keep the original single-page article-list feel.
  [`MyArticles.vue:166`](../../frontend/src/views/user/MyArticles.vue#L166)

**Embedded Reuse**

- Confirm the category center can hide its standalone page header when embedded.
  [`ArticleCategoryCenter.vue:1`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L1)

- Check the prop default keeps `/user/categories` unchanged.
  [`ArticleCategoryCenter.vue:115`](../../frontend/src/views/user/ArticleCategoryCenter.vue#L115)

**Verification**

- Review the unit test that asserts admins see category management on `/user/articles`.
  [`user-views.spec.js:102`](../../frontend/src/views/user/user-views.spec.js#L102)

- Review the e2e test that visits `/user/articles` as admin and opens the tab.
  [`user-center.spec.js:36`](../../frontend/e2e/user-center.spec.js#L36)
