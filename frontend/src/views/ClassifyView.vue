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
    <el-form :model="form" label-width="80px">
      <el-form-item label="商品名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="商品描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="store.loading" @click="onSubmit">
          开始归类
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="store.hsResult" class="result">
      <p>HS 编码：{{ store.hsResult.code }}（置信度：{{ store.hsResult.confidence }}）</p>
    </div>
  </div>
</template>
