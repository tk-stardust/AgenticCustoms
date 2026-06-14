<script setup lang="ts">
import { usePipelineStore } from '@/stores/pipeline'
import { COUNTRY_NAMES } from '@/constants'

const store = usePipelineStore()
function cl(code: string) { return COUNTRY_NAMES[code] || code }
</script>

<template>
  <div class="a4-doc">
    <h2 class="a4-title">中华人民共和国海关出口货物报关单</h2>
    <div class="a4-meta">
      <span>预录入编号：{{ store.documents?.request_id || '—' }}</span>
      <span>海关编号：________</span>
      <span>申报日期：________</span>
    </div>
    <div class="a4-grid">
      <div class="a4-row"><label>出口口岸</label><span></span></div>
      <div class="a4-row"><label>运抵国（地区）</label><span>{{ cl(store.tariffResult?.country || '') || '—' }}</span></div>
      <div class="a4-row"><label>收发货人</label><span></span></div>
      <div class="a4-row"><label>生产销售单位</label><span></span></div>
      <div class="a4-row"><label>运输方式</label><span></span></div>
      <div class="a4-row"><label>运输工具名称</label><span></span></div>
      <div class="a4-row"><label>监管方式</label><span>一般贸易</span></div>
      <div class="a4-row"><label>征免性质</label><span>一般征税</span></div>
      <div class="a4-row"><label>成交方式</label><span></span></div>
      <div class="a4-row"><label>合同协议号</label><span></span></div>
      <div class="a4-row"><label>件数</label><span>{{ store.documents?.customs_declaration?.quantity || '—' }}</span></div>
      <div class="a4-row"><label>包装种类</label><span></span></div>
    </div>
    <table class="a4-table">
      <thead><tr><th>项号</th><th>商品名称</th><th>HS编码</th><th>数量及单位</th><th>单价</th><th>总价</th><th>币制</th><th>原产国</th><th>最终目的国</th><th>征免</th></tr></thead>
      <tbody><tr>
        <td>1</td>
        <td>{{ store.documents?.customs_declaration?.commodity_name || '—' }}</td>
        <td><code>{{ store.documents?.customs_declaration?.hs_code || '—' }}</code></td>
        <td>{{ store.documents?.customs_declaration?.quantity || '—' }}{{ store.documents?.customs_declaration?.unit || '件' }}</td>
        <td>{{ store.documents?.customs_declaration?.declared_value || '—' }}</td>
        <td>{{ store.documents?.customs_declaration?.declared_value || '—' }}</td>
        <td>USD</td>
        <td>{{ cl((store.documents?.customs_declaration?.origin as string) || 'CN') }}</td>
        <td>{{ cl(store.tariffResult?.country || '') || '—' }}</td>
        <td>照章征税</td>
      </tr></tbody>
    </table>
    <div class="a4-section">
      <h4>税费明细</h4>
      <div class="tax-summary">
        <span>综合税率：<b>{{ store.documents?.customs_declaration?.total_tax_rate || '—' }}%</b></span>
        <span>预估税费：<b>{{ store.documents?.customs_declaration?.total_tax_amount || '—' }} 元</b></span>
        <span v-if="store.tariffResult?.fta_applied">FTA：<b class="fta-badge">{{ store.tariffResult.fta_applied }}</b></span>
        <span v-if="store.tariffResult?.fta_saving">FTA节省：<b>{{ store.tariffResult.fta_saving }} 元</b></span>
      </div>
      <table class="a4-table">
        <tr><th>税项</th><th>税率</th><th>金额（元）</th><th>备注</th></tr>
        <tr v-for="(item, i) in ((store.documents?.customs_declaration?.tariff_items || []) as any[])" :key="i">
          <td>{{ item.name }}</td><td>{{ item.rate }}%</td><td>{{ item.amount }}</td><td>{{ item.note || '—' }}</td>
        </tr>
      </table>
      <p class="tax-disclaimer" style="font-size:11px;color:#94a3b8;margin-top:8px">税率数据仅供参考，具体以海关最新公告为准</p>
    </div>
    <p class="a4-footer">申报单位签章：________ &nbsp;&nbsp; 日期：________</p>
  </div>
</template>
