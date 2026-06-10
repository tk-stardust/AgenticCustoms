import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { guest: true } },
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/classify', name: 'classify', component: () => import('@/views/ClassifyView.vue') },
    { path: '/compliance', name: 'compliance', component: () => import('@/views/ComplianceView.vue') },
    { path: '/tariff', name: 'tariff', component: () => import('@/views/TariffView.vue') },
    { path: '/pipeline', name: 'pipeline', component: () => import('@/views/PipelineView.vue') },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/history', name: 'history', component: () => import('@/views/HistoryView.vue') },
    { path: '/chat', name: 'chat', component: () => import('@/views/ChatView.vue') },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.guest) {
    next()
    return
  }
  if (!auth.token) {
    next('/login')
    return
  }
  if (!auth.username) {
    const ok = await auth.checkAuth()
    if (!ok) {
      next('/login')
      return
    }
  }
  next()
})

export default router
