import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ocrImage } from '@/api/ocr'
import type { Commodity } from '@/types'

export function useOcr() {
  const loading = ref(false)
  const result = ref<Commodity | null>(null)
  const lastFileKey = ref('')
  const formEdited = ref(false)

  function markEdited() { formEdited.value = true }

  async function upload(e: Event, form: Commodity, onSuccess?: (result: Commodity) => void) {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    const thisKey = `${file.name}|${file.size}|${file.lastModified}`
    if (thisKey === lastFileKey.value && !formEdited.value) {
      (e.target as HTMLInputElement).value = ''
      return
    }
    loading.value = true
    try {
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve((reader.result as string).split(',')[1])
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
      const res = await ocrImage(base64, file.type)
      form.name = res.name || form.name
      form.description = res.description || form.description
      form.material = res.material || form.material
      form.function = res.function || form.function
      form.usage = res.usage || form.usage
      result.value = { ...res }
      lastFileKey.value = thisKey
      formEdited.value = false
      onSuccess?.(res)
    } catch {
      ElMessage.warning('图片识别失败，请重试或手动输入')
    } finally {
      loading.value = false
      ;(e.target as HTMLInputElement).value = ''
    }
  }

  function clearResult() { result.value = null }

  return { loading, result, lastFileKey, formEdited, markEdited, upload, clearResult }
}
