<template>
  <div class="home">
    <!-- 顶部：问候 + 竞争力环 -->
    <AppCard class="hero">
      <div class="hero-l">
        <div class="hi">你好，{{ session.displayName }} 👋</div>
        <div class="sub u-muted">这是你的职业成长主页</div>
        <div class="comp">
          <span class="comp-label">职业竞争力</span>
          <span class="comp-val">{{ competitiveness }}</span>
          <span v-if="compDelta !== null" class="comp-delta" :class="compDelta >= 0 ? 'u-up' : 'u-down'">
            {{ compDelta >= 0 ? '↑+' : '↓' }}{{ Math.abs(compDelta) }} 较上次
          </span>
        </div>
      </div>
      <ProgressRing :value="competitiveness" :size="116" label="竞争力" />
    </AppCard>

    <!-- 下一步（产品心脏） -->
    <NextStepCard :step="nextStep" class="next" />

    <!-- Journey 进度 -->
    <AppCard class="journey">
      <JourneyStepper :steps="journeySteps" />
    </AppCard>

    <!-- 关键指标 -->
    <div class="stats">
      <StatCard label="最佳匹配岗位" :value="bestMatchScore" unit="分">
        <template #delta>
          <span class="u-faint">{{ bestMatchJob || '还没做匹配' }}</span>
        </template>
      </StatCard>
      <StatCard label="行动完成率"
        :value="actions?.available ? actions.completion_pct + '%' : '—'">
        <template #delta>
          <span class="u-faint">{{ actions?.available ? `${actions.done}/${actions.total} 项` : '生成报告后开启' }}</span>
        </template>
      </StatCard>
      <StatCard label="画像完整度" :value="completeness" unit="%">
        <template #delta>
          <span class="u-faint">{{ completeness >= 70 ? '已就绪' : '建议补全' }}</span>
        </template>
      </StatCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import AppCard from '@/design/components/AppCard.vue'
import ProgressRing from '@/design/components/ProgressRing.vue'
import NextStepCard from '@/design/components/NextStepCard.vue'
import StatCard from '@/design/components/StatCard.vue'
import JourneyStepper, { type JourneyStep } from '@/design/components/JourneyStepper.vue'
import { useSession } from '@/stores/session'
import { useStudent } from '@/stores/student'
import { computeNextStep } from '@/lib/nextStep'

const session = useSession()
const student = useStudent()

onMounted(() => student.loadAll())

const competitiveness = computed(() => Math.round(student.portrait?.competitiveness ?? 0))
const completeness = computed(() => Math.round(student.portrait?.completeness ?? 0))
const compDelta = computed(() => student.progress?.trend?.competitiveness_delta ?? null)
const actions = computed(() => student.progress?.actions)
const bestMatchScore = computed(() => student.bestMatch ? Math.round(student.bestMatch.overall_score) : '—')
const bestMatchJob = computed(() => student.bestMatch?.job_title || '')

const nextStep = computed(() => computeNextStep({
  hasStudent: !!session.studentId,
  portrait: student.portrait,
  progress: student.progress,
  matches: student.matches,
}))

const journeySteps = computed<JourneyStep[]>(() => {
  const hasPortrait = !!student.portrait
  const hasMatch = student.matches.length > 0
  const hasReport = !!student.progress?.actions?.available
  return [
    { key: 'portrait', label: '画像', done: hasPortrait, active: !hasPortrait,
      to: hasPortrait ? '/journey/portrait' : '/journey/upload' },
    { key: 'match', label: '匹配', done: hasMatch, active: hasPortrait && !hasMatch, to: '/journey/match' },
    { key: 'report', label: '报告', done: hasReport, active: hasMatch && !hasReport, to: '/journey/report' },
    { key: 'growth', label: '成长', done: false, active: hasReport, to: '/growth' },
  ]
})
</script>

<style scoped>
.home { display: flex; flex-direction: column; gap: var(--sp-5); }
.hero { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-6);
  background: var(--grad-brand-soft); border: none; }
.hi { font-size: var(--fz-6); font-weight: 800; }
.sub { margin: 4px 0 var(--sp-5); }
.comp { display: flex; align-items: baseline; gap: var(--sp-3); flex-wrap: wrap; }
.comp-label { color: var(--c-text-2); font-size: var(--fz-3); }
.comp-val { font-size: var(--fz-8); font-weight: 800; line-height: 1; color: var(--c-primary); }
.comp-delta { font-size: var(--fz-3); font-weight: 700; }
.journey { padding: var(--sp-6) var(--sp-8); }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--sp-4); }
@media (max-width: 720px) {
  .hero { flex-direction: column-reverse; align-items: flex-start; }
  .stats { grid-template-columns: 1fr; }
}
</style>
