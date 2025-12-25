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
    // // 完全禁用 HMR WebSocket 连接
    // hmr: false,
     // 关键配置 ↓↓↓
    hmr: {
      // 方案1A：使用反向代理
      host: 'www.yunjinqi.top',
      port: 443,  // 如果使用了SSL证书
    },
    watch: {
      usePolling: false
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
    },
    // 添加头部解决跨域
    headers: {
      'Access-Control-Allow-Origin': '*',
    }
  },
  // 生产构建时不需要 HMR
  build: {
    sourcemap: false
  }
}))
