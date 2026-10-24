import { test, expect } from './support/test'
import { mockApi } from './support/mockApi'
import {
  completeApiResponse,
  waitForApiResponse,
  waitForArticleThumbnailResponses,
  waitForHomeResponses
} from './support/apiLifecycle'

test.describe('Home & navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('loads the home page with header, article list and footer', async ({ page }) => {
    const homeResponses = waitForHomeResponses(page)
    const thumbnailResponses = waitForArticleThumbnailResponses(page)
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    // Brand title is set from route meta.
    await expect(page).toHaveTitle(/cloudQuant/)
    // Header logo + footer copyright present.
    await expect(page.locator('.app-header')).toBeVisible()
    await expect(page.locator('.app-footer')).toContainText('版权所有')
    // Articles from the mocked list render.
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
    await Promise.all([...homeResponses, ...thumbnailResponses].map(completeApiResponse))
  })

  test('keeps search and popular articles on the left at desktop widths', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const homeResponses = waitForHomeResponses(page)
    const thumbnailResponses = waitForArticleThumbnailResponses(page)
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await Promise.all([...homeResponses, ...thumbnailResponses].map(completeApiResponse))

    const mainColumn = page.locator('.home-main-column')
    const sidebarColumn = page.locator('.home-sidebar-column')
    await expect(mainColumn).toBeVisible()
    await expect(sidebarColumn).toBeVisible()
    await expect(sidebarColumn.getByPlaceholder('请输入关键字')).toBeVisible()
    await expect(sidebarColumn.getByText('热门文章')).toBeVisible()

    const main = await mainColumn.boundingBox()
    const sidebar = await sidebarColumn.boundingBox()
    expect(main).not.toBeNull()
    expect(sidebar).not.toBeNull()
    expect(sidebar.x + sidebar.width).toBeLessThanOrEqual(main.x)

    // 与 Element Plus 的 xs 栅格边界一致：768px 仍保持侧栏在左；
    // 767px 以下切为单列，并让文章内容优先展示。
    await page.setViewportSize({ width: 768, height: 800 })
    const boundaryMain = await mainColumn.boundingBox()
    const boundarySidebar = await sidebarColumn.boundingBox()
    expect(boundarySidebar.x + boundarySidebar.width).toBeLessThanOrEqual(boundaryMain.x)

    await page.setViewportSize({ width: 767, height: 800 })
    const mobileMain = await mainColumn.boundingBox()
    const mobileSidebar = await sidebarColumn.boundingBox()
    expect(mobileMain.y).toBeLessThan(mobileSidebar.y)
  })

  test('navigates to an article detail from the list', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await page.getByText('量化投资入门').first().click()
    await expect(page).toHaveURL(/\/article\/1/)
    await expect(page.locator('.article-body, .article-content, article').first()).toBeVisible()
  })

  test('navigates to a category via the nav dropdown route', async ({ page }) => {
    const articleResponse = waitForApiResponse(page, 'GET', '/api/articles')
    const hotResponse = waitForApiResponse(page, 'GET', '/api/articles/hot')
    const typeResponse = waitForApiResponse(page, 'GET', '/api/articles/types')
    const thumbnailResponses = waitForArticleThumbnailResponses(page)
    await page.goto('/type/101/1', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/type\/101/)
    await Promise.all([
      articleResponse,
      hotResponse,
      typeResponse,
      ...thumbnailResponses
    ].map(completeApiResponse))
  })

  test('shows the 404 page for unknown routes', async ({ page }) => {
    await page.goto('/this/does/not/exist', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('404')).toBeVisible()
    await expect(page.getByText('页面未找到')).toBeVisible()
  })

  test('search navigation works from the URL', async ({ page }) => {
    const articleResponse = waitForApiResponse(page, 'GET', '/api/articles')
    const hotResponse = waitForApiResponse(page, 'GET', '/api/articles/hot')
    const thumbnailResponses = waitForArticleThumbnailResponses(page)
    await page.goto('/search?keyword=python', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/search/)
    await Promise.all([
      articleResponse,
      hotResponse,
      ...thumbnailResponses
    ].map(completeApiResponse))
  })
})
