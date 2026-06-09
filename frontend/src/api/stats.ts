import client from './client'

export interface DashboardStats {
  total: number
  pass_rate: number
  warnings: number
  hs_codes: number
  by_country: { country: string; count: number }[]
  by_risk: { risk: string; count: number }[]
}

export async function fetchStats(): Promise<DashboardStats> {
  const { data } = await client.get('/stats')
  return data
}
