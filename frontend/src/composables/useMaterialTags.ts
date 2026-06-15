import { ref, watch, type Ref } from 'vue'

export function useMaterialTags(material: Ref<string>, onEdit?: () => void) {
  const tags = ref<string[]>([])
  const input = ref('')

  // 初始化：从外部 material 同步
  function syncFromMaterial() {
    tags.value = (material.value || '').split('/').filter(Boolean)
  }
  syncFromMaterial()
  watch(material, () => {
    if (material.value !== tags.value.join('/')) syncFromMaterial()
  })

  function add() {
    const v = input.value.trim()
    if (!v) return
    const parts = v.split(/[/+、,；\s]+/).filter(Boolean)
    for (const p of parts) {
      if (!tags.value.includes(p)) tags.value.push(p)
    }
    material.value = tags.value.join('/')
    input.value = ''
    onEdit?.()
  }

  function remove(idx: number) {
    tags.value.splice(idx, 1)
    material.value = tags.value.join('/')
    onEdit?.()
  }

  return { tags, input, add, remove }
}
