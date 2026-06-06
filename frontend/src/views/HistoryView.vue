<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Download } from '@element-plus/icons-vue'
import { fetchHistory, type HistoryRecord } from '@/api/history'

const router = useRouter()
const allRecords = ref<HistoryRecord[]>([])
const loading = ref(false)
const search = ref('')
const filter = ref<'all'|'completed'|'pending'|'risk'>('all')

async function load() {
  loading.value = true
  try { const data = await fetchHistory(50); allRecords.value = data }
  finally { loading.value = false }
}

onMounted(load)

const filtered = computed(() => {
  let list = allRecords.value
  if (filter.value === 'completed') list = list.filter(r => r.status === 'completed')
  else if (filter.value === 'pending') list = list.filter(r => r.status === 'pending')
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(r => r.commodity_name?.toLowerCase().includes(q) || r.hs_code?.toLowerCase().includes(q))
  }
  return list
})

const statusMap: Record<string, { label: string; type: 'success'|'info'|'danger' }> = {
  completed: { label: '已完成', type: 'success' },
  pending: { label: '处理中', type: 'info' },
  failed: { label: '失败', type: 'danger' },
}

function statusType(r: HistoryRecord) { return statusMap[r.status]?.type || 'info' }
function statusLabel(r: HistoryRecord) { return statusMap[r.status]?.label || r.status }
</script>

<template>
  <div class="page-container">
    <div class="page-header"><h1>历史记录</h1></div>

    <!-- 空状态 -->
    <div v-if="allRecords.length===0 && !loading" class="empty-state">
      <div class="empty-icon">📋</div>
      <h2>暂无数据</h2>
      <p class="empty-sub">您还没有申报记录</p>
      <button class="btn-primary" @click="router.push('/classify')">开始首次申报</button>
    </div>

    <template v-else>
      <!-- 操作栏 -->
      <div class="toolbar">
        <el-input v-model="search" placeholder="搜索商品名称 / HS编码" :prefix-icon="Search"
          clearable style="width:280px" size="large" class="search-input"/>
        <div class="filter-tabs">
          <button v-for="f in [{k:'all',l:'全部'},{k:'completed',l:'已完成'},{k:'pending',l:'处理中'},{k:'risk',l:'有风险'}]"
            :key="f.k" class="filter-btn" :class="{active:filter===f.k}" @click="filter=f.k as any">{{ f.l }}</button>
        </div>
        <div class="toolbar-actions">
          <el-button :icon="Download" size="large" @click="load">导出</el-button>
          <el-button size="large" @click="load">刷新</el-button>
        </div>
      </div>

      <!-- 表格 -->
      <div class="table-wrap">
        <el-table :data="filtered" stripe v-loading="loading" style="width:100%">
          <el-table-column prop="commodity_name" label="商品名称" min-width="160"/>
          <el-table-column label="HS 编码" width="130">
            <template #default="{ row }"><code>{{ row.hs_code || '—' }}</code></template>
          </el-table-column>
          <el-table-column label="目标国" width="100">
            <template #default="{ row }"><el-tag size="small" round>{{ row.target_country }}</el-tag></template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row)" size="small" effect="dark" round>{{ statusLabel(row) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="180">
            <template #default="{ row }">
              <span class="cell-time">{{ row.created_at?.replace('T',' ').substring(0,19) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default>
              <el-button link type="primary" size="small" @click="router.push('/pipeline')">查看详情</el-button>
              <el-button link size="small" @click="load">重新运行</el-button>
              <el-button link size="small" class="btn-delete">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>
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
.table-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}
:deep(.el-table th){background:#f8fafc;color:#475569;font-weight:600;font-size:13px}
:deep(.el-table tr:hover td){background:#f8fafc}
code{font-family:'JetBrains Mono',monospace;font-size:13px}
.cell-time{font-size:12px;color:#94a3b8}
.btn-delete:hover{color:#ef4444 !important}
</style>
