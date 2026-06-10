import client from './client'
import type { TariffRequest, TariffCalcResponse } from '@/types'

export async function queryTariff(req: TariffRequest): Promise<TariffCalcResponse> {
  const { data } = await client.post<TariffCalcResponse>(
    '/tariff',
    req,
    { timeout: 120000 },
  )
  return data
}
