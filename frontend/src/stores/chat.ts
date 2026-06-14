import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchHistory, clearHistory } from '@/api/chat'

interface ChatMessage {
  role: string
  content: string
  time: string
}

interface RedirectInfo {
  page: string
  label: string
  force?: boolean
  query?: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref('')
  const loading = ref(false)
  const pendingRedirect = ref<RedirectInfo | null>(null)
  const pendingComplete = ref(false)
  const pendingOriginalQuery = ref('')

  function initSessionId() {
    try { sessionId.value = localStorage.getItem('chat-session') || '' } catch { /* ok */ }
  }

  async function loadHistory(): Promise<boolean> {
    if (!sessionId.value) return false
    try {
      const list = await fetchHistory(sessionId.value)
      messages.value = list.map(m => ({ ...m, time: '' }))
      return true
    } catch { return false }
  }

  function pushMessage(role: string, content: string, time: string) {
    messages.value.push({ role, content, time })
  }

  function saveSessionId(id: string) {
    sessionId.value = id
    try { localStorage.setItem('chat-session', id) } catch { /* ok */ }
  }

  function setRedirect(r: RedirectInfo | null, complete: boolean, originalQuery = '') {
    pendingRedirect.value = r
    pendingComplete.value = complete
    pendingOriginalQuery.value = originalQuery
  }

  function clearRedirect() {
    pendingRedirect.value = null
    pendingComplete.value = false
    pendingOriginalQuery.value = ''
  }

  async function clearChat(): Promise<void> {
    if (sessionId.value) {
      try { await clearHistory(sessionId.value) } catch { /* ok */ }
    }
    messages.value = []
    clearRedirect()
  }

  return {
    messages, sessionId, loading, pendingRedirect, pendingComplete, pendingOriginalQuery,
    initSessionId, loadHistory, pushMessage, saveSessionId,
    setRedirect, clearRedirect, clearChat,
  }
})
