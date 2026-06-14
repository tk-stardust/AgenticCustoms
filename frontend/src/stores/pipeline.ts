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
  PipelineFullResponse,
} from '@/types'
import { classifyCommodity } from '@/api/classify'
import { runFullPipeline } from '@/api/pipeline'

export const usePipelineStore = defineStore('pipeline', () => {
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
  const classifyLoading = ref(false)
  const errors = ref<StepError[]>([])
  const autoRun = ref(false)

  const hasErrors = computed(() => errors.value.length > 0)
  const isComplete = computed(() => currentStep.value === 'done')

  async function runClassify(input: Commodity) {
    commodity.value = input
    currentStep.value = 'classifying'
    classifyLoading.value = true
    errors.value = []
    try {
      hsResult.value = await classifyCommodity(input)
      currentStep.value = 'done'
    } catch (e: unknown) {
      errors.value.push({ step: 'classify', message: (e as Error).message })
    } finally {
      classifyLoading.value = false
    }
  }

  async function runPipeline(commodityInput: Commodity, country: string, signal?: AbortSignal) {
    commodity.value = commodityInput
    targetCountry.value = country
    currentStep.value = 'classifying'
    loading.value = true
    errors.value = []
    try {
      const res: PipelineFullResponse = await runFullPipeline(commodityInput, country, signal)
      requestId.value = res.request_id
      documents.value = res.documents
      hsResult.value = res.hs_result
      tariffResult.value = res.tariff_result
      complianceResult.value = res.compliance_result
      originResult.value = res.origin_result
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
    classifyLoading,
    errors,
    hasErrors,
    isComplete,
    runClassify,
    runPipeline,
    reset,
    autoRun,
  }
})
