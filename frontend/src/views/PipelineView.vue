<script setup lang="ts">
import { usePipelineStore } from '@/stores/pipeline'

const store = usePipelineStore()
</script>

<template>
  <div class="page">
    <h1>一键全流程</h1>
    <p v-if="store.loading">处理中...</p>
    <!-- 待 Phase 3 实现完整流水线界面 -->
  </div>
</template>
