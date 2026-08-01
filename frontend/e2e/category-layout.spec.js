import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

test.describe('Category layout', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('desktop uses a left sidebar, while mobile keeps article content first', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/type/909/3')

    const mainColumn = page.locator('.category-main-column')
    const sidebarColumn = page.locator('.category-sidebar-column')
    await expect(mainColumn).toBeVisible()
    await expect(sidebarColumn).toBeVisible()
    await expect(page.locator('.article-item').first()).toBeVisible()
    await expect(sidebarColumn.getByPlaceholder('请输入关键字')).toBeVisible()
    await expect(sidebarColumn.getByText('热门文章')).toBeVisible()

    const desktopMain = await mainColumn.boundingBox()
    const desktopSidebar = await sidebarColumn.boundingBox()
    expect(desktopMain).not.toBeNull()
    expect(desktopSidebar).not.toBeNull()
    expect(desktopSidebar.x + desktopSidebar.width).toBeLessThanOrEqual(desktopMain.x)

    await page.setViewportSize({ width: 375, height: 800 })
    await expect(page.locator('.article-item').first()).toBeVisible()

    const mobileMain = await mainColumn.boundingBox()
    const mobileSidebar = await sidebarColumn.boundingBox()
    expect(mobileMain).not.toBeNull()
    expect(mobileSidebar).not.toBeNull()
    expect(mobileMain.y).toBeLessThan(mobileSidebar.y)
  })
})
