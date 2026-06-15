<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onDeactivated } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'
import type { Commodity } from '@/types'
import { Check, Loading, Camera, QuestionFilled, MagicStick } from '@element-plus/icons-vue'
import { runPipelineSSE } from '@/api/pipeline'
import { COUNTRY_NAMES } from '@/constants'
import { useMaterialTags } from '@/composables/useMaterialTags'
import { useOcr } from '@/composables/useOcr'
import PipelineAgentCard from '@/components/PipelineAgentCard.vue'
import PipelineCustomsPreview from '@/components/PipelineCustomsPreview.vue'
import PipelineOriginPreview from '@/components/PipelineOriginPreview.vue'
import PipelineCompliancePreview from '@/components/PipelineCompliancePreview.vue'

const store = usePipelineStore()
let abortCtrl: AbortController | null = null
const route = useRoute()
const emptyPipeline = (): Commodity => ({ name: '', description: '', material: '', function: '', usage: '' })
const form = ref<Commodity>(emptyPipeline())
const country = ref(store.targetCountry)

// 切页离开（keep-alive 缓存）：停动画。表单由 keep-alive 保留在内存，不写 localStorage
onDeactivated(() => {
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null }
})
// 首次挂载：从聊天助手或 Classify 跳转时自动运行
onMounted(() => {
  // 有预填数据时填入表单（来自 TariffView 等页面跳转）
  if (store.commodity?.name) {
    form.value = { name: store.commodity.name, description: store.commodity.description || '', material: store.commodity.material || '', function: store.commodity.function || '', usage: store.commodity.usage || '', quantity: store.commodity.quantity || 1, declared_value: store.commodity.declared_value || 0 }
    materialTags.value = (store.commodity.material || '').split('/').filter(Boolean)
    country.value = store.targetCountry
  }
  // 从聊天助手跳转：读取结构化参数预填表单（覆盖上述默认值）
  const q = route.query.q as string
  if (q) form.value.name = q
  if (route.query.name) form.value.name = route.query.name as string
  if (route.query.description) form.value.description = route.query.description as string
  if (route.query.material) { form.value.material = route.query.material as string; materialTags.value = (route.query.material as string).split('/').filter(Boolean) }
  if (route.query.function) form.value.function = route.query.function as string
  if (route.query.usage) form.value.usage = route.query.usage as string
  if (route.query.country) country.value = route.query.country as string
  // 需要自动执行（历史记录重跑 或 聊天助手 auto 跳转）
  if (store.autoRun || (route.query.auto === '1' && form.value.name.trim() && form.value.description.trim())) {
    store.autoRun = false
    setTimeout(() => onSubmit(), 500)
  }
})
// keep-alive 切回来：重跑 / 聊天跳转 / 同步结果
onActivated(() => {
  // 历史记录重跑
  if (store.autoRun) {
    if (store.commodity?.name) {
      form.value = { name: store.commodity.name, description: store.commodity.description || '', material: store.commodity.material || '', function: store.commodity.function || '', usage: store.commodity.usage || '', quantity: store.commodity.quantity || 1, declared_value: store.commodity.declared_value || 0 }
      materialTags.value = (store.commodity.material || '').split('/').filter(Boolean)
      country.value = store.targetCountry
      clearResult()
    }
    store.autoRun = false
    setTimeout(() => onSubmit(), 300)
    return
  }
  // 聊天助手 auto 跳转（keep-alive 后 onMounted 不触发，在此处理）
  if (route.query.auto === '1') {
    if (route.query.name) form.value.name = route.query.name as string
    if (route.query.description) form.value.description = route.query.description as string
    if (route.query.material) { form.value.material = route.query.material as string; materialTags.value = (route.query.material as string).split('/').filter(Boolean) }
    if (route.query.function) form.value.function = route.query.function as string
    if (route.query.usage) form.value.usage = route.query.usage as string
    if (route.query.country) country.value = route.query.country as string
    if (form.value.name.trim() && form.value.description.trim()) {
      clearResult()
      setTimeout(() => onSubmit(), 300)
    }
    return
  }
  // 如果 SSE 已完成，同步结果状态
  if (store.documents && phase.value !== 'done') {
    phase.value = 'done'
    activePhase.value = steps.length - 1
    agentPhase.value = agents.length - 1
  }
})
const phase = ref<'idle' | 'running' | 'done'>('idle')
const activePhase = ref(-1)
const agentPhase = ref(-1)
const agentColors = ['blue', 'yellow', 'green', 'purple', 'gray'] as const
const showPreview = ref(false)
const collapseActive = ref(['tax', 'compliance', 'cross'])
const previewType = ref<'customs' | 'origin' | 'compliance'>('customs')
function openPreview(type: 'customs' | 'origin' | 'compliance') {
  previewType.value = type
  showPreview.value = true
}

const steps = [
  { label: 'HS归类',   brief: '编码推理' },
  { label: '关税计算', brief: '税费试算' },
  { label: '合规校验', brief: '风险检查' },
  { label: '原产地',   brief: 'FTA匹配' },
  { label: '文件生成', brief: '申报草单' },
]

const agents = [
  { icon: '🔍', name: '编码推理 Agent', desc: 'RAG 检索 + LLM 推理 HS 编码', key: 'hs' },
  { icon: '💰', name: '关税计算 Agent', desc: '查税率表 + 综合税费试算',     key: 'tariff' },
  { icon: '🛡️', name: '合规校验 Agent', desc: '制裁匹配 + 禁令风险评估',     key: 'compliance' },
  { icon: '📍', name: '原产地 Agent',   desc: 'FTA 规则 + 最优策略推荐',     key: 'origin' },
  { icon: '📄', name: '文件生成 Agent', desc: '汇总结果 + 交叉校验',         key: 'doc' },
]

const logs = [
  '正在解析商品材质与功能特征...',
  '检索 WCO 注释与归类规则...',
  '匹配 OFAC/商务部制裁清单...',
  '比对 RCEP 原产地规则...',
  '生成报关单 + 交叉校验...',
]

const countryOptions = [
  { value: 'US', label: '🇺🇸 美国' },
  { value: 'EU', label: '🇪🇺 欧盟' },
  { value: 'VN', label: '🇻🇳 越南' },
]
function countryLabel(code: string) { return (COUNTRY_NAMES as Record<string,string>)[code] || code }

const materialRef = computed({
  get: () => form.value.material || '',
  set: (v) => { form.value.material = v }
})
const { loading: ocrLoading, result: ocrResult, upload: ocrUpload, markEdited: onFieldEdit } = useOcr()
const { tags: materialTags, input: materialInput, add: addMaterialTag, remove: removeTag } = useMaterialTags(materialRef, onFieldEdit)

async function onUpload(e: Event) {
  await ocrUpload(e, form.value, (res) => {
    if (res.material) {
      materialTags.value = res.material.split('/').filter(Boolean)
    }
  })
}

// 同票多商品项
interface CommodityRow { name: string; hs_code: string; quantity: number; declared_value: number }
const commodityRows = ref<CommodityRow[]>([])
function addRow() {
  commodityRows.value.push({ name: '', hs_code: '', quantity: 1, declared_value: 0 })
}
function removeRow(idx: number) {
  commodityRows.value.splice(idx, 1)
}

function clearForm() {
  form.value = emptyPipeline()
  materialTags.value = []
  commodityRows.value = []
  ocrResult.value = null
}
function clearResult() {
  phase.value = 'idle'
  activePhase.value = -1
  agentPhase.value = -1
  store.reset()
}

async function onSubmit() {
  if (!form.value.name.trim()) { ElMessage.warning('请输入商品名称'); return }
  if (!form.value.description.trim()) { ElMessage.warning('请输入商品描述'); return }
  phase.value = 'running'; activePhase.value = 0; agentPhase.value = -1
  abortCtrl = new AbortController()
  try {
    const res = await runPipelineSSE(
      { ...form.value },
      country.value,
      (event, data) => {
        if (event === 'progress' && typeof data.agent === 'number') {
          agentPhase.value = data.agent
          activePhase.value = data.agent
          if (data.message && typeof data.message === 'string') {
            logs[data.agent] = data.message
          }
        }
      },
      abortCtrl.signal,
    )
    store.requestId = res.request_id as string
    store.documents = res.documents as any
    store.hsResult = res.hs_result as any
    store.tariffResult = res.tariff_result as any
    store.complianceResult = res.compliance_result as any
    store.originResult = res.origin_result as any
    store.loading = false
    activePhase.value = steps.length - 1
    agentPhase.value = agents.length - 1
    phase.value = 'done'
  } catch (e: unknown) {
    if ((e as Error).name === 'AbortError') {
      phase.value = 'idle'
      ElMessage.info('已取消分析')
    } else {
      store.errors.push({ step: 'pipeline', message: (e as Error).message })
      phase.value = 'done'
    }
  }
  abortCtrl = null
}

function cancelPipeline() {
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null }
}

function agentState(i: number) {
  if (phase.value === 'idle') return 'idle'
  if (i < agentPhase.value) return 'done'
  if (i === agentPhase.value) return 'running'
  return 'pending'
}

function downloadZip() {
  const rid = store.documents?.request_id || store.requestId
  if (rid) window.open(`/api/pipeline/download/${rid}`, '_blank')
}
function downloadPdf() {
  const rid = store.documents?.request_id || store.requestId
  if (rid) window.open(`/api/pipeline/pdf/${rid}/${previewType.value}`, '_blank')
}
const showReport = computed(() => phase.value === 'done' && !!store.documents)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>一键全流程</h1>
      <p class="text-muted text-sm">5 大 AI Agent 协作，生成完整申报文件包</p>

      <!-- 5 步流程条 -->
      <div class="flow-steps">
        <div
          v-for="(s, i) in steps" :key="i"
          class="flow-step"
          :class="{ active: i <= activePhase, current: i === activePhase && phase === 'running' }"
        >
          <div class="flow-dot">
            <el-icon v-if="i < activePhase || (i === activePhase && phase === 'done')" :size="12"><Check /></el-icon>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="flow-text">
            <span class="flow-label">{{ s.label }}</span>
            <span class="flow-brief">{{ s.brief }}</span>
          </div>
          <div v-if="i < steps.length - 1" class="flow-line" :class="{ filled: i < activePhase }"></div>
        </div>
      </div>
    </div>

    <div class="layout">
      <!-- ============ 左侧表单 ============ -->
      <div class="panel panel-form">
        <div class="panel-top-bar"></div>
        <h3 class="panel-title">商品信息</h3>
        <el-form :model="form" label-position="top">
          <el-form-item label="商品名称" required>
            <div class="input-with-btn">
              <el-input v-model="form.name" placeholder="例：蓝牙智能音箱" size="large" class="custom-input" clearable maxlength="200" show-word-limit/>
              <label class="ocr-btn" :class="{loading:ocrLoading}" title="拍照识别">
                <el-icon :size="18" v-if="!ocrLoading"><Camera/></el-icon>
                <el-icon :size="18" class="is-loading" v-else><Loading/></el-icon>
                <input type="file" accept="image/*" hidden @change="onUpload"/>
              </label>
            </div>
          </el-form-item>
          <el-form-item label="商品描述" required>
            <el-input v-model="form.description" type="textarea" :rows="3"
              placeholder="外观、材质、工作原理、用途等" class="custom-input" clearable maxlength="2000" show-word-limit @input="onFieldEdit"/>
          </el-form-item>

          <!-- AI 提取横幅 -->
          <div v-if="ocrResult" class="ai-extract">
            <div class="ai-badge">
              <el-icon :size="14"><MagicStick/></el-icon><span>AI 自动识别</span>
              <button type="button" class="ai-edit-btn" @click="ocrResult=null">修改</button>
            </div>
            <div class="extract-tags">
              <span v-if="ocrResult.material" class="extract-tag">材质：<b>{{ ocrResult.material }}</b></span>
              <span v-if="ocrResult.function" class="extract-tag">功能：<b>{{ ocrResult.function }}</b></span>
              <span v-if="ocrResult.usage" class="extract-tag">用途：<b>{{ ocrResult.usage }}</b></span>
            </div>
          </div>

          <!-- 材质独占一行（OCR 后隐藏） -->
          <el-form-item v-if="!ocrResult" label="材质">
            <div class="tag-input-wrap" @click="materialInput && addMaterialTag()">
              <span v-for="(t, i) in materialTags" :key="i" class="mat-tag">
                {{ t }} <span class="mat-close" @click.stop="removeTag(i)">×</span>
              </span>
              <input v-model="materialInput" class="mat-input" placeholder="输入后回车添加"
                @keydown.enter.prevent="addMaterialTag()" @blur="addMaterialTag" />
            </div>
          </el-form-item>

          <el-row v-if="!ocrResult" :gutter="12">
            <el-col :span="12">
              <el-form-item label="功能"><el-input v-model="form.function" placeholder="音乐播放" class="custom-input" clearable maxlength="200"/></el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="用途"><el-input v-model="form.usage" placeholder="家庭娱乐" class="custom-input" clearable maxlength="200"/></el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="始发国">
                <el-input value="🇨🇳 中国" disabled size="large" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="目标国">
                <el-select v-model="country" class="country-select" size="large">
                  <el-option v-for="o in countryOptions" :key="o.value" :value="o.value" :label="o.label" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="货物数量（件）">
                <el-input-number v-model="form.quantity" :min="1" :max="999999" size="large" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="申报价值（元）">
                <el-input-number v-model="form.declared_value" :min="0" :max="999999999" :precision="2" size="large" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>


          <!-- 同票多商品项 -->
          <el-divider content-position="left">
            同票多商品申报
            <el-tooltip placement="top" effect="dark" raw-content>
              <template #content>同一张报关单可申报多个不同商品。<br/>例：一箱货含"蓝牙音箱"和"耳机"，<br/>HS编码不同需分列申报。</template>
              <el-icon :size="14" style="margin-left:6px;color:#94a3b8;cursor:help"><QuestionFilled /></el-icon>
            </el-tooltip>
          </el-divider>
          <div v-for="(row, idx) in commodityRows" :key="idx" class="commodity-row">
            <div class="commodity-row-header">
              <span class="row-label">商品 #{{ idx + 2 }}</span>
              <span class="row-desc">与主商品同票申报</span>
              <el-button size="small" type="danger" plain @click="removeRow(idx)">移除</el-button>
            </div>
            <el-row :gutter="8">
              <el-col :span="8"><el-input v-model="row.name" placeholder="商品名称" size="small" clearable/></el-col>
              <el-col :span="5"><el-input v-model="row.hs_code" placeholder="HS编码" size="small" clearable/></el-col>
              <el-col :span="5"><el-input-number v-model="row.quantity" :min="1" placeholder="数量" size="small" controls-position="right" style="width:100%"/></el-col>
              <el-col :span="6"><el-input-number v-model="row.declared_value" :min="0" :precision="2" placeholder="申报价值" size="small" controls-position="right" style="width:100%"/></el-col>
            </el-row>
          </div>
          <el-button size="small" @click="addRow()" style="margin-top:8px">+ 添加同票商品</el-button>

          <div class="form-actions">
            <button v-if="phase !== 'running'" type="button" class="btn-start" @click="onSubmit">
              ⚡ 开始全流程分析
            </button>
            <button v-else type="button" class="btn-start running" @click="cancelPipeline">
              <span class="agent-progress">
                <span class="mini-spinner"></span>
                Agent {{ Math.min(agentPhase + 1, 5) }}/5 运行中...  (点击取消)
              </span>
            </button>
            <button v-if="phase !== 'running'" type="button" class="btn-ghost" @click="clearForm()">清空表单</button>
          </div>
          <div v-if="phase === 'running'" class="progress-bar">
            <div class="progress-fill" :style="{ width: ((agentPhase + 1) / 5 * 100) + '%' }"></div>
          </div>
        </el-form>
      </div>

      <!-- ============ 右侧 ============ -->
      <div class="panel panel-result" :class="{ 'has-report': showReport }">

        <!-- 空状态：5 Agent 卡片 -->
        <div v-if="phase === 'idle'" class="agent-grid">
          <PipelineAgentCard v-for="(a,i) in agents" :key="i" :agent="a" :index="i" state="idle" :color="agentColors[i]" :style="{ animationDelay: `${i*0.08}s` }" />
        </div>

        <!-- 运行状态：5 Agent 卡片激活 -->
        <div v-if="phase === 'running'" class="agent-grid">
          <PipelineAgentCard v-for="(a,i) in agents" :key="i" :agent="a" :index="i" :state="agentState(i)" :color="agentColors[i]" :log="logs[i]" />
        </div>

        <!-- 完成状态：报告视图 -->
        <div v-if="phase==='done' && !store.documents && store.hasErrors" style="padding:24px;text-align:center">
          <p style="color:#ef4444;font-size:16px">⚠️ 分析出错</p>
          <p style="color:#64748b;font-size:13px;margin-top:8px">{{ store.errors[0]?.message }}</p>
        </div>
        <template v-if="showReport">
          <div class="report-header">
            <div class="report-done">✅ 全流程完成</div>
            <div class="agent-badges">
              <span v-for="(a, i) in agents" :key="i" class="agent-badge-done">✅ {{ a.name }}</span>
            </div>
          </div>

          <!-- HS 编码 -->
          <div class="report-section">
            <h4>HS 编码结果</h4>
            <div class="report-hs">
              <code>{{ store.documents?.customs_declaration?.hs_code || '—' }}</code>
              <el-tag size="small" type="success" effect="dark">{{ store.hsResult ? `置信度 ${(store.hsResult.confidence * 100).toFixed(0)}%` : '已确认' }}</el-tag>
            </div>
            <p class="hs-desc" v-if="store.hsResult?.description">{{ store.hsResult.description }}</p>
          </div>

          <!-- 税费明细 -->
          <div class="report-section">
            <el-collapse v-model="collapseActive" class="report-collapse">
              <el-collapse-item title="税费明细" name="tax">
                <el-alert v-if="store.tariffResult?.data_missing" type="warning" show-icon :closable="false" style="margin-bottom:10px">
                  <template #title>该 HS 编码暂无目标国税率数据，以下为占位项，请人工核实实际税率</template>
                </el-alert>
                <div class="tax-summary">
                  <span>商品：<b>{{ store.documents?.customs_declaration?.commodity_name || '—' }}</b></span>
                  <span>始发国：<b>{{ countryLabel((store.documents?.customs_declaration?.origin as string) || 'CN') }}</b> → 目标国：<b>{{ countryLabel(store.tariffResult?.country || '') }}</b></span>
                  <span v-if="store.tariffResult?.fta_applied">FTA：<b class="fta-badge">{{ store.tariffResult.fta_applied }}</b></span>
                </div>
                <table class="tax-table" v-if="store.tariffResult?.items?.length">
                  <thead>
                    <tr><th>税项</th><th class="num">税率</th><th class="num">金额（元）</th><th>备注</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in store.tariffResult.items" :key="item.name">
                      <td>{{ item.name }}</td>
                      <td class="num">{{ item.rate }}%</td>
                      <td class="num">{{ item.amount?.toFixed(2) || '—' }}</td>
                      <td class="note">{{ item.note || '—' }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colspan="2">法定税费合计</td>
                      <td class="num" colspan="2">
                        <template v-if="store.documents?.customs_declaration?.declared_value">
                          {{ ((store.documents.customs_declaration.declared_value as number) * (store.tariffResult?.total_rate || 0) / 100).toFixed(2) }} 元
                        </template>
                        <template v-else>{{ store.tariffResult?.total_rate || 0 }}%</template>
                      </td>
                    </tr>
                    <tr v-if="store.tariffResult?.fta_saving">
                      <td colspan="2">{{ store.tariffResult.fta_applied ? `FTA 优惠节省（${store.tariffResult.fta_applied}）` : 'FTA 优惠节省' }}</td>
                      <td class="num saving" colspan="2">-{{ ((store.documents?.customs_declaration?.declared_value as number) * (store.tariffResult.fta_saving || 0) / 100).toFixed(2) }} 元</td>
                    </tr>
                    <tr v-if="store.documents?.customs_declaration?.declared_value">
                      <td colspan="2">{{ store.tariffResult?.fta_saving ? '实缴税费' : '合计应缴税费' }}</td>
                      <td class="num total" colspan="2">
                        {{ ((store.documents.customs_declaration.declared_value as number) * ((store.tariffResult?.total_rate || 0) - (store.tariffResult?.fta_saving || 0)) / 100).toFixed(2) }} 元
                      </td>
                    </tr>
                  </tfoot>
                </table>
                <p v-if="store.tariffResult && !store.tariffResult.data_missing && store.tariffResult.total_rate === 0" class="tax-disclaimer" style="color:#0d9488">
                  ℹ️ 该商品当前综合税率为零，可能原因：ITA 免税协定 / FTA 优惠减免 / 目标国零关税政策。如有疑问请以海关最新公告为准。
                </p>
                <p class="tax-disclaimer">税率数据更新至 2026，仅供参考，具体以海关最新公告为准</p>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 风险与合规 -->
          <div class="report-section">
            <el-collapse v-model="collapseActive" class="report-collapse">
              <el-collapse-item name="compliance">
                <template #title>
                  <span>合规校验</span>
                  <span class="risk-badge" :class="store.complianceResult?.risk_level" style="margin-left:12px">
                    {{ store.complianceResult?.risk_level === 'red' ? '🔴 高风险' : store.complianceResult?.risk_level === 'yellow' ? '🟡 中风险' : '🟢 低风险' }}
                  </span>
                </template>
                <div v-if="store.complianceResult" class="checklist">
                  <div class="check-item" :class="{ fail: store.complianceResult.sanctions_hit }">
                    <span class="check-mark">{{ store.complianceResult.sanctions_hit ? '✗' : '✓' }}</span>
                    <div><strong>制裁清单校验</strong><p>OFAC / UN / 不可靠实体清单</p></div>
                  </div>
                  <div class="check-item" :class="{ fail: store.complianceResult.license_required }">
                    <span class="check-mark">{{ store.complianceResult.license_required ? '⚠' : '✓' }}</span>
                    <div><strong>出口许可校验</strong><p>{{ store.complianceResult.license_type || '无需特殊许可' }}</p></div>
                  </div>
                  <div v-for="v in store.complianceResult.violations" :key="v.category" class="check-item fail">
                    <span class="check-mark">{{ v.severity === 'red' ? '✗' : '⚠' }}</span>
                    <div><strong>{{ v.category }}</strong><p>{{ v.description }}</p><span class="check-source">{{ v.source }}</span></div>
                  </div>
                  <div v-if="!store.complianceResult.sanctions_hit && !store.complianceResult.violations.length" class="check-item all-clear">
                    <span class="check-mark">✓</span>
                    <div><strong>全部通过</strong><p>未命中制裁清单，无违规项</p></div>
                  </div>
                </div>
                <p class="compliance-summary">{{ store.documents?.compliance_statement }}</p>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 校验 -->
          <div class="report-section">
            <el-collapse v-model="collapseActive" class="report-collapse">
              <el-collapse-item title="交叉校验" name="cross">
                <div class="cross-check-list">
                  <div v-for="(item, i) in store.documents?.cross_check_items" :key="i" class="cross-check-item" :class="{ fail: !item.passed }">
                    <span class="check-mark">{{ item.passed ? '✓' : '✗' }}</span>
                    <div>
                      <strong>{{ item.name }}</strong>
                      <p>{{ item.detail }}</p>
                    </div>
                  </div>
                </div>
                <div v-if="store.documents?.cross_check_passed" class="cross-check all-pass" style="margin-top:8px">
                  <span class="check-mark">✓</span><span>全部校验通过</span>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <div class="preview-btns">
            <button type="button" class="btn-preview" @click="openPreview('customs')">📋 预览报关单</button>
            <button type="button" class="btn-preview" @click="openPreview('origin')">📜 预览原产地证</button>
            <button type="button" class="btn-preview" @click="openPreview('compliance')">🛡️ 预览合规声明</button>
          </div>
          <div class="report-actions">
            <button type="button" class="btn-ghost" @click="clearResult()">清除结果</button>
          </div>
        </template>
      </div>
    </div>

    <!-- 申报文件预览模态框 -->
    <el-dialog v-model="showPreview" :title="previewType === 'customs' ? '报关单草单' : previewType === 'origin' ? '原产地证书申请书' : '合规声明'" width="80vw" top="3vh" destroy-on-close class="preview-dialog">
      <PipelineCustomsPreview v-if="previewType === 'customs'" />
      <PipelineOriginPreview v-if="previewType === 'origin'" />
      <PipelineCompliancePreview v-if="previewType === 'compliance'" />

      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
        <el-button type="primary" @click="downloadPdf()">📄 下载 PDF</el-button>
        <el-button type="success" @click="downloadZip()">📥 下载打包</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ===== 布局 ===== */
.page-header { margin-bottom: var(--space-5); }
.page-header h1 { font-size: var(--font-size-2xl); font-weight: 700; color: #1e293b; letter-spacing: -0.02em; }
.layout { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-5); align-items: start; }

/* ===== 流程步骤条 ===== */
.flow-steps { display: flex; align-items: flex-start; margin-top: var(--space-4); position: relative; }
.flow-step { flex: 1; display: flex; align-items: center; position: relative; padding-right: 8px; }
.flow-dot {
  width: 28px; height: 28px; border-radius: 50%; background: #e2e8f0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #94a3b8; flex-shrink: 0;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.flow-step.active .flow-dot { background: #0d9488; color: #fff; }
.flow-step.current .flow-dot { animation: dotPulse 1.5s ease infinite; }
.flow-text { margin-left: 6px; display: flex; flex-direction: column; }
.flow-label { font-size: 12px; color: #94a3b8; font-weight: 500; }
.flow-brief { font-size: 10px; color: #cbd5e1; }
.flow-step.active .flow-label { color: #64748b; }
.flow-step.active .flow-brief { color: #94a3b8; }
.flow-line {
  position: absolute; left: 42px; top: 14px; width: calc(100% - 42px); height: 1px;
  background: #e2e8f0; z-index: -1;
}
.flow-line.filled { background: #0d9488; }

@keyframes dotPulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(13,148,136,.5); }
  50% { transform: scale(1.25); box-shadow: 0 0 0 10px rgba(13,148,136,.15); }
}

/* ===== 面板公用 ===== */
.panel {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,.04);
}
.panel-form { position: relative; padding: var(--space-6); }
.panel-result { min-height: 360px; padding: var(--space-6); }
.panel-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0d9488, #14b8a6); }
.panel-title { font-size: var(--font-size-lg); font-weight: 600; margin-bottom: var(--space-5); }

/* ===== 表单 ===== */
.input-with-btn { display: flex; gap: 8px; align-items: stretch; width: 100%; }
.input-with-btn .custom-input { flex: 1; width: 0; }
.ocr-btn { display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; cursor: pointer; color: #94a3b8; transition: all .2s; flex-shrink: 0; }
.ocr-btn:hover { border-color: #0d9488; color: #0d9488; }
.ocr-btn.loading { opacity: .6; pointer-events: none; }
.ai-extract { margin-top: 12px; padding: 12px; background: rgba(13,148,136,.03); border-radius: 10px; }
.ai-badge { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #0d9488; margin-bottom: 6px; }
.extract-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.extract-tag { padding: 3px 10px; border-radius: 999px; font-size: 12px; color: #475569; background: rgba(13,148,136,.08); }
.extract-tag b { color: #1e293b; }
.ai-edit-btn { margin-left: auto; padding: 1px 8px; border: 1px solid #0d9488; border-radius: 4px; background: none; color: #0d9488; font-size: 11px; cursor: pointer; }
.ai-edit-btn:hover { background: #0d9488; color: #fff; }
.commodity-row { padding: 10px 12px; margin-bottom: 8px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
.commodity-row-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.row-label { font-size: 12px; font-weight: 600; color: #475569; }
.row-desc { font-size: 11px; color: #94a3b8; }
.row-hint { font-size: 11px; color: #94a3b8; margin-top: 4px; }
:deep(.el-row) { align-items: flex-start; }
:deep(.custom-input .el-input__wrapper) {
  height: 44px; border-radius: 10px;
  border: 1px solid #e2e8f0; box-shadow: none; transition: all .2s;
}
:deep(.custom-input.is-focus .el-input__wrapper) {
  border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.08);
}
:deep(.country-select .el-select__wrapper) {
  min-height: 44px !important; border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important; box-shadow: none !important;
}
:deep(.country-select .el-select__wrapper:hover) {
  border-color: #e2e8f0 !important;
}

.tag-input-wrap {
  display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
  padding: 4px 8px; border: 1px solid #e2e8f0; border-radius: 10px;
  min-height: 44px; max-height: 120px; overflow-y: auto; width: 100%;
  cursor: text; background: #fff;
}
.tag-input-wrap:focus-within { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.08); }
.mat-tag {
  padding: 2px 8px; border-radius: 999px; font-size: 12px;
  background: rgba(13,148,136,.08); color: #0d9488;
  display: inline-flex; align-items: center; gap: 2px;
}
.mat-close { cursor: pointer; font-weight: 700; color: #5eead4; }
.mat-input { border: none; outline: none; flex: 1; min-width: 60px; font-size: 13px; background: transparent; }


.form-actions { display: flex; gap: 12px; margin-top: var(--space-3); }
.btn-start {
  flex: 1; padding: 14px 40px; font-size: 16px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #0d9488, #0f766e); border: none; border-radius: 12px;
  cursor: pointer; transition: all 0.3s ease;
  will-change: transform, box-shadow;
}
.btn-start:hover:not(:disabled) { box-shadow: 0 0 20px rgba(13,148,136,.3); transform: scale(1.02); }
.btn-start:disabled { opacity: .8; cursor: not-allowed; }
.btn-start.running { background: linear-gradient(135deg, #1e293b, #334155); }

.agent-progress { display: flex; align-items: center; justify-content: center; gap: 8px; }
.mini-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.progress-bar { height: 3px; border-radius: 2px; background: #e2e8f0; margin-top: 8px; overflow: hidden; }
.progress-fill { height: 100%; background: #0d9488; border-radius: 2px; transition: width 0.5s ease; }

/* ===== Agent 卡片 ===== */
.agent-grid { display: flex; flex-direction: column; gap: 12px; }

.agent-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; border-radius: 12px; background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  will-change: transform, opacity;
  opacity: 1; animation: fadeUp 0.35s cubic-bezier(0.4,0,0.2,1) both;
}
.agent-card:hover { transform: translateY(-1px); }
.agent-card.live { position: relative; overflow: hidden; }
.agent-card.running { background: #fff; border-color: #0d9488; box-shadow: 0 4px 12px rgba(13,148,136,.08); }
.agent-card.done { background: #fff; border-color: #e2e8f0; opacity: .85; }

.agent-top-bar { position: absolute; top: 0; left: 0; height: 2px; background: #0d9488; animation: barSweep 0.5s cubic-bezier(0.4,0,0.2,1) both; }
@keyframes barSweep { from { width: 0; } to { width: 100%; } }

.agent-icon { font-size: 22px; flex-shrink: 0; display: flex; align-items: center; }
.agent-card.running .agent-icon { animation: bounceIcon 1s ease infinite; }
@keyframes bounceIcon { 0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)} }

.agent-info { flex: 1; }
.agent-info strong { font-size: 14px; color: #1e293b; }
.agent-info p { font-size: 12px; color: #94a3b8; margin: 2px 0 0; }
.agent-card.running .agent-info p { color: #0d9488; font-weight: 500; }

.tag-idle { background: var(--color-gray-100) !important; color: var(--color-gray-500) !important; border-color: var(--color-gray-200) !important; }
.tag-running { display: inline-flex; align-items: center; background: rgba(59,130,246,.1) !important; color: #3b82f6 !important; border-color: transparent !important; }

/* ===== 报告 ===== */
.report-header { margin-bottom: var(--space-5); }
.report-done { font-size: 18px; font-weight: 700; color: #1e293b; margin-bottom: var(--space-2); }
.agent-badges { display: flex; flex-wrap: wrap; gap: 8px; }
.agent-badge-done { font-size: 11px; color: #64748b; }

.report-section { margin-bottom: var(--space-4); padding-bottom: var(--space-4); border-bottom: 1px solid #f1f5f9; }
.report-section:last-of-type { border-bottom: none; }
.report-section h4 { font-size: 14px; font-weight: 600; color: #334155; margin-bottom: var(--space-3); }
.report-collapse { border: none; }
.report-collapse :deep(.el-collapse-item__header) { font-size: 14px; font-weight: 600; color: #334155; border: none; padding: 0; }
.report-collapse :deep(.el-collapse-item__wrap) { border: none; }
.report-collapse :deep(.el-collapse-item__content) { padding: 12px 0 0; }
.report-hs { display: flex; align-items: center; gap: 12px; }
.report-hs code { font-family: 'JetBrains Mono', monospace; font-size: 22px; color: #0d9488; font-weight: 700; }
.compliance-text { font-size: 13px; color: #64748b; line-height: 1.7; }

.report-actions { display: flex; gap: var(--space-3); margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid #f1f5f9; }
.btn-primary { padding: 10px 24px; font-size: 14px; font-weight: 600; color: #fff; background: linear-gradient(135deg, #0d9488, #0f766e); border: none; border-radius: 10px; cursor: pointer; transition: all 0.2s ease; }
.btn-primary:hover { filter: brightness(1.08); }
.btn-ghost { padding: 10px 20px; font-size: 14px; color: #64748b; background: transparent; border: 1px solid #e2e8f0; border-radius: 10px; cursor: pointer; }
.btn-ghost:hover { border-color: #0d9488; color: #0d9488; }

@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* ===== Agent 颜色主题 ===== */
.agent-card.color-blue { border-left: 3px solid transparent; }
.agent-card.color-yellow { border-left: 3px solid transparent; }
.agent-card.color-green { border-left: 3px solid transparent; }
.agent-card.color-purple { border-left: 3px solid transparent; }
.agent-card.color-gray { border-left: 3px solid transparent; }
.agent-card.color-blue.running { border-color: #3b82f6; background: rgba(59,130,246,.03); }
.agent-card.color-yellow.running { border-color: #f59e0b; background: rgba(245,158,11,.03); }
.agent-card.color-green.running { border-color: #10b981; background: rgba(16,185,129,.03); }
.agent-card.color-purple.running { border-color: #8b5cf6; background: rgba(139,92,246,.03); }
.agent-card.color-gray.running { border-color: #64748b; background: rgba(100,116,139,.03); }
.agent-card.color-blue.done { border-color: #e2e8f0; }
.agent-card.color-yellow.done { border-color: #e2e8f0; }
.agent-card.color-green.done { border-color: #e2e8f0; }
.agent-card.color-purple.done { border-color: #e2e8f0; }
.agent-card.color-gray.done { border-color: #e2e8f0; }
.agent-top-bar.bar-blue { background: #3b82f6; }
.agent-top-bar.bar-yellow { background: #f59e0b; }
.agent-top-bar.bar-green { background: #10b981; }
.agent-top-bar.bar-purple { background: #8b5cf6; }
.agent-top-bar.bar-gray { background: #64748b; }
.icon-blue { background: rgba(59,130,246,.1); border-radius: 10px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
.icon-yellow { background: rgba(245,158,11,.1); border-radius: 10px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
.icon-green { background: rgba(16,185,129,.1); border-radius: 10px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
.icon-purple { background: rgba(139,92,246,.1); border-radius: 10px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
.icon-gray { background: rgba(100,116,139,.1); border-radius: 10px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }

/* ===== 税费明细表 ===== */
.tax-summary { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; font-size: 13px; color: #64748b; }
.tax-summary b { color: #334155; }
.fta-badge { color: #0d9488; }
.tax-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tax-table th { text-align: left; padding: 8px 12px; font-size: 12px; color: #94a3b8; font-weight: 500; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
.tax-table th.num { text-align: right; }
.tax-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.tax-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.tax-table td.note { font-size: 12px; color: #94a3b8; }
.tax-table tfoot td { font-weight: 600; border-bottom: none; padding-top: 12px; }
.tax-table tfoot td.total { color: #0d9488; font-size: 16px; }
.tax-table tfoot td.saving { color: #10b981; }
.tax-disclaimer { font-size: 11px; color: #94a3b8; margin-top: 8px; text-align: right; }

/* ===== 合规清单 ===== */
.risk-badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 14px; }
.risk-badge.red { background: rgba(239,68,68,.08); color: #ef4444; }
.risk-badge.yellow { background: rgba(245,158,11,.08); color: #f59e0b; }
.risk-badge.green { background: rgba(16,185,129,.08); color: #10b981; }
.checklist { display: flex; flex-direction: column; gap: 8px; }
.check-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 8px; background: rgba(16,185,129,.03); border: 1px solid rgba(16,185,129,.1); }
.check-item.fail { background: rgba(239,68,68,.03); border-color: rgba(239,68,68,.1); }
.check-item.all-clear { background: rgba(16,185,129,.05); }
.check-mark { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.check-item:not(.fail) .check-mark { background: rgba(16,185,129,.15); color: #10b981; }
.check-item.fail .check-mark { background: rgba(239,68,68,.15); color: #ef4444; }
.check-item strong { font-size: 13px; color: #334155; display: block; }
.check-item p { font-size: 12px; color: #94a3b8; margin: 2px 0 0; }
.check-source { font-size: 11px; color: #94a3b8; }
.compliance-summary { margin-top: 12px; font-size: 13px; color: #64748b; line-height: 1.8; white-space: pre-wrap; }

/* ===== 交叉校验 ===== */
.cross-check { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.cross-check.all-pass { color: #10b981; }
.cross-check-list { display: flex; flex-direction: column; gap: 6px; }
.cross-check-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 8px; font-size: 13px; background: rgba(16,185,129,.03); border: 1px solid rgba(16,185,129,.1); }
.cross-check-item.fail { background: rgba(239,68,68,.03); border-color: rgba(239,68,68,.1); }
.cross-check-item strong { font-size: 13px; color: #334155; display: block; }
.cross-check-item p { font-size: 12px; color: #94a3b8; margin: 2px 0 0; }

/* ===== 预览按钮组 ===== */
.preview-btns { display: flex; gap: 8px; margin-bottom: 12px; }
.btn-preview { padding: 8px 16px; font-size: 13px; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; transition: all .2s; }
.btn-preview:hover { border-color: #0d9488; color: #0d9488; background: rgba(13,148,136,.04); }

/* ===== 模态框 A4 文档 ===== */
.preview-dialog :deep(.el-dialog__body) { padding: 24px; background: #f1f5f9; }
.a4-doc { background: #fff; padding: 48px 56px; border-radius: 2px; box-shadow: 0 2px 12px rgba(0,0,0,.06); font-family: 'SimSun', '宋体', 'PingFang SC', serif; font-size: 13px; line-height: 1.8; color: #1e293b; max-width: 900px; margin: 0 auto; }
.a4-title { text-align: center; font-size: 18px; font-weight: 700; margin-bottom: 20px; letter-spacing: 2px; }
.a4-meta { display: flex; justify-content: space-between; margin-bottom: 16px; font-size: 12px; color: #64748b; }
.a4-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border: 1px solid #333; margin-bottom: 16px; }
.a4-row { display: flex; border-bottom: 1px solid #333; }
.a4-row:nth-child(odd) { border-right: 1px solid #333; }
.a4-row label { width: 80px; padding: 6px 8px; background: #f8fafc; font-size: 12px; color: #666; flex-shrink: 0; border-right: 1px solid #e2e8f0; }
.a4-row span { padding: 6px 12px; font-weight: 600; font-size: 13px; }
.a4-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; border: 1px solid #333; }
.a4-table th { padding: 6px 8px; background: #f8fafc; font-size: 11px; color: #666; border: 1px solid #333; text-align: center; }
.a4-table td { padding: 6px 8px; border: 1px solid #333; text-align: center; font-size: 12px; }
.a4-table td code { font-family: 'JetBrains Mono', monospace; color: #0d9488; font-weight: 600; }
.a4-section { margin-bottom: 16px; }
.a4-section h4 { font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #334155; }
.a4-section p { white-space: pre-wrap; line-height: 1.8; }
.a4-footer { text-align: center; color: #999; font-size: 12px; margin-top: 24px; }
.compliance-hero { text-align: center; padding: 14px; margin: -48px -56px 24px; border-radius: 2px 2px 0 0; }
.compliance-hero.red { background: #ef4444; color: #fff; }
.compliance-hero.yellow { background: #f59e0b; color: #fff; }
.compliance-hero.green { background: #10b981; color: #fff; }
.compliance-hero h2 { margin: 0; font-size: 18px; }

/* ===== 打印样式（浏览器 Ctrl+P → 另存为 PDF） ===== */
@media print {
  body > * { display: none !important; }
  .el-dialog__wrapper { position: static !important; display: block !important; }
  .el-dialog { position: static !important; margin: 0 !important; max-width: none !important; width: auto !important; box-shadow: none !important; }
  .el-dialog__body { padding: 0 !important; background: #fff !important; }
  .el-dialog__header, .el-dialog__footer { display: none !important; }
  .report-actions, .preview-btns, .el-overlay-dialog, .el-dialog__footer button { display: none !important; }
  .a4-doc { box-shadow: none !important; padding: 20px !important; max-width: none !important; }
}
</style>
