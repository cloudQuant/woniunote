import { expect, test } from '@playwright/test'
import { deflateSync } from 'node:zlib'
import {
  chooseCategory,
  expectCurrentUser,
  expectSuccess,
  fillArticleEditor,
  getBackend,
  loginHeaderModal,
  loginStandalone,
  logoutFromUi,
  registerAccount,
  uniqueUsername
} from './support/realBusinessHelpers.js'

const frontendUrl = process.env.WONIUNOTE_REAL_E2E_URL || ''

test.describe.configure({ retries: 0 })

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
const PNG_CRC_TABLE = Array.from({ length: 256 }, (_, index) => {
  let value = index
  for (let bit = 0; bit < 8; bit += 1) {
    value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1
  }
  return value >>> 0
})

function pngCrc32(bytes) {
  let crc = 0xffffffff
  for (const byte of bytes) {
    crc = PNG_CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  }
  return (crc ^ 0xffffffff) >>> 0
}

function pngChunk(type, data) {
  const typeBytes = Buffer.from(type)
  const payload = Buffer.concat([typeBytes, data])
  const length = Buffer.alloc(4)
  const checksum = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  checksum.writeUInt32BE(pngCrc32(payload))
  return Buffer.concat([length, payload, checksum])
}

function createSmallPng(red, green, blue) {
  const header = Buffer.alloc(13)
  header.writeUInt32BE(2, 0)
  header.writeUInt32BE(2, 4)
  header[8] = 8
  header[9] = 2
  const row = Buffer.from([0, red, green, blue, red, green, blue])
  const pixels = Buffer.concat([row, row])
  return Buffer.concat([
    PNG_SIGNATURE,
    pngChunk('IHDR', header),
    pngChunk('IDAT', deflateSync(pixels)),
    pngChunk('IEND', Buffer.alloc(0))
  ])
}

function requestMatches(response, pathname, method) {
  return new URL(response.url()).pathname === pathname &&
    response.request().method() === method
}

function findComment(comments, commentIdOrText) {
  for (const comment of comments || []) {
    if (String(comment.commentid) === String(commentIdOrText) || comment.content === commentIdOrText) {
      return comment
    }
    const reply = findComment(comment.replies, commentIdOrText)
    if (reply) return reply
  }
  return null
}

function solveDisplayedQuestion(questionText) {
  const match = questionText.match(/^\s*(-?\d+)\s*([+\-×÷])\s*(-?\d+)\s*=\s*\?\s*$/)
  expect(match, `the visible question should be a supported arithmetic expression: ${questionText}`)
    .not.toBeNull()
  const left = Number(match[1])
  const right = Number(match[3])
  const operation = { '+': '+', '-': '-', '×': '*', '÷': '/' }[match[2]]
  const answer = operation === '+' ? left + right
    : operation === '-' ? left - right
      : operation === '*' ? left * right
        : left / right
  expect(Number.isFinite(answer)).toBe(true)
  return { answer, operation, question: `${left} ${match[2]} ${right}` }
}

test('real user registers, logs in through both entries, publishes a private draft, then comments, votes, and logs out', async ({ browser, page }) => {
  test.setTimeout(180000)
  const username = uniqueUsername('i21article')
  const nickname = `Iteration 21 ${username.slice(-6)}`
  const headline = `Iteration 21 business ${username}`
  const draftContent = `Draft body ${username}`
  const publishedContent = `Published body ${username}`
  const commentText = `Real comment ${username}`
  const imageBytes = createSmallPng(216, 64, 48)
  const editedImageBytes = createSmallPng(32, 88, 208)

  const anonymousContext = await browser.newContext()
  const anonymousPage = await anonymousContext.newPage()

  try {
    await registerAccount(page, username, nickname)
    const standaloneTokens = await loginStandalone(page, username)
    await expectCurrentUser(page, standaloneTokens.accessToken, username)
    await expect(page).toHaveURL((url) => url.pathname === '/')

    const typesPromise = page.waitForResponse((response) =>
      requestMatches(response, '/api/articles/types', 'GET')
    )
    await page.goto('/write', { waitUntil: 'domcontentloaded' })
    const typesResponse = await typesPromise
    const typesBody = await expectSuccess(typesResponse)
    expect(typesBody.data.tree).toEqual(expect.any(Array))
    await expect(page.locator('.write-article-page')).toBeVisible()
    await page.getByPlaceholder('请输入文章标题').fill(headline)
    await chooseCategory(page, typesBody.data.tree)
    await fillArticleEditor(page, draftContent)

    const uploadPromise = page.waitForResponse((response) =>
      requestMatches(response, '/api/upload/image', 'POST')
    )
    await page.locator('.thumbnail-uploader input[type="file"]').setInputFiles({
      name: 'iter21-thumbnail.png',
      mimeType: 'image/png',
      buffer: imageBytes
    })
    const uploadBody = await expectSuccess(await uploadPromise)
    const uploadedRelativePath = uploadBody.data.url
    expect(uploadedRelativePath).toMatch(
      /^\/uploads\/uploads\/images\/\d{4}\/(?:0[1-9]|1[0-2])\/[^/]+$/
    )
    const uploadedUrl = new URL(uploadedRelativePath, frontendUrl)
    expect(uploadedUrl.origin).toBe(new URL(frontendUrl).origin)
    expect(uploadedUrl.pathname).toBe(uploadedRelativePath)
    expect(uploadedUrl.search).toBe('')
    expect(uploadedUrl.hash).toBe('')
    const uploadPathSegments = uploadedUrl.pathname.split('/').filter(Boolean)
    expect(uploadPathSegments).toHaveLength(6)
    expect(uploadPathSegments.slice(0, 3)).toEqual(['uploads', 'uploads', 'images'])
    const [uploadYear, uploadMonth, uploadedFilename] = uploadPathSegments.slice(3)
    expect(uploadYear).toMatch(/^\d{4}$/)
    expect(Number(uploadYear)).toBeGreaterThan(0)
    expect(uploadMonth).toMatch(/^(0[1-9]|1[0-2])$/)
    expect(uploadedFilename).toBe(uploadBody.data.filename)
    expect(uploadedFilename).toMatch(/^[1-9]\d*_[1-9]\d{3}\.png$/)
    await expect(page.locator('.thumbnail-preview')).toBeVisible()
    await expect(page.locator('.thumbnail-preview')).toHaveAttribute('src', uploadedRelativePath)

    const uploadedImage = await getBackend(page, uploadedRelativePath)
    expect(uploadedImage.status()).toBe(200)
    expect(uploadedImage.headers()['content-type']).toMatch(/^image\//)
    expect(await uploadedImage.body()).toEqual(imageBytes)

    const draftPromise = page.waitForResponse((response) =>
      requestMatches(response, '/api/articles', 'POST')
    )
    await page.getByRole('button', { name: '保存草稿' }).click()
    const draftBody = await expectSuccess(await draftPromise)
    const articleId = draftBody.data.articleid
    expect(articleId).toBeTruthy()
    await expect(page).toHaveURL(new RegExp(`/article/${articleId}$`))

    const draftReadResponse = await getBackend(page, `/api/articles/${articleId}`, standaloneTokens.accessToken)
    const draftReadBody = await expectSuccess(draftReadResponse)
    expect(draftReadBody.data).toMatchObject({
      articleid: articleId,
      headline,
      drafted: 1
    })
    expect(draftReadBody.data.content).toContain(draftContent)
    expect(draftReadBody.data.content.trim()).not.toBe('')
    expect(draftReadBody.data.thumbnail).toBe(uploadedRelativePath)

    const anonymousDraft = await getBackend(anonymousPage, `/api/articles/${articleId}`)
    expect(anonymousDraft.status()).toBe(404)
    const anonymousDraftPageResponse = anonymousPage.waitForResponse((response) =>
      requestMatches(response, `/api/articles/${articleId}`, 'GET')
    )
    await anonymousPage.goto(new URL(`/article/${articleId}`, frontendUrl).toString(), {
      waitUntil: 'domcontentloaded'
    })
    expect((await anonymousDraftPageResponse).status()).toBe(404)
    await expect(anonymousPage.locator('.el-empty')).toContainText('文章不存在')

    await logoutFromUi(page)
    const modalTokens = await loginHeaderModal(page, username)
    await expectCurrentUser(page, modalTokens.accessToken, username)
    await expect(page.locator('.login-dialog')).toBeHidden()

    const editArticlePromise = page.waitForResponse((response) =>
      requestMatches(response, `/api/articles/${articleId}`, 'GET')
    )
    await page.goto(`/edit/${articleId}`, { waitUntil: 'domcontentloaded' })
    const editArticleBody = await expectSuccess(await editArticlePromise)
    expect(editArticleBody.data).toMatchObject({
      articleid: articleId,
      headline,
      drafted: 1
    })
    expect(editArticleBody.data.content).toContain(draftContent)
    expect(editArticleBody.data.thumbnail).toBe(uploadedRelativePath)
    await expect(page.locator('.page-title')).toHaveText('编辑文章')
    await expect(page.getByPlaceholder('请输入文章标题')).toHaveValue(headline)
    await expect(page.locator('.thumbnail-preview')).toHaveAttribute('src', uploadedRelativePath)
    const editorBody = page.frameLocator('.edui-editor-iframeholder iframe').locator('body')
    await expect(editorBody).toContainText(draftContent)
    await fillArticleEditor(page, publishedContent)

    const editUploadPromise = page.waitForResponse((response) =>
      requestMatches(response, '/api/upload/image', 'POST')
    )
    await page.locator('.thumbnail-uploader input[type="file"]').setInputFiles({
      name: 'iter21-thumbnail-edited.png',
      mimeType: 'image/png',
      buffer: editedImageBytes
    })
    const editUploadBody = await expectSuccess(await editUploadPromise)
    const editedThumbnailPath = editUploadBody.data.url
    expect(editedThumbnailPath).toMatch(
      /^\/uploads\/uploads\/images\/\d{4}\/(?:0[1-9]|1[0-2])\/[^/]+$/
    )
    await expect(page.locator('.thumbnail-preview')).toHaveAttribute('src', editedThumbnailPath)

    const editedImageResponse = await getBackend(page, editedThumbnailPath)
    expect(editedImageResponse.status()).toBe(200)
    expect(editedImageResponse.headers()['content-type']).toMatch(/^image\/png/)
    expect(await editedImageResponse.body()).toEqual(editedImageBytes)

    const publishPromise = page.waitForResponse((response) =>
      requestMatches(response, `/api/articles/${articleId}`, 'PUT')
    )
    await page.getByRole('button', { name: '更新' }).click()
    await expectSuccess(await publishPromise)
    await expect(page).toHaveURL(new RegExp(`/article/${articleId}$`))

    const publishedRead = await getBackend(page, `/api/articles/${articleId}`, modalTokens.accessToken)
    const publishedBody = await expectSuccess(publishedRead)
    expect(publishedBody.data.drafted).toBe(0)
    expect(publishedBody.data.headline).toBe(headline)
    expect(publishedBody.data.content).toContain(publishedContent)
    expect(publishedBody.data.content.trim()).not.toBe('')
    expect(publishedBody.data.thumbnail).toBe(editedThumbnailPath)

    const anonymousPublicResponse = anonymousPage.waitForResponse((response) =>
      requestMatches(response, `/api/articles/${articleId}`, 'GET')
    )
    await anonymousPage.goto(new URL(`/article/${articleId}`, frontendUrl).toString(), {
      waitUntil: 'domcontentloaded'
    })
    const anonymousPublicBody = await expectSuccess(await anonymousPublicResponse)
    expect(anonymousPublicBody.data.content).toContain(publishedContent)
    expect(anonymousPublicBody.data.content.trim()).not.toBe('')
    await expect(anonymousPage.locator('.article-title')).toHaveText(headline)
    await expect(anonymousPage.locator('.article-body')).toContainText(publishedContent)

    const listImageResponsePromise = anonymousPage.waitForResponse((response) =>
      requestMatches(response, new URL(editedThumbnailPath, frontendUrl).pathname, 'GET')
    )
    await anonymousPage.goto(new URL('/', frontendUrl).toString(), { waitUntil: 'domcontentloaded' })
    const publicArticleCard = anonymousPage.locator('.article-item').filter({ hasText: headline })
    await expect(publicArticleCard).toBeVisible()
    const publicCardImage = publicArticleCard.locator('.article-thumbnail img')
    await expect(publicCardImage).toHaveAttribute('src', editedThumbnailPath)
    const listImageResponse = await listImageResponsePromise
    expect(listImageResponse.status()).toBe(200)
    expect(listImageResponse.headers()['content-type']).toMatch(/^image\/png/)
    expect(await listImageResponse.body()).toEqual(editedImageBytes)
    await expect.poll(() => publicCardImage.evaluate((image) => image.naturalWidth)).toBeGreaterThan(0)

    const commentsBeforeResponse = await getBackend(
      page,
      `/api/comments/article/${articleId}?page=1&page_size=50`,
      modalTokens.accessToken
    )
    const commentsBeforeBody = await expectSuccess(commentsBeforeResponse)
    expect(commentsBeforeBody.data).toEqual(expect.any(Array))
    expect(commentsBeforeBody.data).toHaveLength(0)

    const commentPromise = page.waitForResponse((response) =>
      requestMatches(response, '/api/comments', 'POST')
    )
    await page.getByPlaceholder('写下你的评论...').fill(commentText)
    await page.getByRole('button', { name: '发表评论' }).click()
    await expectSuccess(await commentPromise)
    await expect(page.locator('.comment-section')).toContainText(commentText)

    const commentsAfterResponse = await getBackend(
      page,
      `/api/comments/article/${articleId}?page=1&page_size=50`,
      modalTokens.accessToken
    )
    const commentsAfterBody = await expectSuccess(commentsAfterResponse)
    const persistedComment = findComment(commentsAfterBody.data, commentText)
    expect(persistedComment).toBeTruthy()
    expect(persistedComment.content).toBe(commentText)
    const persistedCommentId = persistedComment.commentid
    const beforeAgreeCount = Number(persistedComment.agreecount)

    const commentCard = page.locator('.comment-item').filter({ hasText: commentText })
    await expect(commentCard).toHaveCount(1)
    const votePromise = page.waitForResponse((response) =>
      requestMatches(response, `/api/comments/${persistedCommentId}/vote`, 'POST')
    )
    await commentCard.locator('.comment-actions > span').first().click()
    await expectSuccess(await votePromise)

    const commentsAfterVoteResponse = await getBackend(
      page,
      `/api/comments/article/${articleId}?page=1&page_size=50`,
      modalTokens.accessToken
    )
    const commentsAfterVoteBody = await expectSuccess(commentsAfterVoteResponse)
    const votedComment = findComment(commentsAfterVoteBody.data, persistedCommentId)
    expect(votedComment).toBeTruthy()
    expect(Number(votedComment.agreecount)).toBe(beforeAgreeCount + 1)

    await logoutFromUi(page)
  } finally {
    await anonymousContext.close()
  }
})

test('real math UI saves a short session and reads the skipped answer back as null', async ({ page }) => {
  const username = uniqueUsername('i21math')
  const nickname = `Iteration 21 ${username.slice(-6)}`

  await registerAccount(page, username, nickname)
  const tokens = await loginStandalone(page, username)
  await expectCurrentUser(page, tokens.accessToken, username)

  const initialRecordsResponse = await getBackend(
    page,
    '/api/math-training/records?page=1&page_size=100',
    tokens.accessToken
  )
  const initialRecords = await expectSuccess(initialRecordsResponse)
  expect(initialRecords.total).toBe(0)

  const initialHistoryPromise = page.waitForResponse((response) =>
    requestMatches(response, '/api/math-training/records', 'GET')
  )
  await page.goto('/math-training', { waitUntil: 'domcontentloaded' })
  await expectSuccess(await initialHistoryPromise)
  await page.locator('.start-btn').click()
  const progress = page.locator('.progress-text')
  await expect(progress).toHaveText('第 1 / 20 题')

  const skipped = solveDisplayedQuestion(await page.locator('.question-text').innerText())
  await page.getByRole('button', { name: '跳过' }).click()
  await expect(page.locator('.feedback-box')).toContainText('已跳过')
  await expect(progress).toHaveText('第 2 / 20 题')

  const answered = solveDisplayedQuestion(await page.locator('.question-text').innerText())
  await page.getByPlaceholder('输入答案后按回车').fill(String(answered.answer))
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.locator('.feedback-box')).toContainText('正确！')
  await expect(progress).toHaveText('第 3 / 20 题')

  const recordPromise = page.waitForResponse((response) =>
    requestMatches(response, '/api/math-training/records', 'POST')
  )
  const historyRefreshPromise = page.waitForResponse((response) =>
    requestMatches(response, '/api/math-training/records', 'GET')
  )
  await page.getByRole('button', { name: '结束训练' }).click()
  const [recordResponse] = await Promise.all([recordPromise, historyRefreshPromise])
  await expectSuccess(recordResponse)

  const recordsResponse = await getBackend(
    page,
    '/api/math-training/records?page=1&page_size=100',
    tokens.accessToken
  )
  const recordsBody = await expectSuccess(recordsResponse)
  expect(recordsBody.total).toBe(1)
  expect(recordsBody.data).toHaveLength(1)
  const summary = recordsBody.data[0]
  expect(summary).toMatchObject({
    total_questions: 2,
    correct_count: 1,
    wrong_count: 1,
    accuracy: 50
  })
  expect(summary.id).toBeTruthy()

  const detailResponse = await getBackend(
    page,
    `/api/math-training/records/${summary.id}`,
    tokens.accessToken
  )
  const detailBody = await expectSuccess(detailResponse)
  expect(detailBody.data).toMatchObject({
    id: summary.id,
    total_questions: 2,
    correct_count: 1,
    wrong_count: 1,
    accuracy: 50
  })
  expect(detailBody.data.wrong_answers).toHaveLength(1)
  expect(detailBody.data.wrong_answers[0]).toMatchObject({
    question: skipped.question,
    operation: skipped.operation,
    user_answer: null
  })
  expect(Number(detailBody.data.wrong_answers[0].correct_answer)).toBe(skipped.answer)
  await expect(page.locator('.el-table__body tr').first()).toContainText('50.0%')

  await logoutFromUi(page)
})
