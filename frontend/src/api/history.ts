import client from './client'

export interface HistoryRecord {
  id: number
  request_id: string
  commodity_name: string
  commodity_description?: string
  hs_code: string
  target_country: string
  status: string
  created_at: string
  results: Record<string, unknown> | null
}

export interface HistoryPage {
  items: HistoryRecord[]
  total: number
  page: number
  page_size: number
}

export async function fetchHistory(page: number = 1, page_size: number = 20): Promise<HistoryPage> {
  const { data } = await client.get<HistoryPage>(`/history?page=${page}&page_size=${page_size}`)
  return data
}
