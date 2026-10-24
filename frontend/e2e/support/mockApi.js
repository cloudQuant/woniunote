import { recordUnexpectedMockApi, watchMockContext } from './mockEgress.js'

/**
 * Playwright API mocking support.
 *
 * Intercepts all `/api/**` requests and returns deterministic fixtures in the
 * backend's `{ code, message, data }` envelope. This lets the E2E suite run
 * without a live C++ backend / MySQL / Redis while still exercising the real
 * Vue app (routing, rendering, stores, interceptors, user flows).
 *
 * Per-test overrides: pass an `overrides` map keyed by "METHOD path-substring".
 */

const ok = (data, message = 'success') => ({ code: 200, message, data })
const unexpectedRequests = new WeakMap()
const mockedRequests = new WeakMap()

export const fixtures = {
  articleTypes: {
    1: '交易策略', 101: '股票策略', 102: '期货策略',
    2: '量化框架', 201: 'vnpy',
    7: '编程', 701: 'python'
  },
  articleList: {
    data: [
      { articleid: 1, headline: '量化投资入门', type: 101, readcount: 120, replycount: 3, thumbnail: '', createtime: '2026-01-01 10:00:00', userid: 1, credit: 0, drafted: 0 },
      { articleid: 2, headline: 'Python 数据分析', type: 701, readcount: 88, replycount: 1, thumbnail: '', createtime: '2026-01-02 10:00:00', userid: 1, credit: 0, drafted: 0 }
    ],
    total: 2
  },
  articleCategories: {
    tree: [
      {
        id: 1,
        parent_id: null,
        name: '交易策略',
        sort_order: 1,
        visible: 1,
        article_count: 0,
        children: [
          { id: 101, parent_id: 1, name: '股票策略', sort_order: 1, visible: 1, article_count: 1, children: [] },
          { id: 102, parent_id: 1, name: '期货策略', sort_order: 2, visible: 1, article_count: 0, children: [] }
        ]
      },
      {
        id: 7,
        parent_id: null,
        name: '编程',
        sort_order: 7,
        visible: 1,
        article_count: 0,
        children: [
          { id: 701, parent_id: 7, name: 'python', sort_order: 1, visible: 1, article_count: 1, children: [] }
        ]
      }
    ],
    flat: [
      { id: 1, parent_id: null, name: '交易策略', sort_order: 1, visible: 1, article_count: 0 },
      { id: 101, parent_id: 1, name: '股票策略', sort_order: 1, visible: 1, article_count: 1 },
      { id: 102, parent_id: 1, name: '期货策略', sort_order: 2, visible: 1, article_count: 0 },
      { id: 7, parent_id: null, name: '编程', sort_order: 7, visible: 1, article_count: 0 },
      { id: 701, parent_id: 7, name: 'python', sort_order: 1, visible: 1, article_count: 1 }
    ]
  },
  articleDetail: {
    articleid: 1,
    headline: '量化投资入门',
    type: 101,
    content: '<p>这是一篇关于量化投资的文章正文。</p>',
    thumbnail: '101.png',
    readcount: 121,
    replycount: 1,
    userid: 1,
    credit: 0,
    drafted: 0,
    createtime: '2026-01-01 10:00:00',
    nickname: 'tester'
  },
  articleDetails: {
    1: {
      articleid: 1,
      headline: '量化投资入门',
      type: 101,
      content: '<p>这是一篇关于量化投资的文章正文。</p>',
      thumbnail: '101.png',
      readcount: 121,
      replycount: 1,
      userid: 1,
      credit: 0,
      drafted: 0,
      createtime: '2026-01-01 10:00:00',
      nickname: 'tester',
      navigation: {
        previous: null,
        next: { articleid: 3, headline: '量化投资进阶' }
      }
    },
    3: {
      articleid: 3,
      headline: '量化投资进阶',
      type: 101,
      content: '<p>这是量化投资的进阶文章正文。</p>',
      thumbnail: '101.png',
      readcount: 60,
      replycount: 0,
      userid: 1,
      credit: 0,
      drafted: 0,
      createtime: '2026-01-03 10:00:00',
      nickname: 'tester',
      navigation: {
        previous: { articleid: 1, headline: '量化投资入门' },
        next: null
      }
    }
  },
  comments: {
    data: [
      { commentid: 10, content: '写得很好！', nickname: '读者A', userid: 2, agreecount: 1, opposecount: 0, createtime: '2026-01-03 09:00:00', replies: [] }
    ],
    total: 1
  },
  hot: {
    latest: [{ articleid: 1, headline: '量化投资入门' }],
    most: [{ articleid: 2, headline: 'Python 数据分析' }],
    recommended: [{ articleid: 1, headline: '量化投资入门' }]
  },
  user: { userid: 1, username: 'tester@example.com', nickname: 'tester', role: 'user', credit: 100, avatar: '' },
  adminUser: { userid: 99, username: 'admin@example.com', nickname: 'admin', role: 'admin', credit: 999, avatar: '' }
}

/**
 * Install API route mocks on a Playwright page.
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {object} [options.overrides] map of "METHOD urlSubstring" → responder
 */
export async function mockApi(page, options = {}) {
  const overrides = options.overrides || {}
  unexpectedRequests.set(page, [])
  mockedRequests.set(page, [])
  watchMockContext(page.context()).pages.add(page)

  // Match the API path segment only. The previous glob also matched Vite's
  // development module URL `/src/api/index.js`, causing it to receive JSON
  // instead of JavaScript when E2E_BASE_URL points at `npm run dev`.
  await page.route(/^https?:\/\/[^/]+\/api(?:\/|$)/, async (route) => {
    const req = route.request()
    const method = req.method()
    const url = new URL(req.url())
    const path = url.pathname.replace(/^\/api/, '')
    let requestBody = null
    try { requestBody = req.postDataJSON() } catch { /* multipart or empty body */ }
    mockedRequests.get(page)?.push({ method, path, url: req.url(), body: requestBody })

    // Allow per-test overrides first.
    for (const key of Object.keys(overrides)) {
      const [m, sub] = key.split(' ')
      if (m === method && path.includes(sub)) {
        const r = overrides[key]
        const body = typeof r === 'function' ? await r(req) : r
        return route.fulfill({
          status: body.__status || 200,
          contentType: 'application/json',
          body: JSON.stringify(body.__status ? body.payload : body)
        })
      }
    }

    const json = (data, message) => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(ok(data, message))
    })

    // ---- Default routing ----
    // UEditor expects its raw configuration object, not the normal API envelope.
    if (path === '/uedit' && method === 'GET' && url.searchParams.get('action') === 'config') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          imageActionName: 'uploadimage', imageFieldName: 'upfile', imageAllowFiles: ['.png', '.jpg', '.jpeg', '.gif'],
          scrawlActionName: 'uploadscrawl', scrawlFieldName: 'upfile',
          videoActionName: 'uploadvideo', videoFieldName: 'upfile', videoAllowFiles: ['.mp4', '.avi'],
          fileActionName: 'uploadfile', fileFieldName: 'upfile', fileAllowFiles: ['.pdf', '.doc', '.docx'],
          imageManagerActionName: 'listimage', imageManagerAllowFiles: ['.png', '.jpg', '.jpeg', '.gif'],
          fileManagerActionName: 'listfile', fileManagerAllowFiles: ['.pdf', '.doc', '.docx']
        })
      })
    }
    if (path === '/articles/types' && method === 'GET') return json({ types: fixtures.articleTypes })
    if (path === '/articles/hot' && method === 'GET') return json(fixtures.hot)
    if (path === '/articles/my' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: 25, page: Number(url.searchParams.get('page') || 1), page_size: Number(url.searchParams.get('page_size') || 10) }) })
    if (path === '/articles/drafts/my' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/articles' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: fixtures.articleList.total }) })
    }
    const articleDetailMatch = path.match(/^\/articles\/(\d+)$/)
    if (articleDetailMatch && method === 'GET') {
      return json(fixtures.articleDetails[articleDetailMatch[1]] || fixtures.articleDetail)
    }
    if (path === '/articles' && method === 'POST') return json({ articleid: 3 }, '发布成功')
    if (/^\/articles\/\d+$/.test(path) && method === 'PUT') return json({ articleid: 1 }, '更新成功')

    if (/^\/comments\/article\/\d+$/.test(path) && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.comments.data), total: fixtures.comments.total }) })
    }
    if (path === '/comments' && method === 'POST') return json({ commentid: 11 }, '评论发表成功')
    if (path === '/comments/my' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })

    if (path === '/auth/login' && method === 'POST') {
      const post = req.postDataJSON() || {}
      if (post.password === 'wrongpass') {
        return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ code: 401, message: '用户名或密码错误' }) })
      }
      const u = post.username === 'admin@example.com' ? fixtures.adminUser : fixtures.user
      return json({ access_token: 'e2e-access', refresh_token: 'e2e-refresh', user: u })
    }
    if (path === '/auth/register' && method === 'POST') return json({ userid: 5 }, '注册成功')
    if (path === '/auth/me' && method === 'GET') return json(fixtures.user)
    if (path === '/auth/logout' && method === 'POST') return json(null)
    if (path === '/auth/refresh' && method === 'POST') return json({ access_token: 'e2e-access-refreshed', refresh_token: 'e2e-refresh-refreshed' })

    if (/^\/favorites\/check\/\d+$/.test(path) && method === 'GET') return json({ is_favorited: false })
    if (/^\/favorites\/\d+$/.test(path) && method === 'DELETE') return json(null, '取消收藏成功')
    if (path === '/favorites' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/favorites' && method === 'POST') return json(null, '收藏成功')

    if (path === '/credits/balance' && method === 'GET') return json({ total_credit: 100, type_stats: {} })
    if (path === '/credits/history' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (/^\/credits\/pay-article\/\d+$/.test(path) && method === 'POST') return json({ paid: true })
    if (/^\/credits\/check-article\/\d+$/.test(path) && method === 'GET') return json({ paid: false })

    if (path === '/captcha/generate' && method === 'GET') return json({ image: 'data:image/png;base64,iVBORw0KGgo=', captcha_id: 'cap-1' })

    if (/^\/users\/\d+$/.test(path) && method === 'GET') return json(fixtures.user)
    if (path === '/users/profile' && method === 'PUT') return json(fixtures.user)
    if (path === '/users/password' && method === 'POST') return json(null, '密码修改成功')

    if (/^\/upload\/(image|file|avatar)$/.test(path) && method === 'POST') return json({ url: '/api/thumb/1.png' }, '上传成功')

    if (/^\/comments\/\d+$/.test(path) && method === 'DELETE') return json(null, '删除成功')
    if (/^\/comments\/\d+\/vote$/.test(path) && method === 'POST') return json({ agreecount: 1, opposecount: 0 })

    if (/^\/articles\/\d+\/type$/.test(path) && method === 'PUT') return json({ type: req.postDataJSON()?.type })
    if (/^\/articles\/\d+\/recommend$/.test(path) && method === 'POST') return json({ recommended: true })
    if (/^\/articles\/\d+\/(hide|check)$/.test(path) && method === 'POST') return json({ updated: true })
    if (/^\/articles\/\d+$/.test(path) && method === 'DELETE') return json(null, '删除成功')

    if (path === '/math-training/records' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/math-training/records' && method === 'POST') return json({ id: 1 }, '训练记录已保存')
    if (path === '/math-training/summary' && method === 'GET') return json({ total_sessions: 0, total_questions: 0, average_accuracy: 0, total_duration_seconds: 0, total_correct: 0 })
    if (/^\/math-training\/records\/\d+$/.test(path) && method === 'GET') return json({ id: Number(path.split('/').at(-1)) })
    if (path === '/math-training/wrong-answers' && method === 'GET') return json([])

    if (path === '/admin/stats' && method === 'GET') return json({ users: 10, articles: 2, comments: 1 })
    if (path === '/admin/users' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([fixtures.user, fixtures.adminUser]), total: 2 }) })
    if (path === '/admin/articles' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: fixtures.articleList.total }) })
    }
    if (path === '/admin/article-categories' && method === 'GET') return json(fixtures.articleCategories)
    if (path === '/admin/article-categories' && method === 'POST') return json({ id: 2 })
    if (/^\/admin\/article-categories\/\d+$/.test(path) && method === 'PUT') return json({ id: Number(path.split('/').at(-1)) })
    if (/^\/admin\/article-categories\/\d+$/.test(path) && method === 'DELETE') return json(null)
    if (/^\/admin\/articles\/\d+\/type$/.test(path) && method === 'PUT') {
      return json({ type: req.postDataJSON()?.type }, '分类已更新')
    }

    if (path === '/system/health' && method === 'GET') return json({ status: 'ok' })
    if (path === '/system/status' && method === 'GET') return json({ status: 'ok' })
    if (path === '/system/db' && method === 'GET') return json({ status: 'ok' })
    if (/^\/thumb\//.test(path) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a6sAAAAASUVORK5CYII=', 'base64')
      })
    }

    const records = unexpectedRequests.get(page)
    records?.push({ method, url: req.url() })
    recordUnexpectedMockApi(page, method, url.pathname)
    return route.fulfill({
      status: 501,
      contentType: 'application/json',
      body: JSON.stringify({ code: 501, message: `未登记的 API mock: ${method} ${url.pathname}`, data: null })
    })
  })
}

export function getUnexpectedApiRequests(page) {
  return unexpectedRequests.get(page) || []
}

export function assertNoUnexpectedApiRequests(page) {
  const records = getUnexpectedApiRequests(page)
  if (records.length) {
    const details = records.map(({ method, url }) => {
      let pathname = url
      try { pathname = new URL(url).pathname } catch { /* preserve malformed URL only as a diagnostic fallback */ }
      return `${method} ${pathname}`
    }).join(', ')
    throw new Error(`Mocked tests must register every API method and URL: ${details}`)
  }
}

export function getMockedApiRequests(page) {
  return mockedRequests.get(page) || []
}

/**
 * Seed an authenticated session into localStorage before the app boots.
 * @param {import('@playwright/test').Page} page
 * @param {'user'|'admin'} [role]
 */
export async function loginAs(page, role = 'user') {
  const user = role === 'admin' ? fixtures.adminUser : fixtures.user
  await page.addInitScript((u) => {
    localStorage.setItem('token', 'e2e-access')
    localStorage.setItem('refreshToken', 'e2e-refresh')
    localStorage.setItem('user', JSON.stringify(u))
  }, user)
}
