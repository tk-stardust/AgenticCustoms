import client from './client'

interface ChatResponse {
  reply: string
  action?: string
  redirect?: { page: string; label: string; force?: boolean }
  session_id: string
}

interface HistoryItem {
  role: string
  content: string
}

export async function sendMessage(message: string, sessionId?: string, skipRedirect = false): Promise<ChatResponse> {
  const { data } = await client.post<ChatResponse>('/chat', { message, session_id: sessionId, skip_redirect: skipRedirect })
  return data
}

export async function fetchHistory(sessionId: string): Promise<HistoryItem[]> {
  const { data } = await client.get<HistoryItem[]>(`/chat/history?session_id=${sessionId}`)
  return data
}

export async function clearHistory(sessionId: string): Promise<void> {
  await client.delete(`/chat/history?session_id=${sessionId}`)
}
