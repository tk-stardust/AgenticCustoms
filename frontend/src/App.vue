<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { House, Search, Coin, Connection, DataAnalysis, Clock, Fold, Expand, ChatDotRound, Checked } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import ChatPanel from '@/components/ChatPanel.vue'

const router = useRouter()
const route = useRoute()
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/auth'

const auth = useAuthStore()
const collapsed = ref((() => { try { return localStorage.getItem('sidebar-collapsed') } catch { return null } })() === '1')
watch(collapsed, (v) => { try { localStorage.setItem('sidebar-collapsed', v ? '1' : '0') } catch { /* ok */ } })
const isGuest = computed(() => route.meta.guest === true)
const showPwdDialog = ref(false)
const pwdForm = ref({ old: '', newPwd: '', confirm: '' })
const pwdLoading = ref(false)

async function doChangePwd() {
  if (!pwdForm.value.old || !pwdForm.value.newPwd) { ElMessage.warning('请填写完整'); return }
  if (pwdForm.value.newPwd.length < 4) { ElMessage.warning('新密码至少 4 位'); return }
  if (pwdForm.value.newPwd !== pwdForm.value.confirm) { ElMessage.warning('两次密码不一致'); return }
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.value.old, pwdForm.value.newPwd)
    ElMessage.success('密码修改成功')
    showPwdDialog.value = false
    pwdForm.value = { old: '', newPwd: '', confirm: '' }
  } catch (e: any) { ElMessage.error(e?.message || '修改失败') }
  finally { pwdLoading.value = false }
}

function doLogout() {
  auth.logout()
  router.push('/login')
}
const chatDrawer = ref(false)

const menuItems = [
  { path: '/', label: '首页', icon: House },
  { path: '/classify', label: 'HS 归类', icon: Search },
  { path: '/tariff', label: '关税计算', icon: Coin },
  { path: '/compliance', label: '合规校验', icon: Checked },
  { path: '/pipeline', label: '一键全流程', icon: Connection },
  { path: '/dashboard', label: '风险看板', icon: DataAnalysis },
  { path: '/history', label: '历史记录', icon: Clock },
  { path: '/chat', label: 'AI 助手', icon: ChatDotRound },
]
const breadcrumbs: Record<string, string> = {
  '/': '首页',
  '/classify': 'HS 编码归类',
  '/tariff': '关税计算',
  '/compliance': '合规校验',
  '/pipeline': '一键全流程',
  '/dashboard': '风险看板',
  '/history': '历史记录',
  '/chat': 'AI 助手',
}
</script>

<template>
  <template v-if="isGuest">
    <router-view />
  </template>
  <template v-else>
  <el-container style="height:100vh;overflow:hidden">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar" :class="{ collapsed: collapsed }" style="flex-shrink:0">
      <div class="logo" :class="{ collapsed }">
        <img src="/favicon.png" class="logo-img" />
        <span class="logo-text">AgenticCustoms</span>
      </div>
      <el-menu :default-active="route.path" :collapse="false" @select="(path: string) => router.push(path)">
        <el-tooltip v-for="item in menuItems" :key="item.path" :content="item.label" placement="right" :disabled="!collapsed">
          <el-menu-item :index="item.path"><el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span></el-menu-item>
        </el-tooltip>
      </el-menu>
      <div class="sidebar-footer" :class="{ collapsed }">
        <div class="version-info">
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
          <el-dropdown trigger="click">
            <span class="user-avatar">{{ auth.username ? auth.username[0].toUpperCase() : '👤' }}</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ auth.username }}</el-dropdown-item>
                <el-dropdown-item @click="showPwdDialog = true">修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="doLogout">退出登录</el-dropdown-item>
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

  <!-- AI 对话悬浮按钮 + 抽屉 -->
  <div class="chat-float-btn" @click="chatDrawer = true">
    <el-icon :size="22"><ChatDotRound /></el-icon>
  </div>
  <el-drawer v-model="chatDrawer" title="AI 助手" direction="rtl" size="420" :z-index="200" :body-style="{ padding: 0 }">
    <ChatPanel />
  </el-drawer>

  <!-- 修改密码对话框 -->
  <el-dialog v-model="showPwdDialog" title="修改密码" width="380px" :close-on-click-modal="false">
    <el-form label-position="top" @submit.prevent="doChangePwd">
      <el-form-item label="原密码">
        <el-input v-model="pwdForm.old" type="password" show-password placeholder="请输入原密码" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="pwdForm.newPwd" type="password" show-password placeholder="至少 4 位" />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="再次输入" @keydown.enter="doChangePwd" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showPwdDialog = false">取消</el-button>
      <el-button type="primary" :loading="pwdLoading" @click="doChangePwd">确认修改</el-button>
    </template>
  </el-dialog>
  </template>
</template>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex; flex-direction: column;
  box-shadow: 1px 0 8px rgba(0,0,0,.15);
  overflow: hidden; position: relative;
  transition: width 0.25s cubic-bezier(0.4,0,0.2,1) !important;
}
.logo {
  height: 56px; display: flex; align-items: center; gap: 10px;
  padding: 0 18px; border-bottom: 1px solid rgba(255,255,255,.06);
  transition: padding 0.25s cubic-bezier(0.4,0,0.2,1);
}
.logo.collapsed { padding: 0 18px; }
.logo-img { width: 28px; height: 28px; flex-shrink: 0; transition: transform 0.25s cubic-bezier(0.4,0,0.2,1); }
.logo.collapsed .logo-img { transform: scale(1.1); }
.logo-text {
  color: #fff; font-size: 15px; font-weight: 700; white-space: nowrap; letter-spacing: -.01em;
  display: inline-block; overflow: hidden;
  width: 160px; opacity: 1; transform: translateX(0);
  transition: opacity 0.2s ease 0.05s, width 0.25s cubic-bezier(0.4,0,0.2,1), transform 0.25s cubic-bezier(0.4,0,0.2,1);
}
.logo.collapsed .logo-text { opacity: 0; width: 0; transform: translateX(-8px); }

:deep(.el-menu) { border-right: none; background: transparent; padding: 8px 0; overflow: hidden; white-space: nowrap; }
:deep(.el-menu-item) {
  margin: 2px 12px; border-radius: 8px; height: 40px; line-height: 40px;
  font-size: var(--font-size-sm); color: #94a3b8;
  position: relative; overflow: hidden;
  display: flex !important; align-items: center; justify-content: flex-start !important;
  padding: 0 12px !important;
  transition: color 0.2s, background 0.2s, margin 0.25s, padding 0.25s cubic-bezier(0.4,0,0.2,1);
}
.sidebar.collapsed :deep(.el-menu-item) {
  justify-content: flex-start !important;
  padding: 0 8px !important;
}
:deep(.el-menu-item .el-icon) {
  transition: transform 0.25s cubic-bezier(0.4,0,0.2,1), margin-right 0.25s cubic-bezier(0.4,0,0.2,1);
  flex-shrink: 0; min-width: 0;
}
.sidebar.collapsed :deep(.el-menu-item .el-icon) {
  transform: scale(1.2); margin-right: 0;
}
:deep(.el-menu-item span) {
  white-space: nowrap;
  display: inline-block; overflow: hidden;
  opacity: 1; width: 140px; transform: translateX(0);
  transition: opacity 0.2s ease 0.05s, width 0.25s cubic-bezier(0.4,0,0.2,1), transform 0.25s cubic-bezier(0.4,0,0.2,1);
}
.sidebar.collapsed :deep(.el-menu-item span) {
  visibility: visible; height: auto;
  opacity: 0; width: 0; transform: translateX(-10px);
}
:deep(.el-menu-item .el-icon) { color: #64748b; }
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
.version-info { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #475569; white-space: nowrap; overflow: hidden; opacity: 1; width: 140px; transition: opacity 0.2s ease, width 0.25s cubic-bezier(0.4,0,0.2,1); }
.sidebar-footer.collapsed .version-info { opacity: 0; width: 0; }
.breath-dot { width: 5px; height: 5px; border-radius: 50%; background: #0d9488; flex-shrink: 0; animation: breathe 3s ease-in-out infinite; }
@keyframes breathe { 0%,100%{opacity:.4} 50%{opacity:1} }
.sep { color: #334155; }
.powered { color: #475569; }
.collapse-btn { height: 36px; display: flex; align-items: center; justify-content: center; color: #64748b; cursor: pointer; border-top: 1px solid rgba(255,255,255,.04); transition: color 0.2s, transform 0.25s; }
.collapse-btn:hover { color: #fff; }
.collapse-btn .el-icon { transition: transform 0.25s; }

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
.user-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--color-brand-600); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: opacity 0.2s;
}
.user-avatar:hover { opacity: .85; }

/* 主内容区 */
.main-content {
  flex: 1; overflow-y: auto; background: #f8fafc;
}

/* 页面切换动画 */
.page-fade-enter-active { transition: all 0.25s ease; }
.page-fade-leave-active { transition: all 0.15s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(8px); }
.page-fade-leave-to { opacity: 0; transform: translateY(-4px); }

/* AI 悬浮按钮 */
.chat-float-btn {
  position: fixed; bottom: 28px; right: 28px; z-index: 150;
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--color-brand-600); color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; box-shadow: 0 4px 16px rgba(13,148,136,.35);
  transition: transform 0.2s, box-shadow 0.2s;
}
.chat-float-btn:hover { transform: scale(1.08); box-shadow: 0 6px 20px rgba(13,148,136,.45); }
</style>
