import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/page/:page',
    name: 'HomePage',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/article/:id',
    name: 'ArticleDetail',
    component: () => import('@/views/ArticleDetail.vue'),
    meta: { title: '文章详情' }
  },
  {
    path: '/type/:type/:page',
    name: 'Category',
    component: () => import('@/views/Category.vue'),
    meta: { title: '分类' }
  },
  {
    path: '/type/:type',
    name: 'CategoryDefault',
    redirect: to => ({ name: 'Category', params: { type: to.params.type, page: 1 } })
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/Search.vue'),
    meta: { title: '搜索' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', guest: true }
  },
  {
    path: '/user',
    name: 'UserCenter',
    component: () => import('@/views/UserCenter.vue'),
    meta: { title: '个人中心', requiresAuth: true },
    children: [
      {
        path: '',
        name: 'UserProfile',
        component: () => import('@/views/user/Profile.vue'),
        meta: { title: '个人资料' }
      },
      {
        path: 'articles',
        name: 'UserArticles',
        component: () => import('@/views/user/MyArticles.vue'),
        meta: { title: '我的文章' }
      },
      {
        path: 'favorites',
        name: 'UserFavorites',
        component: () => import('@/views/user/MyFavorites.vue'),
        meta: { title: '我的收藏' }
      },
      {
        path: 'comments',
        name: 'UserComments',
        component: () => import('@/views/user/MyComments.vue'),
        meta: { title: '我的评论' }
      },
      {
        path: 'credits',
        name: 'UserCredits',
        component: () => import('@/views/user/MyCredits.vue'),
        meta: { title: '我的积分' }
      },
      {
        path: 'drafts',
        name: 'UserDrafts',
        component: () => import('@/views/user/MyDrafts.vue'),
        meta: { title: '我的草稿' }
      }
    ]
  },
  {
    path: '/write',
    name: 'WriteArticle',
    component: () => import('@/views/WriteArticle.vue'),
    meta: { title: '写文章', requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/AdminDashboard.vue'),
    meta: { title: '系统管理', requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/todo',
    name: 'Todo',
    component: () => import('@/views/Todo.vue'),
    meta: { title: '待办事项', requiresAuth: true }
  },
  {
    path: '/cards',
    name: 'Cards',
    component: () => import('@/views/Cards.vue'),
    meta: { title: '任务卡片', requiresAuth: true }
  },
  {
    path: '/edit/:id',
    name: 'EditArticle',
    component: () => import('@/views/WriteArticle.vue'),
    meta: { title: '编辑文章', requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面未找到' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - cloudQuant` : 'cloudQuant'
  
  // 需要登录的页面
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  // 需要管理员权限的页面
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next({ name: 'Home' })
    return
  }
  
  // 已登录用户访问登录/注册页面
  if (to.meta.guest && userStore.isLoggedIn) {
    next({ name: 'Home' })
    return
  }
  
  next()
})

export default router
