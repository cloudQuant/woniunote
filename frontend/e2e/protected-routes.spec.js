import { test, expect } from './support/test'
import { mockApi, loginAs } from './support/mockApi'
import {
  completeApiResponse,
  waitForApiResponse,
  waitForArticleThumbnailResponses,
  waitForHomeResponses
} from './support/apiLifecycle'

test.describe('Route guards', () => {
  test.describe.configure({ retries: 0 })

  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('anonymous user is redirected to login from a protected route', async ({ page }) => {
    await page.goto('/write', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/login/)
    // The redirect target is preserved in the query string.
    await expect(page).toHaveURL(/redirect=%2Fwrite|redirect=\/write/)
  })

  test('anonymous user is redirected from the user center', async ({ page }) => {
    const captchaResponse = waitForApiResponse(page, 'GET', '/api/captcha/generate')
    await page.goto('/user', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/login/)
    await completeApiResponse(captchaResponse)
  })

  test('non-admin is redirected home from the admin dashboard', async ({ page }) => {
    await loginAs(page, 'user')
    const homeResponses = waitForHomeResponses(page)
    const thumbnailResponses = waitForArticleThumbnailResponses(page)
    await page.goto('/admin', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/$|\/page/)
    await Promise.all([...homeResponses, ...thumbnailResponses].map(completeApiResponse))
  })

  test('admin can access the admin dashboard', async ({ page }) => {
    await loginAs(page, 'admin')
    const articleResponse = waitForApiResponse(page, 'GET', '/api/articles')
    const typeResponse = waitForApiResponse(page, 'GET', '/api/articles/types')
    const categoryResponse = waitForApiResponse(page, 'GET', '/api/admin/article-categories')
    await page.goto('/admin', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/admin/)
    await Promise.all([articleResponse, typeResponse, categoryResponse].map(completeApiResponse))
  })

  test('authenticated user can open the user center', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/user', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/user/)
    await expect(page.locator('.user-center-page')).toBeVisible()
  })
})
