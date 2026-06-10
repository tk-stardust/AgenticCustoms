<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.value.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (form.value.username.trim().length < 2) {
    ElMessage.warning('用户名至少 2 个字符')
    return
  }
  if (!form.value.password) {
    ElMessage.warning('请输入密码')
    return
  }
  if (form.value.password.length < 4) {
    ElMessage.warning('密码至少 4 位')
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>AgenticCustoms</h1>
      <p class="auth-subtitle">跨境合规贸易智能申报平台</p>
      <el-form label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" maxlength="50" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password @keydown.enter="onSubmit" />
        </el-form-item>
        <button type="submit" class="auth-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </el-form>
      <p class="auth-link">没有账号？<router-link to="/register">去注册</router-link></p>
    </div>
  </div>
</template>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #f1f5f9; }
.auth-card { background: #fff; padding: 40px; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.08); width: 400px; max-width: 90vw; }
.auth-card h1 { font-size: 22px; font-weight: 700; color: var(--color-brand-600); text-align: center; margin: 0 0 4px; }
.auth-subtitle { font-size: 13px; color: var(--color-gray-500); text-align: center; margin: 0 0 28px; }
.auth-btn {
  width: 100%; padding: 12px; border: none; border-radius: 8px;
  background: var(--color-brand-600); color: #fff;
  font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s;
}
.auth-btn:hover:not(:disabled) { background: var(--color-brand-700); }
.auth-btn:disabled { opacity: .6; cursor: not-allowed; }
.auth-link { text-align: center; font-size: 13px; color: var(--color-gray-500); margin: 16px 0 0; }
.auth-link a { color: var(--color-brand-600); text-decoration: none; }
.auth-link a:hover { text-decoration: underline; }
</style>
