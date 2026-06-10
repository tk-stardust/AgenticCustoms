import axios from 'axios'
import type { AxiosInstance, AxiosError } from 'axios'

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

let _redirecting = false

function safeStorage(key: string, value?: string): string | null {
  try {
    if (value !== undefined) localStorage.setItem(key, value)
    else return localStorage.getItem(key)
  } catch { /* storage disabled */ }
  return null
}

client.interceptors.request.use((config) => {
  const token = safeStorage('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string | { msg: string }[] }>) => {
    // 网络错误（服务器无响应）不跳转
    if (!error.response) {
      return Promise.reject(new Error('网络连接失败，请检查网络'))
    }
    const status = error.response.status
    const path = window.location.pathname

    // 401 且不在登录/注册页时，跳转登录
    if (status === 401 && path !== '/login' && path !== '/register') {
      if (!_redirecting) {
        _redirecting = true
        safeStorage('token', '')
        safeStorage('chat-session', '')
        window.location.href = '/login'
      }
      return Promise.reject(new Error('登录已过期，请重新登录'))
    }

    let message = error.message || '请求失败'
    const detail = error.response.data?.detail
    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail)) {
      message = detail.map((e: { msg: string }) => e.msg).join('；')
    } else if (detail) {
      message = String(detail)
    }
    return Promise.reject(new Error(message))
  },
)

export default client
