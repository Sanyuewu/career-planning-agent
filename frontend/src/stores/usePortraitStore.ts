import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { portraitApi } from '../api/portrait'
import { useUserStore } from './useUserStore'
import { clearOtherUsersKeys, clearAllKeys, isExpired } from '../utils/storage'
import type { TransferPath } from '../types'

export type { TransferPath }

export interface PortraitData {
  studentId: string
  basicInfo: {
    name?: string
    school?: string
    major?: string
    grade?: string
  }
  education: any[]
  skills: string[]
  internships: any[]
  projects: any[]
  certs: string[]
  awards: string[]
  careerIntent?: string
  inferredSoftSkills: Record<string, { score?: number; evidence?: string }>
  completeness: number
  competitiveness: number
  competitivenessLevel: string
  highlights: string[]
  weaknesses: string[]
  transferOpportunities: TransferPath[]
  // 多维画像扩展
  interests: string[]
  abilityProfile: Record<string, number>
  personalityTraits: string[]
  preferredCities: string[]
  culturePreference: string[]
}

const STORAGE_KEY_PREFIX = 'portrait_data_'
const SYNC_TS_KEY_PREFIX = 'portrait_sync_at_'
const STALE_AFTER_MS = 5 * 60 * 1000

function getStorageKey(studentId: string): string {
  return `${STORAGE_KEY_PREFIX}${studentId}`
}

function getSyncTsKey(studentId: string): string {
  return `${SYNC_TS_KEY_PREFIX}${studentId}`
}

function clearOtherUsersData(currentStudentId: string) {
  clearOtherUsersKeys([STORAGE_KEY_PREFIX, SYNC_TS_KEY_PREFIX], currentStudentId)
}

function clearAllPortraitData() {
  clearAllKeys([STORAGE_KEY_PREFIX, SYNC_TS_KEY_PREFIX])
}

export const usePortraitStore = defineStore('portrait', () => {
  const portrait = ref<PortraitData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function loadFromStorage() {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    if (!studentId) return

    try {
      const storageKey = getStorageKey(studentId)
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const data = JSON.parse(saved)
        if (data.studentId === studentId) {
          portrait.value = data
        } else {
          localStorage.removeItem(storageKey)
          localStorage.removeItem(getSyncTsKey(studentId))
        }
      }
    } catch (e) {
      console.error('Failed to load portrait from storage:', e)
    }
  }

  function saveToStorage() {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    if (!studentId) return

    if (portrait.value) {
      localStorage.setItem(getStorageKey(studentId), JSON.stringify(portrait.value))
      localStorage.setItem(getSyncTsKey(studentId), Date.now().toString())
    } else {
      localStorage.removeItem(getStorageKey(studentId))
      localStorage.removeItem(getSyncTsKey(studentId))
    }
  }

  function isStale(): boolean {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    if (!studentId) return true
    return isExpired(getSyncTsKey(studentId), STALE_AFTER_MS)
  }

  let _refreshing: Promise<void> | null = null

  /** 如果缓存已陈旧（>5分钟），从后端刷新，否则直接用本地缓存 */
  async function ensureFresh() {
    if (portrait.value && !isStale()) return
    if (_refreshing) return _refreshing
    _refreshing = loadPortrait().finally(() => { _refreshing = null })
    return _refreshing
  }
  
  async function loadPortrait() {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    
    if (!studentId) {
      error.value = '请先上传简历'
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const result = await portraitApi.get(studentId)
      
      portrait.value = {
        studentId: result.student_id,
        basicInfo: result.basic_info || {},
        education: result.education || [],
        skills: result.skills || [],
        internships: result.internships || [],
        projects: result.projects || [],
        certs: result.certs || [],
        awards: result.awards || [],
        careerIntent: result.career_intent,
        inferredSoftSkills: result.inferred_soft_skills || {},
        completeness: result.completeness || 0,
        competitiveness: result.competitiveness || 0,
        competitivenessLevel: result.competitiveness_level || '一般',
        highlights: result.highlights || [],
        weaknesses: result.weaknesses || [],
        transferOpportunities: result.transfer_opportunities || [],
        interests: result.interests || [],
        abilityProfile: result.ability_profile || {},
        personalityTraits: result.personality_traits || [],
        preferredCities: result.preferred_cities || [],
        culturePreference: result.culture_preference || [],
      }

      saveToStorage()

      userStore.setStudentInfo({
        completeness: result.completeness,
        competitiveness: result.competitiveness,
        competitivenessLevel: result.competitiveness_level,
      })
      
      if (result.basic_info?.name || result.skills?.length) {
        userStore.setProfile({
          studentId: result.student_id,
          name: result.basic_info?.name || userStore.studentName,
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
      }
    } catch (e: any) {
      error.value = e.message || '加载画像失败'
    } finally {
      loading.value = false
    }
  }
  
  async function updatePortrait(data: Partial<PortraitData>) {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    
    if (!studentId) {
      error.value = '请先上传简历'
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const updateData: any = {}
      
      if (data.basicInfo) updateData.basic_info = data.basicInfo
      if (data.education) updateData.education = data.education
      if (data.skills) updateData.skills = data.skills
      if (data.internships) updateData.internships = data.internships
      if (data.projects) updateData.projects = data.projects
      if (data.certs !== undefined) updateData.certs = data.certs
      if (data.awards !== undefined) updateData.awards = data.awards
      if (data.careerIntent) updateData.career_intent = data.careerIntent
      
      const result = await portraitApi.update(studentId, updateData)
      
      portrait.value = {
        studentId: result.student_id,
        basicInfo: result.basic_info || {},
        education: result.education || [],
        skills: result.skills || [],
        internships: result.internships || [],
        projects: result.projects || [],
        certs: result.certs || [],
        awards: result.awards || [],
        careerIntent: result.career_intent,
        inferredSoftSkills: result.inferred_soft_skills || {},
        completeness: result.completeness || 0,
        competitiveness: result.competitiveness || 0,
        competitivenessLevel: result.competitiveness_level || '一般',
        highlights: result.highlights || [],
        weaknesses: result.weaknesses || [],
        transferOpportunities: result.transfer_opportunities || [],
        interests: result.interests || [],
        abilityProfile: result.ability_profile || {},
        personalityTraits: result.personality_traits || [],
        preferredCities: result.preferred_cities || [],
        culturePreference: result.culture_preference || [],
      }

      saveToStorage()

      userStore.setProfile({
        studentId: result.student_id,
        name: result.basic_info?.name || userStore.studentName,
        school: result.basic_info?.school || '',
        major: result.basic_info?.major,
        skills: result.skills || [],
        education: result.education || [],
        internships: result.internships || [],
        projects: result.projects || [],
        completeness: result.completeness || 0,
        competitiveness: result.competitiveness || 0,
        competitivenessLevel: result.competitiveness_level || '一般',
      })
      Message.success('画像已保存')
    } catch (e: any) {
      error.value = e.message || '更新画像失败'
      Message.error(error.value!)
    } finally {
      loading.value = false
    }
  }
  
  function setPortrait(data: PortraitData) {
    portrait.value = data
    saveToStorage()
  }

  function setTransferOpportunities(transfers: TransferPath[]) {
    if (portrait.value) {
      portrait.value.transferOpportunities = transfers
      saveToStorage()
    }
  }
  
  function clearPortrait() {
    const userStore = useUserStore()
    const studentId = userStore.studentId
    portrait.value = null
    error.value = null
    if (studentId) {
      localStorage.removeItem(getStorageKey(studentId))
      localStorage.removeItem(getSyncTsKey(studentId))
    }
  }

  loadFromStorage()

  return {
    portrait,
    loading,
    error,
    loadPortrait,
    updatePortrait,
    setPortrait,
    setTransferOpportunities,
    clearPortrait,
    clearAllPortraitData,
    clearOtherUsersData,
    loadFromStorage,
    ensureFresh,
    isStale,
  }
})
