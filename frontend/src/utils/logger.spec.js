import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

// Deterministic localStorage stub.
const memoryStore = (() => {
  let data = {}
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v) },
    removeItem: (k) => { delete data[k] },
    clear: () => { data = {} }
  }
})()
vi.stubGlobal('localStorage', memoryStore)

import {
  logInfo,
  logWarning,
  logError,
  logRequest,
  getLogs,
  getStoredLogs,
  clearLogs,
  exportLogs
} from './logger'
import loggerDefault from './logger'

describe('utils/logger', () => {
  beforeEach(() => {
    localStorage.clear()
    clearLogs()
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('logInfo records an INFO entry (with and without data)', () => {
    logInfo('hello')
    logInfo('with data', { a: 1 })
    const logs = getLogs()
    expect(logs.length).toBe(2)
    expect(logs[0].level).toBe('INFO')
    expect(logs[0].message).toBe('hello')
    expect(logs[1].data).toEqual({ a: 1 })
  })

  it('logWarning records a WARNING entry', () => {
    logWarning('careful')
    logWarning('with data', { b: 2 })
    const logs = getLogs()
    expect(logs.map((l) => l.level)).toEqual(['WARNING', 'WARNING'])
  })

  it('logError captures error name/message/stack', () => {
    const err = new Error('boom')
    logError('failed', err, { ctx: 'x' })
    logError('no error object')
    const logs = getLogs()
    expect(logs[0].level).toBe('ERROR')
    expect(logs[0].data.error.message).toBe('boom')
    expect(logs[1].data.error).toBe(null)
  })

  it('logRequest picks level by status code', () => {
    logRequest('GET', '/a', 200, 10)
    logRequest('GET', '/b', 404, 10)
    logRequest('GET', '/c', 500, 10)
    const levels = getLogs().map((l) => l.level)
    expect(levels).toEqual(['INFO', 'WARNING', 'ERROR'])
  })

  it('persists last logs to localStorage and reads them back', () => {
    logInfo('persist me')
    const stored = getStoredLogs()
    expect(stored.length).toBeGreaterThan(0)
    expect(stored[stored.length - 1].message).toBe('persist me')
  })

  it('getStoredLogs returns [] when storage empty or invalid', () => {
    expect(getStoredLogs()).toEqual([])
    localStorage.setItem('woniunote_logs', '{not json')
    expect(getStoredLogs()).toEqual([])
  })

  it('caps in-memory logs at the maximum (100)', () => {
    for (let i = 0; i < 150; i++) logInfo(`m${i}`)
    const logs = getLogs()
    expect(logs.length).toBe(100)
    // Oldest entries were dropped.
    expect(logs[0].message).toBe('m50')
  })

  it('clearLogs empties memory and storage', () => {
    logInfo('x')
    clearLogs()
    expect(getLogs()).toEqual([])
    expect(localStorage.getItem('woniunote_logs')).toBe(null)
  })

  it('exportLogs renders a readable text format', () => {
    logInfo('plain')
    logInfo('rich', { k: 'v' })
    const text = exportLogs()
    expect(text).toContain('[INFO] plain')
    expect(text).toContain('[INFO] rich | {"k":"v"}')
  })

  it('default export proxies the named functions', () => {
    loggerDefault.info('via default')
    expect(getLogs()[0].message).toBe('via default')
    expect(typeof loggerDefault.exportLogs).toBe('function')
  })
})
