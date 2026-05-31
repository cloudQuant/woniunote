import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { startLoading, stopLoading, resetLoading } from './loading'

const BAR_ID = 'global-loading-bar'

describe('utils/loading', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    resetLoading()
    document.body.innerHTML = ''
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('creates a progress bar on first request', () => {
    startLoading()
    const bar = document.getElementById(BAR_ID)
    expect(bar).not.toBeNull()
    expect(bar.style.width).toBe('30%')
  })

  it('advances width with concurrent requests (capped at 80%)', () => {
    for (let i = 0; i < 10; i++) startLoading()
    const bar = document.getElementById(BAR_ID)
    expect(parseInt(bar.style.width, 10)).toBeLessThanOrEqual(80)
    expect(parseInt(bar.style.width, 10)).toBeGreaterThan(30)
  })

  it('removes the bar after the count returns to zero', () => {
    startLoading()
    stopLoading()
    // finish() sets width 100% then schedules fade + removal.
    const bar = document.getElementById(BAR_ID)
    expect(bar.style.width).toBe('100%')
    vi.advanceTimersByTime(600)
    expect(document.getElementById(BAR_ID)).toBeNull()
  })

  it('only finishes when all concurrent requests complete', () => {
    startLoading()
    startLoading()
    stopLoading()
    // Still one pending → bar remains.
    expect(document.getElementById(BAR_ID)).not.toBeNull()
    stopLoading()
    vi.advanceTimersByTime(600)
    expect(document.getElementById(BAR_ID)).toBeNull()
  })

  it('stopLoading is a no-op when nothing is pending', () => {
    expect(() => stopLoading()).not.toThrow()
  })

  it('resetLoading clears pending state and removes the bar', () => {
    startLoading()
    startLoading()
    resetLoading()
    vi.advanceTimersByTime(600)
    expect(document.getElementById(BAR_ID)).toBeNull()
    // After reset a single stop should not throw or resurrect the bar.
    stopLoading()
    expect(document.getElementById(BAR_ID)).toBeNull()
  })
})
