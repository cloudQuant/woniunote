import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

// ---- Shared mocks ----
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: {}, query: {} })
}))

const success = vi.fn()
const error = vi.fn()
// notifyError calls ElMessage({...}) as a function (Epic 18.1); keep the
// .success/.error methods working for the existing assertions.
const toast = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: Object.assign((...a) => toast(...a), {
    success: (...a) => success(...a),
    error: (...a) => error(...a)
  })
}))

const api = vi.hoisted(() => ({
  articleApi: {
    getMyList: vi.fn(() => Promise.resolve({ data: [{ articleid: 1, headline: 'A', type: 1, drafted: 0 }], total: 1 })),
    delete: vi.fn(() => Promise.resolve({}))
  },
  myCommentApi: { getMyComments: vi.fn(() => Promise.resolve({ data: [{ commentid: 5, content: 'hi', article_id: 2 }], total: 1 })) },
  commentApi: { delete: vi.fn(() => Promise.resolve({})) },
  draftApi: { getMyDrafts: vi.fn(() => Promise.resolve({ data: [{ articleid: 3, headline: 'D', type: 102, updatetime: '2026-01-01' }], total: 1 })) },
  favoriteApi: {
    getList: vi.fn(() => Promise.resolve({ data: [{ favoriteid: 7, articleid: 9, article: { articleid: 9, headline: 'Fav', readcount: 3 } }], total: 1 })),
    remove: vi.fn(() => Promise.resolve({}))
  },
  creditApi: {
    getSummary: vi.fn(() => Promise.resolve({ data: { total_credit: 100, type_stats: { 登录: { total: 5, count: 5 } } } })),
    getList: vi.fn(() => Promise.resolve({ data: [{ creditid: 1, category: '登录', credit: 1 }], total: 1 }))
  },
  userApi: {
    updateProfile: vi.fn(() => Promise.resolve({ data: { nickname: 'new' } })),
    updatePassword: vi.fn(() => Promise.resolve({}))
  },
  uploadApi: { uploadAvatar: vi.fn(() => Promise.resolve({ data: { url: '/uploads/a.png' } })) }
}))
vi.mock('@/api', () => api)

const articleStoreMock = vi.hoisted(() => ({
  fetchArticleTypes: vi.fn(() => Promise.resolve({})),
  getTypeName: vi.fn((id) => `type-${id}`),
  categoryOptions: [
    { value: 1, label: '交易策略', children: [{ value: 101, label: 'CTA策略' }] },
    { value: 2, label: '量化框架' }
  ]
}))

vi.mock('@/stores/article', () => ({
  useArticleStore: () => articleStoreMock
}))

vi.mock('./ArticleCategoryCenter.vue', () => ({
  default: {
    name: 'ArticleCategoryCenter',
    props: ['showHeader'],
    template: '<div class="category-center-stub">分类管理</div>'
  }
}))

import MyArticles from './MyArticles.vue'
import MyComments from './MyComments.vue'
import MyDrafts from './MyDrafts.vue'
import MyFavorites from './MyFavorites.vue'
import MyCredits from './MyCredits.vue'
import Profile from './Profile.vue'

// el-pagination 桩：声明 v-model 事件，避免 Vue 对未声明事件的告警（同 MathHistory.spec）。
const paginationStub = {
  name: 'el-pagination',
  props: ['currentPage', 'pageSize', 'total', 'layout'],
  emits: ['update:current-page', 'current-change'],
  template: '<div class="el-pagination" />'
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  articleStoreMock.fetchArticleTypes.mockReset()
  articleStoreMock.fetchArticleTypes.mockResolvedValue({})
  articleStoreMock.getTypeName.mockImplementation((id) => `type-${id}`)
})

describe('MyArticles.vue', () => {
  it('loads articles on mount', async () => {
    const wrapper = mount(MyArticles, mountOptions())
    await flushPromises()
    expect(api.articleApi.getMyList).toHaveBeenCalled()
    expect(wrapper.vm.articles.length).toBe(1)
    expect(wrapper.vm.loading).toBe(false)
  })

  it('getTypeName/formatDate helpers', async () => {
    const wrapper = mount(MyArticles, mountOptions())
    expect(wrapper.vm.getTypeName(1)).toBe('type-1')
    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01')).not.toBe('')
  })

  it('keeps loading articles when category loading fails', async () => {
    articleStoreMock.fetchArticleTypes.mockRejectedValueOnce(new Error('types fail'))
    const wrapper = mount(MyArticles, mountOptions())
    await flushPromises()
    expect(api.articleApi.getMyList).toHaveBeenCalled()
    expect(wrapper.vm.loading).toBe(false)
  })

  it('shows category management tab on the articles page for logged-in users', async () => {
    localStorage.setItem('user', JSON.stringify({ userid: 1, role: 'user', nickname: 'tester' }))
    localStorage.setItem('token', 'tok')
    const wrapper = mount(MyArticles, mountOptions())
    await flushPromises()
    expect(wrapper.find('.category-center-stub').exists()).toBe(true)
    expect(wrapper.text()).toContain('分类管理')
  })

  it('editArticle navigates to EditArticle', () => {
    const wrapper = mount(MyArticles, mountOptions())
    wrapper.vm.editArticle({ articleid: 42 })
    expect(push).toHaveBeenCalledWith({ name: 'EditArticle', params: { id: 42 } })
  })

  it('deleteArticle calls API and refetches', async () => {
    const wrapper = mount(MyArticles, mountOptions())
    await flushPromises()
    await wrapper.vm.deleteArticle({ articleid: 1 })
    expect(api.articleApi.delete).toHaveBeenCalledWith(1)
    expect(success).toHaveBeenCalledWith('删除成功')
  })

  it('fetchArticles handles errors', async () => {
    api.articleApi.getMyList.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(MyArticles, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)
  })
})

describe('MyComments.vue', () => {
  it('loads comments and deletes', async () => {
    const wrapper = mount(MyComments, mountOptions())
    await flushPromises()
    expect(wrapper.vm.comments.length).toBe(1)
    await wrapper.vm.deleteComment({ commentid: 5 })
    expect(api.commentApi.delete).toHaveBeenCalledWith(5)
    expect(success).toHaveBeenCalledWith('评论已删除')
  })

  it('handles fetch + delete errors', async () => {
    api.myCommentApi.getMyComments.mockRejectedValueOnce(new Error('x'))
    const wrapper = mount(MyComments, mountOptions())
    await flushPromises()
    api.commentApi.delete.mockRejectedValueOnce(new Error('y'))
    await wrapper.vm.deleteComment({ commentid: 5 })
    expect(wrapper.vm.loading).toBe(false)
  })

  it('formats dates, tolerating empty input', async () => {
    const wrapper = mount(MyComments, mountOptions())
    await flushPromises()
    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01')).not.toBe('')
  })

  it('renders comments without an article link and deletes via popconfirm', async () => {
    api.myCommentApi.getMyComments.mockResolvedValueOnce({
      data: [{
        commentid: 9,
        content: 'plain comment',
        article_id: 0,
        article_headline: '',
        createtime: '',
        agreecount: 0,
        opposecount: 0
      }],
      total: 30
    })
    const wrapper = mount(MyComments, mountOptions())
    await flushPromises()

    expect(wrapper.findAll('.router-link')).toHaveLength(0)

    wrapper.findComponent({ name: 'el-popconfirm' }).vm.$emit('confirm')
    await flushPromises()
    expect(api.commentApi.delete).toHaveBeenCalledWith(9)
    expect(success).toHaveBeenCalledWith('评论已删除')
  })

  it('paginates comments when the total exceeds the page size', async () => {
    api.myCommentApi.getMyComments.mockResolvedValueOnce({
      data: [{ commentid: 5, content: 'hi', article_id: 2, article_headline: 'A' }],
      total: 45
    })
    const wrapper = mount(MyComments, mountOptions({ stubs: { 'el-pagination': paginationStub } }))
    await flushPromises()

    const pagination = wrapper.findComponent({ name: 'el-pagination' })
    expect(pagination.exists()).toBe(true)
    pagination.vm.$emit('update:current-page', 3)
    pagination.vm.$emit('current-change', 3)
    await flushPromises()
    expect(wrapper.vm.currentPage).toBe(3)
    expect(api.myCommentApi.getMyComments).toHaveBeenCalledWith({ page: 3, page_size: 20 })
  })

  it('shows the empty state when there are no comments', async () => {
    api.myCommentApi.getMyComments.mockResolvedValueOnce({ data: [], total: 0 })
    const wrapper = mount(MyComments, mountOptions())
    await flushPromises()
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })
})

describe('MyDrafts.vue', () => {
  it('loads drafts and computes type names (parent + leaf)', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    expect(wrapper.vm.drafts.length).toBe(1)
    expect(wrapper.vm.getTypeName(102)).toBe('交易策略') // 102 → parent 1
    expect(wrapper.vm.getTypeName(2)).toBe('量化框架')
    expect(wrapper.vm.getTypeName(99999)).toBe('未分类')
  })

  it('editDraft + deleteDraft', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    wrapper.vm.editDraft({ articleid: 3 })
    expect(push).toHaveBeenCalledWith({ name: 'EditArticle', params: { id: 3 } })
    await wrapper.vm.deleteDraft({ articleid: 3 })
    expect(api.articleApi.delete).toHaveBeenCalledWith(3)
  })

  it('handles date/type edge cases', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01')).not.toBe('')
    expect(wrapper.vm.getTypeName(99)).toBe('未分类')
  })

  it('navigates to the editor when clicking continue editing', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    push.mockClear()

    wrapper.findAllComponents({ name: 'el-button' })[0].vm.$emit('click')
    await flushPromises()
    expect(push).toHaveBeenCalledWith({ name: 'EditArticle', params: { id: 3 } })
  })

  it('deletes a draft after popconfirm confirmation', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()

    wrapper.findComponent({ name: 'el-popconfirm' }).vm.$emit('confirm')
    await flushPromises()
    expect(api.articleApi.delete).toHaveBeenCalledWith(3)
    expect(success).toHaveBeenCalledWith('草稿已删除')
  })

  it('paginates drafts when the total exceeds the page size', async () => {
    api.draftApi.getMyDrafts.mockResolvedValueOnce({
      data: [{ articleid: 3, headline: 'D', type: 2, updatetime: '' }],
      total: 25
    })
    const wrapper = mount(MyDrafts, mountOptions({ stubs: { 'el-pagination': paginationStub } }))
    await flushPromises()

    const pagination = wrapper.findComponent({ name: 'el-pagination' })
    expect(pagination.exists()).toBe(true)
    pagination.vm.$emit('update:current-page', 2)
    pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(wrapper.vm.currentPage).toBe(2)
    expect(api.draftApi.getMyDrafts).toHaveBeenCalledWith({ page: 2, page_size: 10 })
  })

  it('shows the empty state and routes to the editor', async () => {
    api.draftApi.getMyDrafts.mockResolvedValueOnce({ data: [], total: 0 })
    const routerPush = vi.fn()
    const wrapper = mount(MyDrafts, mountOptions({ mocks: { $router: { push: routerPush } } }))
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    wrapper.find('.el-empty').findComponent({ name: 'el-button' }).vm.$emit('click')
    await flushPromises()
    expect(routerPush).toHaveBeenCalledWith({ name: 'WriteArticle' })
  })

  it('handles fetch and delete failures', async () => {
    api.draftApi.getMyDrafts.mockRejectedValueOnce(new Error('fetch fail'))
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)

    api.articleApi.delete.mockRejectedValueOnce(new Error('delete fail'))
    await wrapper.vm.deleteDraft({ articleid: 3 })
    expect(success).not.toHaveBeenCalled()
  })

  it('shows the scenario fallback toast when fetching drafts fails with an empty message', async () => {
    api.draftApi.getMyDrafts.mockRejectedValueOnce(
      Object.assign(new Error(''), { response: { status: 500 } })
    )
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    expect(toast).toHaveBeenCalledWith({
      message: '获取草稿列表失败',
      type: 'error',
      grouping: true
    })
    expect(wrapper.vm.loading).toBe(false)
  })

  it('shows the server message toast when deleting a draft fails with HTTP 500', async () => {
    const wrapper = mount(MyDrafts, mountOptions())
    await flushPromises()
    api.articleApi.delete.mockRejectedValueOnce(
      Object.assign(new Error('服务器内部错误'), { response: { status: 500 } })
    )
    await wrapper.vm.deleteDraft({ articleid: 3 })
    expect(toast).toHaveBeenCalledWith({
      message: '服务器内部错误',
      type: 'error',
      grouping: true
    })
  })
})

describe('MyFavorites.vue', () => {
  it('loads favorites and removes one', async () => {
    const wrapper = mount(MyFavorites, mountOptions())
    await flushPromises()
    expect(wrapper.vm.favorites.length).toBe(1)
    await wrapper.vm.removeFavorite({ articleid: 9 })
    expect(api.favoriteApi.remove).toHaveBeenCalledWith(9)
    expect(success).toHaveBeenCalledWith('已取消收藏')
  })

  it('normalizes the flat article array returned by the C++ backend', async () => {
    api.favoriteApi.getList.mockResolvedValueOnce({
      data: [{ articleid: 12, headline: 'Flat Favorite', readcount: 8, createtime: '2026-01-01' }]
    })
    const wrapper = mount(MyFavorites, mountOptions())
    await flushPromises()
    expect(wrapper.vm.favorites[0].article.headline).toBe('Flat Favorite')
    await wrapper.vm.removeFavorite(wrapper.vm.favorites[0])
    expect(api.favoriteApi.remove).toHaveBeenCalledWith(12)
  })

  it('does not remove a favorite when the article id is missing', async () => {
    const wrapper = mount(MyFavorites, mountOptions())
    await flushPromises()
    api.favoriteApi.remove.mockClear()
    await wrapper.vm.removeFavorite({})
    expect(api.favoriteApi.remove).not.toHaveBeenCalled()
    expect(error).toHaveBeenCalledWith('文章ID不存在')
  })

  it('handles favorite fetch and remove errors', async () => {
    api.favoriteApi.getList.mockRejectedValueOnce(new Error('fetch fail'))
    const wrapper = mount(MyFavorites, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)

    api.favoriteApi.remove.mockRejectedValueOnce(new Error('remove fail'))
    await wrapper.vm.removeFavorite({ articleid: 9 })
    expect(wrapper.vm.loading).toBe(false)
  })
})

describe('MyCredits.vue', () => {
  it('loads summary and credit records', async () => {
    const wrapper = mount(MyCredits, mountOptions())
    await flushPromises()
    expect(wrapper.vm.summary.total_credit).toBe(100)
    expect(wrapper.vm.credits.length).toBe(1)
  })

  it('handles summary error', async () => {
    api.creditApi.getSummary.mockRejectedValueOnce(new Error('x'))
    const wrapper = mount(MyCredits, mountOptions())
    await flushPromises()
    expect(wrapper.vm.summaryLoading).toBe(false)
  })

  it('formats dates and renders negative/zero credit records', async () => {
    api.creditApi.getSummary.mockResolvedValueOnce({
      data: {
        total_credit: -5,
        type_stats: { 扣减: { total: -3, count: 2 }, 清零: { total: 0, count: 1 } }
      }
    })
    api.creditApi.getList.mockResolvedValueOnce({
      data: [
        { creditid: 2, category: '扣减', credit: -3, createtime: '' },
        { creditid: 3, category: '清零', credit: 0, createtime: '' }
      ],
      total: 40
    })
    const wrapper = mount(MyCredits, mountOptions())
    await flushPromises()

    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01')).not.toBe('')
    const items = wrapper.findAll('.credit-item')
    expect(items).toHaveLength(2)
    expect(items[0].classes()).toContain('negative')
    expect(items[0].text()).toContain('-3')
    expect(items[1].classes()).not.toContain('positive')
  })

  it('falls back to an empty type_stats object', async () => {
    api.creditApi.getSummary.mockResolvedValueOnce({ data: { total_credit: 0 } })
    const wrapper = mount(MyCredits, mountOptions())
    await flushPromises()
    expect(wrapper.vm.summary.type_stats).toEqual({})
  })

  it('paginates credit records and refetches on page change', async () => {
    api.creditApi.getList.mockResolvedValueOnce({
      data: [{ creditid: 1, category: '登录', credit: 1, createtime: '2026-01-01' }],
      total: 40
    })
    const wrapper = mount(MyCredits, mountOptions({ stubs: { 'el-pagination': paginationStub } }))
    await flushPromises()

    const pagination = wrapper.findComponent({ name: 'el-pagination' })
    expect(pagination.exists()).toBe(true)
    pagination.vm.$emit('update:current-page', 2)
    pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(wrapper.vm.currentPage).toBe(2)
    expect(api.creditApi.getList).toHaveBeenCalledWith({ page: 2, page_size: 20 })
  })

  it('handles credit list errors and shows the empty state', async () => {
    api.creditApi.getList.mockRejectedValueOnce(new Error('list fail'))
    const wrapper = mount(MyCredits, mountOptions())
    await flushPromises()
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })
})

describe('Profile.vue', () => {
  function withUser() {
    const opts = mountOptions()
    return opts
  }

  it('initializes form from user store on mount', async () => {
    // Seed a user into the store via localStorage before mount.
    localStorage.setItem('user', JSON.stringify({ nickname: 'bob', avatar: '/a.png', qq: '123' }))
    localStorage.setItem('token', 'tok')
    const wrapper = mount(Profile, withUser())
    await flushPromises()
    expect(wrapper.vm.form.nickname).toBe('bob')
    localStorage.clear()
  })

  it('uploadAvatar sets avatar url', async () => {
    const wrapper = mount(Profile, withUser())
    await wrapper.vm.uploadAvatar({ file: new Blob(['x']) })
    expect(wrapper.vm.form.avatar).toBe('/uploads/a.png')
    expect(success).toHaveBeenCalledWith('头像上传成功')
  })

  it('confirm password validator', () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordForm.new_password = 'abcdef'
    const rule = wrapper.vm.passwordRules.confirm_password.find((r) => r.validator)
    let e1 = null; rule.validator(null, 'zzz', (e) => { e1 = e })
    expect(e1).toBeInstanceOf(Error)
    let e2 = 'x'; rule.validator(null, 'abcdef', (e) => { e2 = e })
    expect(e2).toBeUndefined()
  })

  it('saveProfile validates, updates and shows success', async () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.saveProfile()
    expect(api.userApi.updateProfile).toHaveBeenCalled()
    expect(success).toHaveBeenCalledWith('保存成功')
  })

  it('saveProfile aborts on invalid form', async () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.saveProfile()
    expect(api.userApi.updateProfile).not.toHaveBeenCalled()
  })

  it('changePassword validates, calls API and resets', async () => {
    const reset = vi.fn()
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordFormRef = { validate: vi.fn(() => Promise.resolve(true)), resetFields: reset }
    wrapper.vm.passwordForm.old_password = 'oldpass'
    wrapper.vm.passwordForm.new_password = 'newpass'
    await wrapper.vm.changePassword()
    expect(api.userApi.updatePassword).toHaveBeenCalledWith({ old_password: 'oldpass', new_password: 'newpass' })
    expect(reset).toHaveBeenCalled()
  })

  it('changePassword aborts on invalid form', async () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordFormRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.changePassword()
    expect(api.userApi.updatePassword).not.toHaveBeenCalled()
  })

  it('binds v-model inputs to the profile and password forms', async () => {
    const wrapper = mount(Profile, withUser())
    const inputs = wrapper.findAllComponents({ name: 'el-input' })
    expect(inputs.length).toBe(6)

    inputs.forEach((input, index) => input.vm.$emit('update:modelValue', `v${index}`))
    await flushPromises()
    expect(wrapper.vm.form.nickname).toBe('v1')
    expect(wrapper.vm.form.qq).toBe('v2')
    expect(wrapper.vm.passwordForm.old_password).toBe('v3')
    expect(wrapper.vm.passwordForm.new_password).toBe('v4')
    expect(wrapper.vm.passwordForm.confirm_password).toBe('v5')
  })

  it('handles avatar upload failure', async () => {
    api.uploadApi.uploadAvatar.mockRejectedValueOnce(new Error('upload fail'))
    const wrapper = mount(Profile, withUser())
    await wrapper.vm.uploadAvatar({ file: new Blob(['x']) })
    expect(success).not.toHaveBeenCalled()
    expect(wrapper.vm.form.avatar).toBe('')
  })

  it('saveProfile returns early when the form ref is missing', async () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.formRef = null
    await wrapper.vm.saveProfile()
    expect(api.userApi.updateProfile).not.toHaveBeenCalled()
  })

  it('saveProfile handles API failures', async () => {
    api.userApi.updateProfile.mockRejectedValueOnce(new Error('save fail'))
    const wrapper = mount(Profile, withUser())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.saveProfile()
    expect(success).not.toHaveBeenCalled()
    expect(wrapper.vm.saving).toBe(false)
  })

  it('saveProfile surfaces the server message on an HTTP 500 rejection', async () => {
    api.userApi.updateProfile.mockRejectedValueOnce(
      Object.assign(new Error('服务器内部错误'), { response: { status: 500 } })
    )
    const wrapper = mount(Profile, withUser())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.saveProfile()
    expect(toast).toHaveBeenCalledWith({
      message: '服务器内部错误',
      type: 'error',
      grouping: true
    })
    expect(wrapper.vm.saving).toBe(false)
  })

  it('changePassword falls back to the scenario message on an empty rejection message', async () => {
    api.userApi.updatePassword.mockRejectedValueOnce(new Error(''))
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordFormRef = {
      validate: vi.fn(() => Promise.resolve(true)),
      resetFields: vi.fn()
    }
    await wrapper.vm.changePassword()
    expect(toast).toHaveBeenCalledWith({
      message: '修改密码失败',
      type: 'error',
      grouping: true
    })
  })

  it('changePassword returns early when the form ref is missing', async () => {
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordFormRef = null
    await wrapper.vm.changePassword()
    expect(api.userApi.updatePassword).not.toHaveBeenCalled()
  })

  it('changePassword handles API failures', async () => {
    api.userApi.updatePassword.mockRejectedValueOnce(new Error('pw fail'))
    const wrapper = mount(Profile, withUser())
    wrapper.vm.passwordFormRef = { validate: vi.fn(() => Promise.resolve(true)), resetFields: vi.fn() }
    await wrapper.vm.changePassword()
    expect(success).not.toHaveBeenCalled()
    expect(wrapper.vm.changingPassword).toBe(false)
  })

  it('falls back to empty profile fields when user values are missing', async () => {
    localStorage.setItem('user', JSON.stringify({ nickname: '', avatar: '', qq: '' }))
    localStorage.setItem('token', 'tok')
    const wrapper = mount(Profile, withUser())
    await flushPromises()
    expect(wrapper.vm.form.nickname).toBe('')
    expect(wrapper.vm.form.avatar).toBe('')
    expect(wrapper.vm.form.qq).toBe('')
  })
})
