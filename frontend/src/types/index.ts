export interface BasicInfo {
  name: string
  school?: string
  major?: string
  grade?: string
  phone?: string
  email?: string
}

export interface Education {
  degree: string
  school: string
  major: string
  gpa?: number
  startDate?: string
  endDate?: string
}

export interface Experience {
  company: string
  role: string
  duration?: string
  description?: string
}

export interface Project {
  name: string
  techStack?: string[]
  description?: string
  role?: string
}

export interface ResumeParseResult {
  basicInfo: BasicInfo
  education: Education[]
  skills: string[]
  internships: Experience[]
  projects: Project[]
  certs: string[]
  awards: string[]
  careerIntent?: string
  inferredSoftSkills?: Record<string, { score: number; evidence: string }>
  completeness: number
  missingDims: string[]
}

export interface StudentPortrait {
  studentId: string
  basicInfo: BasicInfo
  education: Education[]
  skills: string[]
  internships: Experience[]
  projects: Project[]
  certs: string[]
  awards: string[]
  careerIntent?: string
  inferredSoftSkills?: Record<string, { score: number; evidence: string }>
  completeness: number
  competitiveness: number
  competitivenessLevel: string
  highlights: string[]
  weaknesses: string[]
}

export interface GapItem {
  skill: string
  importance: string
  jdSource: string
  suggestion: string
}

export interface DimensionScore {
  score: number
  detail: string
  evidence: string
}

export interface ProfessionalSkillsScore {
  score: number
  matchedSkills: string[]
  gapSkills: GapItem[]
  semanticMatched: Array<{
    studentSkill: string
    jobSkill: string
    similarity: number
  }>
}

export interface MatchDimensions {
  basicRequirements: DimensionScore
  professionalSkills: ProfessionalSkillsScore
  professionalQualities: DimensionScore
  developmentPotential: DimensionScore
}

export interface SkillMatchDetail {
  skillName: string
  matchStatus: 'matched' | 'partial' | 'missing' | 'semantic_matched'
  jobRequirement?: string
  studentEvidence?: string
  similarityScore?: number
  importance: 'must_have' | 'nice_to_have'
}

export interface ImprovementSuggestion {
  suggestion: string
  priority: 'high' | 'medium' | 'low'
  timeline?: string
  resources?: string[]
}

export interface GapAnalysis {
  gapDescription: string
  severity: 'critical' | 'moderate' | 'minor'
  impact: string
  improvementSuggestions: ImprovementSuggestion[]
}

export interface ConfidenceBreakdown {
  dataQuality: number
  matchPrecision: number
  evidenceStrength: number
  overallConfidence: number
  factors: Record<string, string>
}

export interface MatchResult {
  jobId: string
  jobTitle: string
  overallScore: number
  confidence: number
  dimensions: MatchDimensions
  weightUsed: Record<string, number>
  summary: string
  skillMatchDetails?: SkillMatchDetail[]
  gapAnalysis?: GapAnalysis[]
  confidenceBreakdown?: ConfidenceBreakdown
}

export interface JobInfo {
  id: string
  title: string
  industry?: string
  salary?: string
  skills?: string[]
}

export interface CareerReport {
  reportId: string
  studentId: string
  jobName: string
  overallScore: number
  dimensions: MatchDimensions
  actionPlan: Array<{
    phase: string
    goals: string[]
    timeline: string
  }>
  skillGaps: GapItem[]
  careerPath: Array<{
    job: string
    years: number
    description: string
  }>
  createdAt: string
}

export interface ReportProgress {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  result?: CareerReport
  error?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  state?: string
  emotion?: string
  timestamp: string
}

export interface ChatSession {
  sessionId: string
  state: string
  messages: ChatMessage[]
  emotionScore: number
  turnCount: number
}

export interface CareerGraphNode {
  id: string
  title: string
  name?: string
  industry?: string
  salary?: string
}

export interface CareerGraphEdge {
  from: string
  to: string
  type: 'PROMOTES_TO' | 'CAN_TRANSFER_TO' | 'SIMILAR_TO'
  label?: string
}

export interface CareerGraphData {
  nodes: CareerGraphNode[]
  edges: CareerGraphEdge[]
}

export interface JobTrendData {
  snapshotDate: string
  demandIndex: number
  jdCount: number
  avgSalary: number
  topSkills: string[]
}

export interface PortraitHistoryItem {
  version: number
  portrait: StudentPortrait
  completeness: number
  competitiveness: number
  snapshotReason: string
  createdAt: string
}

export interface ApiResponse<T = unknown> {
  success: boolean
  code: number
  message: string
  data: T
  timestamp: string
}

export interface PaginatedResponse<T = unknown> {
  success: boolean
  code: number
  message: string
  data: T[]
  total: number
  page: number
  pageSize: number
}

// ── 匹配相关（后端 snake_case 风格，API 层直接使用） ──

export interface MarketDemand {
  score: number
  jd_count: number
  avg_salary_k: number
  top_companies: string[]
  detail: string
}

export interface TransferPath {
  target: string
  title?: string
  match_level?: string
  overlap_pct?: number
  advantage?: string
  need_learn?: string | string[]
  gaps?: string[]
}

export interface GapSkill {
  skill: string
  importance: 'must_have' | 'nice_to_have'
  suggestion?: string
  jd_source?: string
}

export interface MatchDimension {
  score: number
  detail?: string
  evidence?: string
  matched_skills?: string[]
  gap_skills?: Array<{
    skill: string
    importance?: 'must_have' | 'nice_to_have'
    suggestion?: string
    jd_source?: string
  }>
}
