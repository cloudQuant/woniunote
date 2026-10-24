import { describe, expect, it } from 'vitest'
import { createAuthSessionStorage } from './authSessionStorage'

function copy(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value))
}

function createFakeIndexedDB({ failOpen = false, blocked = false } = {}) {
  const records = new Map()
  const controls = { readFailure: null, writeFailure: null }
  let openCount = 0
  let transactionQueue = Promise.resolve()
  const database = {
    objectStoreNames: { contains: (name) => name === 'sessions' },
    createObjectStore() {},
    transaction() {
      const previous = transactionQueue
      let releaseQueue
      transactionQueue = new Promise((resolve) => { releaseQueue = resolve })
      let started = false
      let finished = false
      let aborted = false
      let pendingRequestsCount = 0
      const pendingRequests = []
      const writes = new Map()
      const transaction = {
        error: null,
        objectStore() {
          return {
            get(key) {
              const request = { result: undefined, error: null }
              const run = () => queueMicrotask(() => {
                if (aborted) return
                if (controls.readFailure === key || controls.readFailure === '*') {
                  request.error = new Error(`read failed: ${key}`)
                  controls.readFailure = null
                  request.onerror?.({ target: request })
                  pendingRequestsCount -= 1
                  if (pendingRequestsCount === 0) queueMicrotask(complete)
                  return
                }
                request.result = copy(writes.has(key) ? writes.get(key) : records.get(key))
                request.onsuccess?.({ target: request })
                pendingRequestsCount -= 1
                if (pendingRequestsCount === 0) queueMicrotask(complete)
              })
              pendingRequestsCount += 1
              if (started) run()
              else pendingRequests.push(run)
              return request
            },
            put(value, key) {
              if (controls.writeFailure === key || controls.writeFailure === '*') {
                const error = new Error(`write failed: ${key}`)
                controls.writeFailure = null
                queueMicrotask(() => {
                  if (finished) return
                  aborted = true
                  transaction.error = error
                  transaction.onerror?.({ target: transaction })
                  if (finished) return
                  finished = true
                  transaction.onabort?.({ target: transaction })
                  releaseQueue()
                })
                return { result: key, error }
              }
              writes.set(key, copy(value))
              return { result: key, error: null }
            }
          }
        },
        abort() {
          aborted = true
          queueMicrotask(() => {
            if (finished) return
            finished = true
            transaction.onabort?.({ target: transaction })
            releaseQueue()
          })
        }
      }
      const complete = () => {
        if (finished || aborted) return
        finished = true
        for (const [key, value] of writes) records.set(key, copy(value))
        transaction.oncomplete?.({ target: transaction })
        releaseQueue()
      }
      previous.then(() => {
        started = true
        pendingRequests.splice(0).forEach((run) => run())
      })
      return transaction
    },
    close() {}
  }

  return {
    indexedDB: {
      open() {
        openCount += 1
        const request = { result: null, error: null }
        queueMicrotask(() => {
          if (failOpen) {
            request.error = new Error('open failed')
            request.onerror?.({ target: request })
            return
          }
          if (blocked) {
            request.onblocked?.({ target: request })
            return
          }
          request.result = database
          request.onupgradeneeded?.({ target: request })
          request.onsuccess?.({ target: request })
        })
        return request
      }
    },
    records,
    failNextRead(key = '*') { controls.readFailure = key },
    failNextWrite(key = '*') { controls.writeFailure = key },
    getOpenCount() { return openCount },
    triggerVersionChange() { database.onversionchange?.({ target: database }) }
  }
}

function createMemoryStorage(values = {}) {
  const data = new Map(Object.entries(values))
  return {
    getItem(key) { return data.has(key) ? data.get(key) : null },
    setItem(key, value) { data.set(key, String(value)) },
    removeItem(key) { data.delete(key) }
  }
}

describe('auth session IndexedDB adapter', () => {
  it('seeds the authoritative record from legacy state only on first initialization', async () => {
    const fake = createFakeIndexedDB()
    const legacy = createMemoryStorage({
      'woniunote:auth-session': JSON.stringify({
        epoch: 'legacy-epoch', version: 'legacy-version', token: 'legacy-token',
        refreshToken: 'legacy-refresh', user: { userid: 7 }
      })
    })
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      localStorageProvider: () => legacy,
      databaseName: 'seed-test'
    })

    await expect(storage.readCurrent()).resolves.toEqual({
      epoch: 'legacy-epoch', version: 'legacy-version', revision: 0, token: 'legacy-token',
      refreshToken: 'legacy-refresh', user: { userid: 7 }
    })
    legacy.setItem('woniunote:auth-session', JSON.stringify({
      epoch: 'stale-epoch', version: 'stale-version', token: 'stale-token',
      refreshToken: 'stale-refresh', user: { userid: 8 }
    }))
    await expect(storage.readCurrent()).resolves.toMatchObject({
      epoch: 'legacy-epoch', revision: 0, token: 'legacy-token', user: { userid: 7 }
    })
  })

  it('commits compare-and-update atomically and returns the durable winner', async () => {
    const fake = createFakeIndexedDB()
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      localStorageProvider: () => createMemoryStorage(),
      databaseName: 'compare-test'
    })
    const original = await storage.readCurrent()
    const update = await storage.transact((current) => ({
      session: { ...current, version: 'rotated-version', token: 'rotated-access' },
      result: true
    }))

    expect(original.revision).toBe(0)
    expect(update).toMatchObject({
      result: true,
      committed: true,
      session: { epoch: original.epoch, version: 'rotated-version', revision: 1, token: 'rotated-access' }
    })
    const stale = await storage.transact((current) => {
      if (current.version !== original.version) return { result: false }
      return { session: { ...current, token: 'late-access' }, result: true }
    })
    expect(stale).toMatchObject({ result: false, committed: false })
    await expect(storage.readCurrent()).resolves.toMatchObject({
      version: 'rotated-version', token: 'rotated-access'
    })
  })

  it('keeps a logout tombstone authoritative over stale legacy mirrors', async () => {
    const fake = createFakeIndexedDB()
    const legacy = createMemoryStorage({
      'woniunote:auth-session': JSON.stringify({
        epoch: 'old-epoch', version: 'old-version', token: 'old-access',
        refreshToken: 'old-refresh', user: { userid: 1 }
      })
    })
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      localStorageProvider: () => legacy,
      databaseName: 'tombstone-test'
    })
    const tombstone = await storage.transact((current) => ({
      session: {
        epoch: 'logout-epoch', version: 'logout-version', token: '',
        refreshToken: '', user: null
      },
      result: current.epoch === 'old-epoch'
    }))
    legacy.setItem('woniunote:auth-session', JSON.stringify({
      epoch: 'old-epoch', version: 'old-version', token: 'old-access',
      refreshToken: 'old-refresh', user: { userid: 1 }
    }))

    expect(tombstone.result).toBe(true)
    expect(tombstone.session.revision).toBe(1)
    await expect(storage.readCurrent()).resolves.toEqual(tombstone.session)
    fake.records.delete('current')
    await expect(storage.readCurrent()).rejects.toThrow('已阻止恢复旧登录状态')
  })

  it('fails closed when IndexedDB is missing, blocked by open failure, or contains a malformed record', async () => {
    const unsupported = createAuthSessionStorage({
      indexedDBFactory: () => undefined,
      databaseName: 'unsupported-test'
    })
    await expect(unsupported.readCurrent()).rejects.toThrow('不支持安全登录会话存储')

    const failed = createAuthSessionStorage({
      indexedDBFactory: () => createFakeIndexedDB({ failOpen: true }).indexedDB,
      databaseName: 'failed-open-test'
    })
    await expect(failed.readCurrent()).rejects.toThrow('open failed')

    const fake = createFakeIndexedDB()
    fake.records.set('initialized', true)
    fake.records.set('current', { token: 'bad' })
    const malformed = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      databaseName: 'malformed-test'
    })
    await expect(malformed.readCurrent()).rejects.toThrow('记录无效')
  })

  it('rejects a blocked open without claiming the session is available', async () => {
    const blocked = createFakeIndexedDB({ blocked: true })
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => blocked.indexedDB,
      databaseName: 'blocked-open-test'
    })

    await expect(storage.readCurrent()).rejects.toThrow('正在升级')
    expect(blocked.records.size).toBe(0)
  })

  it('reopens the database after another connection triggers versionchange', async () => {
    const fake = createFakeIndexedDB()
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      databaseName: 'versionchange-test'
    })

    const initial = await storage.readCurrent()
    fake.triggerVersionChange()
    await expect(storage.readCurrent()).resolves.toEqual(initial)
    expect(fake.getOpenCount()).toBe(2)
  })

  it('rejects read and write request errors through their aborted transactions', async () => {
    const fake = createFakeIndexedDB()
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      databaseName: 'request-errors-test'
    })
    await storage.readCurrent()

    fake.failNextRead('current')
    await expect(storage.readCurrent()).rejects.toThrow('read failed: current')

    fake.failNextWrite('current')
    await expect(storage.transact((current) => ({
      session: { ...current, token: 'must-not-commit' },
      result: true
    }))).rejects.toThrow('write failed: current')
    await expect(storage.readCurrent()).resolves.toMatchObject({ token: '' })
  })

  it('fails closed when the initialized marker is missing its record or has an invalid value', async () => {
    const missingRecordFake = createFakeIndexedDB()
    missingRecordFake.records.set('initialized', true)
    const missingRecord = createAuthSessionStorage({
      indexedDBFactory: () => missingRecordFake.indexedDB,
      databaseName: 'missing-record-test'
    })
    await expect(missingRecord.readCurrent()).rejects.toThrow('已阻止恢复旧登录状态')

    const invalidMarkerFake = createFakeIndexedDB()
    invalidMarkerFake.records.set('initialized', 'yes')
    const invalidMarker = createAuthSessionStorage({
      indexedDBFactory: () => invalidMarkerFake.indexedDB,
      databaseName: 'invalid-marker-test'
    })
    await expect(invalidMarker.readCurrent()).rejects.toThrow('初始化标记无效')
  })

  it('allocates monotonic revisions in IndexedDB and ignores updater-supplied revisions', async () => {
    const fake = createFakeIndexedDB()
    const storage = createAuthSessionStorage({
      indexedDBFactory: () => fake.indexedDB,
      localStorageProvider: () => createMemoryStorage({
        'woniunote:auth-session': JSON.stringify({
          epoch: 'legacy-e', version: 'legacy-v', revision: 900, token: '',
          refreshToken: '', user: null
        })
      }),
      databaseName: 'revision-test'
    })

    const seeded = await storage.readCurrent()
    expect(seeded.revision).toBe(0)
    const first = await storage.transact((current) => ({
      session: { ...current, revision: 1000000, token: 'one' }, result: true
    }))
    const second = await storage.transact((current) => ({
      session: { ...current, revision: -10, token: 'two' }, result: true
    }))

    expect(first.session.revision).toBe(1)
    expect(second.session.revision).toBe(2)
    await expect(storage.readCurrent()).resolves.toMatchObject({ revision: 2, token: 'two' })
  })

  it('fails closed when a stored revision is invalid or cannot be incremented safely', async () => {
    const invalidFake = createFakeIndexedDB()
    invalidFake.records.set('initialized', true)
    invalidFake.records.set('current', {
      epoch: 'e', version: 'v', revision: Number.MAX_SAFE_INTEGER + 1,
      token: '', refreshToken: '', user: null
    })
    const invalidStorage = createAuthSessionStorage({
      indexedDBFactory: () => invalidFake.indexedDB,
      databaseName: 'invalid-revision-test'
    })
    await expect(invalidStorage.readCurrent()).rejects.toThrow('记录无效')

    const overflowFake = createFakeIndexedDB()
    overflowFake.records.set('initialized', true)
    overflowFake.records.set('current', {
      epoch: 'e', version: 'v', revision: Number.MAX_SAFE_INTEGER,
      token: '', refreshToken: '', user: null
    })
    const overflowStorage = createAuthSessionStorage({
      indexedDBFactory: () => overflowFake.indexedDB,
      databaseName: 'overflow-revision-test'
    })
    await expect(overflowStorage.transact((current) => ({
      session: { ...current, token: 'must-not-commit' }, result: true
    }))).rejects.toThrow('版本已耗尽')
    await expect(overflowStorage.readCurrent()).resolves.toMatchObject({
      revision: Number.MAX_SAFE_INTEGER, token: ''
    })
  })
})
