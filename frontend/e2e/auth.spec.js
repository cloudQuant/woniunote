import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('login page renders the form', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('.login-title')).toContainText('登录')
    await expect(page.getByPlaceholder('请输入用户名')).toBeVisible()
    await expect(page.getByPlaceholder('请输入密码')).toBeVisible()
  })

  test('successful login redirects home and persists session', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('tester@example.com')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByRole('button', { name: '登录' }).click()
    await expect(page).toHaveURL(/\/$|\/page/)
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBe('e2e-access')
  })

  test('failed login keeps the user on the login page', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('tester@example.com')
    await page.getByPlaceholder('请输入密码').fill('wrongpass')
    await page.getByRole('button', { name: '登录' }).click()
    // Stays on login; no token stored.
    await expect(page).toHaveURL(/\/login/)
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBeNull()
  })

  test('register page renders and links back to login', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('.register-title')).toContainText('注册')
    await expect(page.getByRole('link', { name: '立即登录' })).toBeVisible()
  })

  test('register validation blocks mismatched passwords', async ({ page }) => {
    await page.goto('/register')
    await page.getByPlaceholder('请输入用户名').fill('newuser')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请再次输入密码').fill('different')
    await page.getByRole('button', { name: '注册' }).click()
    // Inline validation error appears; we stay on the register page.
    await expect(page).toHaveURL(/\/register/)
    await expect(page.getByText('两次输入密码不一致')).toBeVisible()
  })

  test('logged-in user is redirected away from the login page', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/login')
    await expect(page).toHaveURL(/\/$|\/page/)
  })
})
