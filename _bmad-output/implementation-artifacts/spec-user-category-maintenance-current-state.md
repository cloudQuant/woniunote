# User Category Maintenance Current-State Display

## Scope

Improve `/user/categories` so regular signed-in users can land directly on the category maintenance view and see the current article category structure before editing it.

## Changes

- `/user/categories` now opens `ArticleCategoryCenter` on the `categories` tab by default.
- `ArticleCategoryManager` now shows a current-state overview above the editable table:
  - total category count
  - root category count
  - visible category count
  - linked article count
  - full category paths with per-category article counts
- The manager can rebuild its tree display from a flat response when `tree` is empty.
- `GET /api/admin/article-categories` now bootstraps `article_category` when the table is missing or empty, using the existing legacy category IDs and hierarchy.
- `GET /api/articles/types` falls back to legacy categories when the category table query returns no rows.

## Acceptance Checks

- Direct route: `/user/categories` shows category maintenance details.
- Existing `/user/articles` category management still supports article pagination and the maintenance tab.
- Missing or empty `article_category` no longer leaves the maintenance UI blank.

## Verification

- `npx vitest run --config vitest.config.js src/views/admin/ArticleCategoryManager.spec.js src/views/user/ArticleCategoryCenter.spec.js src/router/index.spec.js`
- `./build.sh`
- `ctest --output-on-failure`
- `npm run lint:ci`
- `npx playwright test e2e/user-center.spec.js`
- `npm run test:coverage`
- `npm run build`
- `npm audit --omit=dev --audit-level=moderate`
- `npm run test:e2e`
