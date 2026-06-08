<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'
import type { Commodity } from '@/types'
import { Check, Loading } from '@element-plus/icons-vue'

const store = usePipelineStore()
const saved = localStorage.getItem("pipelineForm")
const form = ref<Commodity>(saved ? JSON.parse(saved) : { name: '', description: '', material: '', function: '', usage: '' })
const country = ref(store.targetCountry)
onUnmounted(() => localStorage.setItem("pipelineForm", JSON.stringify(form.value)))
onMounted(() => {
  if (!store.autoRun) return
  store.autoRun = false
  if (store.commodity?.name) {
    form.value = { name: store.commodity.name, description: store.commodity.description || '', material: '', function: '', usage: '' }
    materialTags.value = []
    country.value = store.targetCountry
    if (store.autoRun) {
      store.autoRun = false
      setTimeout(() => onSubmit(), 500)  // 等组件渲染完再提交
    }
  }
})
const phase = ref<'idle' | 'running' | 'done'>('idle')
const activePhase = ref(-1)
const agentPhase = ref(-1)

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

async function onSubmit() {
  if (!form.value.name.trim()) { ElMessage.warning('请输入商品名称'); return }
  if (!form.value.description.trim()) { ElMessage.warning('请输入商品描述'); return }
  phase.value = 'running'; activePhase.value = 0; agentPhase.value = 0
  const timer = setInterval(() => {
    if (agentPhase.value < agents.length - 1) {
      agentPhase.value++
      activePhase.value = agentPhase.value
    }
  }, 8000)
  try {
    await store.runPipeline({ ...form.value }, country.value)
  } catch {
    // error already in store.errors
  }
  clearInterval(timer)
  activePhase.value = steps.length - 1
  agentPhase.value = agents.length - 1
  phase.value = 'done'
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
            <el-input v-model="form.name" placeholder="例：蓝牙智能音箱" size="large" class="custom-input" clearable/>
          </el-form-item>
          <el-form-item label="商品描述" required>
            <el-input v-model="form.description" type="textarea" :rows="3"
              placeholder="外观、材质、工作原理、用途等" class="custom-input" clearable/>
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
              <el-form-item label="功能"><el-input v-model="form.function" placeholder="音乐播放" class="custom-input" clearable/></el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="用途"><el-input v-model="form.usage" placeholder="家庭娱乐" class="custom-input" clearable/></el-form-item>
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
                <el-input-number v-model="form.quantity" :min="1" size="large" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="申报价值（元）">
                <el-input-number v-model="form.declared_value" :min="0" :precision="2" size="large" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>


          <button type="button" class="btn-start" :class="{ running: phase === 'running' }" :disabled="phase === 'running'" @click="onSubmit">
            <span v-if="phase !== 'running'">⚡ 开始全流程分析</span>
            <span v-else class="agent-progress">
              <span class="mini-spinner"></span>
              Agent {{ Math.min(agentPhase + 1, 5) }}/5 运行中...
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
          <div v-for="(a, i) in agents" :key="i" class="agent-card" :style="{ animationDelay: `${i*0.08}s` }">
            <div class="agent-icon">{{ a.icon }}</div>
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
            :class="agentState(i)"
          >
            <div class="agent-top-bar" v-if="agentState(i) !== 'idle'"></div>
            <div class="agent-icon">{{ agentState(i) === 'done' ? '✅' : agentState(i) === 'running' ? '🔄' : a.icon }}</div>
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
            <el-descriptions :column="2" size="small" border>
              <el-descriptions-item label="商品名称">{{ store.documents?.customs_declaration?.commodity_name || '—' }}</el-descriptions-item>
              <el-descriptions-item label="综合税率">{{ store.documents?.customs_declaration?.total_tax_rate || 0 }}%</el-descriptions-item>
              <el-descriptions-item label="原产地">{{ store.documents?.customs_declaration?.origin || '—' }}</el-descriptions-item>
              <el-descriptions-item label="单位">{{ store.documents?.customs_declaration?.unit || '—' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 风险与合规 -->
          <div class="report-section">
            <h4>合规声明</h4>
            <p class="compliance-text">{{ store.documents?.compliance_statement }}</p>
          </div>

          <!-- 校验 -->
          <div class="report-section">
            <h4>交叉校验</h4>
            <el-tag v-if="store.documents?.cross_check_passed" type="success" effect="dark">全部一致</el-tag>
            <div v-else>
              <el-alert v-for="(e,i) in store.documents?.cross_check_errors" :key="i"
                type="warning" :title="e" show-icon style="margin-bottom:6px" />
            </div>
          </div>

          <div class="report-actions">
            <button class="btn-primary" @click="downloadReport">📥 下载申报文件</button>
            <button class="btn-ghost" @click="phase='idle'; store.reset()">重新分析</button>
          </div>
        </template>
      </div>
    </div>
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
</style>
