<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

defineProps<{
  agent: { icon: string; name: string; desc: string }
  state: 'idle' | 'done' | 'running' | 'pending'
  color: 'blue' | 'yellow' | 'green' | 'purple' | 'gray'
  log?: string
  index: number
}>()
</script>

<template>
  <div class="agent-card live" :class="[state, `color-${color}`]">
    <div class="agent-top-bar" v-if="state !== 'idle'" :class="`bar-${color}`"></div>
    <div class="agent-icon" :class="`icon-${color}`">
      {{ state === 'done' ? '✅' : state === 'running' ? '🔄' : agent.icon }}
    </div>
    <div class="agent-info">
      <strong>{{ agent.name }}</strong>
      <p>{{ log || agent.desc }}</p>
    </div>
    <el-tag v-if="state === 'done'" size="small" type="success" round>已完成</el-tag>
    <el-tag v-else-if="state === 'running'" size="small" class="tag-running" round>
      <el-icon :size="12" style="margin-right:4px"><Loading /></el-icon>处理中
    </el-tag>
    <el-tag v-else size="small" round class="tag-idle">等待中</el-tag>
  </div>
</template>

<style>
.agent-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; border-radius: 12px; background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  will-change: transform, opacity;
  opacity: 1; animation: agentFadeUp 0.35s cubic-bezier(0.4,0,0.2,1) both;
}
.agent-card:hover { transform: translateY(-1px); }
.agent-card.live { position: relative; overflow: hidden; }
.agent-card.running { background: #fff; border-color: #0d9488; box-shadow: 0 4px 12px rgba(13,148,136,.08); }
.agent-card.done { background: #fff; border-color: #e2e8f0; opacity: .85; }
.agent-top-bar { position: absolute; top: 0; left: 0; height: 2px; background: #0d9488; animation: agentBarSweep 0.5s cubic-bezier(0.4,0,0.2,1) both; }
@keyframes agentBarSweep { from { width: 0; } to { width: 100%; } }
@keyframes agentFadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.agent-icon { font-size: 22px; flex-shrink: 0; display: flex; align-items: center; }
.agent-card.running .agent-icon { animation: agentBounce 1s ease infinite; }
@keyframes agentBounce { 0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)} }
.agent-info { flex: 1; }
.agent-info strong { font-size: 14px; color: #1e293b; }
.agent-info p { font-size: 12px; color: #94a3b8; margin: 2px 0 0; }
.agent-card.running .agent-info p { color: #0d9488; font-weight: 500; }
.tag-idle { background: var(--color-gray-100) !important; color: var(--color-gray-500) !important; border-color: var(--color-gray-200) !important; }
.tag-running { display: inline-flex; align-items: center; background: rgba(59,130,246,.1) !important; color: #3b82f6 !important; border-color: transparent !important; }
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
</style>
