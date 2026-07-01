<template>
  <div class="jobs">
    <header class="hd">
      <h1>🔍 岗位探索</h1>
      <p class="u-muted">浏览岗位画像与职业发展路径</p>
    </header>

    <a-input v-model="q" placeholder="搜索岗位…" size="large" allow-clear class="search" />

    <div v-if="loading" class="muted u-faint">加载中…</div>
    <div v-else class="grid">
      <button v-for="j in filtered" :key="j" class="job-card" @click="go(j)">
        <span class="j-name">{{ j }}</span>
        <span class="j-arrow">→</span>
      </button>
    </div>
    <EmptyState v-if="!loading && !filtered.length" text="没有匹配的岗位" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/design/components/EmptyState.vue'
import { jobApi } from '@/api/job'

const router = useRouter()
const jobs = ref<string[]>([])
const q = ref('')
const loading = ref(true)

const filtered = computed(() => {
  const k = q.value.trim().toLowerCase()
  return k ? jobs.value.filter(j => j.toLowerCase().includes(k)) : jobs.value
})

onMounted(async () => {
  try { jobs.value = await jobApi.list() } catch { /* toasted */ } finally { loading.value = false }
})

function go(title: string) { router.push(`/jobs/${encodeURIComponent(title)}`) }
</script>

<style scoped>
.jobs { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.search { max-width: 420px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--sp-3); }
.job-card { display: flex; align-items: center; justify-content: space-between; background: var(--c-surface);
  border: 1px solid var(--c-border); border-radius: var(--r-md); padding: 16px 18px; cursor: pointer; transition: all .18s; }
.job-card:hover { border-color: var(--c-primary); box-shadow: var(--sh-md); transform: translateY(-2px); }
.j-name { font-weight: 600; font-size: var(--fz-3); }
.j-arrow { color: var(--c-primary); }
</style>
