import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { matchApi } from '../api/match'
import { useUserStore } from './useUserStore'
import { clearAllKeys, isExpired } from '../utils/storage'
import type {
  SkillMatchDetail,
  ImprovementSuggestion,
  GapAnalysis,
  ConfidenceBreakdown,
  MatchDimension,
  MarketDemand,
  TransferPath,
} from '../types'

export type { SkillMatchDetail, ImprovementSuggestion, GapAnalysis, ConfidenceBreakdown, MatchDimension, MarketDemand, TransferPath }

export interface MatchResult {
  job_id: string
  job_title: string
  overall_score: number
  confidence: number
  dimensions: {
    basic_requirements?: MatchDimension
    professional_skills?: MatchDimension
    professional_qualities?: MatchDimension
    development_potential?: MatchDimension
    market_demand?: MarketDemand
  }
  gap_skills?: Array<{
    skill: string
    importance?: 'must_have' | 'nice_to_have'
    suggestion?: string
    jd_source?: string
  }>
  matched_skills?: string[]
  /** @deprecated 兼容旧字段，等同于 matched_skills */
  semantic_matched?: string[]
  weight_used?: Record<string, number>
  summary?: string
  is_degraded?: boolean
  competitive_context?: string
  market_demand?: MarketDemand
  skill_match_details?: SkillMatchDetail[]
  gap_analysis?: GapAnalysis[]
  confidence_breakdown?: ConfidenceBreakdown
  transfer_paths?: TransferPath[]
  job_context?: {
    top_regions?: string[]
    culture_types?: string[]
    top_companies?: string[]
    education_level?: string
    majors?: string[]
    industry?: string
  }
  explanation_tree?: Array<{
    dim: string
    label: string
    score: number
    weight: number
    contribution: number
    factors: Array<{ name: string; value: string }>
  }>
}

const STORAGE_KEY_PREFIX = 'match_results_'
const CURRENT_JOB_KEY = 'current_job'
const CACHE_TIME_KEY_PREFIX = 'match_cache_time_'
const CACHE_EXPIRY_MS = 5 * 60 * 1000

interface StoredMatchData {
  studentId: string
  results: MatchResult[]
  timestamp: number
}

export const useMatchStore = defineStore('match', () => {
  const results = ref<MatchResult[]>([])
  const currentJob = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  let _matchSeq = 0
  
  const bestMatch = computed(() => {
    if (results.value.length === 0) return null
    return results.value.reduce((best, curr) => 
      curr.overall_score > best.overall_score ? curr : best
    )
  })
  
  const sortedResults = computed(() => {
    return [...results.value].sort((a, b) => b.overall_score - a.overall_score)
  })
  
  function getStorageKey(): string {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    return `${STORAGE_KEY_PREFIX}${studentId || 'anonymous'}`
  }

  function getCacheTimeKey(): string {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    return studentId ? `${CACHE_TIME_KEY_PREFIX}${studentId}` : ''
  }

  function isCacheExpired(studentId: string): boolean {
    return isExpired(`${CACHE_TIME_KEY_PREFIX}${studentId}`, CACHE_EXPIRY_MS)
  }

  function clearAllMatchData() {
    clearAllKeys([STORAGE_KEY_PREFIX, CACHE_TIME_KEY_PREFIX], [CURRENT_JOB_KEY])
    results.value = []
    currentJob.value = ''
    error.value = null
  }

  function loadFromStorage() {
    try {
      const userStore = useUserStore()
      const studentId = userStore.studentId
      const storageKey = getStorageKey()

      if (studentId && isCacheExpired(studentId)) {
        localStorage.removeItem(storageKey)
        const cacheTimeKey = getCacheTimeKey()
        if (cacheTimeKey) {
          localStorage.removeItem(cacheTimeKey)
        }
        return
      }

      const savedData = localStorage.getItem(storageKey)
      const savedCurrentJob = localStorage.getItem(CURRENT_JOB_KEY)

      if (savedData) {
        const parsed = JSON.parse(savedData)
        if (studentId) {
          if (parsed.studentId && parsed.studentId !== studentId) {
            return
          }
          results.value = parsed.results || []
        } else {
          results.value = Array.isArray(parsed) ? parsed : []
        }
      }
      if (savedCurrentJob) {
        currentJob.value = savedCurrentJob
      }
    } catch (e) {
      console.error('Failed to load match results from storage:', e)
    }
  }

  function saveToStorage() {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    const storageKey = getStorageKey()

    if (studentId) {
      const data: StoredMatchData = {
        studentId,
        results: results.value,
        timestamp: Date.now()
      }
      localStorage.setItem(storageKey, JSON.stringify(data))
      const cacheTimeKey = getCacheTimeKey()
      if (cacheTimeKey) {
        localStorage.setItem(cacheTimeKey, Date.now().toString())
      }
    } else {
      localStorage.setItem(storageKey, JSON.stringify(results.value))
    }
    localStorage.setItem(CURRENT_JOB_KEY, currentJob.value)
  }
  
  async function loadHistory(studentId: string): Promise<MatchResult[]> {
    loading.value = true
    error.value = null
    
    if (!studentId) {
      loadFromStorage()
      loading.value = false
      return results.value
    }
    
    try {
      const history = await matchApi.getHistory(studentId)
      
      results.value = history.map(r => ({
        job_id: r.job_id || '',
        job_title: r.job_title || '',
        overall_score: r.overall_score || 0,
        confidence: r.confidence || 0.8,
        dimensions: r.dimensions || {},
        gap_skills: r.gap_skills || [],
        matched_skills: r.matched_skills || [],
        weight_used: r.weight_used,
        summary: r.summary,
        is_degraded: r.is_degraded || false,
        market_demand: r.market_demand || undefined,
        skill_match_details: r.skill_match_details || [],
        gap_analysis: r.gap_analysis || [],
        confidence_breakdown: r.confidence_breakdown || undefined,
        transfer_paths: r.transfer_paths || [],
      }))
      
      saveToStorage()
      return results.value
    } catch (e: any) {
      error.value = e.message || '加载历史失败'
      return []
    } finally {
      loading.value = false
    }
  }
  
  async function computeMatch(jobName: string, forceRefresh: boolean = false, weightPreset: string = 'default'): Promise<MatchResult | null> {
    const userStore = useUserStore()
    const studentId = userStore.studentId

    if (!forceRefresh) {
      const existing = results.value.find(r => r.job_title === jobName)
      if (existing) {
        currentJob.value = jobName
        return existing
      }
    }

    if (!studentId) {
      error.value = '请先上传简历'
      return null
    }

    const seq = ++_matchSeq
    loading.value = true
    error.value = null

    try {
      const result = await matchApi.compute(studentId, jobName, weightPreset)

      if (seq !== _matchSeq) return null

      const matchResult: MatchResult = {
        job_id: result.job_id || '',
        job_title: result.job_title || jobName,
        overall_score: result.overall_score || 0,
        confidence: result.confidence || 0.8,
        dimensions: result.dimensions || {},
        gap_skills: result.gap_skills || [],
        matched_skills: result.matched_skills || [],
        weight_used: result.weight_used,
        summary: result.summary,
        is_degraded: result.is_degraded || false,
        market_demand: result.market_demand || undefined,
        competitive_context: result.competitive_context,
        skill_match_details: result.skill_match_details || [],
        gap_analysis: result.gap_analysis || [],
        confidence_breakdown: result.confidence_breakdown || undefined,
        transfer_paths: result.transfer_paths || [],
        job_context: result.job_context || {},
        explanation_tree: result.explanation_tree || [],
      }

      const existingIndex = results.value.findIndex(r => r.job_title === jobName || r.job_title === matchResult.job_title)
      if (existingIndex >= 0) {
        results.value[existingIndex] = matchResult
      } else {
        results.value.push(matchResult)
      }

      currentJob.value = matchResult.job_title
      saveToStorage()
      return matchResult
    } catch (e: any) {
      if (seq === _matchSeq) error.value = (e as any).message || '匹配失败'
      return null
    } finally {
      if (seq === _matchSeq) loading.value = false
    }
  }
  
  async function batchCompute(jobNames: string[]): Promise<MatchResult[]> {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    
    if (!studentId) {
      error.value = '请先上传简历'
      return []
    }
    
    loading.value = true
    error.value = null
    
    try {
      const result = await matchApi.batchCompute(studentId, jobNames)
      
      results.value = result.map(r => ({
        job_id: r.job_id || '',
        job_title: r.job_title || '',
        overall_score: r.overall_score || 0,
        confidence: r.confidence || 0.8,
        dimensions: r.dimensions || {},
        gap_skills: r.gap_skills || [],
        matched_skills: r.matched_skills || [],
        weight_used: r.weight_used,
        is_degraded: r.is_degraded || false,
        skill_match_details: r.skill_match_details || [],
        gap_analysis: r.gap_analysis || [],
        confidence_breakdown: r.confidence_breakdown || undefined,
        transfer_paths: r.transfer_paths || [],
      }))
      
      if (results.value.length > 0) {
        currentJob.value = results.value[0].job_title
      }
      
      saveToStorage()
      
      return results.value
    } catch (e: any) {
      error.value = e.message || '批量匹配失败'
      return []
    } finally {
      loading.value = false
    }
  }
  
  function clearResults() {
    const storageKey = getStorageKey()
    const cacheTimeKey = getCacheTimeKey()
    results.value = []
    currentJob.value = ''
    error.value = null
    localStorage.removeItem(storageKey)
    if (cacheTimeKey) {
      localStorage.removeItem(cacheTimeKey)
    }
    localStorage.removeItem(CURRENT_JOB_KEY)
  }
  
  function deleteResult(jobTitle: string) {
    const index = results.value.findIndex(r => r.job_title === jobTitle)
    if (index >= 0) {
      results.value.splice(index, 1)
      saveToStorage()
    }
    if (currentJob.value === jobTitle) {
      currentJob.value = results.value.length > 0 ? results.value[0].job_title : ''
    }
  }
  
  function getResultByJob(jobName: string): MatchResult | undefined {
    const r = results.value.find(r => r.job_title === jobName)
    return r ? { ...r } : undefined  // 浅拷贝：保证每次切换岗位都产生新对象引用，Vue watcher 每次都能触发
  }
  
  function setCurrentJob(jobName: string) {
    currentJob.value = jobName
    localStorage.setItem(CURRENT_JOB_KEY, jobName)
  }
  
  loadFromStorage()
  
  return {
    results,
    currentJob,
    loading,
    error,
    bestMatch,
    sortedResults,
    loadHistory,
    computeMatch,
    batchCompute,
    clearResults,
    deleteResult,
    getResultByJob,
    setCurrentJob,
    loadFromStorage,
    clearAllMatchData,
  }
})
