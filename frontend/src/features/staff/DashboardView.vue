<template>
  <div class="dash">
    <header class="hd">
      <h1>📊 院校看板</h1>
      <p class="u-muted">{{ roleScope }} · 数据按你的权限范围聚合</p>
    </header>

    <!-- 买单价值：全校在变好 -->
    <AppCard class="trend-hero">
      <div class="th-left">
        <div class="th-label">本期全校竞争力</div>
        <div class="th-big" :class="impClass">
          {{ trends?.improvement_pct === null || trends?.improvement_pct === undefined
             ? '—' : (trends.improvement_pct >= 0 ? '↑ ' : '↓ ') + Math.abs(trends.improvement_pct) + '%' }}
        </div>
        <div class="th-sub u-muted">
          {{ trends?.available ? `覆盖 ${trends.cohort_size} 名学生 · 行动完成率 ${trends.action_completion.avg_pct}%` : '快照数据积累中' }}
        </div>
      </div>
      <div class="th-chart">
        <ChartCard v-if="trendOption" :option="trendOption" :height="160" />
        <EmptyState v-else icon="📈" text="学生多次评估后，这里出现全校竞争力/匹配分趋势" />
      </div>
    </AppCard>

    <!-- KPI -->
    <div class="kpis">
      <StatCard label="学生数" :value="overview?.student_count ?? '—'" />
      <StatCard label="已建画像" :value="overview?.with_portrait ?? '—'" />
      <StatCard label="平均完整度" :value="overview ? overview.avg_completeness + '%' : '—'" />
      <StatCard label="平均竞争力" :value="overview?.avg_competitiveness ?? '—'" />
      <StatCard label="已做匹配" :value="overview?.with_match ?? '—'" />
    </div>

    <div class="grid2">
      <AppCard>
        <SectionTitle title="竞争力分布" />
        <ChartCard v-if="distOption" :option="distOption" :height="240" />
        <EmptyState v-else text="暂无数据" />
      </AppCard>
      <AppCard>
        <SectionTitle title="技能缺口 Top" sub="全校最需要补的技能" />
        <ChartCard v-if="gapOption" :option="gapOption" :height="240" />
        <EmptyState v-else text="暂无匹配记录" />
      </AppCard>
    </div>

    <!-- 预警名单 -->
    <AppCard>
      <SectionTitle title="预警名单" :sub="`${atRisk.length} 人需要关注`" />
      <div v-if="atRisk.length" class="risk">
        <div v-for="r in atRisk" :key="r.student_id" class="risk-row">
          <span class="r-name">{{ r.name || '未命名' }}</span>
          <span class="r-score">竞争力 {{ r.competitiveness }}</span>
          <span class="r-reasons">
            <span v-for="re in r.reasons" :key="re" class="r-tag">{{ re }}</span>
          </span>
        </div>
      </div>
      <EmptyState v-else icon="✅" text="没有预警学生，状态良好" />
    </AppCard>

    <!-- 名册 -->
    <AppCard>
      <SectionTitle title="学生名册" :sub="`${roster.length} 人`" />
      <div class="table" v-if="roster.length">
        <div class="tr th">
          <span>姓名</span><span>完整度</span><span>竞争力</span><span>最佳匹配</span><span>意向</span>
        </div>
        <div class="tr" v-for="s in roster" :key="s.student_id">
          <span class="u-ellipsis">{{ s.name || '—' }}</span>
          <span>{{ s.completeness }}%</span>
          <span>{{ s.competitiveness }}</span>
          <span>{{ s.best_match ? s.best_match + '分 · ' + s.best_job : '—' }}</span>
          <span class="u-ellipsis">{{ s.career_intent || '—' }}</span>
        </div>
      </div>
      <EmptyState v-else text="范围内暂无学生" />
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
import { useSession } from '@/stores/session'
import {
  analyticsApi, type AnalyticsOverview, type TrendsResponse,
  type DistributionItem, type SkillGapItem, type AtRiskItem, type RosterItem,
} from '@/api/staff'

const session = useSession()
const roleScope = computed(() => session.role === 'admin' ? '全校（管理员）' : '我的班级（教师）')

const overview = ref<AnalyticsOverview | null>(null)
const trends = ref<TrendsResponse | null>(null)
const dist = ref<DistributionItem[]>([])
const gaps = ref<SkillGapItem[]>([])
const atRisk = ref<AtRiskItem[]>([])
const roster = ref<RosterItem[]>([])

const impClass = computed(() => {
  const v = trends.value?.improvement_pct
  return v === null || v === undefined ? '' : v >= 0 ? 'u-up' : 'u-down'
})

const trendOption = computed<EChartsOption | null>(() => {
  const comp = (trends.value?.competitiveness_series || []).map(p => [p.month, p.avg])
  const match = (trends.value?.match_series || []).map(p => [p.month, p.avg])
  if (!comp.length && !match.length) return null
  return {
    tooltip: { trigger: 'axis' }, legend: { data: ['竞争力', '匹配分'] },
    grid: { left: 36, right: 16, top: 30, bottom: 24 },
    xAxis: { type: 'category' }, yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      { name: '竞争力', type: 'line', smooth: true, data: comp, itemStyle: { color: '#8b5cf6' }, areaStyle: { opacity: 0.08 } },
      { name: '匹配分', type: 'line', smooth: true, data: match, itemStyle: { color: '#10b981' } },
    ],
  }
})

const distOption = computed<EChartsOption | null>(() => {
  if (!dist.value.length) return null
  return {
    tooltip: {}, grid: { left: 70, right: 20, top: 10, bottom: 24 },
    xAxis: { type: 'value' }, yAxis: { type: 'category', data: dist.value.map(d => d.label) },
    series: [{ type: 'bar', data: dist.value.map(d => d.count), itemStyle: { color: '#6d5efc', borderRadius: [0, 6, 6, 0] }, barWidth: 18 }],
  }
})

const gapOption = computed<EChartsOption | null>(() => {
  if (!gaps.value.length) return null
  const top = gaps.value.slice(0, 8).reverse()
  return {
    tooltip: {}, grid: { left: 80, right: 20, top: 10, bottom: 24 },
    xAxis: { type: 'value' }, yAxis: { type: 'category', data: top.map(g => g.skill) },
    series: [{ type: 'bar', data: top.map(g => g.count), itemStyle: { color: '#f59e0b', borderRadius: [0, 6, 6, 0] }, barWidth: 14 }],
  }
})

onMounted(async () => {
  const [o, t, d, g, r, ro] = await Promise.allSettled([
    analyticsApi.overview(), analyticsApi.trends(), analyticsApi.competitivenessDistribution(),
    analyticsApi.skillGaps(10), analyticsApi.atRisk(), analyticsApi.students(),
  ])
  if (o.status === 'fulfilled') overview.value = o.value
  if (t.status === 'fulfilled') trends.value = t.value
  if (d.status === 'fulfilled') dist.value = d.value.distribution
  if (g.status === 'fulfilled') gaps.value = g.value.skill_gaps
  if (r.status === 'fulfilled') atRisk.value = r.value.at_risk
  if (ro.status === 'fulfilled') roster.value = ro.value.students
})
</script>

<style scoped>
.dash { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.trend-hero { display: flex; gap: var(--sp-6); align-items: center; background: var(--grad-brand-soft); border: none; }
.th-left { flex-shrink: 0; min-width: 200px; }
.th-label { color: var(--c-text-2); font-size: var(--fz-3); }
.th-big { font-size: var(--fz-8); font-weight: 800; line-height: 1.1; margin: 6px 0; color: var(--c-text-3); }
.th-big.u-up { color: var(--c-growth); }
.th-big.u-down { color: var(--c-danger); }
.th-sub { font-size: var(--fz-2); }
.th-chart { flex: 1; min-width: 0; }
.kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--sp-3); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); }
.risk-row { display: grid; grid-template-columns: 1fr auto 2fr; gap: var(--sp-3); align-items: center;
  padding: 9px 0; border-bottom: 1px solid var(--c-border); font-size: var(--fz-3); }
.r-name { font-weight: 600; }
.r-score { color: var(--c-text-2); font-size: var(--fz-2); }
.r-tag { background: #fff0f0; color: var(--c-danger); border-radius: var(--r-sm); padding: 2px 8px; font-size: var(--fz-1); margin-right: 6px; }
.table { font-size: var(--fz-2); }
.tr { display: grid; grid-template-columns: 1.2fr 0.8fr 0.8fr 1.6fr 1.2fr; gap: var(--sp-2); padding: 9px 0; border-bottom: 1px solid var(--c-border); align-items: center; }
.tr.th { color: var(--c-text-3); font-weight: 700; border-bottom: 2px solid var(--c-border-2); }
@media (max-width: 860px) { .kpis { grid-template-columns: repeat(2, 1fr); } .grid2 { grid-template-columns: 1fr; } .trend-hero { flex-direction: column; align-items: stretch; } }
</style>
