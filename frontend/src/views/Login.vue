<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card">
        <h2 class="login-title">登录</h2>
        
        <el-form 
          ref="formRef"
          :model="form" 
          :rules="rules" 
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input 
              v-model="form.username" 
              placeholder="请输入用户名"
              :prefix-icon="User"
            />
          </el-form-item>
          
          <el-form-item label="密码" prop="password">
            <el-input 
              v-model="form.password" 
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              native-type="submit"
              :loading="loading"
              class="login-btn"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="login-footer">
          还没有账号？<router-link to="/register">立即注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @component Login
 * @description 用户登录页面组件
 * 提供用户名密码登录表单，包含表单验证和登录状态处理。
 */
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度在 6 到 32 个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    
    // 跳转到之前的页面或首页
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (error) {
    console.error('登录失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 150px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--wn-color-primary) 0%, var(--wn-color-primary-active) 100%);
  padding: 40px 20px;
}

.login-container {
  width: 100%;
  max-width: 400px;
}

.login-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-lg);
  padding: 40px;
  box-shadow: var(--wn-shadow-lg);
}

.login-title {
  text-align: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--wn-color-text);
  margin: 0 0 30px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  color: var(--wn-color-text-muted);
  font-size: 14px;
}

.login-footer a {
  color: var(--wn-color-link);
}
</style>
