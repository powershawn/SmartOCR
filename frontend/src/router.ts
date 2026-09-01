import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import DashboardView from './views/DashboardView.vue'
import NewOrderView from './views/NewOrderView.vue'
import OrdersView from './views/OrdersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/', component: DashboardView },
    { path: '/orders/new', component: NewOrderView },
    { path: '/orders', component: OrdersView },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('smartocr_token')
  if (!to.meta.public && !token) return '/login'
  if (to.path === '/login' && token) return '/'
})

export default router

