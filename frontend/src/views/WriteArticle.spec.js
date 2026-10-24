import { describe, it, expect, vi, beforeEach } from 'vitest'
import { reactive } from 'vue'
import { createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['log', 'error'])

const routeState = vi.hoisted(() => ({ params: {}, fullPath: '/write', path: '/write' }))
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({ push })
}))

const m = vi.hoisted(() => ({
  useActualStore: false,
  msg: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
  editorFlush: vi.fn(),
  editorContent: '<p>flushed editor content</p>',
  authApi: {
    login: vi.fn(({ username }) => Promise.resolve({ data: {
      access_token: `${username}-access`,
      refresh_token: `${username}-refresh`,
      user: { userid: username === 'first' ? 1 : 2, username, nickname: `${username} profile` }
    } }))
  },
  articleApi: {
    create: vi.fn(() => Promise.resolve({ data: { articleid: 11 } })),
    update: vi.fn(() => Promise.resolve({ data: { articleid: 22 } })),
    getDetail: vi.fn(() => Promise.resolve({ data: {
      headline: 'X', type: 102, content: 'c', thumbnail: 't.png', credit: 0, drafted: 0
    } }))
  },
  uploadApi: { uploadImage: vi.fn(() => Promise.resolve({ data: {
    url: '/uploads/uploads/images/2026/10/1_1000.png'
  } })) },
  store: {
    categoryOptions: [
      { value: 1, label: '交易策略', children: [
        { value: 101, label: '股票策略' },
        { value: 102, label: '期货策略' }
      ] },
      { value: 2, label: '量化框架' }
    ],
    getTypePath: vi.fn((type) => (type >= 100 ? [Math.floor(type / 100), type] : [type]))
  },
  user: { user: { userid: 'owner-1' } }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/api', () => ({ authApi: m.authApi, articleApi: m.articleApi, uploadApi: m.uploadApi }))
vi.mock('@/utils/authSessionStorage', async () => {
  const { authSessionStorageMock } = await import('@/test/authSessionStorageMock')
  return { authSessionStorage: authSessionStorageMock }
})
vi.mock('@/stores/user', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useUserStore: (...args) => m.useActualStore ? actual.useUserStore(...args) : m.user
  }
})
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    fetchArticleTypes: vi.fn(() => Promise.resolve({})),
    articleTypes: { 1: '交易策略', 101: '股票策略', 102: '期货策略', 2: '量化框架' },
    get categoryOptions() { return m.store.categoryOptions },
    getTypePath: m.store.getTypePath
  })
}))
vi.mock('@/components/editor/UEditor.vue', () => ({
  default: {
    name: 'UEditor',
    emits: ['update:modelValue', 'ready'],
    setup(_, { emit, expose }) {
      expose({
        flushContent: () => {
          m.editorFlush()
          emit('update:modelValue', m.editorContent)
        }
      })
      return () => null
    }
  }
}))

import WriteArticle from './WriteArticle.vue'
import { useUserStore } from '@/stores/user'
import { authSessionStorageMock } from '@/test/authSessionStorageMock'
import { readEditorRecovery, saveEditorRecovery } from '@/utils/editorRecovery'

describe('WriteArticle.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.useActualStore = false
    routeState.params = {}
    routeState.fullPath = '/write'
    routeState.path = '/write'
    m.user = createUserSession({ userid: 'owner-1' })
    m.editorContent = '<p>flushed editor content</p>'
    localStorage.clear()
    authSessionStorageMock.reset()
    m.store.categoryOptions = [
      { value: 1, label: '交易策略', children: [
        { value: 101, label: '股票策略' },
        { value: 102, label: '期货策略' }
      ] },
      { value: 2, label: '量化框架' }
    ]
  })

  function createUserSession(user) {
    const state = reactive({
      user: { ...user },
      epoch: 'epoch-owner-1',
      token: 'owner-1-access',
      refreshToken: 'owner-1-refresh',
      generation: 0,
      durableSession: null
    })
    state.syncSession = vi.fn(async () => {
      if (state.durableSession) {
        Object.assign(state, state.durableSession)
        state.durableSession = null
      }
    })
    state.captureCredentials = vi.fn(() => ({
      generation: state.generation,
      epoch: state.epoch,
      token: state.token,
      refreshToken: state.refreshToken,
      userIdentity: state.user?.userid ? `id:${state.user.userid}` : null,
      userId: state.user?.userid ?? state.user?.id ?? state.user?.username ?? null
    }))
    state.isSessionCurrent = vi.fn((snapshot) => snapshot?.generation === state.generation &&
      snapshot?.epoch === state.epoch &&
      snapshot?.userIdentity === (state.user?.userid ? `id:${state.user.userid}` : null))
    state.isCredentialsCurrent = vi.fn((snapshot) => state.isSessionCurrent(snapshot) &&
      snapshot?.token === state.token && snapshot?.refreshToken === state.refreshToken)
    return state
  }

  it('builds categoryOptions with nested children', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    const opts = wrapper.vm.categoryOptions
    const trading = opts.find((o) => o.value === 1)
    expect(trading.children.map((c) => c.value)).toEqual([101, 102])
    // Category 2 has no children → children key removed.
    const framework = opts.find((o) => o.value === 2)
    expect(framework.children).toBeUndefined()
  })

  it('falls back to an empty category list when the store has none', () => {
    m.store.categoryOptions = null
    const wrapper = mount(WriteArticle, mountOptions())
    expect(wrapper.vm.categoryOptions).toEqual([])
  })

  it('two-way binds the editor fields to the form model', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.findComponent({ name: 'el-input' }).vm.$emit('update:modelValue', '标题')
    wrapper.findComponent({ name: 'UEditor' }).vm.$emit('update:modelValue', '<p>正文</p>')
    wrapper.findComponent({ name: 'el-cascader' }).vm.$emit('update:modelValue', [1, 101])
    wrapper.findComponent({ name: 'el-input-number' }).vm.$emit('update:modelValue', 30)
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.form.headline).toBe('标题')
    expect(wrapper.vm.form.content).toBe('<p>正文</p>')
    expect(wrapper.vm.form.typeArray).toEqual([1, 101])
    expect(wrapper.vm.form.credit).toBe(30)
  })

  it('UEditor ready callback is wired through the template', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    expect(() => wrapper.findComponent({ name: 'UEditor' }).vm.$emit('ready')).not.toThrow()
  })

  it('keeps the editor unavailable when the authoritative session cannot initialize', async () => {
    m.useActualStore = true
    const storageError = new Error('IndexedDB unavailable')
    const readCurrent = vi.spyOn(authSessionStorageMock, 'readCurrent')
      .mockRejectedValueOnce(storageError)
    let wrapper
    try {
      const pinia = createPinia()
      const store = useUserStore(pinia)
      const options = mountOptions()
      options.global.plugins = [pinia]
      wrapper = mount(WriteArticle, options)
      await flushPromises()

      expect(store.isLoggedIn).toBe(false)
      expect(wrapper.vm.editorOwnerReady).toBe(false)
      expect(m.articleApi.getDetail).not.toHaveBeenCalled()
      expect(m.articleApi.create).not.toHaveBeenCalled()
      expect(m.msg).toHaveBeenCalledWith(expect.objectContaining({
        message: 'IndexedDB unavailable', type: 'error'
      }))
    } finally {
      wrapper?.unmount()
      readCurrent.mockRestore()
    }
  })

  it('unlocks edit mode with server content and warns when recovery storage cannot be read', async () => {
    routeState.params = { id: '22' }
    routeState.fullPath = '/edit/22'
    routeState.path = '/edit/22'
    const originalGetItem = localStorage.getItem.bind(localStorage)
    const storageRead = vi.spyOn(localStorage, 'getItem').mockImplementation((key) => {
      if (String(key).startsWith('woniunote:editor-recovery:')) {
        throw new Error('Storage access denied')
      }
      return originalGetItem(key)
    })
    let wrapper
    try {
      wrapper = mount(WriteArticle, mountOptions())
      await flushPromises()

      expect(wrapper.vm.editorOwnerReady).toBe(true)
      expect(wrapper.vm.editorOwnerChanged).toBe(false)
      expect(wrapper.vm.form).toMatchObject({ headline: 'X', type: 102, content: 'c' })
      expect(m.msg.warning).toHaveBeenCalledWith(
        '本地编辑恢复稿无法读取，已加载服务器内容；请检查浏览器存储设置'
      )
    } finally {
      storageRead.mockRestore()
      wrapper?.unmount()
    }
  })

  it('keeps recovered content editable when the browser cannot clear its saved copy', async () => {
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', () => ({
      headline: 'Recovered title',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Recovered body</p>'
    }))
    await saveEditorRecovery('owner-1', '/write')
    unregister()

    const originalRemoveItem = localStorage.removeItem.bind(localStorage)
    const storageRemove = vi.spyOn(localStorage, 'removeItem').mockImplementation((key) => {
      if (String(key).startsWith('woniunote:editor-recovery:')) {
        throw new Error('Storage access denied')
      }
      return originalRemoveItem(key)
    })
    m.msg.warning.mockImplementationOnce(() => {
      throw new Error('message service unavailable')
    })
    let wrapper
    try {
      wrapper = mount(WriteArticle, mountOptions())
      await flushPromises()

      expect(wrapper.vm.editorOwnerReady).toBe(true)
      expect(wrapper.vm.editorOwnerChanged).toBe(false)
      expect(wrapper.vm.form).toMatchObject({
        headline: 'Recovered title', content: '<p>Recovered body</p>'
      })
      expect(m.msg.warning).toHaveBeenCalledWith('已恢复未保存内容，但无法清理本地恢复副本')
    } finally {
      storageRemove.mockRestore()
      wrapper?.unmount()
    }
  })

  it('does not restore one account recovery into another account', async () => {
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', () => ({
      headline: 'A private headline',
      type: 101,
      typeArray: [1, 101],
      content: '<p>A private body</p>',
      thumbnail: '/a-private.png'
    }))
    try {
      await saveEditorRecovery('owner-1', '/write')
    } finally {
      unregister()
    }

    m.user = createUserSession({ userid: 'owner-2' })
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()

    expect(wrapper.vm.editorOwnerReady).toBe(true)
    expect(wrapper.vm.form.headline).toBe('')
    expect(wrapper.vm.form.content).toBe('')
    expect(readEditorRecovery('owner-1', '/write')?.draft.headline).toBe('A private headline')
    expect(readEditorRecovery('owner-2', '/write')).toBeNull()
    expect(m.msg.info).not.toHaveBeenCalledWith('已恢复上次未保存的编辑内容')
    wrapper.unmount()
  })

  it('saves the flushed same-account draft synchronously when the page is hidden', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Title immediately before reload'
    wrapper.vm.form.content = '<p>stale model content</p>'
    m.editorContent = '<p>latest iframe content</p>'

    window.dispatchEvent(new Event('pagehide'))

    expect(m.editorFlush).toHaveBeenCalledOnce()
    expect(readEditorRecovery('owner-1', '/write')?.draft).toMatchObject({
      headline: 'Title immediately before reload',
      content: '<p>latest iframe content</p>'
    })
    expect(readEditorRecovery('owner-2', '/write')).toBeNull()
    wrapper.unmount()
  })

  it('does not overwrite an existing recovery while article details are still loading', async () => {
    routeState.params = { id: '22' }
    routeState.fullPath = '/edit/22'
    routeState.path = '/edit/22'
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', () => ({
      headline: 'Already saved title',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Already saved body</p>'
    }))
    await saveEditorRecovery('owner-1', '/edit/22')
    unregister()

    let resolveDetail
    m.articleApi.getDetail.mockImplementationOnce(() => new Promise((resolve) => {
      resolveDetail = resolve
    }))
    const wrapper = mount(WriteArticle, mountOptions())
    await vi.waitFor(() => expect(resolveDetail).toBeTypeOf('function'))
    expect(wrapper.vm.editorOwnerReady).toBe(false)

    window.dispatchEvent(new Event('pagehide'))

    expect(m.editorFlush).not.toHaveBeenCalled()
    expect(readEditorRecovery('owner-1', '/edit/22')?.draft.headline).toBe('Already saved title')

    resolveDetail({ data: {
      headline: 'Server title', type: 101, content: '<p>Server body</p>',
      thumbnail: '', credit: 0, drafted: 1
    } })
    await flushPromises()

    expect(wrapper.vm.editorOwnerReady).toBe(true)
    expect(wrapper.vm.form).toMatchObject({
      headline: 'Already saved title', content: '<p>Already saved body</p>'
    })
    wrapper.unmount()
  })

  it('preserves prior recovery when a pending detail request expires before editor initialization', async () => {
    routeState.params = { id: '22' }
    routeState.fullPath = '/edit/22'
    routeState.path = '/edit/22'
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', () => ({
      headline: 'Already saved title',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Already saved body</p>'
    }))
    await saveEditorRecovery('owner-1', '/edit/22')
    unregister()

    let failDetailRequest
    let expirationSaveResult
    m.articleApi.getDetail.mockImplementationOnce(() => new Promise((resolve, reject) => {
      failDetailRequest = async () => {
        expirationSaveResult = await saveEditorRecovery('owner-1', '/edit/22')
        m.user.durableSession = {
          epoch: 'expired-epoch', token: '', refreshToken: '', user: null, generation: 1
        }
        await m.user.syncSession()
        reject(Object.assign(new Error('expired'), { response: { status: 401 } }))
      }
    }))

    const wrapper = mount(WriteArticle, mountOptions())
    await vi.waitFor(() => expect(failDetailRequest).toBeTypeOf('function'))
    expect(wrapper.vm.editorOwnerReady).toBe(false)

    await failDetailRequest()
    await vi.waitFor(() => expect(m.msg.warning).toHaveBeenCalledWith(
      '登录账号已切换，当前编辑已隔离；请使用原账号恢复草稿。'
    ))
    await flushPromises()

    expect(expirationSaveResult).toBe(false)
    expect(wrapper.vm.editorOwnerChanged).toBe(true)
    expect(readEditorRecovery('owner-1', '/edit/22')?.draft).toMatchObject({
      headline: 'Already saved title', content: '<p>Already saved body</p>'
    })
    expect(readEditorRecovery('owner-2', '/edit/22')).toBeNull()
    wrapper.unmount()
  })

  it('saveArticle aborts when the form ref is missing', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.formRef = null
    await wrapper.vm.saveDraft()
    expect(m.articleApi.create).not.toHaveBeenCalled()
    expect(wrapper.vm.saving).toBe(false)
  })

  it('uploadThumbnail reports failures without throwing', async () => {
    m.uploadApi.uploadImage.mockRejectedValueOnce(new Error('upload down'))
    const wrapper = mount(WriteArticle, mountOptions())
    await expect(wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })).resolves.toBeUndefined()
    expect(wrapper.vm.form.thumbnail).toBe('')
    expect(m.msg.success).not.toHaveBeenCalled()
  })

  it('ignores unsafe paths returned by the upload API', async () => {
    m.uploadApi.uploadImage.mockResolvedValueOnce({ data: { url: '/uploads/../secret.png' } })
    const wrapper = mount(WriteArticle, mountOptions())

    await wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })

    expect(wrapper.vm.form.thumbnail).toBe('')
    expect(m.msg.error).toHaveBeenCalledWith('上传返回了无效的缩略图路径')
    expect(m.msg.success).not.toHaveBeenCalledWith('上传成功')
  })

  it('saveArticle surfaces API failures and clears the loading flag', async () => {
    m.articleApi.create.mockRejectedValueOnce(new Error('save down'))
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'Boom'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.msg.success).not.toHaveBeenCalledWith('发布成功')
    expect(wrapper.vm.publishing).toBe(false)
    expect(push).not.toHaveBeenCalled()
  })

  it('edit mode falls back to the route id when update omits the article id', async () => {
    routeState.params = { id: '22' }
    m.articleApi.update.mockResolvedValueOnce({ data: null })
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Edited'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: '22' } })
  })

  it('onTypeChange picks the last cascader value or null', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.onTypeChange([1, 102])
    expect(wrapper.vm.form.type).toBe(102)
    wrapper.vm.onTypeChange([])
    expect(wrapper.vm.form.type).toBe(null)
  })

  it('onEditorReady is callable', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    expect(() => wrapper.vm.onEditorReady({})).not.toThrow()
  })

  it('uploadThumbnail sets thumbnail url', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    await wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })
    expect(wrapper.vm.form.thumbnail).toBe('/uploads/uploads/images/2026/10/1_1000.png')
    expect(wrapper.vm.thumbnailPreviewUrl).toBe('/uploads/uploads/images/2026/10/1_1000.png')
    expect(m.msg.success).toHaveBeenCalledWith('上传成功')
  })

  it('previews same-origin upload paths as-is and submits the canonical path', async () => {
    const uploadedPath = '/uploads/uploads/images/2026/10/123_4567.png'
    m.uploadApi.uploadImage.mockResolvedValueOnce({ data: { url: uploadedPath } })
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()

    await wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })
    expect(wrapper.vm.form.thumbnail).toBe(uploadedPath)
    expect(wrapper.vm.thumbnailPreviewUrl).toBe(uploadedPath)

    wrapper.vm.form.headline = 'New'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()

    expect(m.articleApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ thumbnail: uploadedPath }),
      expect.objectContaining({ _sessionSnapshot: expect.any(Object) })
    )
  })

  it('previews a legacy basename through /api/thumb without changing the stored value', async () => {
    routeState.params = { id: '22' }
    m.articleApi.getDetail.mockResolvedValueOnce({ data: {
      headline: 'Legacy', type: 102, content: 'body', thumbnail: '101.png', credit: 0, drafted: 1
    } })
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()

    expect(wrapper.vm.form.thumbnail).toBe('101.png')
    expect(wrapper.vm.thumbnailPreviewUrl).toBe('/api/thumb/101.png?v3')
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()

    expect(m.articleApi.update).toHaveBeenCalledWith(
      '22',
      expect.objectContaining({ thumbnail: '101.png' }),
      expect.objectContaining({ _sessionSnapshot: expect.any(Object) })
    )
  })

  it('rejects an unsafe thumbnail before sending article data', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'Unsafe thumbnail'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.form.thumbnail = '/uploads/../secret.png'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }

    await wrapper.vm.publish()

    expect(m.articleApi.create).not.toHaveBeenCalled()
    expect(m.msg.error).toHaveBeenCalledWith('缩略图路径无效')
  })

  it('publish creates a new article and navigates to detail', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'New'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.articleApi.create).toHaveBeenCalled()
    expect(m.msg.success).toHaveBeenCalledWith('发布成功')
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: 11 } })
  })

  it('saveDraft marks drafted and saves', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'Draft'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.saveDraft()
    expect(wrapper.vm.form.drafted).toBe(1)
    expect(m.msg.success).toHaveBeenCalledWith('草稿已保存')
  })

  it('isolates A recovery and rejects publish when B logs in before the stale editor submits', async () => {
    m.useActualStore = true
    const piniaA = createPinia()
    const storeA = useUserStore(piniaA)
    await storeA.login('first', 'password')
    const options = mountOptions()
    options.global.plugins = [piniaA]
    const wrapper = mount(WriteArticle, options)
    await flushPromises()
    wrapper.vm.form.headline = 'A private headline'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = '<p>A private body</p>'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    m.editorContent = '<p>A flushed private body</p>'
    const storeB = useUserStore(createPinia())
    await storeB.login('second', 'password')
    expect(storeA.user).toMatchObject({ userid: 1, nickname: 'first profile' })

    await wrapper.vm.publish()

    expect(m.articleApi.create).not.toHaveBeenCalled()
    expect(wrapper.vm.form.headline).toBe('')
    expect(readEditorRecovery(1, '/write')?.draft).toMatchObject({
      headline: 'A private headline',
      content: '<p>A flushed private body</p>'
    })
    expect(readEditorRecovery(2, '/write')).toBeNull()
    expect(m.msg.warning).toHaveBeenCalledWith('登录账号已切换，当前编辑已隔离；请使用原账号恢复草稿。')
    expect(storeA.user).toMatchObject({ userid: 2, nickname: 'second profile' })
  })

  it('keeps page-exit recovery with the original account after another tab logs in', async () => {
    m.useActualStore = true
    const piniaA = createPinia()
    const storeA = useUserStore(piniaA)
    await storeA.login('first', 'password')
    const options = mountOptions()
    options.global.plugins = [piniaA]
    const wrapper = mount(WriteArticle, options)
    await flushPromises()
    wrapper.vm.form.headline = 'A private headline'
    wrapper.vm.form.content = '<p>A private body</p>'
    m.editorContent = '<p>A latest body</p>'

    const storeB = useUserStore(createPinia())
    await storeB.login('second', 'password')
    await storeA.syncSession()
    window.dispatchEvent(new Event('pagehide'))
    await vi.waitFor(() => expect(m.msg.warning).toHaveBeenCalledWith(
      '登录账号已切换，当前编辑已隔离；请使用原账号恢复草稿。'
    ))

    expect(readEditorRecovery(1, '/write')?.draft).toMatchObject({
      headline: 'A private headline', content: '<p>A latest body</p>'
    })
    expect(readEditorRecovery(2, '/write')).toBeNull()
    wrapper.unmount()
  })

  it('quarantines the old form and blocks submit if recovery storage fails on account switch', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'A private headline'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = '<p>A private body</p>'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    m.editorContent = '<p>A flushed private body</p>'

    const originalSetItem = localStorage.setItem.bind(localStorage)
    const storageWrite = vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
      if (String(key).startsWith('woniunote:editor-recovery:')) {
        throw new Error('editor recovery quota exceeded')
      }
      return originalSetItem(key, value)
    })

    try {
      m.user.durableSession = {
        epoch: 'epoch-owner-2', token: 'owner-2-access',
        refreshToken: 'owner-2-refresh', user: { userid: 2 }, generation: 1
      }
      await m.user.syncSession()
      await vi.waitFor(() => expect(m.msg.warning).toHaveBeenCalledWith(
        '登录账号已切换，当前编辑已隔离；请使用原账号恢复草稿。'
      ))

      expect(m.msg).toHaveBeenCalledWith(expect.objectContaining({
        message: 'editor recovery quota exceeded', type: 'error'
      }))
      expect(wrapper.vm.form).toMatchObject({ headline: '', content: '', thumbnail: '' })
      expect(readEditorRecovery(1, '/write')).toBeNull()
      expect(readEditorRecovery(2, '/write')).toBeNull()

      await wrapper.vm.publish()
      expect(m.articleApi.create).not.toHaveBeenCalled()
    } finally {
      storageWrite.mockRestore()
      wrapper.unmount()
    }
  })

  it('does not fill A article details into the editor after B becomes authoritative', async () => {
    routeState.params = { id: '22' }
    routeState.fullPath = '/edit/22'
    routeState.path = '/edit/22'
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', () => ({
      headline: 'Prior A recovery',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Prior A recovery body</p>'
    }))
    await saveEditorRecovery('owner-1', '/edit/22')
    unregister()

    let resolveDetails
    m.articleApi.getDetail.mockImplementationOnce(() => new Promise((resolve) => {
      resolveDetails = resolve
    }))
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(resolveDetails).toBeTypeOf('function')

    m.user.durableSession = {
      epoch: 'epoch-owner-2',
      token: 'owner-2-access',
      refreshToken: 'owner-2-refresh',
      user: { userid: 'owner-2' },
      generation: 1
    }
    resolveDetails({ data: {
      headline: 'A private headline', type: 102, content: 'A private body',
      thumbnail: '/a.png', credit: 5, drafted: 1
    } })
    await flushPromises()

    expect(wrapper.vm.form).toMatchObject({
      headline: '', content: '', thumbnail: '', credit: 0, drafted: 0
    })
    expect(readEditorRecovery('owner-1', '/edit/22')?.draft).toMatchObject({
      headline: 'Prior A recovery', content: '<p>Prior A recovery body</p>'
    })
    expect(readEditorRecovery('owner-2', '/edit/22')).toBeNull()
  })

  it('does not apply A thumbnail upload after B becomes authoritative', async () => {
    let resolveUpload
    m.uploadApi.uploadImage.mockImplementationOnce(() => new Promise((resolve) => {
      resolveUpload = resolve
    }))
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    const pending = wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })
    await vi.waitFor(() => expect(resolveUpload).toBeTypeOf('function'))

    m.user.durableSession = {
      epoch: 'epoch-owner-2',
      token: 'owner-2-access',
      refreshToken: 'owner-2-refresh',
      user: { userid: 'owner-2' },
      generation: 1
    }
    resolveUpload({ data: { url: '/a-private.png' } })
    await pending

    expect(wrapper.vm.form.thumbnail).toBe('')
    expect(m.msg.success).not.toHaveBeenCalledWith('上传成功')
    expect(readEditorRecovery('owner-2', '/write')).toBeNull()
  })

  it('saveArticle aborts on invalid form', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.publish()
    expect(m.articleApi.create).not.toHaveBeenCalled()
  })

  it('edit mode: loads article on mount and sets cascader path', async () => {
    routeState.params = { id: '22' }
    routeState.fullPath = '/edit/22'
    routeState.path = '/edit/22'
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(wrapper.vm.isEdit).toBe(true)
    expect(m.articleApi.getDetail).toHaveBeenCalledWith(
      '22',
      expect.objectContaining({ _sessionSnapshot: expect.any(Object) })
    )
    expect(wrapper.vm.form.headline).toBe('X')
    expect(wrapper.vm.form.typeArray).toEqual([1, 102])
  })

  it('edit mode: update navigates to returned article id', async () => {
    routeState.params = { id: '22' }
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Edited'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.articleApi.update).toHaveBeenCalledWith(
      '22',
      expect.any(Object),
      expect.objectContaining({ _sessionSnapshot: expect.any(Object) })
    )
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: 22 } })
  })

  it('edit mode: fetch failure shows error and routes Home', async () => {
    routeState.params = { id: '99' }
    m.articleApi.getDetail.mockRejectedValueOnce(new Error('404'))
    mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(m.msg.error).toHaveBeenCalledWith('文章不存在')
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('flushes UEditor and restores the latest snapshot for the same user and route', async () => {
    const seedProvider = () => ({
      headline: 'Recovered title',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Recovered body</p>',
      thumbnail: '/recovered.png',
      credit: 12,
      drafted: 1
    })
    const { registerEditorSnapshotProvider } = await import('@/utils/editorRecovery')
    const unregister = registerEditorSnapshotProvider('owner-1', seedProvider)
    await saveEditorRecovery('owner-1', '/write')
    unregister()

    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()

    expect(wrapper.vm.form).toMatchObject({
      headline: 'Recovered title',
      type: 102,
      typeArray: [1, 102],
      content: '<p>Recovered body</p>',
      thumbnail: '/recovered.png',
      credit: 12,
      drafted: 1
    })
    expect(readEditorRecovery('owner-1', '/write')).toBeNull()
    expect(m.msg.info).toHaveBeenCalledWith('已恢复上次未保存的编辑内容')

    wrapper.vm.form.content = 'unsaved content'
    await saveEditorRecovery('owner-1', '/write')
    expect(m.editorFlush).toHaveBeenCalledOnce()
    expect(readEditorRecovery('owner-1', '/write').draft.content).toBe('<p>flushed editor content</p>')
  })

  it('unregisters the editor snapshot provider after the component unmounts', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Unmounted editor content'

    wrapper.unmount()

    await expect(saveEditorRecovery('owner-1', '/write')).resolves.toBe(false)
    expect(readEditorRecovery('owner-1', '/write')).toBeNull()
  })

  it('uses the account id and route path fallbacks for editor recovery', async () => {
    m.user.user = { id: 'owner-2' }
    routeState.fullPath = ''
    routeState.path = '/edit/22'
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()

    await expect(saveEditorRecovery('owner-2', '/edit/22')).resolves.toBe(true)
    expect(readEditorRecovery('owner-2', '/edit/22').draft.content).toBe('<p>flushed editor content</p>')
    wrapper.unmount()

    m.user.user = { username: 'writer' }
    routeState.path = ''
    const fallbackWrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    await expect(saveEditorRecovery('writer', '/write')).resolves.toBe(true)
    fallbackWrapper.unmount()
  })

  it('does not replace the normal not-found flow for auth-expired edit requests', async () => {
    routeState.params = { id: '99' }
    routeState.fullPath = '/edit/99'
    routeState.path = '/edit/99'
    m.articleApi.getDetail.mockRejectedValueOnce(Object.assign(new Error('expired'), {
      response: { status: 401 }
    }))
    mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(m.msg.error).not.toHaveBeenCalledWith('文章不存在')
    expect(push).not.toHaveBeenCalledWith({ name: 'Home' })
  })
})
