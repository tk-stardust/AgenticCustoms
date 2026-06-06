import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Commodity,
  HsCodeResult,
  TariffResult,
  ComplianceResult,
  OriginResult,
  DeclarationDoc,
  PipelineStep,
  StepError,
} from '@/types'
import { classifyCommodity } from '@/api/classify'
import { runFullPipeline, type PipelineRequest } from '@/api/pipeline'

export const usePipelineStore = defineStore('pipeline', () => {
  // ---- 状态 ----
  const requestId = ref<string | null>(null)
  const commodity = ref<Commodity | null>(null)
  const targetCountry = ref<string>('US')
  const hsResult = ref<HsCodeResult | null>(null)
  const tariffResult = ref<TariffResult | null>(null)
  const complianceResult = ref<ComplianceResult | null>(null)
  const originResult = ref<OriginResult | null>(null)
  const documents = ref<DeclarationDoc | null>(null)
  const currentStep = ref<PipelineStep>('input')
  const loading = ref(false)
  const errors = ref<StepError[]>([])

  // ---- 计算属性 ----
  const hasErrors = computed(() => errors.value.length > 0)
  const isComplete = computed(() => currentStep.value === 'done')

  // ---- 操作 ----
  async function runClassify(input: Commodity) {
    commodity.value = input
    currentStep.value = 'classifying'
    loading.value = true
    errors.value = []
    try {
      hsResult.value = await classifyCommodity(input)
      currentStep.value = 'done'
    } catch (e: unknown) {
      errors.value.push({ step: 'classify', message: (e as Error).message })
    } finally {
      loading.value = false
    }
  }

  async function runPipeline(input: PipelineRequest) {
    commodity.value = input.commodity
    targetCountry.value = input.target_country
    currentStep.value = 'classifying'
    loading.value = true
    errors.value = []
    try {
      const result = await runFullPipeline(input)
      documents.value = result
      currentStep.value = 'done'
    } catch (e: unknown) {
      errors.value.push({ step: 'pipeline', message: (e as Error).message })
    } finally {
      loading.value = false
    }
  }

  function reset() {
    requestId.value = null
    commodity.value = null
    hsResult.value = null
    tariffResult.value = null
    complianceResult.value = null
    originResult.value = null
    documents.value = null
    currentStep.value = 'input'
    loading.value = false
    errors.value = []
  }

  return {
    requestId,
    commodity,
    targetCountry,
    hsResult,
    tariffResult,
    complianceResult,
    originResult,
    documents,
    currentStep,
    loading,
    errors,
    hasErrors,
    isComplete,
    runClassify,
    runPipeline,
    reset,
  }
})
