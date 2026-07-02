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
vi.mock('element-plus', () => ({
  ElMessage: { success: (...a) => success(...a), error: (...a) => error(...a) }
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
})
