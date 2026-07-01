import { http } from '@/lib/http'

export interface ReportChapter { title: string; content: string }

export interface ReportDetail {
  report_id: string
  student_id: string
  job_name: string
  overall_score: number
  dimensions?: any
  action_plan?: any[]
  skill_gaps?: any[]
  career_path?: any[]
  chapters_json?: ReportChapter[]
  created_at?: string
}

export interface ReportStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed' | string
  progress: number
  message?: string
  error_msg?: string
  report_id?: string
  result?: ReportDetail
}

export const reportApi = {
  generate: (sid: string, jobName: string) =>
    http.post<{ task_id: string; report_id: string }>('/report/generate', undefined, { student_id: sid, job_name: jobName }),
  status: (taskId: string) => http.get<ReportStatus>(`/report/status/${taskId}`),
  get: (reportId: string) => http.get<ReportDetail>(`/report/${reportId}`),
  /** 导出文件流（fmt: 'pdf' | 'word'） */
  exportFile: (reportId: string, fmt: 'pdf' | 'word') => http.raw(`/report/${reportId}/${fmt}`),
}
