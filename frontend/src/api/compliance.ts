import client from './client'

export interface ComplianceRequest {
  name: string
  description: string
  material: string
  function: string
  target_country: string
  hs_code?: string
}

export interface ComplianceResponse {
  risk_level: string
  violations: { category: string; description: string; severity: string; source: string }[]
  license_required: boolean
  license_type: string | null
  sanctions_hit: boolean
  summary: string
  hs_code: string
}

export async function checkCompliance(req: ComplianceRequest): Promise<ComplianceResponse> {
  const { data } = await client.post<ComplianceResponse>('/compliance', req, { timeout: 120000 })
  return data
}
