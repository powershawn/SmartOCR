import { reactive, computed } from 'vue'
import { api } from '../api'
import type { User } from '../types'

const saved = localStorage.getItem('smartocr_user')
const state = reactive<{ user: User | null }>({ user: saved ? JSON.parse(saved) : null })

export function useAuth() {
  const save = (payload: { access_token: string; user: User }) => {
    localStorage.setItem('smartocr_token', payload.access_token)
    localStorage.setItem('smartocr_user', JSON.stringify(payload.user))
    state.user = payload.user
  }
  return {
    user: computed(() => state.user),
    isAdmin: computed(() => state.user?.role === 'admin'),
    async googleLogin(credential: string) {
      const { data } = await api.post('/auth/google', { credential })
      save(data)
    },
    async devLogin(email = 'demo@example.com', name = 'Demo User') {
      const { data } = await api.post('/auth/dev', { email, name })
      save(data)
    },
    logout() {
      localStorage.removeItem('smartocr_token')
      localStorage.removeItem('smartocr_user')
      state.user = null
    },
  }
}

