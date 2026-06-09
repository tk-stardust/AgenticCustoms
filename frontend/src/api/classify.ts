import client from './client'
import type { Commodity, HsCodeResult } from '@/types'

export async function classifyCommodity(commodity: Commodity): Promise<HsCodeResult> {
  const { data } = await client.post<HsCodeResult>(
    '/classify',
    commodity,
    { timeout: 120000 },  // LLM 推理最长 2 分钟
  )
  return data
}
