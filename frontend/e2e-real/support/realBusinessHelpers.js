/* global process */

import { expect } from '@playwright/test'
import { randomUUID } from 'node:crypto'

const password = 'Iter21!StrongPass'
const runId = process.env.WONIUNOTE_TEST_RUN_ID || ''
const backendTarget = process.env.WONIUNOTE_API_PROXY_TARGET || ''

function matchesRequest(response, pathname, method) {
  return new URL(response.url()).pathname === pathname &&
    response.request().method() === method
}

function backendUrl(path) {
  return new URL(path, backendTarget).toString()
}

export function uniqueUsername(prefix = 'iter21biz') {
  return `${prefix}_${randomUUID().replaceAll('-', '').slice(0, 16)}`
}

export async function expectSuccess(response) {
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.code).toBe(200)
  return body
}

export async function getBackend(page, path, accessToken) {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
  return page.request.get(backendUrl(path), { headers })
}

export async function registerAccount(page, username, nickname) {
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入昵称（可选）').fill(nickname)
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.getByPlaceholder('请再次输入密码').fill(password)

  const responsePromise = page.waitForResponse((response) =>
    matchesRequest(response, '/api/auth/register', 'POST')
  )
  await page.getByRole('button', { name: '注册' }).click()
  await expectSuccess(await responsePromise)
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/)
}

async function readLiveCaptcha(page, captchaId) {
  expect(runId).toMatch(/^\d{8}T\d{6}Z-[0-9a-f]{12}$/)
  const response = await page.request.post(backendUrl('/api/captcha/test/challenge'), {
    headers: { 'X-Woniunote-Test-Run': runId },
    data: { captcha_id: captchaId }
  })
  const body = await expectSuccess(response)
  expect(body.data.captcha_id).toBe(captchaId)
  expect(body.data.expired).toBe(false)
  expect(body.data.captcha_code).toMatch(/^[A-Z2-9]{4}$/)
  return body.data.captcha_code
}

async function expectCaptchaConsumed(page, captchaId) {
  const response = await page.request.post(backendUrl('/api/captcha/test/challenge'), {
    headers: { 'X-Woniunote-Test-Run': runId },
    data: { captcha_id: captchaId }
  })
  expect(response.status()).toBe(404)
}

async function completeLogin(page, username, modal) {
  const captchaPromise = page.waitForResponse((response) =>
    matchesRequest(response, '/api/captcha/generate', 'GET')
  )

  let form
  if (modal) {
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await page.locator('button.login-link').click()
    form = page.locator('.login-dialog')
  } else {
    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    form = page.locator('.login-page')
  }

  const captchaResponse = await captchaPromise
  const captchaBody = await expectSuccess(captchaResponse)
  const captchaId = captchaBody.data.captcha_id
  expect(captchaId).toBeTruthy()
  await expect(form.locator(modal ? 'img.captcha-img' : 'img.captcha-image')).toBeVisible()
  const captchaCode = await readLiveCaptcha(page, captchaId)

  await form.getByPlaceholder('请输入用户名').fill(username)
  await form.getByPlaceholder(modal ? '请输入你的登录密码' : '请输入密码').fill(password)
  await form.getByPlaceholder(modal ? '请输入右侧的验证码' : '请输入验证码').fill(captchaCode)

  const loginPromise = page.waitForResponse((response) =>
    matchesRequest(response, '/api/auth/login', 'POST')
  )
  await form.getByRole('button', { name: '登录' }).click()
  const loginBody = await expectSuccess(await loginPromise)
  expect(loginBody.data.access_token).toBeTruthy()
  expect(loginBody.data.refresh_token).toBeTruthy()
  await expectCaptchaConsumed(page, captchaId)

  return {
    accessToken: loginBody.data.access_token,
    refreshToken: loginBody.data.refresh_token
  }
}

export function loginStandalone(page, username) {
  return completeLogin(page, username, false)
}

export function loginHeaderModal(page, username) {
  return completeLogin(page, username, true)
}

export async function expectCurrentUser(page, accessToken, username) {
  const response = await getBackend(page, '/api/auth/me', accessToken)
  const body = await expectSuccess(response)
  expect(body.data.username).toBe(username)
  expect(body.data.userid).toBeTruthy()
  return body.data
}

export async function logoutFromUi(page) {
  const logoutPromise = page.waitForResponse((response) =>
    matchesRequest(response, '/api/auth/logout', 'POST')
  )
  await page.locator('.user-link').click()
  await page.getByText('退出登录', { exact: true }).click()
  await expectSuccess(await logoutPromise)
  await expect(page.locator('.user-link')).toHaveCount(0)
  await expect(page.locator('.login-link')).toBeVisible()
}

export function firstLeafPath(nodes, parents = []) {
  for (const node of nodes || []) {
    const path = [...parents, node]
    if (Array.isArray(node.children) && node.children.length > 0) {
      const leafPath = firstLeafPath(node.children, path)
      if (leafPath) return leafPath
    } else {
      return path
    }
  }
  return null
}

export async function chooseCategory(page, tree) {
  const path = firstLeafPath(tree)
  expect(path, 'the real category response should contain a selectable leaf').not.toBeNull()

  const cascader = page.getByPlaceholder('请选择分类')
  for (let depth = 0; depth < path.length; depth += 1) {
    if (depth === 0) await cascader.click()
    const menu = page.locator('.el-cascader-menu').nth(depth)
    await expect(menu).toBeVisible()
    await menu.getByText(path[depth].name, { exact: true }).click()
  }
  await expect(page.locator('.el-cascader-panel')).toBeHidden()
}

export async function fillArticleEditor(page, content) {
  const editorBody = page.frameLocator('.edui-editor-iframeholder iframe').locator('body')
  await expect(editorBody).toBeVisible()
  await editorBody.fill(content)
}
