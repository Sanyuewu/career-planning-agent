export interface TransferOpportunity {
  target: string
  title: string
  match_level: string
  overlap_pct?: number
  advantage?: string
  need_learn?: string[]
}

export interface ResumeParseResult {
  student_id: string
  basic_info: {
    name: string
    school?: string
    major?: string
    grade?: string
  }
  education: Array<{
    degree?: string
    school: string
    major: string
    gpa?: number
  }>
  skills: string[]
  internships: Array<{
    company: string
    role: string
    duration_months?: number
    description?: string
  }>
  projects: Array<{
    name: string
    tech_stack?: string[]
    description?: string
  }>
  certs: string[]
  awards: string[]
  career_intent?: string
  inferred_soft_skills: Record<string, { score?: number; evidence?: string }>
  completeness: number
  missing_dims: string[]
  competitiveness: number
  competitiveness_level: string
  transfer_opportunities?: TransferOpportunity[]
  gap_mapped_transfers?: Array<{
    target: string
    title: string
    gaps: string[]
  }>
}

export const resumeApi = {
  parse(file: File, onProgress?: (percent: number) => void): Promise<ResumeParseResult> {
    const formData = new FormData()
    formData.append('file', file)
    
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 50)
          onProgress(percent)
        }
      })
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText)
            if (onProgress) {
              onProgress(100)
            }
            if (response.result) {
              resolve(response.result)
            } else {
              reject(new Error(response.message || '解析失败'))
            }
          } catch (e) {
            reject(new Error('解析响应格式错误'))
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText)
            reject(new Error(error.detail || '上传失败'))
          } catch {
            reject(new Error('上传失败'))
          }
        }
      })
      
      xhr.addEventListener('error', () => {
        reject(new Error('网络错误'))
      })
      
      xhr.open('POST', '/api/resume/parse')
      const token = localStorage.getItem('access_token')
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }
      xhr.send(formData)
    })
  }
}
