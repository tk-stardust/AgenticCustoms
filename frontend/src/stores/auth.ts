import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, register as apiRegister, fetchMe } from '@/api/auth'

function safeStorage(key: string, value?: string): string | null {
  try {
    if (value !== undefined) localStorage.setItem(key, value)
    else return localStorage.getItem(key)
  } catch { /* storage disabled */ }
  return null
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(safeStorage('token') || '')
  const username = ref('')
  const loading = ref(false)
  let _checking = false

  function setToken(t: string) {
    token.value = t
    safeStorage('token', t)
  }

  async function login(username_: string, password: string) {
    loading.value = true
    try {
      const res = await apiLogin(username_, password)
      setToken(res.token)
      username.value = res.username
      return true
    } finally {
      loading.value = false
    }
  }

  async function register(username_: string, password: string) {
    loading.value = true
    try {
      const res = await apiRegister(username_, password)
      setToken(res.token)
      username.value = res.username
      return true
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    try {
      localStorage.removeItem('token')
      localStorage.removeItem('chat-session')
    } catch { /* ok */ }
  }

  async function checkAuth() {
    if (!token.value) return false
    if (_checking) return true  // 正在校验中，避免并发重复请求
    _checking = true
    try {
      const user = await fetchMe()
      username.value = user.username
      return true
    } catch {
      logout()
      return false
    } finally {
      _checking = false
    }
  }

  return { token, username, loading, login, register, logout, checkAuth }
})
