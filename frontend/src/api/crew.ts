import { request } from './http'

export interface CrewResult {
  success: boolean
  status: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  results?: Record<string, any>
  error?: string
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
}

export interface WorkflowRequest {
  resume_content: string
  parsed_data?: Record<string, any>
  target_jobs?: string[]
  student_id?: string
}

export interface AnalysisRequest {
  resume_content: string
  parsed_data?: Record<string, any>
}

export interface MatchRequest {
  resume_analysis: Record<string, any>
  target_jobs: string[]
}

export interface CrewStatus {
  crewai_installed: boolean
  crewai_version?: string
  llm_provider: string
  llm_model: string
  llm_configured: boolean
}

export interface AgentState {
  status: 'idle' | 'running' | 'completed' | 'failed'
  task?: string
  started_at?: string
  completed_at?: string
  confidence?: number
}

export const crewApi = {
  runWorkflow: async (data: WorkflowRequest): Promise<CrewResult> => {
    const res = await request.post<CrewResult>('/agent/crew/workflow', data)
    return res
  },
  
  startAsyncWorkflow: async (data: WorkflowRequest): Promise<{ task_id: string }> => {
    const res = await request.post<{ task_id: string }>('/agent/crew/workflow/async', data)
    return res
  },
  
  runAnalysis: async (data: AnalysisRequest): Promise<CrewResult> => {
    const res = await request.post<CrewResult>('/agent/crew/analysis', data)
    return res
  },
  
  runMatching: async (data: MatchRequest): Promise<CrewResult> => {
    const res = await request.post<CrewResult>('/agent/crew/match', data)
    return res
  },
  
  getStatus: async (): Promise<CrewStatus> => {
    const res = await request.get<CrewStatus>('/agent/crew/status')
    return res
  },
  
  getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
    const res = await request.get<TaskStatus>(`/agent/status/${taskId}`)
    return res
  },
  
  getTaskResult: async (taskId: string): Promise<CrewResult> => {
    const res = await request.get<CrewResult>(`/agent/result/${taskId}`)
    return res
  },
  
  pollTaskUntilComplete: async (
    taskId: string,
    onProgress?: (progress: number, status?: TaskStatus) => void,
    maxAttempts: number = 150,
    interval: number = 2000
  ): Promise<CrewResult> => {
    for (let i = 0; i < maxAttempts; i++) {
      const status = await crewApi.getTaskStatus(taskId)
      
      onProgress?.(status.progress, status)
      
      if (status.status === 'completed') {
        return await crewApi.getTaskResult(taskId)
      }
      
      if (status.status === 'failed') {
        const result = await crewApi.getTaskResult(taskId)
        throw new Error(result.error || status.error || '任务执行失败')
      }
      
      await new Promise(resolve => setTimeout(resolve, interval))
    }
    
    throw new Error('任务执行超时，请稍后重试')
  },
  
  cancelTask: async (taskId: string): Promise<{ task_id: string; status: string }> => {
    const res = await request.delete<{ task_id: string; status: string }>(`/agent/task/${taskId}`)
    return res
  }
}

