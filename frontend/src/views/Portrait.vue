<template>
  <div class="portrait-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <span>←</span>
      </button>
      <div class="header-content">
        <h1>学生画像</h1>
        <p>七维度画像分析</p>
      </div>
    </div>
    <StepProgress />

    <!-- O4-c: 空状态 -->
    <div v-if="!userStore.studentId" class="empty-state-page">
      <div class="empty-state-icon">📄</div>
      <h2>尚未上传简历</h2>
      <p>上传简历后，系统将自动生成你的学生画像</p>
      <a-button type="primary" @click="$router.push('/upload')">立即上传简历</a-button>
    </div>

    <div class="portrait-container" v-if="userStore.studentId">
      <div class="main-content" v-if="!loading">
        <div class="left-section">
          <div class="card basic-card">
            <div class="card-header">
              <h3>基本信息</h3>
            </div>
            <div class="basic-info" v-if="portrait">
              <div class="info-item">
                <span class="label">姓名</span>
                <span class="value">{{ portrait.basicInfo?.name || userStore.userName }}</span>
              </div>
              <div class="info-item">
                <span class="label">学校</span>
                <span class="value">{{ portrait.basicInfo?.school || userStore.profile?.school || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">专业</span>
                <span class="value">{{ portrait.basicInfo?.major || userStore.profile?.major || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">年级</span>
                <span class="value">{{ portrait.basicInfo?.grade || '-' }}</span>
              </div>
            </div>
          </div>

          <div class="card skills-card">
            <div class="card-header">
              <h3>技能特长</h3>
              <span class="count">{{ skillScores.length > 0 ? skillScores.length : (portrait?.skills?.length || 0) }} 项</span>
            </div>
            <div v-if="skillScores.length > 0" class="skills-detailed">
              <div class="skill-category" v-for="category in skillCategories" :key="category.name">
                <div class="category-header">
                  <span class="category-name">{{ category.name }}</span>
                  <span class="category-count">{{ category.skills.length }}项</span>
                </div>
                <div class="category-skills">
                  <div class="skill-item-detailed" v-for="skill in category.skills" :key="skill.name">
                    <div class="skill-item-header">
                      <span class="skill-item-name">{{ skill.name }}</span>
                      <div class="skill-item-badges">
                        <span class="skill-level" :class="getSkillLevelClass(skill.score)">{{ skill.level }}</span>
                        <span class="skill-certified" v-if="skill.certified">✓ 已认证</span>
                      </div>
                    </div>
                    <div class="skill-item-bar">
                      <div class="skill-item-fill" :style="{ width: skill.score + '%' }" :class="getSkillLevelClass(skill.score)"></div>
                    </div>
                    <div class="skill-item-score">{{ skill.score }}分</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="skills-list" v-else-if="portrait?.skills?.length">
              <span class="skill-tag" v-for="(skill, idx) in portrait.skills" :key="`skill-${idx}`">
                {{ skill }}
              </span>
            </div>
            <div class="empty-hint" v-else>暂无技能信息</div>
          </div>

          <div class="card education-card">
            <div class="card-header">
              <h3>教育经历</h3>
              <span class="count">{{ portrait?.education?.length || 0 }} 条</span>
            </div>
            <div class="timeline" v-if="portrait?.education?.length">
              <div class="timeline-item" v-for="(edu, idx) in portrait.education" :key="`edu-${idx}`">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                  <div class="timeline-title">{{ edu.school }}</div>
                  <div class="timeline-desc">{{ edu.degree }} - {{ edu.major }}</div>
                  <div class="timeline-extra" v-if="edu.gpa != null && edu.gpa !== ''">GPA: {{ edu.gpa }}</div>
                </div>
              </div>
            </div>
            <div class="empty-hint" v-else>暂无教育经历</div>
          </div>

          <div class="card experience-card">
            <div class="card-header">
              <h3>实习经历</h3>
              <span class="count">{{ portrait?.internships?.length || 0 }} 条</span>
            </div>
            <div class="experience-list" v-if="portrait?.internships?.length">
              <div class="experience-item" v-for="(exp, idx) in portrait.internships" :key="`exp-${idx}`">
                <div class="exp-company">{{ exp.company }}</div>
                <div class="exp-role">{{ exp.role }}</div>
                <div class="exp-duration">{{ exp.duration_months != null ? exp.duration_months + '个月' : '时长未知' }}</div>
              </div>
            </div>
            <div class="empty-hint" v-else>暂无实习经历</div>
          </div>

          <div class="card projects-card">
            <div class="card-header">
              <h3>项目经历</h3>
              <span class="count">{{ portrait?.projects?.length || 0 }} 个</span>
            </div>
            <div class="projects-list" v-if="portrait?.projects?.length">
              <div class="project-item" v-for="(proj, idx) in portrait.projects" :key="`proj-${idx}`">
                <div class="project-name">{{ proj.name }}</div>
                <div class="project-desc" v-if="proj.description">{{ proj.description }}</div>
                <div class="project-tech" v-if="proj.tech_stack?.length">
                  <span class="tech-tag" v-for="(tech, ti) in proj.tech_stack" :key="`tech-${idx}-${ti}`">{{ tech }}</span>
                </div>
              </div>
            </div>
            <div class="empty-hint" v-else>暂无项目经历</div>
          </div>

          <div class="card certs-card" v-if="portrait?.certs?.length">
            <div class="card-header">
              <h3>证书资质</h3>
              <span class="count">{{ portrait.certs.length }} 项</span>
            </div>
            <div class="certs-list">
              <span class="cert-tag" v-for="(cert, idx) in portrait.certs" :key="`cert-${idx}`">
                📜 {{ cert }}
              </span>
            </div>
          </div>

          <div class="card awards-card" v-if="portrait?.awards?.length">
            <div class="card-header">
              <h3>荣誉奖项</h3>
              <span class="count">{{ portrait.awards.length }} 项</span>
            </div>
            <div class="awards-list">
              <div class="award-item" v-for="(award, idx) in portrait.awards" :key="`award-${idx}`">
                🏆 {{ award }}
              </div>
            </div>
          </div>
        </div>

        <div class="right-section">
          <div class="card score-card">
            <CompetitivenessGauge
              title="竞争力评估"
              :score="portrait?.competitiveness || 0"
              :level="portrait?.competitivenessLevel"
              :dimensions="competitivenessDimensions"
              :suggestions="portrait?.weaknesses || []"
              :history="competitivenessHistory"
              :peerComparison="peerComparison"
            />
            <div class="score-detail-btn-row">
              <button class="score-detail-btn" @click="toggleScoreDetail">
                {{ showScoreDetail ? '收起明细' : '查看评分明细' }}
              </button>
            </div>
            <div class="score-detail-panel" v-if="showScoreDetail">
              <div v-if="scoreDetailLoading" class="score-detail-loading">加载中...</div>
              <div v-else-if="scoreDetail">
                <div class="score-detail-section">
                  <div class="score-detail-title">竞争力评分（5维度）</div>
                  <div class="score-detail-rows">
                    <div class="score-detail-row" v-for="dim in scoreDetail.competitiveness?.dimensions || []" :key="dim.name">
                      <span class="sd-name">{{ dim.name }}</span>
                      <div class="sd-bar-track">
                        <div class="sd-bar-fill" :style="{ width: (dim.score ?? 0) + '%', background: (dim.score ?? 0) >= 70 ? '#52c41a' : (dim.score ?? 0) >= 50 ? '#667eea' : '#fa8c16' }"></div>
                      </div>
                      <span class="sd-score">{{ dim.score != null ? dim.score : '--' }}</span>
                      <span class="sd-reason" v-if="dim.reason">{{ dim.reason }}</span>
                    </div>
                  </div>
                </div>
                <div class="score-detail-section">
                  <div class="score-detail-title">信息完整度（6维度）</div>
                  <div class="score-detail-rows">
                    <div class="score-detail-row" v-for="dim in scoreDetail.completeness?.dimensions || []" :key="dim.name">
                      <span class="sd-name">{{ dim.name }}</span>
                      <div class="sd-bar-track">
                        <div class="sd-bar-fill" :style="{ width: (dim.score ?? 0) + '%', background: (dim.score ?? 0) >= 80 ? '#52c41a' : (dim.score ?? 0) >= 50 ? '#667eea' : '#ff4d4f' }"></div>
                      </div>
                      <span class="sd-score">{{ dim.score != null ? dim.score : '--' }}</span>
                      <span class="sd-tip" v-if="dim.tip">{{ dim.tip }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="score-detail-empty">暂无明细数据</div>
            </div>
          </div>

          <div class="card radar-card" v-if="skillRadarData.length > 0">
            <SkillRadarChart
              title="技能分布雷达图"
              :skills="skillRadarData"
            />
          </div>

          <div class="card timeline-card">
            <ExperienceTimeline
              title="经历时间线"
              :internships="portrait?.internships || []"
              :projects="portrait?.projects || []"
            />
          </div>

          <div class="card highlights-card">
            <div class="card-header">
              <h3>核心亮点</h3>
            </div>
            <div class="highlights-list" v-if="portrait?.highlights?.length">
              <div class="highlight-item" v-for="(h, idx) in portrait.highlights" :key="`highlight-${idx}`">
                <span class="highlight-icon">✓</span>
                <span class="highlight-text">{{ h }}</span>
              </div>
            </div>
            <div class="empty-hint" v-else>暂无亮点信息</div>
          </div>

          <div class="card weaknesses-card" v-if="portrait?.weaknesses?.length">
            <div class="card-header">
              <h3>待提升</h3>
            </div>
            <div class="weaknesses-list">
              <div class="weakness-item" v-for="(w, idx) in portrait.weaknesses" :key="`weakness-${idx}`">
                <span class="weakness-icon">!</span>
                <span class="weakness-text">{{ w }}</span>
              </div>
            </div>
          </div>

          <div class="card soft-skills-card">
            <div class="card-header">
              <h3>软技能评估</h3>
            </div>
            <div v-if="portrait?.inferredSoftSkills && Object.keys(portrait.inferredSoftSkills).length">
              <div ref="softRadarRef" class="soft-radar-box"></div>
              <div class="soft-skills-evidence">
                <div class="evidence-item" v-for="(value, key) in portrait.inferredSoftSkills" :key="key">
                  <span class="ev-label">{{ skillLabels[String(key)] || key }}</span>
                  <span class="ev-score" :class="(value.score ?? 0) >= 7 ? 'ev-high' : (value.score ?? 0) >= 5 ? 'ev-mid' : 'ev-low'">
                    {{ value.score != null ? value.score.toFixed(1) : '--' }}分
                  </span>
                  <span class="ev-text" v-if="value.evidence">{{ value.evidence }}</span>
                </div>
              </div>
            </div>
            <div class="empty-hint" v-else>
              <p>软技能评估需上传简历后自动生成</p>
              <a-button size="small" type="outline" @click="$router.push('/upload')" style="margin-top:8px">去上传简历</a-button>
            </div>
          </div>

          <!-- 兴趣领域 -->
          <div class="card interests-card" v-if="portrait?.interests?.length">
            <div class="card-header"><h3>兴趣领域</h3></div>
            <div class="interests-tags">
              <span class="interest-tag" v-for="(it, idx) in portrait.interests" :key="idx">{{ it }}</span>
            </div>
          </div>

          <!-- 求职偏好 -->
          <div class="card interests-card" v-if="portrait?.preferredCities?.length || portrait?.culturePreference?.length">
            <div class="card-header"><h3>求职偏好</h3></div>
            <div v-if="portrait?.preferredCities?.length" class="pref-row">
              <span class="pref-label">📍 期望城市</span>
              <div class="interests-tags">
                <span class="interest-tag city-tag" v-for="(c, idx) in portrait.preferredCities" :key="idx">{{ c }}</span>
              </div>
            </div>
            <div v-if="portrait?.culturePreference?.length" class="pref-row">
              <span class="pref-label">🏢 偏好文化</span>
              <div class="interests-tags">
                <span class="interest-tag culture-tag" v-for="(c, idx) in portrait.culturePreference" :key="idx">{{ c }}</span>
              </div>
            </div>
          </div>

          <!-- 能力画像（7维雷达） -->
          <div class="card ability-card" v-if="portrait?.abilityProfile && Object.keys(portrait.abilityProfile).length">
            <div class="card-header"><h3>能力画像</h3></div>
            <div ref="abilityRadarRef" class="ability-radar-box"></div>
            <div class="ability-bars">
              <div class="ability-bar-item" v-for="(val, dim) in portrait.abilityProfile" :key="dim">
                <span class="ab-dim">{{ dim }}</span>
                <div class="ab-track"><div class="ab-fill" :style="{width: (val ?? 0) + '%', background: (val ?? 0) >= 70 ? '#52c41a' : (val ?? 0) >= 50 ? '#faad14' : '#ff4d4f'}"></div></div>
                <span class="ab-val">{{ val != null ? Math.round(val) : '--' }}</span>
              </div>
            </div>
          </div>

          <!-- 性格特征 -->
          <div class="card personality-card" v-if="portrait?.personalityTraits?.length">
            <div class="card-header"><h3>性格特征</h3></div>
            <div class="personality-tags">
              <span class="personality-tag" v-for="(t, idx) in portrait.personalityTraits" :key="idx">{{ t }}</span>
            </div>
          </div>

          <!-- 职业发展路径 -->
          <div class="card career-path-card" v-if="careerPaths.length > 0">
            <div class="card-header">
              <h3>职业发展路径</h3>
              <span class="count">{{ portrait?.careerIntent || '' }}</span>
            </div>
            <div class="path-flow" v-for="(path, pi) in careerPaths.slice(0, 2)" :key="pi">
              <div class="path-step" v-for="(node, ni) in path.nodes" :key="ni">
                <div class="step-node" :class="ni === 0 ? 'step-current' : 'step-future'">
                  {{ node.title }}
                </div>
                <div class="step-arrow" v-if="ni < path.nodes.length - 1">→</div>
              </div>
            </div>
            <div class="path-hint">
              <button class="path-graph-btn" @click="$router.push(`/graph/${encodeURIComponent(portrait?.careerIntent || '')}`)">
                查看完整图谱 →
              </button>
            </div>
          </div>

          <div class="card action-card">
            <button class="primary-btn" @click="$router.push('/match')">
              <span>🎯</span> 进行人岗匹配
            </button>
            <button class="secondary-btn" @click="$router.push('/report')">
              <span>📄</span> 生成职业报告
            </button>
            <button class="edit-btn" @click="openEdit">
              <span>✏️</span> 编辑资料
            </button>
          </div>
        </div>
      </div>

      <!-- 编辑资料模态框 -->
      <div class="edit-modal-overlay" v-if="showEdit" @click.self="showEdit = false">
        <div class="edit-modal">
          <div class="edit-modal-header">
            <h3>编辑个人资料</h3>
            <button class="close-btn" @click="showEdit = false">✕</button>
          </div>
          <div class="edit-modal-body">
            <div class="form-section">
              <label class="form-label">基本信息</label>
              <div class="row-item">
                <input v-model="editForm.basicInfo.name" class="form-input" placeholder="姓名" />
                <input v-model="editForm.basicInfo.school" class="form-input" placeholder="学校" />
                <input v-model="editForm.basicInfo.major" class="form-input" placeholder="专业" />
                <input v-model="editForm.basicInfo.grade" class="form-input short-input" placeholder="年级（如：大三）" />
              </div>
            </div>

            <div class="form-section">
              <label class="form-label">职业意向 <span class="required-mark">*</span></label>
              <input
                v-model="editForm.careerIntent"
                class="form-input"
                :class="{ 'input-error': editErrors.careerIntent }"
                placeholder="例如：后端开发工程师、数据分析师..."
                @blur="validateFieldRealtime('careerIntent')"
                @input="editErrors.careerIntent && validateFieldRealtime('careerIntent')"
              />
              <span class="field-error-msg" v-if="editErrors.careerIntent">{{ editErrors.careerIntent }}</span>
            </div>

            <div class="form-section">
              <label class="form-label">技能标签 <span class="required-mark">*</span></label>
              <div class="tags-input-wrap">
                <div class="tags-list" v-if="editForm.skills.length">
                  <span
                    v-for="(skill, idx) in editForm.skills"
                    :key="`edit-skill-${idx}`"
                    class="edit-tag"
                  >
                    {{ skill }}
                    <span class="remove-tag" @click="editForm.skills.splice(idx, 1); validateFieldRealtime('skills')">×</span>
                  </span>
                </div>
                <input
                  v-model="newSkillInput"
                  class="form-input tags-append-input"
                  :class="{ 'input-error': editErrors.skills }"
                  placeholder="输入技能后按 Enter 添加"
                  @keydown.enter.prevent="addSkill"
                />
                <span class="field-error-msg" v-if="editErrors.skills">{{ editErrors.skills }}</span>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title-row">
                <label class="form-label">教育经历</label>
                <button class="add-row-btn" @click="editForm.education.push({ school: '', degree: '', major: '', gpa: '' })">+ 添加</button>
              </div>
              <div
                v-for="(edu, idx) in editForm.education"
                :key="`edu-edit-${idx}`"
                class="row-item"
              >
                <input v-model="edu.school" class="form-input" placeholder="学校名称" />
                <select v-model="edu.degree" class="form-input">
                  <option value="">学历</option>
                  <option value="专科">专科</option>
                  <option value="本科">本科</option>
                  <option value="硕士">硕士</option>
                  <option value="博士">博士</option>
                </select>
                <input v-model="edu.major" class="form-input" placeholder="专业" />
                <input v-model="edu.gpa" class="form-input short-input" placeholder="GPA（选填）" />
                <button class="remove-row-btn" @click="editForm.education.splice(idx, 1)">×</button>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title-row">
                <label class="form-label">实习经历</label>
                <button class="add-row-btn" @click="editForm.internships.push({ company: '', role: '', duration_months: null })">+ 添加</button>
              </div>
              <div
                v-for="(intern, idx) in editForm.internships"
                :key="`intern-${idx}`"
                class="row-item"
              >
                <input v-model="intern.company" class="form-input" placeholder="公司名称" />
                <input v-model="intern.role" class="form-input" placeholder="担任岗位" />
                <input v-model.number="intern.duration_months" class="form-input short-input" placeholder="月数" type="number" min="1" />
                <button class="remove-row-btn" @click="editForm.internships.splice(idx, 1)">×</button>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title-row">
                <label class="form-label">项目经历</label>
                <button class="add-row-btn" @click="editForm.projects.push({ name: '', tech_stack: [], description: '' })">+ 添加</button>
              </div>
              <div
                v-for="(proj, idx) in editForm.projects"
                :key="`proj-edit-${idx}`"
                class="row-item"
              >
                <input v-model="proj.name" class="form-input" placeholder="项目名称" />
                <input
                  :value="(proj.tech_stack || []).join(', ')"
                  class="form-input"
                  placeholder="技术栈（逗号分隔）"
                  @input="(e) => updateTechStack(proj, e)"
                />
                <button class="remove-row-btn" @click="editForm.projects.splice(idx, 1)">×</button>
              </div>
            </div>
          </div>

            <div class="form-section">
              <label class="form-label">荣誉奖项</label>
              <div class="tags-input-wrap">
                <div class="tags-list" v-if="editForm.awards.length">
                  <span v-for="(aw, idx) in editForm.awards" :key="`award-edit-${idx}`" class="edit-tag">
                    {{ aw }}<span class="remove-tag" @click="editForm.awards.splice(idx, 1)">×</span>
                  </span>
                </div>
                <input v-model="newAwardInput" class="form-input tags-append-input" placeholder="输入奖项后按 Enter 添加"
                  @keydown.enter.prevent="() => { const a = newAwardInput.trim(); if(a && !editForm.awards.includes(a)) editForm.awards.push(a); newAwardInput='' }" />
              </div>
            </div>

            <div class="form-section">
              <label class="form-label">证书资质</label>
              <div class="tags-input-wrap">
                <div class="tags-list" v-if="editForm.certs.length">
                  <span v-for="(ct, idx) in editForm.certs" :key="`cert-edit-${idx}`" class="edit-tag">
                    {{ ct }}<span class="remove-tag" @click="editForm.certs.splice(idx, 1)">×</span>
                  </span>
                </div>
                <input v-model="newCertInput" class="form-input tags-append-input" placeholder="输入证书后按 Enter 添加"
                  @keydown.enter.prevent="() => { const c = newCertInput.trim(); if(c && !editForm.certs.includes(c)) editForm.certs.push(c); newCertInput='' }" />
              </div>
            </div>

            <div class="form-section">
              <label class="form-label">兴趣领域</label>
              <div class="interest-options">
                <label
                  v-for="opt in INTEREST_OPTIONS"
                  :key="opt"
                  class="interest-option"
                  :class="{ selected: editForm.interests.includes(opt) }"
                >
                  <input type="checkbox" :value="opt" v-model="editForm.interests" style="display:none" />
                  {{ opt }}
                </label>
              </div>
            </div>

            <div class="form-section">
              <label class="form-label">期望工作城市
                <span class="form-label-tip">影响岗位匹配地区得分</span>
              </label>
              <div class="interest-options">
                <label
                  v-for="opt in CITY_OPTIONS"
                  :key="opt"
                  class="interest-option"
                  :class="{ selected: editForm.preferredCities.includes(opt) }"
                >
                  <input type="checkbox" :value="opt" v-model="editForm.preferredCities" style="display:none" />
                  {{ opt }}
                </label>
              </div>
            </div>

            <div class="form-section">
              <label class="form-label">偏好企业文化
                <span class="form-label-tip">影响岗位匹配文化得分</span>
              </label>
              <div class="interest-options">
                <label
                  v-for="opt in CULTURE_OPTIONS"
                  :key="opt"
                  class="interest-option"
                  :class="{ selected: editForm.culturePreference.includes(opt) }"
                >
                  <input type="checkbox" :value="opt" v-model="editForm.culturePreference" style="display:none" />
                  {{ opt }}
                </label>
              </div>
            </div>

          <div class="edit-modal-footer">
            <button class="cancel-btn" @click="showEdit = false">取消</button>
            <button class="save-btn" :disabled="saving" @click="saveEdit">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>

      <div class="skeleton-main" v-if="loading">
        <div class="skeleton-left">
          <SkeletonLoader type="card" :rows="3" />
          <SkeletonLoader type="tags" :rows="5" />
          <SkeletonLoader type="list" :rows="2" show-avatar />
        </div>
        <div class="skeleton-right">
          <SkeletonLoader type="score" :rows="2" />
          <SkeletonLoader type="radar" />
        </div>
      </div>
    </div>

    <div class="empty-state" v-else-if="!userStore.studentId">
      <div class="empty-icon">📄</div>
      <h3>请先上传简历</h3>
      <p>上传简历后才能查看学生画像</p>
      <button class="primary-btn" @click="$router.push('/upload')">
        上传简历
      </button>
    </div>

    <div class="error-banner" v-if="portraitStore.error && !loading">
      <span>{{ portraitStore.error }}</span>
      <button @click="portraitStore.loadPortrait()">重试</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated, computed, watch, nextTick } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { usePortraitStore } from '../stores/usePortraitStore'
import { jobApi } from '../api/job'
import { statsApi, type CompetitivenessHistoryItem, type PeerComparisonData, type SkillScoreItem } from '../api/stats'
import StepProgress from '../components/StepProgress.vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import SkillRadarChart from '../components/SkillRadarChart.vue'
import CompetitivenessGauge from '../components/CompetitivenessGauge.vue'
import ExperienceTimeline from '../components/ExperienceTimeline.vue'
import * as echarts from 'echarts'
import { portraitApi } from '../api/portrait'
import { Message } from '@arco-design/web-vue'
import { SOFT_SKILL_LABELS, INTEREST_OPTIONS, CITY_OPTIONS, CULTURE_OPTIONS } from '../constants'

const userStore = useUserStore()
const portraitStore = usePortraitStore()

const competitivenessHistory = ref<CompetitivenessHistoryItem[]>([])
const peerComparison = ref<PeerComparisonData | null>(null)
const skillScores = ref<SkillScoreItem[]>([])

async function loadCompetitivenessHistory() {
  if (!userStore.studentId) return
  try {
    const data = await statsApi.getCompetitivenessHistory(userStore.studentId)
    competitivenessHistory.value = data.history || []
    peerComparison.value = data.peer_comparison || null
  } catch {
    competitivenessHistory.value = []
    peerComparison.value = null
  }
}

async function loadSkillScores() {
  if (!userStore.studentId) return
  try {
    const data = await statsApi.getSkillScores(userStore.studentId)
    skillScores.value = data.skills || []
  } catch {
    skillScores.value = []
  }
}

// ---- 评分明细 ----
const showScoreDetail = ref(false)
const scoreDetailLoading = ref(false)
const scoreDetail = ref<any>(null)

async function toggleScoreDetail() {
  showScoreDetail.value = !showScoreDetail.value
  if (showScoreDetail.value && !scoreDetail.value && userStore.studentId) {
    scoreDetailLoading.value = true
    try {
      scoreDetail.value = await portraitApi.getScoreDetail(userStore.studentId)
    } catch {
      scoreDetail.value = null
    } finally {
      scoreDetailLoading.value = false
    }
  }
}

// ---- 编辑功能 ----
const showEdit = ref(false)
const saving = ref(false)
const newSkillInput = ref('')
const editForm = ref({
  basicInfo: { name: '', school: '', major: '', grade: '' },
  careerIntent: '',
  skills: [] as string[],
  education: [] as Array<{ school: string; degree: string; major: string; gpa: string }>,
  internships: [] as Array<{ company: string; role: string; duration_months: number | null }>,
  projects: [] as Array<{ name: string; tech_stack: string[]; description: string }>,
  awards: [] as string[],
  certs: [] as string[],
  interests: [] as string[],
  preferredCities: [] as string[],
  culturePreference: [] as string[],
})
const newAwardInput = ref('')
const newCertInput = ref('')

const editErrors = ref<Record<string, string>>({})

function validateEditForm(): boolean {
  editErrors.value = {}
  let isValid = true

  if (!editForm.value.careerIntent.trim()) {
    editErrors.value.careerIntent = '请填写职业意向'
    isValid = false
  }

  if (editForm.value.skills.length === 0) {
    editErrors.value.skills = '请至少添加一项技能'
    isValid = false
  }

  editForm.value.internships.forEach((intern, idx) => {
    if (intern.company && !intern.role) {
      editErrors.value[`intern_role_${idx}`] = '请填写岗位名称'
      isValid = false
    }
    if (!intern.company && intern.role) {
      editErrors.value[`intern_company_${idx}`] = '请填写公司名称'
      isValid = false
    }
    if (intern.duration_months !== null && intern.duration_months < 1) {
      editErrors.value[`intern_duration_${idx}`] = '时长需大于0'
      isValid = false
    }
  })

  editForm.value.projects.forEach((proj, idx) => {
    if (proj.name && proj.tech_stack && proj.tech_stack.length === 0) {
      editErrors.value[`proj_tech_${idx}`] = '请填写技术栈'
      isValid = false
    }
  })

  return isValid
}

function validateFieldRealtime(field: string) {
  switch (field) {
    case 'careerIntent':
      if (!editForm.value.careerIntent.trim()) {
        editErrors.value.careerIntent = '请填写职业意向'
      } else {
        delete editErrors.value.careerIntent
      }
      break
    case 'skills':
      if (editForm.value.skills.length === 0) {
        editErrors.value.skills = '请至少添加一项技能'
      } else {
        delete editErrors.value.skills
      }
      break
  }
}

function openEdit() {
  const p = portraitStore.portrait
  if (!p) return
  const bi = p.basicInfo || {}
  editForm.value = {
    basicInfo: { name: bi.name || '', school: bi.school || '', major: bi.major || '', grade: bi.grade || '' },
    careerIntent: p.careerIntent || '',
    skills: [...(p.skills || [])],
    education: (p.education || []).map((e: any) => ({ school: e.school || '', degree: e.degree || '', major: e.major || '', gpa: String(e.gpa || '') })),
    internships: (p.internships || []).map(i => ({ company: i.company || '', role: i.role || '', duration_months: i.duration_months ?? null })),
    projects: (p.projects || []).map(proj => ({ name: proj.name || '', tech_stack: [...(proj.tech_stack || [])], description: proj.description || '' })),
    awards: [...(p.awards || [])],
    certs: [...(p.certs || [])],
    interests: [...(p.interests || [])],
    preferredCities: [...(p.preferredCities || [])],
    culturePreference: [...(p.culturePreference || [])],
  }
  editErrors.value = {}
  showEdit.value = true
}

function addSkill() {
  const s = newSkillInput.value.trim()
  if (s && !editForm.value.skills.includes(s)) {
    editForm.value.skills.push(s)
  }
  newSkillInput.value = ''
  validateFieldRealtime('skills')
}

function updateTechStack(proj: { tech_stack: string[] }, e: Event) {
  proj.tech_stack = (e.target as HTMLInputElement).value.split(',').map(s => s.trim()).filter(Boolean)
}

async function saveEdit() {
  if (!userStore.studentId) return
  
  if (!validateEditForm()) {
    Message.warning('请完善必填信息')
    return
  }
  
  saving.value = true
  try {
    await portraitApi.update(userStore.studentId, {
      basic_info: editForm.value.basicInfo,
      career_intent: editForm.value.careerIntent,
      skills: editForm.value.skills,
      education: editForm.value.education.filter(e => e.school || e.degree || e.major),
      internships: editForm.value.internships.filter(i => i.company || i.role),
      projects: editForm.value.projects.filter(p => p.name),
      awards: editForm.value.awards,
      certs: editForm.value.certs,
      interests: editForm.value.interests,
      preferred_cities: editForm.value.preferredCities,
      culture_preference: editForm.value.culturePreference,
      inferred_soft_skills: {},
    } as any)
    await portraitStore.loadPortrait()
    // 画像核心数据变更 → 清除旧匹配缓存 + 标记更新时间
    const { useMatchStore } = await import('../stores/useMatchStore')
    useMatchStore().clearResults()
    localStorage.setItem('portrait_update_time', Date.now().toString())
    showEdit.value = false
    Message.success('资料已更新')
  } catch (e: any) {
    Message.error(e.message || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const loading = computed(() => portraitStore.loading)
const portrait = computed(() => portraitStore.portrait)

const skillRadarData = computed(() => {
  if (skillScores.value.length > 0) {
    return skillScores.value.slice(0, 8).map(skill => ({
      name: skill.name,
      value: skill.score
    }))
  }
  if (!portrait.value?.skills?.length) return []
  return portrait.value.skills.slice(0, 8).map(skill => ({
    name: skill,
    value: Math.floor(Math.random() * 40) + 60
  }))
})

const skillCategories = computed(() => {
  if (skillScores.value.length === 0) return []
  const categories: Record<string, typeof skillScores.value> = {}
  skillScores.value.forEach(skill => {
    const cat = skill.category || '其他'
    if (!categories[cat]) categories[cat] = []
    categories[cat].push(skill)
  })
  return Object.entries(categories).map(([name, skills]) => ({ name, skills }))
})

function getSkillLevelClass(score: number): string {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'average'
  return 'weak'
}

const competitivenessDimensions = computed(() => {
  const p = portrait.value
  if (!p) return []
  return [
    { name: '技能水平', score: Math.min(100, (p.skills?.length || 0) * 10) },
    { name: '项目经验', score: Math.min(100, (p.projects?.length || 0) * 25) },
    { name: '实习经历', score: Math.min(100, (p.internships?.length || 0) * 30) },
    { name: '证书资质', score: Math.min(100, (p.certs?.length || 0) * 15) },
    { name: '荣誉奖项', score: Math.min(100, (p.awards?.length || 0) * 20) },
  ]
})

// ---- ECharts：软技能雷达图 ----
const softRadarRef = ref<HTMLElement | null>(null)
let softRadarChart: echarts.ECharts | null = null
let softRadarObserver: ResizeObserver | null = null

const SKILL_ORDER = ['communication', 'learning_ability', 'innovation', 'teamwork', 'stress_resistance']

function renderSoftRadar(softSkills: Record<string, any>) {
  if (!softRadarRef.value) return
  if (!softRadarChart) {
    softRadarChart = echarts.init(softRadarRef.value)
    softRadarObserver = new ResizeObserver(() => softRadarChart?.resize())
    softRadarObserver.observe(softRadarRef.value)
  }

  const indicator = SKILL_ORDER.map(k => ({ name: skillLabels[k] || k, max: 10 }))
  const values = SKILL_ORDER.map(k => {
    const v = softSkills[k]
    return v && v.score != null ? Number(v.score) : 0
  })

  // 行业平均参考线（固定基准）
  const avgValues = SKILL_ORDER.map(() => 6.0)

  softRadarChart.setOption({
    legend: {
      data: ['我的评分', '行业平均'],
      bottom: 0,
      textStyle: { fontSize: 11, color: '#888' },
      itemWidth: 12,
      itemHeight: 8,
    },
    tooltip: {
      trigger: 'item',
      formatter: (_params: any) => {
        const labels = SKILL_ORDER.map(k => skillLabels[k] || k)
        return labels.map((l, i) => `${l}：${values[i].toFixed(1)}`).join('<br/>')
      },
    },
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 5,
      radius: '65%',
      axisName: { color: '#555', fontSize: 12, fontWeight: 500 },
      splitArea: {
        areaStyle: {
          color: ['rgba(102,126,234,0.04)', 'rgba(102,126,234,0.08)',
                  'rgba(102,126,234,0.13)', 'rgba(102,126,234,0.18)',
                  'rgba(102,126,234,0.23)'],
        },
      },
      axisLine: { lineStyle: { color: '#dde0f0' } },
      splitLine: { lineStyle: { color: '#dde0f0' } },
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: values,
          name: '我的评分',
          areaStyle: { color: 'rgba(118,75,162,0.22)' },
          lineStyle: { color: '#764ba2', width: 2 },
          itemStyle: { color: '#667eea' },
          symbol: 'circle',
          symbolSize: 5,
        },
        {
          value: avgValues,
          name: '行业平均',
          areaStyle: { color: 'rgba(0,0,0,0)' },
          lineStyle: { color: '#ccc', width: 1.5, type: 'dashed' },
          itemStyle: { color: '#ccc' },
          symbol: 'none',
        },
      ],
    }],
  }, true)
}

watch(
  portrait,
  async (p) => {
    if (!p?.inferredSoftSkills) return
    await nextTick()
    renderSoftRadar(p.inferredSoftSkills)
  },
  { deep: true, flush: 'post' },
)

onUnmounted(() => {
  softRadarObserver?.disconnect()
  softRadarObserver = null
  softRadarChart?.dispose()
  softRadarChart = null
  abilityRadarChart?.dispose()
  abilityRadarChart = null
})

// ---- ECharts：能力画像雷达图 ----
const abilityRadarRef = ref<HTMLElement | null>(null)
let abilityRadarChart: echarts.ECharts | null = null

function renderAbilityRadar(profile: Record<string, number>) {
  if (!abilityRadarRef.value) return
  const dims = Object.keys(profile)
  if (!dims.length) return
  if (!abilityRadarChart) {
    abilityRadarChart = echarts.init(abilityRadarRef.value)
  }
  const indicator = dims.map(d => ({ name: d, max: 100 }))
  const values = dims.map(d => Math.round(profile[d] || 0))
  abilityRadarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      radius: '65%',
      axisName: { color: '#555', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(52,211,153,0.04)', 'rgba(52,211,153,0.08)', 'rgba(52,211,153,0.13)', 'rgba(52,211,153,0.18)'] } },
      axisLine: { lineStyle: { color: '#d1fae5' } },
      splitLine: { lineStyle: { color: '#d1fae5' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '能力评分',
        areaStyle: { color: 'rgba(16,185,129,0.2)' },
        lineStyle: { color: '#10b981', width: 2 },
        itemStyle: { color: '#059669' },
        symbol: 'circle',
        symbolSize: 4,
      }],
    }],
  }, true)
}

watch(
  () => portrait.value?.abilityProfile,
  async (profile) => {
    if (!profile || !Object.keys(profile).length) return
    await nextTick()
    renderAbilityRadar(profile)
  },
  { deep: true, immediate: true, flush: 'post' },
)

const skillLabels = SOFT_SKILL_LABELS

const careerPaths = ref<Array<{ nodes: Array<{ title: string; salary?: string }> }>>([])

async function loadCareerPaths(jobTitle: string) {
  if (!jobTitle) return
  try {
    const data = await jobApi.getCareerGraph(jobTitle)
    careerPaths.value = (data.promotion_paths || []).filter(p => p.nodes && p.nodes.length > 1)
  } catch {
    careerPaths.value = []
  }
}

watch(
  () => portrait.value?.careerIntent,
  (intent) => { if (intent) loadCareerPaths(intent) },
  { immediate: true },
)

onMounted(async () => {
  if (userStore.studentId) {
    await portraitStore.ensureFresh()
    loadCompetitivenessHistory()
    loadSkillScores()
    // 修复: localStorage 加载时 watch immediate 可能在 DOM 就绪前触发，手动补一次渲染
    await nextTick()
    if (portrait.value?.abilityProfile && Object.keys(portrait.value.abilityProfile).length) {
      renderAbilityRadar(portrait.value.abilityProfile)
    }
    if (portrait.value?.inferredSoftSkills && Object.keys(portrait.value.inferredSoftSkills).length) {
      renderSoftRadar(portrait.value.inferredSoftSkills)
    }
  }
})

onActivated(async () => {
  if (!userStore.studentId) return
  
  const lastUpdate = localStorage.getItem('portrait_update_time')
  const lastLoad = localStorage.getItem('portrait_load_time')
  
  if (lastUpdate && (!lastLoad || parseInt(lastUpdate) > parseInt(lastLoad || '0'))) {
    await portraitStore.loadPortrait()
    localStorage.setItem('portrait_load_time', Date.now().toString())
  }
})
</script>

<style scoped>
.error-banner {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #cf1322;
  padding: 12px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  z-index: 100;
}
.error-banner button {
  background: #cf1322;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.portrait-page {
  min-height: 100vh;
  background: #f8fafc;
}

.empty-state-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
}
.empty-state-icon { font-size: 64px; margin-bottom: 16px; }
.empty-state-page h2 { font-size: 20px; color: #1d2129; margin: 0 0 8px; }
.empty-state-page p { color: #86909c; margin: 0 0 24px; }

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

.portrait-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
}

.left-section, .right-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.count {
  font-size: 13px;
  color: #666;
}

.basic-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
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
  color: #1a1a2e;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
}

.skills-detailed {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skill-category {
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px;
}

.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.category-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.category-count {
  font-size: 12px;
  color: #999;
}

.category-skills {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skill-item-detailed {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skill-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skill-item-name {
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.skill-item-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.skill-level {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.skill-level.excellent {
  background: #f6ffed;
  color: #52c41a;
}

.skill-level.good {
  background: #e6f7ff;
  color: #1890ff;
}

.skill-level.average {
  background: #fff7e6;
  color: #fa8c16;
}

.skill-level.weak {
  background: #fff1f0;
  color: #f5222d;
}

.skill-certified {
  font-size: 11px;
  color: #52c41a;
  background: #f6ffed;
  padding: 2px 6px;
  border-radius: 4px;
}

.skill-item-bar {
  height: 4px;
  background: #e5e5e5;
  border-radius: 2px;
  overflow: hidden;
}

.skill-item-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.skill-item-fill.excellent {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.skill-item-fill.good {
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
}

.skill-item-fill.average {
  background: linear-gradient(90deg, #faad14 0%, #ffc53d 100%);
}

.skill-item-fill.weak {
  background: linear-gradient(90deg, #ff4d4f 0%, #ff7875 100%);
}

.skill-item-score {
  font-size: 11px;
  color: #999;
  text-align: right;
}

.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  padding-bottom: 20px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #667eea;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 14px;
  width: 2px;
  height: calc(100% - 10px);
  background: #eee;
}

.timeline-item:last-child::before {
  display: none;
}

.timeline-title {
  font-weight: 500;
  font-size: 15px;
  color: #1a1a2e;
}

.timeline-desc {
  font-size: 13px;
  color: #666;
  margin-top: 2px;
}

.timeline-extra {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.experience-list, .projects-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.experience-item, .project-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 10px;
}

.exp-company, .project-name {
  font-weight: 500;
  font-size: 14px;
  color: #1a1a2e;
}

.exp-role {
  font-size: 13px;
  color: #666;
  margin-top: 2px;
}

.exp-duration {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.project-desc {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}

.project-tech {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.tech-tag {
  padding: 2px 8px;
  background: #e8f4ff;
  color: #1890ff;
  border-radius: 4px;
  font-size: 11px;
}

.certs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cert-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, #fff7e6 0%, #ffe7ba 100%);
  color: #d46b08;
  border-radius: 20px;
  font-size: 13px;
  border: 1px solid #ffd591;
}

.awards-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.award-item {
  padding: 10px 14px;
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  color: #389e0d;
  border-radius: 10px;
  font-size: 14px;
  border: 1px solid #b7eb8f;
}

/* ── 兴趣/能力/性格卡片 ─────────────────────────────────── */
.interests-tags, .personality-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 0;
}
.interest-tag {
  padding: 5px 14px;
  background: linear-gradient(135deg, #e6f7ff, #bae7ff);
  color: #096dd9;
  border-radius: 20px;
  font-size: 13px;
  border: 1px solid #91d5ff;
}
.city-tag {
  background: linear-gradient(135deg, #f0f9eb, #d9f7be);
  color: #389e0d;
  border-color: #b7eb8f;
}
.culture-tag {
  background: linear-gradient(135deg, #f9f0ff, #efdbff);
  color: #531dab;
  border-color: #d3adf7;
}
.pref-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}
.pref-row:last-child { margin-bottom: 0; }
.pref-label {
  font-size: 12px;
  color: #888;
  white-space: nowrap;
  padding-top: 5px;
  min-width: 72px;
}
.personality-tag {
  padding: 5px 14px;
  background: linear-gradient(135deg, #fff0f6, #ffd6e7);
  color: #c41d7f;
  border-radius: 20px;
  font-size: 13px;
  border: 1px solid #ffadd2;
}
.ability-radar-box {
  width: 100%;
  height: 220px;
}

.score-detail-btn-row {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}

.score-detail-btn {
  padding: 6px 20px;
  border-radius: 20px;
  border: 1.5px solid #667eea;
  background: transparent;
  color: #667eea;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.score-detail-btn:hover {
  background: #667eea;
  color: white;
}

.score-detail-panel {
  margin-top: 16px;
  border-top: 1px dashed #eee;
  padding-top: 16px;
}

.score-detail-loading {
  text-align: center;
  color: #aaa;
  font-size: 13px;
  padding: 12px;
}

.score-detail-empty {
  text-align: center;
  color: #bbb;
  font-size: 13px;
}

.score-detail-section {
  margin-bottom: 16px;
}

.score-detail-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 10px;
}

.score-detail-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-name {
  font-size: 12px;
  color: #555;
  width: 70px;
  flex-shrink: 0;
}

.sd-bar-track {
  flex: 1;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
}

.sd-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.sd-score {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}

.sd-reason, .sd-tip {
  font-size: 11px;
  color: #999;
  width: 100%;
  padding-left: 78px;
  margin-top: -4px;
}
.ability-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.ability-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.ab-dim { width: 64px; flex-shrink: 0; color: #555; }
.ab-track { flex: 1; background: #f0f0f0; border-radius: 4px; height: 8px; overflow: hidden; }
.ab-fill { height: 100%; border-radius: 4px; transition: width .4s; }
.ab-val { width: 30px; text-align: right; color: #333; font-weight: 600; }

.empty-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 20px;
}

.score-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-label {
  width: 60px;
  font-size: 13px;
  color: #666;
}

.score-bar {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.score-fill.competitiveness {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.score-value {
  width: 50px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

.competitiveness-level {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.level-label {
  font-size: 13px;
  color: #666;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.level-badge.excellent {
  background: linear-gradient(135deg, #f6ffed, #d9f7be);
  color: #389e0d;
  border: 1px solid #b7eb8f;
}

.level-badge.good {
  background: linear-gradient(135deg, #e6f7ff, #bae7ff);
  color: #096dd9;
  border: 1px solid #91d5ff;
}

.level-badge.normal {
  background: #fff7e6;
  color: #fa8c16;
}

.level-badge.weak {
  background: #fff1f0;
  color: #f5222d;
}

@keyframes badge-pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; opacity: 1; }
  50% { box-shadow: 0 0 0 6px transparent; opacity: 0.85; }
}

.badge-pulse {
  animation: badge-pulse 2s ease-in-out infinite;
}

.highlights-list, .weaknesses-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.highlight-item, .weakness-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.highlight-icon {
  color: #52c41a;
  font-weight: 600;
}

.weakness-icon {
  color: #faad14;
  font-weight: 600;
}

.highlight-text, .weakness-text {
  font-size: 14px;
  color: #333;
}

.soft-radar-box {
  width: 100%;
  height: 220px;
  margin-bottom: 12px;
}

.soft-skills-evidence {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  flex-wrap: wrap;
}

.ev-label {
  font-weight: 600;
  color: #444;
  min-width: 60px;
}

.ev-score {
  font-size: 12px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 10px;
}

.ev-high { background: #f6ffed; color: #389e0d; }
.ev-mid  { background: #e6f7ff; color: #0958d9; }
.ev-low  { background: #fff7e6; color: #d46b08; }

.ev-text {
  color: #888;
  font-size: 12px;
  flex: 1;
}

.path-flow {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
  padding: 10px;
  background: #f8fafc;
  border-radius: 10px;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 4px;
}

.step-node {
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.step-current {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.step-future {
  background: #e8f4ff;
  color: #1677ff;
  border: 1px solid #bae0ff;
}

.step-arrow {
  color: #aaa;
  font-size: 14px;
}

.path-hint {
  text-align: right;
  margin-top: 4px;
}

.path-graph-btn {
  background: none;
  border: none;
  color: #667eea;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 0;
}

.path-graph-btn:hover {
  text-decoration: underline;
}

.action-card {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.secondary-btn {
  width: 100%;
  padding: 12px 24px;
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
  transform: translateY(-1px);
}

.primary-btn {
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
}

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1a1a2e;
}

.empty-state p {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
}

.empty-state .primary-btn {
  width: auto;
  padding: 12px 32px;
}

.skeleton-main {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
  padding: 24px;
}

.skeleton-left,
.skeleton-right {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

@media (max-width: 1024px) {
  .skeleton-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  .portrait-container {
    padding: 16px;
  }
  .page-header {
    padding: 16px;
  }
}

/* ---- 编辑按钮 ---- */
.edit-btn {
  margin-top: 8px;
  width: 100%;
  padding: 10px;
  background: #f0f5ff;
  color: #2f54eb;
  border: 1px solid #adc6ff;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.edit-btn:hover { background: #e0ebff; }

/* ---- 编辑模态框 ---- */
.edit-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.edit-modal {
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 560px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.edit-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.edit-modal-header h3 { margin: 0; font-size: 18px; color: #1a1a2e; }
.close-btn {
  background: none; border: none; font-size: 18px;
  cursor: pointer; color: #999; line-height: 1;
}
.close-btn:hover { color: #333; }
.edit-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.interest-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.interest-option {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1.5px solid #e0e0e0;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.interest-option:hover {
  border-color: #667eea;
  color: #667eea;
}

.interest-option.selected {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

.edit-modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.form-section { display: flex; flex-direction: column; gap: 8px; }
.form-label { font-size: 13px; font-weight: 600; color: #555; }
.form-label-tip { font-size: 11px; font-weight: 400; color: #aaa; margin-left: 6px; }
.form-input {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}
.form-input:focus { border-color: #667eea; }
.short-input { width: 80px; }
.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.add-row-btn {
  background: none; border: none;
  color: #667eea; font-size: 13px;
  cursor: pointer; font-weight: 500;
}
.add-row-btn:hover { color: #4f5bdb; }
.row-item {
  display: flex;
  gap: 8px;
  align-items: center;
}
.row-item .form-input { flex: 1; }
.remove-row-btn {
  background: none; border: none;
  color: #ff4d4f; font-size: 18px;
  cursor: pointer; flex-shrink: 0;
  line-height: 1;
}
.tags-input-wrap { display: flex; flex-direction: column; gap: 8px; }
.tags-list { display: flex; flex-wrap: wrap; gap: 6px; }
.edit-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: #f0f5ff; color: #2f54eb;
  border: 1px solid #adc6ff; border-radius: 6px;
  padding: 3px 10px; font-size: 13px;
}
.remove-tag {
  cursor: pointer; color: #999; font-size: 14px; line-height: 1;
}
.remove-tag:hover { color: #ff4d4f; }
.tags-append-input { margin-top: 4px; }
.cancel-btn {
  padding: 9px 20px;
  background: #fff; border: 1px solid #d9d9d9;
  border-radius: 8px; color: #666;
  font-size: 14px; cursor: pointer;
}
.cancel-btn:hover { border-color: #999; }
.save-btn {
  padding: 9px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none; border-radius: 8px; color: #fff;
  font-size: 14px; font-weight: 500; cursor: pointer;
}
.save-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.required-mark {
  color: #f5222d;
  font-size: 12px;
}

.field-error-msg {
  font-size: 12px;
  color: #f5222d;
  margin-top: 4px;
  display: block;
}

.input-error {
  border-color: #f5222d !important;
}

.input-error:focus {
  box-shadow: 0 0 0 2px rgba(245, 34, 45, 0.1);
}
</style>
