<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sendMessage, fetchHistory, clearHistory } from '@/api/chat'

const router = useRouter()
const input = ref('')
const messages = ref<{ role: string; content: string; time: string }[]>([])
const loading = ref(false)
const sessionId = ref((() => { try { return localStorage.getItem('chat-session') || '' } catch { return '' } })())
const pendingRedirect = ref<{ page: string; label: string; force?: boolean } | null>(null)
const pendingQuery = ref('')

const quickQuestions = [
  '什么是 HS 编码？',
  '出口美国需要注意什么？',
  'RCEP 是什么？',
  '蓝牙音箱应该归什么类？',
]

function genTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function loadHistory() {
  if (!sessionId.value) return
  try {
    const list = await fetchHistory(sessionId.value)
    messages.value = list.map(m => ({ ...m, time: '' }))
  } catch { /* no history yet */ }
}

onMounted(loadHistory)

async function send(text?: string) {
  const msg = (text || input.value).trim()
  if (!msg || loading.value) return

  // 处理跳转确认
  if (pendingRedirect.value) {
    if (/^[是不好]/i.test(msg)) {
      if (pendingRedirect.value.force) {
        messages.value.push({ role: 'assistant', content: '该功能需要在专用流程中完成，聊天暂不支持。请前往一键全流程页面。', time: genTime() })
        pendingRedirect.value = null
        pendingQuery.value = ''
        return
      } else {
        // 不跳转 → 用 skip_redirect 重新请求，在对话中直接回答
        const q = pendingQuery.value
        pendingRedirect.value = null
        pendingQuery.value = ''
        input.value = ''
        loading.value = true
        messages.value.push({ role: 'user', content: '不跳转，直接回答', time: genTime() })
        try {
          const res = await sendMessage(q, sessionId.value || undefined, true)
          if (!sessionId.value) { sessionId.value = res.session_id; try { localStorage.setItem('chat-session', res.session_id) } catch { /* ok */ } }
          messages.value.push({ role: 'assistant', content: res.reply, time: genTime() })
        } catch (e: any) { ElMessage.error(e?.message || '请求失败') }
        finally { loading.value = false }
        return
      }
    } else if (/^[跳转是好的]/i.test(msg)) {
      const r = pendingRedirect.value
      const q = encodeURIComponent(pendingQuery.value)
      pendingRedirect.value = null
      pendingQuery.value = ''
      router.push(`/${r.page}?q=${q}`)
      return
    }
    pendingRedirect.value = null
    pendingQuery.value = ''
  }

  messages.value.push({ role: 'user', content: msg, time: genTime() })
  input.value = ''
  loading.value = true

  try {
    const res = await sendMessage(msg, sessionId.value || undefined)
    if (!sessionId.value) {
      sessionId.value = res.session_id
      try { localStorage.setItem('chat-session', res.session_id) } catch { /* ok */ }
    }

    if (res.action === 'confirm_redirect') {
      pendingRedirect.value = res.redirect || null
      pendingQuery.value = msg
    } else if (res.action === 'redirect') {
      // Agent 直接跳转，不弹确认卡片
      const r = res.redirect
      const q = encodeURIComponent(msg)
      if (r) router.push(`/${r.page}?q=${q}`)
    }

    messages.value.push({ role: 'assistant', content: res.reply, time: genTime() })
  } catch (e: any) {
    ElMessage.error(e?.message || '发送失败')
  } finally {
    loading.value = false
    await nextTick()
    scrollBottom()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function scrollBottom() {
  const el = document.querySelector('.chat-messages')
  if (el) el.scrollTop = el.scrollHeight
}

async function clearChat() {
  try {
    await ElMessageBox.confirm('确认清空当前对话？', '清空对话', { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  if (sessionId.value) {
    try { await clearHistory(sessionId.value) } catch { /* ok */ }
  }
  messages.value = []
  pendingRedirect.value = null
}
</script>

<template>
  <div class="chat-panel">
    <!-- 顶部栏 -->
    <div class="chat-topbar" v-if="messages.length > 0">
      <button class="chat-clear-btn" @click="clearChat">清空对话</button>
    </div>

    <!-- 消息区 -->
    <div class="chat-messages">
      <div v-if="messages.length === 0" class="chat-empty">
        <div class="chat-empty-icon">🤖</div>
        <h3>你好，我是海关智能助手</h3>
        <p>可以帮你查 HS 编码、计算关税、校验合规风险等</p>
        <div class="quick-questions">
          <span
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            @click="send(q)"
          >{{ q }}</span>
        </div>
      </div>

      <template v-for="(msg, i) in messages" :key="i">
        <div :class="['chat-msg', msg.role]" :style="{ animationDelay: `${i * 0.05}s` }">
          <div class="chat-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="chat-msg-wrap">
            <div class="chat-bubble">{{ msg.content }}</div>
            <div class="chat-time" v-if="msg.time">{{ msg.time }}</div>
          </div>
        </div>
      </template>

      <div v-if="pendingRedirect" class="redirect-card">
        <div class="redirect-text">
          ⚡ 检测到你想进行<strong>{{ pendingRedirect.label }}</strong>，需要跳转到对应页面吗？
        </div>
        <div class="redirect-actions">
          <button class="redirect-btn primary" @click="send('跳转')">跳转</button>
          <button class="redirect-btn ghost" @click="send('不跳转')">不跳转</button>
        </div>
      </div>

      <div v-if="loading" class="chat-msg assistant">
        <div class="chat-avatar">🤖</div>
        <div>
          <div class="typing-indicator">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input-area">
      <div class="chat-input-card">
        <textarea
          v-model="input"
          class="chat-input"
          rows="2"
          placeholder="输入您的问题... (Enter 发送，Shift+Enter 换行)"
          @keydown="onKeydown"
          :disabled="loading"
        ></textarea>
        <div class="chat-input-actions">
          <span class="chat-hint">{{ loading ? 'AI 正在回复...' : 'Enter 发送 · Shift+Enter 换行' }}</span>
          <button class="chat-send-btn" :disabled="loading || !input.trim()" @click="send()">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-panel { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

/* 顶部栏 */
.chat-topbar {
  display: flex; align-items: center; justify-content: flex-end;
  padding: 4px 12px; flex-shrink: 0;
  background: #f9fafc; border-bottom: 1px solid var(--color-gray-200);
}

/* 消息区 */
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; background: #f9fafc; }
.chat-empty { text-align: center; padding: 48px 16px; color: var(--color-gray-400); }
.chat-empty-icon { font-size: 40px; margin-bottom: 12px; }
.chat-empty h3 { font-size: 16px; font-weight: 600; color: var(--color-gray-600); margin: 0 0 6px; }
.chat-empty p { font-size: 13px; margin: 0 0 16px; }
.quick-questions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.quick-tag {
  padding: 6px 14px; border-radius: 20px; font-size: 13px; color: var(--color-brand-600);
  background: var(--color-brand-50); cursor: pointer; transition: all 0.2s;
  border: 1px solid transparent;
}
.quick-tag:hover { background: var(--color-brand-100); border-color: var(--color-brand-300); }

/* 消息气泡 */
.chat-msg { display: flex; gap: 10px; margin-bottom: 16px; }
.chat-msg.user { justify-content: flex-end; }
.chat-msg.user .chat-avatar { order: 2; }
.chat-avatar {
  width: 32px; height: 32px; min-width: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
  background: var(--color-gray-100);
}
.chat-msg.user .chat-avatar { background: #e0e3ff; }
.chat-msg-wrap { max-width: 75%; }
.chat-bubble {
  padding: 12px 16px; border-radius: 16px; font-size: 14px;
  line-height: 1.6; white-space: pre-wrap; word-break: break-word;
}
.chat-msg.user .chat-bubble {
  background: var(--color-brand-600); color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg.assistant .chat-bubble {
  background: #fff; color: var(--color-gray-800);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 6px rgba(0,0,0,.05);
}
.chat-time { font-size: 12px; color: var(--color-gray-400); margin-top: 3px; padding: 0 10px; }
.chat-msg.user .chat-time { text-align: right; }

/* typing */
.typing-indicator { display: flex; gap: 4px; padding: 12px 16px; background: #fff; border-radius: 16px; border-bottom-left-radius: 4px; box-shadow: 0 1px 6px rgba(0,0,0,.05); }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-gray-300); animation: bounce 1.4s infinite ease-in-out both; }
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

/* 跳转卡片 */
.redirect-card {
  margin: 8px 0; padding: 14px; background: #fffbeb; border: 1px solid #fde68a;
  border-radius: 10px;
}
.redirect-text { font-size: 14px; color: #92400e; margin-bottom: 10px; }
.redirect-text strong { color: #78350f; }
.redirect-actions { display: flex; gap: 8px; }
.redirect-btn {
  padding: 6px 18px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; border: none;
}
.redirect-btn.primary { background: var(--color-brand-600); color: #fff; }
.redirect-btn.primary:hover { background: var(--color-brand-700); }
.redirect-btn.ghost { background: #fff; color: var(--color-gray-700); border: 1px solid var(--color-gray-300); }
.redirect-btn.ghost:hover { background: var(--color-gray-50); }

/* 输入区 */
.chat-input-area {
  flex-shrink: 0; padding: 0 16px 16px;
  background: #f9fafc;
}
.chat-input-card {
  background: #fff; border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,.06), 0 1px 4px rgba(0,0,0,.04);
  padding: 14px 16px 12px;
  display: flex; flex-direction: column; gap: 8px;
}
.chat-input {
  border: none; box-shadow: none; font-size: 14px; line-height: 1.55;
  padding: 4px 6px; min-height: 72px; max-height: 160px;
  font-family: inherit; resize: none; outline: none;
}
.chat-input:focus { box-shadow: none; }
.chat-input-actions { display: flex; justify-content: space-between; align-items: center; }
.chat-hint { font-size: 12px; color: #bdc3c7; }
.chat-send-btn {
  border-radius: 20px; font-size: 13px; font-weight: 600;
  height: 36px; padding: 0 20px;
  background: linear-gradient(135deg, var(--color-brand-600), var(--color-brand-700));
  border: none; color: #fff; cursor: pointer; transition: all 0.2s;
}
.chat-send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(13,148,136,.4);
}
.chat-send-btn:disabled { opacity: .5; cursor: not-allowed; }
.chat-clear-btn { background: none; border: none; font-size: 13px; color: var(--color-gray-400); cursor: pointer; }
.chat-clear-btn:hover { color: var(--color-danger); }
</style>
