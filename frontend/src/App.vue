<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <AppHeader />
      <main class="main-content">
        <router-view />
      </main>
      <AppFooter />
    </div>
  </el-config-provider>
</template>

<script setup>
/**
 * @file App.vue
 * @description Root component of the application.
 * Wraps the application in Element Plus configuration provider for internalization (zh-cn).
 * Defines the main layout structure with Header, Main Content area, and Footer.
 */
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
}
</style>
