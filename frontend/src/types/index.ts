// ---- 枚举 ----
export type RiskLevel = 'red' | 'yellow' | 'green'

export type TradeRoute = 'cn_us' | 'cn_eu' | 'cn_asean'

export type IntentType =
  | 'hs_classify'
  | 'tariff_calc'
  | 'compliance_check'
  | 'origin_match'
  | 'full_pipeline'

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

export interface DeclarationDoc {
  customs_declaration: Record<string, unknown>
  origin_certificate?: Record<string, unknown>
  compliance_statement: string
  cross_check_passed: boolean
  cross_check_errors: string[]
}

// ---- 流水线 ----

export interface StepError {
  step: string
  message: string
}

// ---- API ----

export interface ApiResponse<T> {
  data: T
  message?: string
  request_id?: string
}
