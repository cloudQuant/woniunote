/**
 * @file main.js
 * @description Frontend application entry point. Initializes the Vue application
 * and applies global plugins (Pinia, Router). Element Plus components, directives
 * and their styles are imported on demand by unplugin-vue-components /
 * unplugin-auto-import (see vite.config.js); icons are imported per component.
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'

// ElMessage / ElMessageBox 在代码里是具名导入（便于单元测试 mock），resolver
// 不会改写已有 import，因此在这里显式引入其按需样式。样式是全局的，只需一次。
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/themes/index.css'
import { useThemeStore } from './stores/theme'

/**
 * Create the Vue application instance.
 */
const app = createApp(App)

// Initialize plugins
const pinia = createPinia()
app.use(pinia)
app.use(router)

// 初始化主题（在挂载前应用持久化/系统偏好主题，配合 index.html 防闪烁脚本）
useThemeStore(pinia).initTheme()

// Mount the application
app.mount('#app')
