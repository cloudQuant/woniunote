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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { User, Document, Star, ChatDotRound, Coin, EditPen } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
</script>

<style scoped>
.user-center-page {
  padding: 20px 0;
  background: #f5f7fa;
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.user-sidebar {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.user-info {
  padding: 30px 20px;
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
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
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  min-height: 500px;
}

@media (max-width: 768px) {
  .user-sidebar {
    margin-bottom: 20px;
  }
}
</style>
