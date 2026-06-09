<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { House, Search, Connection, DataAnalysis, Clock, Fold, Expand, Bell } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const menuItems = [
  { path: '/', label: '首页', icon: House },
  { path: '/classify', label: 'HS 归类', icon: Search },
  { path: '/pipeline', label: '一键全流程', icon: Connection },
  { path: '/dashboard', label: '风险看板', icon: DataAnalysis },
  { path: '/history', label: '历史记录', icon: Clock },
]
const breadcrumbs: Record<string, string> = {
  '/': '首页',
  '/classify': 'HS 编码归类',
  '/pipeline': '一键全流程',
  '/dashboard': '风险看板',
  '/history': '历史记录',
}
</script>

<template>
  <el-container style="height:100vh;overflow:hidden">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar" style="flex-shrink:0">
      <div class="logo" :class="{ collapsed }">
        <img src="/favicon.png" class="logo-img" :class="{ small: collapsed }" />
        <span class="logo-text" :style="{ opacity: collapsed ? 0 : 1 }">AgenticCustoms</span>
      </div>
      <el-menu :default-active="route.path" :collapse="collapsed" @select="(path: string) => router.push(path)">
        <el-tooltip v-for="item in menuItems" :key="item.path" :content="item.label" placement="right" :disabled="!collapsed">
          <el-menu-item :index="item.path"><el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span></el-menu-item>
        </el-tooltip>
      </el-menu>
      <div class="sidebar-footer" :class="{ collapsed }">
        <div class="version-info" v-show="!collapsed">
          <span class="breath-dot"></span><span>v1.0.0</span>
          <span class="sep">·</span><span class="powered">Agentic RAG</span>
        </div>
      </div>
      <div class="collapse-btn" @click="collapsed = !collapsed">
        <el-icon :size="14"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </div>
    </el-aside>

    <!-- 右侧主区域 -->
    <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <span class="breadcrumb">
            <template v-for="(label, path) in breadcrumbs" :key="path">
              <template v-if="route.path.startsWith(path)">
                <span v-if="path !== '/'" class="breadcrumb-sep">/</span>
                <span :class="{ active: route.path === path }">{{ label }}</span>
              </template>
            </template>
          </span>
        </div>
        <div class="topbar-right">
          <el-badge :value="3" :max="99" class="bell-badge">
            <el-icon :size="18" class="bell-icon"><Bell /></el-icon>
          </el-badge>
          <el-dropdown trigger="click">
            <span class="user-avatar">👤</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </main>
    </div>
  </el-container>
</template>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex; flex-direction: column;
  box-shadow: 1px 0 8px rgba(0,0,0,.15);
  overflow: hidden; position: relative;
  transition: width 0.25s cubic-bezier(0.4,0,0.2,1);
}
.logo {
  height: 56px; display: flex; align-items: center; gap: 10px;
  padding: 0 16px; border-bottom: 1px solid rgba(255,255,255,.06);
}
.logo.collapsed { justify-content: center; padding: 0; }
.logo.collapsed .logo-text { opacity: 0; max-width: 0; }
.logo-img { width: 28px; height: 28px; flex-shrink: 0; transition: all 0.25s; }
.logo-img.small { width: 24px; height: 24px; }
.logo-text { color: #fff; font-size: 15px; font-weight: 700; white-space: nowrap; letter-spacing: -.01em; }

:deep(.el-menu) { border-right: none; background: transparent; padding: 8px 0; overflow: hidden; white-space: nowrap; }
:deep(.el-menu-item) {
  margin: 2px 12px; border-radius: 8px; height: 40px; line-height: 40px;
  font-size: var(--font-size-sm); color: #94a3b8;
  position: relative; overflow: hidden;
  transition: color 0.2s, background 0.2s, margin 0.25s, padding 0.25s;
}
:deep(.el-menu--collapse .el-menu-item) {
  justify-content: center; padding-left: 0 !important; padding-right: 0 !important;
}
:deep(.el-menu-item .el-icon) {
  transition: transform 0.25s, margin 0.25s;
  flex-shrink: 0;
}
:deep(.el-menu-item span) {
  white-space: nowrap;
}
:deep(.el-menu-item .el-icon) { color: #64748b; transition: color 0.2s; }
:deep(.el-menu-item:hover) { color: #e2e8f0; background: rgba(255,255,255,.04); }
:deep(.el-menu-item:hover .el-icon) { color: #94a3b8; }
:deep(.el-menu-item.is-active) { color: #fff; background: var(--color-brand-600); border-radius: 8px; }
:deep(.el-menu-item.is-active .el-icon) { color: #fff; }
:deep(.el-menu-item.is-active::before) { display: none; }
:deep(.el-menu-item:not(.is-active):hover::after) {
  content: ''; position: absolute; left: 0; top: 30%;
  width: 2px; height: 40%; border-radius: 0 2px 2px 0; background: rgba(148,163,184,.3);
}

.sidebar-footer { padding: 12px 16px; margin-top: auto; border-top: 1px solid rgba(255,255,255,.04); }
.sidebar-footer.collapsed { padding: 8px; }
.sidebar-footer.collapsed .version-info { display: none; }
.version-info { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #475569; }
.breath-dot { width: 5px; height: 5px; border-radius: 50%; background: #0d9488; flex-shrink: 0; animation: breathe 3s ease-in-out infinite; }
@keyframes breathe { 0%,100%{opacity:.4} 50%{opacity:1} }
.sep { color: #334155; }
.powered { color: #475569; }
.collapse-btn { height: 36px; display: flex; align-items: center; justify-content: center; color: #475569; cursor: pointer; border-top: 1px solid rgba(255,255,255,.04); transition: color 0.2s, transform 0.25s; }
.collapse-btn:hover { color: #94a3b8; }
.collapse-btn .el-icon { transition: transform 0.25s; }
.collapse-btn:hover { color: #94a3b8; }

/* 顶部栏 */
.topbar {
  height: 56px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(226,232,240,0.6);
  flex-shrink: 0; z-index: 10;
}
.breadcrumb { font-size: 14px; color: #94a3b8; }
.breadcrumb-sep { margin: 0 6px; color: #cbd5e1; }
.breadcrumb .active { color: #1e293b; font-weight: 600; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.bell-icon { color: #64748b; cursor: pointer; transition: color 0.2s; }
.bell-icon:hover { color: #0d9488; }
.user-avatar { font-size: 22px; cursor: pointer; }

/* 主内容区 */
.main-content {
  flex: 1; overflow-y: auto; background: #f8fafc;
}

/* 页面切换动画 */
.page-fade-enter-active { transition: all 0.25s ease; }
.page-fade-leave-active { transition: all 0.15s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(8px); }
.page-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
