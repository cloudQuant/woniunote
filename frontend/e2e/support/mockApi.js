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
    readcount: 121,
    replycount: 1,
    userid: 1,
    credit: 0,
    drafted: 0,
    createtime: '2026-01-01 10:00:00',
    nickname: 'tester'
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

  await page.route('**/api/**', async (route) => {
    const req = route.request()
    const method = req.method()
    const url = new URL(req.url())
    const path = url.pathname.replace(/^\/api/, '')

    // Allow per-test overrides first.
    for (const key of Object.keys(overrides)) {
      const [m, sub] = key.split(' ')
      if (m === method && path.includes(sub)) {
        const r = overrides[key]
        const body = typeof r === 'function' ? r(req) : r
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
    if (path === '/articles/types') return json({ types: fixtures.articleTypes })
    if (path === '/articles/hot') return json(fixtures.hot)
    if (path === '/articles/my') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: 25, page: Number(url.searchParams.get('page') || 1), page_size: Number(url.searchParams.get('page_size') || 10) }) })
    if (path === '/articles/drafts/my') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/articles' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: fixtures.articleList.total }) })
    }
    if (/^\/articles\/\d+$/.test(path) && method === 'GET') return json(fixtures.articleDetail)
    if (path === '/articles' && method === 'POST') return json({ articleid: 3 }, '发布成功')
    if (/^\/articles\/\d+$/.test(path) && method === 'PUT') return json({ articleid: 1 }, '更新成功')

    if (/^\/comments\/article\/\d+$/.test(path)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.comments.data), total: fixtures.comments.total }) })
    }
    if (path === '/comments' && method === 'POST') return json({ commentid: 11 }, '评论发表成功')
    if (path === '/comments/my') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })

    if (path === '/auth/login') {
      const post = req.postDataJSON() || {}
      if (post.password === 'wrongpass') {
        return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ code: 401, message: '用户名或密码错误' }) })
      }
      const u = post.username === 'admin@example.com' ? fixtures.adminUser : fixtures.user
      return json({ access_token: 'e2e-access', refresh_token: 'e2e-refresh', user: u })
    }
    if (path === '/auth/register') return json({ userid: 5 }, '注册成功')
    if (path === '/auth/me') return json(fixtures.user)
    if (path === '/auth/logout') return json(null)

    if (/^\/favorites\/check\/\d+$/.test(path)) return json({ is_favorited: false })
    if (path === '/favorites' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/favorites' && method === 'POST') return json(null, '收藏成功')

    if (path === '/credits/balance') return json({ total_credit: 100, type_stats: {} })
    if (path === '/credits/history') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })

    if (path === '/captcha/generate') return json({ image: 'data:image/png;base64,iVBORw0KGgo=', captcha_id: 'cap-1' })

    if (path === '/math-training/records' && method === 'GET') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([]), total: 0 }) })
    if (path === '/math-training/records' && method === 'POST') return json({ id: 1 }, '训练记录已保存')
    if (path === '/math-training/summary') return json({ total_sessions: 0, total_questions: 0, average_accuracy: 0, total_duration_seconds: 0, total_correct: 0 })

    if (path === '/admin/stats') return json({ users: 10, articles: 2, comments: 1 })
    if (path === '/admin/users') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok([fixtures.user, fixtures.adminUser]), total: 2 }) })
    if (path === '/admin/articles' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...ok(fixtures.articleList.data), total: fixtures.articleList.total }) })
    }
    if (path === '/admin/article-categories' && method === 'GET') return json(fixtures.articleCategories)
    if (/^\/admin\/articles\/\d+\/type$/.test(path) && method === 'PUT') {
      return json({ type: req.postDataJSON()?.type }, '分类已更新')
    }

    if (path === '/system/health') return json({ status: 'ok' })

    // Fallback: empty success.
    return json(null)
  })
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
