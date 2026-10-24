import { defineConfig } from 'vite'
import baseConfig from './vite.config.js'
import { createMockEgressLog, recordMockEgressDenied } from './e2e/support/mockEgress.js'

export default defineConfig((environment) => {
  if (process.env.WONIUNOTE_REAL_E2E === '1' || process.env.WONIUNOTE_API_PROXY_TARGET) {
    throw new Error('Mock preview refuses real-backend environment variables')
  }
  const egressLogPath = process.env.WONIUNOTE_MOCK_EGRESS_LOG
  if (!egressLogPath) throw new Error('Mock preview requires WONIUNOTE_MOCK_EGRESS_LOG')

  const config = baseConfig(environment)
  const guardPlugin = {
    name: 'woniunote-mock-preview-egress-guard',
    configurePreviewServer(server) {
      const state = {
        schemaVersion: 1,
        ready: true,
        deniedCount: 0,
        events: [],
        eventsTruncated: false
      }
      createMockEgressLog(egressLogPath)
      server.middlewares.use((request, response, next) => {
        let pathname
        try {
          pathname = new URL(request.url || '/', 'http://mock-preview.invalid').pathname
        } catch {
          return next()
        }
        const isApi = pathname === '/api' || pathname.startsWith('/api/')
        const isUpload = pathname === '/uploads' || pathname.startsWith('/uploads/')
        if (!isApi && !isUpload) return next()

        recordMockEgressDenied(egressLogPath, state, request.method, pathname)
        response.statusCode = 503
        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        response.setHeader('Cache-Control', 'no-store')
        response.setHeader('X-Woniunote-Mock-Egress', 'blocked')
        response.end(JSON.stringify({ code: 503, message: 'Mock E2E API egress blocked', data: null }))
      })
    }
  }

  return {
    ...config,
    // An explicit empty object prevents Vite preview from inheriting the
    // development server's /api and /uploads proxy rules.
    preview: { ...config.preview, proxy: {} },
    plugins: [...config.plugins, guardPlugin]
  }
})
