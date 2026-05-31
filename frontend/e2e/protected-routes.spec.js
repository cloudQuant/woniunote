import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

test.describe('Route guards', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('anonymous user is redirected to login from a protected route', async ({ page }) => {
    await page.goto('/write')
    await expect(page).toHaveURL(/\/login/)
    // The redirect target is preserved in the query string.
    await expect(page).toHaveURL(/redirect=%2Fwrite|redirect=\/write/)
  })

  test('anonymous user is redirected from the user center', async ({ page }) => {
    await page.goto('/user')
    await expect(page).toHaveURL(/\/login/)
  })

  test('non-admin is redirected home from the admin dashboard', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/$|\/page/)
  })

  test('admin can access the admin dashboard', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/admin/)
  })

  test('authenticated user can open the user center', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/user')
    await expect(page).toHaveURL(/\/user/)
    await expect(page.locator('.user-center-page')).toBeVisible()
  })
})
