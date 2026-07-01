<template>
  <div class="report">
    <header class="hd">
      <h1>职业发展报告</h1>
      <p class="u-muted">基于你的画像与目标岗位，生成可执行的成长规划</p>
    </header>

    <!-- 生成入口 -->
    <AppCard v-if="phase === 'idle'" class="gen">
      <div class="gen-job">目标岗位：<b>{{ job || '未选择' }}</b></div>
      <AppButton size="lg" :disabled="!job" @click="generate">生成报告</AppButton>
      <p v-if="!job" class="u-faint">请先在「人岗匹配」选定一个岗位</p>
    </AppCard>

    <!-- 生成中 -->
    <AppCard v-else-if="phase === 'generating'" class="progress">
      <div class="spin"></div>
      <div class="p-title">正在生成报告… {{ progress }}%</div>
      <div class="track"><div class="track-fill" :style="{ width: progress + '%' }"></div></div>
      <div class="p-sub u-faint">检索职业图谱 · 四维匹配 · AI 撰写规划</div>
    </AppCard>

    <AppCard v-else-if="phase === 'failed'" class="failed">
      <EmptyState icon="😵" text="报告生成失败，可能是 AI 服务异常，请稍后重试">
        <AppButton @click="phase = 'idle'">重试</AppButton>
      </EmptyState>
    </AppCard>

    <!-- 结果 -->
    <template v-else-if="phase === 'done' && report">
      <div class="actions">
        <AppButton size="sm" variant="ghost" @click="exportFile('pdf')">导出 PDF</AppButton>
        <AppButton size="sm" variant="ghost" @click="exportFile('word')">导出 Word</AppButton>
      </div>
      <AppCard v-for="(ch, i) in report.chapters_json || []" :key="i" class="chapter">
        <h3>{{ ch.title }}</h3>
        <div class="ch-body">{{ ch.content }}</div>
      </AppCard>
      <div class="cta">
        <AppButton size="lg" @click="$router.push('/growth')">去成长页，跟踪你的行动 →</AppButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { reportApi, type ReportDetail } from '@/api/report'
import { useSession } from '@/stores/session'
import { useStudent } from '@/stores/student'

const route = useRoute()
const session = useSession()
const student = useStudent()

const phase = ref<'idle' | 'generating' | 'done' | 'failed'>('idle')
const progress = ref(0)
const report = ref<ReportDetail | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const job = computed(() => (route.query.job as string) || student.bestMatch?.job_title || '')

onMounted(() => student.loadAll())
onUnmounted(() => { if (timer) clearInterval(timer) })

async function generate() {
  const sid = session.studentId
  if (!sid || !job.value) { Message.warning('请先选择目标岗位'); return }
  phase.value = 'generating'; progress.value = 5
  try {
    const { task_id } = await reportApi.generate(sid, job.value)
    poll(task_id)
  } catch { phase.value = 'idle' }
}

function poll(taskId: string) {
  timer = setInterval(async () => {
    try {
      const s = await reportApi.status(taskId)
      if (s.progress) progress.value = s.progress
      if (s.status === 'completed') {
        if (timer) clearInterval(timer)
        report.value = s.result || (s.report_id ? await reportApi.get(s.report_id) : null)
        phase.value = 'done'
        student.loadAll(true)
      } else if (s.status === 'failed') {
        if (timer) clearInterval(timer)
        phase.value = 'failed'
      }
    } catch {
      if (timer) clearInterval(timer)
      phase.value = 'failed'
    }
  }, 1500)
}

async function exportFile(fmt: 'pdf' | 'word') {
  if (!report.value) return
  try {
    const res = await reportApi.exportFile(report.value.report_id, fmt)
    if (!res.ok) { Message.error('导出失败'); return }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `职业报告.${fmt === 'pdf' ? 'pdf' : 'docx'}`; a.click()
    URL.revokeObjectURL(url)
  } catch { Message.error('导出失败') }
}
</script>

<style scoped>
.report { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.gen { text-align: center; display: flex; flex-direction: column; align-items: center; gap: var(--sp-4); padding: var(--sp-10); }
.gen-job { font-size: var(--fz-4); }
.progress { text-align: center; padding: var(--sp-10); }
.spin { width: 38px; height: 38px; margin: 0 auto var(--sp-4); border: 3px solid var(--c-border);
  border-top-color: var(--c-primary); border-radius: 50%; animation: s .8s linear infinite; }
@keyframes s { to { transform: rotate(360deg); } }
.p-title { font-size: var(--fz-4); font-weight: 700; }
.track { height: 8px; background: var(--c-bg); border-radius: var(--r-full); overflow: hidden; max-width: 360px; margin: var(--sp-4) auto 0; }
.track-fill { height: 100%; background: var(--grad-brand); transition: width .4s; }
.p-sub { margin-top: var(--sp-3); }
.actions { display: flex; gap: var(--sp-3); justify-content: flex-end; }
.chapter h3 { font-size: var(--fz-5); font-weight: 800; margin-bottom: var(--sp-3); color: var(--c-primary); }
.ch-body { white-space: pre-wrap; line-height: 1.75; color: var(--c-text); font-size: var(--fz-3); }
.cta { text-align: center; }
</style>
