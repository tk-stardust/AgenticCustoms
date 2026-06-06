import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/classify',
    },
    {
      path: '/classify',
      name: 'classify',
      component: () => import('@/views/ClassifyView.vue'),
    },
    {
      path: '/pipeline',
      name: 'pipeline',
      component: () => import('@/views/PipelineView.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
    },
  ],
})

export default router
