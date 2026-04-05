import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { reportApi } from '../api/report'
import { useUserStore } from './useUserStore'
import { clearOtherUsersKeys, clearAllKeys } from '../utils/storage'

export interface ReportContent {
  reportId: string
  studentId: string
  jobName: string
  overallScore: number
  confidence?: number
  dimensions: Record<string, any>
  chaptersJson?: any[]
  actionPlan?: any[]
  skillGaps?: any[]
  careerPath?: any[]
  createdAt: string
}

const STORAGE_KEY_PREFIX = 'report_data_'
const PENDING_REPORT_KEY = 'pending_report_id'

export const useReportStore = defineStore('report', () => {
  const reportContent = ref<ReportContent | null>(null)
  const status = ref<'idle' | 'pending' | 'generating' | 'done' | 'failed'>('idle')
  const progress = ref(0)
  const progressMsg = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const reportId = computed(() => reportContent.value?.reportId || null)

  function getStorageKey(): string | null {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    if (!studentId) return null
    return `${STORAGE_KEY_PREFIX}${studentId}`
  }

  function clearOtherUsersData(currentStudentId: string): void {
    clearOtherUsersKeys([STORAGE_KEY_PREFIX], currentStudentId)
  }

  function loadFromStorage(): void {
    const storageKey = getStorageKey()
    if (!storageKey) return

    const userStore = useUserStore()
    const currentStudentId = userStore.studentId
    if (!currentStudentId) return

    clearOtherUsersData(currentStudentId)

    const savedData = localStorage.getItem(storageKey)
    if (savedData) {
      try {
        const parsed: ReportContent = JSON.parse(savedData)
        if (parsed.studentId === currentStudentId) {
          reportContent.value = parsed
          status.value = 'done'
        } else {
          localStorage.removeItem(storageKey)
        }
      } catch (e) {
        console.error('Failed to parse saved report data:', e)
        localStorage.removeItem(storageKey)
      }
    }

    const pendingReportId = localStorage.getItem(PENDING_REPORT_KEY)
    if (pendingReportId && reportContent.value?.reportId !== pendingReportId) {
      localStorage.removeItem(PENDING_REPORT_KEY)
    }
  }

  function saveToStorage(): void {
    const storageKey = getStorageKey()
    if (!storageKey || !reportContent.value) return

    const userStore = useUserStore()
    if (reportContent.value.studentId !== userStore.studentId) {
      return
    }

    localStorage.setItem(storageKey, JSON.stringify(reportContent.value))
    if (reportContent.value.reportId) {
      localStorage.setItem(PENDING_REPORT_KEY, reportContent.value.reportId)
    }
  }

  function clearAllReportData(): void {
    clearAllKeys([STORAGE_KEY_PREFIX], [PENDING_REPORT_KEY])
    
    reportContent.value = null
    status.value = 'idle'
    progress.value = 0
    progressMsg.value = ''
    error.value = null
  }

  function setReport(data: ReportContent | null) {
    reportContent.value = data
    if (data) {
      status.value = 'done'
    }
  }

  function clearReport() {
    const storageKey = getStorageKey()
    if (storageKey) {
      localStorage.removeItem(storageKey)
    }
    localStorage.removeItem(PENDING_REPORT_KEY)
    reportContent.value = null
    status.value = 'idle'
    progress.value = 0
    progressMsg.value = ''
    error.value = null
  }

  function setLoading(val: boolean) {
    loading.value = val
  }

  function setError(val: string | null) {
    error.value = val
    if (val) {
      status.value = 'failed'
    }
  }

  function setGenerating(id: string) {
    status.value = 'generating'
    progress.value = 0
    progressMsg.value = '开始生成...'
    reportContent.value = {
      reportId: id,
      studentId: '',
      jobName: '',
      overallScore: 0,
      dimensions: {},
      createdAt: new Date().toISOString()
    }
  }

  function updateProgress(val: number, msg?: string) {
    progress.value = val
    if (msg) progressMsg.value = msg
  }

  async function loadReport(id: string) {
    loading.value = true
    error.value = null
    try {
      const res = await reportApi.get(id)
      if (res) {
        reportContent.value = {
          reportId: res.report_id || id,
          studentId: res.student_id || '',
          jobName: res.job_name || '',
          overallScore: res.overall_score || 0,
          confidence: res.confidence,
          dimensions: res.dimensions || {},
          chaptersJson: res.chapters_json || [],
          actionPlan: res.action_plan || [],
          skillGaps: res.skill_gaps || [],
          careerPath: res.career_path || [],
          createdAt: res.created_at || new Date().toISOString()
        }
        status.value = 'done'
      }
    } catch (e: any) {
      error.value = e?.message || '加载报告失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function startGenerate(studentId: string, jobName: string) {
    status.value = 'generating'
    progress.value = 0
    progressMsg.value = '正在生成报告...'
    error.value = null

    try {
      const res = await reportApi.generate(studentId, jobName)
      const taskId = res.task_id || res.report_id
      if (!taskId) {
        throw new Error('生成失败：未返回任务ID')
      }

      reportContent.value = {
        reportId: taskId,
        studentId: studentId,
        jobName: jobName,
        overallScore: 0,
        dimensions: {},
        createdAt: new Date().toISOString()
      }

      return taskId
    } catch (e: any) {
      status.value = 'failed'
      error.value = e?.message || '生成报告失败'
      throw e
    }
  }

  return {
    reportContent,
    status,
    progress,
    progressMsg,
    loading,
    error,
    reportId,
    getStorageKey,
    clearOtherUsersData,
    loadFromStorage,
    saveToStorage,
    clearAllReportData,
    setReport,
    clearReport,
    setLoading,
    setError,
    setGenerating,
    updateProgress,
    loadReport,
    startGenerate
  }
})
