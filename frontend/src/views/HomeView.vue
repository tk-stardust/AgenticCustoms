<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Connection, DataAnalysis, Clock, ArrowRight, TrendCharts, Timer, Checked } from '@element-plus/icons-vue'
import { fetchStats } from '@/api/stats'

const router = useRouter()
const visible = ref(false)
const dbStats = ref({ total: 0, pass_rate: 100, warnings: 0, hs_codes: 0 })

const cards = computed(() => [
  { path:'/classify',  title:'HS 编码归类', desc:'输入商品描述，AI 自动推理最匹配的 HS 编码，附推理路径与条文溯源', icon:Search,      color:'teal',   tags:['RAG 检索','~17s'],      stat:`已收录 ${dbStats.value.hs_codes} 条 HS 编码`,     bg:'linear-gradient(135deg,rgba(13,148,136,.03),rgba(13,148,136,.01))' },
  { path:'/pipeline',  title:'一键全流程',   desc:'一次输入，同时完成归类、关税、合规、原产地分析，生成全套申报文件',   icon:Connection,  color:'indigo', tags:['多 Agent 协作','~60s'], stat:`合规通过率 ${dbStats.value.pass_rate}%`,          bg:'linear-gradient(135deg,rgba(79,70,229,.03),rgba(79,70,229,.01))' },
  { path:'/dashboard', title:'风险看板',     desc:'可视化展示申报国家分布、HS 章别统计，风险等级与合规趋势一目了然',     icon:DataAnalysis, color:'amber',  tags:['数据看板'],             stat:`当前 ${dbStats.value.warnings} 项风险预警待处理`,   bg:'linear-gradient(135deg,rgba(245,158,11,.03),rgba(245,158,11,.01))' },
  { path:'/history',   title:'历史记录',     desc:'查看过往申报记录，追溯每次合规分析的完整结果与校验详情',               icon:Clock,       color:'slate',  tags:['可追溯'],               stat:`共 ${dbStats.value.total} 条申报记录`,            bg:'linear-gradient(135deg,rgba(100,116,139,.03),rgba(100,116,139,.01))' },
])
const colorMap: Record<string,{bg:string;fg:string}> = {
  teal:{bg:'rgba(13,148,136,.1)',fg:'#0d9488'}, indigo:{bg:'rgba(79,70,229,.1)',fg:'#4f46e5'},
  amber:{bg:'rgba(245,158,11,.1)',fg:'#f59e0b'}, slate:{bg:'rgba(100,116,139,.1)',fg:'#64748b'},
}
const flowSteps = [
  { icon:'🔍', label:'HS 归类' }, { icon:'💰', label:'关税计算' },
  { icon:'🛡️', label:'合规校验' }, { icon:'📍', label:'原产地匹配' }, { icon:'📄', label:'申报文件' },
]

onMounted(async () => {
  requestAnimationFrame(() => visible.value = true)
  try { dbStats.value = await fetchStats() } catch { /* keep defaults */ }
})
</script>

<template>
  <div class="home">
    <div class="hero">
      <h1>跨境合规贸易智能申报平台</h1>
      <!-- 5步可视化流程 -->
      <div class="flow-steps">
        <template v-for="(s,i) in flowSteps" :key="i">
          <div class="flow-step">
            <div class="step-icon">{{ s.icon }}</div>
            <span class="step-label">{{ s.label }}</span>
          </div>
          <span v-if="i<flowSteps.length-1" class="step-arrow"><el-icon :size="16"><ArrowRight/></el-icon></span>
        </template>
      </div>
    </div>

    <div class="cards">
      <div v-for="(c,i) in cards" :key="c.path" class="card" :class="{visible}" :style="{background:c.bg,transitionDelay:`${i*0.1}s`}" @click="router.push(c.path)">
        <div class="card-line"><div class="card-line-sweep" :class="`sweep-${c.color}`"></div></div>
        <div class="card-top-row">
          <div class="card-icon" :style="{background:colorMap[c.color].bg,color:colorMap[c.color].fg}"><el-icon :size="24"><component :is="c.icon"/></el-icon></div>
          <span class="card-num">{{ c.stat.split(' ')[0] }} <small>{{ c.stat.split(' ').slice(1).join(' ') }}</small></span>
        </div>
        <h3>{{ c.title }}</h3>
        <p>{{ c.desc }}</p>
        <div class="card-tags">
          <span v-for="t in c.tags" :key="t" class="tag" :style="{background:colorMap[c.color].bg,color:colorMap[c.color].fg}">{{ t }}</span>
        </div>
      </div>
    </div>

    <!-- 底部统计卡片（实时数据） -->
    <div class="stat-cards">
      <div class="stat-card">
        <el-icon :size="20" color="#0d9488"><TrendCharts/></el-icon>
        <div><b>{{ dbStats.total }}</b>条</div><span>累计申报</span>
      </div>
      <div class="stat-card">
        <el-icon :size="20" color="#4f46e5"><Timer/></el-icon>
        <div><b>{{ dbStats.hs_codes }}</b>条</div><span>HS编码库</span>
      </div>
      <div class="stat-card">
        <el-icon :size="20" color="#22c55e"><Checked/></el-icon>
        <div><b>{{ dbStats.pass_rate }}%</b></div><span>合规通过率</span>
      </div>
    </div>
    <p class="copyright">© 2026 AgenticCustoms · 跨境合规贸易智能申报平台</p>
  </div>
</template>

<style scoped>
.home { padding: 32px 48px 48px; max-width: 960px; margin: 0 auto; }

.hero { text-align: center; margin-bottom: 40px; }
.hero h1 {
  font-size: var(--font-size-3xl); font-weight: 700; letter-spacing: -0.02em;
  background: linear-gradient(135deg,#0d9488,#115e59);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}

/* 5步流程 */
.flow-steps { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; }
.flow-step { display: flex; align-items: center; gap: 6px; }
.step-icon { width: 36px; height: 36px; border-radius: 50%; background: rgba(13,148,136,.08); display: flex; align-items: center; justify-content: center; font-size: 16px; }
.step-label { font-size: var(--font-size-sm); color: var(--color-gray-600); font-weight: 500; }
.step-arrow { color: var(--color-gray-300); }

.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media(max-width:768px){.cards{grid-template-columns:1fr}}

.card {
  position: relative; overflow: hidden; border: 1px solid var(--color-gray-200); border-radius: var(--radius-card);
  padding: 24px; cursor: pointer;
  box-shadow: var(--shadow-card);
  will-change: transform,opacity,box-shadow;
  opacity: 0; transform: translateY(20px);
  transition: opacity .6s var(--transition-normal),transform .6s var(--transition-normal),box-shadow .3s var(--transition-normal),border-color .3s var(--transition-normal);
}
.card.visible{opacity:1;transform:translateY(0)}
.card:hover{transform:translateY(-2px);border-color:var(--color-brand-600);box-shadow:var(--shadow-hover)}
.card-line{position:absolute;top:0;left:0;right:0;height:2px;background:var(--color-gray-200);overflow:hidden}
.card-line-sweep{position:absolute;top:0;left:0;width:0;height:100%;transition:width .4s var(--transition-normal)}
.card:hover .card-line-sweep{width:100%}
.sweep-teal{background:linear-gradient(90deg,transparent,#0d9488)}
.sweep-indigo{background:linear-gradient(90deg,transparent,#4f46e5)}
.sweep-amber{background:linear-gradient(90deg,transparent,#f59e0b)}
.sweep-slate{background:linear-gradient(90deg,transparent,#64748b)}

.card-top-row{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}
.card-icon{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.card-num{font-size:20px;font-weight:600;color:var(--color-gray-800);text-align:right}
.card-num small{display:block;font-size:var(--font-size-xs);color:var(--color-gray-400);font-weight:400}
.card h3{font-size:var(--font-size-xl);font-weight:600;color:var(--color-gray-800);margin-bottom:8px}
.card p{font-size:var(--font-size-base);color:var(--color-gray-500);line-height:1.6;margin-bottom:12px}
.card-tags{display:flex;gap:6px}
.tag{padding:3px 10px;border-radius:var(--radius-pill);font-size:var(--font-size-xs);font-weight:500}

/* 底部统计 */
.stat-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:40px}
.stat-card{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:4px;padding:16px;background:var(--color-white);border:1px solid var(--color-gray-200);border-radius:var(--radius-card);box-shadow:var(--shadow-sm)}
.stat-card b{font-size:var(--font-size-xl);font-weight:600}
.stat-card span{font-size:var(--font-size-xs);color:var(--color-gray-500)}
.copyright{text-align:center;margin-top:16px;font-size:var(--font-size-xs);color:var(--color-gray-400)}
</style>
