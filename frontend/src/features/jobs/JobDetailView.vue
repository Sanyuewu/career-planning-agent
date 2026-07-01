<template>
  <div class="detail">
    <button class="back" @click="$router.push('/jobs')">← 返回岗位</button>

    <AppCard v-if="info" class="head">
      <div class="j-title">{{ info.title }}</div>
      <div class="j-meta u-muted">
        <span v-if="info.salary">💰 {{ info.salary }}</span>
        <span v-if="info.industry">🏢 {{ info.industry }}</span>
        <span v-if="info.education">🎓 {{ info.education }}</span>
      </div>
      <p v-if="info.overview" class="j-overview">{{ info.overview }}</p>
    </AppCard>

    <AppCard v-if="info?.skills?.length">
      <SectionTitle title="核心技能要求" />
      <div class="tags"><span v-for="s in info.skills" :key="s" class="tag">{{ s }}</span></div>
    </AppCard>

    <AppCard v-if="transfers.length">
      <SectionTitle title="可转岗方向" sub="基于技能重叠的横向发展" />
      <div class="paths">
        <button v-for="t in transfers" :key="t.target" class="path" @click="go(t.target)">
          <span>{{ t.target }}</span><span class="p-arrow">→</span>
        </button>
      </div>
    </AppCard>

    <div v-if="loading" class="u-faint">加载中…</div>
    <AppButton size="lg" class="cta" @click="matchThis">用这个岗位做匹配 →</AppButton>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import { jobApi, type JobInfo, type CareerPaths } from '@/api/job'

const route = useRoute()
const router = useRouter()

const title = computed(() => decodeURIComponent(route.params.title as string))
const info = ref<JobInfo | null>(null)
const paths = ref<CareerPaths | null>(null)
const loading = ref(true)

const transfers = computed(() => (paths.value?.transfer_paths || []).map((t: any) => ({ target: t.target || t.title })).filter(t => t.target))

async function load() {
  loading.value = true
  try {
    info.value = await jobApi.info(title.value)
    try { paths.value = await jobApi.careerGraph(title.value) } catch { /* optional */ }
  } catch { /* toasted */ } finally { loading.value = false }
}

onMounted(load)
watch(title, load)

function go(t: string) { router.push(`/jobs/${encodeURIComponent(t)}`) }
function matchThis() { router.push({ path: '/journey/match', query: { job: title.value } }) }
</script>

<style scoped>
.detail { display: flex; flex-direction: column; gap: var(--sp-4); }
.back { align-self: flex-start; background: none; border: none; color: var(--c-text-2); cursor: pointer; font-size: var(--fz-3); }
.back:hover { color: var(--c-primary); }
.j-title { font-size: var(--fz-6); font-weight: 800; }
.j-meta { display: flex; gap: var(--sp-4); flex-wrap: wrap; margin: var(--sp-2) 0 var(--sp-3); font-size: var(--fz-2); }
.j-overview { line-height: 1.7; color: var(--c-text); }
.tags { display: flex; flex-wrap: wrap; gap: 8px; }
.tag { background: var(--c-primary-weak); color: var(--c-primary); border-radius: var(--r-sm); padding: 5px 11px; font-size: var(--fz-2); font-weight: 600; }
.paths { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
.path { display: flex; align-items: center; gap: 10px; border: 1px solid var(--c-border-2); background: var(--c-surface);
  border-radius: var(--r-full); padding: 8px 16px; cursor: pointer; transition: all .18s; }
.path:hover { border-color: var(--c-primary); color: var(--c-primary); }
.p-arrow { color: var(--c-primary); }
.cta { align-self: center; margin-top: var(--sp-2); }
</style>
