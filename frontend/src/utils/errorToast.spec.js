import { describe, it, expect, vi, beforeEach } from 'vitest'

const elMessage = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: (...a) => elMessage(...a)
}))

import { notifyError } from './errorToast'

describe('notifyError', () => {
  beforeEach(() => vi.clearAllMocks())

  it('prefers the error message when present', () => {
    notifyError(new Error('服务器内部错误'), '获取列表失败')
    expect(elMessage).toHaveBeenCalledWith({
      message: '服务器内部错误',
      type: 'error',
      grouping: true
    })
  })

  it('falls back to the scenario message when error.message is empty', () => {
    notifyError(new Error(''), '获取列表失败')
    expect(elMessage).toHaveBeenCalledWith({
      message: '获取列表失败',
      type: 'error',
      grouping: true
    })
  })

  it('passes grouping: true to collapse concurrent toasts', () => {
    notifyError({ message: 'boom' }, '获取列表失败')
    expect(elMessage).toHaveBeenCalledWith(expect.objectContaining({ grouping: true }))
  })

  it('uses the default fallback for null/undefined errors', () => {
    notifyError(undefined)
    expect(elMessage).toHaveBeenCalledWith({
      message: '请求失败',
      type: 'error',
      grouping: true
    })
  })
})
