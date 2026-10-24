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
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { userApi, uploadApi } from '@/api'
import { notifyError } from '@/utils/errorToast'
import { logWarning } from '@/utils/logger'

const userStore = useUserStore()

const formRef = ref(null)
const passwordFormRef = ref(null)
const saving = ref(false)
const changingPassword = ref(false)
const profileOwner = ref(null)

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

function ownerKey(snapshot) {
  return JSON.stringify([snapshot?.epoch || '', snapshot?.userIdentity || null])
}

function clearPasswordFields() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate?.()
}

function resetProfileForCurrentUser(snapshot = userStore.captureCredentials()) {
  const user = userStore.user
  form.nickname = user?.nickname || ''
  form.avatar = user?.avatar || ''
  form.qq = user?.qq || ''
  profileOwner.value = ownerKey(snapshot)
  clearPasswordFields()
  formRef.value?.clearValidate?.()
}

watch(
  () => ownerKey(userStore.captureCredentials()),
  (nextOwner) => {
    if (profileOwner.value && profileOwner.value !== nextOwner) {
      resetProfileForCurrentUser(userStore.captureCredentials())
    }
  },
  { flush: 'sync' }
)

async function syncProfileOwnerForSubmit() {
  const ownerAtSubmit = profileOwner.value
  await userStore.syncSession()
  const snapshot = userStore.captureCredentials()
  const currentOwner = ownerKey(snapshot)
  if (!ownerAtSubmit) {
    resetProfileForCurrentUser(snapshot)
    return snapshot
  }
  if (currentOwner !== ownerAtSubmit || profileOwner.value !== currentOwner) {
    resetProfileForCurrentUser(snapshot)
    ElMessage.warning('登录账号已切换，资料已更新，请核对后再提交。')
    return null
  }
  return snapshot
}

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
    const snapshot = await syncProfileOwnerForSubmit()
    if (!snapshot) return
    const res = await uploadApi.uploadAvatar(file, { _sessionSnapshot: snapshot })
    await userStore.syncSession()
    if (!userStore.isSessionCurrent(snapshot) || profileOwner.value !== ownerKey(snapshot)) return
    form.avatar = res.data.url
    ElMessage.success('头像上传成功')
  } catch (error) {
    console.error('上传失败:', error)
    notifyError(error, '上传失败')
  }
}

async function saveProfile() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const snapshot = await syncProfileOwnerForSubmit()
    if (!snapshot) return
    const res = await userApi.updateProfile({
      nickname: form.nickname,
      avatar: form.avatar,
      qq: form.qq
    }, { _sessionSnapshot: snapshot })
    await userStore.syncSession()
    if (!userStore.isSessionCurrent(snapshot) || profileOwner.value !== ownerKey(snapshot)) return
    const updated = await userStore.updateUser(res.data, snapshot)
    if (!updated) return
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    notifyError(error, '保存失败')
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
    const snapshot = await syncProfileOwnerForSubmit()
    if (!snapshot) return
    await userApi.updatePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    }, { _sessionSnapshot: snapshot })
    await userStore.syncSession()
    if (!userStore.isSessionCurrent(snapshot)) return
    ElMessage.success('密码修改成功')
    passwordFormRef.value.resetFields()
  } catch (error) {
    console.error('修改密码失败:', error)
    notifyError(error, '修改密码失败')
  } finally {
    changingPassword.value = false
  }
}

onMounted(async () => {
  try {
    await userStore.syncSession()
  } catch (error) {
    // The store reports the storage failure and clears in-memory credentials.
    logWarning('用户资料页面无法同步登录状态', { message: error?.message || '未知错误' })
    return
  }
  if (!profileOwner.value) resetProfileForCurrentUser(userStore.captureCredentials())
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
