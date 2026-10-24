import { test, expect } from './support/test'
import { performance } from 'node:perf_hooks'
import {
  fixtures,
  getMockedApiRequests,
  getUnexpectedApiRequests,
  loginAs,
  mockApi
} from './support/mockApi'

function deferred() {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}

function isRefreshRequest(request) {
  return new URL(request.url()).pathname === '/api/auth/refresh'
}

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

function isMyArticlesRequest(request) {
  return new URL(request.url()).pathname === '/api/articles/my'
}

function statusResponse(status, message) {
  return { __status: status, payload: { code: status, message } }
}

async function readDurableSession(page) {
  return page.evaluate(() => new Promise((resolve, reject) => {
    const open = indexedDB.open('woniunote-auth-session', 1)
    open.onerror = () => reject(open.error || new Error('IndexedDB open failed'))
    open.onsuccess = () => {
      const database = open.result
      const transaction = database.transaction('sessions', 'readonly')
      const request = transaction.objectStore('sessions').get('current')
      let session = null
      request.onsuccess = () => { session = request.result }
      request.onerror = () => reject(request.error || new Error('IndexedDB read failed'))
      transaction.oncomplete = () => {
        database.close()
        resolve(session)
      }
      transaction.onerror = () => reject(transaction.error || new Error('IndexedDB transaction failed'))
    }
  }))
}

test.describe('Authentication across tabs', () => {
  test.describe.configure({ retries: 0 })

  test('late refresh in one tab cannot restore or replay after another tab logs out and signs in as a new user', async ({ page }) => {
    test.setTimeout(60000)

    const refreshStarted = deferred()
    const releaseRefresh = deferred()
    const refreshNetwork = {
      requestStartedAt: null,
      requestFailed: [],
      responseReceivedAt: null,
      requestFinishedAt: null
    }
    let mockRefreshStartedAt = null
    const refreshEnvelope = {
      code: 200,
      message: 'success',
      data: { access_token: 'late-old-access', refresh_token: 'late-old-refresh' }
    }
    await mockApi(page, {
      overrides: {
        'GET /articles/my': {
          __status: 401,
          payload: { code: 401, message: '旧会话已过期' }
        },
        'POST /auth/refresh': async () => {
          mockRefreshStartedAt = performance.now()
          refreshStarted.resolve()
          return releaseRefresh.promise
        }
      }
    })
    const pageB = await page.context().newPage()
    page.on('request', (request) => {
      if (isRefreshRequest(request)) refreshNetwork.requestStartedAt = performance.now()
    })
    page.on('requestfailed', (request) => {
      if (isRefreshRequest(request)) {
        refreshNetwork.requestFailed.push({
          at: performance.now(),
          errorText: request.failure()?.errorText || ''
        })
      }
    })
    page.on('response', (response) => {
      if (isRefreshRequest(response.request())) refreshNetwork.responseReceivedAt = performance.now()
    })
    page.on('requestfinished', (request) => {
      if (isRefreshRequest(request)) refreshNetwork.requestFinishedAt = performance.now()
    })
    let browserLockPromise
    let lockHeld = false

    try {
      await mockApi(pageB)
      await loginAs(page, 'user')
      await loginAs(pageB, 'user')
      // Initialize B first, so it is ready to perform the account switch as
      // soon as A's deliberately delayed refresh starts.
      await pageB.goto('/user/articles', { waitUntil: 'domcontentloaded' })
      await expect(pageB.locator('.user-link')).toContainText('tester')
      // Prepare B's real logout dropdown before A starts the held refresh.
      await pageB.bringToFront()
      await pageB.locator('.user-link').click()
      await expect(pageB.getByText('退出登录', { exact: true })).toBeVisible()

      const refreshRequestPromise = page.waitForRequest(isRefreshRequest, { timeout: 10000 })
      await page.goto('/user/articles', { waitUntil: 'domcontentloaded' })
      await refreshStarted.promise
      const refreshRequest = await refreshRequestPromise
      expect(refreshNetwork.requestStartedAt).not.toBeNull()
      expect(mockRefreshStartedAt).not.toBeNull()
      const initialArticleRequestCount = getMockedApiRequests(page).filter((request) =>
        request.method === 'GET' && request.path === '/articles/my'
      ).length
      expect(initialArticleRequestCount).toBeGreaterThan(0)

      expect(await page.evaluate(() => typeof navigator.locks?.request)).toBe('function')
      expect(await pageB.evaluate(() => typeof navigator.locks?.request)).toBe('function')

      // Bring tab B back to the foreground for its timed logout and login actions.
      await pageB.bringToFront()
      await expect.poll(() => pageB.evaluate(() => document.visibilityState)).toBe('visible')

      // Hold the real browser lock while tab B begins logout. Its canonical
      // session must not clear until the lock is released.
      browserLockPromise = page.evaluate(() => navigator.locks.request(
        'woniunote:auth-session-lock',
        () => new Promise((resolve) => {
          window.__iter21AuthLockHeld = true
          window.__iter21ReleaseAuthLock = resolve
        })
      ))
      await expect.poll(() => page.evaluate(() => window.__iter21AuthLockHeld === true)).toBe(true)
      lockHeld = true

      await pageB.getByText('退出登录', { exact: true }).click()
      await expect(pageB).toHaveURL(/\/$/)
      await expect.poll(() => readDurableSession(pageB))
        .toMatchObject({ token: 'e2e-access', refreshToken: 'e2e-refresh' })

      await page.evaluate(() => window.__iter21ReleaseAuthLock())
      await browserLockPromise
      lockHeld = false

      await expect(pageB.locator('.login-link')).toBeVisible()
      await expect.poll(() => readDurableSession(pageB))
        .toMatchObject({ token: '', refreshToken: '', user: null })

      // Use the real Header modal so B's Pinia login action creates the new
      // epoch. B is already on Home after logout, avoiding a fresh page load
      // while A's five-second refresh request is held open.
      await pageB.locator('.login-link').click()
      const loginDialog = pageB.locator('.login-dialog')
      await loginDialog.getByPlaceholder('请输入用户名').fill('admin@example.com')
      await loginDialog.getByPlaceholder('请输入你的登录密码').fill('secret123')
      await loginDialog.getByPlaceholder('请输入右侧的验证码').fill('1234')
      await loginDialog.locator('.login-footer .el-button--primary').click()
      await expect.poll(() => readDurableSession(pageB))
        .toMatchObject({ token: 'e2e-access', user: { userid: 99, nickname: 'admin' } })
      const newSession = await readDurableSession(pageB)
      expect(newSession.user).toMatchObject({ userid: 99, nickname: 'admin' })
      expect(newSession.token).toBe('e2e-access')
      const newEpochPersistedAt = performance.now()
      expect(refreshNetwork.requestStartedAt).toBeLessThan(newEpochPersistedAt)
      expect(mockRefreshStartedAt).toBeLessThan(newEpochPersistedAt)

      // Release A's old response only after B's new epoch is durable in the
      // authoritative IndexedDB record. Local storage only announces changes.
      const refreshResponsePromise = page.waitForResponse(
        (response) => isRefreshRequest(response.request()),
        { timeout: 5000 }
      )
      const refreshReleasedAt = performance.now()
      expect(refreshReleasedAt - refreshNetwork.requestStartedAt).toBeLessThan(5000)
      releaseRefresh.resolve(refreshEnvelope)
      const refreshResponse = await refreshResponsePromise
      const refreshFinishError = await refreshResponse.finished()
      const refreshResponsePayload = await refreshResponse.json()
      expect(refreshResponse.status()).toBe(200)
      expect(refreshResponsePayload).toEqual(refreshEnvelope)
      expect(refreshFinishError).toBeNull()
      expect(refreshNetwork.requestFailed).toEqual([])
      expect(refreshRequest.failure()).toBeNull()
      expect(refreshNetwork.requestFinishedAt).not.toBeNull()
      expect(refreshNetwork.responseReceivedAt).toBeGreaterThanOrEqual(refreshReleasedAt)
      expect(refreshNetwork.responseReceivedAt).toBeGreaterThan(newEpochPersistedAt)
      expect(refreshNetwork.requestFinishedAt - refreshNetwork.requestStartedAt).toBeLessThan(5000)
      await expect(loginDialog).toBeHidden()
      await expect(pageB.locator('.user-link')).toContainText('admin')
      await expect(page.locator('.user-link')).toContainText('admin')
      await expect(page.getByText('登录已过期，请重新登录').first()).toBeVisible()
      await expect(page).toHaveURL(/\/user\/articles$/)

      const settledSession = await readDurableSession(page)
      expect(settledSession).toMatchObject({
        epoch: newSession.epoch,
        token: 'e2e-access',
        refreshToken: 'e2e-refresh',
        user: { userid: 99, nickname: 'admin' }
      })
      const articleRequests = getMockedApiRequests(page).filter((request) =>
        request.method === 'GET' && request.path === '/articles/my'
      )
      expect(articleRequests).toHaveLength(initialArticleRequestCount)
      expect(getUnexpectedApiRequests(pageB)).toEqual([])
    } finally {
      if (lockHeld) {
        await page.evaluate(() => window.__iter21ReleaseAuthLock?.())
        await browserLockPromise
      }
      releaseRefresh.resolve(refreshEnvelope)
      await pageB.close()
    }
  })

  test('serializes concurrent same-session refreshes across Pinia tabs and replays both requests with rotated credentials', async ({ page }) => {
    test.setTimeout(60000)

    const bothInitialRequests = deferred()
    const firstRefreshStarted = deferred()
    const secondRefreshStarted = deferred()
    const refreshResponses = [deferred(), deferred()]
    const scenario = {
      initialArticleRequests: [],
      articleAttempts: [],
      refreshRequests: []
    }
    const optionsForTab = (tab, browserPage) => ({
      overrides: {
        'GET /articles/my': async (request) => {
          const authorization = request.headers().authorization || ''
          const attempt = { tab, authorization }
          scenario.articleAttempts.push(attempt)
          const priorAttempts = scenario.articleAttempts.filter((attempt) => attempt.tab === tab).length
          if (priorAttempts === 1) {
            attempt.status = 401
            scenario.initialArticleRequests.push(tab)
            if (scenario.initialArticleRequests.length === 2) bothInitialRequests.resolve()
            await bothInitialRequests.promise
            return statusResponse(401, 'access token expired')
          }
          attempt.status = 200
          return {
            code: 200,
            message: 'success',
            data: fixtures.articleList.data,
            total: fixtures.articleList.data.length,
            page: 1,
            page_size: 10
          }
        },
        'POST /auth/refresh': async (request) => {
          const index = scenario.refreshRequests.length
          const canonical = await readDurableSession(browserPage)
          scenario.refreshRequests.push({
            tab,
            at: Date.now(),
            body: request.postDataJSON(),
            canonicalEpoch: canonical.epoch,
            canonicalVersion: canonical.version,
            canonicalAlreadyRotated: canonical.token === 'rotated-access'
          })
          if (index === 0) firstRefreshStarted.resolve()
          if (index === 1) secondRefreshStarted.resolve()
          if (index > 1) return statusResponse(500, 'unexpected extra refresh')
          return refreshResponses[index].promise
        }
      }
    })

    const pageB = await page.context().newPage()
    let mutationLockPromise
    let mutationLockHeld = false

    try {
      await Promise.all([mockApi(page, optionsForTab('A', page)), mockApi(pageB, optionsForTab('B', pageB))])
      await Promise.all([loginAs(page, 'user'), loginAs(pageB, 'user')])
      await Promise.all([page.goto('/', { waitUntil: 'domcontentloaded' }), pageB.goto('/', { waitUntil: 'domcontentloaded' })])
      await expect(page.locator('.user-link')).toContainText('tester')
      await expect(pageB.locator('.user-link')).toContainText('tester')
      const initialSessions = await Promise.all([page, pageB].map(readDurableSession))
      expect(initialSessions[0]).toMatchObject({
        epoch: initialSessions[1].epoch,
        token: 'e2e-access',
        refreshToken: 'e2e-refresh',
        user: { userid: 1, nickname: 'tester' }
      })

      // Hold the existing session-mutation lock so the two candidate refresh
      // outcomes can be delivered deterministically before a token write.
      mutationLockPromise = page.evaluate(() => navigator.locks.request(
        'woniunote:auth-session-lock',
        () => new Promise((resolve) => {
          window.__iter21MutationLockHeld = true
          window.__iter21ReleaseMutationLock = resolve
        })
      ))
      await expect.poll(() => page.evaluate(() => window.__iter21MutationLockHeld === true)).toBe(true)
      mutationLockHeld = true

      const initial401Responses = Promise.all([page, pageB].map((tab) =>
        tab.waitForResponse((response) => isMyArticlesRequest(response.request()) && response.status() === 401)
      ))
      const openMyArticles = async (tab) => {
        await tab.locator('.user-link').click()
        await tab.getByText('我的文章', { exact: true }).click()
        await expect(tab).toHaveURL(/\/user\/articles$/)
      }
      await Promise.all([openMyArticles(page), openMyArticles(pageB)])
      await initial401Responses
      await firstRefreshStarted.promise
      await expect.poll(async () => page.evaluate(async () => {
        const locks = await navigator.locks.query()
        return locks.pending.filter((lock) => lock.name === 'woniunote:auth-refresh-lock').length
      })).toBe(1)

      // On the unfixed implementation, each tab issues a refresh. Deliver the
      // losing 401 first, queueing its clear ahead of the winner's token write.
      // With the cross-tab refresh lock, the second call cannot exist yet.
      const secondRefreshArrived = await Promise.race([
        secondRefreshStarted.promise.then(() => true),
        new Promise((resolve) => setTimeout(() => resolve(false), 500))
      ])
      if (secondRefreshArrived) {
        refreshResponses[1].resolve(statusResponse(401, 'refresh token already rotated'))
        await expect.poll(async () => page.evaluate(async () => {
          const locks = await navigator.locks.query()
          return locks.pending.filter((lock) => lock.name === 'woniunote:auth-session-lock').length
        })).toBeGreaterThan(0)
      }

      refreshResponses[0].resolve({
        code: 200,
        message: 'success',
        data: { access_token: 'rotated-access', refresh_token: 'rotated-refresh' }
      })
      await expect.poll(async () => page.evaluate(async () => {
        const locks = await navigator.locks.query()
        return locks.pending.filter((lock) => lock.name === 'woniunote:auth-session-lock').length
      })).toBeGreaterThan(secondRefreshArrived ? 1 : 0)

      await page.evaluate(() => window.__iter21ReleaseMutationLock())
      await mutationLockPromise
      mutationLockHeld = false

      // On the old per-tab-only implementation the losing 401 is queued
      // before the winner's token commit and clears this shared session.
      // Assert the durable result first so the baseline failure identifies
      // the involuntary logout rather than a later page-render timeout.
      await expect.poll(() => readDurableSession(page), { timeout: 3000 })
        .toMatchObject({ token: 'rotated-access', refreshToken: 'rotated-refresh' })

      for (const tab of [page, pageB]) {
        await expect.poll(() => getMockedApiRequests(tab).filter((request) =>
          request.method === 'GET' && request.path === '/articles/my'
        ).length >= 2).toBe(true)
      }
      await expect(page.locator('.user-link')).toContainText('tester')
      await expect(pageB.locator('.user-link')).toContainText('tester')

      expect(scenario.refreshRequests).toHaveLength(1)
      expect(scenario.refreshRequests[0].body).toEqual({ refresh_token: 'e2e-refresh' })
      for (const tab of ['A', 'B']) {
        const attempts = scenario.articleAttempts.filter((attempt) => attempt.tab === tab)
        expect(attempts.length).toBeGreaterThanOrEqual(2)
        expect(attempts.filter((attempt) => attempt.status === 401)).toEqual([
          { tab, authorization: 'Bearer e2e-access', status: 401 }
        ])
        expect(attempts.filter((attempt) => attempt.authorization === 'Bearer rotated-access')).toEqual([
          { tab, authorization: 'Bearer rotated-access', status: 200 }
        ])
        expect(attempts.every((attempt) =>
          attempt.authorization === 'Bearer e2e-access' || attempt.authorization === 'Bearer rotated-access'
        )).toBe(true)
      }
      const finalSessions = await Promise.all([page, pageB].map(readDurableSession))
      expect(finalSessions[0]).toMatchObject({
        epoch: initialSessions[0].epoch,
        token: 'rotated-access',
        refreshToken: 'rotated-refresh',
        user: { userid: 1, nickname: 'tester' }
      })
      expect(finalSessions[1]).toMatchObject({
        epoch: initialSessions[0].epoch,
        token: 'rotated-access',
        refreshToken: 'rotated-refresh',
        user: { userid: 1, nickname: 'tester' }
      })
      const durableSessions = await Promise.all([page, pageB].map(readDurableSession))
      expect(durableSessions[0]).toMatchObject({
        epoch: initialSessions[0].epoch,
        token: 'rotated-access',
        refreshToken: 'rotated-refresh',
        user: { userid: 1, nickname: 'tester' }
      })
      expect(durableSessions[1]).toEqual(durableSessions[0])
      expect(getUnexpectedApiRequests(page)).toEqual([])
      expect(getUnexpectedApiRequests(pageB)).toEqual([])
    } finally {
      if (mutationLockHeld) {
        await page.evaluate(() => window.__iter21ReleaseMutationLock?.())
        await mutationLockPromise
      }
      for (const response of refreshResponses) {
        response.resolve(statusResponse(401, 'test cleanup'))
      }
      await pageB.close()
    }
  })

  test('fails closed on IndexedDB errors without reviving legacy credentials or blocking public APIs', async ({ page }) => {
    const publicApiRequests = []
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (url.pathname.startsWith('/api/')) {
        publicApiRequests.push({ path: url.pathname, authorization: request.headers().authorization || '' })
      }
    })
    await mockApi(page)
    await page.addInitScript(() => {
      const staleSession = {
        epoch: 'legacy-stale-epoch', version: 'legacy-stale-version',
        token: 'legacy-stale-access', refreshToken: 'legacy-stale-refresh',
        user: { userid: 77, username: 'former@example.com', nickname: 'former', role: 'admin' }
      }
      localStorage.setItem('woniunote:auth-session', JSON.stringify(staleSession))
      localStorage.setItem('token', staleSession.token)
      localStorage.setItem('refreshToken', staleSession.refreshToken)
      localStorage.setItem('user', JSON.stringify(staleSession.user))
      Object.defineProperty(IDBFactory.prototype, 'open', {
        configurable: true,
        value() { throw new Error('IndexedDB unavailable in this test') }
      })
    })

    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
    await expect(page.locator('.login-link')).toBeVisible()
    expect(await page.locator('.user-link').count()).toBe(0)
    expect(publicApiRequests.length).toBeGreaterThan(0)
    expect(publicApiRequests.every((request) => !request.authorization)).toBe(true)

    const protectedLoginCaptchaPromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/write', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/login/)
    expect((await completeResponse(protectedLoginCaptchaPromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    await page.getByPlaceholder('请输入用户名').fill('former@example.com')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请输入验证码').fill('1234')
    const captchaRefreshPromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.locator('.login-btn').click()
    expect((await completeResponse(captchaRefreshPromise)).status()).toBe(200)
    await expect(page.getByText('安全登录会话存储不可用，请刷新页面后重试', { exact: true })).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
    expect(getMockedApiRequests(page).some((request) =>
      request.method === 'POST' && request.path === '/auth/login'
    )).toBe(false)
    expect(publicApiRequests.every((request) => !request.authorization)).toBe(true)
    expect(getUnexpectedApiRequests(page)).toEqual([])
  })
})
