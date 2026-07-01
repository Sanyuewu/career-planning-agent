<template>
  <div class="ov">
    <header class="hd"><h1>🌐 平台总览</h1><p class="u-muted">全平台跨校运营视角</p></header>

    <div class="kpis">
      <StatCard label="入驻学校" :value="totals?.tenants ?? '—'" />
      <StatCard label="学生总数" :value="totals?.students ?? '—'" />
      <StatCard label="生成报告" :value="totals?.reports ?? '—'" />
      <StatCard label="人岗匹配" :value="totals?.matches ?? '—'" />
    </div>

    <AppCard>
      <SectionTitle title="跨校对标" sub="各校平均竞争力" />
      <ChartCard v-if="benchOption" :option="benchOption" :height="280" />
      <EmptyState v-else text="暂无学校数据" />
    </AppCard>

    <AppCard>
      <SectionTitle title="学校排行" sub="按本期提升% 降序" />
      <div class="table" v-if="tenants.length">
        <div class="tr th"><span>学校</span><span>学生</span><span>教师</span><span>报告</span><span>均竞争力</span><span>提升%</span></div>
        <div class="tr" v-for="t in tenants" :key="t.id">
          <span class="u-ellipsis">{{ t.name }}</span>
          <span>{{ t.student_count }}</span>
          <span>{{ t.teacher_count }}</span>
          <span>{{ t.report_count }}</span>
          <span>{{ t.avg_competitiveness }}</span>
          <span :class="impClass(t.improvement_pct)">{{ t.improvement_pct === null ? '—' : (t.improvement_pct >= 0 ? '+' : '') + t.improvement_pct + '%' }}</span>
        </div>
      </div>
      <EmptyState v-else text="还没有学校入驻" />
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import AppCard from '@/design/components/AppCard.vue'
import StatCard from '@/design/components/StatCard.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import ChartCard from '@/design/components/ChartCard.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { platformApi, type PlatformTotals, type TenantStat } from '@/api/platform'

const totals = ref<PlatformTotals | null>(null)
const tenants = ref<TenantStat[]>([])

function impClass(v: number | null) { return v === null ? '' : v >= 0 ? 'u-up' : 'u-down' }

const benchOption = computed<EChartsOption | null>(() => {
  const withData = tenants.value.filter(t => t.avg_competitiveness > 0)
  if (!withData.length) return null
  return {
    tooltip: {}, grid: { left: 90, right: 24, top: 10, bottom: 24 },
    xAxis: { type: 'value', max: 100 },
    yAxis: { type: 'category', data: withData.map(t => t.name) },
    series: [{ type: 'bar', data: withData.map(t => t.avg_competitiveness), itemStyle: { color: '#6d5efc', borderRadius: [0, 6, 6, 0] }, barWidth: 16 }],
  }
})

onMounted(async () => {
  try {
    const o = await platformApi.overview()
    totals.value = o.totals
    tenants.value = o.tenants
  } catch { /* toasted */ }
})
</script>

<style scoped>
.ov { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--sp-4); }
.table { font-size: var(--fz-2); }
.tr { display: grid; grid-template-columns: 1.6fr 0.7fr 0.7fr 0.7fr 1fr 1fr; gap: var(--sp-2); padding: 9px 0; border-bottom: 1px solid var(--c-border); align-items: center; }
.tr.th { color: var(--c-text-3); font-weight: 700; border-bottom: 2px solid var(--c-border-2); }
@media (max-width: 720px) { .kpis { grid-template-columns: 1fr 1fr; } }
</style>
