import { expect, test } from '@playwright/test'
import { randomUUID } from 'node:crypto'

const password = 'Iter21!StrongPass'
const runId = process.env.WONIUNOTE_TEST_RUN_ID || ''
const backendTarget = process.env.WONIUNOTE_API_PROXY_TARGET || ''
const frontendOrigin = new URL(process.env.WONIUNOTE_REAL_E2E_URL).origin

async function expectAuthRedirect(page, pathname) {
  await expect(page).toHaveURL((candidate) =>
    candidate.origin === frontendOrigin &&
    candidate.pathname === pathname &&
    candidate.searchParams.size === 1 &&
    candidate.searchParams.get('redirect') === '/math-training' &&
    candidate.hash === ''
  )
}

function uniqueUsername(prefix) {
  return `${prefix}_${randomUUID().replaceAll('-', '').slice(0, 16)}`
}

function captchaResponse(response) {
  return response.url().endsWith('/api/captcha/generate') &&
    response.request().method() === 'GET'
}

async function readLiveCaptcha(page, captchaId) {
  expect(runId).toMatch(/^\d{8}T\d{6}Z-[0-9a-f]{12}$/)
  const peek = await page.request.post(
    new URL('/api/captcha/test/challenge', backendTarget).toString(),
    {
      headers: { 'X-Woniunote-Test-Run': runId },
      data: { captcha_id: captchaId }
    }
  )
  expect(peek.status()).toBe(200)
  const envelope = await peek.json()
  expect(envelope.code).toBe(200)
  expect(envelope.data.captcha_id).toBe(captchaId)
  expect(envelope.data.expired).toBe(false)
  expect(envelope.data.captcha_code).toMatch(/^[A-Z2-9]{4}$/)
  return envelope.data.captcha_code
}

async function registration(page, username, nickname) {
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入昵称（可选）').fill(nickname)
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.getByPlaceholder('请再次输入密码').fill(password)

  const responsePromise = page.waitForResponse((response) =>
    response.url().endsWith('/api/auth/register') && response.request().method() === 'POST'
  )
  await page.getByRole('button', { name: '注册' }).click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  expect((await response.json()).code).toBe(200)
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/)
}

async function completeLogin(page, username, { modal = false } = {}) {
  const generatedCaptchaPromise = page.waitForResponse(captchaResponse)
  if (modal) {
    await page.locator('button.login-link').click()
  } else {
    // Navigating to the login page mounts the real login form and requests a
    // one-time challenge from the backend.
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
  }
  const challengeResponse = await generatedCaptchaPromise
  expect(challengeResponse.status()).toBe(200)
  const challengeBody = await challengeResponse.json()
  expect(challengeBody.code).toBe(200)
  const captchaId = challengeBody.data.captcha_id
  expect(captchaId).toBeTruthy()
  await expect(page.locator(modal ? 'img.captcha-img' : 'img.captcha-image')).toBeVisible()
  const captchaCode = await readLiveCaptcha(page, captchaId)

  const usernameInput = page.getByPlaceholder('请输入用户名').last()
  const passwordInput = page.getByPlaceholder(modal ? '请输入你的登录密码' : '请输入密码')
  const captchaInput = page.getByPlaceholder(modal ? '请输入右侧的验证码' : '请输入验证码')
  await usernameInput.fill(username)
  await passwordInput.fill(password)
  await captchaInput.fill(captchaCode)

  const loginResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith('/api/auth/login') && response.request().method() === 'POST'
  )
  if (modal) {
    await page.locator('.login-dialog').getByRole('button', { name: '登录' }).click()
  } else {
    await page.locator('.login-btn').click()
  }
  const loginResponse = await loginResponsePromise
  expect(loginResponse.status()).toBe(200)
  const loginBody = await loginResponse.json()
  expect(loginBody.code).toBe(200)
  expect(loginBody.data.access_token).toBeTruthy()
  expect(loginBody.data.refresh_token).toBeTruthy()
  return {
    accessToken: loginBody.data.access_token,
    refreshToken: loginBody.data.refresh_token
  }
}

async function logoutFromUi(page) {
  const logoutResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith('/api/auth/logout') && response.request().method() === 'POST'
  )
  await page.locator('.user-link').click()
  await page.getByText('退出登录', { exact: true }).click()
  const logoutResponse = await logoutResponsePromise
  expect(logoutResponse.status()).toBe(200)
  await expect(page.locator('.user-link')).toHaveCount(0)
  await expect(page.locator('.login-link')).toBeVisible()
}

test('protected-page registration redirect logs in with an ordinary username and revokes its session', async ({ page }) => {
  const username = uniqueUsername('iter21')

  await page.goto('/math-training', { waitUntil: 'domcontentloaded' })
  await expectAuthRedirect(page, '/login')
  await page.getByRole('link', { name: '立即注册' }).click()
  await expectAuthRedirect(page, '/register')

  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入昵称（可选）').fill('Iter21 redirect')
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.getByPlaceholder('请再次输入密码').fill(password)
  const registrationResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith('/api/auth/register') && response.request().method() === 'POST'
  )
  const generatedCaptchaPromise = page.waitForResponse(captchaResponse)
  await page.getByRole('button', { name: '注册' }).click()
  const registrationResponse = await registrationResponsePromise
  expect(registrationResponse.status()).toBe(200)
  expect((await registrationResponse.json()).code).toBe(200)
  await expectAuthRedirect(page, '/login')

  const challengeResponse = await generatedCaptchaPromise
  expect(challengeResponse.status()).toBe(200)
  const captchaId = (await challengeResponse.json()).data.captcha_id
  const captchaCode = await readLiveCaptcha(page, captchaId)
  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.getByPlaceholder('请输入验证码').fill(captchaCode)

  const loginResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith('/api/auth/login') && response.request().method() === 'POST'
  )
  await page.locator('.login-btn').click()
  const loginResponse = await loginResponsePromise
  expect(loginResponse.status()).toBe(200)
  const loginBody = await loginResponse.json()
  expect(loginBody.code).toBe(200)
  const loginTokens = {
    accessToken: loginBody.data.access_token,
    refreshToken: loginBody.data.refresh_token
  }
  expect(loginTokens.accessToken).toBeTruthy()
  expect(loginTokens.refreshToken).toBeTruthy()
  await expect(page).toHaveURL((candidate) => candidate.pathname === '/math-training')

  const refreshResponse = await page.request.post(new URL('/api/auth/refresh', backendTarget).toString(), {
    data: { refresh_token: loginTokens.refreshToken }
  })
  expect(refreshResponse.status()).toBe(200)
  const refreshBody = await refreshResponse.json()
  expect(refreshBody.code).toBe(200)
  expect(refreshBody.data.access_token).toBeTruthy()
  expect(refreshBody.data.refresh_token).toBeTruthy()
  expect(refreshBody.data.refresh_token).not.toBe(loginTokens.refreshToken)

  const logoutResponse = await page.request.post(new URL('/api/auth/logout', backendTarget).toString(), {
    headers: { Authorization: `Bearer ${refreshBody.data.access_token}` },
    data: { refresh_token: refreshBody.data.refresh_token }
  })
  expect(logoutResponse.status()).toBe(200)
  const afterLogout = await page.request.post(new URL('/api/auth/refresh', backendTarget).toString(), {
    data: { refresh_token: refreshBody.data.refresh_token }
  })
  expect(afterLogout.status()).toBe(401)
})

test('standalone login page accepts an email-style username and UI logout revokes its session', async ({ page }) => {
  const username = `iter21+${randomUUID().replaceAll('-', '').slice(0, 12)}@example.test`
  await registration(page, username, 'Iter21 email page')
  const loginTokens = await completeLogin(page, username)
  await expect(page).toHaveURL((candidate) => candidate.pathname === '/')
  await logoutFromUi(page)

  const refreshAfterLogout = await page.request.post(
    new URL('/api/auth/refresh', backendTarget).toString(),
    { data: { refresh_token: loginTokens.refreshToken } }
  )
  expect(refreshAfterLogout.status()).toBe(401)
})

for (const usernameKind of ['ordinary', 'email-style']) {
  test(`header login modal accepts a ${usernameKind} username and UI logout revokes its session`, async ({ page }) => {
    const username = usernameKind === 'ordinary'
      ? uniqueUsername('iter21_modal')
      : `iter21+${randomUUID().replaceAll('-', '').slice(0, 12)}@example.test`
    const nickname = `Iter21 ${usernameKind}`
    await registration(page, username, nickname)
    await page.locator('a.logo').click()
    await expect(page).toHaveURL((candidate) => candidate.pathname === '/')

    const loginTokens = await completeLogin(page, username, { modal: true })
    await expect(page.locator('.login-dialog')).toBeHidden()
    await expect(page.locator('.user-link')).toContainText(nickname)

    await logoutFromUi(page)
    const refreshAfterLogout = await page.request.post(
      new URL('/api/auth/refresh', backendTarget).toString(),
      { data: { refresh_token: loginTokens.refreshToken } }
    )
    expect(refreshAfterLogout.status()).toBe(401)
  })
}
