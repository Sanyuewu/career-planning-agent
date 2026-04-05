import { request } from './http'

export interface ReportGenerateResult {
  task_id?: string
  report_id?: string
  student_id?: string
  job_name?: string
  overall_score?: number
  confidence?: number
  dimensions?: any
  action_plan?: any[]
  skill_gaps?: any[]
  career_path?: any[]
  chapters_json?: any[]
  created_at?: string
}

export interface ReportStatus {
  status: string
  progress: number
  message?: string
  error_msg?: string
  result?: ReportGenerateResult
}

export interface ReportDetail {
  report_id: string
  student_id: string
  job_name: string
  overall_score: number
  confidence?: number
  dimensions: any
  action_plan: any[]
  skill_gaps: any[]
  career_path: any[]
  chapters_json?: any[]
  created_at: string
}

export interface ReportUpdateData {
  action_plan?: any[]
  skill_gaps?: any[]
  career_path?: any[]
}

export const reportApi = {
  generate(studentId: string, jobName: string): Promise<ReportGenerateResult> {
    const params = new URLSearchParams()
    params.append('student_id', studentId)
    params.append('job_name', jobName)
    return request.post(`/report/generate?${params.toString()}`)
  },
  
  getStatus(taskId: string): Promise<ReportStatus> {
    return request.get(`/report/status/${taskId}`)
  },
  
  get(reportId: string): Promise<ReportDetail> {
    return request.get(`/report/${reportId}`)
  },
  
  update(reportId: string, data: ReportUpdateData): Promise<{ success: boolean; message: string }> {
    return request.put(`/report/${reportId}`, data)
  },
  
  polish(reportId: string, options?: { chapter_titles?: string[]; feedback_hint?: string }): Promise<ReportDetail & { snapshot_hash?: string; chapters_json?: any[] }> {
    return request.post(`/report/${reportId}/polish`, options || {})
  },

  undoPolish(reportId: string): Promise<{ report_id: string; undone: boolean; message: string }> {
    return request.post(`/report/${reportId}/undo_polish`, {})
  },

  getCompleteness(reportId: string): Promise<{completeness_score: number, is_complete: boolean, issues: {field: string, label: string, severity: string, msg: string}[]}> {
    return request.get(`/report/${reportId}/completeness`)
  },

  adjust(reportId: string, data: { feedback_summary?: string; focus_chapters?: string[] }): Promise<{ adjusted: boolean; chapters_count: number }> {
    return request.post(`/report/${reportId}/adjust`, data)
  },

  feedbackOptimize(reportId: string, data: { rating: number; issues: string[]; comment: string; chapters?: string[] | null }): Promise<{ report_id: string; optimized: boolean; chapters_count: number; chapters_json: any[]; snapshot_saved: boolean }> {
    return request.post(`/report/${reportId}/feedback_optimize`, data)
  },
}
