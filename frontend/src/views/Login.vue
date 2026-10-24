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

          <el-form-item label="图片验证码" prop="captchaCode">
            <div class="captcha-row">
              <el-input
                v-model="form.captchaCode"
                placeholder="请输入验证码"
                autocomplete="off"
              />
              <img
                :src="captchaImage"
                alt="图片验证码，点击刷新"
                class="captcha-image"
                @click="refreshCaptcha"
              />
            </div>
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
          还没有账号？<router-link :to="registerTarget">立即注册</router-link>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { notifyError } from '@/utils/errorToast'
import { authEntryTarget, getAuthRedirect } from '@/utils/authNavigation'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const captchaImage = ref('')
const captchaId = ref('')

const registerTarget = computed(() => authEntryTarget('Register', route.query.redirect, router))

const form = reactive({
  username: '',
  password: '',
  captchaCode: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度在 6 到 32 个字符', trigger: 'blur' }
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ]
}

async function refreshCaptcha() {
  try {
    const response = await fetch('/api/captcha/generate')
    const result = await response.json()
    if (result?.code !== 200 || !result.data?.captcha_id || !result.data?.image) {
      throw new Error(result?.message || '验证码暂不可用')
    }
    captchaId.value = result.data.captcha_id
    captchaImage.value = result.data.image
  } catch (error) {
    captchaId.value = ''
    captchaImage.value = ''
    notifyError(error, '获取验证码失败')
  }
}

onMounted(refreshCaptcha)

async function handleLogin() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  if (!captchaId.value) {
    notifyError(new Error('验证码暂不可用，请稍后刷新重试'), '登录失败')
    await refreshCaptcha()
    return
  }
  
  loading.value = true
  try {
    await userStore.login(form.username, form.password, captchaId.value, form.captchaCode)
    ElMessage.success('登录成功')
    
    const redirect = getAuthRedirect(route, router)
    router.push(redirect || '/')
  } catch (error) {
    console.error('登录失败:', error)
    notifyError(error, '登录失败')
    form.captchaCode = ''
    await refreshCaptcha()
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

.captcha-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.captcha-row :deep(.el-input) {
  flex: 1;
}

.captcha-image {
  width: 118px;
  height: 40px;
  object-fit: contain;
  cursor: pointer;
  border: 1px solid var(--wn-color-border);
  border-radius: var(--wn-radius-sm);
}
</style>
