import client from './client'
import type { Commodity, DeclarationDoc } from '@/types'

export async function runFullPipeline(
  commodity: Commodity,
  targetCountry: string = 'US',
): Promise<DeclarationDoc> {
  const { data } = await client.post<DeclarationDoc>(
    `/pipeline/full?target_country=${targetCountry}`,
    commodity,
  )
  return data
}
