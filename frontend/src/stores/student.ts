import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portraitApi, type Portrait } from '@/api/portrait'
import { progressApi, type ProgressResponse } from '@/api/progress'
import { matchApi, type MatchResult } from '@/api/match'
import { useSession } from './session'

// 学生域数据中枢：画像 + 成长 + 匹配历史。主页/画像/匹配/成长 共享，避免各页重复拉取。
export const useStudent = defineStore('student', () => {
  const portrait = ref<Portrait | null>(null)
  const progress = ref<ProgressResponse | null>(null)
  const matches = ref<MatchResult[]>([])
  const loading = ref(false)
  const loaded = ref(false)

  const bestMatch = computed<MatchResult | null>(() =>
    matches.value.length ? matches.value.reduce((a, b) => (b.overall_score > a.overall_score ? b : a)) : null)

  async function loadAll(force = false) {
    const sid = useSession().studentId
    if (!sid) return
    if (loaded.value && !force) return
    loading.value = true
    try {
      const [p, pr, hist] = await Promise.allSettled([
        portraitApi.get(sid), progressApi.get(sid), matchApi.history(sid),
      ])
      portrait.value = p.status === 'fulfilled' ? p.value : null
      progress.value = pr.status === 'fulfilled' ? pr.value : null
      matches.value = hist.status === 'fulfilled' ? (hist.value || []) : []
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  function setPortrait(p: Portrait) { portrait.value = p; loaded.value = true }
  function reset() { portrait.value = null; progress.value = null; matches.value = []; loaded.value = false }

  return { portrait, progress, matches, loading, loaded, bestMatch, loadAll, setPortrait, reset }
})
