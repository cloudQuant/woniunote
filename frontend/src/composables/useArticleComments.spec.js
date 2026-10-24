import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const m = vi.hoisted(() => ({
  msg: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
  push: vi.fn(),
  user: { isLoggedIn: false },
  route: { params: { id: '7' } },
  commentApi: {
    getByArticle: vi.fn(() => Promise.resolve({ data: [] })),
    create: vi.fn(() => Promise.resolve({})),
    agree: vi.fn(() => Promise.resolve({})),
    oppose: vi.fn(() => Promise.resolve({}))
  }
}))

vi.mock('vue-router', () => ({
  useRoute: () => m.route,
  useRouter: () => ({ push: m.push })
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/stores/user', () => ({ useUserStore: () => m.user }))
vi.mock('@/api', () => ({ commentApi: m.commentApi }))

import { useArticleComments } from './useArticleComments'

/** 在组件上下文中调用 composable，返回其全部状态与方法。 */
function setup(article = { articleid: 99 }) {
  const articleRef = ref(article)
  let api
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useArticleComments({ article: articleRef })
        return () => h('div')
      }
    }),
    mountOptions()
  )
  return { api, articleRef, wrapper }
}

describe('useArticleComments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.user.isLoggedIn = false
    m.commentApi.getByArticle.mockResolvedValue({ data: [] })
    m.commentApi.create.mockResolvedValue({})
    m.commentApi.agree.mockResolvedValue({})
    m.commentApi.oppose.mockResolvedValue({})
  })

  it('fetchComments 按路由 id 拉取评论并写入列表', async () => {
    m.commentApi.getByArticle.mockResolvedValueOnce({
      data: [{ commentid: 1, replies: [{ commentid: 2 }] }]
    })
    const { api } = setup()

    await api.fetchComments()

    expect(m.commentApi.getByArticle).toHaveBeenCalledWith('7', { page: 1, page_size: 50 })
    expect(api.comments.value).toHaveLength(1)
  })

  it('totalComments 统计顶层评论与其回复', async () => {
    m.commentApi.getByArticle.mockResolvedValueOnce({
      data: [
        { commentid: 1, replies: [{ commentid: 11 }, { commentid: 12 }] },
        { commentid: 2 }, // 无 replies 字段
        { commentid: 3, replies: [] }
      ]
    })
    const { api } = setup()

    await api.fetchComments()

    expect(api.totalComments.value).toBe(5) // 3 条顶层 + 2 条回复
  })

  it('fetchComments 失败时保留空列表并打印错误', async () => {
    m.commentApi.getByArticle.mockRejectedValueOnce(new Error('network'))
    const { api } = setup()

    await api.fetchComments()

    expect(api.comments.value).toEqual([])
    expect(console.error).toHaveBeenCalledWith('获取评论失败:', expect.any(Error))
  })

  it('submitComment 忽略空白内容', async () => {
    const { api } = setup()
    api.newComment.value = '   '

    await api.submitComment()

    expect(m.commentApi.create).not.toHaveBeenCalled()
    expect(api.submittingComment.value).toBe(false)
  })

  it('submitComment 成功后清空输入、刷新列表并提示', async () => {
    const { api } = setup()
    api.newComment.value = ' 你好 '

    await api.submitComment()

    expect(m.commentApi.create).toHaveBeenCalledWith({ articleid: 99, content: '你好' })
    expect(api.newComment.value).toBe('')
    expect(m.commentApi.getByArticle).toHaveBeenCalled()
    expect(m.msg.success).toHaveBeenCalledWith('评论发表成功')
    expect(api.submittingComment.value).toBe(false)
  })

  it('submitComment 失败时复位提交状态并打印错误', async () => {
    m.commentApi.create.mockRejectedValueOnce(new Error('boom'))
    const { api } = setup()
    api.newComment.value = 'hi'

    await api.submitComment()

    expect(api.submittingComment.value).toBe(false)
    expect(m.msg.success).not.toHaveBeenCalled()
    expect(console.error).toHaveBeenCalledWith('发表评论失败:', expect.any(Error))
  })

  it('startReply 未登录时跳转登录页', () => {
    const { api } = setup()
    m.user.isLoggedIn = false

    api.startReply({ commentid: 5 })

    expect(m.push).toHaveBeenCalledWith({ name: 'Login' })
    expect(api.replyingTo.value).toBe(null)
  })

  it('startReply 已登录时展开回复框并清空草稿', () => {
    m.user.isLoggedIn = true
    const { api } = setup()
    api.replyContent.value = '旧草稿'

    api.startReply({ commentid: 5 })

    expect(api.replyingTo.value).toBe(5)
    expect(api.replyContent.value).toBe('')
  })

  it('cancelReply 收起回复框并清空草稿', () => {
    const { api } = setup()
    api.replyingTo.value = 5
    api.replyContent.value = '草稿'

    api.cancelReply()

    expect(api.replyingTo.value).toBe(null)
    expect(api.replyContent.value).toBe('')
  })

  it('submitReply 忽略空白内容', async () => {
    const { api } = setup()
    api.replyContent.value = '  '

    await api.submitReply({ commentid: 5 })

    expect(m.commentApi.create).not.toHaveBeenCalled()
    expect(api.submittingReply.value).toBe(false)
  })

  it('submitReply 成功后带上 replyid、收起回复框并刷新列表', async () => {
    const { api } = setup()
    api.replyingTo.value = 5
    api.replyContent.value = ' 回复内容 '

    await api.submitReply({ commentid: 5 })

    expect(m.commentApi.create).toHaveBeenCalledWith({
      articleid: 99,
      content: '回复内容',
      replyid: 5
    })
    expect(api.replyingTo.value).toBe(null)
    expect(api.replyContent.value).toBe('')
    expect(m.commentApi.getByArticle).toHaveBeenCalled()
    expect(m.msg.success).toHaveBeenCalledWith('回复成功')
    expect(api.submittingReply.value).toBe(false)
  })

  it('submitReply 失败时复位状态并打印错误', async () => {
    m.commentApi.create.mockRejectedValueOnce(new Error('boom'))
    const { api } = setup()
    api.replyingTo.value = 5
    api.replyContent.value = 'hi'

    await api.submitReply({ commentid: 5 })

    expect(api.submittingReply.value).toBe(false)
    expect(console.error).toHaveBeenCalledWith('回复失败:', expect.any(Error))
  })

  it('agreeComment 未登录时跳转登录页且不调用接口', async () => {
    const { api } = setup()
    const comment = { commentid: 1, agreecount: 2 }
    m.user.isLoggedIn = false

    await api.agreeComment(comment)

    expect(m.push).toHaveBeenCalledWith({ name: 'Login' })
    expect(m.commentApi.agree).not.toHaveBeenCalled()
    expect(comment.agreecount).toBe(2)
  })

  it('agreeComment 成功后从服务端重读计数，不乐观自增', async () => {
    m.user.isLoggedIn = true
    const { api } = setup()
    const comment = { commentid: 1, agreecount: 2 }
    m.commentApi.getByArticle.mockResolvedValueOnce({
      data: [{ commentid: 1, agreecount: 3, opposecount: 0, replies: [] }]
    })

    await api.agreeComment(comment)

    expect(m.commentApi.agree).toHaveBeenCalledWith(1)
    expect(m.commentApi.getByArticle).toHaveBeenCalledTimes(1)
    expect(comment.agreecount).toBe(2)
    expect(api.comments.value[0].agreecount).toBe(3)
  })

  it('agreeComment 失败时计数不变并打印错误', async () => {
    m.user.isLoggedIn = true
    m.commentApi.agree.mockRejectedValueOnce(new Error('boom'))
    const { api } = setup()
    const comment = { commentid: 1, agreecount: 0 }

    await api.agreeComment(comment)

    expect(comment.agreecount).toBe(0)
    expect(console.error).toHaveBeenCalledWith('点赞失败:', expect.any(Error))
  })

  it('agreeComment 结果未知时不重发、不自增，刷新计数并保留待核实状态', async () => {
    m.user.isLoggedIn = true
    const error = Object.assign(new Error('unknown'), {
      response: { data: { error_code: 'WRITE_OUTCOME_UNKNOWN' } }
    })
    m.commentApi.agree.mockRejectedValueOnce(error)
    m.commentApi.getByArticle.mockResolvedValueOnce({
      data: [{ commentid: 1, agreecount: 3, opposecount: 0, replies: [] }]
    })
    const { api } = setup()
    const comment = { commentid: 1, agreecount: 2 }

    await api.agreeComment(comment)

    expect(m.commentApi.agree).toHaveBeenCalledTimes(1)
    expect(m.commentApi.getByArticle).toHaveBeenCalledTimes(1)
    expect(comment.agreecount).toBe(2)
    expect(api.comments.value[0].agreecount).toBe(3)
    expect(api.pendingVoteVerifications.value['1']).toEqual({
      voteType: 'agree',
      countRefreshState: 'refreshed'
    })
  })

  it('识别响应 data.data 中的未知写入错误码并只刷新、不重发', async () => {
    m.user.isLoggedIn = true
    m.commentApi.agree.mockRejectedValueOnce({
      response: { data: { data: { error_code: 'WRITE_OUTCOME_UNKNOWN' } } }
    })
    const { api } = setup()

    await api.agreeComment({ commentid: 15, agreecount: 2 })

    expect(m.commentApi.agree).toHaveBeenCalledTimes(1)
    expect(m.commentApi.getByArticle).toHaveBeenCalledTimes(1)
    expect(api.pendingVoteVerifications.value['15']).toEqual({
      voteType: 'agree',
      countRefreshState: 'refreshed'
    })
    expect(m.msg.warning).toHaveBeenCalledWith(expect.stringContaining('暂未确认'))
  })

  it('明确的点赞与反对 4xx 失败显示错误提示而不进入待核实', async () => {
    m.user.isLoggedIn = true
    const rejectedResponse = () => ({
      response: { status: 400, data: { error_code: 'INVALID_REQUEST', message: '请求无效' } }
    })
    m.commentApi.agree.mockRejectedValueOnce(rejectedResponse())
    m.commentApi.oppose.mockRejectedValueOnce(rejectedResponse())
    const { api } = setup()

    await api.agreeComment({ commentid: 16, agreecount: 0 })
    await api.opposeComment({ commentid: 17, opposecount: 0 })

    expect(m.msg).toHaveBeenNthCalledWith(1, {
      message: '点赞失败',
      type: 'error',
      grouping: true
    })
    expect(m.msg).toHaveBeenNthCalledWith(2, {
      message: '踩失败',
      type: 'error',
      grouping: true
    })
    expect(m.msg).toHaveBeenCalledTimes(2)
    expect(api.pendingVoteVerifications.value).toEqual({})
    expect(m.commentApi.agree).toHaveBeenCalledTimes(1)
    expect(m.commentApi.oppose).toHaveBeenCalledTimes(1)
  })

  it('投票响应丢失且计数刷新失败时保持待核实状态', async () => {
    m.user.isLoggedIn = true
    m.commentApi.agree.mockRejectedValueOnce(new Error('network'))
    m.commentApi.getByArticle.mockRejectedValueOnce(new Error('refresh network'))
    const { api } = setup()
    const comment = { commentid: 1, agreecount: 2 }

    await api.agreeComment(comment)

    expect(m.commentApi.agree).toHaveBeenCalledTimes(1)
    expect(m.commentApi.getByArticle).toHaveBeenCalledTimes(1)
    expect(comment.agreecount).toBe(2)
    expect(api.pendingVoteVerifications.value['1']).toEqual({
      voteType: 'agree',
      countRefreshState: 'failed'
    })
  })

  it('opposeComment 未登录时跳转登录页且不调用接口', async () => {
    const { api } = setup()
    const comment = { commentid: 1, opposecount: 0 }
    m.user.isLoggedIn = false

    await api.opposeComment(comment)

    expect(m.push).toHaveBeenCalledWith({ name: 'Login' })
    expect(m.commentApi.oppose).not.toHaveBeenCalled()
    expect(comment.opposecount).toBe(0)
  })

  it('opposeComment 成功后只使用服务端返回的新计数', async () => {
    m.user.isLoggedIn = true
    const { api } = setup()
    const comment = { commentid: 1, opposecount: 4 }
    m.commentApi.getByArticle.mockResolvedValueOnce({
      data: [{ commentid: 1, agreecount: 0, opposecount: 5, replies: [] }]
    })

    await api.opposeComment(comment)

    expect(m.commentApi.oppose).toHaveBeenCalledWith(1)
    expect(m.commentApi.getByArticle).toHaveBeenCalledTimes(1)
    expect(comment.opposecount).toBe(4)
    expect(api.comments.value[0].opposecount).toBe(5)
  })

  it('opposeComment 失败时计数不变并打印错误', async () => {
    m.user.isLoggedIn = true
    m.commentApi.oppose.mockRejectedValueOnce(new Error('boom'))
    const { api } = setup()
    const comment = { commentid: 1, opposecount: 0 }

    await api.opposeComment(comment)

    expect(comment.opposecount).toBe(0)
    expect(console.error).toHaveBeenCalledWith('踩失败:', expect.any(Error))
  })
})
