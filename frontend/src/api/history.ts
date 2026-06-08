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

export async function fetchHistory(limit: number = 20): Promise<HistoryRecord[]> {
  const { data } = await client.get<HistoryRecord[]>(`/history?limit=${limit}`)
  return data
}
