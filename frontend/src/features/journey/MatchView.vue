<template>
  <div class="match">
    <header class="hd">
      <h1>人岗匹配</h1>
      <p class="u-muted">选一个目标岗位，看看你的四维契合度和差距</p>
    </header>

    <AppCard class="picker">
      <a-select v-model="selectedJob" placeholder="选择 / 搜索目标岗位" allow-search size="large"
                :options="jobOptions" style="flex:1" />
      <AppButton size="md" :loading="computing" @click="() => compute()">开始匹配</AppButton>
    </AppCard>

    <!-- 推荐 -->
    <AppCard v-if="recommends.length && !result">
      <SectionTitle title="为你推荐" sub="按能力×意愿综合排序" />
      <div class="recos">
        <button v-for="r in recommends" :key="r.job_title" class="reco" @click="compute(r.job_title)">
          <span class="reco-job">{{ r.job_title }}</span>
          <span class="reco-score">{{ Math.round(r.score) }}分</span>
        </button>
      </div>
    </AppCard>

    <!-- 结果 -->
    <template v-if="result">
      <AppCard class="result">
        <div class="r-head">
          <div>
            <div class="r-job">{{ result.job_title }}</div>
            <div class="r-sum u-muted">{{ result.summary || '四维综合匹配' }}</div>
          </div>
          <ProgressRing :value="result.overall_score" :size="100" label="综合" />
        </div>

        <div v-if="result.eligible === false" class="veto">⚠️ {{ result.veto_reason || '基础要求未达标' }}</div>

        <div class="dims">
          <div v-for="d in dims" :key="d.key" class="dim">
            <div class="dim-top"><span>{{ d.label }}</span><b>{{ Math.round(d.score) }}</b></div>
            <div class="bar"><div class="fill" :style="{ width: d.score + '%' }"></div></div>
          </div>
        </div>

        <div class="skills">
          <div class="sk-col">
            <div class="sk-h">✅ 已匹配</div>
            <span v-for="s in (result.matched_skills || []).slice(0, 8)" :key="s" class="sk ok">{{ s }}</span>
            <span v-if="!result.matched_skills?.length" class="u-faint">—</span>
          </div>
          <div class="sk-col">
            <div class="sk-h">🎯 待补齐</div>
            <span v-for="g in (result.gap_skills || []).slice(0, 8)" :key="g.skill" class="sk gap">{{ g.skill }}</span>
            <span v-if="!result.gap_skills?.length" class="u-faint">无明显缺口</span>
          </div>
        </div>
      </AppCard>

      <div class="cta">
        <AppButton size="lg" @click="toReport">下一步：生成职业报告 →</AppButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import ProgressRing from '@/design/components/ProgressRing.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import { matchApi, type MatchResult, type Recommendation } from '@/api/match'
import { jobApi } from '@/api/job'
import { useSession } from '@/stores/session'
import { useStudent } from '@/stores/student'

const router = useRouter()
const session = useSession()
const student = useStudent()

const jobs = ref<string[]>([])
const selectedJob = ref('')
const result = ref<MatchResult | null>(null)
const recommends = ref<Recommendation[]>([])
const computing = ref(false)

const jobOptions = computed(() => jobs.value.map(j => ({ label: j, value: j })))

const dims = computed(() => {
  const d = result.value?.dimensions || {}
  return [
    { key: 'basic', label: '基础要求', score: d.basic_requirements?.score ?? 0 },
    { key: 'skill', label: '专业技能', score: d.professional_skills?.score ?? 0 },
    { key: 'quality', label: '职业素养', score: d.professional_qualities?.score ?? 0 },
    { key: 'potential', label: '发展潜力', score: d.development_potential?.score ?? 0 },
  ]
})

onMounted(async () => {
  student.loadAll()
  try { jobs.value = await jobApi.list() } catch { /* toasted */ }
  const sid = session.studentId
  if (sid) { try { recommends.value = (await matchApi.recommend(sid, 5)).recommendations } catch { /* noop */ } }
})

async function compute(job?: string) {
  const sid = session.studentId
  const j = job || selectedJob.value
  if (!sid) { Message.warning('请先上传简历'); return }
  if (!j) { Message.warning('请选择岗位'); return }
  selectedJob.value = j
  computing.value = true
  try {
    result.value = await matchApi.compute(sid, j)
    student.loadAll(true)
  } catch { /* toasted */ } finally {
    computing.value = false
  }
}

function toReport() {
  router.push({ path: '/journey/report', query: { job: selectedJob.value } })
}
</script>

<style scoped>
.match { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.picker { display: flex; align-items: center; gap: var(--sp-3); }
.recos { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
.reco { display: flex; align-items: center; gap: 8px; border: 1px solid var(--c-border-2);
  background: var(--c-surface); border-radius: var(--r-full); padding: 8px 16px; cursor: pointer; transition: all .18s; }
.reco:hover { border-color: var(--c-primary); background: var(--c-primary-weak); }
.reco-job { font-weight: 600; font-size: var(--fz-3); }
.reco-score { color: var(--c-primary); font-weight: 700; font-size: var(--fz-2); }
.r-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); }
.r-job { font-size: var(--fz-5); font-weight: 800; }
.r-sum { margin-top: 4px; font-size: var(--fz-2); }
.veto { margin: var(--sp-4) 0 0; background: #fff4e6; color: #c2630a; border-radius: var(--r-md); padding: 10px 14px; font-size: var(--fz-2); }
.dims { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4) var(--sp-6); margin: var(--sp-5) 0; }
.dim-top { display: flex; justify-content: space-between; font-size: var(--fz-2); margin-bottom: 6px; }
.dim-top b { color: var(--c-primary); }
.bar { height: 8px; background: var(--c-bg); border-radius: var(--r-full); overflow: hidden; }
.fill { height: 100%; background: var(--grad-brand); border-radius: var(--r-full); }
.skills { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-5); border-top: 1px solid var(--c-border); padding-top: var(--sp-4); }
.sk-h { font-size: var(--fz-2); color: var(--c-text-2); margin-bottom: 8px; }
.sk { display: inline-block; border-radius: var(--r-sm); padding: 4px 10px; font-size: var(--fz-1); margin: 0 6px 6px 0; }
.sk.ok { background: var(--c-growth-weak); color: #0b8a63; }
.sk.gap { background: #fff0f0; color: var(--c-danger); }
.cta { text-align: center; }
@media (max-width: 720px) { .dims, .skills { grid-template-columns: 1fr; } }
</style>
