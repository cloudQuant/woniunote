import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { mountOptions } from '@/test/harness'
import EmptyState from '@/components/common/EmptyState.vue'

import ArticleComments from './ArticleComments.vue'

const TOP = {
  commentid: 1,
  nickname: '张三',
  avatar: '',
  content: '顶层评论',
  agreecount: 3,
  opposecount: 1,
  createtime: '2026-01-01T10:00:00Z',
  replies: [
    {
      commentid: 2,
      nickname: '李四',
      avatar: '',
      content: '楼中楼回复',
      agreecount: 1,
      opposecount: 0,
      createtime: '2026-01-01T11:00:00Z'
    }
  ]
}

// 无昵称、无头像、无时间的边界评论
const NO_REPLY = {
  commentid: 3,
  nickname: '',
  avatar: '',
  content: '没有回复的评论',
  agreecount: 0,
  opposecount: 0,
  createtime: ''
}

function mountComments(props = {}) {
  return mount(
    ArticleComments,
    mountOptions({
      props: {
        comments: [TOP, NO_REPLY],
        totalComments: 4,
        isLoggedIn: true,
        newComment: '',
        submittingComment: false,
        replyingTo: null,
        replyContent: '',
        submittingReply: false,
        ...props
      }
    })
  )
}

describe('ArticleComments.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染标题、评论列表与楼中楼回复', () => {
    const wrapper = mountComments()
    expect(wrapper.get('.section-title').text()).toBe('评论 (4)')
    const items = wrapper.findAll('.comment-item')
    expect(items).toHaveLength(2)

    const first = items[0]
    expect(first.find('.comment-author').text()).toBe('张三')
    expect(first.find('.comment-content').text()).toBe('顶层评论')
    // 只取顶层评论自己的操作入口（.reply-item 内还有一组）
    expect(first.findAll('.comment-body > .comment-actions > span').map((s) => s.text())).toEqual([
      '3',
      '1',
      '回复'
    ])
    expect(first.find('.reply-list').exists()).toBe(true)
    expect(first.find('.reply-item .comment-author').text()).toBe('李四')
    expect(first.find('.reply-item .comment-content').text()).toBe('楼中楼回复')
  })

  it('昵称为空时回退为匿名，头像回退为首字母', () => {
    const wrapper = mountComments()
    const second = wrapper.findAll('.comment-item')[1]
    expect(second.find('.comment-author').text()).toBe('匿名')
    // el-avatar 桩渲染默认插槽 → 昵称首字母 / 'U'
    expect(second.find('.comment-avatar').text()).toBe('U')
    expect(wrapper.findAll('.comment-item')[0].find('.comment-avatar').text()).toBe('张')
  })

  it('无评论时展示空态', () => {
    const wrapper = mountComments({ comments: [], totalComments: 0 })
    expect(wrapper.find('.comment-item').exists()).toBe(false)
    const empty = wrapper.findComponent(EmptyState)
    expect(empty.exists()).toBe(true)
    expect(empty.props('description')).toBe('暂无评论')
    expect(empty.props('compact')).toBe(true)
  })

  it('未登录时展示登录提示、隐藏表单与回复入口', () => {
    const wrapper = mountComments({ isLoggedIn: false })
    expect(wrapper.find('.comment-form').exists()).toBe(false)
    expect(wrapper.get('.login-prompt').text()).toContain('登录')
    expect(wrapper.get('.login-prompt').find('a.router-link').exists()).toBe(true)
    // 每条评论只剩点赞/反对两个入口
    wrapper.findAll('.comment-item').forEach((item) => {
      expect(item.findAll('.comment-body > .comment-actions > span')).toHaveLength(2)
    })
  })

  it('发表评论输入变化时抛出 update:newComment', async () => {
    const wrapper = mountComments()
    const textarea = wrapper.findAllComponents({ name: 'el-input' })[0]
    await textarea.vm.$emit('update:modelValue', '你好')
    expect(wrapper.emitted('update:newComment')).toEqual([['你好']])
  })

  it('发表评论按钮抛出 submit-comment，空内容时禁用', async () => {
    const wrapper = mountComments({ newComment: '' })
    const submitBtn = wrapper.findAllComponents({ name: 'el-button' })[0]
    expect(submitBtn.props('disabled')).toBe(true)

    await wrapper.setProps({ newComment: '写点什么' })
    expect(submitBtn.props('disabled')).toBe(false)
    await submitBtn.vm.$emit('click')
    expect(wrapper.emitted('submit-comment')).toHaveLength(1)
  })

  it('提交中时按钮处于 loading 状态', () => {
    const wrapper = mountComments({ newComment: 'x', submittingComment: true })
    expect(wrapper.findAllComponents({ name: 'el-button' })[0].props('loading')).toBe(true)
  })

  it('顶层评论的点赞、反对、回复入口抛出对应事件', async () => {
    const wrapper = mountComments()
    const spans = wrapper
      .findAll('.comment-item')[0]
      .findAll('.comment-body > .comment-actions > span')

    await spans[0].trigger('click')
    expect(wrapper.emitted('agree')[0][0].commentid).toBe(1)
    await spans[1].trigger('click')
    expect(wrapper.emitted('oppose')[0][0].commentid).toBe(1)
    await spans[2].trigger('click')
    expect(wrapper.emitted('start-reply')[0][0].commentid).toBe(1)
  })

  it('楼中楼回复的点赞与反对抛出对应事件', async () => {
    const wrapper = mountComments()
    const spans = wrapper.findAll('.reply-item')[0].findAll('.comment-actions span')
    expect(spans).toHaveLength(2)

    await spans[0].trigger('click')
    expect(wrapper.emitted('agree')[0][0].commentid).toBe(2)
    await spans[1].trigger('click')
    expect(wrapper.emitted('oppose')[0][0].commentid).toBe(2)
  })

  it('replyingTo 命中时展开回复表单并转发输入与按钮事件', async () => {
    const wrapper = mountComments({ replyingTo: 1, replyContent: '收到' })
    const first = wrapper.findAll('.comment-item')[0]
    const second = wrapper.findAll('.comment-item')[1]
    expect(first.find('.reply-form').exists()).toBe(true)
    expect(second.find('.reply-form').exists()).toBe(false)

    const replyInput = wrapper.findAllComponents({ name: 'el-input' })[1]
    await replyInput.vm.$emit('update:modelValue', '收到啦')
    expect(wrapper.emitted('update:replyContent')).toEqual([['收到啦']])

    const [cancelBtn, replyBtn] = first.findAllComponents({ name: 'el-button' })
    await cancelBtn.vm.$emit('click')
    expect(wrapper.emitted('cancel-reply')).toHaveLength(1)

    await replyBtn.vm.$emit('click')
    expect(wrapper.emitted('submit-reply')[0][0].commentid).toBe(1)
  })

  it('回复内容为空时回复按钮禁用，提交中时 loading', () => {
    const wrapper = mountComments({ replyingTo: 1, replyContent: '   ' })
    const replyBtn = wrapper.findAll('.comment-item')[0].findAllComponents({ name: 'el-button' })[1]
    expect(replyBtn.props('disabled')).toBe(true)
    expect(replyBtn.props('loading')).toBe(false)

    const submitting = mountComments({
      replyingTo: 1,
      replyContent: 'hi',
      submittingReply: true
    })
    const loadingBtn = submitting
      .findAll('.comment-item')[0]
      .findAllComponents({ name: 'el-button' })[1]
    expect(loadingBtn.props('loading')).toBe(true)
    expect(loadingBtn.props('disabled')).toBe(false)
  })

  it('formatDate 空值返回空串，合法日期返回本地化文本', () => {
    const wrapper = mountComments()
    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate(null)).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01T10:00:00Z')).toContain('2026')
  })
})
