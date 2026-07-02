---
title: 'Admin Article Menu Category Management'
type: 'feature'
created: '2026-07-02'
status: 'done'
baseline_commit: 'e252514bf98fd39b0188f065af9a52eae9605af1'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/CLAUDE.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The `dev_cpp` branch exposes the article navigation menu from a hard-coded C++ map and the frontend infers hierarchy from numeric ID ranges, so admins cannot add, delete, rename, hide, reorder, or safely repoint categories without code changes. Article editing also depends on that rigid map, making future article category switching brittle.

**Approach:** Move article menu/category nodes into a dedicated MySQL-backed `article_category` tree while preserving the existing `article.type` integer contract and `/api/articles/types` response shape. Add admin-only CRUD endpoints and an admin UI tab for node management, and let the header, write page, and admin article list consume the same tree so article category switching is straightforward now and extensible later.

## Boundaries & Constraints

**Always:** Keep the active stack focused on C++ Drogon and Vue 3. Preserve compatibility for existing article URLs and filters using numeric `type` IDs. Keep `/api/articles/types` returning `data.types` for old callers and add `data.tree`/`data.flat` for new callers. Seed the DB table with the current static categories and keep article rows unchanged. Validate all admin writes server-side: non-empty name, valid parent, no parent cycle, no duplicate sibling names, and valid move target when deleting a category with articles.

**Ask First:** Halt before changing article URL format, renaming the `article.type` column, deleting existing article data, making drag-and-drop ordering a required dependency, or broadening the feature into a full article bulk-management workflow beyond category reassignment.

**Never:** Do not develop the legacy Flask backend. Do not keep the category source hard-coded after introducing the DB table. Do not allow category deletion to orphan articles or children. Do not expose category mutation endpoints without `AdminFilter`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Public category load | Visitor opens the site after DB migration | `/api/articles/types` returns `types`, `flat`, and sorted visible `tree`; header renders custom admin-defined menu | If the new table is missing/unavailable, return the legacy static map so public navigation does not hard-fail |
| Create node | Admin posts `{name,parent_id,sort_order}` | New node is inserted, returned in admin list/tree, and appears in public tree when visible | 400 for blank name, missing parent, duplicate sibling name, or invalid parent |
| Rename/reparent node | Admin updates a node name or parent | Node updates immediately; tree order remains deterministic by `sort_order,id`; dependent article URLs keep using the same type ID | 400 if parent creates a cycle or sibling name conflicts |
| Delete node with articles | Admin deletes category containing articles | UI requires a replacement category; backend moves affected articles to replacement, reparents children to deleted node's parent, then deletes node | 400 if replacement is absent, same as deleted node, descendant of deleted node, or not found |
| Delete node without articles | Admin deletes empty category at any depth | Backend reparents direct children to deleted parent, deletes node, and refreshes UI/store | 404 for unknown category |
| Switch article category | Admin changes category in article table | Backend validates target category and updates `article.type`; frontend row and article store reflect the new category name | 400 for invalid category; 404 for missing article |

</frozen-after-approval>

## Code Map

- `backend_cpp/controllers/ArticleController.cc` -- current static `ARTICLE_TYPES` and public `/api/articles/types` endpoint to replace with DB-backed tree response plus fallback.
- `backend_cpp/controllers/AdminController.h` / `backend_cpp/controllers/AdminController.cc` -- existing admin routes; add article-category CRUD and admin article category reassignment.
- `backend_cpp/models/ArticleCategory.h` / `backend_cpp/models/ArticleCategory.cc` -- new pure category model/tree helpers for JSON responses and testable hierarchy validation.
- `backend_cpp/CMakeLists.txt` and `backend_cpp/tests/CMakeLists.txt` -- include the new model and tests.
- `scripts/sql/09_article_category.sql` -- fresh-install schema and seed data for the current article type IDs.
- `scripts/sql/migrations/2026-07-02_article_category_menu.sql` -- idempotent migration for existing deployments.
- `scripts/verify_db_schema.sh` -- include `article_category` columns/indexes in schema checks.
- `frontend/src/api/index.js` -- add admin category CRUD and article type reassignment wrappers.
- `frontend/src/stores/article.js` -- cache `types`, `flat`, `tree`; expose force refresh and tree-derived cascader options.
- `frontend/src/components/layout/AppHeader.vue` -- render navigation from `articleStore.articleTypeTree` instead of numeric ID inference.
- `frontend/src/views/WriteArticle.vue` -- use store-provided cascader options and path resolution instead of ID arithmetic.
- `frontend/src/views/admin/AdminDashboard.vue` -- add a category/menu management tab and wire article row category switching.
- `frontend/src/views/admin/ArticleCategoryManager.vue` -- new focused UI for add child/root, rename, hide/show, sort, delete with article migration target.
- `frontend/src/**/*.{spec.js}` and `backend_cpp/tests/*` -- coverage for tree conversion, CRUD wrappers, UI actions, and article category switching behavior.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/sql/09_article_category.sql` and `scripts/sql/migrations/2026-07-02_article_category_menu.sql` -- create/seed `article_category` with current category IDs, parent IDs, sort order, visibility, timestamps, indexes, and idempotent inserts.
- [x] `scripts/verify_db_schema.sh` -- add expected table/index metadata for `article_category`.
- [x] `backend_cpp/models/ArticleCategory.h` / `backend_cpp/models/ArticleCategory.cc` -- implement category DTO, JSON flat/tree builders, descendant checks, and path helpers independent of live DB.
- [x] `backend_cpp/controllers/ArticleController.cc` / `.h` -- make `/api/articles/types` query visible DB categories, return `types`, `flat`, `tree`, and fall back to legacy static data on DB/table failure.
- [x] `backend_cpp/controllers/AdminController.cc` / `.h` -- add `GET/POST/PUT/DELETE /api/admin/article-categories` and `PUT /api/admin/articles/{id}/type`, guarded by `AdminFilter`, with validation and safe delete/move semantics.
- [x] `frontend/src/api/index.js` -- expose `adminApi.getArticleCategories/createArticleCategory/updateArticleCategory/deleteArticleCategory/updateArticleType` and keep existing article APIs intact.
- [x] `frontend/src/stores/article.js` -- normalize API response into `articleTypes`, `articleTypeFlat`, `articleTypeTree`; add `refreshArticleTypes`, `getTypePath`, and `categoryOptions`.
- [x] `frontend/src/components/layout/AppHeader.vue` and `frontend/src/views/WriteArticle.vue` -- consume store tree/options so custom nodes appear without hard-coded ID hierarchy.
- [x] `frontend/src/views/admin/AdminDashboard.vue` and `frontend/src/views/admin/ArticleCategoryManager.vue` -- add admin tab for category CRUD and article table category switching.
- [x] `backend_cpp/tests` and `frontend/src` specs -- cover model tree helpers, store normalization/path lookup, header menu rendering, write-page category selection, category manager actions, and admin article type switching.

**Acceptance Criteria:**
- Given an admin is logged in, when they open the admin dashboard, then a menu/category tab lists the current article categories as an editable hierarchy.
- Given an admin adds a root or child category, when the operation succeeds, then the category appears in the admin tab, header menu, and write article category picker after refresh.
- Given an admin renames, hides/shows, or changes sort order for a category, when they save, then public navigation and article writing use the updated name/visibility/order.
- Given an admin deletes a category with articles and chooses a replacement category, when deletion succeeds, then affected articles are reassigned and no article keeps the deleted type.
- Given an admin changes an article row category, when the backend confirms the change, then the admin table displays the new category and future article filters use the new type.
- Given non-admin or anonymous users call mutation endpoints, when the request reaches the backend, then `AdminFilter` rejects it.

## Spec Change Log

## Design Notes

The new table should not replace `article.type` in this iteration; it should make that existing integer meaningful and editable. Keep compatibility by returning the old map and adding richer shapes:

```json
{
  "types": {"1": "交易策略", "101": "CTA策略"},
  "flat": [{"id": 1, "parent_id": null, "name": "交易策略"}],
  "tree": [{"id": 1, "name": "交易策略", "children": [{"id": 101, "name": "CTA策略"}]}]
}
```

## Verification

**Commands:**
- `cd backend_cpp/build && cmake --build . --target woniunote_tests && ctest --output-on-failure` -- expected: all backend unit tests pass.
- `cd backend_cpp && cppcheck --enable=warning,performance,portability --std=c++17 --language=c++ --inline-suppr --suppress=missingIncludeSystem --suppress=normalCheckLevelMaxBranches --error-exitcode=1 -I core -I controllers -I filters -I models controllers core filters models main.cc` -- expected: zero findings.
- `cd frontend && npm run lint:ci` -- expected: zero warnings/errors.
- `cd frontend && npm run test:coverage` -- expected: all tests pass and current coverage gate remains satisfied.
- `cd frontend && npm run build` -- expected: production build succeeds.
- `cd frontend && npm run test:e2e` -- expected: existing E2E suite remains green.
- `git diff --check` -- expected: no whitespace errors.

## Suggested Review Order

**Design Entry**

- DB-backed category contract replaces hard-coded navigation while keeping legacy fallback: [backend_cpp/controllers/ArticleController.cc](../../backend_cpp/controllers/ArticleController.cc)

**Schema And Category Model**

- Fresh installs and migrations seed the editable article category tree: [scripts/sql/09_article_category.sql](../../scripts/sql/09_article_category.sql), [scripts/sql/migrations/2026-07-02_article_category_menu.sql](../../scripts/sql/migrations/2026-07-02_article_category_menu.sql)
- Tree helpers preserve `types`, `flat`, `tree`, path, and descendant semantics: [backend_cpp/models/ArticleCategory.cc](../../backend_cpp/models/ArticleCategory.cc)

**Admin API Safety**

- Admin routes expose category CRUD and article type switching behind `AdminFilter`: [backend_cpp/controllers/AdminController.h](../../backend_cpp/controllers/AdminController.h)
- Duplicate sibling validation, cycle checks, article type switching, and safe delete/migration live in one controller boundary: [backend_cpp/controllers/AdminController.cc](../../backend_cpp/controllers/AdminController.cc)

**Frontend Consumption**

- Store normalizes old and new category payloads into shared map/flat/tree state: [frontend/src/stores/article.js](../../frontend/src/stores/article.js)
- Header and article editor consume the server category tree instead of numeric-ID hierarchy assumptions: [frontend/src/components/layout/AppHeader.vue](../../frontend/src/components/layout/AppHeader.vue), [frontend/src/views/WriteArticle.vue](../../frontend/src/views/WriteArticle.vue)

**Admin UI**

- Dashboard adds the category tab and inline article category switching: [frontend/src/views/admin/AdminDashboard.vue](../../frontend/src/views/admin/AdminDashboard.vue)
- Dedicated manager handles create/edit/show/delete with migration target selection: [frontend/src/views/admin/ArticleCategoryManager.vue](../../frontend/src/views/admin/ArticleCategoryManager.vue)

**Tests And Tooling**

- Backend tests cover tree filtering, promotion, path, and descendant checks: [backend_cpp/tests/test_article_category.cc](../../backend_cpp/tests/test_article_category.cc)
- Frontend tests cover store normalization and admin category manager actions: [frontend/src/stores/article.spec.js](../../frontend/src/stores/article.spec.js), [frontend/src/views/admin/ArticleCategoryManager.spec.js](../../frontend/src/views/admin/ArticleCategoryManager.spec.js)
- Schema verifier now tracks the new table and indexes: [scripts/verify_db_schema.sh](../../scripts/verify_db_schema.sh)
