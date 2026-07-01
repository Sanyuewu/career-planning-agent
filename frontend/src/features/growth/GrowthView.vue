<template>
  <div class="growth">
    <header class="hd">
      <h1>📈 我的成长</h1>
      <p class="u-muted">画像 → 差距 → 行动 → 进步：看见自己在变好</p>
    </header>

    <div v-if="!studentId" class="empty">
      <EmptyState text="请先上传简历，开启成长追踪">
        <AppButton @click="$router.push('/journey/upload')">去上传</AppButton>
      </EmptyState>
    </div>

    <template v-else>
      <!-- KPI -->
      <div class="kpis">
        <StatCard label="竞争力" :value="latestComp ?? '—'" :delta="trend?.competitiveness_delta ?? null"
          :delta-text="fmtDelta(trend?.competitiveness_delta)" />
        <StatCard label="目标匹配" :value="matchProgress?.curr_total ?? bestMatch ?? '—'" unit="分">
          <template #delta>
            <span v-if="matchProgress?.available" :class="deltaClass(matchProgress?.total_delta)">
              上次 {{ matchProgress?.prev_total }} → 这次 {{ matchProgress?.curr_total }}（{{ fmtDelta(matchProgress?.total_delta) }}）
            </span>
            <span v-else class="u-faint">首次评估</span>
          </template>
        </StatCard>
        <StatCard label="行动完成率" :value="actions?.available ? actions.completion_pct + '%' : '—'">
          <template #delta>
            <span v-if="!actions?.available" class="u-faint">暂无计划</span>
            <span v-else>
              <span class="u-faint">{{ actions.done }}/{{ actions.total }} 项</span>
              <span v-if="(actions.overdue || 0) > 0" class="u-down"> · {{ actions.overdue }} 逾期</span>
            </span>
          </template>
        </StatCard>
      </div>

      <!-- 曲线 -->
      <AppCard>
        <SectionTitle title="成长曲线">
          <template #action><AppButton size="sm" variant="ghost" :loading="loading" @click="load">刷新</AppButton></template>
        </SectionTitle>
        <ChartCard v-if="curveOption" :option="curveOption" :height="280" />
        <EmptyState v-else text="做一次人岗匹配后，这里会出现你的竞争力/匹配分变化曲线" />
      </AppCard>

      <!-- 成长归因 -->
      <AppCard v-if="growth?.available && growth.drivers?.length">
        <SectionTitle title="成长来自哪里" />
        <ul class="drivers">
          <li v-for="(d, i) in growth.drivers" :key="i">✅ {{ d }}</li>
        </ul>
      </AppCard>

      <!-- 行动清单 -->
      <AppCard>
        <SectionTitle title="行动计划">
          <template #action>
            <AppButton size="sm" :loading="reEval" :disabled="!targetJob" @click="reEvaluate">完成后重新评估</AppButton>
          </template>
        </SectionTitle>
        <div v-if="items.length">
          <label v-for="it in items" :key="it.id" class="item" :class="{ done: it.status === 'done' }">
            <input type="checkbox" :checked="it.status === 'done'"
              :disabled="it.status === 'done' || completing === it.id" @change="complete(it)" />
            <span class="it-title">{{ it.title }}</span>
            <span v-if="it.timeline" class="it-time u-faint">{{ it.timeline }}</span>
          </label>
          <p v-if="targetJob" class="hint u-faint">勾选完成后点「重新评估」，会重测「{{ targetJob }}」，看看匹配分涨了多少。</p>
        </div>
        <EmptyState v-else text="生成一份职业报告后，行动计划会出现在这里">
          <AppButton variant="soft" @click="$router.push('/journey/report')">去生成报告</AppButton>
        </EmptyState>
      </AppCard>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import StatCard from '@/design/components/StatCard.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import ChartCard from '@/design/components/ChartCard.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { progressApi, type ProgressTrend, type GrowthAttribution, type MatchProgress, type ActionCompletion, type ActionItem } from '@/api/progress'
import { matchApi } from '@/api/match'
import { useSession } from '@/stores/session'

const session = useSession()
const studentId = computed(() => session.studentId)

const loading = ref(false)
const reEval = ref(false)
const completing = ref<string | null>(null)

const trend = ref<ProgressTrend | null>(null)
const growth = ref<GrowthAttribution | null>(null)
const matchProgress = ref<MatchProgress | null>(null)
const actions = ref<ActionCompletion | null>(null)
const items = ref<ActionItem[]>([])

const latestComp = computed(() => {
  const c = trend.value?.competitiveness_curve
  return c && c.length ? Math.round(c[c.length - 1].value ?? 0) : null
})
const bestMatch = computed(() => {
  const m = trend.value?.match_curve
  return m && m.length ? Math.round(Math.max(...m.map(p => p.value ?? 0))) : null
})
const targetJob = computed(() => actions.value?.job_name || matchProgress.value?.job_name || '')

function fmtDelta(d?: number | null) { return d === null || d === undefined ? '' : `${d >= 0 ? '+' : ''}${d}` }
function deltaClass(d?: number | null) { return d === null || d === undefined ? '' : d > 0 ? 'u-up' : d < 0 ? 'u-down' : '' }

const curveOption = computed<EChartsOption | null>(() => {
  const comp = (trend.value?.competitiveness_curve || []).map(p => [p.date, p.value])
  const match = (trend.value?.match_curve || []).map(p => [p.date, p.value])
  if (!comp.length && !match.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['竞争力', '匹配分'] },
    grid: { left: 38, right: 16, top: 38, bottom: 28 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      { name: '竞争力', type: 'line', smooth: true, data: comp, itemStyle: { color: '#8b5cf6' }, areaStyle: { opacity: 0.08 } },
      { name: '匹配分', type: 'line', smooth: true, data: match, itemStyle: { color: '#10b981' } },
    ],
  }
})

async function load() {
  if (!studentId.value) return
  loading.value = true
  try {
    const [p, plan] = await Promise.all([progressApi.get(studentId.value), progressApi.actionPlan(studentId.value)])
    trend.value = p.trend; growth.value = p.growth; matchProgress.value = p.match_progress
    actions.value = plan.completion || p.actions
    items.value = plan.has_plan ? (plan.plan?.items || []) : []
  } catch { /* toasted */ } finally {
    loading.value = false
  }
}

async function complete(it: ActionItem) {
  if (!studentId.value || it.status === 'done') return
  completing.value = it.id
  const prev = it.status
  it.status = 'done'
  try {
    const res = await progressApi.completeItem(studentId.value, it.id)
    actions.value = res.completion
    Message.success('已完成，记得「重新评估」看看进步')
  } catch { it.status = prev } finally {
    completing.value = null
  }
}

async function reEvaluate() {
  if (!studentId.value || !targetJob.value) return
  reEval.value = true
  try {
    await matchApi.compute(studentId.value, targetJob.value)
    await load()
    const d = matchProgress.value?.total_delta
    Message.success(d !== undefined && d !== null ? (d >= 0 ? `匹配分 +${d}，继续加油！` : `匹配分 ${d}`) : '已重新评估')
  } catch { /* toasted */ } finally {
    reEval.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.growth { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.empty { padding: var(--sp-10) 0; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--sp-4); }
.drivers li { padding: 5px 0; color: var(--c-text); }
.item { display: flex; align-items: center; gap: var(--sp-3); padding: 11px 0; border-bottom: 1px solid var(--c-border); cursor: pointer; }
.item input { width: 17px; height: 17px; accent-color: var(--c-growth); cursor: pointer; }
.item.done .it-title { text-decoration: line-through; color: var(--c-text-3); }
.it-title { flex: 1; font-size: var(--fz-3); }
.it-time { font-size: var(--fz-1); }
.hint { margin-top: var(--sp-3); font-size: var(--fz-2); }
@media (max-width: 720px) { .kpis { grid-template-columns: 1fr; } }
</style>
