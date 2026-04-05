import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { crewApi, type CrewResult, type TaskStatus, type WorkflowRequest, type AnalysisRequest, type MatchRequest } from '../api/crew'

export type AgentStatus = 'idle' | 'running' | 'completed' | 'failed'

export interface AgentState {
  status: AgentStatus
  task?: string
  startedAt?: string
  completedAt?: string
  confidence?: number
}

export const useCrewStore = defineStore('crew', () => {
  const currentTaskId = ref<string | null>(null)
  const taskStatus = ref<TaskStatus | null>(null)
  const agentStates = ref<Record<string, AgentState>>({
    resume_analyzer: { status: 'idle' },
    job_matcher: { status: 'idle' },
    career_advisor: { status: 'idle' },
    report_generator: { status: 'idle' }
  })
  const lastResult = ref<CrewResult | null>(null)
  const isProcessing = ref(false)
  const progress = ref(0)
  const error = ref<string | null>(null)
  
  const currentAgent = computed(() => {
    for (const [key, state] of Object.entries(agentStates.value)) {
      if (state.status === 'running') {
        return key
      }
    }
    return null
  })
  
  const isCompleted = computed(() => {
    return taskStatus.value?.status === 'completed'
  })
  
  const isFailed = computed(() => {
    return taskStatus.value?.status === 'failed'
  })
  
  function resetAgentStates() {
    agentStates.value = {
      resume_analyzer: { status: 'idle' },
      job_matcher: { status: 'idle' },
      career_advisor: { status: 'idle' },
      report_generator: { status: 'idle' }
    }
  }
  
  function updateAgentState(agent: string, state: Partial<AgentState>) {
    agentStates.value[agent] = {
      ...agentStates.value[agent],
      ...state
    }
  }
  
  async function runWorkflow(data: WorkflowRequest): Promise<CrewResult> {
    isProcessing.value = true
    error.value = null
    progress.value = 0
    resetAgentStates()
    
    try {
      const crewStatus = await crewApi.getStatus()
      
      if (!crewStatus.crewai_installed || !crewStatus.llm_configured) {
        throw new Error('CrewAI服务未配置，请检查后端设置')
      }
      
      updateAgentState('resume_analyzer', { status: 'running' })
      
      const result = await crewApi.runWorkflow(data)
      
      if (result.success) {
        updateAgentState('resume_analyzer', { status: 'completed' })
        updateAgentState('job_matcher', { status: 'completed' })
        updateAgentState('career_advisor', { status: 'completed' })
        updateAgentState('report_generator', { status: 'completed' })
        lastResult.value = result
        progress.value = 1
      } else {
        throw new Error(result.error || '工作流执行失败')
      }
      
      return result
    } catch (e: any) {
      error.value = e.message || '未知错误'
      for (const [key, state] of Object.entries(agentStates.value)) {
        if (state.status === 'running') {
          updateAgentState(key, { status: 'failed' })
        }
      }
      throw e
    } finally {
      isProcessing.value = false
    }
  }
  
  async function startAsyncWorkflow(data: WorkflowRequest): Promise<string> {
    isProcessing.value = true
    error.value = null
    progress.value = 0
    resetAgentStates()
    
    try {
      const { task_id } = await crewApi.startAsyncWorkflow(data)
      currentTaskId.value = task_id
      
      updateAgentState('resume_analyzer', { status: 'running' })
      
      const result = await crewApi.pollTaskUntilComplete(
        task_id,
        (p, status) => {
          progress.value = p
          if (status) {
            taskStatus.value = status
          }
          
          if (p < 0.25) {
            updateAgentState('resume_analyzer', { status: 'running' })
          } else if (p < 0.5) {
            updateAgentState('resume_analyzer', { status: 'completed' })
            updateAgentState('job_matcher', { status: 'running' })
          } else if (p < 0.75) {
            updateAgentState('job_matcher', { status: 'completed' })
            updateAgentState('career_advisor', { status: 'running' })
          } else if (p < 1) {
            updateAgentState('career_advisor', { status: 'completed' })
            updateAgentState('report_generator', { status: 'running' })
          }
        }
      )
      
      updateAgentState('report_generator', { status: 'completed' })
      lastResult.value = result
      progress.value = 1
      
      return task_id
    } catch (e: any) {
      error.value = e.message || '未知错误'
      for (const [key, state] of Object.entries(agentStates.value)) {
        if (state.status === 'running') {
          updateAgentState(key, { status: 'failed' })
        }
      }
      throw e
    } finally {
      isProcessing.value = false
    }
  }
  
  async function runAnalysis(data: AnalysisRequest): Promise<CrewResult> {
    isProcessing.value = true
    error.value = null
    progress.value = 0
    resetAgentStates()
    
    try {
      updateAgentState('resume_analyzer', { status: 'running' })
      
      const result = await crewApi.runAnalysis(data)
      
      if (result.success) {
        updateAgentState('resume_analyzer', { status: 'completed' })
        lastResult.value = result
        progress.value = 1
      } else {
        throw new Error(result.error || '分析执行失败')
      }
      
      return result
    } catch (e: any) {
      error.value = e.message || '未知错误'
      updateAgentState('resume_analyzer', { status: 'failed' })
      throw e
    } finally {
      isProcessing.value = false
    }
  }
  
  async function runMatching(data: MatchRequest): Promise<CrewResult> {
    isProcessing.value = true
    error.value = null
    progress.value = 0
    
    try {
      updateAgentState('job_matcher', { status: 'running' })
      
      const result = await crewApi.runMatching(data)
      
      if (result.success) {
        updateAgentState('job_matcher', { status: 'completed' })
        lastResult.value = result
        progress.value = 1
      } else {
        throw new Error(result.error || '匹配执行失败')
      }
      
      return result
    } catch (e: any) {
      error.value = e.message || '未知错误'
      updateAgentState('job_matcher', { status: 'failed' })
      throw e
    } finally {
      isProcessing.value = false
    }
  }
  
  async function cancelTask(): Promise<void> {
    if (currentTaskId.value) {
      try {
        await crewApi.cancelTask(currentTaskId.value)
      } catch (e) {
        console.error('Cancel task failed:', e)
      }
    }
    
    currentTaskId.value = null
    taskStatus.value = null
    isProcessing.value = false
    resetAgentStates()
  }
  
  function reset() {
    currentTaskId.value = null
    taskStatus.value = null
    resetAgentStates()
    lastResult.value = null
    isProcessing.value = false
    progress.value = 0
    error.value = null
  }
  
  return {
    currentTaskId,
    taskStatus,
    agentStates,
    lastResult,
    isProcessing,
    progress,
    error,
    currentAgent,
    isCompleted,
    isFailed,
    resetAgentStates,
    updateAgentState,
    runWorkflow,
    startAsyncWorkflow,
    runAnalysis,
    runMatching,
    cancelTask,
    reset
  }
})
