<template>
  <div class="user-center-page">
    <div class="container">
      <el-row :gutter="20">
        <el-col :span="5" :xs="24">
        <div class="user-sidebar">
          <div class="user-info">
            <el-avatar :size="80" :src="userStore.user?.avatar">
              {{ userStore.user?.nickname?.charAt(0) || 'U' }}
            </el-avatar>
            <h3 class="user-name">{{ userStore.user?.nickname }}</h3>
            <p class="user-credit">积分: {{ userStore.user?.credit }}</p>
          </div>
          
          <el-menu
            :default-active="activeMenu"
            router
          >
            <el-menu-item index="/user">
              <el-icon><User /></el-icon>
              <span>个人资料</span>
            </el-menu-item>
            <el-menu-item index="/user/articles">
              <el-icon><Document /></el-icon>
              <span>我的文章</span>
            </el-menu-item>
            <el-menu-item v-if="userStore.isAdmin" index="/user/categories">
              <el-icon><Menu /></el-icon>
              <span>分类管理</span>
            </el-menu-item>
            <el-menu-item index="/user/favorites">
              <el-icon><Star /></el-icon>
              <span>我的收藏</span>
            </el-menu-item>
            <el-menu-item index="/user/comments">
              <el-icon><ChatDotRound /></el-icon>
              <span>我的评论</span>
            </el-menu-item>
            <el-menu-item index="/user/credits">
              <el-icon><Coin /></el-icon>
              <span>我的积分</span>
            </el-menu-item>
            <el-menu-item index="/user/drafts">
              <el-icon><EditPen /></el-icon>
              <span>我的草稿</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-col>
      <el-col :span="19" :xs="24">
        <div class="user-content">
          <router-view />
        </div>
      </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @component UserCenter
 * @description 用户中心布局组件
 * 包含左侧用户信息/导航栏和右侧内容区域。
 * 负责展示通过 `router-view` 渲染的子路由组件（如个人资料、文章管理等）。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { User, Document, Star, ChatDotRound, Coin, EditPen, Menu } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
</script>

<style scoped>
.user-center-page {
  padding: 20px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.user-sidebar {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  overflow: hidden;
}

.user-info {
  padding: 30px 20px;
  text-align: center;
  background: linear-gradient(135deg, var(--wn-color-primary) 0%, var(--wn-color-primary-active) 100%);
  color: var(--wn-color-on-primary);
}

.user-name {
  margin: 15px 0 5px;
  font-size: 18px;
}

.user-credit {
  margin: 0;
  font-size: 14px;
  opacity: 0.8;
}

.user-content {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  padding: 30px;
  min-height: 500px;
}

@media (max-width: 768px) {
  .user-sidebar {
    margin-bottom: 20px;
  }
}
</style>
