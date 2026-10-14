import { expect } from '@playwright/test'

/**
 * Cross-browser helpers for driving the UEditor editing surface.
 *
 * The editing area is a same-origin iframe (`.edui-editor-iframeholder iframe`).
 * `page.frameLocator(...)` works for Chromium and Firefox but has two measured
 * automation gaps (iteration 20 / Epic 20.2), both of which are Playwright-side
 * rather than product defects — the editor itself works in every engine
 * (verified with real keystrokes and screenshots):
 *
 *  - WebKit: UEditor creates the iframe with a `javascript:` URL. Playwright's
 *    WebKit build never resolves that element through `frameLocator(...)`
 *    (`.contentFrame()` hangs), although the frame is reachable via
 *    `page.frames()` and `iframe.contentDocument`.
 *  - Firefox: clicking the editor body while the iframe is scrolled above the
 *    viewport focuses the frame but the following keystrokes are dropped.
 *
 * These helpers therefore (a) scroll the editor into view, (b) focus the real
 * editing document through `iframe.contentDocument`, and (c) send real
 * keystrokes through `page.keyboard`. Only Playwright's frame plumbing is
 * bypassed; the editor DOM, focus handling and typing path under test are the
 * real ones.
 */
export const EDITOR_IFRAME = '.edui-editor-iframeholder iframe'

/** Read the editing document's body HTML. */
export function editorBodyHtml(page) {
  return page.evaluate((selector) => {
    const frame = document.querySelector(selector)
    if (!frame || !frame.contentDocument || !frame.contentDocument.body) return null
    return frame.contentDocument.body.innerHTML
  }, EDITOR_IFRAME)
}

/** Read the editing document's body text. */
export function editorBodyText(page) {
  return page.evaluate((selector) => {
    const frame = document.querySelector(selector)
    if (!frame || !frame.contentDocument || !frame.contentDocument.body) return null
    return frame.contentDocument.body.innerText
  }, EDITOR_IFRAME)
}

/**
 * Scroll the editor into view and focus its editing document.
 *
 * The blur of the currently focused control is required for Firefox: after
 * interacting with another form control (e.g. the category cascader), Firefox
 * keeps routing `page.keyboard` input to that control even once the iframe
 * document reports focus — measured as "iframe has focus, keystrokes never
 * arrive". Blurring first resets that state.
 */
export async function focusEditor(page) {
  await page.locator(EDITOR_IFRAME).scrollIntoViewIfNeeded()
  await page.evaluate((selector) => {
    if (document.activeElement && typeof document.activeElement.blur === 'function') {
      document.activeElement.blur()
    }
    const frame = document.querySelector(selector)
    frame.contentDocument.body.focus()
  }, EDITOR_IFRAME)
}

/**
 * Focus the editor and type real keystrokes into it, verifying they arrived.
 *
 * Under the full parallel browser matrix (heavy load) the focus transition can
 * race the typing and the keystrokes are dropped without any error — observed
 * as an empty editing document in WebKit and Firefox. The helper verifies the
 * text landed and retries once from a fresh focus state; the retry happens only
 * when the document is still empty, so nothing is ever duplicated. A partial
 * insert is reported as a failure instead of being typed over.
 */
export async function typeInEditor(page, text) {
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    await focusEditor(page)
    await page.keyboard.type(text)
    try {
      await expect.poll(() => editorBodyText(page), { timeout: 2000 }).toContain(text)
      return
    } catch (error) {
      const current = (await editorBodyText(page)) || ''
      if (current.trim() !== '' || attempt === 2) throw error
    }
  }
}

/** Wait until the editing document's HTML contains `substring`. */
export function expectEditorHtmlToContain(page, substring) {
  return expect
    .poll(() => editorBodyHtml(page), { timeout: 5000 })
    .toContain(substring)
}

/** Wait until the editing document's HTML does NOT contain `substring`. */
export function expectEditorHtmlNotToContain(page, substring) {
  return expect
    .poll(async () => (await editorBodyHtml(page)) ?? '', { timeout: 5000 })
    .not.toContain(substring)
}

/** Wait until the editing document's text contains `substring`. */
export function expectEditorTextToContain(page, substring) {
  return expect
    .poll(async () => (await editorBodyText(page)) ?? '', { timeout: 5000 })
    .toContain(substring)
}
