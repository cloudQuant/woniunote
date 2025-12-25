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
    hmr: {
      // 禁用 HMR 在生产代理环境中，或配置正确的 host
      clientPort: 8888,
      host: 'localhost'
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
  }
})
