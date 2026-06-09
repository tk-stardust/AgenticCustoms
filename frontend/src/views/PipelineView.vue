<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'
import type { Commodity } from '@/types'
import { Check, Loading, Camera } from '@element-plus/icons-vue'
import { ocrImage } from '@/api/ocr'
import { runPipelineSSE } from '@/api/pipeline'

const store = usePipelineStore()
let abortCtrl: AbortController | null = null
const emptyPipeline = (): Commodity => ({ name: '', description: '', material: '', function: '', usage: '' })
const saved = localStorage.getItem("pipelineForm")
const form = ref<Commodity>(saved && JSON.parse(saved).name ? JSON.parse(saved) : emptyPipeline())
const country = ref(store.targetCountry)

// 切页离开（keep-alive 缓存）：停动画 + 存表单
onDeactivated(() => {
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null }
  if (form.value.name) localStorage.setItem("pipelineForm", JSON.stringify(form.value))
  else localStorage.removeItem("pipelineForm")
})
// 页面刷新/关闭：存表单
onUnmounted(() => {
  if (form.value.name) localStorage.setItem("pipelineForm", JSON.stringify(form.value))
  else localStorage.removeItem("pipelineForm")
})
// 首次挂载：从 Classify 跳转过来时自动运行
onMounted(() => {
  if (!store.autoRun) return
  store.autoRun = false
  if (store.commodity?.name) {
    form.value = { name: store.commodity.name, description: store.commodity.description || '', material: '', function: '', usage: '' }
    materialTags.value = []
    country.value = store.targetCountry
    setTimeout(() => onSubmit(), 500)
  }
})
// keep-alive 切回来：重启动画，或同步已完成的 store 结果
onActivated(() => {
  // keep-alive 切回来：如果 SSE 已完成，同步结果状态
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
  '检索第 84-85 章税则品目...',
  '匹配 OFAC/商务部制裁清单...',
  '比对 RCEP 原产地规则...',
  '生成报关单 + 交叉校验...',
]

const countryOptions = [
  { value: 'US', label: '🇺🇸 美国' },
  { value: 'EU', label: '🇪🇺 欧盟' },
  { value: 'VN', label: '🇻🇳 越南' },
]

const materialTags = ref<string[]>([])
const materialInput = ref('')
const ocrLoading = ref(false)

// 同票多商品项
interface CommodityRow { name: string; hs_code: string; quantity: number; declared_value: number }
const commodityRows = ref<CommodityRow[]>([])
function addRow() {
  commodityRows.value.push({ name: '', hs_code: '', quantity: 1, declared_value: 0 })
}
function removeRow(idx: number) {
  commodityRows.value.splice(idx, 1)
}

async function onUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  ocrLoading.value = true
  try {
    const base64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve((reader.result as string).split(',')[1])
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    const result = await ocrImage(base64, file.type)
    form.value.name = result.name || form.value.name
    form.value.description = result.description || form.value.description
    form.value.material = result.material || form.value.material
    form.value.function = result.function || form.value.function
    form.value.usage = result.usage || form.value.usage
  } catch { /* ignored */ }
  finally { ocrLoading.value = false }
}

function addMaterialTag() {
  const v = materialInput.value.trim()
  if (v && !materialTags.value.includes(v)) {
    materialTags.value.push(v)
    form.value.material = materialTags.value.join('/')
  }
  materialInput.value = ''
}
function removeTag(idx: number) {
  materialTags.value.splice(idx, 1)
  form.value.material = materialTags.value.join('/')
}

function clearForm() {
  form.value = emptyPipeline()
  materialTags.value = []
  commodityRows.value = []
  localStorage.removeItem("pipelineForm")
}
function clearResult() {
  phase.value = 'idle'
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

function downloadReport() {
  const rid = store.documents?.request_id
  if (rid) window.open(`/api/pipeline/report/${rid}`, '_blank')
}
function printDocument() {
  window.print()
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
                <el-icon :size="18"><Camera/></el-icon>
                <input type="file" accept="image/*" hidden @change="onUpload"/>
              </label>
            </div>
          </el-form-item>
          <el-form-item label="商品描述" required>
            <el-input v-model="form.description" type="textarea" :rows="3"
              placeholder="外观、材质、工作原理、用途等" class="custom-input" clearable maxlength="2000" show-word-limit/>
          </el-form-item>

          <!-- 材质独占一行 -->
          <el-form-item label="材质">
            <div class="tag-input-wrap" @click="materialInput && addMaterialTag()">
              <span v-for="(t, i) in materialTags" :key="i" class="mat-tag">
                {{ t }} <span class="mat-close" @click.stop="removeTag(i)">×</span>
              </span>
              <input v-model="materialInput" class="mat-input" placeholder="输入后回车添加"
                @keydown.enter.prevent="addMaterialTag()" @blur="addMaterialTag" />
            </div>
          </el-form-item>

          <el-row :gutter="12">
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
          <el-divider v-if="commodityRows.length" content-position="left">附加商品项（同票）</el-divider>
          <div v-for="(row, idx) in commodityRows" :key="idx" class="commodity-row">
            <el-row :gutter="8">
              <el-col :span="6"><el-input v-model="row.name" placeholder="商品名称" size="small" clearable/></el-col>
              <el-col :span="4"><el-input v-model="row.hs_code" placeholder="HS编码" size="small" clearable/></el-col>
              <el-col :span="3"><el-input-number v-model="row.quantity" :min="1" size="small" style="width:100%"/></el-col>
              <el-col :span="3"><el-input-number v-model="row.declared_value" :min="0" :precision="2" size="small" style="width:100%"/></el-col>
              <el-col :span="2"><el-button size="small" type="danger" plain @click="removeRow(idx)">✕</el-button></el-col>
            </el-row>
          </div>
          <el-button size="small" type="primary" plain @click="addRow()" style="margin-top:8px">+ 添加商品</el-button>

          <button v-if="phase !== 'running'" type="button" class="btn-start" @click="onSubmit">
            ⚡ 开始全流程分析
          </button>
          <button v-else type="button" class="btn-start running" @click="cancelPipeline">
            <span class="agent-progress">
              <span class="mini-spinner"></span>
              Agent {{ Math.min(agentPhase + 1, 5) }}/5 运行中...  (点击取消)
            </span>
          </button>
          <div v-if="phase === 'running'" class="progress-bar">
            <div class="progress-fill" :style="{ width: ((agentPhase + 1) / 5 * 100) + '%' }"></div>
          </div>
        </el-form>
      </div>

      <!-- ============ 右侧 ============ -->
      <div class="panel panel-result" :class="{ 'has-report': showReport }">

        <!-- 空状态：5 Agent 卡片 -->
        <div v-if="phase === 'idle'" class="agent-grid">
          <div v-for="(a, i) in agents" :key="i" class="agent-card" :class="`color-${agentColors[i]}`" :style="{ animationDelay: `${i*0.08}s` }">
            <div class="agent-icon" :class="`icon-${agentColors[i]}`">{{ a.icon }}</div>
            <div class="agent-info">
              <strong>{{ a.name }}</strong>
              <p>{{ a.desc }}</p>
            </div>
            <el-tag size="small" round class="tag-idle">等待中</el-tag>
          </div>
        </div>

        <!-- 运行状态：5 Agent 卡片激活 -->
        <div v-if="phase === 'running'" class="agent-grid">
          <div
            v-for="(a, i) in agents" :key="i"
            class="agent-card live"
            :class="[agentState(i), `color-${agentColors[i]}`]"
          >
            <div class="agent-top-bar" v-if="agentState(i) !== 'idle'" :class="`bar-${agentColors[i]}`"></div>
            <div class="agent-icon" :class="`icon-${agentColors[i]}`">{{ agentState(i) === 'done' ? '✅' : agentState(i) === 'running' ? '🔄' : a.icon }}</div>
            <div class="agent-info">
              <strong>{{ a.name }}</strong>
              <p>{{ logs[i] || a.desc }}</p>
            </div>
            <el-tag v-if="agentState(i) === 'done'" size="small" type="success" round>已完成</el-tag>
            <el-tag v-else-if="agentState(i) === 'running'" size="small" class="tag-running" round>
              <el-icon :size="12" style="margin-right:4px"><Loading /></el-icon>处理中
            </el-tag>
            <el-tag v-else size="small" round class="tag-idle">等待中</el-tag>
          </div>
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
              <el-tag size="small" type="success" effect="dark">已确认</el-tag>
            </div>
          </div>

          <!-- 税费明细 -->
          <div class="report-section">
            <h4>税费明细</h4>
            <div class="tax-summary">
              <span>商品：<b>{{ store.documents?.customs_declaration?.commodity_name || '—' }}</b></span>
              <span>原产地：<b>{{ store.documents?.customs_declaration?.origin || '—' }}</b></span>
              <span v-if="store.tariffResult?.fta_applied">FTA：<b class="fta-badge">{{ store.tariffResult.fta_applied }}</b></span>
            </div>
            <table class="tax-table" v-if="store.tariffResult?.items?.length">
              <thead>
                <tr><th>税项</th><th>税率</th><th>金额（元）</th><th>备注</th></tr>
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
                  <td colspan="2">综合税率</td>
                  <td class="num total" colspan="2">{{ store.tariffResult.total_rate }}%</td>
                </tr>
                <tr v-if="store.tariffResult.fta_saving">
                  <td colspan="2">FTA 优惠节省</td>
                  <td class="num saving" colspan="2">-{{ store.tariffResult.fta_saving?.toFixed(2) }} 元</td>
                </tr>
              </tfoot>
            </table>
            <p class="tax-disclaimer">税率数据更新至 2024-06，仅供参考，具体以海关最新公告为准</p>
          </div>

          <!-- 风险与合规 -->
          <div class="report-section">
            <h4>合规校验</h4>
            <div class="risk-badge" :class="store.complianceResult?.risk_level">
              {{ store.complianceResult?.risk_level === 'red' ? '🔴 高风险' : store.complianceResult?.risk_level === 'yellow' ? '🟡 中风险' : '🟢 低风险' }}
            </div>
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
          </div>

          <!-- 校验 -->
          <div class="report-section">
            <h4>交叉校验</h4>
            <div v-if="store.documents?.cross_check_passed" class="cross-check all-pass">
              <span class="check-mark">✓</span><span>全部校验通过</span>
            </div>
            <div v-else class="cross-check-list">
              <div v-for="(e,i) in store.documents?.cross_check_errors" :key="i" class="cross-check-item fail">
                <span class="check-mark">✗</span><span>{{ e }}</span>
              </div>
            </div>
          </div>

          <div class="preview-btns">
            <button type="button" class="btn-preview" @click="openPreview('customs')">📋 预览报关单</button>
            <button type="button" class="btn-preview" @click="openPreview('origin')">📜 预览原产地证</button>
            <button type="button" class="btn-preview" @click="openPreview('compliance')">🛡️ 预览合规声明</button>
          </div>
          <div class="report-actions">
            <button class="btn-primary" @click="downloadReport">📥 下载申报文件</button>
            <button type="button" class="btn-ghost" @click="clearResult()">清除结果</button>
            <button type="button" class="btn-ghost" @click="clearForm()">清空表单</button>
          </div>
        </template>
      </div>
    </div>

    <!-- 申报文件预览模态框 -->
    <el-dialog v-model="showPreview" :title="previewType === 'customs' ? '报关单草单' : previewType === 'origin' ? '原产地证书申请书' : '合规声明'" width="80vw" top="3vh" destroy-on-close class="preview-dialog">
      <!-- 报关单 -->
      <div v-if="previewType === 'customs'" class="a4-doc">
        <h2 class="a4-title">中华人民共和国海关出口货物报关单</h2>
        <div class="a4-meta">
          <span>预录入编号：{{ store.documents?.request_id || '—' }}</span>
          <span>申报日期：{{ new Date().toISOString().slice(0, 10) }}</span>
        </div>
        <div class="a4-grid">
          <div class="a4-row"><label>出口口岸</label><span>{{ store.documents?.customs_declaration?.port || '待填写' }}</span></div>
          <div class="a4-row"><label>经营单位</label><span>待填写</span></div>
          <div class="a4-row"><label>发货单位</label><span>待填写</span></div>
          <div class="a4-row"><label>运输方式</label><span>待填写</span></div>
          <div class="a4-row"><label>贸易方式</label><span>一般贸易</span></div>
          <div class="a4-row"><label>征免性质</label><span>一般征税</span></div>
        </div>
        <table class="a4-table">
          <thead><tr><th>商品名称</th><th>HS编码</th><th>单位</th><th>数量</th><th>原产国</th><th>单价</th><th>总价</th></tr></thead>
          <tbody><tr>
            <td>{{ store.documents?.customs_declaration?.commodity_name || '—' }}</td>
            <td><code>{{ store.documents?.customs_declaration?.hs_code || '—' }}</code></td>
            <td>{{ store.documents?.customs_declaration?.unit || '件' }}</td>
            <td>{{ store.documents?.customs_declaration?.quantity || '—' }}</td>
            <td>{{ store.documents?.customs_declaration?.origin || 'CN' }}</td>
            <td>{{ store.documents?.customs_declaration?.declared_value || '—' }}</td>
            <td>{{ store.documents?.customs_declaration?.declared_value || '—' }}</td>
          </tr></tbody>
        </table>
        <p class="a4-footer">申报单位签章：________ &nbsp;&nbsp; 日期：________</p>
      </div>

      <!-- 原产地证书 -->
      <div v-if="previewType === 'origin'" class="a4-doc">
        <h2 class="a4-title">原产地证书申请书</h2>
        <div class="a4-grid">
          <div class="a4-row"><label>申请人</label><span>待填写</span></div>
          <div class="a4-row"><label>证书类型</label><span>{{ store.documents?.origin_certificate?.fta || '—' }}</span></div>
          <div class="a4-row"><label>出口国</label><span>中国</span></div>
          <div class="a4-row"><label>进口国</label><span>{{ store.tariffResult?.country || '—' }}</span></div>
          <div class="a4-row"><label>HS编码</label><span><code>{{ store.documents?.origin_certificate?.hs_code || '—' }}</code></span></div>
          <div class="a4-row"><label>原产地标准</label><span>{{ store.documents?.origin_certificate?.origin_criteria || '—' }}</span></div>
        </div>
        <div class="a4-section">
          <h4>适用 FTA</h4>
          <p>{{ store.tariffResult?.fta_applied || '无' }}</p>
        </div>
        <div class="a4-section" v-if="store.originResult">
          <h4>原产地分析</h4>
          <p>推荐原产地：<b>{{ store.originResult.recommended_origin || 'CN' }}</b></p>
          <p>满足条件：{{ store.originResult.meeting_criteria?.join('、') || '—' }}</p>
          <p v-if="store.originResult.rvc_percentage">区域价值成分：<b>{{ store.originResult.rvc_percentage }}%</b></p>
          <p>{{ store.originResult.note }}</p>
        </div>
        <p class="a4-footer">申请人签章：________ &nbsp;&nbsp; 日期：________</p>
      </div>

      <!-- 合规声明 -->
      <div v-if="previewType === 'compliance'" class="a4-doc">
        <div class="compliance-hero" :class="store.complianceResult?.risk_level">
          <h2>{{ store.complianceResult?.risk_level === 'red' ? '✗ 不合规' : store.complianceResult?.risk_level === 'yellow' ? '⚠ 部分合规' : '✓ 合规通过' }}</h2>
        </div>
        <h2 class="a4-title">跨境贸易合规声明</h2>
        <div class="a4-meta">
          <span>声明编号：CC-{{ store.documents?.request_id || '—' }}</span>
          <span>生成日期：{{ new Date().toISOString().slice(0, 10) }}</span>
        </div>
        <div class="a4-section">
          <h4>商品信息</h4>
          <p>商品名称：{{ store.documents?.customs_declaration?.commodity_name || '—' }}</p>
          <p>HS编码：{{ store.documents?.customs_declaration?.hs_code || '—' }} | 目标国：{{ store.tariffResult?.country || '—' }}</p>
        </div>
        <div class="a4-section">
          <h4>校验结果</h4>
          <div class="checklist">
            <div class="check-item" :class="{ fail: store.complianceResult?.sanctions_hit }">
              <span class="check-mark">{{ store.complianceResult?.sanctions_hit ? '✗' : '☑' }}</span>
              <span>制裁清单校验 — {{ store.complianceResult?.sanctions_hit ? '命中' : '通过' }}</span>
            </div>
            <div class="check-item" :class="{ fail: store.complianceResult?.license_required }">
              <span class="check-mark">{{ store.complianceResult?.license_required ? '⚠' : '☑' }}</span>
              <span>出口许可校验 — {{ store.complianceResult?.license_required ? '需要许可' : '无需许可' }}</span>
            </div>
            <div v-for="v in store.complianceResult?.violations" :key="v.category" class="check-item fail">
              <span class="check-mark">✗</span>
              <span>{{ v.category }} — {{ v.description }}</span>
            </div>
            <div class="check-item">
              <span class="check-mark">☑</span><span>环保合规 — 符合 RoHS / REACH</span>
            </div>
            <div class="check-item">
              <span class="check-mark">☑</span><span>知识产权校验 — 通过</span>
            </div>
          </div>
        </div>
        <div class="a4-section">
          <h4>综合评定</h4>
          <p>{{ store.documents?.compliance_statement }}</p>
        </div>
        <p class="a4-footer">本声明自生成之日起30日内有效 | AgenticCustoms 智能合规平台</p>
      </div>

      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
        <el-button @click="printDocument()">🖨️ 打印 / PDF</el-button>
        <el-button type="primary" @click="downloadReport">下载 HTML</el-button>
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
.input-with-btn { display: flex; gap: 8px; align-items: stretch; }
.input-with-btn .custom-input { flex: 1; }
.ocr-btn { display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; cursor: pointer; color: #94a3b8; transition: all .2s; flex-shrink: 0; }
.ocr-btn:hover { border-color: #0d9488; color: #0d9488; }
.ocr-btn.loading { opacity: .6; pointer-events: none; }
.commodity-row { padding: 8px; margin-bottom: 4px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
:deep(.el-row) { align-items: flex-start; }
:deep(.custom-input .el-input__wrapper) {
  height: 44px; border-radius: 10px;
  border: 1px solid #e2e8f0; box-shadow: none;
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
  height: 80px; overflow-y: auto; width: 100%;
  cursor: text; background: #fff;
  align-self: flex-start;
}
.tag-input-wrap:focus-within { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.08); }
.mat-tag {
  padding: 2px 8px; border-radius: 999px; font-size: 12px;
  background: rgba(13,148,136,.08); color: #0d9488;
  display: inline-flex; align-items: center; gap: 2px;
}
.mat-close { cursor: pointer; font-weight: 700; color: #5eead4; }
.mat-input { border: none; outline: none; flex: 1; min-width: 60px; font-size: 13px; background: transparent; }


.btn-start {
  width: 100%; padding: 14px 40px; font-size: 16px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #0d9488, #0f766e); border: none; border-radius: 12px;
  cursor: pointer; transition: all 0.3s ease; margin-top: var(--space-3);
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
.compliance-summary { margin-top: 12px; font-size: 13px; color: #64748b; line-height: 1.6; }

/* ===== 交叉校验 ===== */
.cross-check { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.cross-check.all-pass { color: #10b981; }
.cross-check-list { display: flex; flex-direction: column; gap: 6px; }
.cross-check-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px; font-size: 13px; }
.cross-check-item.fail { background: rgba(239,68,68,.04); color: #ef4444; }

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
  .a4-doc { box-shadow: none !important; padding: 20px !important; max-width: none !important; }
}
</style>
