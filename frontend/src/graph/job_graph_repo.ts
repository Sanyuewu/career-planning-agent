import jobGraphData from '../../../data/job_graph.json'

export interface JobInfo {
  title: string
  salary?: string
  industry?: string
  education?: string
  experience?: string
  skills?: string[]
  overview?: string
  responsibilities?: string[]
  demandLevel?: string
  certRequirements?: string[]
  innovationReq?: string
  learningReq?: string
  stressReq?: string
  communicationReq?: string
  internshipReq?: string
}

class JobGraphRepository {
  private nodeMap: Record<string, any> = {}

  constructor() {
    if (Array.isArray(jobGraphData?.nodes)) {
      for (const node of (jobGraphData as any).nodes) {
        if (node.id && node.attrs !== undefined) {
          this.nodeMap[node.id] = node.attrs || {}
        }
      }
    }
  }

  getJobInfo(jobTitle: string): JobInfo | null {
    const nodeId = `job_${jobTitle}`
    const attrs = this.nodeMap[nodeId]
    if (!attrs || Object.keys(attrs).length === 0) return null

    return {
      title: attrs.title || jobTitle,
      salary: attrs.salary,
      industry: attrs.industry,
      education: attrs.education_level,
      skills: attrs.skills || [],
      overview: attrs.overview,
      responsibilities: attrs.responsibilities || [],
      demandLevel: 'medium',
      certRequirements: attrs.cert_requirements || [],
      innovationReq: attrs.innovation_req,
      learningReq: attrs.learning_req,
      stressReq: attrs.stress_req,
      communicationReq: attrs.communication_req,
      internshipReq: attrs.internship_req,
    }
  }
}

export const jobGraph = new JobGraphRepository()
