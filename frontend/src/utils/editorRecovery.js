import { logWarning } from '@/utils/logger'

const STORAGE_PREFIX = 'woniunote:editor-recovery:'

let activeProvider = null
let pageExitListenersInstalled = false

function storageKey(ownerId) {
  return `${STORAGE_PREFIX}${encodeURIComponent(String(ownerId))}`
}

function reportPageExitError(registration, error) {
  try {
    registration.onPageExitError?.(error)
  } catch (handlerError) {
    logWarning('无法报告页面离开时的编辑恢复失败', {
      message: handlerError?.message || '未知错误'
    })
  }
}

function handlePageExit() {
  const registration = activeProvider
  if (!registration?.path) return
  try {
    if (registration.shouldPersistOnExit && !registration.shouldPersistOnExit()) return
    saveEditorRecoverySync(registration.ownerId, registration.path)
  } catch (error) {
    reportPageExitError(registration, error)
  }
}

function installPageExitListeners() {
  if (pageExitListenersInstalled || typeof window === 'undefined') return
  window.addEventListener('pagehide', handlePageExit)
  window.addEventListener('beforeunload', handlePageExit)
  pageExitListenersInstalled = true
}

function removePageExitListeners() {
  if (!pageExitListenersInstalled || typeof window === 'undefined') return
  window.removeEventListener('pagehide', handlePageExit)
  window.removeEventListener('beforeunload', handlePageExit)
  pageExitListenersInstalled = false
}

/** Register the active editor's flush-and-snapshot callback. */
export function registerEditorSnapshotProvider(ownerId, provider, lifecycle = {}) {
  if (ownerId === null || ownerId === undefined || ownerId === '' || typeof provider !== 'function') {
    return () => {}
  }

  const registration = {
    ownerId: String(ownerId),
    provider,
    path: lifecycle.path,
    shouldPersistOnExit: lifecycle.shouldPersistOnExit,
    onPageExitError: lifecycle.onPageExitError
  }
  activeProvider = registration
  installPageExitListeners()
  return () => {
    if (activeProvider === registration) {
      activeProvider = null
      removePageExitListeners()
    }
  }
}

/** Flush and save the active editor under its owner, never under a later user. */
export async function saveEditorRecovery(ownerId, path) {
  if (ownerId === null || ownerId === undefined || !path || !activeProvider) return false
  const expectedOwner = String(ownerId)
  if (activeProvider.ownerId !== expectedOwner) return false

  const draft = await activeProvider.provider()
  if (!draft || activeProvider?.ownerId !== expectedOwner) return false

  localStorage.setItem(storageKey(expectedOwner), JSON.stringify({
    ownerId: expectedOwner,
    path: String(path),
    savedAt: Date.now(),
    draft
  }))
  return true
}

/** Save the active editor synchronously for browser page lifecycle events. */
export function saveEditorRecoverySync(ownerId, path) {
  if (ownerId === null || ownerId === undefined || !path || !activeProvider) return false
  const expectedOwner = String(ownerId)
  const registration = activeProvider
  if (registration.ownerId !== expectedOwner) return false

  const draft = registration.provider()
  if (draft && typeof draft.then === 'function') {
    // Lifecycle writes cannot wait for asynchronous providers, but attach both
    // Promise outcomes so a rejected flush is reported instead of unhandled.
    void Promise.resolve(draft).then(
      () => reportPageExitError(registration,
        new TypeError('Editor recovery lifecycle provider must be synchronous')
      ),
      error => reportPageExitError(registration, error)
    )
    return false
  }
  if (!draft || activeProvider !== registration) return false

  localStorage.setItem(storageKey(expectedOwner), JSON.stringify({
    ownerId: expectedOwner,
    path: String(path),
    savedAt: Date.now(),
    draft
  }))
  return true
}

/** Read only the snapshot for this account and exact route. */
export function readEditorRecovery(ownerId, path) {
  if (ownerId === null || ownerId === undefined || !path) return null
  const raw = localStorage.getItem(storageKey(ownerId))
  if (!raw) return null

  try {
    const snapshot = JSON.parse(raw)
    if (snapshot?.ownerId !== String(ownerId) || snapshot.path !== String(path) || !snapshot.draft) {
      return null
    }
    return snapshot
  } catch {
    return null
  }
}

export function clearEditorRecovery(ownerId) {
  if (ownerId === null || ownerId === undefined || ownerId === '') return
  localStorage.removeItem(storageKey(ownerId))
}
