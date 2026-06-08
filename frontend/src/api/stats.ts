import client from './client'

export interface DashboardStats {
  total: number
  pass_rate: number
  warnings: number
  hs_codes: number
}

export async function fetchStats(): Promise<DashboardStats> {
  const { data } = await client.get('/stats')
  return data
}
