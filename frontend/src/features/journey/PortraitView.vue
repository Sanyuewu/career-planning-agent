<template>
  <div v-if="!portrait" class="loading">
    <EmptyState icon="📄" text="还没有画像，先上传一份简历吧">
      <AppButton @click="$router.push('/journey/upload')">去上传</AppButton>
    </EmptyState>
  </div>

  <div v-else class="portrait">
    <AppCard class="hero">
      <div>
        <div class="name">{{ portrait.basic_info?.name || '我的画像' }}</div>
        <div class="meta u-muted">
          {{ portrait.basic_info?.school || '' }}
          {{ portrait.basic_info?.major ? ' · ' + portrait.basic_info.major : '' }}
        </div>
        <div class="pills">
          <span class="pill">完整度 {{ Math.round(portrait.completeness) }}%</span>
          <span class="pill strong">竞争力 {{ Math.round(portrait.competitiveness) }} · {{ portrait.competitiveness_level }}</span>
        </div>
        <AppButton variant="ghost" size="sm" class="reupload" @click="$router.push('/journey/upload')">
          🔄 更新简历
        </AppButton>
      </div>
      <ProgressRing :value="portrait.competitiveness" :size="104" label="竞争力" />
    </AppCard>

    <!-- 竞争力曲线 -->
    <AppCard v-if="curveOption">
      <SectionTitle title="竞争力变化" sub="基于你的画像快照" />
      <ChartCard :option="curveOption" :height="200" />
    </AppCard>

    <div class="grid">
      <!-- 技能 -->
      <AppCard>
        <SectionTitle title="专业技能" :sub="`${portrait.skills.length} 项`" />
        <div class="tags">
          <span v-for="s in portrait.skills" :key="s" class="tag">{{ s }}</span>
          <span v-if="!portrait.skills.length" class="u-faint">暂无</span>
        </div>
        <div class="add">
          <a-input v-model="newSkill" placeholder="补充一个技能…" size="small" @keyup.enter="addSkill" />
          <AppButton size="sm" variant="soft" :loading="saving" @click="addSkill">添加</AppButton>
        </div>
      </AppCard>

      <!-- 软技能 -->
      <AppCard>
        <SectionTitle title="综合素养" />
        <div v-for="(label, key) in SOFT_LABELS" :key="key" class="soft">
          <span class="soft-l">{{ label }}</span>
          <div class="bar"><div class="bar-fill" :style="{ width: softPct(key) + '%' }"></div></div>
        </div>
      </AppCard>
    </div>

    <div class="cta">
      <AppButton size="lg" @click="$router.push('/journey/match')">下一步：人岗匹配 →</AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import ProgressRing from '@/design/components/ProgressRing.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import ChartCard from '@/design/components/ChartCard.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { portraitApi } from '@/api/portrait'
import { useSession } from '@/stores/session'
import { useStudent } from '@/stores/student'

const session = useSession()
const student = useStudent()
const portrait = computed(() => student.portrait)

const SOFT_LABELS: Record<string, string> = {
  innovation: '创新能力', learning: '学习能力', stress_resistance: '抗压能力',
  communication: '沟通能力', internship: '实习经历',
}

onMounted(() => student.loadAll())

function softPct(key: string): number {
  const s = portrait.value?.inferred_soft_skills?.[key]?.score ?? 3
  return Math.round((s / 5) * 100)
}

const curveOption = computed<EChartsOption | null>(() => {
  const curve = student.progress?.trend?.competitiveness_curve || []
  if (curve.length < 1) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      type: 'line', smooth: true, showSymbol: true,
      data: curve.map(p => [p.date, p.value]),
      itemStyle: { color: '#6d5efc' }, areaStyle: { opacity: 0.1 },
    }],
  }
})

const newSkill = ref('')
const saving = ref(false)
async function addSkill() {
  const sid = session.studentId
  const v = newSkill.value.trim()
  if (!v || !sid) return
  saving.value = true
  try {
    const skills = [...(portrait.value?.skills || []), v]
    const p = await portraitApi.update(sid, { skills })
    student.setPortrait(p)
    await student.loadAll(true)
    newSkill.value = ''
    Message.success('画像已更新')
  } catch { /* toasted */ } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.portrait { display: flex; flex-direction: column; gap: var(--sp-5); }
.loading { padding: var(--sp-10) 0; }
.hero { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-6); }
.name { font-size: var(--fz-6); font-weight: 800; }
.meta { margin: 4px 0 var(--sp-4); }
.pills { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
.pill { background: var(--c-bg); border: 1px solid var(--c-border); border-radius: var(--r-full);
  padding: 4px 12px; font-size: var(--fz-2); color: var(--c-text-2); }
.pill.strong { background: var(--c-primary-weak); color: var(--c-primary); border-color: transparent; font-weight: 700; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); }
.tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: var(--sp-4); }
.tag { background: var(--c-growth-weak); color: #0b8a63; border-radius: var(--r-sm); padding: 5px 11px; font-size: var(--fz-2); font-weight: 600; }
.add { display: flex; gap: 8px; }
.soft { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.soft-l { width: 72px; font-size: var(--fz-2); color: var(--c-text-2); flex-shrink: 0; }
.bar { flex: 1; height: 8px; background: var(--c-bg); border-radius: var(--r-full); overflow: hidden; }
.bar-fill { height: 100%; background: var(--grad-brand); border-radius: var(--r-full); }
.cta { text-align: center; margin-top: var(--sp-2); }
.reupload { margin-top: var(--sp-3); }
@media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
