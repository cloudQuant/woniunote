import { test, expect } from './support/test'
import { getMockedApiRequests, loginAs, mockApi } from './support/mockApi'
import {
  EDITOR_IFRAME,
  editorBodyText,
  expectEditorTextToContain,
  focusEditor
} from './support/editor'

const mathJaxUrl = 'https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js'

function waitForApiResponse(page, method, path) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === method && url.pathname === '/api' + path
  })
}

async function completeResponse(responsePromise) {
  const response = await responsePromise
  expect(await response.finished()).toBeNull()
  return response
}

test('UEditor becomes usable after DOMContentLoaded while MathJax still holds window.load', async ({
  page
}, testInfo) => {
  await mockApi(page)
  await loginAs(page)

  let releaseMathJax
  let markMathJaxRequested
  const mathJaxRequestStarted = new Promise((resolve) => {
    markMathJaxRequested = resolve
  })
  const holdMathJax = new Promise((resolve) => {
    releaseMathJax = resolve
  })
  await page.route(mathJaxUrl, async (route) => {
    markMathJaxRequested()
    await holdMathJax
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: 'window.__ueditorTestMathJaxLoadFinished = true'
    })
  })

  await page.addInitScript(() => {
    window.__ueditorTestLifecycle = []
    document.addEventListener('DOMContentLoaded', () => {
      window.__ueditorTestLifecycle.push({
        event: 'DOMContentLoaded',
        readyState: document.readyState,
        time: Math.round(performance.now() * 100) / 100
      })
    }, true)
    window.addEventListener('load', () => {
      window.__ueditorTestLifecycle.push({
        event: 'window.load',
        readyState: document.readyState,
        time: Math.round(performance.now() * 100) / 100
      })
    }, true)
  })

  const typesResponsePromise = waitForApiResponse(page, 'GET', '/articles/types')
  const editorConfigResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === 'GET' && url.pathname === '/api/uedit' &&
      url.searchParams.get('action') === 'config'
  })
  let beforeWindowLoad
  let editorContent
  try {
    await page.goto('/write', { waitUntil: 'domcontentloaded' })
    await mathJaxRequestStarted
    const apiResponses = await Promise.all([
      typesResponsePromise,
      editorConfigResponsePromise
    ].map(completeResponse))
    expect(apiResponses.every((response) => response.status() === 200)).toBe(true)
    await expect(page.locator('.write-article-page')).toBeVisible()

    const whileMathJaxHeld = await page.evaluate(() => ({
      readyState: document.readyState,
      lifecycle: window.__ueditorTestLifecycle || []
    }))
    await testInfo.attach('ueditor-while-mathjax-held.json', {
      body: Buffer.from(JSON.stringify(whileMathJaxHeld, null, 2)),
      contentType: 'application/json'
    })
    console.log('UEDITOR_WHILE_MATHJAX_HELD', JSON.stringify(whileMathJaxHeld))
    expect(whileMathJaxHeld.lifecycle.some((event) => event.event === 'DOMContentLoaded')).toBe(true)
    expect(whileMathJaxHeld.lifecycle.some((event) => event.event === 'window.load')).toBe(false)

    await expect(page.locator('.edui-editor')).toBeVisible()
    await expect(page.locator(EDITOR_IFRAME)).toBeVisible()

    beforeWindowLoad = await page.evaluate((iframeSelector) => {
      const instances = window.UE?.instants && typeof window.UE.instants === 'object'
        ? Object.values(window.UE.instants)
        : []
      const instanceKeys = window.UE?.instants && typeof window.UE.instants === 'object'
        ? Object.keys(window.UE.instants)
        : []
      const iframeIds = Array.from(document.querySelectorAll('.ueditor-container iframe'))
        .map((iframe) => iframe.id)
      const editorIframe = document.querySelector(iframeSelector)
      const editorBody = editorIframe?.contentDocument?.body
      const editor = document.querySelector('.edui-editor')
      return {
        readyState: document.readyState,
        lifecycle: window.__ueditorTestLifecycle || [],
        editorExists: Boolean(editor),
        iframeIds,
        iframeCount: iframeIds.length,
        iframeDocumentReadyState: editorIframe?.contentDocument?.readyState || null,
        contenteditable: editorBody?.getAttribute('contenteditable') || null,
        isContentEditable: editorBody?.isContentEditable || false,
        instanceKeys,
        readyInstanceCount: instances.filter((instance) => instance?.isReady).length
      }
    }, EDITOR_IFRAME)
    await testInfo.attach('ueditor-before-window-load.json', {
      body: Buffer.from(JSON.stringify(beforeWindowLoad, null, 2)),
      contentType: 'application/json'
    })
    console.log('UEDITOR_BEFORE_WINDOW_LOAD', JSON.stringify(beforeWindowLoad))
    expect(beforeWindowLoad.lifecycle.some((event) => event.event === 'DOMContentLoaded')).toBe(true)
    expect(beforeWindowLoad.lifecycle.some((event) => event.event === 'window.load')).toBe(false)
    expect(beforeWindowLoad.readyInstanceCount).toBe(1)
    expect(beforeWindowLoad.iframeCount).toBe(1)
    expect(beforeWindowLoad.contenteditable).toBe('true')
    expect(beforeWindowLoad.isContentEditable).toBe(true)
    await focusEditor(page)
    await page.keyboard.type('ready before window load')
    await expectEditorTextToContain(page, 'ready before window load')
    editorContent = await editorBodyText(page)
    expect(editorContent).toContain('ready before window load')
  } finally {
    const mathJaxResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.origin + url.pathname === mathJaxUrl
    })
    releaseMathJax()
    const mathJaxResponse = await completeResponse(mathJaxResponsePromise)
    expect(mathJaxResponse.status()).toBe(200)
    await page.waitForLoadState('load')
  }

  const afterWindowLoad = await page.evaluate(() => {
    const instances = window.UE?.instants && typeof window.UE.instants === 'object'
      ? Object.values(window.UE.instants)
      : []
    const instanceKeys = window.UE?.instants && typeof window.UE.instants === 'object'
      ? Object.keys(window.UE.instants)
      : []
    const iframeIds = Array.from(document.querySelectorAll('.ueditor-container iframe'))
      .map((iframe) => iframe.id)
      const iframe = document.querySelector('.edui-editor-iframeholder iframe')
    return {
      lifecycle: window.__ueditorTestLifecycle || [],
      iframeIds,
      iframeCount: iframeIds.length,
      instanceKeys,
      readyInstanceCount: instances.filter((instance) => instance?.isReady).length,
      editorContent: iframe?.contentDocument?.body?.innerText || ''
    }
  })
  await testInfo.attach('ueditor-after-window-load.json', {
    body: Buffer.from(JSON.stringify(afterWindowLoad, null, 2)),
    contentType: 'application/json'
  })
  expect(afterWindowLoad.lifecycle.some((event) => event.event === 'window.load')).toBe(true)
  expect(afterWindowLoad.readyInstanceCount).toBe(1)
  expect(afterWindowLoad.iframeCount).toBe(1)
  expect(afterWindowLoad.iframeIds).toEqual(beforeWindowLoad.iframeIds)
  expect(afterWindowLoad.instanceKeys).toEqual(beforeWindowLoad.instanceKeys)
  expect(afterWindowLoad.editorContent).toBe(editorContent)

  expect(getMockedApiRequests(page).map(({ method, path }) => `${method} ${path}`)).toEqual(
    expect.arrayContaining([
      'GET /articles/types',
      'GET /uedit'
    ])
  )
})
