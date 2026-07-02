---
title: 'Personal Center Article List And Category Fix'
type: 'bugfix'
created: '2026-07-02'
status: 'done'
route: 'one-shot'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-admin-article-menu-category-management.md'
---

# Personal Center Article List And Category Fix

## Intent

**Problem:** In the personal center, "My Articles" could remain stuck when article category loading failed before the article list request ran, and "My Favorites" assumed a nested favorite response shape that the C++ backend does not return. Article category switching was also hard to discover from the admin dashboard, so the user needed the article category change workflow directly in the personal center.

**Approach:** Keep the personal center article/favorite pages resilient to backend response shapes and category loading failures, add a user-owned article category switch endpoint, and expose category switching inline in "My Articles" with the existing category tree.

## Suggested Review Order

**Backend Route Safety**

- Protected owner-only article category switch route: [backend_cpp/controllers/ArticleController.h](../../backend_cpp/controllers/ArticleController.h)
- Owner check, category validation, legacy fallback, and update response: [backend_cpp/controllers/ArticleController.cc](../../backend_cpp/controllers/ArticleController.cc)

**Personal Center UX**

- Inline category cascader and non-blocking category loading in "My Articles": [frontend/src/views/user/MyArticles.vue](../../frontend/src/views/user/MyArticles.vue)
- Flat/nested favorite response normalization in "My Favorites": [frontend/src/views/user/MyFavorites.vue](../../frontend/src/views/user/MyFavorites.vue)

**API Surface**

- User article category update wrapper: [frontend/src/api/index.js](../../frontend/src/api/index.js)

**Regression Coverage**

- API wrapper assertion: [frontend/src/api/index.spec.js](../../frontend/src/api/index.spec.js)
- Personal center loading, category switching, rollback, and favorites normalization tests: [frontend/src/views/user/user-views.spec.js](../../frontend/src/views/user/user-views.spec.js)
