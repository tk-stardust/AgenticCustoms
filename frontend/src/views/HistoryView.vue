<script setup lang="ts">
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePipelineStore } from '@/stores/pipeline'
import client from '@/api/client'
import { fetchHistory, type HistoryRecord } from '@/api/history'

const router = useRouter()
const pipelineStore = usePipelineStore()
const allRecords = ref<HistoryRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const reportVisible = ref(false)
const previewType = ref<'customs' | 'origin' | 'compliance'>('customs')
const previewHtml = ref('')
const currentRequestId = ref('')

async function openPreview(row: HistoryRecord, type: 'customs' | 'origin' | 'compliance') {
  if (!row.request_id) return
  currentRequestId.value = row.request_id
  previewType.value = type
  previewHtml.value = ''
  reportVisible.value = true
  const { data } = await client.get(`/pipeline/report/${row.request_id}/${type}`)
  previewHtml.value = data as string
}
function downloadZip() {
  if (currentRequestId.value) window.open(`/api/pipeline/download/${currentRequestId.value}`, '_blank')
}
function downloadPdf() {
  if (currentRequestId.value) window.open(`/api/pipeline/pdf/${currentRequestId.value}/${previewType.value}`, '_blank')
}
async function deleteRecord(row: HistoryRecord) {
  try { await ElMessageBox.confirm(`确定删除「${row.commodity_name}」的申报记录？`, '确认删除', { type:'warning' }) }
  catch { return }
  await client.delete(`/history/${row.id}`)
  ElMessage.success('已删除')
  load()
}
function rerun(row: HistoryRecord) {
  pipelineStore.commodity = {
    name: row.commodity_name || '',
    description: row.commodity_description || '',
    material: '',
    function: '',
    usage: '',
  }
  pipelineStore.targetCountry = row.target_country || 'US'
  pipelineStore.autoRun = true
  router.push('/pipeline')
}
const loading = ref(false)
const search = ref('')
const filter = ref<'all'|'completed'|'failed'|'risk'>('all')
const jumpPage = ref('')
const tableScrollRef = ref<HTMLElement | null>(null)
const showBackTop = ref(false)
const searchInputRef = ref<any>(null)

function scrollToTop() {
  tableScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}
function onTableScroll() {
  showBackTop.value = (tableScrollRef.value?.scrollTop || 0) > 200
}

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const pageNumbers = computed(() => {
  const pages: (number | string)[] = []
  const tp = totalPages.value
  const cp = page.value
  if (tp <= 7) { for (let i = 1; i <= tp; i++) pages.push(i); return pages }
  pages.push(1)
  if (cp > 3) pages.push('...')
  const start = Math.max(2, cp - 1)
  const end = Math.min(tp - 1, cp + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (cp < tp - 2) pages.push('...')
  pages.push(tp)
  return pages
})

function goPage(p: number | string) {
  if (typeof p === 'string') return
  if (p < 1 || p > totalPages.value) return
  page.value = p
  load()
}
function jumpToPage() {
  const n = parseInt(jumpPage.value)
  if (n && n >= 1 && n <= totalPages.value) { goPage(n); jumpPage.value = '' }
}

async function load() {
  loading.value = true
  try {
    const data = await fetchHistory(page.value, pageSize.value, search.value, filter.value)
    allRecords.value = data.items
    total.value = data.total
  }
  finally { loading.value = false }
}

function onPageSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  load()
}

const FILTER_KEY = 'historyFilter'

function readStoredFilter() {
  const q = sessionStorage.getItem(FILTER_KEY)
  if (q === 'risk' || q === 'completed' || q === 'failed') { filter.value = q; load() }
  sessionStorage.removeItem(FILTER_KEY)
}

onMounted(() => { readStoredFilter(); load() })
// 筛选变化时重新加载 + 存 sessionStorage
watch([filter, search], () => {
  page.value = 1
  sessionStorage.setItem(FILTER_KEY, filter.value)
  load()
})
// keep-alive 切回来
onActivated(readStoredFilter)

const countryNames: Record<string, string> = { US: '🇺🇸 美国', EU: '🇪🇺 欧盟', VN: '🇻🇳 越南', CN: '🇨🇳 中国' }
const statusMap: Record<string, { label: string; type: 'success'|'info'|'danger' }> = {
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

const riskMap: Record<string, { label: string; type: 'success'|'warning'|'danger' }> = {
  green: { label: '低风险', type: 'success' },
  yellow: { label: '中风险', type: 'warning' },
  red: { label: '高风险', type: 'danger' },
}

function riskLevel(row: HistoryRecord): string {
  return (row.results as any)?.risk_level || ''
}
function riskLabel(row: HistoryRecord) { return riskMap[riskLevel(row)]?.label || '—' }
function riskType(row: HistoryRecord) { return riskMap[riskLevel(row)]?.type }

function onSearchClear() { setTimeout(() => searchInputRef.value?.focus(), 100) }
function statusType(r: HistoryRecord) { return statusMap[r.status]?.type || 'info' }
function statusLabel(r: HistoryRecord) { return statusMap[r.status]?.label || r.status }
</script>

<template>
  <div class="page-container">
    <div class="page-header"><h1>历史记录</h1></div>

    <!-- 操作栏（有数据或搜索中时显示） -->
    <div v-if="total > 0 || search || filter !== 'all'" class="toolbar">
      <el-input ref="searchInputRef" v-model="search" placeholder="搜索商品名称 / HS编码" :prefix-icon="Search"
        clearable style="width:280px" size="large" class="search-input"
        @clear="onSearchClear"/>
      <div class="filter-tabs">
        <button v-for="f in [{k:'all',l:'全部'},{k:'completed',l:'已完成'},{k:'failed',l:'失败'},{k:'risk',l:'有风险'}]"
          :key="f.k" class="filter-btn" :class="{active:filter===f.k}" @click="filter=f.k as any">{{ f.l }}</button>
      </div>
      <div class="toolbar-actions">
        <el-button size="large" @click="load">刷新</el-button>
      </div>
    </div>

    <!-- 空状态：数据库真的没数据 -->
    <div v-if="filter==='all' && total===0 && !loading" class="empty-state">
      <div class="empty-icon">📋</div>
      <h2>暂无数据</h2>
      <p class="empty-sub">您还没有申报记录</p>
      <button class="btn-primary" @click="router.push('/pipeline')">开始首次申报</button>
    </div>

    <!-- 有数据（或筛选后为空）时始终显示表格 + 分页器 -->
    <template v-if="filter!=='all' || total>0">
      <!-- 表格 -->
      <div class="table-wrap">
        <div class="table-scroll" ref="tableScrollRef" @scroll="onTableScroll">
          <el-table :data="allRecords" stripe v-loading="loading" style="width:100%" max-height="calc(100vh - 290px)">
            <el-table-column label="商品名称" min-width="120">
              <template #default="{ row }">
                <el-tooltip :content="row.commodity_name" placement="top" :show-after="400" :disabled="(row.commodity_name||'').length <= 12">
                  <span class="cell-name">{{ row.commodity_name }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column label="HS 编码" width="120">
              <template #default="{ row }"><code>{{ row.hs_code || '—' }}</code></template>
            </el-table-column>
            <el-table-column label="目标国" width="90">
              <template #default="{ row }"><el-tag size="small" round>{{ countryNames[row.target_country] || row.target_country }}</el-tag></template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag v-if="riskLevel(row)" :type="riskType(row)" size="small" effect="dark" round>{{ riskLabel(row) }}</el-tag>
                <span v-else class="cell-hint">—</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusType(row)" size="small" effect="dark" round>{{ statusLabel(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">
                <span class="cell-time">{{ row.created_at?.replace('T',' ').substring(0,16) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <div class="cell-actions">
                  <el-button link type="primary" size="small" v-if="row.status==='completed'" @click="openPreview(row, 'customs')">查看详情</el-button>
                  <span v-else class="cell-hint">—</span>
                  <el-button link size="small" type="info" @click="rerun(row)">重新运行</el-button>
                  <el-button link size="small" type="danger" @click="deleteRecord(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="history-pagination" v-if="total > 0">
          <div class="pagination-left">
            共 <b>{{ total }}</b> 条记录，第 <b>{{ page }}/{{ totalPages }}</b> 页
          </div>
          <div class="pagination-center">
            <button class="page-btn" :disabled="page === 1" @click="goPage(1)" title="首页">«</button>
            <button class="page-btn" :disabled="page === 1" @click="goPage(page - 1)" title="上一页">&lt;</button>
            <template v-for="p in pageNumbers" :key="p">
              <span v-if="p === '...'" class="page-ellipsis">...</span>
              <button v-else class="page-btn" :class="{ active: p === page }" @click="goPage(p)">{{ p }}</button>
            </template>
            <button class="page-btn" :disabled="page === totalPages" @click="goPage(page + 1)" title="下一页">&gt;</button>
            <button class="page-btn" :disabled="page === totalPages" @click="goPage(totalPages)" title="尾页">»</button>
          </div>
          <div class="pagination-right">
            <span class="size-label">每页</span>
            <el-select v-model="pageSize" @change="onPageSizeChange" size="small" class="size-select">
              <el-option :value="10" label="10 条"/>
              <el-option :value="20" label="20 条"/>
              <el-option :value="50" label="50 条"/>
              <el-option :value="100" label="100 条"/>
            </el-select>
            <span class="jump-label">前往</span>
            <el-input v-model="jumpPage" size="small" class="jump-input" placeholder="页码" @keydown.enter="jumpToPage"/>
            <span class="jump-label">页</span>
          </div>
        </div>
      </div>
    </template>
    <el-dialog v-model="reportVisible" :title="previewType==='customs'?'报关单草单':previewType==='origin'?'原产地证书申请书':'合规声明'" width="80vw" top="3vh" destroy-on-close>
      <div class="preview-tabs">
        <button :class="['preview-tab', {active:previewType==='customs'}]" @click="openPreview({request_id:currentRequestId} as any, 'customs')">📋 报关单</button>
        <button :class="['preview-tab', {active:previewType==='origin'}]" @click="openPreview({request_id:currentRequestId} as any, 'origin')">📜 原产地证</button>
        <button :class="['preview-tab', {active:previewType==='compliance'}]" @click="openPreview({request_id:currentRequestId} as any, 'compliance')">🛡️ 合规声明</button>
      </div>
      <iframe :srcdoc="previewHtml" style="width:100%;height:60vh;border:none;border-radius:8px;background:#fff;margin-top:12px"></iframe>
      <template #footer>
        <el-button type="primary" @click="downloadPdf()">📄 下载 PDF</el-button>
        <el-button type="success" @click="downloadZip">📥 下载 ZIP</el-button>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 回到顶部 -->
    <transition name="fade">
      <button v-if="showBackTop" class="back-top-btn" @click="scrollToTop" title="回到顶部">↑</button>
    </transition>

    <!-- 页脚 -->
    <div class="page-footer">© 2026 AgenticCustoms</div>
  </div>
</template>

<style scoped>
.page-header{margin-bottom:20px}
.page-header h1{font-size:24px;font-weight:700;color:#1e293b;letter-spacing:-0.02em}

/* 空状态 */
.empty-state{text-align:center;padding:64px 32px;background:radial-gradient(ellipse at center,rgba(13,148,136,.04) 0%,transparent 70%);border-radius:16px}
.empty-icon{font-size:48px;margin-bottom:16px}
.empty-state h2{font-size:18px;font-weight:600;color:#1e293b;margin-bottom:8px}
.empty-sub{font-size:14px;color:#64748b;margin-bottom:20px}
.btn-primary{display:inline-flex;align-items:center;padding:12px 28px;font-size:15px;font-weight:600;color:#fff;background:linear-gradient(135deg,#0d9488,#0f766e);border:none;border-radius:10px;cursor:pointer;transition:all .2s}
.btn-primary:hover{filter:brightness(1.08);box-shadow:0 4px 12px rgba(13,148,136,.3)}

/* 操作栏 */
.toolbar{display:flex;align-items:center;gap:16px;margin-bottom:16px;flex-wrap:wrap}
:deep(.search-input .el-input__wrapper){border-radius:10px;height:40px}
.filter-tabs{display:flex;gap:4px;background:#f1f5f9;padding:3px;border-radius:10px}
.filter-btn{padding:6px 16px;border:none;border-radius:8px;font-size:13px;color:#64748b;background:transparent;cursor:pointer;transition:all .2s}
.filter-btn.active{background:#fff;color:#0d9488;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.toolbar-actions{margin-left:auto;display:flex;gap:8px}

/* 表格 */
.page-container{padding-bottom:40px}
.table-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);display:flex;flex-direction:column}
.table-scroll :deep(.el-scrollbar__thumb){background:#cbd5e1 !important}
.table-scroll :deep(.el-scrollbar__thumb:hover){background:#94a3b8 !important}
:deep(.el-table th){background:#f8fafc;color:#475569;font-weight:600;font-size:13px}
:deep(.el-table tr:hover td){background:#f8fafc}
code{font-family:'JetBrains Mono',monospace;font-size:13px}
.cell-time{font-size:12px;color:#94a3b8}
.cell-name{display:block;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cell-actions{display:flex;align-items:center;white-space:nowrap}
.cell-actions :deep(.el-button){padding:4px 6px;border-radius:6px;transition:all .2s}
.cell-actions :deep(.el-button--primary:hover){background:#0d9488;color:#fff}
.cell-actions :deep(.el-button--info:hover){background:#64748b;color:#fff}
.cell-actions :deep(.el-button--danger:hover){background:#ef4444;color:#fff}
.cell-hint{font-size:12px;color:#94a3b8}

/* ===== 自定义分页器 ===== */
.history-pagination {
  display: flex; align-items: center; justify-content: center; gap: 32px;
  position: sticky; bottom: 0; z-index: 10;
  background: rgba(255,255,255,.9); backdrop-filter: blur(8px);
  border-top: 1px solid #e2e8f0;
  box-shadow: 0 -4px 12px rgba(0,0,0,.04);
  padding: 12px 24px;
}
.pagination-left { font-size: 14px; color: #64748b; }
.pagination-left b { color: #1e293b; font-weight: 600; }

.pagination-center { display: flex; align-items: center; gap: 4px; }
.page-btn {
  width: 36px; height: 36px; border-radius: 8px; border: 1px solid #e2e8f0;
  background: #fff; color: #64748b; font-size: 14px; font-weight: 500;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: all .15s; line-height: 1;
}
.page-btn:hover:not(:disabled):not(.active) { background: #f8fafc; color: #1e293b; }
.page-btn.active { background: #0d9488; color: #fff; border-color: #0d9488; }
.page-btn:disabled { opacity: .35; cursor: not-allowed; }
.page-ellipsis { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 13px; }

.pagination-right { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #64748b; }
.size-select { width: 100px; }
.size-select :deep(.el-input__wrapper) { border-radius: 8px; height: 36px; border-color: #e2e8f0; box-shadow: none; }
.jump-input { width: 60px; }
.jump-input :deep(.el-input__wrapper) { border-radius: 6px; height: 36px; border-color: #e2e8f0; box-shadow: none; padding: 0 8px; }
.jump-input :deep(.el-input__inner) { font-size: 13px; }
.jump-label { font-size: 13px; color: #64748b; }

/* ===== 回到顶部 ===== */
.back-top-btn {
  position: fixed; right: 24px; bottom: 80px; z-index: 50;
  width: 40px; height: 40px; border-radius: 50%;
  background: #fff; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,.08);
  color: #0d9488; font-size: 18px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .2s;
}
.back-top-btn:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); transform: translateY(-2px); }
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ===== 预览弹窗 ===== */
.preview-tabs { display: flex; gap: 4px; background: #f1f5f9; padding: 3px; border-radius: 10px; }
.preview-tab { padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; color: #64748b; background: transparent; cursor: pointer; transition: all .2s; }
.preview-tab.active { background: #fff; color: #0d9488; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.06); }

/* ===== 页脚 ===== */
.page-footer { text-align: center; padding: 16px; font-size: 12px; color: #94a3b8; }
</style>
