<script setup lang="ts">
import { ref, computed, onMounted, onDeactivated, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { queryTariff } from '@/api/tariff'
import { COUNTRY_NAMES } from '@/constants'
import { usePipelineStore } from '@/stores/pipeline'
import { useMaterialTags } from '@/composables/useMaterialTags'
import type { TariffCalcResponse } from '@/types'

const route = useRoute()
const router = useRouter()
const pipelineStore = usePipelineStore()
const mode = ref<'auto' | 'direct'>('auto')
const form = ref({
  name: '', description: '', material: '', function: '',
  hsCode: '', targetCountry: '', declaredValue: '',
})
onMounted(() => {
  // 从聊天助手跳转：读取结构化参数预填表单
  const q = route.query.q as string
  if (q) {
    if (/^\d{4,6}(\.\d{2,4})?$/.test(q)) {
      mode.value = 'direct'
      form.value.hsCode = q
    } else {
      form.value.name = q
    }
  }
  if (route.query.name) form.value.name = route.query.name as string
  if (route.query.description) form.value.description = route.query.description as string
  if (route.query.material) { form.value.material = route.query.material as string; materialTags.value = (route.query.material as string).split('/').filter(Boolean) }
  if (route.query.function) form.value.function = route.query.function as string
  if (route.query.country) form.value.targetCountry = route.query.country as string
  if (route.query.hs_code) { mode.value = 'direct'; form.value.hsCode = route.query.hs_code as string }
  if (route.query.declared_value) form.value.declaredValue = route.query.declared_value as string
  // 参数齐全 + auto 标志 → 自动开始计算
  if (route.query.auto === '1' && (form.value.name.trim() || form.value.hsCode.trim()) && form.value.targetCountry) {
    setTimeout(() => calculate(), 300)
  }
})
onDeactivated(() => {
  if (stepTimer) { clearInterval(stepTimer); stepTimer = null }
})
onActivated(() => {
  if (route.query.auto === '1' && (form.value.name.trim() || form.value.hsCode.trim()) && form.value.targetCountry) {
    setTimeout(() => calculate(), 300)
  }
})
const loading = ref(false)
const loadingStep = ref(0)
const result = ref<TariffCalcResponse | null>(null)
let stepTimer: ReturnType<typeof setInterval> | null = null
const materialRef = computed({
  get: () => form.value.material || '',
  set: (v) => { form.value.material = v }
})
const { tags: materialTags, input: materialInput, add: addMaterialTag, remove: removeTag } = useMaterialTags(materialRef)

const stepTotal = computed(() => mode.value === 'auto' ? 4 : 3)
const autoSteps = ['正在拆解商品特征...', '检索 WCO 注释与税则...', '匹配历史归类案例...', 'LLM 推理合成 + 税率查询中...']
const directSteps = ['校验 HS 编码有效性...', '查询目标国最新税则...', 'LLM 分析税费项目中...']

const canCalculate = computed(() => {
  if (loading.value) return false
  if (mode.value === 'auto') return form.value.name.trim() && form.value.targetCountry
  return form.value.hsCode.trim() && form.value.targetCountry
})

async function calculate() {
  if (!canCalculate.value) return
  loading.value = true
  loadingStep.value = 0
  stepTimer = setInterval(() => { if (loadingStep.value < stepTotal.value - 1) loadingStep.value++ }, 5000)

  try {
    const res = await queryTariff({
      hs_code: mode.value === 'direct' ? form.value.hsCode : undefined,
      name: form.value.name,
      description: form.value.description,
      material: form.value.material,
      function: form.value.function,
      target_country: form.value.targetCountry,
      declared_value: parseFloat(form.value.declaredValue) || 0,
    })
    result.value = res
    loadingStep.value = stepTotal.value - 1
  } catch (e: any) {
    ElMessage.error(e?.message || '计算失败')
  } finally {
    if (stepTimer) { clearInterval(stepTimer); stepTimer = null }
    setTimeout(() => { loading.value = false; loadingStep.value = 0 }, 500)
  }
}

function reset() {
  form.value = { name: '', description: '', material: '', function: '', hsCode: '', targetCountry: '', declaredValue: '' }
  result.value = null
  materialTags.value = []
}

const tariffItems = computed(() => result.value?.tariff?.items || [])

function goPipeline() {
  if (result.value) {
    pipelineStore.commodity = {
      name: form.value.name || result.value.product_name || '',
      description: form.value.description || '',
      material: form.value.material || '',
      function: form.value.function || '',
      usage: '',
      quantity: 1,
      declared_value: parseFloat(form.value.declaredValue) || 0,
    }
    pipelineStore.targetCountry = form.value.targetCountry
  }
  router.push('/pipeline')
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>关税计算</h1>
      <p class="page-subtitle">智能计算跨境贸易税费，支持自动归类与直接编码查询</p>
    </div>

    <!-- 模式切换 -->
    <div class="mode-switch">
      <button :class="['mode-btn', { active: mode === 'auto' }]" @click="mode = 'auto'">
        🤖 AI 自动归类
      </button>
      <button :class="['mode-btn', { active: mode === 'direct' }]" @click="mode = 'direct'">
        💰 直接输入编码
      </button>
    </div>

    <!-- 输入区域 -->
    <div class="input-section">
      <!-- 左侧表单 -->
      <div class="input-card">
        <div class="input-card-title">
          {{ mode === 'auto' ? '商品信息' : '编码信息' }}
        </div>

        <!-- 模式 A：AI 自动归类 -->
        <template v-if="mode === 'auto'">
          <el-form label-position="top">
            <el-form-item label="商品名称" required>
              <el-input v-model="form.name" placeholder="例如：蓝牙智能音箱" maxlength="100" />
            </el-form-item>
            <el-form-item label="商品描述">
              <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述外观、材质、功能、用途等，越详细归类越准确" maxlength="500" />
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
            <el-form-item label="目标国家 / 地区" required>
              <el-select v-model="form.targetCountry" placeholder="请选择">
                <el-option v-for="(name, code) in COUNTRY_NAMES" :key="code" :value="code" :label="`${name} (${code})`" />
              </el-select>
            </el-form-item>
            <el-form-item label="申报价值 (USD)">
              <el-input v-model="form.declaredValue" type="number" placeholder="1000" />
            </el-form-item>
          </el-form>
        </template>

        <!-- 模式 B：直接输入编码 -->
        <template v-else>
          <el-form label-position="top">
            <el-form-item label="HS 编码" required>
              <el-input v-model="form.hsCode" placeholder="例如：8518.22.00" maxlength="12" />
              <div class="form-hint">输入 6-10 位 HS 编码，系统将自动匹配税则</div>
            </el-form-item>
            <el-form-item label="商品名称（可选）">
              <el-input v-model="form.name" placeholder="蓝牙智能音箱" maxlength="100" />
            </el-form-item>
            <el-form-item label="目标国家" required>
              <el-select v-model="form.targetCountry" placeholder="请选择">
                <el-option v-for="(name, code) in COUNTRY_NAMES" :key="code" :value="code" :label="`${name} (${code})`" />
              </el-select>
            </el-form-item>
            <el-form-item label="申报价值 (USD)">
              <el-input v-model="form.declaredValue" type="number" placeholder="1000" />
            </el-form-item>
          </el-form>
        </template>

        <div class="btn-row">
          <button class="btn-primary" :disabled="!canCalculate" @click="calculate">
            <el-icon><Search /></el-icon> {{ mode === 'auto' ? '开始计算' : '直接计算' }}
          </button>
          <button class="btn-ghost" @click="reset">清空</button>
        </div>
      </div>

      <!-- 右侧状态面板 -->
      <div class="info-card">
        <!-- 加载中：步骤进度动画 -->
        <template v-if="loading">
          <div class="info-card-title">处理中...</div>
          <div class="progress-steps">
            <div v-for="(label, i) in (mode==='auto'?autoSteps:directSteps)" :key="i"
              class="progress-step" :class="{ done: i < loadingStep, current: i === loadingStep }">
              <span class="progress-dot">
                <span v-if="i < loadingStep">&#10003;</span>
                <span v-else-if="i === loadingStep" class="pulse"></span>
                <span v-else>{{ i + 1 }}</span>
              </span>
              <span class="progress-label">{{ label }}</span>
            </div>
          </div>
        </template>
        <!-- 空闲：步骤说明 -->
        <template v-else>
          <div class="info-card-title">计算说明</div>
          <div class="info-steps">
            <div v-for="(s,i) in (mode==='auto'
              ?[['1','特征拆解','提取材质、功能、用途等属性'],['2','RAG 检索','匹配 WCO 税则与历史案例'],['3','编码推理','输出 HS 编码与置信度'],['4','税费计算','查询税率，计算总税费']]
              :[['1','编码校验','验证 HS 编码有效性'],['2','税率查询','匹配目标国最新税则'],['3','税费计算','基础关税 + 增值税 + 优惠税率']])"
              :key="i" class="info-step">
              <div class="info-step-num">{{ s[0] }}</div>
              <div class="info-step-text"><strong>{{ s[1] }}</strong><br>{{ s[2] }}</div>
            </div>
          </div>
          <div class="info-time">{{ mode==='auto'?'预计处理时间 ~15-20 秒':'预计处理时间 ~3-5 秒' }}</div>
        </template>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="result && !loading" class="result-section">
      <div class="result-card">
        <div class="result-header">
          <div class="result-header-left">
            <span class="hs-badge">{{ result.hs_code }}</span>
            <span v-if="result.confidence" class="hs-confidence">置信度 {{ (result.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div class="result-header-right">
            <div class="result-product-name">{{ result.product_name }}</div>
            <div v-if="result.hs_description" class="result-product-desc">{{ result.hs_description }}</div>
          </div>
        </div>

        <div class="result-body">
          <div class="result-body-title">{{ COUNTRY_NAMES[result.tariff.country] || result.tariff.country }} 进口税率明细</div>

          <el-table :data="tariffItems" stripe style="width:100%">
            <el-table-column prop="name" label="税费项目" />
            <el-table-column prop="rate" label="税率" width="120">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column prop="amount" label="金额 (USD)" width="140">
              <template #default="{ row }">
                <span v-if="row.amount != null" class="tax-amount">${{ row.amount.toFixed(2) }}</span>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="备注" min-width="160">
              <template #default="{ row }">
                <span v-if="row.note" class="text-sm">{{ row.note }}</span>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="result.tariff.data_missing" class="data-warning">
            ⚠️ 部分税率数据缺失，结果仅供参考，请人工核实
          </div>

          <div class="suggestion-box">
            <div class="suggestion-title">💡 优化建议</div>
            <div class="suggestion-text">
              <p v-if="result.tariff.fta_applied">✓ 可适用 {{ result.tariff.fta_applied }} 优惠税率，预计节省 ${{ result.tariff.fta_saving?.toFixed(2) || '0.00' }}</p>
              <p v-else>• 当前未命中 FTA 优惠，建议核查原产地规则是否符合 RCEP 等协定条件</p>
              <p v-if="result.tariff.total_rate === 0 && !result.tariff.data_missing">• 该编码在目标国为免税商品</p>
              <p>• 申报价值为估算，实际税费以海关审定价为准</p>
            </div>
          </div>
        </div>

        <div class="result-footer">
          <div class="total-tax">
            <span class="total-tax-label">预估总税费：</span>
            <span class="total-tax-value">${{ result.tariff.total_amount?.toFixed(2) || '0.00' }}</span>
            <span class="total-tax-note">（综合税率 {{ result.tariff.total_rate }}%）</span>
          </div>
          <button class="btn-text" @click="goPipeline">跳转全流程生成申报文件 →</button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!result && !loading" class="empty-state">
      <div class="empty-icon">💰</div>
      <div class="empty-title">输入商品信息开始计算</div>
      <div class="empty-desc">选择计算模式，填写表单后点击计算按钮</div>
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 24px 32px 32px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-gray-800); margin: 0 0 6px; }
.page-subtitle { font-size: 14px; color: var(--color-gray-500); margin: 0; }

/* 模式切换 */
.mode-switch { display: flex; gap: 8px; margin-bottom: 20px; padding: 4px; background: var(--color-gray-100); border-radius: 10px; width: fit-content; }
.mode-btn { padding: 8px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; background: transparent; color: var(--color-gray-500); transition: all 0.2s ease; }
.mode-btn.active { background: #fff; color: var(--color-brand-600); box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.mode-btn:hover:not(.active) { color: var(--color-gray-800); }

/* 输入区 */
.input-section { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
@media (max-width: 900px) { .input-section { grid-template-columns: 1fr; } }

.input-card, .info-card {
  background: #fff; border-radius: 16px; padding: 24px;
  border: 1px solid var(--color-gray-200);
}
.input-card-title, .info-card-title {
  font-size: 16px; font-weight: 600; color: var(--color-gray-800); margin-bottom: 20px;
}
.info-card { background: var(--color-gray-50); }

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
.form-hint { font-size: 12px; color: var(--color-gray-400); margin-top: 4px; }

.btn-row { display: flex; gap: 12px; margin-top: 8px; }
.btn-primary {
  background: var(--color-brand-600); color: #fff; border: none;
  padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 500;
  cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
  transition: all 0.2s ease;
}
.btn-primary:hover { background: var(--color-brand-700); }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-ghost {
  background: #fff; color: var(--color-gray-700); border: 1px solid var(--color-gray-300);
  padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer;
  transition: all 0.2s ease;
}
.btn-ghost:hover { background: var(--color-gray-50); }
.btn-text {
  background: none; border: none; color: var(--color-brand-600); font-size: 13px;
  font-weight: 500; cursor: pointer; padding: 0;
}
.btn-text:hover { text-decoration: underline; }

/* 信息面板 */
.info-steps { margin-bottom: 16px; }
.info-step { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
.info-step-num {
  width: 22px; height: 22px; min-width: 22px; border-radius: 50%;
  background: var(--color-gray-200); color: var(--color-gray-500);
  font-size: 12px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.info-step-text { font-size: 13px; color: var(--color-gray-600); line-height: 1.5; }
.info-step-text strong { color: var(--color-gray-800); }
.info-time { text-align: center; font-size: 12px; color: var(--color-gray-400); padding-top: 12px; border-top: 1px solid var(--color-gray-200); margin-bottom: 12px; }
.info-scene { font-size: 13px; color: var(--color-gray-500); line-height: 1.7; }
.info-scene strong { color: var(--color-gray-800); }

/* 加载进度 */
.progress-steps { display: flex; flex-direction: column; gap: 10px; }
.progress-step { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--color-gray-400); transition: color 0.3s; }
.progress-step.done { color: var(--color-gray-600); }
.progress-step.current { color: var(--color-brand-600); font-weight: 500; }
.progress-dot {
  width: 22px; height: 22px; min-width: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
  background: var(--color-gray-200); color: var(--color-gray-500);
  transition: all 0.3s;
}
.progress-step.done .progress-dot { background: #d1fae5; color: #065f46; }
.progress-step.current .progress-dot { background: var(--color-brand-100); color: var(--color-brand-600); box-shadow: 0 0 0 3px rgba(13,148,136,.15); }
.pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--color-brand-600); animation: pulse 1.4s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* 结果 */
.result-section { margin-top: 0; }
.result-card { background: #fff; border-radius: 16px; border: 1px solid var(--color-gray-200); overflow: hidden; }
.result-header {
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
  padding: 20px 24px; border-bottom: 1px solid #d1fae5;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
}
.result-header-left { display: flex; align-items: center; gap: 16px; }
.hs-badge {
  background: var(--color-brand-600); color: #fff;
  padding: 8px 16px; border-radius: 8px;
  font-size: 20px; font-weight: 700;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  letter-spacing: 1px;
}
.hs-confidence { font-size: 13px; color: var(--color-brand-700); font-weight: 500; }
.result-header-right { text-align: right; }
.result-product-name { font-size: 16px; font-weight: 600; color: var(--color-gray-800); }
.result-product-desc { font-size: 13px; color: var(--color-gray-500); margin-top: 2px; }
.result-body { padding: 24px; }
.result-body-title { font-size: 14px; font-weight: 600; color: var(--color-gray-800); margin-bottom: 16px; }

.tax-amount { font-weight: 600; color: var(--color-danger); }
.text-muted { color: var(--color-gray-400); }
.text-sm { font-size: 13px; color: var(--color-gray-600); }

.data-warning {
  margin-top: 16px; padding: 12px 16px; background: #fefce8; border: 1px solid #fde68a;
  border-radius: 8px; font-size: 13px; color: #92400e;
}

.suggestion-box {
  margin-top: 16px; padding: 16px; background: #fffbeb; border-radius: 8px;
  border: 1px solid #fde68a;
}
.suggestion-title { font-size: 13px; font-weight: 600; color: #92400e; margin-bottom: 8px; }
.suggestion-text { font-size: 13px; color: #78350f; line-height: 1.7; }
.suggestion-text p { margin: 4px 0; }

.result-footer {
  background: var(--color-gray-50); padding: 16px 24px;
  border-top: 1px solid var(--color-gray-200);
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
}
.total-tax { display: flex; align-items: baseline; gap: 8px; }
.total-tax-label { font-size: 14px; color: var(--color-gray-500); }
.total-tax-value { font-size: 24px; font-weight: 700; color: var(--color-danger); }
.total-tax-note { font-size: 12px; color: var(--color-gray-400); }

/* 空状态 */
.empty-state { text-align: center; padding: 60px 20px; color: var(--color-gray-400); }
.empty-icon { font-size: 48px; margin-bottom: 16px; opacity: .5; }
.empty-title { font-size: 16px; font-weight: 500; color: var(--color-gray-500); margin-bottom: 6px; }
.empty-desc { font-size: 14px; }
</style>
