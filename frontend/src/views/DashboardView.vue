<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchHistory, type HistoryRecord } from '@/api/history'
import { fetchStats, type DashboardStats } from '@/api/stats'

use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const router = useRouter()
const records = ref<HistoryRecord[]>([])
const stats = ref<DashboardStats>({ total: 0, pass_rate: 100, warnings: 0, hs_codes: 0, by_country: [], by_risk: [] })
const chartRecords = ref<HistoryRecord[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    stats.value = await fetchStats()
    const h = await fetchHistory(1, 50)
    chartRecords.value = h.items
    records.value = h.items.slice(0, 5)
  }
  finally { loading.value = false }
}

onMounted(loadData)

const pieOption = computed(() => ({
  title: { text: '申报国家分布', left: 'center', textStyle: { fontSize: 14, color: '#334155' } },
  tooltip: { trigger: 'item' as const },
  legend: { bottom: 0 },
  series: [{
    type: 'pie' as const, radius: ['45%', '72%'],
    data: stats.value.by_country?.length
      ? stats.value.by_country.map(d => ({ name: d.country, value: d.count }))
      : [
        { name: '🇺🇸 美国', value: 45, itemStyle: { color: '#3b82f6' } },
        { name: '🇪🇺 欧盟', value: 30, itemStyle: { color: '#8b5cf6' } },
        { name: '🇨🇳 中国', value: 15, itemStyle: { color: '#ef4444' } },
        { name: '🇻🇳 东盟', value: 10, itemStyle: { color: '#10b981' } },
      ],
    itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
  }],
}))

const barOption = computed(() => ({
  title: { text: 'HS 章别统计 Top5', left: 'center', textStyle: { fontSize: 14, color: '#334155' } },
  tooltip: {},
  xAxis: { type: 'category' as const, data: chartRecords.value.length
    ? Object.entries(chartRecords.value.reduce((acc:Record<string,number>,r)=>{const p=r.hs_code?.substring(0,2)||'—';acc[p]=(acc[p]||0)+1;return acc},{})).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([n])=>`第${n}章`)
    : ['84章(机械)', '85章(电子)', '62章(服装)', '94章(家具)', '87章(车辆)'],
    axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value' as const },
  series: [{ type: 'bar' as const, data: chartRecords.value.length
    ? Object.entries(chartRecords.value.reduce((acc:Record<string,number>,r)=>{const p=r.hs_code?.substring(0,2)||'—';acc[p]=(acc[p]||0)+1;return acc},{})).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([,v])=>v)
    : [32, 28, 15, 12, 8],
    itemStyle: { borderRadius: [4,4,0,0], color: '#0d9488' } }],
}))

// Risk table mock data — 类型对齐 HistoryRecord
const demoRecords: HistoryRecord[] = [
  { id:1, request_id:'demo1', commodity_name:'蓝牙智能音箱', hs_code:'851822', target_country:'US', status:'completed', created_at:'2026-06-06 14:30', results:{ cross_check_passed: true } },
  { id:2, request_id:'demo2', commodity_name:'棉制女式长裤', hs_code:'620462', target_country:'EU', status:'completed', created_at:'2026-06-06 11:15', results:{ cross_check_passed: false } },
  { id:3, request_id:'demo3', commodity_name:'木质餐桌套件', hs_code:'940360', target_country:'VN', status:'completed', created_at:'2026-06-05 16:42', results:{ cross_check_passed: true } },
  { id:4, request_id:'demo4', commodity_name:'锂离子电池组', hs_code:'850760', target_country:'US', status:'completed', created_at:'2026-06-05 09:20', results:{ cross_check_passed: false } },
]
function loadDemo() {
  demoMode.value = true
  stats.value = { total: 86, pass_rate: 93.0, warnings: 7, hs_codes: 28, by_country: [], by_risk: [] }
  records.value = demoRecords
  chartRecords.value = demoRecords
}
const demoMode = ref(false)
function goRiskHistory() {
  sessionStorage.setItem('historyFilter', 'risk')
  router.push('/history')
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>风险看板</h1>
      <span v-if="demoMode" style="font-size:12px;color:#f59e0b;cursor:pointer;margin-left:12px" @click="demoMode=false;loadData()">⚠ 示例数据 · 点击退出</span>
    </div>

    <div v-if="records.length===0 && !loading && !demoMode" class="empty-state">
      <div class="empty-icon">📊</div>
      <h2>暂无数据</h2>
      <p class="empty-sub">运行一键全流程后，风险数据将在此汇总分析</p>
      <button class="btn-primary" @click="router.push('/pipeline')">去一键全流程</button>
      <button class="btn-text" style="margin-top:12px" @click="loadDemo()">📋 加载示例数据</button>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-label">总申报次数</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-chg up">较上月 +12%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">合规通过率</div>
          <div class="stat-value">{{ stats.pass_rate }}%</div>
          <div class="progress-bar-sm"><div class="progress-fill-sm" :style="{ width: stats.pass_rate + '%' }"></div></div>
        </div>
        <div class="stat-card" style="cursor:pointer" @click="goRiskHistory()">
          <div class="stat-label">风险预警</div>
          <div class="stat-value">{{ stats.warnings }}</div>
          <el-tag type="danger" size="small" effect="dark">待处理</el-tag>
        </div>
        <div class="stat-card">
          <div class="stat-label">HS 编码库</div>
          <div class="stat-value">{{ stats.hs_codes }}</div>
          <div class="stat-chg down">已导入 485 条</div>
        </div>
      </div>

      <!-- 图表 -->
      <div class="charts-row">
        <div class="chart-box"><v-chart :option="pieOption" autoresize style="height:320px"/></div>
        <div class="chart-box"><v-chart :option="barOption" autoresize style="height:320px"/></div>
      </div>

      <!-- 风险列表 -->
      <div class="section-title">近期风险记录</div>
      <div class="table-wrap">
        <el-table :data="demoMode ? demoRecords : records" stripe style="width:100%">
          <el-table-column prop="commodity_name" label="商品名称" min-width="150"/>
          <el-table-column label="HS 编码" width="120">
            <template #default="{row}"><code>{{ row.hs_code }}</code></template>
          </el-table-column>
          <el-table-column label="目标国" width="100">
            <template #default="{row}"><el-tag size="small" round>{{ row.target_country }}</el-tag></template>
          </el-table-column>
          <el-table-column label="风险等级" width="120">
            <template #default="{row}">
              <el-tag :type="(row.results as any)?.cross_check_passed ? 'success' : 'danger'" size="small" effect="dark" round>
                {{ (row.results as any)?.cross_check_passed ? '🟢 低风险' : '🔴 高风险' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100"/>
          <el-table-column prop="created_at" label="时间" width="180"/>
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

/* 统计卡片 */
.stat-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.stat-label{font-size:12px;color:#94a3b8;margin-bottom:6px}
.stat-value{font-size:28px;font-weight:700;color:#1e293b}
.stat-chg{font-size:12px;margin-top:4px}
.stat-chg.up{color:#22c55e}
.stat-chg.down{color:#0d9488}
.progress-bar-sm{height:4px;border-radius:2px;background:#e2e8f0;margin-top:8px;overflow:hidden}
.progress-fill-sm{height:100%;border-radius:2px;background:linear-gradient(90deg,#0d9488,#14b8a6)}

/* 图表 */
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.chart-box{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}

.section-title{font-size:16px;font-weight:600;color:#1e293b;margin-bottom:12px}

.table-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}
:deep(.el-table th){background:#f8fafc;color:#475569;font-weight:600;font-size:13px}
:deep(.el-table tr:hover td){background:#f8fafc}
code{font-family:'JetBrains Mono',monospace;font-size:13px}
</style>
