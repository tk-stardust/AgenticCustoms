<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Connection, DataAnalysis, Clock, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const visible = ref(false)
onMounted(() => requestAnimationFrame(() => visible.value = true))

const cards = [
  { path:'/classify',  title:'HS 编码归类', desc:'输入商品描述，AI 自动推理最匹配的 HS 编码，附推理路径与条文溯源', icon:Search,     color:'teal',   tags:['RAG 检索','~17s'],      stat:'本月已智能归类 1,247 件' },
  { path:'/pipeline',  title:'一键全流程',   desc:'一次输入，同时完成归类、关税、合规、原产地分析，生成全套申报文件',   icon:Connection, color:'indigo', tags:['多 Agent 协作','~60s'], stat:'平均节省申报时间 42 分钟' },
  { path:'/dashboard', title:'风险看板',     desc:'可视化展示申报国家分布、HS 章别统计，风险等级与合规趋势一目了然',     icon:DataAnalysis,color:'amber',  tags:['数据看板'],             stat:'当前待处理风险预警 3 项' },
  { path:'/history',   title:'历史记录',     desc:'查看过往申报记录，追溯每次合规分析的完整结果与校验详情',               icon:Clock,      color:'slate',  tags:['可追溯'],               stat:'共 86 条申报记录' },
]
const colorMap: Record<string,{bg:string;fg:string}> = {
  teal:{bg:'rgba(13,148,136,.1)',fg:'#0d9488'}, indigo:{bg:'rgba(79,70,229,.1)',fg:'#4f46e5'},
  amber:{bg:'rgba(245,158,11,.1)',fg:'#f59e0b'}, slate:{bg:'rgba(100,116,139,.1)',fg:'#64748b'},
}
</script>

<template>
  <div class="home">
    <div class="hero">
      <h1>跨境合规贸易智能申报平台</h1>
      <p class="sub">
        基于 Agentic RAG 与多智能体协作，AI 辅助完成
        <strong>HS 归类</strong><span class="arrow">→</span>
        <strong>关税计算</strong><span class="arrow">→</span>
        <strong>合规校验</strong><span class="arrow">→</span>
        <strong>原产地匹配</strong><span class="arrow">→</span>
        <strong>申报文件</strong>
      </p>
    </div>

    <div class="cards">
      <div v-for="(c,i) in cards" :key="c.path" class="card" :class="{ visible }"
        :style="{ transitionDelay: `${i*0.1}s` }" @click="router.push(c.path)">
        <div class="card-line"><div class="card-line-sweep" :class="`sweep-${c.color}`"></div></div>
        <div class="card-icon" :style="{background:colorMap[c.color].bg,color:colorMap[c.color].fg}">
          <el-icon :size="24"><component :is="c.icon"/></el-icon>
        </div>
        <h3>{{ c.title }}</h3>
        <p>{{ c.desc }}</p>
        <div class="card-tags">
          <span v-for="t in c.tags" :key="t" class="tag"
            :style="{background:colorMap[c.color].bg,color:colorMap[c.color].fg}">{{ t }}</span>
        </div>
        <div class="card-stat"><span>{{ c.stat }}</span><el-icon :size="12"><ArrowRight/></el-icon></div>
      </div>
    </div>

    <div class="footer-stats">
      <span>今日归类 <strong>12</strong> 件</span><span class="dot">·</span>
      <span>本月节省 <strong>340</strong> 分钟</span><span class="dot">·</span>
      <span>合规率 <strong>99.2%</strong></span>
    </div>
    <p class="copyright">© 2026 AgenticCustoms · 跨境合规贸易智能申报平台</p>
  </div>
</template>

<style scoped>
.home { padding: 32px 48px 48px; max-width: 960px; margin: 0 auto; }
.hero { text-align: center; margin-bottom: 48px; }
.hero h1 {
  font-size: 28px; font-weight: 700; letter-spacing: -0.02em; white-space: nowrap;
  background: linear-gradient(135deg,#0d9488,#115e59);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.sub { margin-top:12px; font-size:14px; color:#64748b; line-height:1.8; }
.sub strong { color:#0d9488; font-weight:600; }
.sub .arrow { color:#94a3b8; margin:0 4px; }

.cards { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
@media(max-width:768px){.cards{grid-template-columns:1fr}}

.card {
  position:relative;overflow:hidden; background:#fff; border:1px solid #e2e8f0; border-radius:12px;
  padding:24px; cursor:pointer;
  box-shadow:0 1px 3px rgba(0,0,0,.05),0 1px 2px rgba(0,0,0,.03);
  will-change:transform,opacity,box-shadow;
  opacity:0;transform:translateY(20px);
  transition:opacity .6s cubic-bezier(.4,0,.2,1),transform .6s cubic-bezier(.4,0,.2,1),box-shadow .3s cubic-bezier(.4,0,.2,1),border-color .3s cubic-bezier(.4,0,.2,1);
}
.card.visible{opacity:1;transform:translateY(0)}
.card:hover{transform:translateY(-4px);border-color:#0d9488;box-shadow:0 10px 25px -5px rgba(0,0,0,.08),0 8px 10px -6px rgba(0,0,0,.02),0 0 0 3px rgba(13,148,136,.1)}
.card-line{position:absolute;top:0;left:0;right:0;height:2px;background:#e2e8f0;overflow:hidden}
.card-line-sweep{position:absolute;top:0;left:0;width:0;height:100%;transition:width .4s cubic-bezier(.4,0,.2,1)}
.card:hover .card-line-sweep{width:100%}
.sweep-teal{background:linear-gradient(90deg,transparent,#0d9488)}
.sweep-indigo{background:linear-gradient(90deg,transparent,#4f46e5)}
.sweep-amber{background:linear-gradient(90deg,transparent,#f59e0b)}
.sweep-slate{background:linear-gradient(90deg,transparent,#64748b)}
.card-icon{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;margin-bottom:16px}
.card h3{font-size:18px;font-weight:600;color:#1e293b;margin-bottom:8px}
.card p{font-size:14px;color:#64748b;line-height:1.6;margin-bottom:16px}
.card-tags{display:flex;gap:8px;margin-bottom:12px}
.tag{padding:3px 10px;border-radius:9999px;font-size:12px;font-weight:500}
.card-stat{display:flex;align-items:center;gap:4px;font-size:12px;color:#94a3b8;transition:color .2s}
.card:hover .card-stat{color:#64748b}

.footer-stats{text-align:center;margin-top:48px;font-size:13px;color:#94a3b8}
.footer-stats strong{color:#475569;font-weight:600}
.dot{margin:0 8px;color:#cbd5e1}
.copyright{text-align:center;margin-top:8px;font-size:12px;color:#cbd5e1}
</style>
