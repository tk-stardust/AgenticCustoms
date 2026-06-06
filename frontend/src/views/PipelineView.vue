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
const country = ref('US')

async function onSubmit() {
  await store.runPipeline({ ...form.value }, country.value)
}
</script>

<template>
  <div class="page">
    <h1>一键全流程</h1>

    <!-- 输入表单 -->
    <el-card class="section">
      <template #header>商品信息</template>
      <el-form :model="form" label-width="80px">
        <el-form-item label="商品名称" required>
          <el-input v-model="form.name" placeholder="如：蓝牙智能音箱" />
        </el-form-item>
        <el-form-item label="商品描述" required>
          <el-input v-model="form.description" type="textarea" :rows="3"
            placeholder="详细描述商品的外观、材质、工作原理、用途等" />
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
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用途">
              <el-input v-model="form.usage" placeholder="如：家庭娱乐" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标国">
              <el-select v-model="country">
                <el-option label="美国 (US)" value="US" />
                <el-option label="欧盟 (EU)" value="EU" />
                <el-option label="越南 (VN)" value="VN" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="store.loading" @click="onSubmit">
            {{ store.loading ? '全流程分析中（约40-60秒）...' : '开始全流程分析' }}
          </el-button>
          <el-button @click="store.reset()">清空</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 错误 -->
    <el-alert v-if="store.hasErrors" type="error" :title="store.errors[0]?.message"
      closable show-icon style="margin-bottom: 16px" />

    <!-- 结果 -->
    <template v-if="store.documents">
      <!-- 报关单 -->
      <el-card class="section">
        <template #header>
          <span>报关单草单</span>
          <el-tag v-if="store.documents.cross_check_passed" type="success" style="float:right">校验通过</el-tag>
          <el-tag v-else type="warning" style="float:right">校验未通过</el-tag>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="商品名称">{{ store.documents.customs_declaration?.commodity_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="HS 编码">{{ store.documents.customs_declaration?.hs_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="原产地">{{ store.documents.customs_declaration?.origin || '—' }}</el-descriptions-item>
          <el-descriptions-item label="综合税率">{{ store.documents.customs_declaration?.total_tax_rate || 0 }}%</el-descriptions-item>
          <el-descriptions-item label="数量">{{ store.documents.customs_declaration?.quantity || '—' }}</el-descriptions-item>
          <el-descriptions-item label="单位">{{ store.documents.customs_declaration?.unit || '—' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 原产地证书 -->
      <el-card class="section" v-if="store.documents.origin_certificate">
        <template #header>原产地证书申请书</template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="出口商">{{ store.documents.origin_certificate?.exporter || '待填写' }}</el-descriptions-item>
          <el-descriptions-item label="HS 编码">{{ store.documents.origin_certificate?.hs_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="原产地标准">{{ store.documents.origin_certificate?.origin_criteria || '—' }}</el-descriptions-item>
          <el-descriptions-item label="适用 FTA">{{ store.documents.origin_certificate?.fta || '—' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 合规声明 -->
      <el-card class="section">
        <template #header>合规声明</template>
        <p>{{ store.documents.compliance_statement }}</p>
      </el-card>

      <!-- 校验错误 -->
      <el-card class="section" v-if="store.documents.cross_check_errors?.length">
        <template #header>交叉校验警告</template>
        <el-alert v-for="(err, i) in store.documents.cross_check_errors" :key="i"
          type="warning" :title="err" show-icon style="margin-bottom: 8px" />
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}
h1 {
  margin-bottom: 20px;
}
.section {
  margin-bottom: 16px;
}
</style>
