<script setup lang="ts">
import { ref } from 'vue'
import { usePipelineStore } from '@/stores/pipeline'
import type { Commodity } from '@/types'

const store = usePipelineStore()

const form = ref<Commodity>({
  name: '',
  description: '',
  material: '',
  function: '',
  usage: '',
})

async function onSubmit() {
  await store.runClassify({ ...form.value })
}
</script>

<template>
  <div class="page">
    <h1>HS 编码归类</h1>

    <el-card class="form-card">
      <el-form :model="form" label-width="80px">
        <el-form-item label="商品名称" required>
          <el-input v-model="form.name" placeholder="如：蓝牙智能音箱" />
        </el-form-item>
        <el-form-item label="商品描述" required>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="详细描述商品的外观、材质、工作原理、用途等"
          />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="材质">
              <el-input v-model="form.material" placeholder="如：塑料、铝合金" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="功能">
              <el-input v-model="form.function" placeholder="如：音乐播放、语音助手" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="用途">
          <el-input v-model="form.usage" placeholder="如：家庭娱乐、办公" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="store.loading" @click="onSubmit">
            {{ store.loading ? '分析中...' : '开始归类' }}
          </el-button>
          <el-button @click="store.reset()">清空</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 错误提示 -->
    <el-alert
      v-if="store.hasErrors"
      type="error"
      :title="store.errors[0]?.message"
      closable
      show-icon
      style="margin-top: 16px"
    />

    <!-- 归类结果 -->
    <template v-if="store.hsResult">
      <el-card class="result-card">
        <template #header>
          <div class="result-header">
            <span>归类结果</span>
            <el-tag :type="store.hsResult.confidence >= 0.7 ? 'success' : 'warning'">
              置信度 {{ (store.hsResult.confidence * 100).toFixed(0) }}%
            </el-tag>
          </div>
        </template>

        <div class="hs-code">
          <span class="label">HS 编码</span>
          <span class="code">{{ store.hsResult.code }}</span>
        </div>
        <p class="desc">{{ store.hsResult.description }}</p>

        <el-divider />

        <h4>推理路径</h4>
        <ol class="reasoning">
          <li v-for="(step, i) in store.hsResult.reasoning_path" :key="i">{{ step }}</li>
        </ol>

        <template v-if="store.hsResult.citations.length">
          <h4 style="margin-top: 16px">条文溯源</h4>
          <ul class="citations">
            <li v-for="(cite, i) in store.hsResult.citations" :key="i">{{ cite }}</li>
          </ul>
        </template>

        <template v-if="store.hsResult.alternatives.length">
          <el-divider />
          <h4>备选编码</h4>
          <div v-for="alt in store.hsResult.alternatives" :key="alt.code" class="alt-item">
            <el-tag size="small">{{ alt.code }}</el-tag>
            {{ alt.description }}（置信度 {{ (alt.confidence * 100).toFixed(0) }}%）
          </div>
        </template>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}
h1 {
  margin-bottom: 20px;
}
.form-card {
  margin-bottom: 16px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hs-code {
  margin: 12px 0;
}
.hs-code .label {
  color: #909399;
  margin-right: 12px;
}
.hs-code .code {
  font-size: 32px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: 2px;
}
.desc {
  color: #606266;
  margin-bottom: 8px;
}
.reasoning li, .citations li {
  font-size: 13px;
  color: #606266;
  margin-bottom: 4px;
}
.alt-item {
  margin-bottom: 4px;
  font-size: 13px;
  color: #909399;
}
</style>
