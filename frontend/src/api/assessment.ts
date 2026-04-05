// 测评功能暂时隐藏，相关 API 注释
// import { request } from './http'
//
// export interface AssessmentQuestions {
//   logic: any[]
//   career_tendency: any[]
//   tech_self_assessment: any[]
//   tech_job_hint: string
// }
//
// export interface AssessmentResult {
//   logic_score: number
//   tendency_dimensions: Record<string, number>
//   tech_scores: Record<string, number>
//   ability_profile_update: Record<string, number>
//   overall: number
//   profile_updated?: boolean
//   merged_ability_profile?: Record<string, number>
// }
//
// export const assessmentApi = {
//   getQuestions(jobHint: string = ''): Promise<AssessmentQuestions> {
//     return request.get(`/assessment/questions?job_hint=${encodeURIComponent(jobHint)}`)
//   },
//   submit(data: {
//     student_id: string | null
//     answers: Array<{ q_id: string; answer: string }>
//     job_hint: string
//   }): Promise<AssessmentResult> {
//     return request.post('/assessment/submit', data)
//   },
// }
