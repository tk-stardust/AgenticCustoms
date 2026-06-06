import client from './client'
import type { Commodity, HsCodeResult, ApiResponse } from '@/types'

export async function classifyCommodity(commodity: Commodity): Promise<HsCodeResult> {
  const { data } = await client.post<ApiResponse<HsCodeResult>>('/classify', commodity)
  return data.data
}
