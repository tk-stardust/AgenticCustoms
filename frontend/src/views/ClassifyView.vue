<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'
import type { Commodity } from '@/types'
import { Search, MagicStick, CopyDocument, Check, Camera } from '@element-plus/icons-vue'
import { ocrImage } from '@/api/ocr'

const store = usePipelineStore()
const form = ref<Commodity>({ name:'',description:'',material:'',function:'',usage:'' })
const loadingStep = ref(0)
const ocrLoading = ref(false)
const ocrResult = ref<Commodity | null>(null)  // 仅存 OCR 识别结果，手动输入不触发
let stepTimer: ReturnType<typeof setInterval> | null = null

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
    ocrResult.value = { ...result }
  } catch { /* ignored */ }
  finally { ocrLoading.value = false }
}
const collActive = ref<string[]>(['reasoning'])

async function onSubmit() {
  if (!form.value.name.trim()) { ElMessage.warning('请输入商品名称'); return }
  if (!form.value.description.trim()) { ElMessage.warning('请输入商品描述'); return }
  loadingStep.value=0
  stepTimer = setInterval(()=>{ if(loadingStep.value<3) loadingStep.value++ },5000)
  await store.runClassify({...form.value})
  if(stepTimer){clearInterval(stepTimer);stepTimer=null}
  loadingStep.value=3
}
const confidenceType = computed(()=>{
  if(!store.hsResult) return 'info'
  const c = store.hsResult.confidence
  return c>=0.9?'success':c>=0.7?'warning':'danger'
})
const showManual=ref(false); const manualHs=ref('')
async function copyCode(){ if(!store.hsResult) return; await navigator.clipboard.writeText(store.hsResult.code) }
const loadingLogs = ['正在拆解商品特征...','检索 WCO 注释第 84-85 章...','匹配历史归类案例...','LLM 推理合成中...']
</script>

<template>
  <div class="page-container">
    <div class="page-header"><h1>HS 编码归类</h1><p class="text-muted text-sm">基于 Agentic RAG 引擎，自动推理国际贸易商品编码</p></div>

    <div class="layout">
      <!-- 左侧表单 -->
      <div class="panel panel-form">
        <div class="panel-top-bar"></div>
        <h3 class="panel-title">商品信息</h3>
        <el-form :model="form" label-position="top">
          <div class="field-group">
            <label class="field-label"><span class="required-star">*</span> 商品名称</label>
            <div class="input-with-btn">
              <el-input v-model="form.name" placeholder="例：蓝牙智能音箱" size="large" class="custom-input" clearable/>
              <label class="ocr-btn" :class="{loading:ocrLoading}" title="拍照识别">
                <el-icon :size="18"><Camera/></el-icon>
                <input type="file" accept="image/*" hidden @change="onUpload"/>
              </label>
            </div>
          </div>
          <div class="field-group">
            <label class="field-label"><span class="required-star">*</span> 商品描述</label>
            <el-input v-model="form.description" type="textarea" :rows="4"
              placeholder="描述外观、材质、功能、用途..." class="custom-textarea" clearable/>
          </div>
          <div v-if="ocrResult" class="ai-extract">
            <div class="ai-badge"><el-icon :size="14"><MagicStick/></el-icon><span>AI 自动识别</span></div>
            <div class="extract-tags">
              <span v-if="ocrResult.material" class="extract-tag">材质：<b>{{ ocrResult.material }}</b></span>
              <span v-if="ocrResult.function" class="extract-tag">功能：<b>{{ ocrResult.function }}</b></span>
              <span v-if="ocrResult.usage" class="extract-tag">用途：<b>{{ ocrResult.usage }}</b></span>
            </div>
          </div>
          <el-row v-else :gutter="12">
            <el-col :span="8"><el-form-item label="材质"><el-input v-model="form.material" placeholder="塑料/金属" clearable/></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="功能"><el-input v-model="form.function" placeholder="音乐播放" clearable/></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="用途"><el-input v-model="form.usage" placeholder="家庭娱乐" clearable/></el-form-item></el-col>
          </el-row>
          <div class="btn-group">
            <button type="button" class="btn-primary" :class="{loading:store.classifyLoading}" :disabled="store.classifyLoading" @click="onSubmit">
              <el-icon v-if="!store.classifyLoading" :size="18" style="margin-right:6px"><Search/></el-icon>
              <span v-if="store.classifyLoading" class="spinner"></span>
              {{ store.classifyLoading?'AI 推理中...':'开始归类' }}
            </button>
            <button class="btn-ghost" @click="store.reset()" :disabled="store.classifyLoading">清空</button>
          </div>
        </el-form>
      </div>

      <!-- 右侧结果 -->
      <div class="panel panel-result" :class="{'has-result':store.hsResult}">
        <!-- 空状态 -->
        <div v-if="!store.hsResult && !store.classifyLoading" class="empty-state">
          <div class="empty-illustration"><div class="robot-icon"><span class="robot-eye">◎</span></div></div>
          <h2>AI 智能归类引擎就绪</h2>
          <p class="empty-sub">输入商品信息后，AI 将自动完成：</p>
          <div class="preview-steps">
            <div v-for="(s,i) in [['1','特征拆解','提取材质、功能、用途'],['2','RAG 检索','匹配 WCO 税则与历史案例'],['3','编码推理','输出 HS 编码与置信度']]" :key="i"
              class="preview-step" :style="{animationDelay:`${i*.1}s`}">
              <span class="step-num">{{ s[0] }}</span>
              <div><strong>{{ s[1] }}</strong><p>{{ s[2] }}</p></div>
            </div>
          </div>
          <p class="empty-time">预计处理时间 ~15 秒</p>
        </div>

        <!-- 加载 -->
        <div v-if="store.classifyLoading" class="loading-state">
          <h3>正在归类...</h3>
          <div class="loading-steps">
            <div v-for="(log,i) in loadingLogs" :key="i" class="loading-step" :class="{active:i===loadingStep,done:i<loadingStep}">
              <div class="step-indicator">
                <el-icon v-if="i<loadingStep" :size="14"><Check/></el-icon>
                <span v-else-if="i===loadingStep" class="pulse-dot"></span>
                <span v-else class="pending-dot"></span>
              </div>
              <span class="step-text">{{ log }}</span>
            </div>
          </div>
        </div>

        <!-- 结果 -->
        <template v-if="store.hsResult">
          <div class="result-hero">
            <div><div class="hs-label">HS 编码</div><div class="hs-code">{{ store.hsResult.code }}</div><p class="hs-desc">{{ store.hsResult.description }}</p></div>
            <button class="copy-btn" @click="copyCode" title="复制编码"><el-icon :size="18"><CopyDocument/></el-icon></button>
          </div>
          <div class="confidence-bar">
            <div class="conf-label"><span>置信度</span><span class="conf-value">{{ (store.hsResult.confidence*100).toFixed(1) }}%</span></div>
            <div class="conf-track"><div class="conf-fill" :class="confidenceType" :style="{width:(store.hsResult.confidence*100)+'%'}"></div></div>
          </div>
          <el-collapse v-model="collActive" class="reasoning-collapse">
            <el-collapse-item title="推理路径" name="reasoning">
              <ol class="reasoning-list"><li v-for="(s,i) in store.hsResult.reasoning_path" :key="i" :style="{animationDelay:`${i*.05}s`}">{{ s }}</li></ol>
            </el-collapse-item>
          </el-collapse>
          <el-collapse v-if="store.hsResult.citations.length" class="reasoning-collapse">
            <el-collapse-item title="条文溯源" name="citations">
              <div v-for="(c,i) in store.hsResult.citations" :key="i" class="citation-card" :style="{animationDelay:`${i*.08}s`}">{{ c }}</div>
            </el-collapse-item>
          </el-collapse>
          <div v-if="store.hsResult.alternatives.length" style="margin-top:12px">
            <div class="alt-title">备选编码</div>
            <div v-for="a in store.hsResult.alternatives" :key="a.code" class="alt-row">
              <el-tag size="small" round>{{ a.code }}</el-tag><span>{{ a.description }}</span><span class="alt-conf">{{ (a.confidence*100).toFixed(0) }}%</span>
            </div>
          </div>
          <div class="result-actions">
            <button class="btn-primary">确认选用</button>
            <button class="btn-ghost" @click="store.reset()">重新推理</button>
            <button class="btn-text" @click="showManual=!showManual">人工修正</button>
          </div>
          <div v-if="showManual" class="manual-fix">
            <el-input v-model="manualHs" placeholder="输入正确的 HS 编码" size="small" style="margin-right:8px"/>
            <el-button size="small" type="primary">提交</el-button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header{margin-bottom:24px}
.page-header h1{font-size:24px;font-weight:700;color:#1e293b;letter-spacing:-0.02em}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}

.panel{background:#fff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,.04)}
.panel-form{position:relative;padding:24px}
.panel-result{min-height:400px;padding:24px}
.panel-top-bar{position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#0d9488,#14b8a6)}
.panel-title{font-size:16px;font-weight:600;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}
.input-with-btn{display:flex;gap:8px;align-items:stretch}
.input-with-btn .custom-input{flex:1}
.ocr-btn{display:flex;align-items:center;justify-content:center;width:44px;height:44px;background:var(--color-white);border:1px solid var(--color-gray-200);border-radius:var(--radius-md);cursor:pointer;color:var(--color-gray-400);transition:all var(--transition-smooth);flex-shrink:0}
.ocr-btn:hover{border-color:var(--color-brand-500);color:var(--color-brand-500)}
.ocr-btn.loading{opacity:.6;pointer-events:none}

.field-group{margin-bottom:16px}
.field-label{display:flex;align-items:center;gap:6px;font-size:14px;font-weight:500;color:#1e293b;margin-bottom:8px}
.required-star{color:var(--color-danger);font-weight:700;font-size:14px;flex-shrink:0}
:deep(.custom-input .el-input__wrapper){height:44px;border-radius:10px;border:1px solid #e2e8f0;box-shadow:none;transition:all .2s}
:deep(.custom-input.is-focus .el-input__wrapper){border-color:#0d9488;box-shadow:0 0 0 3px rgba(13,148,136,.08)}
:deep(.custom-textarea .el-textarea__inner){border-radius:10px;border:1px solid #e2e8f0;box-shadow:none;resize:none;min-height:100px;font-size:14px}
:deep(.custom-textarea .el-textarea__inner:focus){border-color:#0d9488;box-shadow:0 0 0 3px rgba(13,148,136,.08)}

.ai-extract{margin-top:12px;padding:12px;background:rgba(13,148,136,.03);border-radius:10px}
.ai-badge{display:flex;align-items:center;gap:4px;font-size:12px;color:#0d9488;margin-bottom:6px}
.extract-tags{display:flex;flex-wrap:wrap;gap:8px}
.extract-tag{padding:3px 10px;border-radius:999px;font-size:12px;color:#475569;background:rgba(13,148,136,.08)}
.extract-tag b{color:#1e293b}

.btn-group{display:flex;gap:12px;margin-top:8px}
.btn-primary{display:inline-flex;align-items:center;padding:12px 28px;font-size:16px;font-weight:600;color:#fff;background:linear-gradient(135deg,#0d9488,#0f766e);border:none;border-radius:10px;cursor:pointer;transition:all .2s;will-change:transform}
.btn-primary:hover:not(:disabled){filter:brightness(1.08);box-shadow:0 4px 12px rgba(13,148,136,.3);transform:scale(1.02)}
.btn-primary:active:not(:disabled){transform:scale(.98)}
.btn-primary:disabled{opacity:.7;cursor:not-allowed}
.btn-ghost{padding:12px 20px;font-size:14px;color:#64748b;background:transparent;border:1px solid #e2e8f0;border-radius:10px;cursor:pointer;transition:all .2s}
.btn-ghost:hover{border-color:#0d9488;color:#0d9488}
.btn-text{padding:8px 12px;font-size:13px;color:#94a3b8;background:none;border:none;cursor:pointer;text-decoration:underline}
.btn-text:hover{color:#0d9488}
.spinner{display:inline-block;width:16px;height:16px;margin-right:8px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* 空状态 */
.empty-state{text-align:center;padding:32px 24px;background:radial-gradient(ellipse at center,rgba(13,148,136,.04) 0%,transparent 70%);border-radius:12px;animation:fadeUp .4s cubic-bezier(.4,0,.2,1)}
.robot-icon{width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,rgba(13,148,136,.08),rgba(20,184,166,.12));display:inline-flex;align-items:center;justify-content:center;margin-bottom:16px}
.robot-eye{font-size:28px;color:#0d9488}
.empty-state h2{font-size:18px;font-weight:600;color:#1e293b;margin-bottom:8px}
.empty-sub{font-size:13px;color:#94a3b8;margin-bottom:20px}
.preview-steps{display:flex;flex-direction:column;gap:12px;text-align:left;max-width:300px;margin:0 auto 16px}
.preview-step{display:flex;align-items:flex-start;gap:10px;animation:fadeUp .3s cubic-bezier(.4,0,.2,1) both}
.step-num{width:22px;height:22px;border-radius:50%;background:#e2e8f0;display:inline-flex;align-items:center;justify-content:center;font-size:12px;color:#94a3b8;flex-shrink:0;transition:all .2s}
.preview-step:hover .step-num{background:#0d9488;color:#fff}
.preview-step strong{font-size:14px;color:#334155}
.preview-step p{font-size:12px;color:#94a3b8;margin:2px 0 0}
.empty-time{font-size:12px;color:#94a3b8}

/* 加载 */
.loading-state{padding:16px}
.loading-state h3{font-size:16px;color:#1e293b;margin-bottom:20px}
.loading-steps{display:flex;flex-direction:column;gap:16px}
.loading-step{display:flex;align-items:center;gap:12px;transition:all .3s}
.loading-step.done .step-text{color:#0d9488}
.loading-step.active .step-text{color:#0d9488;font-weight:600}
.step-indicator{width:28px;height:28px;display:flex;align-items:center;justify-content:center}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:#0d9488;animation:pulse 1.2s ease infinite}
.pending-dot{width:8px;height:8px;border-radius:50%;background:#e2e8f0}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.5);opacity:.5}}
.step-text{font-size:14px;color:#64748b}

/* 结果 */
.panel-result.has-result{background:linear-gradient(180deg,rgba(13,148,136,.02) 0%,#fff 30%)}
.result-hero{display:flex;justify-content:space-between;align-items:flex-start;animation:fadeUp .4s cubic-bezier(.4,0,.2,1)}
.hs-label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em}
.hs-code{font-family:'JetBrains Mono',monospace;font-size:36px;font-weight:700;color:#1e293b;letter-spacing:3px;margin:4px 0}
.hs-desc{font-size:14px;color:#64748b;margin-top:4px}
.copy-btn{width:40px;height:40px;border-radius:10px;background:rgba(13,148,136,.06);border:1px solid #e2e8f0;color:#0d9488;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s}
.copy-btn:hover{background:rgba(13,148,136,.12)}
.confidence-bar{margin:20px 0}
.conf-label{display:flex;justify-content:space-between;font-size:13px;color:#64748b;margin-bottom:6px}
.conf-value{font-weight:600}
.conf-track{height:6px;border-radius:3px;background:#e2e8f0;overflow:hidden}
.conf-fill{height:100%;border-radius:3px;transition:width .8s cubic-bezier(.4,0,.2,1)}
.conf-fill.success{background:linear-gradient(90deg,#0d9488,#14b8a6)}
.conf-fill.warning{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.conf-fill.danger{background:linear-gradient(90deg,#ef4444,#f87171)}
.reasoning-collapse{margin-top:12px}
:deep(.reasoning-collapse .el-collapse-item__header){font-size:14px;font-weight:500;color:#334155}
.reasoning-list li{font-size:13px;color:#64748b;line-height:1.7;margin-bottom:6px;animation:fadeUp .3s cubic-bezier(.4,0,.2,1) both}
.citation-card{padding:10px 14px;border-radius:8px;background:rgba(13,148,136,.04);font-size:13px;color:#475569;margin-bottom:6px;animation:fadeUp .25s cubic-bezier(.4,0,.2,1) both}
.alt-title{font-size:13px;font-weight:600;color:#334155;margin-bottom:6px}
.alt-row{display:flex;align-items:center;gap:8px;font-size:13px;color:#64748b;margin-bottom:4px}
.alt-conf{color:#94a3b8;font-size:12px;margin-left:auto}
.result-actions{display:flex;gap:12px;margin-top:24px;padding-top:16px;border-top:1px solid #f1f5f9}
.manual-fix{display:flex;margin-top:12px}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
</style>
