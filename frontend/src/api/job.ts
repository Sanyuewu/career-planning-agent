import { http } from '@/lib/http'
import { matchApi } from './match'

export interface JobInfo {
  title: string
  salary?: string
  industry?: string
  education?: string
  skills?: string[]
  overview?: string
  responsibilities?: string[]
  top_regions?: string[]
  tags?: string[]
}

export interface CareerPaths {
  nodes: Array<{ id: string; title: string; salary?: string }>
  edges: Array<{ from: string; to: string; type: string; label?: string }>
  promotion_paths?: any[]
  transfer_paths?: any[]
}

export const jobApi = {
  list: () => matchApi.jobs(),
  info: (title: string) => http.get<JobInfo>('/jobs/info', { job: title }),
  careerGraph: (title: string) => http.get<CareerPaths>('/jobs/career-graph', { job: title }),
}
