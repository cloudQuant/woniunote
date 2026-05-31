/**
 * @file main.js
 * @description Frontend application entry point. Initializes the Vue application,
 * registers global components (Element Plus icons), and applies global plugins (Pinia, Router, Element Plus).
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/themes/index.css'
import { useThemeStore } from './stores/theme'

/**
 * Create the Vue application instance.
 */
const app = createApp(App)

/**
 * Register all Element Plus icons globally.
 * This allows using icons as components without individual imports.
 */
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Initialize plugins
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 初始化主题（在挂载前应用持久化/系统偏好主题，配合 index.html 防闪烁脚本）
useThemeStore(pinia).initTheme()

// Mount the application
app.mount('#app')
