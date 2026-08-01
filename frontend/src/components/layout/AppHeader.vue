<template>
  <header class="app-header">
    <!-- 顶部Logo栏 -->
    <div class="top-bar">
      <div class="top-container">
        <router-link to="/" class="logo">
          <img src="/logo-transparent.png" alt="云子量化" class="logo-img" />
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
          <template v-for="cat in categoriesWithSubs" :key="cat.id">
            <el-dropdown
              v-if="cat.subs.length > 0"
              trigger="hover"
              @command="handleCategoryClick"
              class="nav-dropdown"
            >
              <span class="nav-item" @click="handleCategoryClick(cat.id)">
                {{ cat.name }}
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="sub in cat.subs"
                    :key="sub.id"
                    :command="sub.id"
                  >
                    {{ sub.label }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <button
              v-else
              type="button"
              class="nav-item nav-button"
              @click="handleCategoryClick(cat.id)"
            >
              {{ cat.name }}
            </button>
          </template>
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
            <button type="button" class="nav-item login-link" @click="showLoginModal = true">登录</button>
          </template>
        </div>
      </div>
    </div>
    
    <!-- 登录弹窗 -->
    <el-dialog 
      v-model="showLoginModal" 
      width="min(520px, 92vw)" 
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
          </div>
          <button type="button" class="login-close" @click="close" aria-label="关闭">×</button>
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
 * 计算带子分类的分类列表。
 * 优先使用后端返回的分类树；没有 tree 时由 store 用旧 ID 规则兜底。
 */
const categoriesWithSubs = computed(() => {
  const sourceTree = articleStore.articleTypeTree?.length
    ? articleStore.articleTypeTree
    : buildTreeFromTypes(articleStore.articleTypes || {})
  return sourceTree.map((cat) => ({
    id: cat.id,
    name: cat.name,
    subs: flattenMenuNodes(cat.children || [])
  }))
})

function buildTreeFromTypes(types) {
  const roots = []
  const byId = new Map()
  for (const [rawId, name] of Object.entries(types)) {
    const id = parseInt(rawId)
    byId.set(id, { id, name, children: [] })
  }
  for (const node of byId.values()) {
    const parentId = node.id >= 100 ? Math.floor(node.id / 100) : null
    if (parentId && byId.has(parentId)) {
      byId.get(parentId).children.push(node)
    } else {
      roots.push(node)
    }
  }
  const sortById = (nodes) => {
    nodes.sort((a, b) => a.id - b.id)
    nodes.forEach((node) => sortById(node.children || []))
    return nodes
  }
  return sortById(roots)
}

function flattenMenuNodes(nodes, depth = 0) {
  const result = []
  for (const node of nodes) {
    result.push({
      id: node.id,
      name: node.name,
      label: `${'　'.repeat(depth)}${node.name}`
    })
    if (Array.isArray(node.children) && node.children.length > 0) {
      result.push(...flattenMenuNodes(node.children, depth + 1))
    }
  }
  return result
}

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
  padding: var(--wn-space-4) var(--wn-space-5);
  display: flex;
  align-items: center;
  gap: var(--wn-space-5);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--wn-space-3);
  text-decoration: none;
}

.logo-img {
  height: 40px;
  width: auto;
  filter: var(--wn-logo-filter, none);
  transition: filter var(--wn-transition-base);
}

.slogan-wrapper {
  flex: 1;
  overflow: hidden;
  margin-left: var(--wn-space-5);
}

.slogan {
  display: inline-block;
  color: var(--wn-color-primary);
  font-size: var(--wn-font-size-xl);
  font-weight: 500;
  white-space: nowrap;
  animation: scrolling 20s linear infinite;
}

@keyframes scrolling {
  0% { transform: translateX(-20%); }
  100% { transform: translateX(100%); }
}

/* 减弱动效：系统开启 prefers-reduced-motion 时，slogan 跑马灯静止 (R9.1/R9.4) */
@media (prefers-reduced-motion: reduce) {
  .slogan {
    animation: none;
  }
}

/* 导航栏 - 使用主题导航色 */
.nav-bar {
  background: var(--wn-color-nav-bg);
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--wn-space-5);
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
  font-size: var(--wn-font-size-base);
  padding: var(--wn-space-3) 18px;
  text-decoration: none;
  transition: background 0.3s;
  display: flex;
  align-items: center;
  gap: var(--wn-space-1);
  cursor: pointer;
}

.nav-button {
  border: 0;
  cursor: pointer;
  font: inherit;
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
  /* 重置原生 button 默认样式，保持与原 span 视觉一致 */
  background: none;
  border: none;
  font: inherit;
  cursor: pointer;
}

.nav-dropdown {
  display: inline-block;
}

.nav-dropdown .nav-item {
  display: flex;
  align-items: center;
}

/* 搜索栏 - 桌面隐藏（桌面使用 Sidebar 搜索），仅移动端显示 */
.search-bar {
  display: none;
}

@media (max-width: 768px) {
  .nav-menu {
    flex-wrap: wrap;
  }
  
  .nav-item {
    padding: var(--wn-space-3) var(--wn-space-3);
    font-size: var(--wn-font-size-sm);
  }
  
  .slogan {
    display: none;
  }

  /* 移动端：在导航条下方、文章列表之上提供可达的搜索入口 */
  .search-bar {
    display: block;
    padding: var(--wn-space-3) var(--wn-space-5);
    background: var(--wn-color-surface);
    border-bottom: 1px solid var(--wn-color-border);
  }
}

/* 登录弹窗样式 */
:deep(.login-dialog) {
  border-radius: 4px;
  overflow: hidden;
  max-width: 92vw;
}

:deep(.login-dialog .el-dialog__header) {
  padding: 0;
  margin: 0;
}

:deep(.login-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.login-dialog .el-dialog__footer) {
  padding: var(--wn-space-4) var(--wn-space-5) var(--wn-space-5);
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
  padding: var(--wn-space-4) 28px;
  color: var(--wn-color-on-primary);
  cursor: pointer;
  font-size: var(--wn-font-size-md);
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
  /* 重置原生 button 默认样式，保持与原 span 视觉一致 */
  background: none;
  border: none;
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
  padding: var(--wn-space-7) var(--wn-space-7) var(--wn-space-3);
}

.login-form {
  width: 100%;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-form :deep(.el-form-item__label) {
  color: var(--wn-color-text);
  font-size: var(--wn-font-size-base);
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
  gap: var(--wn-space-4);
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
  gap: var(--wn-space-3);
}

.login-footer .el-button {
  min-width: 80px;
}
</style>
