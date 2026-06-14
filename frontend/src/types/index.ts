// ---- 枚举 ----
export type RiskLevel = 'red' | 'yellow' | 'green'


export type PipelineStep =
  | 'input'
  | 'classifying'
  | 'parallel'
  | 'generating'
  | 'done'

// ---- 领域实体（与后端 Pydantic 对齐）----

export interface Commodity {
  name: string
  material?: string
  function?: string
  usage?: string
  description: string
  quantity?: number
  declared_value?: number
  image_url?: string
}

export interface HsCodeResult {
  code: string
  description: string
  confidence: number
  reasoning_path: string[]
  citations: string[]
  alternatives: HsCodeResult[]
}

export interface TariffItem {
  name: string
  rate: number
  amount?: number
  note: string
}

export interface TariffResult {
  hs_code: string
  country: string
  items: TariffItem[]
  total_rate: number
  total_amount?: number
  fta_applied?: string
  fta_saving?: number
  data_missing?: boolean
}

export interface Violation {
  category: string
  description: string
  severity: RiskLevel
  source: string
}

export interface ComplianceResult {
  risk_level: RiskLevel
  violations: Violation[]
  license_required: boolean
  license_type?: string
  sanctions_hit: boolean
  summary: string
}

export interface OriginResult {
  hs_code: string
  applicable_ftas: string[]
  recommended_origin?: string
  meeting_criteria: string[]
  rvc_percentage?: number
  note: string
}

export interface CrossCheckItem {
  name: string
  passed: boolean
  detail: string
}

export interface DeclarationDoc {
  customs_declaration: Record<string, unknown>
  origin_certificate?: Record<string, unknown>
  compliance_statement: string
  cross_check_passed: boolean
  cross_check_errors: string[]
  cross_check_items: CrossCheckItem[]
  request_id?: string
}

// ---- 流水线 ----

export interface StepError {
  step: string
  message: string
}

export interface PipelineFullResponse {
  request_id: string
  documents: DeclarationDoc
  hs_result: HsCodeResult
  tariff_result: TariffResult
  compliance_result: ComplianceResult
  origin_result: OriginResult
}

// ---- 关税计算 ----

export interface TariffRequest {
  hs_code?: string
  name: string
  description: string
  material: string
  function: string
  target_country: string
  declared_value: number
}

export interface TariffCalcResponse {
  hs_code: string
  confidence: number
  hs_description: string
  product_name: string
  tariff: TariffResult
}
