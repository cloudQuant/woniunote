import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['log', 'error'])

const routeState = vi.hoisted(() => ({ current: null }))
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => routeState.current,
  useRouter: () => ({ push })
}))

const m = vi.hoisted(() => ({
  msg: { success: vi.fn(), error: vi.fn() },
  user: { isLoggedIn: false, isEditor: false, user: { userid: 1 } },  articleApi: {
    getDetail: vi.fn(() => Promise.resolve({ data: { articleid: 1, headline: 'Hello', type: 101, userid: 1, content: '<p>body</p>' } }))
  },
  commentApi: {
    getByArticle: vi.fn(() => Promise.resolve({ data: [
      { commentid: 10, content: 'c1', agreecount: 0, opposecount: 0, replies: [{ commentid: 11 }] }
    ] })),
    create: vi.fn(() => Promise.resolve({})),
    agree: vi.fn(() => Promise.resolve({})),
    oppose: vi.fn(() => Promise.resolve({}))
  },
  favoriteApi: {
    check: vi.fn(() => Promise.resolve({ data: { is_favorited: false } })),
    add: vi.fn(() => Promise.resolve({})),
    remove: vi.fn(() => Promise.resolve({}))
  }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg, default: {} }))
vi.mock('@/stores/user', () => ({ useUserStore: () => m.userReactive }))
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({ fetchArticleTypes: vi.fn(() => Promise.resolve({})), getTypeName: (t) => `cat-${t}` })
}))
vi.mock('@/api', () => ({ articleApi: m.articleApi, commentApi: m.commentApi, favoriteApi: m.favoriteApi }))
vi.mock('@/components/sidebar/Sidebar.vue', () => ({ default: { name: 'Sidebar', render: () => null } }))
vi.mock('@/components/viewer/PdfViewer.vue', () => ({ default: { name: 'PdfViewer', render: () => null } }))

import ArticleDetail from './ArticleDetail.vue'

// Make the user store reactive so component computeds (canEdit) re-evaluate.
m.userReactive = reactive({ isLoggedIn: false, isEditor: false, user: { userid: 1 } })

describe('ArticleDetail.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reactive route so the component's watch on route.params.id fires.
    routeState.current = reactive({ params: { id: '1' }, fullPath: '/article/1' })
    m.userReactive.isLoggedIn = false
    m.userReactive.isEditor = false
    m.userReactive.user = { userid: 1 }
  })

  it('fetches article + comments on mount and sets document.title', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(m.articleApi.getDetail).toHaveBeenCalledWith('1')
    expect(wrapper.vm.article.headline).toBe('Hello')
    expect(document.title).toContain('Hello')
    expect(wrapper.vm.loading).toBe(false)
  })

  it('totalComments counts top-level + replies', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.vm.totalComments).toBe(2) // 1 comment + 1 reply
  })

  it('typeName resolves via article store', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.vm.typeName).toBe('cat-101')
  })

  it('renders previous and next article titles as router links', async () => {
    m.articleApi.getDetail.mockResolvedValueOnce({
      data: {
        articleid: 20,
        headline: '当前文章',
        type: 101,
        userid: 1,
        content: '<p>body</p>',
        navigation: {
          previous: { articleid: 10, headline: '上一篇标题' },
          next: { articleid: 30, headline: '下一篇标题' }
        }
      }
    })

    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()

    const navigation = wrapper.get('nav[aria-label="同类文章导航"]')
    expect(navigation.find('.article-navigation__previous').text()).toContain('上一篇文章')
    expect(navigation.find('.article-navigation__next').text()).toContain('下一篇文章')
    expect(navigation.findAll('a.router-link').map((link) => link.text()))
      .toEqual(['上一篇标题', '下一篇标题'])
  })

  it('renders plain, non-navigable fallback text when navigation is absent', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()

    const navigation = wrapper.get('nav[aria-label="同类文章导航"]')
    expect(navigation.text()).toContain('暂无上一篇文章')
    expect(navigation.text()).toContain('暂无下一篇文章')
    expect(navigation.findAll('a')).toHaveLength(0)
  })

  it('only renders a link for the direction that has a neighbouring article', async () => {
    m.articleApi.getDetail.mockResolvedValueOnce({
      data: {
        articleid: 10,
        headline: '第一篇文章',
        type: 101,
        userid: 1,
        content: '<p>body</p>',
        navigation: {
          previous: null,
          next: { articleid: 20, headline: '下一篇标题' }
        }
      }
    })

    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()

    const navigation = wrapper.get('nav[aria-label="同类文章导航"]')
    expect(navigation.find('.article-navigation__previous').text()).toContain('暂无上一篇文章')
    expect(navigation.find('.article-navigation__previous').find('a').exists()).toBe(false)
    expect(navigation.find('.article-navigation__next').find('a.router-link').text()).toBe('下一篇标题')
  })

  it('canEdit true for author, false for anonymous', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.vm.canEdit).toBe(false) // not logged in
    m.userReactive.isLoggedIn = true
    expect(wrapper.vm.canEdit).toBe(true) // author userid === 1
  })

  it('formatDate returns empty for falsy and a string otherwise', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01').length).toBeGreaterThan(0)
  })

  it('checks favorite status when logged in', async () => {
    m.userReactive.isLoggedIn = true
    m.favoriteApi.check.mockResolvedValueOnce({ data: { is_favorited: true } })
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(m.favoriteApi.check).toHaveBeenCalledWith('1')
    expect(wrapper.vm.isFavorited).toBe(true)
  })

  it('toggleFavorite redirects anonymous users to Login', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    await wrapper.vm.toggleFavorite()
    expect(push).toHaveBeenCalledWith({ name: 'Login', query: { redirect: '/article/1' } })
  })

  it('toggleFavorite adds then removes favorite when logged in', async () => {
    m.userReactive.isLoggedIn = true
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    await wrapper.vm.toggleFavorite() // not favorited → add
    expect(m.favoriteApi.add).toHaveBeenCalled()
    expect(wrapper.vm.isFavorited).toBe(true)
    await wrapper.vm.toggleFavorite() // favorited → remove
    expect(m.favoriteApi.remove).toHaveBeenCalled()
    expect(wrapper.vm.isFavorited).toBe(false)
  })

  it('submitComment ignores empty input and posts non-empty', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    wrapper.vm.newComment = '   '
    await wrapper.vm.submitComment()
    expect(m.commentApi.create).not.toHaveBeenCalled()
    wrapper.vm.newComment = 'nice'
    await wrapper.vm.submitComment()
    expect(m.commentApi.create).toHaveBeenCalledWith({ articleid: 1, content: 'nice' })
    expect(m.msg.success).toHaveBeenCalledWith('评论发表成功')
  })

  it('reply flow: start (auth gate), cancel, submit', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    // anonymous → redirected
    wrapper.vm.startReply({ commentid: 10 })
    expect(push).toHaveBeenCalledWith({ name: 'Login' })
    // logged in → sets replyingTo
    m.userReactive.isLoggedIn = true
    wrapper.vm.startReply({ commentid: 10 })
    expect(wrapper.vm.replyingTo).toBe(10)
    wrapper.vm.replyContent = 'reply!'
    await wrapper.vm.submitReply({ commentid: 10 })
    expect(m.commentApi.create).toHaveBeenCalledWith({ articleid: 1, content: 'reply!', replyid: 10 })
    expect(wrapper.vm.replyingTo).toBe(null) // cancelReply called
    // cancelReply directly
    wrapper.vm.replyingTo = 5
    wrapper.vm.cancelReply()
    expect(wrapper.vm.replyingTo).toBe(null)
  })

  it('submitReply ignores empty content', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    wrapper.vm.replyContent = '  '
    await wrapper.vm.submitReply({ commentid: 10 })
    expect(m.commentApi.create).not.toHaveBeenCalled()
  })

  it('agree/oppose increment counts when logged in, gate when not', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    const c = { commentid: 10, agreecount: 0, opposecount: 0 }
    // anonymous gate
    await wrapper.vm.agreeComment(c)
    expect(push).toHaveBeenCalledWith({ name: 'Login' })
    expect(m.commentApi.agree).not.toHaveBeenCalled()
    m.userReactive.isLoggedIn = true
    await wrapper.vm.agreeComment(c)
    expect(c.agreecount).toBe(1)
    await wrapper.vm.opposeComment(c)
    expect(c.opposecount).toBe(1)
  })

  it('editArticle navigates to edit route', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    wrapper.vm.editArticle()
    expect(push).toHaveBeenCalledWith({ name: 'EditArticle', params: { id: 1 } })
  })

  it('fetchArticle handles API failure gracefully', async () => {
    m.articleApi.getDetail.mockRejectedValueOnce(new Error('boom'))
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)
  })

  it('refetches when route id changes (watch)', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    m.articleApi.getDetail.mockClear()
    // Mutate the same reactive route object the component captured at mount.
    routeState.current.params.id = '2'
    await wrapper.vm.$nextTick()
    await flushPromises()
    expect(m.articleApi.getDetail).toHaveBeenCalledWith('2')
  })

  it('replaces navigation data when the route changes', async () => {
    m.articleApi.getDetail
      .mockResolvedValueOnce({
        data: {
          articleid: 1,
          headline: '第一篇文章',
          type: 101,
          userid: 1,
          content: '<p>first</p>',
          navigation: { previous: null, next: { articleid: 2, headline: '第二篇文章' } }
        }
      })
      .mockResolvedValueOnce({
        data: {
          articleid: 2,
          headline: '第二篇文章',
          type: 101,
          userid: 1,
          content: '<p>second</p>',
          navigation: { previous: { articleid: 1, headline: '第一篇文章' }, next: null }
        }
      })

    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.get('.article-navigation__next').text()).toContain('第二篇文章')

    routeState.current.params.id = '2'
    await wrapper.vm.$nextTick()
    await flushPromises()

    expect(wrapper.get('.article-navigation__previous').text()).toContain('第一篇文章')
    expect(wrapper.get('.article-navigation__next').text()).toContain('暂无下一篇文章')
  })

  it('renders el-skeleton placeholder while loading (first paint)', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    // Before async fetch resolves the component is in its loading state.
    expect(wrapper.vm.loading).toBe(true)
    expect(wrapper.find('.loading-container').exists()).toBe(true)
    expect(wrapper.find('.el-skeleton').exists()).toBe(true)
    // The real article container is not rendered yet (no abrupt content).
    expect(wrapper.find('.article-container').exists()).toBe(false)
  })

  it('replaces skeleton with article content once loading completes', async () => {
    const wrapper = mount(ArticleDetail, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)
    // Skeleton placeholder is gone, real content is shown.
    expect(wrapper.find('.loading-container').exists()).toBe(false)
    expect(wrapper.find('.el-skeleton').exists()).toBe(false)
    expect(wrapper.find('.article-container').exists()).toBe(true)
    expect(wrapper.find('.article-title').text()).toBe('Hello')
  })
})
