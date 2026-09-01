<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { UploadCloud, FileText, Sparkles, Check, RotateCcw, Save, X, AlertCircle, ScanText, Image } from 'lucide-vue-next'
import { api, errorMessage } from '../api'
import type { OCRResult } from '../types'
import MoneyInput from '../components/MoneyInput.vue'

const router = useRouter()
const step = ref(1)
const file = ref<File | null>(null)
const dragover = ref(false)
const processing = ref(false)
const progress = ref(0)
const saving = ref(false)
const error = ref('')
const result = ref<OCRResult | null>(null)
const previewUrl = ref('')
const previewMode = ref<'document' | 'detected'>('document')
const form = reactive({
  customer_name: '', quotation_number: '', customer_company: '', quotation_date: '',
  contact_person: '', project_department: '', contact_phone: '', salesperson: '',
  project_name: '', phone: '', sales_contact: '', quotation_status: '',
  subtotal: null as number | null, tax_amount: null as number | null,
  total_with_tax: null as number | null, discounted_total_with_tax: null as number | null,
  payment_terms: '', quotation_valid_until: '', notes: '', currency: 'TWD',
  customer_approval: '', sales_approval: '', manager_approval: '',
})
const accept = '.jpg,.jpeg,.png,.pdf'
const showRawOcr = false
let progressTimer: number | undefined

const confidence = computed(() => {
  if (!result.value?.lines.length) return 0
  return Math.round(result.value.lines.reduce((sum, line) => sum + line.confidence, 0) / result.value.lines.length * 100)
})
const lowConfidenceCount = computed(() => result.value?.lines.filter((line) => line.confidence < .8).length || 0)
const pageCount = computed(() => Math.max(0, ...(result.value?.lines.map((line) => line.page) || [])))
const progressStage = computed(() => {
  if (progress.value >= 100) return '分析完成，正在整理結果'
  if (progress.value >= 72) return '正在配對欄位與表格座標'
  if (progress.value >= 34) return 'PaddleOCR 正在辨識文字'
  return '正在安全上傳文件'
})

function confidenceTone(score: number) {
  return score >= .9 ? 'high' : score >= .8 ? 'medium' : 'low'
}

function choose(list: FileList | null) {
  const selected = list?.[0]
  if (!selected) return
  const allowed = ['image/jpeg', 'image/png', 'application/pdf']
  if (!allowed.includes(selected.type)) { error.value = '僅支援 JPG、JPEG、PNG、PDF'; return }
  if (selected.size > 20 * 1024 * 1024) { error.value = '檔案不可超過 20 MB'; return }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = selected
  previewUrl.value = URL.createObjectURL(selected)
  error.value = ''
}

async function recognize() {
  if (!file.value) return
  processing.value = true
  progress.value = 6
  window.clearInterval(progressTimer)
  progressTimer = window.setInterval(() => {
    if (progress.value < 92) {
      progress.value = Math.min(92, progress.value + Math.max(1, Math.round((94 - progress.value) * .08)))
    }
  }, 450)
  error.value = ''
  try {
    const body = new FormData(); body.append('file', file.value)
    const { data } = await api.post('/orders/ocr', body)
    result.value = data
    previewMode.value = 'document'
    Object.assign(form, {
      customer_name: data.suggested.customer_name || '',
      quotation_number: data.suggested.quotation_number || '',
      customer_company: data.suggested.customer_company || '',
      quotation_date: data.suggested.quotation_date || '',
      contact_person: data.suggested.contact_person || '',
      project_department: data.suggested.project_department || '',
      contact_phone: data.suggested.contact_phone || '',
      salesperson: data.suggested.salesperson || '',
      project_name: data.suggested.project_name || '',
      phone: data.suggested.phone || '',
      sales_contact: data.suggested.sales_contact || '',
      quotation_status: data.suggested.quotation_status || '',
      subtotal: data.suggested.subtotal,
      tax_amount: data.suggested.tax_amount,
      total_with_tax: data.suggested.total_with_tax,
      discounted_total_with_tax: data.suggested.discounted_total_with_tax,
      payment_terms: data.suggested.payment_terms || '',
      quotation_valid_until: data.suggested.quotation_valid_until || '',
      notes: data.suggested.notes || '',
      customer_approval: data.suggested.customer_approval || '',
      sales_approval: data.suggested.sales_approval || '',
      manager_approval: data.suggested.manager_approval || '',
      currency: data.suggested.currency || 'TWD',
    })
    progress.value = 100
    await new Promise((resolve) => window.setTimeout(resolve, 350))
    step.value = 2
  } catch (e) { error.value = errorMessage(e) }
  finally {
    window.clearInterval(progressTimer)
    progressTimer = undefined
    processing.value = false
  }
}

async function save() {
  if (!result.value || !form.quotation_number || !form.customer_name) { error.value = '請填寫報價單號／Case 編號與客戶名稱'; return }
  saving.value = true
  error.value = ''
  try {
    await api.post('/orders', {
      order_number: form.quotation_number,
      customer_name: form.customer_name,
      order_date: form.quotation_date || null,
      total_amount: form.discounted_total_with_tax ?? form.total_with_tax ?? form.subtotal,
      currency: form.currency,
      notes: form.notes,
      upload_token: result.value.upload_token,
      source_filename: result.value.filename, raw_text: result.value.raw_text,
      extracted_data: { ...form, lines: result.value.lines, average_confidence: confidence.value },
    })
    step.value = 3
  } catch (e) { error.value = errorMessage(e) }
  finally { saving.value = false }
}

function reset() {
  file.value = null; result.value = null; step.value = 1; error.value = ''
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}
onUnmounted(() => {
  window.clearInterval(progressTimer)
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div class="page new-order-page">
    <div class="page-heading compact"><div><div class="eyebrow"><span></span>AI EXTRACTION</div><h1>新增訂單</h1><p>上傳文件、確認辨識結果，再安全寫入資料庫。</p></div></div>
    <div class="stepper">
      <div :class="{ active: step >= 1 }"><i>1</i><span><b>上傳文件</b><small>圖片或 PDF</small></span></div><em></em>
      <div :class="{ active: step >= 2 }"><i>2</i><span><b>確認資料</b><small>檢查與修改</small></span></div><em></em>
      <div :class="{ active: step >= 3 }"><i>3</i><span><b>完成歸檔</b><small>寫入資料庫</small></span></div>
    </div>

    <section v-if="step === 1" class="panel upload-panel">
      <div class="dropzone" :class="{ dragover, filled: file }" @dragover.prevent="dragover = true" @dragleave="dragover = false" @drop.prevent="dragover = false; choose($event.dataTransfer?.files || null)">
        <input type="file" :accept="accept" @change="choose(($event.target as HTMLInputElement).files)" />
        <template v-if="!file"><div class="upload-icon"><UploadCloud :size="30" /></div><h2>拖放訂單至此</h2><p>或點擊選擇本機檔案</p><span class="formats">JPG · JPEG · PNG · PDF　/　MAX 20 MB</span></template>
        <template v-else><div class="file-selected"><div class="file-icon"><FileText :size="28" /></div><div><b>{{ file.name }}</b><small>{{ (file.size / 1024 / 1024).toFixed(2) }} MB · 已準備辨識</small></div><button class="icon-btn" @click.stop="reset"><X :size="18" /></button></div></template>
      </div>
      <div v-if="processing" class="ai-progress-card" aria-live="polite">
        <div class="ai-progress-head"><div><span class="progress-orbit"><Sparkles :size="16" /></span><span><b>AI 分析中</b><small>{{ progressStage }}</small></span></div><strong>{{ progress }}%</strong></div>
        <div class="ai-progress-track"><i :style="{ width: `${progress}%` }"></i></div>
        <div class="ai-progress-foot"><span>PADDLEOCR ENGINE</span><small>請保持此頁開啟，首次使用可能需要下載模型</small></div>
      </div>
      <div v-if="error" class="error-box"><AlertCircle :size="16" />{{ error }}</div>
      <div class="actions end"><button class="btn btn-primary" :disabled="!file || processing" @click="recognize"><Sparkles :size="17" />{{ processing ? 'AI 分析中…' : '開始 AI 辨識' }}</button></div>
    </section>

    <section v-if="step === 2" class="review-layout">
      <div class="panel document-preview">
        <div class="panel-head review-preview-head">
          <div><h2>{{ previewMode === 'document' ? '原始文件' : '辨識內容明細' }}</h2><p>{{ previewMode === 'document' ? file?.name : `共抓到 ${result?.lines.length || 0} 行文字` }}</p></div>
          <span class="confidence">平均信心 {{ confidence }}%</span>
        </div>
        <div class="review-mode-switch">
          <button :class="{ active: previewMode === 'document' }" @click="previewMode = 'document'"><Image :size="15" />原始文件</button>
          <button :class="{ active: previewMode === 'detected' }" @click="previewMode = 'detected'"><ScanText :size="15" />抓到的內容</button>
        </div>
        <div v-if="previewMode === 'document'" class="preview-frame"><img v-if="file?.type.startsWith('image/')" :src="previewUrl" alt="訂單預覽" /><iframe v-else :src="previewUrl"></iframe></div>
        <div v-else class="detected-content">
          <div class="detection-summary">
            <div><strong>{{ result?.lines.length || 0 }}</strong><span>文字行</span></div>
            <div><strong>{{ pageCount }}</strong><span>頁文件</span></div>
            <div :class="{ warning: lowConfidenceCount }"><strong>{{ lowConfidenceCount }}</strong><span>建議檢查</span></div>
          </div>
          <div v-if="lowConfidenceCount" class="review-hint"><AlertCircle :size="15" />低於 80% 的內容已用紅色標示，建議對照原始文件確認。</div>
          <div class="detected-lines">
            <article v-for="(line, index) in result?.lines" :key="index" :class="confidenceTone(line.confidence)">
              <span class="line-number">{{ String(index + 1).padStart(2, '0') }}</span>
              <div class="line-copy"><b>{{ line.text }}</b><small>第 {{ line.page }} 頁</small></div>
              <div class="line-score"><b>{{ Math.round(line.confidence * 100) }}%</b><span><i :style="{ width: `${Math.round(line.confidence * 100)}%` }"></i></span></div>
            </article>
            <div v-if="!result?.lines.length" class="empty-state"><ScanText :size="30" /><b>沒有抓到文字</b><span>建議換成更清晰、正向拍攝的文件再試一次。</span></div>
          </div>
        </div>
      </div>
      <div class="panel review-form">
        <div class="panel-head"><div><h2>擷取結果</h2><p>請確認所有欄位後再儲存</p></div><div class="ai-chip"><Sparkles :size="14" />AI 已完成</div></div>
        <form @submit.prevent="save">
          <div class="form-section-title"><span>01</span><div><b>基本資訊</b><small>客戶、專案與報價識別資料</small></div></div>
          <div class="form-row"><label>客戶名稱<input v-model="form.customer_name" placeholder="輸入客戶名稱" required /></label><label>報價單號 / Case 編號<input v-model="form.quotation_number" placeholder="例如 Q-2026-001" required /></label></div>
          <div class="form-row"><label>客戶單位<input v-model="form.customer_company" placeholder="公司或所屬單位" /></label><label>報價日期<input v-model="form.quotation_date" type="date" /></label></div>
          <div class="form-row"><label>連絡人<input v-model="form.contact_person" placeholder="客戶連絡人" /></label><label>專案部門<input v-model="form.project_department" placeholder="專案所屬部門" /></label></div>
          <div class="form-row"><label>連絡電話<input v-model="form.contact_phone" type="tel" placeholder="連絡人電話" /></label><label>業務<input v-model="form.salesperson" placeholder="負責業務" /></label></div>
          <div class="form-row"><label>專案名稱<input v-model="form.project_name" placeholder="輸入專案名稱" /></label><label>電話<input v-model="form.phone" type="tel" placeholder="公司電話" /></label></div>
          <div class="form-row"><label>業務窗口<input v-model="form.sales_contact" placeholder="業務窗口姓名" /></label><label>報價單狀態<input v-model="form.quotation_status" list="quotation-statuses" placeholder="例如：已報價" /><datalist id="quotation-statuses"><option value="待報價"></option><option value="已報價"></option><option value="已接受"></option><option value="已失效"></option><option value="已取消"></option></datalist></label></div>

          <div class="form-section-title"><span>02</span><div><b>金額資訊</b><small>所有金額將以 {{ form.currency }} 保存</small></div><select v-model="form.currency" aria-label="幣別"><option>TWD</option><option>USD</option><option>JPY</option><option>CNY</option></select></div>
          <div class="form-row"><label>未稅總計<MoneyInput v-model="form.subtotal" :currency="form.currency" /></label><label>5% 稅額<MoneyInput v-model="form.tax_amount" :currency="form.currency" /></label></div>
          <div class="form-row"><label>含稅總計<MoneyInput v-model="form.total_with_tax" :currency="form.currency" /></label><label>含稅優惠價格<MoneyInput v-model="form.discounted_total_with_tax" :currency="form.currency" /></label></div>

          <div class="form-section-title"><span>03</span><div><b>付款與條件</b><small>付款方式、效期及其他說明</small></div></div>
          <label>付款條件<input v-model="form.payment_terms" placeholder="例如：簽約 50%，驗收後 50%" /></label>
          <label>報價有效期限<input v-model="form.quotation_valid_until" placeholder="例如：2026/09/30 或報價後 30 天" /></label>
          <label>備註<textarea v-model="form.notes" rows="3" placeholder="可補充報價或專案說明"></textarea></label>

          <div class="form-section-title"><span>04</span><div><b>簽核資訊</b><small>由欄位正下方最近的文字擷取</small></div></div>
          <div class="form-row"><label>客戶確認<input v-model="form.customer_approval" placeholder="簽章／日期或確認內容" /></label><label>業務確認<input v-model="form.sales_approval" placeholder="簽章／日期或確認內容" /></label></div>
          <label>主管核准<input v-model="form.manager_approval" placeholder="簽章／日期或核准內容" /></label>
          <details v-if="showRawOcr"><summary>查看 OCR 原始文字（{{ result?.lines.length }} 行）</summary><pre>{{ result?.raw_text }}</pre></details>
          <div v-if="error" class="error-box"><AlertCircle :size="16" />{{ error }}</div>
          <div class="actions spread"><button type="button" class="btn btn-ghost" @click="reset"><RotateCcw :size="16" />重新上傳</button><button class="btn btn-primary" :disabled="saving"><Save :size="16" />{{ saving ? '儲存中…' : '確認並儲存' }}</button></div>
        </form>
      </div>
    </section>

    <section v-if="step === 3" class="panel success-panel"><div class="success-icon"><Check :size="38" /></div><div class="eyebrow"><span></span>SAVED SUCCESSFULLY</div><h2>訂單已成功歸檔</h2><p>辨識內容與原始檔案都已安全儲存，可立即前往訂單查詢。</p><div class="actions center"><button class="btn btn-ghost" @click="reset">繼續新增</button><button class="btn btn-primary" @click="router.push('/orders')">查看訂單</button></div></section>
  </div>
</template>
