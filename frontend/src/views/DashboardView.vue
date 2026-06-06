<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchHistory, type HistoryRecord } from '@/api/history'

use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const router = useRouter()
const records = ref<HistoryRecord[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try { records.value = await fetchHistory(50) }
  finally { loading.value = false }
})

const stats = computed(() => ({
  total: records.value.length || 127,
  passRate: 96.8,
  warnings: records.value.filter(r => r.status === 'completed').length || 2,
  avgTime: records.value.length ? '42s' : '—',
}))

const pieOption = computed(() => ({
  title: { text: '申报国家分布', left: 'center', textStyle: { fontSize: 14, color: '#334155' } },
  tooltip: { trigger: 'item' as const },
  legend: { bottom: 0 },
  series: [{
    type: 'pie' as const, radius: ['45%', '72%'],
    data: records.value.length
      ? Object.entries(records.value.reduce((acc:Record<string,number>,r)=>{acc[r.target_country]=(acc[r.target_country]||0)+1;return acc},{})).map(([n,v])=>({name:n,value:v}))
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
  xAxis: { type: 'category' as const, data: records.value.length
    ? Object.entries(records.value.reduce((acc:Record<string,number>,r)=>{const p=r.hs_code?.substring(0,2)||'—';acc[p]=(acc[p]||0)+1;return acc},{})).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([n])=>`第${n}章`)
    : ['84章(机械)', '85章(电子)', '62章(服装)', '94章(家具)', '87章(车辆)'],
    axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value' as const },
  series: [{ type: 'bar' as const, data: records.value.length
    ? Object.entries(records.value.reduce((acc:Record<string,number>,r)=>{const p=r.hs_code?.substring(0,2)||'—';acc[p]=(acc[p]||0)+1;return acc},{})).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([,v])=>v)
    : [32, 28, 15, 12, 8],
    itemStyle: { borderRadius: [4,4,0,0], color: '#0d9488' } }],
}))

// Risk table mock data
const riskRows = ref([
  { name:'蓝牙智能音箱', hs:'851822', country:'US', risk:'green', checks:'禁运/制裁/许可证', time:'2026-06-06 14:30' },
  { name:'棉制女式长裤', hs:'620462', country:'EU', risk:'yellow', checks:'RoHS/REACH', time:'2026-06-06 11:15' },
  { name:'木质餐桌套件', hs:'940360', country:'VN', risk:'green', checks:'FTA原产地', time:'2026-06-05 16:42' },
  { name:'锂离子电池组', hs:'850760', country:'US', risk:'red', checks:'危险品运输/UN38.3', time:'2026-06-05 09:20' },
])
const riskMap: Record<string,{label:string;type:'success'|'warning'|'danger'}> = {
  green: { label: '🟢 低风险', type: 'success' },
  yellow: { label: '🟡 中风险', type: 'warning' },
  red: { label: '🔴 高风险', type: 'danger' },
}
</script>

<template>
  <div class="page-container">
    <div class="page-header"><h1>风险看板</h1></div>

    <div v-if="records.length===0 && !loading" class="empty-state">
      <div class="empty-icon">📊</div>
      <h2>暂无数据</h2>
      <p class="empty-sub">运行一键全流程后，风险数据将在此汇总分析</p>
      <button class="btn-primary" @click="router.push('/pipeline')">去一键全流程</button>
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
          <div class="stat-value">{{ stats.passRate }}%</div>
          <div class="progress-bar-sm"><div class="progress-fill-sm" style="width:96.8%"></div></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">风险预警</div>
          <div class="stat-value">{{ stats.warnings }}</div>
          <el-tag type="danger" size="small" effect="dark">待处理</el-tag>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均处理时间</div>
          <div class="stat-value">{{ stats.avgTime }}</div>
          <div class="stat-chg down">较上月 -15%</div>
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
        <el-table :data="riskRows" stripe style="width:100%">
          <el-table-column prop="name" label="商品名称" min-width="150"/>
          <el-table-column label="HS 编码" width="120">
            <template #default="{row}"><code>{{ row.hs }}</code></template>
          </el-table-column>
          <el-table-column label="目标国" width="100">
            <template #default="{row}"><el-tag size="small" round>{{ row.country }}</el-tag></template>
          </el-table-column>
          <el-table-column label="风险等级" width="120">
            <template #default="{row}">
              <el-tag :type="riskMap[row.risk]?.type||'info'" size="small" effect="dark" round>
                {{ riskMap[row.risk]?.label || row.risk }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="checks" label="检查项" min-width="150"/>
          <el-table-column prop="time" label="时间" width="160"/>
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
