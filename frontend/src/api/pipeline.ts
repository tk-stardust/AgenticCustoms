import client from './client'
import type { Commodity, PipelineFullResponse } from '@/types'

export async function runFullPipeline(
  commodity: Commodity,
  targetCountry: string = 'US',
  signal?: AbortSignal,
): Promise<PipelineFullResponse> {
  const { data } = await client.post<PipelineFullResponse>(
    `/pipeline/full?target_country=${targetCountry}`,
    commodity,
    { timeout: 300000, signal },
  )
  return data
}
