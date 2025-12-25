import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 8888,
    allowedHosts: ['yunjinqi.top', 'www.yunjinqi.top', 'localhost'],
    hmr: false,  // 在通过 Nginx 代理访问时禁用 HMR
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
  }
})
