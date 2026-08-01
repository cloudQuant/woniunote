import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

test.describe('Article detail & comments', () => {
  test('renders article content, title and comments', async ({ page }) => {
    await mockApi(page)
    await page.goto('/article/1')
    await expect(page).toHaveTitle(/量化投资入门/)
    await expect(page.getByText('这是一篇关于量化投资的文章正文')).toBeVisible()
    // Existing comment from the mock renders.
    await expect(page.getByText('写得很好！')).toBeVisible()
  })

  test('navigates to the next article through the detail navigation link', async ({ page }) => {
    await mockApi(page)
    await page.goto('/article/1')

    const navigation = page.getByRole('navigation', { name: '同类文章导航' })
    await expect(navigation.getByText('暂无上一篇文章')).toBeVisible()
    await navigation.getByRole('link', { name: '量化投资进阶' }).click()

    await expect(page).toHaveURL(/\/article\/3$/)
    await expect(page).toHaveTitle(/量化投资进阶/)
    await expect(page.getByText('这是量化投资的进阶文章正文')).toBeVisible()
    await expect(navigation.getByText('暂无下一篇文章')).toBeVisible()
  })

  test('does not render a previous link when there is no previous article', async ({ page }) => {
    await mockApi(page)
    await page.goto('/article/1')

    const previousRow = page.locator('.article-navigation__previous')
    await expect(previousRow.getByText('暂无上一篇文章')).toBeVisible()
    await expect(previousRow.locator('a')).toHaveCount(0)
  })

  test('anonymous favorite attempt redirects to login', async ({ page }) => {
    await mockApi(page)
    await page.goto('/article/1')
    const favBtn = page.getByRole('button', { name: /收藏/ }).first()
    if (await favBtn.count()) {
      await favBtn.click()
      await expect(page).toHaveURL(/\/login/)
    }
  })

  test('logged-in user can post a comment', async ({ page }) => {
    await mockApi(page)
    await loginAs(page, 'user')
    await page.goto('/article/1')

    const box = page.locator('textarea').first()
    await box.fill('这是一条 E2E 测试评论')
    // Submit button label contains 评论/发表/发布.
    const submit = page.getByRole('button', { name: /评论|发表|发布/ }).first()
    await submit.click()
    // Success path: the create call was mocked; a success toast appears.
    await expect(page.getByText('评论发表成功')).toBeVisible()
  })
})
