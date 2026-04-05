import { ref } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { resumeApi } from '../api/resume'

const STEPS = [
  { label: '📖 读取文件内容', progress: 15 },
  { label: '🔍 OCR文字识别', progress: 35 },
  { label: '🤖 AI结构化抽取', progress: 65 },
  { label: '🔗 技能归一化处理', progress: 80 },
  { label: '📊 完整度评分计算', progress: 95 },
]

export function useUpload() {
  const uploading = ref(false)
  const parseProgress = ref(0)
  const parseStatus = ref<'idle' | 'uploading' | 'parsing' | 'done' | 'failed'>('idle')
  const parseSteps = ref(STEPS.map(s => ({ ...s, done: false })))
  const missingDims = ref<string[]>([])
  const parseResult = ref<any>(null)
  const error = ref<string | null>(null)
  
  const userStore = useUserStore()
  
  const DIM_LABELS: Record<string, string> = {
    soft_skills: '软技能评估',
    career_intent: '求职意向',
    certs: '证书信息',
    projects: '项目经验',
    internships: '实习经历',
    awards: '获奖经历',
  }
  
  async function uploadResume(file: File): Promise<boolean> {
    if (file.size > 10 * 1024 * 1024) {
      error.value = '文件大小超过10MB限制'
      return false
    }
    
    uploading.value = true
    parseStatus.value = 'uploading'
    parseProgress.value = 5
    parseSteps.value = STEPS.map(s => ({ ...s, done: false }))
    error.value = null
    parseResult.value = null
    
    try {
      const result = await resumeApi.parse(file, (percent) => {
        parseProgress.value = Math.min(percent, 50)
        
        const stepIdx = STEPS.findIndex(s => s.progress > percent * 2)
        if (stepIdx > 0) {
          for (let i = 0; i < stepIdx; i++) {
            parseSteps.value[i].done = true
          }
        }
      })
      
      parseStatus.value = 'parsing'
      
      for (let i = 0; i < STEPS.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 300))
        parseSteps.value[i].done = true
        parseProgress.value = 50 + (i + 1) * 10
      }
      
      parseProgress.value = 100
      parseStatus.value = 'done'
      missingDims.value = result.missing_dims || []
      parseResult.value = result
      
      userStore.setProfile({
        studentId: result.student_id,
        name: result.basic_info?.name || '',
        school: result.basic_info?.school || '',
        major: result.basic_info?.major,
        skills: result.skills || [],
        education: result.education || [],
        internships: result.internships || [],
        projects: result.projects || [],
        completeness: result.completeness,
        competitiveness: result.competitiveness,
        competitivenessLevel: result.competitiveness_level,
      })
      
      return true
    } catch (e: any) {
      parseStatus.value = 'failed'
      error.value = e.message || '解析失败，请重试'
      return false
    } finally {
      uploading.value = false
    }
  }
  
  function reset() {
    uploading.value = false
    parseProgress.value = 0
    parseStatus.value = 'idle'
    parseSteps.value = STEPS.map(s => ({ ...s, done: false }))
    missingDims.value = []
    parseResult.value = null
    error.value = null
  }
  
  return {
    uploading,
    parseProgress,
    parseStatus,
    parseSteps,
    missingDims,
    parseResult,
    error,
    DIM_LABELS,
    uploadResume,
    reset,
  }
}

export function useFileUpload(options: {
  accept?: string
  maxSize?: number
  multiple?: boolean
} = {}) {
  const file = ref<File | null>(null)
  const files = ref<File[]>([])
  const progress = ref(0)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  
  const maxSize = options.maxSize || 10 * 1024 * 1024
  const accept = options.accept || ''
  
  function validateFile(f: File): boolean {
    if (maxSize && f.size > maxSize) {
      error.value = `文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`
      return false
    }
    
    if (accept) {
      const acceptTypes = accept.split(',').map(t => t.trim())
      const fileExt = '.' + f.name.split('.').pop()?.toLowerCase()
      
      const isAccepted = acceptTypes.some(type => {
        if (type.startsWith('.')) {
          return fileExt === type.toLowerCase()
        }
        return f.type === type
      })
      
      if (!isAccepted) {
        error.value = `只支持 ${accept} 格式的文件`
        return false
      }
    }
    
    return true
  }
  
  function setFile(f: File) {
    error.value = null
    if (validateFile(f)) {
      file.value = f
      if (!options.multiple) {
        files.value = [f]
      }
    }
  }
  
  function addFile(f: File) {
    error.value = null
    if (validateFile(f)) {
      files.value.push(f)
      if (files.value.length === 1) {
        file.value = f
      }
    }
  }
  
  function removeFile(index?: number) {
    if (index !== undefined) {
      files.value.splice(index, 1)
      if (file.value === files.value[index]) {
        file.value = files.value[0] || null
      }
    } else {
      file.value = null
      files.value = []
    }
  }
  
  function clear() {
    file.value = null
    files.value = []
    progress.value = 0
    uploading.value = false
    error.value = null
  }
  
  function handleDrop(e: DragEvent) {
    e.preventDefault()
    const droppedFiles = Array.from(e.dataTransfer?.files || [])
    
    if (options.multiple) {
      droppedFiles.forEach(f => addFile(f))
    } else if (droppedFiles.length > 0) {
      setFile(droppedFiles[0])
    }
  }
  
  function handleInputChange(e: Event) {
    const input = e.target as HTMLInputElement
    const selectedFiles = Array.from(input.files || [])
    
    if (options.multiple) {
      selectedFiles.forEach(f => addFile(f))
    } else if (selectedFiles.length > 0) {
      setFile(selectedFiles[0])
    }
    
    input.value = ''
  }
  
  return {
    file,
    files,
    progress,
    uploading,
    error,
    setFile,
    addFile,
    removeFile,
    clear,
    handleDrop,
    handleInputChange,
  }
}
