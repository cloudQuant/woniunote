<template>
  <div class="profile-page">
    <h3 class="page-title">个人资料</h3>
    
    <el-form 
      ref="formRef"
      :model="form" 
      :rules="rules" 
      label-width="100px"
      style="max-width: 500px"
    >
      <el-form-item label="头像">
        <el-upload
          class="avatar-uploader"
          :show-file-list="false"
          :http-request="uploadAvatar"
          accept="image/*"
        >
          <el-avatar :size="100" :src="form.avatar">
            {{ userStore.user?.nickname?.charAt(0) || 'U' }}
          </el-avatar>
        </el-upload>
        <span class="avatar-tip">点击更换头像</span>
      </el-form-item>
      
      <el-form-item label="用户名">
        <el-input :value="userStore.user?.username" disabled />
      </el-form-item>
      
      <el-form-item label="昵称" prop="nickname">
        <el-input v-model="form.nickname" placeholder="请输入昵称" />
      </el-form-item>
      
      <el-form-item label="QQ" prop="qq">
        <el-input v-model="form.qq" placeholder="请输入QQ号" />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="saveProfile" :loading="saving">
          保存修改
        </el-button>
      </el-form-item>
    </el-form>
    
    <el-divider />
    
    <h3 class="page-title">修改密码</h3>
    
    <el-form 
      ref="passwordFormRef"
      :model="passwordForm" 
      :rules="passwordRules" 
      label-width="100px"
      style="max-width: 500px"
    >
      <el-form-item label="旧密码" prop="old_password">
        <el-input 
          v-model="passwordForm.old_password" 
          type="password" 
          placeholder="请输入旧密码"
          show-password
        />
      </el-form-item>
      
      <el-form-item label="新密码" prop="new_password">
        <el-input 
          v-model="passwordForm.new_password" 
          type="password" 
          placeholder="请输入新密码"
          show-password
        />
      </el-form-item>
      
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input 
          v-model="passwordForm.confirm_password" 
          type="password" 
          placeholder="请再次输入新密码"
          show-password
        />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="changePassword" :loading="changingPassword">
          修改密码
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
/**
 * @component Profile
 * @description 用户个人资料设置组件
 * 提供修改头像、昵称、QQ等个人信息的功能。
 * 同时包含修改密码的表单，支持旧密码验证和新密码确认。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { userApi, uploadApi } from '@/api'

const userStore = useUserStore()

const formRef = ref(null)
const passwordFormRef = ref(null)
const saving = ref(false)
const changingPassword = ref(false)

const form = reactive({
  nickname: '',
  avatar: '',
  qq: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  nickname: [
    { max: 30, message: '昵称不能超过30个字符', trigger: 'blur' }
  ]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入旧密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度在 6 到 32 个字符', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度在 6 到 32 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function uploadAvatar({ file }) {
  try {
    const res = await uploadApi.uploadAvatar(file)
    form.avatar = res.data.url
    ElMessage.success('头像上传成功')
  } catch (error) {
    console.error('上传失败:', error)
  }
}

async function saveProfile() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  saving.value = true
  try {
    const res = await userApi.updateProfile({
      nickname: form.nickname,
      avatar: form.avatar,
      qq: form.qq
    })
    userStore.updateUser(res.data)
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  if (!passwordFormRef.value) return
  
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  changingPassword.value = true
  try {
    await userApi.updatePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    passwordFormRef.value.resetFields()
  } catch (error) {
    console.error('修改密码失败:', error)
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  const user = userStore.user
  if (user) {
    form.nickname = user.nickname || ''
    form.avatar = user.avatar || ''
    form.qq = user.qq || ''
  }
})
</script>

<style scoped>
.profile-page {
  padding: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 25px;
  color: var(--wn-color-text);
}

.avatar-uploader {
  cursor: pointer;
}

.avatar-tip {
  display: block;
  font-size: 12px;
  color: var(--wn-color-text-muted);
  margin-top: 8px;
}
</style>
