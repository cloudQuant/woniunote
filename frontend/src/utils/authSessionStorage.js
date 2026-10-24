const DATABASE_NAME = 'woniunote-auth-session'
const DATABASE_VERSION = 1
const OBJECT_STORE = 'sessions'
const CURRENT_SESSION_KEY = 'current'
const INITIALIZED_KEY = 'initialized'
const LEGACY_SESSION_KEY = 'woniunote:auth-session'

function makeMarker() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function parseLegacyUser(storage) {
  try {
    return JSON.parse(storage.getItem('user') || 'null')
  } catch {
    // A malformed legacy mirror is ignored only while seeding the new authority.
    return null
  }
}

function readLegacySession(storage) {
  if (!storage) return null

  const canonical = storage.getItem(LEGACY_SESSION_KEY)
  if (canonical) {
    try {
      const parsed = JSON.parse(canonical)
      if (parsed && typeof parsed === 'object' && typeof parsed.epoch === 'string' &&
          typeof parsed.version === 'string') {
        return parsed
      }
    } catch {
      // An invalid legacy canonical record falls back to the older key mirrors.
    }
  }

  return {
    epoch: storage.getItem('woniunote:auth-session-epoch') || makeMarker(),
    version: storage.getItem('woniunote:auth-session-version') || makeMarker(),
    token: storage.getItem('token') || '',
    refreshToken: storage.getItem('refreshToken') || '',
    user: parseLegacyUser(storage)
  }
}

function normalizeSession(session, { seed = false } = {}) {
  if (!session || typeof session !== 'object' || typeof session.epoch !== 'string' ||
      !session.epoch || typeof session.version !== 'string' || !session.version ||
      typeof session.token !== 'string' || typeof session.refreshToken !== 'string' ||
      (!seed && (!Number.isSafeInteger(session.revision) || session.revision < 0)) ||
      (session.user !== null && (typeof session.user !== 'object' || Array.isArray(session.user)))) {
    throw new Error('安全登录会话记录无效')
  }

  return {
    epoch: session.epoch,
    version: session.version,
    // Legacy revisions are deliberately reset to zero. A caller-controlled
    // mirror must never be able to move the authoritative order forward.
    revision: seed ? 0 : session.revision,
    token: session.token,
    refreshToken: session.refreshToken,
    user: session.user ? { ...session.user } : null
  }
}

function copySession(session) {
  return {
    epoch: session.epoch,
    version: session.version,
    revision: session.revision,
    token: session.token,
    refreshToken: session.refreshToken,
    user: session.user ? { ...session.user } : null
  }
}

/**
 * IndexedDB is the authoritative cross-tab session record. Every decision and
 * update runs in one readwrite transaction; callers publish results only after
 * that transaction completes.
 */
export function createAuthSessionStorage({
  indexedDBFactory = () => globalThis.indexedDB,
  localStorageProvider = () => globalThis.localStorage,
  databaseName = DATABASE_NAME
} = {}) {
  let databasePromise = null
  let initialized = false

  function openDatabase() {
    if (databasePromise) return databasePromise

    const factory = indexedDBFactory()
    if (!factory?.open) {
      return Promise.reject(new Error('当前浏览器不支持安全登录会话存储'))
    }

    databasePromise = new Promise((resolve, reject) => {
      const request = factory.open(databaseName, DATABASE_VERSION)
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(OBJECT_STORE)) {
          request.result.createObjectStore(OBJECT_STORE)
        }
      }
      request.onsuccess = () => {
        const database = request.result
        database.onversionchange = () => {
          database.close()
          databasePromise = null
        }
        resolve(database)
      }
      request.onerror = () => {
        databasePromise = null
        reject(request.error || new Error('无法打开安全登录会话存储'))
      }
      request.onblocked = () => {
        databasePromise = null
        reject(new Error('安全登录会话存储正在升级，请关闭其他页面后重试'))
      }
    })
    return databasePromise
  }

  async function transact(update) {
    const database = await openDatabase()

    return new Promise((resolve, reject) => {
      const transaction = database.transaction(OBJECT_STORE, 'readwrite')
      const store = transaction.objectStore(OBJECT_STORE)
      const markerRequest = store.get(INITIALIZED_KEY)
      let current = null
      let next = null
      let result
      let hasUpdate = false
      let failure = null

      const failTransaction = (error) => {
        failure = error
        transaction.abort()
      }

      markerRequest.onsuccess = () => {
        if (markerRequest.result !== undefined && markerRequest.result !== true) {
          failTransaction(new Error('安全登录会话初始化标记无效'))
          return
        }

        const request = store.get(CURRENT_SESSION_KEY)
        request.onsuccess = () => {
          try {
            if (request.result === undefined && markerRequest.result === true) {
              throw new Error('安全登录会话记录缺失，已阻止恢复旧登录状态')
            }
            if (request.result === undefined) {
              const legacy = readLegacySession(localStorageProvider()) || {
                epoch: makeMarker(), version: makeMarker(), token: '', refreshToken: '', user: null
              }
              current = normalizeSession({ ...legacy, user: legacy.user ?? null }, { seed: true })
              store.put(current, CURRENT_SESSION_KEY)
              store.put(true, INITIALIZED_KEY)
            } else {
              current = normalizeSession(request.result)
              if (markerRequest.result === undefined) store.put(true, INITIALIZED_KEY)
            }

            const decision = update(copySession(current))
            if (decision && Object.prototype.hasOwnProperty.call(decision, 'session')) {
              if (current.revision >= Number.MAX_SAFE_INTEGER) {
                throw new Error('安全登录会话版本已耗尽，请重新初始化会话存储')
              }
              // Revision is allocated only from the value read inside this
              // readwrite transaction; updater-supplied values are ignored.
              next = normalizeSession({
                ...decision.session,
                revision: current.revision + 1
              })
              hasUpdate = true
              store.put(next, CURRENT_SESSION_KEY)
            }
            result = decision?.result
          } catch (error) {
            failTransaction(error)
          }
        }
        request.onerror = () => {
          failTransaction(request.error || new Error('无法读取安全登录会话'))
        }
      }
      markerRequest.onerror = () => {
        failTransaction(markerRequest.error || new Error('无法读取安全登录会话状态'))
      }
      transaction.onerror = () => {
        if (!failure) failure = transaction.error || new Error('安全登录会话事务失败')
      }
      transaction.onabort = () => {
        reject(failure || transaction.error || new Error('安全登录会话事务已中止'))
      }
      transaction.oncomplete = () => {
        initialized = true
        resolve({
          session: copySession(next || current),
          result,
          committed: hasUpdate
        })
      }
    })
  }

  return {
    async readCurrent() {
      if (!initialized) await transact(() => null)
      const database = await openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = database.transaction(OBJECT_STORE, 'readonly')
        const store = transaction.objectStore(OBJECT_STORE)
        const markerRequest = store.get(INITIALIZED_KEY)
        let session = null
        let failure = null
        markerRequest.onsuccess = () => {
          if (markerRequest.result !== true) {
            failure = new Error('安全登录会话尚未初始化')
            transaction.abort()
            return
          }
          const sessionRequest = store.get(CURRENT_SESSION_KEY)
          sessionRequest.onsuccess = () => {
            try {
              if (sessionRequest.result === undefined) {
                throw new Error('安全登录会话记录缺失，已阻止恢复旧登录状态')
              }
              session = normalizeSession(sessionRequest.result)
            } catch (error) {
              failure = error
              transaction.abort()
            }
          }
          sessionRequest.onerror = () => {
            failure = sessionRequest.error || new Error('无法读取安全登录会话')
            transaction.abort()
          }
        }
        markerRequest.onerror = () => {
          failure = markerRequest.error || new Error('无法读取安全登录会话状态')
          transaction.abort()
        }
        transaction.onerror = () => {
          if (!failure) failure = transaction.error || new Error('安全登录会话读取失败')
        }
        transaction.onabort = () => {
          reject(failure || transaction.error || new Error('安全登录会话读取已中止'))
        }
        transaction.oncomplete = () => resolve(copySession(session))
      })
    },
    transact
  }
}

export const authSessionStorage = createAuthSessionStorage()
