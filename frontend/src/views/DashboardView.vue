<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowUpRight, Plus, ScanLine } from 'lucide-vue-next'
import StatCard from '../components/StatCard.vue'
import { api } from '../api'
import type { Order } from '../types'

const router = useRouter()
const stats = ref({ total_orders: 0, this_month: 0, total_amount: '0', pending_review: 0 })
const recent = ref<Order[]>([])
const money = (value: string | null) => new Intl.NumberFormat('zh-TW').format(Number(value || 0))
const date = (value: string) => new Intl.DateTimeFormat('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))

onMounted(async () => {
  const [s, o] = await Promise.all([api.get('/orders/stats'), api.get('/orders', { params: { page_size: 5 } })])
  stats.value = s.data
  recent.value = o.data.items
})
</script>

<template>
  <div class="page dashboard-page">
    <div class="page-heading">
      <div><div class="eyebrow"><span></span>OVERVIEW</div><h1>訂單營運總覽</h1><p>追蹤辨識進度與最新訂單狀態。</p></div>
      <button class="btn btn-primary" @click="router.push('/orders/new')"><Plus :size="18" />新增訂單</button>
    </div>
    <div class="stats-grid">
      <StatCard label="累計訂單" :value="stats.total_orders" helper="已歸檔筆數" />
      <StatCard label="本月新增" :value="stats.this_month" helper="本月處理量" tone="cyan" />
      <StatCard label="訂單總額" :value="`NT$ ${money(stats.total_amount)}`" helper="所有有效訂單" tone="violet" />
      <StatCard label="待確認" :value="stats.pending_review" helper="需要人工覆核" tone="amber" />
    </div>
    <div class="content-grid">
      <section class="panel recent-panel">
        <div class="panel-head"><div><h2>近期訂單</h2><p>最新建立與更新的訂單</p></div><button class="text-btn" @click="router.push('/orders')">查看全部 <ArrowUpRight :size="15" /></button></div>
        <div class="order-table-wrap"><table class="order-table"><thead><tr><th>訂單編號</th><th>客戶</th><th>金額</th><th>擁有者</th><th>建立時間</th></tr></thead><tbody>
          <tr v-for="order in recent" :key="order.id"><td><b>{{ order.order_number }}</b></td><td>{{ order.customer_name }}</td><td>NT$ {{ money(order.total_amount) }}</td><td><span class="owner-pill">{{ order.owner.name }}</span></td><td class="muted">{{ date(order.created_at) }}</td></tr>
          <tr v-if="!recent.length"><td colspan="5"><div class="empty-mini">尚無訂單，立即上傳第一張訂單。</div></td></tr>
        </tbody></table></div>
      </section>
      <aside class="panel quick-panel">
        <div class="scan-visual"><div class="scan-corners"></div><ScanLine :size="42" /><span></span></div>
        <h2>開始智慧辨識</h2><p>拖放圖片或 PDF，AI 將自動擷取訂單欄位供您確認。</p>
        <button class="btn btn-primary btn-wide" @click="router.push('/orders/new')">上傳訂單 <ArrowUpRight :size="17" /></button>
        <div class="model-state"><span></span><div><b>PaddleOCR</b><small>預訓練模型已就緒</small></div></div>
      </aside>
    </div>
  </div>
</template>

