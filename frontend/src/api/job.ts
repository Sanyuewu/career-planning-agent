import { request } from './http'

export interface JobInfo {
  title: string
  salary?: string
  industry?: string
  education?: string
  experience?: string
  skills?: string[]
  overview?: string
  responsibilities?: string[]
  top_regions?: string[]
  culture_types?: string[]
  majors?: string[]
  tags?: string[]
}

export interface GraphPathData {
  nodes: Array<{
    id: string
    title: string
    industry?: string
    salary?: string
  }>
  edges: Array<{
    from: string
    to: string
    type: string
    label?: string
  }>
  promotion_paths?: Array<{
    from: string
    to: string
    years?: string
    description?: string
  }>
  transfer_paths?: Array<{
    target: string
    match_level?: string
    overlap_pct?: number
    advantage?: string
    need_learn?: string
  }>
}

export interface CareerPaths {
  nodes: Array<{ id: string; title: string; salary?: string }>
  edges: Array<{ from: string; to: string; type: string; label?: string }>
  promotion_paths?: Array<{
    nodes: Array<{ title: string; salary?: string }>
    transitions?: Array<{ to?: string; years?: string; description?: string }>
  }>
  transfer_paths?: Array<{
    target: string
    title?: string
    match_level?: string
    overlap_pct?: number
    advantage?: string
    need_learn?: string
  }>
}

export interface RealJobSample {
  company_name: string
  salary?: string
  address?: string
  size?: string
  description?: string
}

export interface RealJobData {
  jd_count: number
  avg_salary_k: number
  top_companies: string[]
  samples?: RealJobSample[]
}

export interface MainTransfers {
  main: {
    title: string
    salary?: string
    industry?: string
    description?: string
  } | null
  transfers: Array<{
    target: string
    title?: string
    match_level: string
    overlap_pct?: number
    advantage?: string
    need_learn?: string
    target_info?: {
      title?: string
      industry?: string
      salary?: string
    }
  }>
  graph: {
    nodes: Array<{ id: string; title?: string }>
    edges: Array<{ from: string; to: string; type?: string; label?: string }>
  }
}

export interface LiveJob {
  id: number
  job_name: string
  raw_title: string
  company: string
  city: string
  salary_raw: string
  salary_min_k: number
  salary_max_k: number
  skills: string[]
  description: string
  source: string
  source_url: string
  fetched_at: string
  is_active: number
}

export interface LiveJobStats {
  job_name: string
  jd_count: number
  avg_salary_k: number
  last_fetched: string
}

export const jobApi = {
  async getJobs(): Promise<string[]> {
    return request.get('/match/jobs').then((res: any) => {
      if (Array.isArray(res)) return res
      const jobs = res.jobs || []
      return jobs.map((j: any) => j.title || j.job_name || j)
    })
  },

  async getJobInfo(jobTitle: string): Promise<JobInfo> {
    return request.get<JobInfo>(`/jobs/info?job=${encodeURIComponent(jobTitle)}`)
  },

  async getCareerGraph(jobTitle: string): Promise<CareerPaths> {
    return request.get<CareerPaths>(`/jobs/career-graph?job=${encodeURIComponent(jobTitle)}`)
  },

  async getRealJobs(jobTitle: string, limit: number = 10): Promise<RealJobData> {
    return request.get<RealJobData>(`/jobs/real?job=${encodeURIComponent(jobTitle)}&limit=${limit}`)
  },

  /** 搜索岗位 */
  async search(query: string, limit: number = 10): Promise<Array<{id: string, title: string, industry: string, salary: string}>> {
    return request.get(`/jobs/search?query=${encodeURIComponent(query)}&limit=${limit}`)
  },

  /** ✅ 新增：任务专用API - 主岗位 + 换岗派生节点 */
  async getMainTransfers(jobName: string): Promise<MainTransfers> {
    return request.get<MainTransfers>(`/graph/main-transfers/${encodeURIComponent(jobName)}`)
  },

  /** 获取市场趋势数据 */
  async getMarketTrend(jobName: string): Promise<any> {
    return request.get(`/market/trend?job_name=${encodeURIComponent(jobName)}`)
  },

  /** 查询实时抓取岗位列表 */
  async getLiveJobs(params: {
    job_name?: string
    city?: string
    salary_min_k?: number
    limit?: number
    offset?: number
  }): Promise<{ jobs: LiveJob[]; count: number; offset: number }> {
    const query = new URLSearchParams()
    if (params.job_name) query.set('job_name', params.job_name)
    if (params.city) query.set('city', params.city)
    if (params.salary_min_k != null) query.set('salary_min_k', String(params.salary_min_k))
    if (params.limit != null) query.set('limit', String(params.limit))
    if (params.offset != null) query.set('offset', String(params.offset))
    return request.get(`/jobs/live?${query.toString()}`)
  },

  /** 实时岗位均薪/数量统计 */
  async getLiveJobStats(jobNames?: string[]): Promise<{ stats: LiveJobStats[]; total_active: number; as_of: string }> {
    const q = jobNames ? `?job_names=${encodeURIComponent(jobNames.join(','))}` : ''
    return request.get(`/jobs/live/stats${q}`)
  },

  /** F-4: AI 岗位洞察（LLM 实时生成） */
  async getAiInsight(jobName: string): Promise<{ job_name: string; insight: string; core_skills: string[]; salary: string; industry: string; generated_by: string }> {
    return request.get(`/jobs/ai_insight?job_name=${encodeURIComponent(jobName)}`)
  },

  /** B-6: 实时均薪 vs 历史均薪对比 */
  async getSalaryComparison(jobName: string): Promise<{
    job_name: string
    live_avg_k: number
    live_count: number
    historical_avg_k: number
    historical_count: number
    change_pct: number
    insufficient_data: boolean
  }> {
    return request.get(`/market/salary_comparison?job_name=${encodeURIComponent(jobName)}`)
  },
}
