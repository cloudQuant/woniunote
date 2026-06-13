import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig(() => {
  // HMR over the production domain (SSL via Nginx) is only correct when the
  // dev server is actually reached through that domain. For local dev
  // (http://localhost:8888) those settings make the HMR client try to reach
  // wss://www.yunjinqi.top:443, which fails and triggers repeated full-page
  // reloads. Enable the prod HMR config only when WONIUNOTE_PUBLIC_HMR=1.
  const usePublicHmr = process.env.WONIUNOTE_PUBLIC_HMR === '1'
  const hmr = usePublicHmr
    ? { host: 'www.yunjinqi.top', clientPort: 443 }
    : true

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        // ESM-safe path resolution ("type":"module" → no __dirname).
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: '0.0.0.0',
      port: 8888,
      allowedHosts: ['yunjinqi.top', 'www.yunjinqi.top', 'localhost', '127.0.0.1'],
      // 本地开发使用默认 HMR（localhost:8888）；仅当通过公网域名+SSL 反代访问时
      // 才用生产 HMR 设置（WONIUNOTE_PUBLIC_HMR=1）。
      hmr,
      proxy: {
        '/api': {
          target: 'http://localhost:5173',
          changeOrigin: true
        },
        '/uploads': {
          target: 'http://localhost:5173',
          changeOrigin: true
        }
      }
    },
    preview: {
      host: '0.0.0.0',
      port: 8888,
      allowedHosts: ['yunjinqi.top', 'www.yunjinqi.top', 'localhost', '127.0.0.1'],
      proxy: {
        '/api': {
          target: 'http://localhost:5173',
          changeOrigin: true
        },
        '/uploads': {
          target: 'http://localhost:5173',
          changeOrigin: true
        }
      }
    },
    // 生产构建时不需要 HMR
    build: {
      sourcemap: false,
      // Raise the warning ceiling: pdfjs-dist is intrinsically large and lives
      // in its own lazily-loaded chunk, so it should not flag the whole build.
      chunkSizeWarningLimit: 1600,
      rollupOptions: {
        onwarn(warning, warn) {
          if (warning.code === 'INVALID_ANNOTATION' && warning.id?.includes('@vueuse/core')) {
            return
          }
          warn(warning)
        },
        output: {
          // Split heavy third-party libs into their own long-cached vendor
          // chunks so the app shell stays small and library upgrades don't
          // bust the app bundle's cache (and vice versa).
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined
            if (id.includes('pdfjs-dist')) return 'vendor-pdfjs'
            if (id.includes('element-plus') || id.includes('@element-plus')) {
              return 'vendor-element-plus'
            }
            if (
              id.includes('/vue/') ||
              id.includes('/@vue/') ||
              id.includes('/vue-router/') ||
              id.includes('/pinia/')
            ) {
              return 'vendor-vue'
            }
            return 'vendor'
          }
        }
      }
    }
  }
})
