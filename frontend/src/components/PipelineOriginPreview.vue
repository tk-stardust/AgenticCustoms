<script setup lang="ts">
import { usePipelineStore } from '@/stores/pipeline'
import { COUNTRY_NAMES } from '@/constants'

const store = usePipelineStore()
function cl(code: string) { return COUNTRY_NAMES[code] || code }
</script>

<template>
  <div class="a4-doc">
    <h2 class="a4-title">原产地证书申请书</h2>
    <div class="a4-meta">
      <span>申请号：________</span>
      <span>发票号：________</span>
      <span>申请日期：________</span>
    </div>
    <div class="a4-grid">
      <div class="a4-row"><label>申请人</label><span></span></div>
      <div class="a4-row"><label>证书类型</label><span>{{ store.documents?.origin_certificate?.fta || '一般原产地证' }}</span></div>
      <div class="a4-row"><label>出口国</label><span>{{ cl('CN') }}</span></div>
      <div class="a4-row"><label>进口国</label><span>{{ cl(store.tariffResult?.country || (store.documents?.origin_certificate as any)?.destination_country) || '—' }}</span></div>
      <div class="a4-row"><label>HS编码</label><span><code>{{ store.documents?.origin_certificate?.hs_code || '—' }}</code></span></div>
      <div class="a4-row"><label>原产地标准</label><span>{{ store.documents?.origin_certificate?.origin_criteria || '—' }}</span></div>
      <div class="a4-row"><label>FOB总值（美元）</label><span>{{ store.documents?.customs_declaration?.declared_value || '—' }}</span></div>
      <div class="a4-row"><label>拟出运日期</label><span>________</span></div>
      <div class="a4-row"><label>数量/重量</label><span>{{ store.documents?.customs_declaration?.quantity || '—' }}{{ store.documents?.customs_declaration?.unit || '件' }}</span></div>
      <div class="a4-row"><label>是否含进口成分</label><span>否</span></div>
    </div>
    <div class="a4-section">
      <h4>适用 FTA</h4>
      <p>{{ store.tariffResult?.fta_applied || '无' }}</p>
    </div>
    <div class="a4-section" v-if="store.originResult">
      <h4>原产地分析</h4>
      <p>推荐原产地：<b>{{ cl(store.originResult?.recommended_origin || 'CN') }}</b></p>
      <p>满足条件：{{ store.originResult.meeting_criteria?.join('、') || '—' }}</p>
      <p v-if="store.originResult.rvc_percentage">区域价值成分：<b>{{ store.originResult.rvc_percentage }}%</b></p>
      <p>{{ store.originResult.note }}</p>
    </div>
    <p class="a4-footer">申请人签章：________ &nbsp;&nbsp; 日期：________</p>
  </div>
</template>
