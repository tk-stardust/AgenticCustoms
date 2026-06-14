<script setup lang="ts">
import { ref, onMounted, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkCompliance } from '@/api/compliance'
import { COUNTRY_NAMES } from '@/constants'
import type { ComplianceResponse } from '@/api/compliance'

const route = useRoute()
const form = ref({ name: '', description: '', material: '', function: '', targetCountry: '', hsCode: '' })
onMounted(() => {
  // 从聊天助手跳转：读取结构化参数预填表单
  const q = route.query.q as string
  if (q) form.value.name = q
  if (route.query.name) form.value.name = route.query.name as string
  if (route.query.description) form.value.description = route.query.description as string
  if (route.query.material) { form.value.material = route.query.material as string; materialTags.value = (route.query.material as string).split('/').filter(Boolean) }
  if (route.query.function) form.value.function = route.query.function as string
  if (route.query.country) form.value.targetCountry = route.query.country as string
  if (route.query.hs_code) form.value.hsCode = route.query.hs_code as string
  // 参数齐全 + auto 标志 → 自动开始校验
  if (route.query.auto === '1' && form.value.name.trim() && form.value.targetCountry) {
    setTimeout(() => onSubmit(), 300)
  }
})
onActivated(() => {
  if (route.query.auto === '1' && form.value.name.trim() && form.value.targetCountry) {
    setTimeout(() => onSubmit(), 300)
  }
})
const loading = ref(false)
const result = ref<ComplianceResponse | null>(null)
const materialTags = ref<string[]>([])
const materialInput = ref('')
function addMaterialTag() {
  const v = materialInput.value.trim()
  if (!v) return
  const parts = v.split(/[/+、,；\s]+/).filter(Boolean)
  for (const p of parts) {
    if (!materialTags.value.includes(p)) materialTags.value.push(p)
  }
  form.value.material = materialTags.value.join('/')
  materialInput.value = ''
}
function removeTag(idx: number) {
  materialTags.value.splice(idx, 1)
  form.value.material = materialTags.value.join('/')
}

const riskColor: Record<string, string> = { green: '#16a34a', yellow: '#ca8a04', red: '#dc2626' }
const riskLabel: Record<string, string> = { green: '🟢 低风险', yellow: '🟡 中风险', red: '🔴 高风险' }
const severityLabel: Record<string, string> = { green: '低', yellow: '中', red: '高' }

async function onSubmit() {
  if (!form.value.name.trim()) { ElMessage.warning('请输入商品名称'); return }
  if (!form.value.targetCountry) { ElMessage.warning('请选择目标国家'); return }
  loading.value = true
  try {
    result.value = await checkCompliance({
      name: form.value.name,
      description: form.value.description,
      material: form.value.material,
      function: form.value.function,
      target_country: form.value.targetCountry,
      hs_code: form.value.hsCode || undefined,
    })
  } catch (e: any) { ElMessage.error(e?.message || '校验失败') }
  finally { loading.value = false }
}

function reset() {
  form.value = { name: '', description: '', material: '', function: '', targetCountry: '', hsCode: '' }
  result.value = null
  materialTags.value = []
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>合规校验</h1>
      <p class="page-subtitle">检查商品出口合规风险，识别禁限品、许可证、制裁清单</p>
    </div>

    <div class="layout">
      <!-- 左侧表单 -->
      <div class="panel panel-form">
        <div class="panel-header">商品信息</div>
        <el-form label-position="top">
          <el-form-item label="商品名称" required>
            <el-input v-model="form.name" placeholder="例如：蓝牙智能音箱" maxlength="100" />
          </el-form-item>
          <el-form-item label="商品描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述外观、材质、功能等" maxlength="500" />
          </el-form-item>
          <el-form-item label="材质">
            <div class="tag-input-wrap" @click="materialInput && addMaterialTag()">
              <span v-for="(t, i) in materialTags" :key="i" class="mat-tag">
                {{ t }} <span class="mat-close" @click.stop="removeTag(i)">×</span>
              </span>
              <input v-model="materialInput" class="mat-input" placeholder="输入后回车添加，支持粘贴拆分"
                @keydown.enter.prevent="addMaterialTag()" @blur="addMaterialTag" />
            </div>
          </el-form-item>
          <el-form-item label="功能">
            <el-input v-model="form.function" placeholder="音乐播放" maxlength="50" />
          </el-form-item>
          <el-form-item label="HS 编码（可选）">
            <el-input v-model="form.hsCode" placeholder="已知编码可直接填写" maxlength="12" />
          </el-form-item>
          <el-form-item label="目标国家" required>
            <el-select v-model="form.targetCountry" placeholder="请选择">
              <el-option v-for="(n, c) in COUNTRY_NAMES" :key="c" :value="c" :label="`${n} (${c})`" />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="btn-row">
          <button class="btn-primary" :disabled="loading" @click="onSubmit">
            {{ loading ? '校验中...' : '开始校验' }}
          </button>
          <button class="btn-ghost" @click="reset">清空</button>
        </div>
      </div>

      <!-- 右侧 -->
      <div class="panel panel-result">
        <!-- 空状态 -->
        <div v-if="!result && !loading" class="empty-content">
          <div class="empty-icon">🛡️</div>
          <h3>输入商品信息开始校验</h3>
          <p>系统将检查禁限品、许可证要求、制裁清单等合规风险</p>
        </div>

        <!-- 加载 -->
        <div v-if="loading" class="loading-content">
          <div class="spinner"></div>
          <p>正在分析合规风险...</p>
        </div>

        <!-- 结果 -->
        <div v-if="result && !loading" class="result-content">
          <div class="risk-badge" :style="{ background: riskColor[result.risk_level] }">
            {{ riskLabel[result.risk_level] }}
          </div>
          <div class="result-hs" v-if="result.hs_code">HS 编码：{{ result.hs_code }}</div>

          <!-- 违规项 -->
          <div class="section">
            <div class="section-title">违规项检查</div>
            <div v-if="result.violations.length === 0" class="check-item pass">✅ 未发现违规项</div>
            <div v-for="(v, i) in result.violations" :key="i" class="check-item fail">
              <div class="check-header">
                <span class="check-cat">{{ v.category }}</span>
                <el-tag :type="v.severity==='red'?'danger':v.severity==='yellow'?'warning':'success'" size="small">{{ severityLabel[v.severity] || v.severity }}</el-tag>
              </div>
              <div class="check-desc">{{ v.description }}</div>
              <div class="check-source" v-if="v.source">来源：{{ v.source }}</div>
            </div>
          </div>

          <!-- 许可证 -->
          <div class="section">
            <div class="section-title">许可证要求</div>
            <div :class="['check-item', result.license_required ? 'fail' : 'pass']">
              {{ result.license_required ? `⚠️ 需要许可证：${result.license_type || '待确认'}` : '✅ 无需特殊许可证' }}
            </div>
          </div>

          <!-- 制裁 -->
          <div class="section">
            <div class="section-title">制裁命中</div>
            <div :class="['check-item', result.sanctions_hit ? 'fail' : 'pass']">
              {{ result.sanctions_hit ? '⚠️ 命中制裁清单' : '✅ 未命中制裁清单' }}
            </div>
          </div>

          <!-- 结论 -->
          <div class="section" v-if="result.summary">
            <div class="section-title">合规结论</div>
            <div class="summary-text">{{ result.summary }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 24px 32px 32px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-gray-800); margin: 0 0 6px; }
.page-subtitle { font-size: 14px; color: var(--color-gray-500); margin: 0; }

.layout { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

.panel { background: #fff; border: 1px solid var(--color-gray-200); border-radius: 16px; padding: 24px; }
.panel-header { font-size: 16px; font-weight: 600; color: var(--color-gray-800); margin-bottom: 20px; }
.tag-input-wrap {
  display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
  padding: 4px 8px; border: 1px solid #e2e8f0; border-radius: 10px;
  min-height: 44px; max-height: 120px; overflow-y: auto; width: 100%; cursor: text; background: #fff;
}
.tag-input-wrap:focus-within { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.08); }
.mat-tag {
  padding: 2px 8px; border-radius: 999px; font-size: 12px;
  background: rgba(13,148,136,.08); color: #0d9488;
  display: inline-flex; align-items: center; gap: 2px;
}
.mat-close { cursor: pointer; font-weight: 700; color: #5eead4; }
.mat-input { border: none; outline: none; flex: 1; min-width: 60px; font-size: 13px; background: transparent; }
.btn-row { display: flex; gap: 12px; margin-top: 8px; }
.btn-primary {
  background: var(--color-brand-600); color: #fff; border: none;
  padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 500;
  cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) { background: var(--color-brand-700); }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-ghost {
  background: #fff; color: var(--color-gray-700); border: 1px solid var(--color-gray-300);
  padding: 10px 24px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.btn-ghost:hover { background: var(--color-gray-50); }

/* Empty / Loading */
.empty-content, .loading-content { text-align: center; padding: 80px 20px; color: var(--color-gray-400); }
.empty-icon { font-size: 48px; margin-bottom: 16px; opacity: .5; }
.empty-content h3 { font-size: 16px; font-weight: 600; color: var(--color-gray-500); margin: 0 0 6px; }
.empty-content p { font-size: 14px; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--color-gray-200); border-top-color: var(--color-brand-600); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-content p { font-size: 14px; color: var(--color-gray-500); }

/* Result */
.result-content { padding: 4px 0; }
.risk-badge { color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 18px; font-weight: 700; text-align: center; margin-bottom: 12px; }
.result-hs { font-size: 13px; color: var(--color-gray-500); text-align: center; margin-bottom: 20px; font-family: monospace; }
.section { margin-bottom: 20px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--color-gray-800); margin-bottom: 10px; }
.check-item { padding: 12px 14px; border-radius: 8px; font-size: 14px; line-height: 1.5; }
.check-item.pass { background: #f0fdf4; color: #166534; }
.check-item.fail { background: #fef2f2; border: 1px solid #fecaca; margin-bottom: 8px; }
.check-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.check-cat { font-weight: 600; color: var(--color-gray-800); }
.check-desc { color: var(--color-gray-600); }
.check-source { font-size: 12px; color: var(--color-gray-400); margin-top: 4px; }
.summary-text { font-size: 14px; color: var(--color-gray-600); line-height: 1.7; background: var(--color-gray-50); padding: 12px; border-radius: 8px; }
</style>
