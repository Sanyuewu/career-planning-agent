<template>
  <div class="company-page">
    <div class="page-header">
      <div class="header-left">
        <h1>企业工作台</h1>
        <p class="sub">管理企业信息，发布岗位，寻找匹配候选人</p>
      </div>
      <div class="header-actions">
        <button class="action-btn primary" @click="showPostJob = true">
          <span>📝</span> 发布新岗位
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-item">
        <span class="stat-value">{{ postedJobs.length }}</span>
        <span class="stat-label">已发布岗位</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ totalCandidates }}</span>
        <span class="stat-label">匹配候选人</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ savedCandidates.length }}</span>
        <span class="stat-label">收藏候选人</span>
      </div>
    </div>

    <div class="main-tabs">
      <button :class="['tab', { active: activeTab === 'jobs' }]" @click="activeTab = 'jobs'">岗位管理</button>
      <button :class="['tab', { active: activeTab === 'match' }]" @click="activeTab = 'match'">反向寻才</button>
      <button :class="['tab', { active: activeTab === 'saved' }]" @click="activeTab = 'saved'">收藏夹</button>
      <button :class="['tab', { active: activeTab === 'profile' }]" @click="activeTab = 'profile'">企业档案</button>
    </div>

    <div class="tab-content">
      <div v-if="activeTab === 'jobs'" class="jobs-panel">
        <div class="panel-header">
          <h3>已发布岗位</h3>
          <div class="search-box">
            <input v-model="jobSearch" placeholder="搜索岗位..." />
          </div>
        </div>
        
        <div class="jobs-list" v-if="!loadingJobs">
          <div class="job-item" v-for="job in filteredPostedJobs" :key="job.id">
            <div class="job-main">
              <div class="job-info">
                <h4>{{ job.title }}</h4>
                <div class="job-meta">
                  <span>{{ job.salary || '面议' }}</span>
                  <span>{{ job.location || '不限' }}</span>
                  <span>{{ job.experience || '不限经验' }}</span>
                </div>
                <div class="job-skills" v-if="job.skills?.length">
                  <span class="skill-tag" v-for="s in job.skills.slice(0, 5)" :key="s">{{ s }}</span>
                </div>
              </div>
              <div class="job-stats">
                <div class="stat">
                  <span class="num">{{ job.view_count || 0 }}</span>
                  <span class="label">浏览</span>
                </div>
                <div class="stat">
                  <span class="num">{{ job.apply_count || 0 }}</span>
                  <span class="label">投递</span>
                </div>
              </div>
            </div>
            <div class="job-actions">
              <span class="status-badge" :class="job.status">{{ job.status === 'active' ? '招聘中' : '已下线' }}</span>
              <button class="btn-text" @click="editJob(job)">编辑</button>
              <button class="btn-text danger" @click="toggleJobStatus(job)">
                {{ job.status === 'active' ? '下线' : '上线' }}
              </button>
            </div>
          </div>
        </div>
        
        <div class="empty-state" v-else-if="!postedJobs.length">
          <p>暂无发布岗位</p>
          <button class="primary-btn" @click="showPostJob = true">发布第一个岗位</button>
        </div>
      </div>

      <div v-else-if="activeTab === 'match'" class="match-panel">
        <div class="match-form-card">
          <h3>反向寻才</h3>
          <p>根据岗位和技能要求，智能匹配最合适的候选人</p>
          
          <div class="form-group">
            <label>目标岗位</label>
            <select v-model="matchForm.job_name">
              <option value="">请选择岗位</option>
              <option v-for="j in jobList" :key="j" :value="j">{{ j }}</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>技能要求</label>
            <div class="skill-templates" v-if="Object.keys(JOB_SKILL_TEMPLATES).length">
              <span class="template-label">快速选择模板：</span>
              <button 
                v-for="(skills, templateName) in JOB_SKILL_TEMPLATES" 
                :key="templateName"
                class="template-btn"
                @click="applySkillTemplate(skills)"
                :title="skills.join('、')"
              >
                {{ templateName }}
              </button>
            </div>
            <div class="skill-input-area">
              <div class="skill-tags" v-if="matchForm.required_skills.length">
                <span class="skill-tag" v-for="(s, i) in matchForm.required_skills" :key="i">
                  {{ s }}
                  <span class="remove" @click="removeSkill(i)">×</span>
                </span>
              </div>
              <input v-model="skillInput" placeholder="输入技能后按回车..." @keydown.enter.prevent="addSkill" />
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>最低匹配度</label>
              <select v-model="matchForm.min_score">
                <option :value="60">60分以上</option>
                <option :value="70">70分以上</option>
                <option :value="80">80分以上</option>
              </select>
            </div>
            <div class="form-group">
              <label>学历要求</label>
              <select v-model="matchForm.degree">
                <option value="">不限</option>
                <option value="本科">本科及以上</option>
                <option value="硕士">硕士及以上</option>
              </select>
            </div>
          </div>
          
          <button class="match-btn" :disabled="!matchForm.job_name || matching" @click="runMatch">
            {{ matching ? '匹配中...' : '🔍 开始匹配' }}
          </button>
        </div>

        <div class="candidates-section" v-if="candidates.length">
          <div class="section-header">
            <h3>匹配结果 <span class="count">{{ candidates.length }} 位候选人</span></h3>
            <div class="market-hint" v-if="marketStats">
              市场均薪 {{ marketStats.avg_salary_k }}k/月 · {{ marketStats.jd_count }} 个在招岗位
            </div>
          </div>
          
          <div class="candidates-grid">
            <div class="candidate-card" v-for="c in candidates" :key="c.student_id">
              <div class="candidate-header">
                <div class="avatar">{{ c.name?.slice(-1) || '?' }}</div>
                <div class="candidate-basic">
                  <div class="name">{{ c.name || '匿名用户' }}</div>
                  <div class="meta">
                    <span>{{ c.degree || '学历未知' }}</span>
                    <span>{{ c.major || '专业未知' }}</span>
                  </div>
                  <div class="school" v-if="c.school">{{ c.school }}</div>
                </div>
                <div class="score-badge" :class="getScoreClass(c.score)">{{ c.score }}分</div>
              </div>
              
              <div class="candidate-stats">
                <div class="stat-item">
                  <span class="stat-label">竞争力</span>
                  <span class="stat-value level-tag" :class="'level-' + c.competitiveness_level">{{ c.competitiveness_level || 'C' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">完整度</span>
                  <span class="stat-value">{{ c.completeness || 0 }}%</span>
                </div>
                <div class="stat-item" v-if="c.internship_months">
                  <span class="stat-label">实习</span>
                  <span class="stat-value">{{ c.internship_months }}月</span>
                </div>
              </div>
              
              <div class="candidate-skills" v-if="c.skills?.length">
                <span class="skill-tag" v-for="s in c.skills.slice(0, 6)" :key="s">{{ s }}</span>
              </div>
              
              <div class="match-detail" v-if="c.matched_skills?.length || c.gap_skills?.length">
                <div class="match-row" v-if="c.matched_skills?.length">
                  <span class="match-label">✓ 匹配技能:</span>
                  <span class="match-value good">{{ c.matched_skills.slice(0, 4).join('、') }}</span>
                </div>
                <div class="match-row" v-if="c.gap_skills?.length">
                  <span class="match-label">✗ 差距技能:</span>
                  <span class="match-value gap">{{ c.gap_skills.slice(0, 3).join('、') }}</span>
                </div>
              </div>
              
              <div class="candidate-footer">
                <div class="actions">
                  <button class="btn-icon" :class="{ saved: c.saved }" @click="toggleSave(c)">
                    {{ c.saved ? '★' : '☆' }}
                  </button>
                  <button class="btn-text" @click="showCandidateDetail(c)">查看详情</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="empty-state" v-else-if="matchDone">
          <p>未找到符合条件的候选人</p>
          <p class="hint">请尝试调整筛选条件</p>
        </div>
      </div>

      <div v-else-if="activeTab === 'saved'" class="saved-panel">
        <div class="panel-header">
          <h3>收藏的候选人</h3>
        </div>
        
        <div class="candidates-grid" v-if="savedCandidates.length">
          <div class="candidate-card" v-for="c in savedCandidates" :key="c.student_id">
            <div class="candidate-header">
              <div class="avatar">{{ c.name?.slice(-1) || '?' }}</div>
              <div class="candidate-basic">
                <div class="name">{{ c.name || '匿名用户' }}</div>
                <div class="meta">
                  <span>{{ c.degree || '学历未知' }}</span>
                  <span>{{ c.major || '专业未知' }}</span>
                </div>
              </div>
              <div class="score-badge" :class="getScoreClass(c.score)">{{ c.score }}分</div>
            </div>
            <div class="candidate-skills" v-if="c.skills?.length">
              <span class="skill-tag" v-for="s in c.skills.slice(0, 6)" :key="s">{{ s }}</span>
            </div>
            <div class="candidate-footer">
              <div class="saved-job">匹配岗位：{{ c.matched_job }}</div>
              <button class="btn-text danger" @click="removeSaved(c)">移除</button>
            </div>
          </div>
        </div>
        
        <div class="empty-state" v-else>
          <p>暂无收藏候选人</p>
          <p class="hint">在"反向寻才"中匹配候选人后可收藏</p>
        </div>
      </div>

      <div v-else-if="activeTab === 'profile'" class="profile-panel">
        <div class="profile-card">
          <div class="card-header">
            <h3>企业档案</h3>
            <button class="edit-btn" @click="editMode = !editMode">
              {{ editMode ? '取消' : '编辑' }}
            </button>
          </div>
          
          <div v-if="!editMode" class="profile-view">
            <div class="profile-row">
              <span class="label">公司名称</span>
              <span class="value">{{ profile.company_name || '未填写' }}</span>
            </div>
            <div class="profile-row">
              <span class="label">所属行业</span>
              <span class="value">{{ profile.industry || '未填写' }}</span>
            </div>
            <div class="profile-row">
              <span class="label">公司规模</span>
              <span class="value">{{ profile.size || '未填写' }}</span>
            </div>
            <div class="profile-row">
              <span class="label">联系邮箱</span>
              <span class="value">{{ profile.contact_email || '未填写' }}</span>
            </div>
            <div class="profile-row">
              <span class="label">公司简介</span>
              <span class="value desc">{{ profile.description || '暂无简介' }}</span>
            </div>
          </div>
          
          <div v-else class="profile-form">
            <div class="form-group">
              <label>公司名称</label>
              <input v-model="editForm.company_name" placeholder="请输入公司名称" />
            </div>
            <div class="form-group">
              <label>所属行业</label>
              <input v-model="editForm.industry" placeholder="如：互联网/金融/教育" />
            </div>
            <div class="form-group">
              <label>公司规模</label>
              <select v-model="editForm.size">
                <option value="">请选择</option>
                <option v-for="s in COMPANY_SIZE_OPTIONS" :key="s">{{ s }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>联系邮箱</label>
              <input v-model="editForm.contact_email" type="email" placeholder="hr@company.com" />
            </div>
            <div class="form-group">
              <label>公司简介</label>
              <textarea v-model="editForm.description" placeholder="介绍公司业务和文化..." rows="4"></textarea>
            </div>
            <button class="save-btn" :disabled="saving" @click="saveProfile">
              {{ saving ? '保存中...' : '保存档案' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal-overlay" v-if="showPostJob" @click.self="showPostJob = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingJob ? '编辑岗位' : '发布新岗位' }}</h3>
          <button class="close-btn" @click="closeJobModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>岗位名称 <span class="required">*</span></label>
            <input v-model="jobForm.title" placeholder="如：Java开发工程师" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>薪资范围</label>
              <input v-model="jobForm.salary" placeholder="如：15-25K" />
            </div>
            <div class="form-group">
              <label>工作地点</label>
              <input v-model="jobForm.location" placeholder="如：北京" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>经验要求</label>
              <select v-model="jobForm.experience">
                <option value="">不限</option>
                <option v-for="e in EXPERIENCE_OPTIONS" :key="e">{{ e }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>学历要求</label>
              <select v-model="jobForm.education">
                <option value="">不限</option>
                <option v-for="d in DEGREE_OPTIONS" :key="d">{{ d }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>技能要求</label>
            <div class="skill-input-area">
              <div class="skill-tags" v-if="jobForm.skills.length">
                <span class="skill-tag" v-for="(s, i) in jobForm.skills" :key="i">
                  {{ s }}
                  <span class="remove" @click="jobForm.skills.splice(i, 1)">×</span>
                </span>
              </div>
              <input v-model="jobSkillInput" placeholder="输入技能后按回车..." @keydown.enter.prevent="addJobSkill" />
            </div>
          </div>
          <div class="form-group">
            <label>岗位描述</label>
            <textarea v-model="jobForm.description" placeholder="岗位职责、任职要求等..." rows="4"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeJobModal">取消</button>
          <button class="btn-primary" :disabled="!jobForm.title || postingJob" @click="submitJob">
            {{ postingJob ? '发布中...' : (editingJob ? '保存修改' : '发布岗位') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { request } from '../api/http'
import { Message } from '@arco-design/web-vue'
import { COMPANY_SIZE_OPTIONS, DEGREE_OPTIONS, EXPERIENCE_OPTIONS, JOB_SKILL_TEMPLATES } from '../constants'

interface Profile {
  company_name: string
  industry: string
  size: string
  description: string
  contact_email: string
}

interface PostedJob {
  id: string
  title: string
  salary?: string
  location?: string
  experience?: string
  education?: string
  skills: string[]
  description?: string
  status: string
  view_count: number
  apply_count: number
}

interface Candidate {
  student_id: string
  name: string
  degree: string
  major: string
  school?: string
  skills: string[]
  internship_months?: number
  competitiveness_level: string
  completeness?: number
  score: number
  match_score?: number
  matched_skills?: string[]
  gap_skills?: string[]
  saved?: boolean
  matched_job?: string
  notes?: string
  saved_at?: string
}

interface MarketStats {
  jd_count: number
  avg_salary_k: number
}

const activeTab = ref('jobs')
const profile = ref<Profile>({ company_name: '', industry: '', size: '', description: '', contact_email: '' })
const editForm = reactive<Profile>({ company_name: '', industry: '', size: '', description: '', contact_email: '' })
const editMode = ref(false)
const saving = ref(false)

const postedJobs = ref<PostedJob[]>([])
const loadingJobs = ref(true)
const jobSearch = ref('')
const showPostJob = ref(false)
const editingJob = ref<PostedJob | null>(null)
const postingJob = ref(false)
const jobForm = reactive({
  title: '',
  salary: '',
  location: '',
  experience: '',
  education: '',
  skills: [] as string[],
  description: ''
})
const jobSkillInput = ref('')

const jobList = ref<string[]>([])
const matchForm = reactive({ job_name: '', required_skills: [] as string[], min_score: 70, degree: '' })
const skillInput = ref('')
const matching = ref(false)
const matchDone = ref(false)
const candidates = ref<Candidate[]>([])
const marketStats = ref<MarketStats | null>(null)

const savedCandidates = ref<Candidate[]>([])

const totalCandidates = computed(() => candidates.value.length)

const filteredPostedJobs = computed(() => {
  if (!jobSearch.value) return postedJobs.value
  const q = jobSearch.value.toLowerCase()
  return postedJobs.value.filter(j => j.title.toLowerCase().includes(q))
})

function getScoreClass(score: number) {
  if (score >= 80) return 'high'
  if (score >= 70) return 'mid'
  return 'low'
}

function addSkill() {
  const s = skillInput.value.trim()
  if (s && !matchForm.required_skills.includes(s)) {
    matchForm.required_skills.push(s)
  }
  skillInput.value = ''
}

function removeSkill(i: number) {
  matchForm.required_skills.splice(i, 1)
}

function applySkillTemplate(skills: string[]) {
  matchForm.required_skills = [...new Set([...matchForm.required_skills, ...skills])]
  Message.success(`已添加 ${skills.length} 个技能`)
}

function addJobSkill() {
  const s = jobSkillInput.value.trim()
  if (s && !jobForm.skills.includes(s)) {
    jobForm.skills.push(s)
  }
  jobSkillInput.value = ''
}

async function loadProfile() {
  try {
    const res = await request.get<Profile>('/company/profile')
    profile.value = res
    Object.assign(editForm, res)
  } catch (e) {
  }
}

async function loadJobs() {
  try {
    const res = await request.get<any>('/match/jobs')
    // /match/jobs 返回字符串数组
    if (Array.isArray(res)) {
      jobList.value = typeof res[0] === 'string' ? res : res.map((j: any) => j.title || j.name || '')
    } else {
      jobList.value = []
    }
  } catch (e) {
    jobList.value = []
  }
}

async function loadPostedJobs() {
  loadingJobs.value = true
  try {
    const res = await request.get<PostedJob[]>('/company/jobs')
    postedJobs.value = res
  } catch {
    postedJobs.value = []
  } finally {
    loadingJobs.value = false
  }
}

async function loadSavedCandidates() {
  try {
    const res = await request.get<Candidate[]>('/company/saved_candidates')
    savedCandidates.value = res
  } catch {
    savedCandidates.value = []
  }
}

async function saveProfile() {
  saving.value = true
  try {
    await request.put('/company/profile', { ...editForm })
    profile.value = { ...editForm }
    editMode.value = false
    Message.success('保存成功')
  } catch (e: any) {
    Message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function runMatch() {
  if (!matchForm.job_name) return
  matching.value = true
  matchDone.value = false
  candidates.value = []
  marketStats.value = null
  try {
    const res = await request.post<{ candidates: any[] }>('/company/reverse_match', {
      job_name: matchForm.job_name,
      required_skills: matchForm.required_skills,
      min_score: matchForm.min_score,
      degree: matchForm.degree,
    })
    candidates.value = res.candidates.map(c => ({ 
      ...c, 
      score: c.match_score || c.score || 0,
      saved: savedCandidates.value.some(s => s.student_id === c.student_id) 
    }))
    
    try {
      const stats = await request.get<MarketStats>(`/jobs/${encodeURIComponent(matchForm.job_name)}/real`)
      marketStats.value = stats
    } catch {}
  } catch (e: any) {
    Message.error(e?.message || '匹配失败')
  } finally {
    matching.value = false
    matchDone.value = true
  }
}

async function toggleSave(candidate: Candidate) {
  try {
    if (candidate.saved) {
      await request.delete(`/company/saved_candidates/${candidate.student_id}`)
      savedCandidates.value = savedCandidates.value.filter(c => c.student_id !== candidate.student_id)
      candidate.saved = false
      Message.success('已取消收藏')
    } else {
      await request.post('/company/saved_candidates', {
        student_id: candidate.student_id,
        matched_job: matchForm.job_name
      })
      savedCandidates.value.push({ ...candidate, matched_job: matchForm.job_name })
      candidate.saved = true
      Message.success('已收藏')
    }
  } catch (e: any) {
    Message.error(e?.message || '操作失败')
  }
}

function showCandidateDetail(candidate: Candidate) {
  const matchedSkills = candidate.matched_skills?.slice(0, 5).join('、') || '无'
  const gapSkills = candidate.gap_skills?.slice(0, 5).join('、') || '无'
  const skills = candidate.skills?.slice(0, 10).join('、') || '暂无'
  
  Message.info({
    content: `【${candidate.name || '匿名用户'}】
学历：${candidate.degree || '未知'} | 专业：${candidate.major || '未知'}
学校：${candidate.school || '未知'}
竞争力：${candidate.competitiveness_level || 'C'} | 完整度：${candidate.completeness || 0}%
实习经历：${candidate.internship_months || 0}个月
技能：${skills}
匹配技能：${matchedSkills}
差距技能：${gapSkills}`,
    duration: 8000
  })
}

async function removeSaved(candidate: Candidate) {
  try {
    await request.delete(`/company/saved_candidates/${candidate.student_id}`)
    savedCandidates.value = savedCandidates.value.filter(c => c.student_id !== candidate.student_id)
    Message.success('已移除')
  } catch (e: any) {
    Message.error(e?.message || '操作失败')
  }
}

function editJob(job: PostedJob) {
  editingJob.value = job
  Object.assign(jobForm, {
    title: job.title,
    salary: job.salary || '',
    location: job.location || '',
    experience: job.experience || '',
    education: job.education || '',
    skills: job.skills || [],
    description: job.description || ''
  })
  showPostJob.value = true
}

function closeJobModal() {
  showPostJob.value = false
  editingJob.value = null
  Object.assign(jobForm, { title: '', salary: '', location: '', experience: '', education: '', skills: [], description: '' })
}

async function submitJob() {
  if (!jobForm.title) return
  postingJob.value = true
  try {
    if (editingJob.value) {
      await request.put(`/company/jobs/${editingJob.value.id}`, { ...jobForm })
      Message.success('修改成功')
    } else {
      await request.post('/company/jobs', { ...jobForm })
      Message.success('发布成功')
    }
    closeJobModal()
    loadPostedJobs()
  } catch (e: any) {
    Message.error(e?.message || '操作失败')
  } finally {
    postingJob.value = false
  }
}

async function toggleJobStatus(job: PostedJob) {
  try {
    const newStatus = job.status === 'active' ? 'inactive' : 'active'
    await request.put(`/company/jobs/${job.id}/status`, { status: newStatus })
    job.status = newStatus
    Message.success(newStatus === 'active' ? '已上线' : '已下线')
  } catch (e: any) {
    Message.error(e?.message || '操作失败')
  }
}

onMounted(() => {
  loadProfile()
  loadJobs()
  loadPostedJobs()
  loadSavedCandidates()
})
</script>

<style scoped>
.company-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 80px 40px 40px;
  max-width: 1280px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}

.sub {
  font-size: 14px;
  color: #888;
  margin: 0;
}

.action-btn {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
}

.action-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.stats-row {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.stat-item {
  background: white;
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  font-size: 13px;
  color: #888;
}

.main-tabs {
  display: flex;
  gap: 4px;
  background: white;
  padding: 6px;
  border-radius: 12px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.tab {
  padding: 10px 24px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.tab:hover {
  background: #f5f5f5;
}

.tab.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.tab-content {
  min-height: 400px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.search-box input {
  padding: 8px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  width: 200px;
}

.search-box input:focus {
  border-color: #667eea;
}

.jobs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-item {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.job-main {
  display: flex;
  gap: 24px;
  flex: 1;
}

.job-info h4 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
}

.job-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}

.job-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  padding: 4px 10px;
  background: #f0f4ff;
  color: #667eea;
  border-radius: 6px;
  font-size: 12px;
}

.job-stats {
  display: flex;
  gap: 20px;
}

.job-stats .stat {
  text-align: center;
}

.job-stats .num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #333;
}

.job-stats .label {
  font-size: 12px;
  color: #999;
}

.job-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: #f0ffe8;
  color: #52c41a;
}

.status-badge.inactive {
  background: #f5f5f5;
  color: #999;
}

.btn-text {
  background: none;
  border: none;
  color: #667eea;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
}

.btn-text.danger {
  color: #ff4d4f;
}

.btn-text:hover {
  text-decoration: underline;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-state p {
  margin: 0 0 8px;
}

.empty-state .hint {
  font-size: 13px;
  color: #bbb;
}

.primary-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 16px;
}

.match-form-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.match-form-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
}

.match-form-card > p {
  font-size: 14px;
  color: #888;
  margin: 0 0 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  margin-bottom: 6px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid #e5e5e5;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #667eea;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.skill-templates {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.template-label {
  font-size: 12px;
  color: #666;
}

.template-btn {
  padding: 4px 10px;
  font-size: 12px;
  background: #f0f5ff;
  color: #2f54eb;
  border: 1px solid #adc6ff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-btn:hover {
  background: #d6e4ff;
  border-color: #597ef7;
}

.skill-input-area {
  border: 1.5px solid #e5e5e5;
  border-radius: 10px;
  padding: 8px 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.skill-input-area:focus-within {
  border-color: #667eea;
}

.skill-input-area .skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-input-area .skill-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.skill-input-area .skill-tag .remove {
  cursor: pointer;
  opacity: 0.6;
}

.skill-input-area .skill-tag .remove:hover {
  opacity: 1;
}

.skill-input-area input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 100px;
  padding: 4px 0;
  font-size: 14px;
}

.match-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

.match-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.section-header .count {
  font-weight: 400;
  color: #888;
  font-size: 14px;
}

.market-hint {
  font-size: 13px;
  color: #888;
}

.candidates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.candidate-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.candidate-header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

.candidate-basic {
  flex: 1;
}

.candidate-basic .name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.candidate-basic .meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #888;
}

.score-badge {
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.score-badge.high { background: #f0ffe8; color: #52c41a; }
.score-badge.mid { background: #fff7e6; color: #fa8c16; }
.score-badge.low { background: #fff2f0; color: #ff4d4f; }

.candidate-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.candidate-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.candidate-stats .stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.candidate-stats .stat-label {
  font-size: 11px;
  color: #999;
}

.candidate-stats .stat-value {
  font-size: 12px;
  font-weight: 500;
  color: #333;
}

.match-detail {
  background: #fafafa;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 12px;
}

.match-detail .match-row {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
}

.match-detail .match-row:last-child {
  margin-bottom: 0;
}

.match-detail .match-label {
  color: #666;
  flex-shrink: 0;
}

.match-detail .match-value.good {
  color: #52c41a;
}

.match-detail .match-value.gap {
  color: #ff4d4f;
}

.candidate-basic .school {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.candidate-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.level-tag {
  font-size: 12px;
  font-weight: 500;
}

.level-A, .level-优秀 { color: #f5a623; }
.level-B, .level-较强 { color: #764ba2; }
.level-C, .level-一般 { color: #52c41a; }
.level-D, .level-薄弱 { color: #aaa; }

.candidate-footer .actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #ccc;
}

.btn-icon.saved {
  color: #faad14;
}

.saved-job {
  font-size: 12px;
  color: #888;
}

.profile-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 600px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.edit-btn {
  padding: 6px 16px;
  border: 1.5px solid #667eea;
  border-radius: 8px;
  background: none;
  color: #667eea;
  font-size: 13px;
  cursor: pointer;
}

.edit-btn:hover {
  background: #f0f4ff;
}

.profile-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}

.profile-row:last-child {
  border-bottom: none;
}

.profile-row .label {
  width: 100px;
  font-size: 13px;
  color: #888;
  flex-shrink: 0;
}

.profile-row .value {
  font-size: 14px;
  color: #333;
}

.profile-row .value.desc {
  line-height: 1.6;
}

.save-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

.save-btn:disabled {
  opacity: 0.6;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  width: 560px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.required {
  color: #ff4d4f;
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}

.btn-secondary {
  flex: 1;
  padding: 12px;
  border: 1.5px solid #e5e5e5;
  border-radius: 10px;
  background: white;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary {
  flex: 1;
  padding: 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.6;
}

@media (max-width: 768px) {
  .company-page {
    padding: 70px 16px 24px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .stats-row {
    flex-wrap: wrap;
  }
  
  .main-tabs {
    overflow-x: auto;
  }
  
  .tab {
    white-space: nowrap;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .candidates-grid {
    grid-template-columns: 1fr;
  }
}
</style>
