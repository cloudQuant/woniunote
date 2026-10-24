import { test, expect } from './support/test'
import { getMockedApiRequests, mockApi, loginAs } from './support/mockApi'

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

function waitForHomeResponses(page) {
  return [
    waitForApiResponse(page, 'GET', '/articles'),
    waitForApiResponse(page, 'GET', '/articles/hot')
  ]
}

test.describe('Authentication', () => {
  test.describe.configure({ retries: 0 })

  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('login page renders the form', async ({ page }) => {
    const captchaResponsePromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('.login-title')).toContainText('登录')
    await expect(page.getByPlaceholder('请输入用户名')).toBeVisible()
    await expect(page.getByPlaceholder('请输入密码')).toBeVisible()
    await expect(page.getByPlaceholder('请输入验证码')).toBeVisible()
    expect((await completeResponse(captchaResponsePromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
  })

  test('successful login redirects home and persists session', async ({ page }) => {
    const captchaResponsePromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    expect((await completeResponse(captchaResponsePromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    await page.getByPlaceholder('请输入用户名').fill('tester@example.com')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请输入验证码').fill('1234')
    const loginResponsePromise = waitForApiResponse(page, 'POST', '/auth/login')
    const homeResponsePromises = waitForHomeResponses(page)
    // Submit via the form's own button (the header now also has a "登录"
    // entry button after the R11 keyboard-accessibility change).
    await page.locator('.login-btn').click()
    const [loginResponse, articlesResponse, hotResponse] = await Promise.all([
      loginResponsePromise,
      ...homeResponsePromises
    ].map(completeResponse))
    expect(loginResponse.status()).toBe(200)
    expect(articlesResponse.status()).toBe(200)
    expect(hotResponse.status()).toBe(200)
    await expect(page).toHaveURL(/\/$|\/page/)
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBe('e2e-access')
    const login = getMockedApiRequests(page).find((request) => request.method === 'POST' && request.path === '/auth/login')
    expect(login.body).toMatchObject({
      username: 'tester@example.com',
      password: 'secret123',
      captcha_id: 'cap-1',
      captcha_code: '1234'
    })
  })

  test('accepts a regular username through the page login entry', async ({ page }) => {
    const captchaResponsePromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    expect((await completeResponse(captchaResponsePromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    await page.getByPlaceholder('请输入用户名').fill('tester')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请输入验证码').fill('1234')
    const loginResponsePromise = waitForApiResponse(page, 'POST', '/auth/login')
    const homeResponsePromises = waitForHomeResponses(page)
    await page.locator('.login-btn').click()
    const [loginResponse, articlesResponse, hotResponse] = await Promise.all([
      loginResponsePromise,
      ...homeResponsePromises
    ].map(completeResponse))
    expect(loginResponse.status()).toBe(200)
    expect(articlesResponse.status()).toBe(200)
    expect(hotResponse.status()).toBe(200)
    await expect(page).toHaveURL(/\/$|\/page/)
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
    expect(getMockedApiRequests(page).find((request) => request.path === '/auth/login').body.username).toBe('tester')
  })

  test('failed login keeps the user on the login page', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    // The first captcha is loaded asynchronously on mount. Wait until its
    // image is applied so the request registered below can only observe the
    // refresh caused by the failed login.
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    const initialCaptchaCount = getMockedApiRequests(page)
      .filter((request) => request.path === '/captcha/generate').length
    expect(initialCaptchaCount).toBe(1)

    const loginResponse = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === '/api/auth/login' && response.request().method() === 'POST'
    })
    const captchaRefreshResponse = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === '/api/captcha/generate' && response.request().method() === 'GET'
    })
    await page.getByPlaceholder('请输入用户名').fill('tester@example.com')
    await page.getByPlaceholder('请输入密码').fill('wrongpass')
    await page.getByPlaceholder('请输入验证码').fill('1234')
    // Submit via the form's own button (the header now also has a "登录"
    // entry button after the R11 keyboard-accessibility change).
    await page.locator('.login-btn').click()

    const [failedLoginResponse] = await Promise.all([
      loginResponse,
      captchaRefreshResponse
    ].map(completeResponse))
    expect(failedLoginResponse.status()).toBe(401)
    await expect(page.getByRole('alert')).toContainText('用户名或密码错误')
    // Stays on login; no token stored.
    await expect(page).toHaveURL(/\/login/)
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBeNull()
    expect(getMockedApiRequests(page).filter((request) => request.path === '/captcha/generate'))
      .toHaveLength(initialCaptchaCount + 1)
    expect(getMockedApiRequests(page).find((request) => request.path === '/auth/login').body)
      .toMatchObject({
        username: 'tester@example.com', password: 'wrongpass',
        captcha_id: 'cap-1', captcha_code: '1234'
      })
    await expect(page.getByPlaceholder('请输入用户名')).toHaveValue('tester@example.com')
    await expect(page.getByPlaceholder('请输入验证码')).toHaveValue('')
  })

  test('header login entry sends the same username, password, and captcha contract', async ({ page }) => {
    const homeResponsePromises = waitForHomeResponses(page)
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    const homeResponses = await Promise.all(homeResponsePromises.map(completeResponse))
    expect(homeResponses.every((response) => response.status() === 200)).toBe(true)
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
    const captchaResponsePromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.locator('.login-link').click()
    const dialog = page.locator('.login-dialog')
    expect((await completeResponse(captchaResponsePromise)).status()).toBe(200)
    await expect(dialog.locator('.captcha-img')).toHaveAttribute('src', /^data:image\/png/)
    await dialog.getByPlaceholder('请输入用户名').fill('tester')
    await dialog.getByPlaceholder('请输入你的登录密码').fill('secret123')
    const captcha = dialog.getByPlaceholder('请输入右侧的验证码')
    await expect(captcha).toBeVisible()
    await captcha.fill('1234')
    const loginResponsePromise = waitForApiResponse(page, 'POST', '/auth/login')
    await dialog.locator('.login-footer .el-button--primary').click()
    expect((await completeResponse(loginResponsePromise)).status()).toBe(200)
    await expect(dialog).toBeHidden()
    expect(getMockedApiRequests(page).find((request) => request.path === '/auth/login').body).toMatchObject({
      username: 'tester',
      password: 'secret123',
      captcha_id: 'cap-1',
      captcha_code: '1234'
    })
  })

  test('register page renders and links back to login', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('.register-title')).toContainText('注册')
    await expect(page.getByRole('link', { name: '立即登录' })).toBeVisible()
  })

  test('register validation blocks mismatched passwords', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'domcontentloaded' })
    await page.getByPlaceholder('请输入用户名').fill('newuser')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请再次输入密码').fill('different')
    await page.getByRole('button', { name: '注册' }).click()
    // Inline validation error appears; we stay on the register page.
    await expect(page).toHaveURL(/\/register/)
    await expect(page.getByText('两次输入密码不一致')).toBeVisible()
  })

  test('preserves a protected deep link through register and then login', async ({ page }) => {
    const protectedLoginCaptchaPromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/write', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/login\?redirect=/)
    expect((await completeResponse(protectedLoginCaptchaPromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    await page.getByRole('link', { name: '立即注册' }).click()
    await expect(page).toHaveURL(/\/register\?redirect=/)
    await page.getByPlaceholder('请输入用户名').fill('newuser')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请再次输入密码').fill('secret123')
    const registerResponsePromise = waitForApiResponse(page, 'POST', '/auth/register')
    const postRegisterCaptchaPromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.getByRole('button', { name: '注册' }).click()
    expect((await completeResponse(registerResponsePromise)).status()).toBe(200)
    await expect(page).toHaveURL(/\/login\?redirect=/)
    expect((await completeResponse(postRegisterCaptchaPromise)).status()).toBe(200)
    await expect(page.locator('.captcha-image')).toHaveAttribute('src', /^data:image\/png/)
    await page.getByPlaceholder('请输入用户名').fill('newuser')
    await page.getByPlaceholder('请输入密码').fill('secret123')
    await page.getByPlaceholder('请输入验证码').fill('1234')
    const loginResponsePromise = waitForApiResponse(page, 'POST', '/auth/login')
    const editorConfigResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return response.request().method() === 'GET' && url.pathname === '/api/uedit' &&
        url.searchParams.get('action') === 'config'
    })
    await page.locator('.login-btn').click()
    const [loginResponse, editorConfigResponse] = await Promise.all([
      loginResponsePromise,
      editorConfigResponsePromise
    ].map(completeResponse))
    expect(loginResponse.status()).toBe(200)
    expect(editorConfigResponse.status()).toBe(200)
    await expect(page).toHaveURL(/\/write$/)
    await expect(page.locator('.write-article-page')).toBeVisible()
    await expect(page.locator('.edui-editor')).toBeVisible()
  })

  test('does not carry an external redirect into registration', async ({ page }) => {
    const captchaResponsePromise = waitForApiResponse(page, 'GET', '/captcha/generate')
    await page.goto('/login?redirect=%2F%2Fevil.example%2Fpath', { waitUntil: 'domcontentloaded' })
    expect((await completeResponse(captchaResponsePromise)).status()).toBe(200)
    await expect(page.locator('.login-footer a')).toHaveAttribute('href', '/register')
  })

  test('logged-in user is redirected away from the login page', async ({ page }) => {
    await loginAs(page, 'user')
    const homeResponses = waitForHomeResponses(page)
    const thumbnailResponses = [
      waitForApiResponse(page, 'GET', '/thumb/101.png'),
      waitForApiResponse(page, 'GET', '/thumb/701.png')
    ]
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/$|\/page/)
    const homeAndThumbnailResponses = await Promise.all(
      [...homeResponses, ...thumbnailResponses].map(completeResponse)
    )
    expect(homeAndThumbnailResponses.every((response) => response.status() === 200)).toBe(true)
  })
})
