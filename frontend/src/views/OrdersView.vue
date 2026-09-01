<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { Search, ChevronLeft, ChevronRight, X, Save, Database, RotateCcw, Trash2, AlertTriangle, CalendarRange } from 'lucide-vue-next'
import { api, errorMessage } from '../api'
import { useAuth } from '../stores/auth'
import type { Order, User } from '../types'
import MoneyInput from '../components/MoneyInput.vue'

const auth = useAuth()
const orders = ref<Order[]>([])
const users = ref<User[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const selected = ref<Order | null>(null)
const deleting = ref<Order | null>(null)
const deletingBusy = ref(false)
const filters = reactive({ q: '', status: '', owner_id: '', date_from: '', date_to: '', page: 1, page_size: 20 })
const edit = reactive({
  customer_name: '', quotation_number: '', customer_company: '', quotation_date: '',
  contact_person: '', project_department: '', contact_phone: '', salesperson: '',
  project_name: '', phone: '', sales_contact: '', quotation_status: '',
  subtotal: null as number | null, tax_amount: null as number | null,
  total_with_tax: null as number | null, discounted_total_with_tax: null as number | null,
  payment_terms: '', quotation_valid_until: '', notes: '', currency: 'TWD',
  customer_approval: '', sales_approval: '', manager_approval: '',
  record_status: 'confirmed',
})
let timer: number

const money = (value: string | null) => new Intl.NumberFormat('zh-TW').format(Number(value || 0))
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('zh-TW').format(new Date(value)) : '—'
const formatDateTime = (value: string | null) => value
  ? new Intl.DateTimeFormat('zh-TW', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    }).format(new Date(value))
  : '—'

const toDateInput = (date: Date) => [
  date.getFullYear(),
  String(date.getMonth() + 1).padStart(2, '0'),
  String(date.getDate()).padStart(2, '0'),
].join('-')

function dateRange(months: number) {
  const end = new Date()
  const start = new Date(end)
  if (months > 0) {
    const day = start.getDate()
    start.setDate(1)
    start.setMonth(start.getMonth() - months)
    const lastDay = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate()
    start.setDate(Math.min(day, lastDay))
  }
  return { from: toDateInput(start), to: toDateInput(end) }
}

function applyDateRange(months: number) {
  const range = dateRange(months)
  filters.date_from = range.from
  filters.date_to = range.to
  filters.page = 1
}

function isDateRangeActive(months: number) {
  const range = dateRange(months)
  return filters.date_from === range.from && filters.date_to === range.to
}

function resetFilters() {
  Object.assign(filters, {
    q: '', status: '', owner_id: '', date_from: '', date_to: '', page: 1, page_size: 20,
  })
}

async function load() {
  loading.value = true
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
  try { const { data } = await api.get('/orders', { params }); orders.value = data.items; total.value = data.total }
  catch (e) { error.value = errorMessage(e) }
  finally { loading.value = false }
}

function open(order: Order) {
  selected.value = order
  const data = order.extracted_data || {}
  Object.assign(edit, {
    customer_name: String(data.customer_name || order.customer_name || ''),
    quotation_number: String(data.quotation_number || order.order_number || ''),
    customer_company: String(data.customer_company || ''),
    quotation_date: String(data.quotation_date || order.order_date || ''),
    contact_person: String(data.contact_person || ''),
    project_department: String(data.project_department || ''),
    contact_phone: String(data.contact_phone || ''),
    salesperson: String(data.salesperson || ''),
    project_name: String(data.project_name || ''),
    phone: String(data.phone || ''),
    sales_contact: String(data.sales_contact || ''),
    quotation_status: String(data.quotation_status || ''),
    subtotal: data.subtotal == null ? null : Number(data.subtotal),
    tax_amount: data.tax_amount == null ? null : Number(data.tax_amount),
    total_with_tax: data.total_with_tax == null ? (order.total_amount == null ? null : Number(order.total_amount)) : Number(data.total_with_tax),
    discounted_total_with_tax: data.discounted_total_with_tax == null ? null : Number(data.discounted_total_with_tax),
    payment_terms: String(data.payment_terms || ''),
    quotation_valid_until: String(data.quotation_valid_until || ''),
    notes: String(data.notes || order.notes || ''),
    currency: String(data.currency || order.currency || 'TWD'),
    customer_approval: String(data.customer_approval || ''),
    sales_approval: String(data.sales_approval || ''),
    manager_approval: String(data.manager_approval || ''),
    record_status: order.status,
  })
}

async function save() {
  if (!selected.value) return
  try {
    await api.patch(`/orders/${selected.value.id}`, {
      order_number: edit.quotation_number,
      customer_name: edit.customer_name,
      order_date: edit.quotation_date || null,
      total_amount: edit.discounted_total_with_tax ?? edit.total_with_tax ?? edit.subtotal,
      currency: edit.currency,
      notes: edit.notes,
      status: edit.record_status,
      extracted_data: {
        ...selected.value.extracted_data,
        customer_name: edit.customer_name,
        quotation_number: edit.quotation_number,
        customer_company: edit.customer_company,
        quotation_date: edit.quotation_date || null,
        contact_person: edit.contact_person,
        project_department: edit.project_department,
        contact_phone: edit.contact_phone,
        salesperson: edit.salesperson,
        project_name: edit.project_name,
        phone: edit.phone,
        sales_contact: edit.sales_contact,
        quotation_status: edit.quotation_status,
        subtotal: edit.subtotal,
        tax_amount: edit.tax_amount,
        total_with_tax: edit.total_with_tax,
        discounted_total_with_tax: edit.discounted_total_with_tax,
        payment_terms: edit.payment_terms,
        quotation_valid_until: edit.quotation_valid_until,
        notes: edit.notes,
        currency: edit.currency,
        customer_approval: edit.customer_approval,
        sales_approval: edit.sales_approval,
        manager_approval: edit.manager_approval,
      },
    })
    selected.value = null; await load()
  } catch (e) { error.value = errorMessage(e) }
}

async function confirmDelete() {
  if (!deleting.value) return
  deletingBusy.value = true
  error.value = ''
  try {
    await api.delete(`/orders/${deleting.value.id}`)
    deleting.value = null
    if (orders.value.length === 1 && filters.page > 1) filters.page--
    else await load()
  } catch (e) { error.value = errorMessage(e) }
  finally { deletingBusy.value = false }
}

watch(() => [filters.q, filters.status, filters.owner_id, filters.date_from, filters.date_to], () => { window.clearTimeout(timer); filters.page = 1; timer = window.setTimeout(load, 350) })
watch(() => filters.page, load)
onMounted(async () => { if (auth.isAdmin.value) users.value = (await api.get('/users')).data; await load() })
</script>

<template>
  <div class="page orders-page">
    <div class="page-heading"><div><div class="eyebrow"><span></span>ORDER DATABASE</div><h1>訂單查詢</h1><p>{{ auth.isAdmin.value ? '管理員可檢視與管理所有帳號的訂單。' : '查詢與管理您帳號下的所有訂單。' }}</p></div><div class="record-count"><Database :size="17" /><b>{{ total }}</b> 筆資料</div></div>
    <section class="panel filter-panel">
      <div class="search-box"><Search :size="18" /><input v-model="filters.q" placeholder="搜尋訂單編號或客戶名稱…" /></div>
      <select v-if="auth.isAdmin.value" v-model="filters.owner_id"><option value="">所有帳號</option><option v-for="user in users" :key="user.id" :value="user.id">{{ user.name }} · {{ user.email }}</option></select>
      <select v-model="filters.status"><option value="">所有狀態</option><option value="confirmed">已確認</option><option value="pending">待確認</option><option value="cancelled">已取消</option></select>
      <button type="button" class="btn btn-ghost filter-reset" title="清除所有過濾條件" @click="resetFilters"><RotateCcw :size="15" />重設條件</button>
      <div class="date-filter-wrap">
        <div class="date-filter-label"><span><CalendarRange :size="15" /></span><div><b>訂單日期</b><small>選擇查詢區間</small></div></div>
        <div class="date-filter"><input v-model="filters.date_from" type="date" aria-label="開始日期" /><span>至</span><input v-model="filters.date_to" type="date" aria-label="結束日期" /></div>
        <div class="date-quick" aria-label="日期快捷篩選">
          <button type="button" :class="{ active: isDateRangeActive(0) }" @click="applyDateRange(0)">當日</button>
          <button type="button" :class="{ active: isDateRangeActive(3) }" @click="applyDateRange(3)">近 3 個月</button>
          <button type="button" :class="{ active: isDateRangeActive(6) }" @click="applyDateRange(6)">近 6 個月</button>
        </div>
      </div>
    </section>
    <div v-if="error" class="error-box">{{ error }}</div>
    <section class="panel orders-table-panel">
      <div class="order-table-wrap"><table class="order-table large"><thead><tr><th>訂單編號</th><th>客戶名稱</th><th>訂單日期</th><th>金額</th><th v-if="auth.isAdmin.value">帳號</th><th>狀態</th><th>建立時間</th><th class="action-heading">操作</th></tr></thead><tbody>
        <tr v-for="order in orders" :key="order.id" @click="open(order)"><td><b class="order-id">{{ order.order_number }}</b></td><td>{{ order.customer_name }}</td><td>{{ formatDate(order.order_date) }}</td><td><b>{{ order.currency }} {{ money(order.total_amount) }}</b></td><td v-if="auth.isAdmin.value"><div class="user-cell"><span>{{ order.owner.name.slice(0, 1) }}</span><div><b>{{ order.owner.name }}</b><small>{{ order.owner.email }}</small></div></div></td><td><span class="status-pill" :class="order.status">{{ order.status === 'confirmed' ? '已確認' : order.status === 'pending' ? '待確認' : '已取消' }}</span></td><td class="muted created-time">{{ formatDateTime(order.created_at) }}</td><td class="action-cell"><button type="button" class="icon-btn delete-order-btn" title="刪除訂單" :aria-label="`刪除訂單 ${order.order_number}`" @click.stop="deleting = order"><Trash2 :size="16" /></button></td></tr>
        <tr v-if="!orders.length && !loading"><td :colspan="auth.isAdmin.value ? 8 : 7"><div class="empty-state"><Database :size="32" /><b>沒有符合條件的訂單</b><span>調整搜尋條件或先新增訂單。</span></div></td></tr>
      </tbody></table></div>
      <div class="pagination"><span>第 {{ filters.page }} 頁，共 {{ Math.max(1, Math.ceil(total / filters.page_size)) }} 頁</span><div><button class="icon-btn" :disabled="filters.page <= 1" @click="filters.page--"><ChevronLeft :size="18" /></button><button class="icon-btn" :disabled="filters.page * filters.page_size >= total" @click="filters.page++"><ChevronRight :size="18" /></button></div></div>
    </section>

    <div v-if="deleting" class="modal-backdrop delete-backdrop" @click.self="deleting = null">
      <section class="panel delete-confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-order-title">
        <button class="icon-btn alert-close" aria-label="關閉" :disabled="deletingBusy" @click="deleting = null"><X :size="18" /></button>
        <div class="delete-symbol"><AlertTriangle :size="27" /></div>
        <div class="eyebrow"><span></span>SOFT DELETE</div>
        <h2 id="delete-order-title">刪除這筆訂單？</h2>
        <p>「{{ deleting.order_number }} · {{ deleting.customer_name }}」將從訂單查詢與統計中隱藏，資料庫紀錄及原始文件仍會保留。</p>
        <div class="actions end"><button type="button" class="btn btn-ghost" :disabled="deletingBusy" @click="deleting = null">取消</button><button type="button" class="btn btn-danger" :disabled="deletingBusy" @click="confirmDelete"><Trash2 :size="16" />{{ deletingBusy ? '刪除中…' : '確認刪除' }}</button></div>
      </section>
    </div>

    <div v-if="selected" class="modal-backdrop" @click.self="selected = null"><section class="modal order-edit-modal panel"><div class="modal-head"><div><div class="eyebrow"><span></span>ORDER DETAIL</div><h2>編輯完整訂單</h2></div><button class="icon-btn" @click="selected = null"><X :size="19" /></button></div><form @submit.prevent="save">
      <div class="form-section-title"><span>01</span><div><b>基本資訊</b><small>客戶、專案與報價識別資料</small></div></div>
      <div class="form-row"><label>客戶名稱<input v-model="edit.customer_name" required /></label><label>報價單號 / Case 編號<input v-model="edit.quotation_number" required /></label></div>
      <div class="form-row"><label>客戶單位<input v-model="edit.customer_company" /></label><label>報價日期<input v-model="edit.quotation_date" type="date" /></label></div>
      <div class="form-row"><label>連絡人<input v-model="edit.contact_person" /></label><label>專案部門<input v-model="edit.project_department" /></label></div>
      <div class="form-row"><label>連絡電話<input v-model="edit.contact_phone" type="tel" /></label><label>業務<input v-model="edit.salesperson" /></label></div>
      <div class="form-row"><label>專案名稱<input v-model="edit.project_name" /></label><label>電話<input v-model="edit.phone" type="tel" /></label></div>
      <div class="form-row"><label>業務窗口<input v-model="edit.sales_contact" /></label><label>報價單狀態<input v-model="edit.quotation_status" list="edit-quotation-statuses" /><datalist id="edit-quotation-statuses"><option value="待報價"></option><option value="已報價"></option><option value="已接受"></option><option value="已失效"></option><option value="已取消"></option></datalist></label></div>

      <div class="form-section-title"><span>02</span><div><b>金額資訊</b><small>未稅、稅額與含稅價格</small></div><select v-model="edit.currency" aria-label="幣別"><option>TWD</option><option>USD</option><option>JPY</option><option>CNY</option></select></div>
      <div class="form-row"><label>未稅總計<MoneyInput v-model="edit.subtotal" :currency="edit.currency" /></label><label>5% 稅額<MoneyInput v-model="edit.tax_amount" :currency="edit.currency" /></label></div>
      <div class="form-row"><label>含稅總計<MoneyInput v-model="edit.total_with_tax" :currency="edit.currency" /></label><label>含稅優惠價格<MoneyInput v-model="edit.discounted_total_with_tax" :currency="edit.currency" /></label></div>

      <div class="form-section-title"><span>03</span><div><b>付款與條件</b><small>付款方式、效期及其他說明</small></div></div>
      <div class="form-row"><label>付款條件<input v-model="edit.payment_terms" /></label><label>報價有效期限<input v-model="edit.quotation_valid_until" /></label></div>
      <label>備註<textarea v-model="edit.notes" rows="3"></textarea></label>

      <div class="form-section-title"><span>04</span><div><b>簽核資訊</b><small>客戶、業務與主管簽核內容</small></div></div>
      <div class="form-row"><label>客戶確認<input v-model="edit.customer_approval" /></label><label>業務確認<input v-model="edit.sales_approval" /></label></div>
      <div class="form-row"><label>主管核准<input v-model="edit.manager_approval" /></label><label>系統訂單狀態<select v-model="edit.record_status"><option value="confirmed">已確認</option><option value="pending">待確認</option><option value="cancelled">已取消</option></select></label></div>

      <div class="source-info"><span>來源檔案</span><b>{{ selected.source_filename }}</b><small>擁有者：{{ selected.owner.name }} · {{ selected.owner.email }}</small></div>
      <div class="actions end"><button type="button" class="btn btn-ghost" @click="selected = null">取消</button><button class="btn btn-primary"><Save :size="16" />儲存變更</button></div>
    </form></section></div>
  </div>
</template>
