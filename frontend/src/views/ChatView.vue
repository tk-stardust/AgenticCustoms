<script setup lang="ts">
import ChatPanel from '@/components/ChatPanel.vue'
</script>

<template>
  <div class="page-container">
    <div class="chat-wrapper">
      <ChatPanel />
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 24px 32px 32px; max-width: 900px; margin: 0 auto; height: calc(100vh - 56px); display: flex; flex-direction: column; }
.page-header { margin-bottom: 16px; flex-shrink: 0; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-gray-800); margin: 0 0 6px; }
.page-subtitle { font-size: 14px; color: var(--color-gray-500); margin: 0; }
.chat-wrapper { flex: 1; background: #fff; border-radius: 16px; border: 1px solid var(--color-gray-200); overflow: hidden; display: flex; flex-direction: column; }
</style>
