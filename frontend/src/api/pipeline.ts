import client from './client'
import type { Commodity, DeclarationDoc, ApiResponse } from '@/types'

export interface PipelineRequest {
  commodity: Commodity
  target_country: string
}

export async function runFullPipeline(req: PipelineRequest): Promise<DeclarationDoc> {
  const { data } = await client.post<ApiResponse<DeclarationDoc>>('/pipeline/full', req)
  return data.data
}
