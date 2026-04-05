<template>
  <div class="upload-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <span>←</span>
      </button>
      <div class="header-content">
        <h1>{{ isManualMode ? '手动录入' : '简历上传' }}</h1>
        <p>{{ isManualMode ? '填写您的个人信息' : '支持 PDF、Word、图片格式' }}</p>
      </div>
      <button class="mode-switch" @click="toggleMode">
        {{ isManualMode ? '📄 上传简历' : '✏️ 手动录入' }}
      </button>
    </div>

    <!-- 分步表单指示器 -->
    <div class="step-indicator" v-if="isManualMode && parseStatus === 'idle'">
      <div 
        v-for="(step, index) in formSteps" 
        :key="index"
        :class="['step-dot', { 
          active: currentStep === index, 
          completed: currentStep > index 
        }]"
        @click="goToStep(index)"
      >
        <span class="step-number">{{ index + 1 }}</span>
        <span class="step-label">{{ step.title }}</span>
      </div>
      <div class="step-line">
        <div class="step-line-fill" :style="{ width: (currentStep / (formSteps.length - 1)) * 100 + '%' }"></div>
      </div>
    </div>

    <StepProgress />

    <div class="upload-container">
      <!-- 手动录入模式 - 分步表单 -->
      <div class="manual-section" v-if="isManualMode && parseStatus === 'idle'">
        <div class="form-card">
          <!-- 步骤1: 基本信息 -->
          <div class="form-step" v-show="currentStep === 0">
            <div class="step-header">
              <h2>基本信息</h2>
              <p>请填写您的基本信息（带 * 为必填项）</p>
            </div>
            <div class="form-section">
              <div class="form-grid">
                <div class="form-item">
                  <label>姓名 <span class="required">*</span></label>
                  <input v-model="manualForm.name" placeholder="请输入姓名" @blur="validateField('name')" />
                  <span class="field-error" v-if="errors.name">{{ errors.name }}</span>
                </div>
                <div class="form-item">
                  <label>学校 <span class="required">*</span></label>
                  <input v-model="manualForm.school" placeholder="请输入学校名称" @blur="validateField('school')" />
                  <span class="field-error" v-if="errors.school">{{ errors.school }}</span>
                </div>
                <div class="form-item">
                  <label>专业</label>
                  <input v-model="manualForm.major" placeholder="请输入专业名称" />
                </div>
                <div class="form-item">
                  <label>年级</label>
                  <select v-model="manualForm.grade">
                    <option value="">请选择</option>
                    <option value="大一">大一</option>
                    <option value="大二">大二</option>
                    <option value="大三">大三</option>
                    <option value="大四">大四</option>
                    <option value="研一">研一</option>
                    <option value="研二">研二</option>
                    <option value="研三">研三</option>
                  </select>
                </div>
                <div class="form-item">
                  <label>联系电话</label>
                  <input v-model="manualForm.phone" placeholder="请输入联系电话" @blur="validateField('phone')" />
                  <span class="field-error" v-if="errors.phone">{{ errors.phone }}</span>
                </div>
                <div class="form-item">
                  <label>邮箱</label>
                  <input v-model="manualForm.email" placeholder="请输入邮箱地址" @blur="validateField('email')" />
                  <span class="field-error" v-if="errors.email">{{ errors.email }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 步骤2: 专业技能 & 证书资质 -->
          <div class="form-step" v-show="currentStep === 1">
            <div class="step-header">
              <h2>专业技能 & 证书资质</h2>
              <p>展示您的专业能力和获得的证书</p>
            </div>
            <div class="form-section">
              <h3>专业技能</h3>
              <div class="skill-input-area">
                <div class="skill-tags" v-if="manualForm.skills.length">
                  <span class="skill-tag" v-for="(skill, idx) in manualForm.skills" :key="`skill-${idx}`">
                    {{ skill }}
                    <button class="remove-skill" @click="removeSkill(idx)">×</button>
                  </span>
                </div>
                <div class="skill-input-row">
                  <input 
                    v-model="skillInput" 
                    placeholder="输入技能后按回车添加"
                    @keydown.enter.prevent="addSkill"
                  />
                  <button class="add-btn" @click="addSkill">添加</button>
                </div>
                <div class="skill-suggestions">
                  <span class="suggestion-label">常用技能：</span>
                  <button 
                    class="suggestion-btn" 
                    v-for="skill in suggestedSkills" 
                    :key="skill"
                    @click="addSuggestedSkill(skill)"
                  >
                    {{ skill }}
                  </button>
                </div>
              </div>
            </div>

            <div class="form-section">
              <h3>证书资质</h3>
              <div class="cert-input-area">
                <div class="cert-list" v-if="manualForm.certs.length">
                  <span class="cert-tag" v-for="(cert, idx) in manualForm.certs" :key="`cert-${idx}`">
                    {{ cert }}
                    <button class="remove-cert" @click="removeCert(idx)">×</button>
                  </span>
                </div>
                <div class="cert-input-row">
                  <input 
                    v-model="certInput" 
                    placeholder="输入证书名称后按回车添加"
                    @keydown.enter.prevent="addCert"
                  />
                  <button class="add-btn" @click="addCert">添加</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 步骤3: 实习 & 项目经历 -->
          <div class="form-step" v-show="currentStep === 2">
            <div class="step-header">
              <h2>实习 & 项目经历</h2>
              <p>展示您的实践经验（选填）</p>
            </div>
            <div class="form-section">
              <h3>实习经历</h3>
              <div class="experience-list" v-if="manualForm.internships.length">
                <div class="experience-item" v-for="(exp, idx) in manualForm.internships" :key="`exp-${idx}`">
                  <div class="exp-header">
                    <span class="exp-company">{{ exp.company }}</span>
                    <button class="remove-exp" @click="removeInternship(idx)">×</button>
                  </div>
                  <div class="exp-detail">{{ exp.role }} · {{ exp.duration_months }}个月</div>
                </div>
              </div>
              <div class="experience-form">
                <div class="form-grid">
                  <input v-model="expForm.company" placeholder="公司名称" />
                  <input v-model="expForm.role" placeholder="职位名称" />
                  <input v-model.number="expForm.duration_months" type="number" placeholder="时长(月)" />
                </div>
                <textarea v-model="expForm.description" placeholder="工作内容描述（可选）"></textarea>
                <button class="add-exp-btn" @click="addInternship">+ 添加实习经历</button>
              </div>
            </div>

            <div class="form-section">
              <h3>项目经历</h3>
              <div class="project-list" v-if="manualForm.projects.length">
                <div class="project-item" v-for="(proj, idx) in manualForm.projects" :key="`proj-${idx}`">
                  <div class="proj-header">
                    <span class="proj-name">{{ proj.name }}</span>
                    <button class="remove-proj" @click="removeProject(idx)">×</button>
                  </div>
                  <div class="proj-tech" v-if="proj.tech_stack?.length">
                    <span class="tech-tag" v-for="(tech, tIdx) in proj.tech_stack" :key="`tech-${idx}-${tIdx}`">{{ tech }}</span>
                  </div>
                </div>
              </div>
              <div class="project-form">
                <input v-model="projForm.name" placeholder="项目名称" />
                <textarea v-model="projForm.description" placeholder="项目描述（可选）"></textarea>
                <input v-model="projForm.tech_stack" placeholder="技术栈（逗号分隔）" />
                <button class="add-proj-btn" @click="addProject">+ 添加项目经历</button>
              </div>
            </div>
          </div>

          <!-- 步骤4: 求职意向 & 提交 -->
          <div class="form-step" v-show="currentStep === 3">
            <div class="step-header">
              <h2>求职意向 & 提交</h2>
              <p>填写您的求职方向并提交</p>
            </div>
            <div class="form-section">
              <h3>求职意向</h3>
              <div class="form-grid">
                <div class="form-item full-width">
                  <label>期望岗位</label>
                  <input v-model="manualForm.career_intent" placeholder="如：Java工程师、产品经理" />
                </div>
              </div>
            </div>

            <div class="form-section summary-section">
              <h3>填写摘要</h3>
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-label">姓名</span>
                  <span class="summary-value">{{ manualForm.name || '-' }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">学校</span>
                  <span class="summary-value">{{ manualForm.school || '-' }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">专业</span>
                  <span class="summary-value">{{ manualForm.major || '-' }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">技能</span>
                  <span class="summary-value">{{ manualForm.skills.length }} 个</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">证书</span>
                  <span class="summary-value">{{ manualForm.certs.length }} 个</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">实习</span>
                  <span class="summary-value">{{ manualForm.internships.length }} 段</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">项目</span>
                  <span class="summary-value">{{ manualForm.projects.length }} 个</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">求职意向</span>
                  <span class="summary-value">{{ manualForm.career_intent || '-' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 表单导航按钮 -->
          <div class="form-actions">
            <button class="secondary-btn" @click="prevStep" v-if="currentStep > 0">
              上一步
            </button>
            <button class="secondary-btn" @click="resetForm" v-if="currentStep === 0">
              重置
            </button>
            <button class="primary-btn" @click="nextStep" v-if="currentStep < formSteps.length - 1" :disabled="!canProceed">
              下一步
            </button>
            <button class="primary-btn" @click="submitManualForm" v-if="currentStep === formSteps.length - 1" :disabled="!isFormValid || submitting">
              {{ submitting ? '提交中...' : '提交并生成画像' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 上传简历模式 -->
      <div class="upload-section" v-if="!isManualMode && parseStatus === 'idle'">
        <div 
          class="drop-zone"
          :class="{ 'drag-over': isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input 
            type="file" 
            ref="fileInput"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
            @change="handleFileChange"
            hidden
          />
          <div class="drop-icon">📄</div>
          <div class="drop-text">
            <p class="main-text">拖拽文件到此处，或点击上传</p>
            <p class="sub-text">支持 PDF、Word、PNG、JPG 格式，最大 10MB</p>
          </div>
        </div>
        
        <div class="file-preview" v-if="selectedFile">
          <div class="file-info">
            <span class="file-icon">📋</span>
            <div class="file-details">
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
            </div>
          </div>
          <button class="remove-btn" @click="clearFile">✕</button>
        </div>
        
        <button 
          class="upload-btn" 
          @click="uploadResume"
          :disabled="!selectedFile || uploading"
          v-if="selectedFile"
        >
          <span>{{ uploading ? '⏳' : '🚀' }}</span> {{ uploading ? '解析中...' : '开始解析' }}
        </button>
      </div>

      <div class="parsing-section" v-else-if="parseStatus === 'uploading' || parseStatus === 'parsing'">
        <div class="progress-card">
          <h3>{{ isManualMode ? '正在生成画像...' : '正在解析简历...' }}</h3>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: parseProgress + '%' }"></div>
          </div>
          <div class="progress-text">{{ parseProgress }}%</div>
          
          <div class="steps-list">
            <div 
              v-for="(step, index) in parseSteps" 
              :key="index"
              :class="['step-item', { done: step.done }]"
            >
              <span class="step-check">{{ step.done ? '✓' : '○' }}</span>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="result-section" v-else-if="parseStatus === 'done' && parseResult">
        <div class="success-header">
          <div class="success-icon">✓</div>
          <h2>{{ isManualMode ? '画像生成完成' : '简历解析完成' }}</h2>
          <p>已成功提取您的信息</p>
        </div>
        
        <div class="result-cards">
          <div class="result-card">
            <h4>基本信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">姓名</span>
                <span class="value">{{ parseResult.basic_info?.name || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">学校</span>
                <span class="value">{{ parseResult.basic_info?.school || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">专业</span>
                <span class="value">{{ parseResult.basic_info?.major || '-' }}</span>
              </div>
            </div>
          </div>
          
          <div class="result-card">
            <h4>评分结果</h4>
            <div class="score-row">
              <div class="score-item">
                <div class="score-circle">
                  <span class="score-value">{{ Math.round((parseResult.completeness || 0) * 100) }}</span>
                  <span class="score-unit">%</span>
                </div>
                <span class="score-label">完整度</span>
              </div>
              <div class="score-item">
                <div class="score-circle competitiveness">
                  <span class="score-value">{{ Math.round(parseResult.competitiveness || 0) }}</span>
                  <span class="score-unit">分</span>
                </div>
                <span class="score-label">竞争力</span>
              </div>
            </div>
            <div class="level-badge" :class="getLevelClass(parseResult.competitiveness_level)">
              {{ parseResult.competitiveness_level || '一般' }}
            </div>
          </div>
          
          <div class="result-card" v-if="parseResult.skills?.length">
            <h4>技能标签 ({{ parseResult.skills.length }})</h4>
            <div class="skill-tags-result">
              <span class="skill-tag-result" v-for="(skill, idx) in parseResult.skills.slice(0, 10)" :key="`skill-res-${idx}`">
                {{ skill }}
              </span>
              <span class="skill-tag-result more" v-if="parseResult.skills.length > 10">
                +{{ parseResult.skills.length - 10 }}
              </span>
            </div>
          </div>
          
          <!-- D-1: 简历质量评分 -->
          <div class="result-card" v-if="parseResult.parse_quality">
            <h4>简历质量评分</h4>
            <div class="quality-row">
              <span class="quality-score-num" :class="parseResult.parse_quality.score >= 70 ? 'good' : 'warn'">
                {{ parseResult.parse_quality.score }}分
              </span>
              <span class="quality-level-badge">{{ parseResult.parse_quality.level }}</span>
            </div>
            <ul class="quality-suggestions" v-if="parseResult.parse_quality.suggestions?.length">
              <li v-for="(s, i) in parseResult.parse_quality.suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>

          <div class="result-card warning" v-if="missingDims.length > 0">
            <h4>⚠️ 缺失维度</h4>
            <p class="warning-text">以下信息缺失，建议补充完善：</p>
            <div class="missing-list">
              <span class="missing-tag" v-for="(dim, idx) in missingDims" :key="`missing-${idx}`">
                {{ DIM_LABELS[dim] || dim }}
              </span>
            </div>
          </div>

          <div class="result-card transfer-card" v-if="transferOpportunities.length > 0">
            <h4>🔄 换岗机会推荐</h4>
            <p class="transfer-hint">基于您的技能和意向岗位，为您推荐以下换岗方向：</p>
            <div class="transfer-list">
              <div class="transfer-item" v-for="(tf, idx) in transferOpportunities.slice(0, 5)" :key="`transfer-${idx}`">
                <div class="transfer-header">
                  <span class="transfer-title">{{ tf.title }}</span>
                  <span class="transfer-match" :class="getMatchClass(tf.match_level)">
                    {{ getMatchLabel(tf.match_level) }}
                  </span>
                </div>
                <div class="transfer-detail" v-if="tf.overlap_pct">
                  <span class="detail-label">技能匹配度</span>
                  <div class="progress-mini">
                    <div class="progress-mini-fill" :style="{ width: ((tf.overlap_pct || 0) * 100) + '%' }"></div>
                  </div>
                  <span class="detail-value">{{ ((tf.overlap_pct || 0) * 100).toFixed(0) }}%</span>
                </div>
                <div class="transfer-advantage" v-if="tf.advantage">
                  <span class="detail-label">优势</span>
                  <span class="advantage-text">{{ tf.advantage }}</span>
                </div>
                <div class="transfer-gaps" v-if="tf.need_learn?.length">
                  <span class="detail-label">需补技能</span>
                  <div class="gap-tags">
                    <span class="gap-tag" v-for="skill in tf.need_learn.slice(0, 4)" :key="skill">{{ skill }}</span>
                    <span class="gap-tag more" v-if="tf.need_learn.length > 4">+{{ tf.need_learn.length - 4 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="auto-redirect-hint" v-if="autoRedirectCountdown > 0">
          {{ autoRedirectCountdown }} 秒后自动跳转到画像页...
          <button class="cancel-redirect-btn" @click="cancelRedirect">取消</button>
        </div>

        <div class="action-buttons">
          <button class="secondary-btn" @click="reset">
            {{ isManualMode ? '重新填写' : '重新上传' }}
          </button>
          <button class="primary-btn" @click="goToPortrait">
            查看画像
          </button>
          <button class="primary-btn" @click="goToMatch">
            开始匹配
          </button>
        </div>
      </div>

      <div class="error-section" v-else-if="parseStatus === 'failed'">
        <div class="error-card">
          <div class="error-icon">⚠️</div>
          <h3>{{ isManualMode ? '生成失败' : '解析失败' }}</h3>
          <p>{{ error || '请检查后重试' }}</p>
          <button class="primary-btn" @click="reset">
            {{ isManualMode ? '重新填写' : '重新上传' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUpload } from '../composables/useUpload'
import { useUserStore } from '../stores/useUserStore'
import { usePortraitStore } from '../stores/usePortraitStore'
import { useMatchStore } from '../stores/useMatchStore'
import { portraitApi } from '../api/portrait'
import type { TransferPath } from '../stores/usePortraitStore'
import StepProgress from '../components/StepProgress.vue'

const AUTOSAVE_KEY = 'resume_form_draft'

const router = useRouter()
const userStore = useUserStore()
const portraitStore = usePortraitStore()
const matchStore = useMatchStore()
const {
  uploading,
  parseStatus,
  parseProgress,
  parseSteps,
  missingDims,
  parseResult,
  error,
  DIM_LABELS,
  uploadResume: doUpload,
  reset: doReset,
} = useUpload()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const isManualMode = ref(false)
const submitting = ref(false)
const transferOpportunities = ref<TransferPath[]>([])

const currentStep = ref(0)
const formSteps = [
  { title: '基本信息', key: 'basic' },
  { title: '技能证书', key: 'skills' },
  { title: '经历', key: 'experience' },
  { title: '求职意向', key: 'intent' },
]

const errors = reactive<Record<string, string>>({
  name: '',
  school: '',
  phone: '',
  email: '',
})

const manualForm = reactive({
  name: '',
  school: '',
  major: '',
  grade: '',
  phone: '',
  email: '',
  skills: [] as string[],
  certs: [] as string[],
  internships: [] as { company: string; role: string; duration_months: number; description?: string }[],
  projects: [] as { name: string; description?: string; tech_stack: string[] }[],
  career_intent: '',
})

const skillInput = ref('')
const certInput = ref('')
const expForm = reactive({
  company: '',
  role: '',
  duration_months: 0,
  description: '',
})
const projForm = reactive({
  name: '',
  description: '',
  tech_stack: '',
})

const suggestedSkills = [
  'Java', 'Python', 'JavaScript', 'Vue.js', 'React', 
  'MySQL', 'Redis', 'Docker', 'Git', 'Spring Boot'
]

const isFormValid = computed(() => {
  return manualForm.name.trim() && manualForm.school.trim()
})

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return manualForm.name.trim() && manualForm.school.trim()
  }
  return true
})

function validateField(field: string) {
  switch (field) {
    case 'name':
      errors.name = manualForm.name.trim() ? '' : '请输入姓名'
      break
    case 'school':
      errors.school = manualForm.school.trim() ? '' : '请输入学校名称'
      break
    case 'phone':
      if (manualForm.phone && !/^1[3-9]\d{9}$/.test(manualForm.phone)) {
        errors.phone = '请输入正确的手机号码'
      } else {
        errors.phone = ''
      }
      break
    case 'email':
      if (manualForm.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(manualForm.email)) {
        errors.email = '请输入正确的邮箱地址'
      } else {
        errors.email = ''
      }
      break
  }
}

function nextStep() {
  if (currentStep.value === 0) {
    validateField('name')
    validateField('school')
    if (errors.name || errors.school) {
      Message.warning('请完善必填信息')
      return
    }
  }
  if (currentStep.value < formSteps.length - 1) {
    currentStep.value++
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function goToStep(index: number) {
  if (index < currentStep.value || canProceed.value) {
    currentStep.value = index
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function toggleMode() {
  isManualMode.value = !isManualMode.value
  if (isManualMode.value) loadDraft()
}

function addSkill() {
  const skill = skillInput.value.trim()
  if (skill && !manualForm.skills.includes(skill)) {
    manualForm.skills.push(skill)
    skillInput.value = ''
  }
}

function addSuggestedSkill(skill: string) {
  if (!manualForm.skills.includes(skill)) {
    manualForm.skills.push(skill)
  }
}

function removeSkill(index: number) {
  manualForm.skills.splice(index, 1)
}

function addCert() {
  const cert = certInput.value.trim()
  if (cert && !manualForm.certs.includes(cert)) {
    manualForm.certs.push(cert)
    certInput.value = ''
  }
}

function removeCert(index: number) {
  manualForm.certs.splice(index, 1)
}

function addInternship() {
  if (expForm.company && expForm.role) {
    manualForm.internships.push({
      company: expForm.company,
      role: expForm.role,
      duration_months: expForm.duration_months || 1,
      description: expForm.description,
    })
    expForm.company = ''
    expForm.role = ''
    expForm.duration_months = 0
    expForm.description = ''
  }
}

function removeInternship(index: number) {
  manualForm.internships.splice(index, 1)
}

function addProject() {
  if (projForm.name) {
    manualForm.projects.push({
      name: projForm.name,
      description: projForm.description,
      tech_stack: projForm.tech_stack ? projForm.tech_stack.split(',').map(t => t.trim()).filter(Boolean) : [],
    })
    projForm.name = ''
    projForm.description = ''
    projForm.tech_stack = ''
  }
}

function removeProject(index: number) {
  manualForm.projects.splice(index, 1)
}

function resetForm() {
  manualForm.name = ''
  manualForm.school = ''
  manualForm.major = ''
  manualForm.grade = ''
  manualForm.phone = ''
  manualForm.email = ''
  manualForm.skills = []
  manualForm.certs = []
  manualForm.internships = []
  manualForm.projects = []
  manualForm.career_intent = ''
  currentStep.value = 0
  errors.name = ''
  errors.school = ''
  errors.phone = ''
  errors.email = ''
}

async function submitManualForm() {
  if (!isFormValid.value) {
    Message.warning('请填写姓名和学校')
    return
  }
  
  submitting.value = true
  parseStatus.value = 'parsing'
  parseProgress.value = 10
  
  try {
    const studentId = userStore.studentId || `student_${Date.now().toString(36)}`
    
    parseProgress.value = 30
    
    const portraitData = {
      student_id: studentId,
      basic_info: {
        name: manualForm.name,
        school: manualForm.school,
        major: manualForm.major,
        grade: manualForm.grade,
        phone: manualForm.phone,
        email: manualForm.email,
      },
      education: [{
        school: manualForm.school,
        major: manualForm.major,
      }],
      skills: manualForm.skills,
      certs: manualForm.certs,
      internships: manualForm.internships,
      projects: manualForm.projects,
      career_intent: manualForm.career_intent,
      // 手动录入全量覆盖：清空旧简历解析的遗留字段
      awards: [],
      interests: [],
      inferred_soft_skills: {},
    }
    
    parseProgress.value = 50
    
    const result = await portraitApi.update(studentId, portraitData)
    
    parseProgress.value = 80
    
    userStore.setStudent(result.student_id, result.basic_info?.name || manualForm.name)
    userStore.setProfile({
      studentId: result.student_id,
      name: result.basic_info?.name || manualForm.name,
      school: result.basic_info?.school || manualForm.school,
      major: result.basic_info?.major,
      skills: result.skills || manualForm.skills,
      education: result.education || [],
      internships: result.internships || [],
      projects: result.projects || [],
      completeness: result.completeness || 0.5,
      competitiveness: result.competitiveness || 50,
      competitivenessLevel: result.competitiveness_level || '一般',
    })
    
    parseProgress.value = 100
    parseStatus.value = 'done'
    parseResult.value = result
    clearDraft()
    
    matchStore.clearResults()
    localStorage.setItem('portrait_update_time', Date.now().toString())
    
    Message.success('画像生成成功！')
  } catch (e: any) {
    parseStatus.value = 'failed'
    const errorMsg = e.message || '未知错误'
    
    // 细化错误提示
    if (errorMsg.includes('network') || errorMsg.includes('Network')) {
      error.value = '网络连接失败，请检查网络后重试'
    } else if (errorMsg.includes('timeout') || errorMsg.includes('Timeout')) {
      error.value = '请求超时，请稍后重试'
    } else if (errorMsg.includes('413') || errorMsg.includes('too large')) {
      error.value = '文件过大，请上传10MB以内的文件'
    } else if (errorMsg.includes('format') || errorMsg.includes('type')) {
      error.value = '文件格式不支持，请上传PDF、DOCX或图片文件'
    } else if (errorMsg.includes('parse') || errorMsg.includes('解析')) {
      error.value = '简历解析失败，请确保文件内容清晰可读'
    } else {
      error.value = errorMsg
    }
    
    Message.error(error.value || '上传失败，请重试')
  } finally {
    submitting.value = false
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    selectedFile.value = input.files[0]
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    selectedFile.value = files[0]
  }
}

function clearFile() {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function uploadResume() {
  if (!selectedFile.value) return
  const success = await doUpload(selectedFile.value)
  if (success) {
    selectedFile.value = null
  }
}

function reset() {
  doReset()
  clearFile()
  resetForm()
}

function goToPortrait() {
  router.push('/portrait')
}

function goToMatch() {
  router.push('/match')
}

function cancelRedirect() {
  if (_redirectTimer) clearInterval(_redirectTimer)
  autoRedirectCountdown.value = 0
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ---- 表单自动保存 ----
let _autosaveTimer: ReturnType<typeof setTimeout> | null = null

function scheduleAutosave() {
  if (_autosaveTimer) clearTimeout(_autosaveTimer)
  _autosaveTimer = setTimeout(() => {
    if (manualForm.name || manualForm.school) {
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify({ ...manualForm }))
    }
  }, 800)
}

function loadDraft() {
  try {
    const saved = localStorage.getItem(AUTOSAVE_KEY)
    if (!saved) return
    const draft = JSON.parse(saved)
    Object.assign(manualForm, draft)
    Message.info('已恢复上次未完成的填写内容')
  } catch {}
}

function clearDraft() {
  localStorage.removeItem(AUTOSAVE_KEY)
}

function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (isManualMode.value && (manualForm.name || manualForm.school) && parseStatus.value !== 'done') {
    e.preventDefault()
    e.returnValue = ''
  }
}

// 监听表单变化自动保存
watch(manualForm, scheduleAutosave, { deep: true })

// 解析/录入成功后 3 秒自动跳转画像页
let _redirectTimer: ReturnType<typeof setTimeout> | null = null
const autoRedirectCountdown = ref(0)

watch(parseStatus, (status) => {
  if (status === 'done') {
    portraitStore.clearPortrait()
    if (parseResult.value?.transfer_opportunities) {
      transferOpportunities.value = parseResult.value.transfer_opportunities
    }
    autoRedirectCountdown.value = 3
    _redirectTimer = setInterval(() => {
      autoRedirectCountdown.value--
      if (autoRedirectCountdown.value <= 0) {
        clearInterval(_redirectTimer!)
        router.push('/portrait')
      }
    }, 1000)
  }
})

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  if (isManualMode.value) loadDraft()
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  if (_autosaveTimer) clearTimeout(_autosaveTimer)
  if (_redirectTimer) clearInterval(_redirectTimer)
})

function getLevelClass(level: string | undefined): string {
  if (level === 'A') return 'excellent'
  if (level === 'B') return 'good'
  if (level === 'C') return 'normal'
  return 'normal'
}

function getMatchClass(matchLevel?: string): string {
  if (matchLevel === 'high') return 'high'
  if (matchLevel === 'medium') return 'medium'
  return 'low'
}

function getMatchLabel(matchLevel?: string): string {
  if (matchLevel === 'high') return '高匹配'
  if (matchLevel === 'medium') return '中匹配'
  return '可尝试'
}
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  background: #f8fafc;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 32px;
  background: white;
  border-bottom: 1px solid #eee;
}

.back-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #eee;
  background: #fff;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #f5f5f5;
}

.header-content {
  flex: 1;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.header-content p {
  font-size: 14px;
  color: #666;
  margin: 4px 0 0;
}

.mode-switch {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  transition: all 0.2s;
}

.mode-switch:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.step-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  padding: 24px 32px;
  background: white;
  position: relative;
}

.step-dot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  position: relative;
  z-index: 1;
  padding: 0 40px;
}

.step-number {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.step-dot.active .step-number {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.step-dot.completed .step-number {
  background: #52c41a;
  color: white;
}

.step-label {
  font-size: 13px;
  color: #999;
  white-space: nowrap;
  transition: color 0.3s;
}

.step-dot.active .step-label {
  color: #667eea;
  font-weight: 500;
}

.step-dot.completed .step-label {
  color: #52c41a;
}

.step-line {
  position: absolute;
  top: 42px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 200px);
  max-width: 500px;
  height: 3px;
  background: #f0f0f0;
  z-index: 0;
}

.step-line-fill {
  height: 100%;
  background: linear-gradient(90deg, #52c41a 0%, #667eea 100%);
  transition: width 0.3s ease;
}

.upload-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}

.form-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.form-step {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.step-header h2 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #1a1a2e;
}

.step-header p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.form-section:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
}

.form-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
  color: #1a1a2e;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item.full-width {
  grid-column: span 2;
}

.form-item label {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.required {
  color: #f5222d;
}

.form-item input,
.form-item select,
.form-item textarea {
  padding: 10px 14px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-item input:focus,
.form-item select:focus,
.form-item textarea:focus {
  border-color: #667eea;
}

.form-item textarea {
  resize: vertical;
  min-height: 80px;
}

.field-error {
  font-size: 12px;
  color: #f5222d;
  margin-top: 4px;
}

.form-item input.error,
.form-item select.error,
.form-item textarea.error {
  border-color: #f5222d;
}

.skill-input-area,
.cert-input-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-tags,
.cert-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag,
.cert-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
}

.remove-skill,
.remove-cert {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  line-height: 1;
}

.skill-input-row,
.cert-input-row {
  display: flex;
  gap: 10px;
}

.skill-input-row input,
.cert-input-row input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.add-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  background: #667eea;
  color: white;
  border: none;
}

.skill-suggestions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.suggestion-label {
  font-size: 13px;
  color: #999;
}

.suggestion-btn {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  background: #f5f5f5;
  color: #666;
  border: none;
  transition: all 0.2s;
}

.suggestion-btn:hover {
  background: #667eea;
  color: white;
}

.experience-list,
.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.experience-item,
.project-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.exp-header,
.proj-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.exp-company,
.proj-name {
  font-weight: 500;
  font-size: 14px;
}

.exp-detail {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}

.proj-tech {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.tech-tag {
  padding: 2px 8px;
  background: #e6f7ff;
  color: #1890ff;
  border-radius: 4px;
  font-size: 11px;
}

.remove-exp,
.remove-proj {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 18px;
}

.experience-form,
.project-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.experience-form .form-grid {
  grid-template-columns: repeat(3, 1fr);
}

.add-exp-btn,
.add-proj-btn {
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  background: #f5f5f5;
  color: #666;
  border: 1px dashed #d9d9d9;
  transition: all 0.2s;
}

.add-exp-btn:hover,
.add-proj-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
}

.primary-btn {
  flex: 1;
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  flex: 1;
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  background: white;
  color: #667eea;
  border: 1px solid #667eea;
}

.secondary-btn:hover {
  background: #f8f9ff;
}

.drop-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 16px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #667eea;
  background: #f8f9ff;
}

.drop-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.drop-text .main-text {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin: 0 0 8px;
}

.drop-text .sub-text {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.file-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  margin-top: 16px;
  border: 1px solid #eee;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 24px;
}

.file-details {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.file-size {
  font-size: 12px;
  color: #999;
}

.remove-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 14px;
  color: #999;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #ff4d4f;
  color: white;
}

.upload-btn {
  width: 100%;
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  margin-top: 16px;
}

.upload-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.progress-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  text-align: center;
}

.progress-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 24px;
}

.progress-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 14px;
  color: #667eea;
  font-weight: 600;
  margin-bottom: 24px;
}

.steps-list {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 14px;
  color: #999;
  transition: all 0.3s;
}

.step-item.done {
  color: #52c41a;
  background: #f6ffed;
}

.success-header {
  text-align: center;
  margin-bottom: 32px;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #f6ffed;
  color: #52c41a;
  font-size: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.success-header h2 {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 8px;
}

.success-header p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.result-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.result-card h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 16px;
  color: #333;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #999;
}

.info-item .value {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.score-row {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 16px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.score-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.score-circle.competitiveness {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
}

.score-value {
  font-size: 24px;
  font-weight: 700;
}

.score-unit {
  font-size: 12px;
}

.score-label {
  font-size: 13px;
  color: #666;
}

.level-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.level-badge.excellent {
  background: #f6ffed;
  color: #52c41a;
}

.level-badge.good {
  background: #e6f7ff;
  color: #1890ff;
}

.level-badge.normal {
  background: #fff7e6;
  color: #fa8c16;
}

.skill-tags-result {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag-result {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
}

.skill-tag-result.more {
  background: #f0f0f0;
  color: #666;
}

.result-card.warning {
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.warning-text {
  font-size: 13px;
  color: #d48806;
  margin: 0 0 12px;
}

.missing-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.missing-tag {
  padding: 4px 12px;
  background: #fff1b8;
  color: #d48806;
  border-radius: 12px;
  font-size: 12px;
}

.quality-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.quality-score-num {
  font-size: 22px;
  font-weight: 700;
}
.quality-score-num.good { color: #52c41a; }
.quality-score-num.warn { color: #fa8c16; }
.quality-level-badge {
  background: #f0f2f5;
  color: #595959;
  border-radius: 10px;
  padding: 2px 10px;
  font-size: 12px;
}
.quality-suggestions {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #595959;
  line-height: 1.8;
}

.auto-redirect-hint {
  text-align: center;
  color: #667eea;
  font-size: 13px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.cancel-redirect-btn {
  background: none;
  border: 1px solid #667eea;
  color: #667eea;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.error-section {
  display: flex;
  justify-content: center;
}

.error-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  max-width: 400px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
}

.error-card p {
  font-size: 14px;
  color: #666;
  margin: 0 0 20px;
}

.transfer-card {
  background: linear-gradient(135deg, #f0f5ff 0%, #e6f7ff 100%);
  border: 1px solid #91caff;
}

.transfer-card h4 {
  color: #1890ff;
}

.transfer-hint {
  font-size: 13px;
  color: #666;
  margin: 0 0 16px;
}

.transfer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.transfer-item {
  background: white;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid #e6f7ff;
}

.transfer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.transfer-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.transfer-match {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.transfer-match.high {
  background: #f6ffed;
  color: #52c41a;
}

.transfer-match.medium {
  background: #e6f7ff;
  color: #1890ff;
}

.transfer-match.low {
  background: #fff7e6;
  color: #fa8c16;
}

.transfer-detail {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.detail-label {
  font-size: 12px;
  color: #999;
  min-width: 70px;
}

.progress-mini {
  flex: 1;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-mini-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff 0%, #52c41a 100%);
  border-radius: 3px;
}

.detail-value {
  font-size: 12px;
  font-weight: 600;
  color: #1890ff;
  min-width: 40px;
  text-align: right;
}

.transfer-advantage {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.advantage-text {
  font-size: 13px;
  color: #333;
  flex: 1;
}

.transfer-gaps {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.gap-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}

.gap-tag {
  padding: 3px 8px;
  background: #fff1b8;
  color: #d48806;
  border-radius: 4px;
  font-size: 11px;
}

.gap-tag.more {
  background: #f0f0f0;
  color: #666;
}

.summary-section {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #999;
}

.summary-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

@media (max-width: 768px) {
  .step-indicator {
    padding: 16px;
  }
  
  .step-dot {
    padding: 0 20px;
  }
  
  .step-label {
    font-size: 11px;
  }
  
  .step-line {
    width: calc(100% - 100px);
  }
  
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
