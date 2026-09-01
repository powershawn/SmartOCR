<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, FilePlus2, Search, LogOut, ScanLine, ShieldCheck, AlertTriangle, X } from 'lucide-vue-next'
import { useAuth } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const alertMessage = ref('')

function showError(event: Event) {
  alertMessage.value = (event as CustomEvent<string>).detail || '發生未預期的錯誤'
}

onMounted(() => window.addEventListener('smartocr:error', showError))
onUnmounted(() => window.removeEventListener('smartocr:error', showError))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <router-view v-if="route.meta.public" />
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark"><ScanLine :size="22" /></span><span>Smart<span>OCR</span></span></div>
      <nav>
        <RouterLink to="/"><LayoutDashboard :size="19" />總覽</RouterLink>
        <RouterLink to="/orders/new"><FilePlus2 :size="19" />新增訂單</RouterLink>
        <RouterLink to="/orders"><Search :size="19" />訂單查詢</RouterLink>
      </nav>
      <div class="sidebar-foot">
        <div class="system-state"><span></span>AI 服務正常</div>
        <div class="profile">
          <img v-if="auth.user.value?.picture" :src="auth.user.value.picture" alt="" />
          <div v-else class="avatar">{{ auth.user.value?.name?.slice(0, 1) }}</div>
          <div class="profile-copy"><b>{{ auth.user.value?.name }}</b><small>{{ auth.user.value?.email }}</small></div>
          <button class="icon-btn" title="登出" @click="logout"><LogOut :size="17" /></button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <header class="topbar">
        <div class="mobile-brand"><ScanLine :size="20" /> SmartOCR</div>
        <div class="admin-chip" v-if="auth.isAdmin.value"><ShieldCheck :size="15" />系統管理員 · 全域資料</div>
      </header>
      <router-view />
    </main>
  </div>
  <div v-if="alertMessage" class="modal-backdrop alert-backdrop" role="presentation" @click.self="alertMessage = ''">
    <section class="alert-modal panel" role="alertdialog" aria-modal="true" aria-labelledby="error-title">
      <button class="icon-btn alert-close" aria-label="關閉" @click="alertMessage = ''"><X :size="18" /></button>
      <div class="alert-symbol"><AlertTriangle :size="28" /></div>
      <div>
        <div class="eyebrow"><span></span>SOMETHING WENT WRONG</div>
        <h2 id="error-title">操作未完成</h2>
        <p>{{ alertMessage }}</p>
      </div>
      <button class="btn btn-primary btn-wide" @click="alertMessage = ''">我知道了</button>
    </section>
  </div>
</template>
