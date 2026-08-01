import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

const pagesWithArticleSidebar = [
  {
    name: '首页',
    path: '/',
    main: '.home-main-column',
    sidebar: '.home-sidebar-column'
  },
  {
    name: '分类页',
    path: '/type/101/1',
    main: '.category-main-column',
    sidebar: '.category-sidebar-column'
  },
  {
    name: '搜索页',
    path: '/search?keyword=python',
    main: '.search-main-column',
    sidebar: '.search-sidebar-column'
  },
  {
    name: '文章详情页',
    path: '/article/1',
    main: '.article-detail-main-column',
    sidebar: '.article-detail-sidebar-column'
  }
]

test.describe('Article sidebar layout', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  for (const pageConfig of pagesWithArticleSidebar) {
    test(`${pageConfig.name}在桌面端将搜索与热门文章置于左侧`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 })
      await page.goto(pageConfig.path)

      const mainColumn = page.locator(pageConfig.main)
      const sidebarColumn = page.locator(pageConfig.sidebar)
      await expect(mainColumn).toBeVisible()
      await expect(sidebarColumn).toBeVisible()
      await expect(sidebarColumn.getByPlaceholder('请输入关键字')).toBeVisible()
      await expect(sidebarColumn.getByText('热门文章')).toBeVisible()

      const desktopMain = await mainColumn.boundingBox()
      const desktopSidebar = await sidebarColumn.boundingBox()
      expect(desktopMain).not.toBeNull()
      expect(desktopSidebar).not.toBeNull()
      expect(desktopSidebar.x + desktopSidebar.width).toBeLessThanOrEqual(desktopMain.x)

      // Element Plus 的 xs 栅格从 767px 以下才切换为单列。
      await page.setViewportSize({ width: 768, height: 800 })
      const boundaryMain = await mainColumn.boundingBox()
      const boundarySidebar = await sidebarColumn.boundingBox()
      expect(boundaryMain).not.toBeNull()
      expect(boundarySidebar).not.toBeNull()
      expect(boundarySidebar.x + boundarySidebar.width).toBeLessThanOrEqual(boundaryMain.x)

      await page.setViewportSize({ width: 767, height: 800 })
      const mobileMain = await mainColumn.boundingBox()
      const mobileSidebar = await sidebarColumn.boundingBox()
      expect(mobileMain).not.toBeNull()
      expect(mobileSidebar).not.toBeNull()
      expect(mobileMain.y).toBeLessThan(mobileSidebar.y)
    })
  }
})
