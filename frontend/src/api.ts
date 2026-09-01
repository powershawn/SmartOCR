import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 300_000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('smartocr_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('smartocr_token')
      localStorage.removeItem('smartocr_user')
      if (location.pathname !== '/login') location.href = '/login'
    } else if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('smartocr:error', { detail: errorMessage(error) }))
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: any): string {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) {
    const labels: Record<string, string> = {
      date_from: '開始日期', date_to: '結束日期', owner_id: '帳號',
      order_date: '訂單日期', total_amount: '訂單金額',
    }
    return detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.at(-1) : ''
      return `${field ? `${labels[field] || field}：` : ''}${item.msg || '資料格式錯誤'}`
    }).join('\n')
  }
  return typeof detail === 'string' ? detail : error?.message || '發生未預期的錯誤'
}
