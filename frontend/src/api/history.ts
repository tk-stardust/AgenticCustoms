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

export async function fetchHistory(
  page: number = 1,
  page_size: number = 20,
  search: string = '',
  filter: string = 'all',
): Promise<HistoryPage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(page_size) })
  if (search) params.set('search', search)
  if (filter !== 'all') params.set('filter', filter)
  const { data } = await client.get<HistoryPage>(`/history?${params.toString()}`)
  return data
}
