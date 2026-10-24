import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installLocalStorage } from '@/test/harness'
import {
  clearEditorRecovery,
  readEditorRecovery,
  registerEditorSnapshotProvider,
  saveEditorRecovery,
  saveEditorRecoverySync
} from './editorRecovery'

installLocalStorage()

describe('editor recovery', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('flushes the active editor before saving a user-scoped snapshot', async () => {
    const flush = vi.fn()
    const unregister = registerEditorSnapshotProvider('user-1', () => {
      flush()
      return { headline: 'draft', content: '<p>latest</p>' }
    })

    await expect(saveEditorRecovery('user-1', '/write')).resolves.toBe(true)
    expect(flush).toHaveBeenCalledOnce()
    expect(readEditorRecovery('user-1', '/write')).toMatchObject({
      ownerId: 'user-1',
      path: '/write',
      draft: { headline: 'draft', content: '<p>latest</p>' }
    })
    expect(readEditorRecovery('user-2', '/write')).toBeNull()
    unregister()
  })

  it('writes a synchronous lifecycle snapshot for the active account', () => {
    const flush = vi.fn()
    const unregister = registerEditorSnapshotProvider('user-1', () => {
      flush()
      return { headline: 'latest before reload', content: '<p>flushed</p>' }
    })

    expect(saveEditorRecoverySync('user-1', '/edit/4')).toBe(true)
    expect(flush).toHaveBeenCalledOnce()
    expect(readEditorRecovery('user-1', '/edit/4')?.draft).toEqual({
      headline: 'latest before reload', content: '<p>flushed</p>'
    })
    expect(readEditorRecovery('user-2', '/edit/4')).toBeNull()
    unregister()
  })

  it('reports an asynchronous provider failure during synchronous page exit', async () => {
    const error = new Error('editor flush failed')
    const onPageExitError = vi.fn(() => { throw new Error('editor warning handler unavailable') })
    const unregister = registerEditorSnapshotProvider(
      'user-1',
      async () => { throw error },
      { path: '/edit/4', onPageExitError }
    )

    expect(() => window.dispatchEvent(new Event('pagehide'))).not.toThrow()
    await vi.waitFor(() => expect(onPageExitError).toHaveBeenCalledWith(error))

    unregister()
  })

  it('keeps an existing recovery when the synchronous provider has no draft', () => {
    const priorDraft = {
      headline: 'Saved before initialization',
      content: '<p>Previously saved</p>'
    }
    localStorage.setItem('woniunote:editor-recovery:user-1', JSON.stringify({
      ownerId: 'user-1', path: '/edit/4', savedAt: 1, draft: priorDraft
    }))
    const unregister = registerEditorSnapshotProvider('user-1', () => null, { path: '/edit/4' })

    window.dispatchEvent(new Event('pagehide'))

    expect(readEditorRecovery('user-1', '/edit/4')?.draft).toEqual(priorDraft)
    unregister()
  })

  it('does not persist a page-exit snapshot when no route was registered', () => {
    const priorDraft = { headline: 'Saved for a known route' }
    localStorage.setItem('woniunote:editor-recovery:user-1', JSON.stringify({
      ownerId: 'user-1', path: '/edit/4', savedAt: 1, draft: priorDraft
    }))
    const unregister = registerEditorSnapshotProvider(
      'user-1', () => ({ headline: 'ambiguous route draft' })
    )

    window.dispatchEvent(new Event('pagehide'))

    expect(readEditorRecovery('user-1', '/edit/4')?.draft).toEqual(priorDraft)
    unregister()
  })

  it('reports a resolved asynchronous provider as unsupported for page-exit saving', async () => {
    const onPageExitError = vi.fn()
    const unregister = registerEditorSnapshotProvider(
      'user-1',
      async () => ({ headline: 'too late for page exit' }),
      { path: '/edit/4', onPageExitError }
    )

    window.dispatchEvent(new Event('beforeunload'))

    await vi.waitFor(() => expect(onPageExitError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Editor recovery lifecycle provider must be synchronous' })
    ))
    expect(readEditorRecovery('user-1', '/edit/4')).toBeNull()
    unregister()
  })

  it('does not write a sync snapshot if its provider is replaced during the flush', () => {
    let unregisterReplacement
    const unregisterOriginal = registerEditorSnapshotProvider('user-1', () => {
      unregisterReplacement = registerEditorSnapshotProvider(
        'user-2', () => ({ headline: 'other account' })
      )
      return { headline: 'stale user-1 draft' }
    })

    expect(saveEditorRecoverySync('user-1', '/edit/4')).toBe(false)
    expect(readEditorRecovery('user-1', '/edit/4')).toBeNull()
    expect(readEditorRecovery('user-2', '/edit/4')).toBeNull()

    unregisterOriginal()
    unregisterReplacement()
  })

  it('reports a synchronous page-exit storage failure to the active editor', () => {
    const error = new Error('editor recovery quota exceeded')
    const onPageExitError = vi.fn()
    const unregister = registerEditorSnapshotProvider(
      'user-1',
      () => ({ headline: 'latest draft' }),
      { path: '/edit/4', onPageExitError }
    )
    const originalSetItem = localStorage.setItem.bind(localStorage)
    const storageWrite = vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
      if (String(key).startsWith('woniunote:editor-recovery:')) throw error
      return originalSetItem(key, value)
    })

    try {
      window.dispatchEvent(new Event('pagehide'))
      expect(onPageExitError).toHaveBeenCalledWith(error)
      expect(readEditorRecovery('user-1', '/edit/4')).toBeNull()
    } finally {
      storageWrite.mockRestore()
      unregister()
    }
  })

  it('saves on beforeunload and removes both lifecycle listeners on unregister', () => {
    const unregister = registerEditorSnapshotProvider(
      'user-1', () => ({ headline: 'latest before unload' }), { path: '/edit/4' }
    )
    const storageWrite = vi.spyOn(localStorage, 'setItem')

    window.dispatchEvent(new Event('beforeunload'))
    expect(readEditorRecovery('user-1', '/edit/4')?.draft.headline).toBe('latest before unload')
    const writesAfterBeforeUnload = storageWrite.mock.calls.length

    unregister()
    window.dispatchEvent(new Event('pagehide'))
    window.dispatchEvent(new Event('beforeunload'))

    expect(storageWrite).toHaveBeenCalledTimes(writesAfterBeforeUnload)
    storageWrite.mockRestore()
  })

  it('ignores invalid and mismatched synchronous lifecycle saves', () => {
    expect(saveEditorRecoverySync(null, '/edit/4')).toBe(false)
    expect(saveEditorRecoverySync('user-1', '/edit/4')).toBe(false)

    const unregister = registerEditorSnapshotProvider(
      'user-2', () => ({ headline: 'other account' })
    )
    expect(saveEditorRecoverySync('user-1', '/edit/4')).toBe(false)
    expect(readEditorRecovery('user-1', '/edit/4')).toBeNull()
    unregister()
  })

  it('does not restore a snapshot at a different route and can clear it after recovery', async () => {
    const unregister = registerEditorSnapshotProvider('user-1', () => ({ headline: 'draft' }))
    await saveEditorRecovery('user-1', '/write/4')

    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    expect(readEditorRecovery('user-1', '/write/4')).toMatchObject({ draft: { headline: 'draft' } })
    clearEditorRecovery('user-1')
    expect(readEditorRecovery('user-1', '/write/4')).toBeNull()
    unregister()
  })

  it('ignores invalid and superseded editor providers', async () => {
    expect(registerEditorSnapshotProvider(null, () => ({}))()).toBeUndefined()
    expect(registerEditorSnapshotProvider('user-1', null)()).toBeUndefined()
    await expect(saveEditorRecovery('user-1', '/write')).resolves.toBe(false)

    const oldProvider = registerEditorSnapshotProvider('user-1', () => ({ headline: 'old' }))
    const newProvider = registerEditorSnapshotProvider('user-2', () => ({ headline: 'new' }))
    oldProvider()
    await expect(saveEditorRecovery('user-1', '/write')).resolves.toBe(false)
    await expect(saveEditorRecovery('user-2', '')).resolves.toBe(false)
    newProvider()
    await expect(saveEditorRecovery('user-2', '/write')).resolves.toBe(false)
  })

  it('does not save an empty or replaced provider result', async () => {
    const emptyProvider = registerEditorSnapshotProvider('user-1', () => null)
    await expect(saveEditorRecovery('user-1', '/write')).resolves.toBe(false)
    emptyProvider()

    let resolveDraft
    const unregisterPending = registerEditorSnapshotProvider(
      'user-1',
      () => new Promise((resolve) => { resolveDraft = resolve })
    )
    const pendingSave = saveEditorRecovery('user-1', '/write')
    await vi.waitFor(() => expect(resolveDraft).toBeTypeOf('function'))
    const unregisterNew = registerEditorSnapshotProvider('user-2', () => ({ headline: 'other user' }))
    resolveDraft({ headline: 'stale user draft' })
    await expect(pendingSave).resolves.toBe(false)
    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    unregisterPending()
    unregisterNew()
  })

  it('rejects malformed, mismatched, and incomplete stored snapshots safely', () => {
    expect(readEditorRecovery(null, '/write')).toBeNull()
    expect(readEditorRecovery('user-1', '')).toBeNull()
    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    localStorage.setItem('woniunote:editor-recovery:user-1', '{bad json')
    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    localStorage.setItem('woniunote:editor-recovery:user-1', JSON.stringify({
      ownerId: 'user-2', path: '/write', draft: { headline: 'wrong owner' }
    }))
    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    localStorage.setItem('woniunote:editor-recovery:user-1', JSON.stringify({
      ownerId: 'user-1', path: '/write', draft: null
    }))
    expect(readEditorRecovery('user-1', '/write')).toBeNull()
    expect(clearEditorRecovery('')).toBeUndefined()
  })
})
