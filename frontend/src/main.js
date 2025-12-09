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
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// Mount the application
app.mount('#app')
