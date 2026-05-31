<template>
  <header class="app-header">
    <!-- 顶部Logo栏 -->
    <div class="top-bar">
      <div class="top-container">
        <router-link to="/" class="logo">
          <img src="/logo.png" alt="cloudQuant Logo" class="logo-img" />
        </router-link>
        <div class="slogan-wrapper">
          <span class="slogan">量化投资 · 量化自我 · 量化是一生的修行</span>
        </div>
      </div>
    </div>
    
    <!-- 导航栏 -->
    <div class="nav-bar">
      <div class="nav-container">
        <nav class="nav-menu">
          <router-link to="/" class="nav-item">快捷导航</router-link>
          
          <!-- 带下拉菜单的分类导航 -->
          <el-dropdown 
            v-for="cat in categoriesWithSubs" 
            :key="cat.id"
            trigger="hover"
            @command="handleCategoryClick"
            class="nav-dropdown"
          >
            <span class="nav-item">
              {{ cat.name }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item 
                  v-for="sub in cat.subs" 
                  :key="sub.id"
                  :command="sub.id"
                >
                  {{ sub.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </nav>
        
        <div class="nav-right">
          <ThemeSwitcher />
          <template v-if="userStore.isLoggedIn">
            <el-dropdown trigger="click" @command="handleUserCommand">
              <span class="nav-item user-link">
                {{ userStore.user?.nickname || '用户' }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="write">写文章</el-dropdown-item>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="articles">我的文章</el-dropdown-item>
                  <el-dropdown-item command="favorites">我的收藏</el-dropdown-item>
                  <el-dropdown-item command="mathTraining">数学训练</el-dropdown-item>
                  <el-dropdown-item v-if="userStore.isAdmin" command="admin" divided>系统管理</el-dropdown-item>
                  <el-dropdown-item :divided="!userStore.isAdmin" command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <span class="nav-item login-link" @click="showLoginModal = true">登录</span>
          </template>
        </div>
      </div>
    </div>
    
    <!-- 登录弹窗 -->
    <el-dialog 
      v-model="showLoginModal" 
      width="520px" 
      :close-on-click-modal="false" 
      :show-close="false"
      class="login-dialog"
      :append-to-body="true"
    >
      <!-- 自定义头部 -->
      <template #header="{ close }">
        <div class="login-header">
          <div class="login-tabs">
            <span 
              :class="['login-tab', { active: activeTab === 'login' }]"
              @click="activeTab = 'login'"
            >登录</span>
            <span 
              :class="['login-tab', { active: activeTab === 'forgot' }]"
              @click="activeTab = 'forgot'"
            >找回密码</span>
          </div>
          <span class="login-close" @click="close">×</span>
        </div>
      </template>
      
      <!-- 登录表单 -->
      <div class="login-body" v-if="activeTab === 'login'">
        <el-form 
          :model="loginForm" 
          :rules="loginRules" 
          ref="loginFormRef" 
          label-width="100px"
          label-position="left"
          class="login-form"
        >
          <el-form-item label="登录邮箱：" prop="username">
            <el-input 
              v-model="loginForm.username" 
              placeholder="请输入你的邮箱地址"
              size="large"
            />
          </el-form-item>
          <el-form-item label="登录密码：" prop="password">
            <el-input 
              v-model="loginForm.password" 
              type="password" 
              placeholder="请输入你的登录密码" 
              show-password
              size="large"
            />
          </el-form-item>
          <el-form-item label="图片验证码：" prop="captchaCode">
            <div class="captcha-row">
              <el-input 
                v-model="loginForm.captchaCode" 
                placeholder="请输入右侧的验证码"
                size="large"
                class="captcha-input"
              />
              <img 
                :src="captchaImage" 
                alt="验证码" 
                class="captcha-img"
                @click="refreshCaptcha"
                title="点击刷新验证码"
              />
            </div>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 找回密码表单 -->
      <div class="login-body" v-else>
        <el-form 
          :model="forgotForm" 
          label-width="100px"
          label-position="left"
          class="login-form"
        >
          <el-form-item label="注册邮箱：">
            <el-input 
              v-model="forgotForm.email" 
              placeholder="请输入你的注册邮箱"
              size="large"
            />
          </el-form-item>
          <p class="forgot-tip">密码重置链接将发送到您的邮箱</p>
        </el-form>
      </div>
      
      <template #footer>
        <div class="login-footer">
          <el-button @click="showLoginModal = false" size="large">关闭</el-button>
          <el-button 
            v-if="activeTab === 'login'"
            type="primary" 
            @click="handleLogin" 
            :loading="loginLoading"
            size="large"
          >登录</el-button>
          <el-button 
            v-else
            type="primary" 
            @click="handleForgotPassword"
            size="large"
          >发送重置邮件</el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="search-container">
        <el-input
          v-model="searchKeyword"
          placeholder="请输入关键字"
          @keyup.enter="handleSearch"
          clearable
        >
          <template #append>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
      </div>
    </div>
  </header>
</template>

<script setup>
/**
 * @component AppHeader
 * @description 应用顶部导航组件
 * 包含 Logo、Slogan、导航菜单、用户登录/信息展示以及登录弹窗。
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'

const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

// 状态
const searchKeyword = ref('')
const showLoginModal = ref(false)
const loginLoading = ref(false)
const loginFormRef = ref(null)
const activeTab = ref('login')
const captchaImage = ref('')
const captchaId = ref('')

// 表单数据
const loginForm = reactive({
  username: '',
  password: '',
  captchaCode: ''
})

const forgotForm = reactive({
  email: ''
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ]
}

/**
 * 计算带子分类的分类列表
 * 将扁平的分类数据转换为层级结构（主分类 -> 子分类）
 */
const categoriesWithSubs = computed(() => {
  const types = articleStore.articleTypes
  const result = []
  
  // 获取主分类（ID < 100）
  const mainIds = Object.keys(types)
    .filter(id => parseInt(id) < 100)
    .sort((a, b) => parseInt(a) - parseInt(b))
  
  for (const mainId of mainIds) {
    const id = parseInt(mainId)
    const subs = []
    
    // 获取子分类（ID 在 mainId*100 到 (mainId+1)*100 之间）
    for (const [subId, subName] of Object.entries(types)) {
      const sid = parseInt(subId)
      if (sid >= id * 100 && sid < (id + 1) * 100) {
        subs.push({ id: sid, name: subName })
      }
    }
    
    result.push({
      id,
      name: types[mainId],
      subs
    })
  }
  
  return result
})

// 初始化
onMounted(async () => {
  await articleStore.fetchArticleTypes()
})

/**
 * 刷新验证码
 */
async function refreshCaptcha() {
  try {
    const response = await fetch('/api/captcha/generate')
    const data = await response.json()
    if (data.code === 200) {
      captchaImage.value = data.data.image
      captchaId.value = data.data.captcha_id
    }
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

// 监听登录弹窗打开
watch(showLoginModal, (newVal) => {
  if (newVal) {
    refreshCaptcha()
  }
})

/**
 * 处理搜索
 */
function handleSearch() {
  if (searchKeyword.value.trim()) {
    router.push({ name: 'Search', query: { keyword: searchKeyword.value } })
  }
}

/**
 * 处理分类点击
 * @param {number} typeId - 分类ID
 */
function handleCategoryClick(typeId) {
  router.push({ name: 'Category', params: { type: typeId, page: 1 } })
}

/**
 * 处理登录提交
 */
async function handleLogin() {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loginLoading.value = true
    try {
      await userStore.login(
        loginForm.username, 
        loginForm.password,
        captchaId.value,
        loginForm.captchaCode
      )
      showLoginModal.value = false
      ElMessage.success('登录成功')
      // 清空表单
      loginForm.username = ''
      loginForm.password = ''
      loginForm.captchaCode = ''
    } catch (error) {
      ElMessage.error(error.message || '登录失败')
      // 登录失败后刷新验证码
      refreshCaptcha()
    } finally {
      loginLoading.value = false
    }
  })
}

/**
 * 处理忘记密码
 */
function handleForgotPassword() {
  if (!forgotForm.email) {
    ElMessage.warning('请输入注册邮箱')
    return
  }
  ElMessage.info('密码重置功能开发中')
}

/**
 * 处理用户下拉菜单命令
 * @param {string} command - 菜单命令
 */
function handleUserCommand(command) {
  switch (command) {
    case 'write':
      router.push({ name: 'WriteArticle' })
      break
    case 'mathTraining':
      router.push({ name: 'MathTraining' })
      break
    case 'profile':
      router.push({ name: 'UserProfile' })
      break
    case 'articles':
      router.push({ name: 'UserArticles' })
      break
    case 'favorites':
      router.push({ name: 'UserFavorites' })
      break
    case 'admin':
      router.push({ name: 'AdminDashboard' })
      break
    case 'logout':
      userStore.logout()
      ElMessage.success('已退出登录')
      router.push({ name: 'Home' })
      break
  }
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--wn-color-surface);
}

/* 顶部Logo栏 */
.top-bar {
  background: var(--wn-color-surface);
  border-bottom: 1px solid var(--wn-color-border);
}

.top-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 15px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.logo-img {
  height: 40px;
  width: auto;
}

.logo-text {
  font-size: 24px;
  font-weight: bold;
  color: var(--wn-color-primary);
}

.slogan-wrapper {
  flex: 1;
  overflow: hidden;
  margin-left: 20px;
}

.slogan {
  display: inline-block;
  color: var(--wn-color-primary);
  font-size: 18px;
  font-weight: 500;
  white-space: nowrap;
  animation: scrolling 20s linear infinite;
}

@keyframes scrolling {
  0% { transform: translateX(-20%); }
  100% { transform: translateX(100%); }
}

/* 导航栏 - 使用主题导航色 */
.nav-bar {
  background: var(--wn-color-nav-bg);
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-menu {
  display: flex;
  gap: 0;
}

.nav-item {
  color: var(--wn-color-nav-text);
  font-size: 14px;
  padding: 12px 18px;
  text-decoration: none;
  transition: background 0.3s;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.nav-item:hover {
  background: var(--wn-color-nav-hover);
}

.nav-item.router-link-active {
  background: var(--wn-color-nav-active);
}

.nav-right {
  display: flex;
  align-items: center;
}

.user-link {
  cursor: pointer;
}

.login-link {
  cursor: pointer;
}

.nav-dropdown {
  display: inline-block;
}

.nav-dropdown .nav-item {
  display: flex;
  align-items: center;
}

/* 搜索栏 - 放在侧边栏 */
.search-bar {
  display: none;
}

@media (max-width: 768px) {
  .nav-menu {
    flex-wrap: wrap;
  }
  
  .nav-item {
    padding: 10px 12px;
    font-size: 13px;
  }
  
  .slogan {
    display: none;
  }
}

/* 登录弹窗样式 */
:deep(.login-dialog) {
  border-radius: 4px;
  overflow: hidden;
}

:deep(.login-dialog .el-dialog__header) {
  padding: 0;
  margin: 0;
}

:deep(.login-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.login-dialog .el-dialog__footer) {
  padding: 15px 20px 20px;
  border-top: 1px solid var(--wn-color-border);
}

.login-header {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  background: var(--wn-color-primary);
}

.login-tabs {
  display: flex;
}

.login-tab {
  padding: 15px 28px;
  color: var(--wn-color-on-primary);
  cursor: pointer;
  font-size: 15px;
  transition: background 0.3s;
  font-weight: 500;
}

.login-tab:hover {
  background: rgba(255, 255, 255, 0.15);
}

.login-tab.active {
  background: rgba(0, 0, 0, 0.1);
}

.login-close {
  display: flex;
  align-items: center;
  padding: 0 18px;
  color: var(--wn-color-on-primary);
  font-size: 24px;
  cursor: pointer;
  transition: background 0.3s;
}

.login-close:hover {
  background: rgba(255, 255, 255, 0.15);
}

.login-body {
  padding: 30px 30px 10px;
}

.login-form {
  width: 100%;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-form :deep(.el-form-item__label) {
  color: var(--wn-color-text);
  font-size: 14px;
}

.login-form :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--wn-color-border) inset;
  border-radius: var(--wn-radius-sm);
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--wn-color-border-strong) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--wn-color-primary) inset;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 15px;
}

.captcha-input {
  flex: 1;
}

.captcha-img {
  height: 42px;
  min-width: 120px;
  cursor: pointer;
  border-radius: 4px;
  transition: opacity 0.3s;
}

.captcha-img:hover {
  opacity: 0.85;
}

.login-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.login-footer .el-button {
  min-width: 80px;
}

.forgot-tip {
  color: var(--wn-color-text-muted);
  font-size: 13px;
  text-align: center;
  margin-top: 20px;
}
</style>
