<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-card">
        <h2 class="register-title">注册</h2>
        
        <el-form 
          ref="formRef"
          :model="form" 
          :rules="rules" 
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <el-form-item label="用户名" prop="username">
            <el-input 
              v-model="form.username" 
              placeholder="请输入用户名"
              :prefix-icon="User"
            />
          </el-form-item>
          
          <el-form-item label="昵称" prop="nickname">
            <el-input 
              v-model="form.nickname" 
              placeholder="请输入昵称（可选）"
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
          
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input 
              v-model="form.confirmPassword" 
              type="password"
              placeholder="请再次输入密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              native-type="submit"
              :loading="loading"
              class="register-btn"
            >
              注册
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="register-footer">
          已有账号？<router-link to="/login">立即登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @component Register
 * @description 用户注册页面组件
 * 提供用户注册表单，包含用户名、昵称、密码及确认密码的验证逻辑。
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度在 6 到 32 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleRegister() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await userStore.register({
      username: form.username,
      nickname: form.nickname || form.username,
      password: form.password
    })
    ElMessage.success('注册成功，请登录')
    router.push({ name: 'Login' })
  } catch (error) {
    console.error('注册失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: calc(100vh - 150px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--wn-color-primary) 0%, var(--wn-color-primary-active) 100%);
  padding: 40px 20px;
}

.register-container {
  width: 100%;
  max-width: 400px;
}

.register-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-lg);
  padding: 40px;
  box-shadow: var(--wn-shadow-lg);
}

.register-title {
  text-align: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--wn-color-text);
  margin: 0 0 30px;
}

.register-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.register-footer {
  text-align: center;
  margin-top: 20px;
  color: var(--wn-color-text-muted);
  font-size: 14px;
}

.register-footer a {
  color: var(--wn-color-link);
}
</style>
