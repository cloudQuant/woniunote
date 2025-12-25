import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 8888,
    allowedHosts: ['yunjinqi.top', 'www.yunjinqi.top', 'localhost', '127.0.0.1'],
    // 配置 HMR 以支持通过 Nginx SSL 代理连接
    hmr: {
      host: 'www.yunjinqi.top',
      clientPort: 443
    },
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
    sourcemap: false
  }
}))
