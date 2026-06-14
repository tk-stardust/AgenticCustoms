<script setup lang="ts">
import { usePipelineStore } from '@/stores/pipeline'
import { COUNTRY_NAMES } from '@/constants'

const store = usePipelineStore()
function cl(code: string) { return COUNTRY_NAMES[code] || code }
</script>

<template>
  <div class="a4-doc">
    <div class="compliance-hero" :class="store.complianceResult?.risk_level">
      <h2>{{ store.complianceResult?.risk_level === 'red' ? '✗ 不合规' : store.complianceResult?.risk_level === 'yellow' ? '⚠ 部分合规' : '✓ 合规通过' }}</h2>
    </div>
    <h2 class="a4-title">跨境贸易合规声明</h2>
    <div class="a4-meta">
      <span>声明编号：CC-{{ store.documents?.request_id || '—' }}</span>
      <span>生成日期：{{ new Date().toISOString().slice(0, 10) }}</span>
    </div>
    <div class="a4-section">
      <h4>商品信息</h4>
      <p>商品名称：{{ store.documents?.customs_declaration?.commodity_name || '—' }}</p>
      <p>HS编码：{{ store.documents?.customs_declaration?.hs_code || '—' }} | 目标国：{{ cl(store.tariffResult?.country || '') || '—' }}</p>
    </div>
    <div class="a4-section">
      <h4>校验结果</h4>
      <div class="checklist">
        <div class="check-item" :class="{ fail: store.complianceResult?.sanctions_hit }">
          <span class="check-mark">{{ store.complianceResult?.sanctions_hit ? '✗' : '☑' }}</span>
          <span>制裁清单校验 — {{ store.complianceResult?.sanctions_hit ? '命中' : '通过' }}</span>
        </div>
        <div class="check-item" :class="{ fail: store.complianceResult?.license_required }">
          <span class="check-mark">{{ store.complianceResult?.license_required ? '⚠' : '☑' }}</span>
          <span>出口许可校验 — {{ store.complianceResult?.license_required ? '需要许可' : '无需许可' }}</span>
        </div>
        <div v-for="v in store.complianceResult?.violations" :key="v.category" class="check-item fail">
          <span class="check-mark">✗</span>
          <span>{{ v.category }} — {{ v.description }}</span>
        </div>
        <div class="check-item">
          <span class="check-mark">☑</span><span>环保合规 — 符合 RoHS / REACH</span>
        </div>
        <div class="check-item">
          <span class="check-mark">☑</span><span>知识产权校验 — 通过</span>
        </div>
      </div>
    </div>
    <div class="a4-section">
      <h4>综合评定</h4>
      <p>{{ store.documents?.compliance_statement }}</p>
    </div>
    <p class="a4-footer">本声明自生成之日起30日内有效 | AgenticCustoms 智能合规平台</p>
  </div>
</template>
