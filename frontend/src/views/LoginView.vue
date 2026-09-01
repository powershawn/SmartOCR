<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ScanLine, FileCheck2, ShieldCheck, Zap, ArrowRight } from 'lucide-vue-next'
import { useAuth } from '../stores/auth'
import { errorMessage } from '../api'

declare global {
  interface Window { google?: any; handleGoogleLogin?: (response: any) => void }
}

const router = useRouter()
const auth = useAuth()
const error = ref('')
const loading = ref(false)
const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
const allowDev = import.meta.env.VITE_ALLOW_DEV_LOGIN === 'true'
const adminEmail = import.meta.env.VITE_SUPER_ADMIN_EMAIL || 'admin@example.com'

async function finish(action: () => Promise<void>) {
  loading.value = true
  error.value = ''
  try { await action(); router.push('/') }
  catch (e) { error.value = errorMessage(e) }
  finally { loading.value = false }
}

onMounted(() => {
  if (!clientId) return
  window.handleGoogleLogin = (response) => finish(() => auth.googleLogin(response.credential))
  const script = document.createElement('script')
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  script.onload = () => {
    window.google.accounts.id.initialize({ client_id: clientId, callback: window.handleGoogleLogin })
    window.google.accounts.id.renderButton(document.getElementById('google-button'), {
      theme: 'filled_black', size: 'large', width: 340, shape: 'pill', text: 'continue_with', locale: 'zh-TW',
    })
  }
  document.head.appendChild(script)
})
</script>

<template>
  <div class="login-page">
    <div class="login-grid"></div>
    <section class="login-hero">
      <div class="brand login-brand"><span class="brand-mark"><ScanLine :size="22" /></span><span>Smart<span>OCR</span></span></div>
      <div class="hero-copy">
        <div class="eyebrow"><span></span>INTELLIGENT ORDER AUTOMATION</div>
        <h1>讓每一張訂單<br /><em>秒速成為資料。</em></h1>
        <p>以 AI 辨識、人工覆核與權限控管，打造可靠而流暢的訂單數位化流程。</p>
        <div class="feature-row">
          <div><Zap :size="19" /><span><b>快速辨識</b><small>圖片與 PDF</small></span></div>
          <div><FileCheck2 :size="19" /><span><b>人工校對</b><small>資料更精準</small></span></div>
          <div><ShieldCheck :size="19" /><span><b>帳號隔離</b><small>安全可控</small></span></div>
        </div>
      </div>
      <small class="login-version">SMARTOCR PLATFORM / V1.0</small>
    </section>
    <section class="login-panel">
      <div class="login-box">
        <div class="mini-icon"><ScanLine :size="27" /></div>
        <h2>歡迎回來</h2>
        <p>使用 Google 帳號登入工作區</p>
        <div id="google-button" class="google-button"></div>
        <div v-if="!clientId" class="config-note">尚未設定 Google Client ID，可先使用下方開發體驗登入。</div>
        <template v-if="allowDev">
          <div class="divider"><span>開發環境體驗</span></div>
          <button class="btn btn-primary btn-wide" :disabled="loading" @click="finish(() => auth.devLogin())">體驗一般帳號 <ArrowRight :size="17" /></button>
          <button class="btn btn-ghost btn-wide" :disabled="loading" @click="finish(() => auth.devLogin(adminEmail, 'System Admin'))">體驗最高管理員</button>
        </template>
        <div v-if="error" class="error-box">{{ error }}</div>
        <small class="privacy">登入即表示您同意服務條款與隱私權政策</small>
      </div>
    </section>
  </div>
</template>
