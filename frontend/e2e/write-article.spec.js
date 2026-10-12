import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

/**
 * E2E coverage for the "写文章 + Markdown 导入" flow (迭代 17 / Epic 17.5).
 *
 * The page mounts the real UEditor (loaded from `/ueditor/*`), so the editor
 * body lives in an iframe and the "导入内容" dialog is a second iframe
 * (`/ueditor/dialogs/contentimport/contentimport.html`). Playwright's
 * `frameLocator` is used for both.
 *
 * Determinism notes:
 *  - Backend calls are mocked via support/mockApi.js (same envelope as the
 *    other specs).
 *  - MathJax is loaded from a public CDN by both index.html and the import
 *    dialog. It is blocked here so the suite stays hermetic (no outbound
 *    network) and so the preview deterministically keeps the raw `$...$`
 *    delimiters in the DOM — which is exactly what we want to assert: the
 *    Markdown converter must protect formulas from the emphasis/paragraph
 *    rewrites. When MathJax does load it replaces the delimiters with
 *    `<mjx-container>` and the raw delimiters are gone.
 */

const IMPORT_BUTTON = '.edui-for-contentimport .edui-button-body'
const DIALOG_IFRAME = 'iframe[src*="contentimport"]'
const EDITOR_FRAME = '.edui-editor-iframeholder iframe'

/** Sample Markdown mixing a heading, inline math and a multi-line display block. */
const SAMPLE_MARKDOWN = [
  '# 标题',
  '',
  '行内公式 $c^*$ 与 $n^*$ 的说明。',
  '',
  '$$',
  '\\frac{a}{b} = c',
  '$$',
  '',
  '结束段落。'
].join('\n')

/** Block the MathJax CDN so the run needs no outbound network. */
async function blockMathJaxCdn(page) {
  await page.route((url) => url.hostname === 'cdn.bootcdn.net', (route) => route.abort())
}

/**
 * Wait until `locator` stops moving.
 *
 * UEditor is configured with `autoHeightEnabled`, so its iframe grows from
 * `initialFrameHeight` (450px) to the content height a beat after mount. That
 * shift moves everything below the editor (the 保存草稿 / 发布 buttons) by
 * several hundred pixels, and a click issued while the shift is in flight can
 * land its mouseup on a different element — the button then never fires.
 * Sampling the box until two consecutive reads agree removes that race.
 */
async function waitForStableLayout(locator) {
  let previous = null
  await expect(async () => {
    const box = await locator.boundingBox()
    expect(box).not.toBeNull()
    const stable = previous !== null && Math.abs(box.y - previous.y) < 1
    previous = box
    expect(stable).toBe(true)
  }).toPass({ timeout: 10000, intervals: [150] })
}

/** Click the toolbar entry and return a locator scoped to the dialog iframe. */
async function openImportDialog(page) {
  await page.locator(IMPORT_BUTTON).click()
  const dialog = page.frameLocator(DIALOG_IFRAME)
  await expect(dialog.locator('#markdown-input')).toBeAttached()
  return dialog
}

test.describe('Write article + Markdown import', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await blockMathJaxCdn(page)
  })

  test('anonymous visitor is redirected to login and bounced back to /write', async ({ page }) => {
    await page.goto('/write')
    await expect(page).toHaveURL(/\/login/)
    await expect(page).toHaveURL(/redirect=%2Fwrite|redirect=\/write/)
  })

  test('author opens the write page with the editor and the import entry', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/write')

    await expect(page).toHaveURL(/\/write$/)
    await expect(page.locator('.write-article-page')).toBeVisible()
    await expect(page.locator('.page-title')).toHaveText('写文章')
    await expect(page.getByPlaceholder('请输入文章标题')).toBeVisible()
    // UEditor booted: toolbar + editing surface.
    await expect(page.locator('.edui-editor')).toBeVisible()
    await expect(page.locator(IMPORT_BUTTON)).toBeVisible()
    await expect(page.locator(IMPORT_BUTTON)).toHaveAttribute('title', '导入内容')
  })

  test('import dialog converts pasted Markdown and keeps $...$ formulas intact', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/write')

    const dialog = await openImportDialog(page)
    await dialog.getByText('粘贴Markdown').click()
    await expect(dialog.locator('#markdown-input')).toBeVisible()

    await dialog.locator('#fileInputContent').fill(SAMPLE_MARKDOWN)
    await dialog.locator('#markdown-input').getByText('转换预览').click()

    const preview = dialog.locator('.file-result')
    await expect(preview).toBeVisible()

    // Heading and surrounding prose were converted.
    await expect(preview.locator('h1')).toHaveText('标题')
    await expect(preview).toContainText('结束段落。')

    // Formulas survive as raw `$...$` / `$$...$$` (MathJax blocked above).
    const text = await preview.innerText()
    expect(text).toContain('$c^*$')
    expect(text).toContain('$n^*$')
    expect(text).toContain('$$')
    expect(text).toContain('\\frac{a}{b} = c')

    // Regression guard: `*` inside `$...$` must not be turned into <em>.
    const html = await preview.innerHTML()
    expect(html).not.toContain('<em>')
    expect(html).toContain('<h1>标题</h1>')

    await expect(dialog.locator('.file-tip')).toContainText('转换成功')
  })

  test('confirming the import inserts the converted HTML into the editor', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/write')

    const dialog = await openImportDialog(page)
    await dialog.getByText('粘贴Markdown').click()
    await dialog.locator('#fileInputContent').fill(SAMPLE_MARKDOWN)
    await dialog.locator('#markdown-input').getByText('转换预览').click()
    await expect(dialog.locator('.file-result')).toBeVisible()

    await page.locator('.edui-okbutton').click()
    await expect(page.locator('.edui-dialog:visible')).toHaveCount(0)

    const editor = page.frameLocator(EDITOR_FRAME)
    const body = editor.locator('body')
    await expect(body.locator('h1')).toHaveText('标题')
    const editorHtml = await body.innerHTML()
    expect(editorHtml).toContain('$c^*$')
    expect(editorHtml).toContain('$n^*$')
    expect(editorHtml).toContain('\\frac{a}{b} = c')
    expect(editorHtml).toContain('结束段落。')
  })

  test('closing the import dialog without confirming leaves the editor interactive', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/write')

    const dialog = await openImportDialog(page)
    await dialog.getByText('粘贴Markdown').click()
    await dialog.locator('#fileInputContent').fill(SAMPLE_MARKDOWN)

    // The dialog's own 关闭 link only hides the paste panel; the dialog shell
    // is dismissed with the 取消 button.
    await page.locator('.edui-cancelbutton').click()
    await expect(page.locator('.edui-dialog:visible')).toHaveCount(0)

    // Nothing was inserted, and the editing surface still accepts input.
    const editor = page.frameLocator(EDITOR_FRAME)
    const body = editor.locator('body')
    await expect(body).not.toContainText('标题')

    await body.click()
    await page.keyboard.type('手动输入的内容')
    await expect(body).toContainText('手动输入的内容')
  })

  test('saving a draft in edit mode posts the article body with drafted=1', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/edit/1')

    // The form is pre-filled from the article detail API.
    await expect(page.getByPlaceholder('请输入文章标题')).toHaveValue('量化投资入门')
    await expect(page.locator('.el-cascader input')).toHaveValue('交易策略 / 股票策略')

    // Regression guard (iteration 18 / defect #7): the editor iframe must be
    // backfilled with the article body — this silently failed before the
    // iteration-17 UEditor ready fix (isReady was never true, so the
    // modelValue watch and the ready-path setContent were both dead).
    const editorFrame = page.frameLocator(EDITOR_FRAME)
    await expect(editorFrame.locator('body')).toContainText('这是一篇关于量化投资的文章正文')

    const saveButton = page.getByRole('button', { name: '保存草稿' })
    await waitForStableLayout(saveButton)

    const requestPromise = page.waitForRequest(
      (req) => req.method() === 'PUT' && new URL(req.url()).pathname === '/api/articles/1'
    )
    await saveButton.click()
    const body = (await requestPromise).postDataJSON()

    expect(body.headline).toBe('量化投资入门')
    expect(body.type).toBe(101)
    expect(body.drafted).toBe(1)
    expect(body.content).toContain('这是一篇关于量化投资的文章正文')
  })

  // Regression guard for a fixed defect (iteration 17, found by this spec):
  // this UEditor build fires `contentchange` only for programmatic changes
  // (setContent / execCommand / plugin operations) — plain typing never
  // fires it (verified in-browser with listener counters: 0 events after
  // typing, 2 events after an import-dialog insert), and UEditor's event
  // proxy does not forward native `input` events. Listening only to
  // contentChange therefore left manually typed text out of the v-model, so
  // a new article's `content` rule failed with 请输入内容 and manual edits
  // were silently dropped on save. UEditor.vue now also binds native
  // `input` (debounced 300ms) plus a `blur` flush on the editor iframe body.
  test('publishing a new article posts the editor content', async ({ page }) => {
    await loginAs(page, 'user')
    await page.goto('/write')

    await page.getByPlaceholder('请输入文章标题').fill('E2E 新文章')

    await page.locator('.el-cascader').click()
    await page.locator('.el-cascader-panel .el-cascader-node').filter({ hasText: '交易策略' }).first().click()
    await page.locator('.el-cascader-panel .el-cascader-node').filter({ hasText: '股票策略' }).first().click()
    await page.keyboard.press('Escape')

    const editor = page.frameLocator(EDITOR_FRAME)
    await editor.locator('body').click()
    await page.keyboard.type('这是通过编辑器输入的正文。')

    const publishButton = page.getByRole('button', { name: '发布' })
    await waitForStableLayout(publishButton)

    const requestPromise = page.waitForRequest(
      (req) => req.method() === 'POST' && new URL(req.url()).pathname === '/api/articles'
    )
    await publishButton.click()
    const body = (await requestPromise).postDataJSON()

    expect(body.headline).toBe('E2E 新文章')
    expect(body.type).toBe(101)
    expect(body.drafted).toBe(0)
    expect(body.content).toContain('这是通过编辑器输入的正文')
  })
})
