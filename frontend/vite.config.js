import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
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
    plugins: [
      vue(),
      // Element Plus 按需引入：模板里的 <el-*> 组件与 v-loading 等指令由
      // resolver 自动注入组件（含其样式），函数式 API（ElMessage 等）由
      // AutoImport 兜底。替代 main.js 中的全量 app.use(ElementPlus) 与
      // element-plus/dist/index.css，使 vendor-element-plus 只保留用到的部分。
      // dts: false —— 纯 JS 项目，不生成 auto-imports.d.ts / components.d.ts。
      AutoImport({ resolvers: [ElementPlusResolver()], dts: false }),
      Components({ resolvers: [ElementPlusResolver({ importStyle: 'css' })], dts: false })
    ],
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
            // Element Plus 必须保持未分配（返回 undefined）：
            // 函数式 manualChunks 会把每个被分配模块的整棵静态依赖拖进该 chunk
            // （Rollup addStaticDependenciesToManualChunk），element-plus 的
            // barrel（es/index.mjs）静态 import 了全部组件，一旦 barrel 被分配，
            // 按需引入就被整体打回（实测 343KB → 826KB）。交给 Rollup 默认分包。
            if (id.includes('/element-plus/')) return undefined
            if (id.includes('pdfjs-dist')) return 'vendor-pdfjs'
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
