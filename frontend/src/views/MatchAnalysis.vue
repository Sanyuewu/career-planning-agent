<template>
  <div class="match-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <span>←</span>
      </button>
      <div class="header-content">
        <h1>人岗匹配</h1>
        <p>智能分析岗位匹配度</p>
      </div>
    </div>
    <StepProgress />

    <!-- O4-c: 空状态 -->
    <div v-if="!userStore.studentId" class="empty-state-page">
      <div class="empty-state-icon">🎯</div>
      <h2>请先完善画像</h2>
      <p>完成简历上传和学生画像后，才能进行人岗匹配分析</p>
      <a-button type="primary" @click="$router.push('/upload')">上传简历</a-button>
    </div>

    <div class="match-container" v-if="userStore.studentId">
      <div class="search-section">
        <div class="recommend-bar">
          <button class="recommend-btn" @click="fetchRecommendations" :disabled="recommendLoading">
            {{ recommendLoading ? '分析中...' : '🎯 为我推荐最匹配岗位' }}
          </button>
        </div>

        <div v-if="recommendations.length > 0" class="recommend-section">
          <h3>根据您的画像，推荐以下岗位：</h3>
          <div class="rec-list">
            <div
              v-for="rec in recommendations"
              :key="rec.job_title"
              class="rec-card"
              @click="selectJob(rec.job_title)"
            >
              <div class="rec-top">
                <span class="rec-title">{{ rec.job_title }}</span>
                <span class="rec-score">{{ rec.score != null ? rec.score.toFixed(0) : '--' }}分</span>
              </div>
              <p class="rec-summary">{{ rec.summary }}</p>
            </div>
          </div>
        </div>

        <div class="filter-section">
          <div class="filter-row">
            <div class="filter-group">
              <label class="filter-label">行业分类</label>
              <div class="filter-options">
                <button
                  v-for="cat in jobCategories"
                  :key="cat.value"
                  :class="['filter-option', { active: selectedCategory === cat.value }]"
                  @click="selectCategory(cat.value)"
                >
                  {{ cat.label }}
                </button>
              </div>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-group">
              <label class="filter-label">技能类型</label>
              <div class="filter-options">
                <button
                  v-for="skill in skillTypes"
                  :key="skill.value"
                  :class="['filter-option', { active: selectedSkillType === skill.value }]"
                  @click="selectSkillType(skill.value)"
                >
                  {{ skill.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 权重方案选择 -->
        <div class="weight-preset-section">
          <label class="filter-label">权重方案</label>
          <div class="weight-preset-options">
            <button
              v-for="preset in weightPresets"
              :key="preset.key"
              :class="['weight-preset-btn', { active: selectedWeightPreset === preset.key }]"
              @click="selectedWeightPreset = preset.key"
              :title="preset.key === 'default' ? '基础20% 技能35% 素养25% 潜力20%' :
                      preset.key === 'tech' ? '基础20% 技能45% 素养20% 潜力15%' :
                      preset.key === 'management' ? '基础20% 技能30% 素养35% 潜力15%' :
                      preset.key === 'research' ? '基础25% 技能40% 素养20% 潜力15%' :
                      '基础20% 技能30% 素养30% 潜力20%'"
            >
              {{ preset.label }}
            </button>
          </div>
          <div class="weight-detail">
            <span v-if="selectedWeightPreset === 'default'">基础 20% · 技能 35% · 素养 25% · 潜力 20%</span>
            <span v-else-if="selectedWeightPreset === 'tech'">基础 20% · 技能 45% · 素养 20% · 潜力 15%</span>
            <span v-else-if="selectedWeightPreset === 'management'">基础 20% · 技能 30% · 素养 35% · 潜力 15%</span>
            <span v-else-if="selectedWeightPreset === 'research'">基础 25% · 技能 40% · 素养 20% · 潜力 15%</span>
            <span v-else>基础 20% · 技能 30% · 素养 30% · 潜力 20%</span>
          </div>
        </div>

        <div class="search-box" style="position:relative">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input
              v-model="searchJob"
              placeholder="搜索岗位名称..."
              @input="onSearchInput"
              @keyup.enter="doMatch"
              @focus="onSearchFocus"
              @blur="hideJobSuggestions"
              autocomplete="off"
            />
            <button v-if="searchJob" class="clear-btn" @click="clearSearch">✕</button>
          </div>
          <button class="search-btn" @click="doMatch" :disabled="matchStore.loading">
            {{ matchStore.loading ? '分析中...' : '分析匹配' }}
          </button>
          <div class="search-dropdown" v-if="showJobSuggestions">
            <div class="dropdown-section" v-if="searchHistory.length > 0 && !searchJob.trim()">
              <div class="dropdown-header">
                <span>搜索历史</span>
                <button class="clear-history-btn" @click="clearSearchHistory">清空</button>
              </div>
              <div class="history-tags">
                <span
                  v-for="(item, index) in searchHistory"
                  :key="index"
                  class="history-tag"
                  @mousedown.prevent="selectJob(item)"
                >
                  🕐 {{ item }}
                </span>
              </div>
            </div>
            <div class="dropdown-section" v-if="filteredJobSuggestions.length > 0">
              <div class="dropdown-header" v-if="searchJob.trim()">
                <span>匹配岗位</span>
                <span class="match-count">{{ filteredJobSuggestions.length }} 个结果</span>
              </div>
              <div
                class="job-suggestion-item"
                v-for="job in filteredJobSuggestions"
                :key="job"
                @mousedown.prevent="selectJob(job)"
              >
                <span class="job-name">{{ job }}</span>
                <span class="job-category-tag" v-if="getJobCategory(job)">{{ getJobCategory(job) }}</span>
              </div>
            </div>
            <div class="no-result" v-if="searchJob.trim() && filteredJobSuggestions.length === 0">
              <span>未找到匹配的岗位</span>
            </div>
          </div>
        </div>
        <div class="hot-jobs">
          <span class="label">热门岗位：</span>
          <button
            v-for="job in filteredHotJobs"
            :key="job"
            class="job-tag"
            :disabled="matchStore.loading"
            @click="selectJob(job)"
          >
            {{ job }}
          </button>
          <button 
            class="job-tag batch-btn" 
            @click="batchMatch" 
            :disabled="matchStore.loading || batchMatching"
          >
            {{ batchMatching ? `批量匹配中(${batchProgress}/${filteredHotJobs.length})` : '🚀 一键匹配全部热门岗位' }}
          </button>
        </div>
      </div>

      <div class="skeleton-section" v-if="matchStore.loading">
        <div class="skeleton-card">
          <div class="skel skel-title"></div>
          <div class="skel skel-circle"></div>
          <div class="skel skel-bar"></div>
          <div class="skel skel-bar short"></div>
          <div class="skel skel-bar"></div>
          <div class="skel skel-bar short"></div>
        </div>
        <div class="skeleton-hint">AI正在深度分析您的岗位匹配度，请稍候...</div>
      </div>

      <div class="no-result-hint" v-else-if="!currentResult && !matchStore.loading">
        <EmptyState 
          icon="🔍"
          title="搜索岗位开始分析"
          description="输入岗位名称或点击热门岗位进行匹配分析"
          action-text="开始匹配"
          @action="doMatch"
        />
      </div>
      
      <div class="result-section" v-else-if="currentResult">
        <GuestLimitHint type="match" @login="showLoginModal = true" />
        <!-- CrewAI Agent分析过程展示 -->
        <AgentProcessPanel
          v-if="showCrewAIPanel && crewAIEnabled"
          :agent-states="getAgentStatesForPanel()"
          :current-agent="crewStore.currentAgent || undefined"
          :duration="crewStore.lastResult?.duration_seconds"
          :confidence="crewStore.lastResult?.results?.confidence"
        />
        
        <!-- 深度分析进度 -->
        <AsyncTaskProgress
          v-if="showDeepAnalysis && crewStore.isProcessing"
          :visible="showDeepAnalysis"
          title="🚀 CrewAI深度分析"
          description="正在使用多Agent协作进行深度分析..."
          :progress="crewStore.progress"
          status="running"
          :steps="['简历分析', '岗位匹配', '职业建议', '报告生成']"
          :current-step="Math.floor(crewStore.progress * 4)"
          @cancel="cancelDeepAnalysis"
        />
        
        <div class="score-card">
          <div class="score-header">
            <h2>{{ currentResult.job_title }}</h2>
            <div class="score-header-right">
              <span class="confidence" v-if="currentResult.confidence">
                置信度 {{ (currentResult.confidence * 100).toFixed(0) }}%
              </span>
              <button 
                v-if="crewAIEnabled && !showDeepAnalysis" 
                class="deep-analysis-btn" 
                @click="startDeepAnalysis" 
                :disabled="crewStore.isProcessing"
                title="使用CrewAI进行深度分析"
              >
                🚀 深度分析
              </button>
              <button class="reanalyze-btn" @click="doMatch" :disabled="matchStore.loading" title="重新分析（刷新匹配结果）">
                {{ matchStore.loading ? '分析中...' : '重新分析' }}
              </button>
            </div>
          </div>
          <div class="score-circle-container">
            <svg viewBox="0 0 100 100" class="score-svg">
              <circle cx="50" cy="50" r="45" class="bg-circle" />
              <circle 
                cx="50" cy="50" r="45" 
                class="score-circle"
                :style="{ strokeDashoffset: 283 - (283 * currentResult.overall_score / 100) }"
              />
            </svg>
            <div class="score-value">
              <span class="number">{{ currentResult.overall_score?.toFixed(0) || 0 }}</span>
              <span class="unit">分</span>
            </div>
          </div>
          <div class="score-label">综合匹配度</div>
          <div class="match-level" :class="getMatchLevel(currentResult.overall_score)">
            {{ getMatchLevelText(currentResult.overall_score) }}
          </div>
          <div class="quick-actions">
            <button class="quick-action-btn report-btn" @click="goToReport">
              <span>📊</span> 生成报告
            </button>
            <button class="quick-action-btn chat-btn" @click="goToChat">
              <span>💬</span> 咨询AI
            </button>
          </div>
          <div class="review-warning" v-if="currentResult.confidence && currentResult.confidence < 0.75">
            ⚠️ 置信度较低，建议人工复核
          </div>
          <div class="confidence-breakdown-section" v-if="currentResult.confidence_breakdown">
            <div class="breakdown-header" @click="showConfidenceDetail = !showConfidenceDetail">
              <span class="breakdown-title">🔍 置信度分析</span>
              <span class="toggle-arrow">{{ showConfidenceDetail ? '▲' : '▼' }}</span>
            </div>
            <div class="breakdown-body" v-if="showConfidenceDetail">
              <div class="breakdown-item">
                <div class="breakdown-label">
                  <span>数据质量</span>
                  <span class="breakdown-value">{{ (currentResult.confidence_breakdown.dataQuality * 100).toFixed(0) }}%</span>
                </div>
                <div class="breakdown-bar">
                  <div class="breakdown-fill" :style="{ width: (currentResult.confidence_breakdown.dataQuality * 100) + '%' }"></div>
                </div>
              </div>
              <div class="breakdown-item">
                <div class="breakdown-label">
                  <span>匹配精度</span>
                  <span class="breakdown-value">{{ (currentResult.confidence_breakdown.matchPrecision * 100).toFixed(0) }}%</span>
                </div>
                <div class="breakdown-bar">
                  <div class="breakdown-fill" :style="{ width: (currentResult.confidence_breakdown.matchPrecision * 100) + '%' }"></div>
                </div>
              </div>
              <div class="breakdown-item">
                <div class="breakdown-label">
                  <span>证据强度</span>
                  <span class="breakdown-value">{{ (currentResult.confidence_breakdown.evidenceStrength * 100).toFixed(0) }}%</span>
                </div>
                <div class="breakdown-bar">
                  <div class="breakdown-fill" :style="{ width: (currentResult.confidence_breakdown.evidenceStrength * 100) + '%' }"></div>
                </div>
              </div>
              <div class="breakdown-factors" v-if="Object.keys(currentResult.confidence_breakdown.factors || {}).length > 0">
                <div class="factor-item" v-for="(desc, factor) in currentResult.confidence_breakdown.factors" :key="factor">
                  <span class="factor-name">{{ factor }}</span>
                  <span class="factor-desc">{{ desc }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="competitive-context" v-if="currentResult.competitive_context">
            {{ currentResult.competitive_context }}
          </div>
        </div>

        <div class="dimensions-card">
          <div class="card-header-with-action">
            <h3>五维度分析</h3>
            <button class="detail-toggle-btn" @click="showDimensionDetailModal = true">
              📈 查看详情
            </button>
          </div>
          <div class="dimensions-layout">
            <div ref="radarRef" class="radar-chart-box"></div>
            <div class="dimension-list">
              <div class="dimension-item" v-for="dim in dimensionList" :key="dim.key">
                <div class="dim-header">
                  <span class="dim-name">{{ dim.name }}</span>
                  <span class="dim-score" :class="(dim.score ?? 0) >= 80 ? 'score-high' : (dim.score ?? 0) >= 60 ? 'score-mid' : 'score-low'">
                    {{ dim.score != null ? dim.score : '--' }}分
                  </span>
                </div>
                <div class="dim-bar">
                  <div class="dim-fill" :style="{ width: (dim.score ?? 0) + '%', background: (dim.score ?? 0) >= 80 ? 'linear-gradient(90deg,#52c41a,#73d13d)' : (dim.score ?? 0) >= 60 ? 'linear-gradient(90deg,#667eea,#764ba2)' : 'linear-gradient(90deg,#fa8c16,#ffa940)' }"></div>
                </div>
                <div class="dim-detail" v-if="dim.detail">{{ dim.detail }}</div>
                <div class="dim-evidence-detail" v-if="dim.evidence">
                  <div
                    v-for="(item, i) in parseEvidence(dim.evidence)"
                    :key="i"
                    :class="['evidence-item', 'evidence-' + item.type]"
                  >
                    <span class="evidence-bullet">{{ item.type === 'match' ? '✓' : item.type === 'gap' ? '✗' : '·' }}</span>
                    <span>{{ item.text }}</span>
                  </div>
                </div>
                <div class="dim-jd-sources" v-if="dim.jd_sources?.length">
                  <div class="jd-source-header">来自真实招聘JD的要求：</div>
                  <div class="jd-source-item" v-for="(src, si) in dim.jd_sources" :key="`jdsrc-${si}`">
                    <span :class="['src-importance', src.importance === 'must_have' ? 'src-must' : 'src-nice']">
                      {{ src.importance === 'must_have' ? '必须' : '加分' }}
                    </span>
                    <span class="src-skill">{{ src.skill }}</span>
                    <span class="src-from" v-if="src.source">— {{ src.source }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="skills-card" v-if="currentResult.matched_skills?.length || currentResult.skill_match_details?.length">
          <div class="card-header-with-action">
            <h3>技能匹配详情</h3>
            <button class="detail-toggle-btn" @click="showSkillDetailModal = true">
              📊 查看完整分析
            </button>
          </div>
          <div class="skill-match-summary">
            <div class="summary-item" v-if="matchedSkillCount > 0">
              <span class="summary-label">完全匹配</span>
              <span class="summary-value matched">{{ matchedSkillCount }}项</span>
            </div>
            <div class="summary-item" v-if="partialSkillCount > 0">
              <span class="summary-label">部分匹配</span>
              <span class="summary-value partial">{{ partialSkillCount }}项</span>
            </div>
            <div class="summary-item" v-if="semanticMatchedCount > 0">
              <span class="summary-label">语义匹配</span>
              <span class="summary-value semantic">{{ semanticMatchedCount }}项</span>
            </div>
            <div class="summary-item" v-if="missingSkillCount > 0">
              <span class="summary-label">缺失技能</span>
              <span class="summary-value missing">{{ missingSkillCount }}项</span>
            </div>
            <div class="summary-item" v-if="skillHitRate !== null">
              <span class="summary-label">关键技能命中率</span>
              <span class="summary-value" :class="skillHitRate >= 80 ? 'matched' : skillHitRate >= 60 ? 'partial' : 'missing'">
                {{ skillHitRate }}%
              </span>
            </div>
          </div>
          <div class="skill-tags">
            <span class="skill-tag matched" v-for="(skill, idx) in currentResult.matched_skills?.slice(0, 8)" :key="`matched-${idx}`">
              ✓ {{ skill }}
            </span>
            <span v-if="(currentResult.matched_skills?.length || 0) > 8" class="skill-tag more">
              +{{ (currentResult.matched_skills?.length || 0) - 8 }} 更多
            </span>
          </div>
        </div>
        <div class="review-hint" v-if="currentResult.confidence && currentResult.confidence < 0.75">
          ⚠️ 置信度较低（{{ (currentResult.confidence * 100).toFixed(0) }}%），当前结果仅供参考，建议人工复核或补充简历信息后重新分析
        </div>

        <div class="gap-card" v-if="currentResult.gap_skills?.length || currentResult.gap_analysis?.length">
          <div class="card-header-with-action">
            <h3>差距分析与改进建议</h3>
            <button class="detail-toggle-btn" @click="showGapDetailModal = true" v-if="currentResult.gap_analysis?.length">
              📋 详细分析
            </button>
          </div>
          <div class="gap-summary" v-if="currentResult.gap_analysis?.length">
            <div class="gap-summary-item" v-for="(gap, idx) in currentResult.gap_analysis.slice(0, 2)" :key="idx">
              <div class="gap-severity-badge" :class="gap.severity">
                {{ gap.severity === 'critical' ? '关键' : gap.severity === 'moderate' ? '中等' : '轻微' }}
              </div>
              <div class="gap-summary-content">
                <p class="gap-summary-desc">{{ gap.gapDescription }}</p>
                <p class="gap-summary-impact">{{ gap.impact }}</p>
              </div>
            </div>
          </div>
          <div class="gap-list">
            <div class="gap-item" v-for="(gap, idx) in currentResult.gap_skills?.slice(0, 5)" :key="`gap-${idx}`">
              <div class="gap-header">
                <span class="gap-skill">{{ gap.skill }}</span>
                <span :class="['gap-importance', gap.importance]">
                  {{ gap.importance === 'must_have' ? '必须' : '加分' }}
                </span>
              </div>
              <div class="gap-suggestion" v-if="gap.suggestion">{{ gap.suggestion }}</div>
              <div class="gap-resources" v-if="SKILL_RESOURCES[gap.skill]">
                <span class="resource-label">📚 学习资源：</span>
                <a v-for="res in SKILL_RESOURCES[gap.skill].resources.slice(0, 2)" 
                   :key="res.url" 
                   :href="res.url" 
                   target="_blank" 
                   class="resource-link">
                  {{ res.title }}
                </a>
              </div>
            </div>
          </div>
          <div class="improvement-section" v-if="topImprovementSuggestions.length > 0">
            <h4>🎯 优先改进建议</h4>
            <div class="improvement-list">
              <div class="improvement-item" v-for="(sug, idx) in topImprovementSuggestions" :key="`sug-${idx}`">
                <div class="improvement-priority" :class="sug.priority">
                  {{ sug.priority === 'high' ? '高' : sug.priority === 'medium' ? '中' : '低' }}
                </div>
                <div class="improvement-content">
                  <p class="improvement-text">{{ sug.suggestion }}</p>
                  <p class="improvement-timeline" v-if="sug.timeline">⏱️ {{ sug.timeline }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 学习资源推荐卡片 -->
        <LearningResourceCard
          v-if="learningResources.length > 0"
          :resources="learningResources"
          @start-learning="(skill) => Message.info(`即将跳转到 ${skill} 学习资源`)"
          @add-to-plan="(skill) => Message.success(`${skill} 已加入学习计划`)"
        />

        <!-- 真实招聘样本卡片 -->
        <div class="real-jobs-card" v-if="currentResult.market_demand && currentResult.market_demand.jd_count > 0">
          <div class="real-jobs-header" @click="toggleRealJobs">
            <div class="real-jobs-title">
              <span class="market-icon">📊</span>
              <span>真实市场招聘数据</span>
              <span class="jd-badge">{{ currentResult.market_demand.jd_count }} 条</span>
            </div>
            <div class="real-jobs-meta">
              <span v-if="currentResult.market_demand.avg_salary_k > 0" class="salary-tag">
                均薪 {{ currentResult.market_demand.avg_salary_k.toFixed(1) }}k/月
              </span>
              <span class="toggle-icon">{{ showRealJobs ? '▲' : '▼' }}</span>
            </div>
          </div>
          <div class="real-jobs-body" v-if="showRealJobs">
            <div class="top-companies" v-if="currentResult.market_demand.top_companies?.length">
              <span class="meta-label">活跃招聘企业：</span>
              <span class="company-tag" v-for="(c, idx) in currentResult.market_demand.top_companies" :key="`company-${idx}`">{{ c }}</span>
            </div>
            <div class="top-regions" v-if="currentResult.job_context?.top_regions?.length">
              <span class="meta-label">主要需求城市：</span>
              <span class="region-tag" v-for="(r, idx) in currentResult.job_context.top_regions" :key="`region-${idx}`">{{ r }}</span>
            </div>
            <div class="culture-types" v-if="currentResult.job_context?.culture_types?.length">
              <span class="meta-label">团队文化标签：</span>
              <span class="culture-tag" v-for="(c, idx) in currentResult.job_context.culture_types" :key="`culture-${idx}`">{{ c }}</span>
            </div>

            <!-- 市场趋势图表 -->
            <MarketTrendChart
              v-if="marketTrendData.length > 0"
              :job-name="currentResult.job_title"
              :trend-data="marketTrendData"
            />
            
            <div v-if="realJobSamples.length > 0" class="sample-list">
              <div class="sample-item" v-for="(s, idx) in realJobSamples" :key="`sample-${idx}`">
                <div class="sample-top">
                  <span class="sample-company">{{ s.company_name }}</span>
                  <span class="sample-salary">{{ s.salary || '薪资面议' }}</span>
                </div>
                <div class="sample-addr" v-if="s.address">📍 {{ s.address }}</div>
                <div class="sample-size" v-if="s.size">🏢 {{ s.size }}</div>
                <div class="sample-desc" v-if="s.description">{{ s.description }}</div>
              </div>
            </div>
            <div v-else-if="realJobsLoading" class="samples-loading">加载招聘样本中...</div>
          </div>
        </div>

        <!-- B-5: 实时岗位市场概况 -->
        <div class="live-stats-card" v-if="liveJobStats">
          <div class="live-stats-header">
            <h3>实时市场行情</h3>
            <span class="live-stats-tag">Live</span>
          </div>
          <div class="live-stats-row">
            <div class="live-stat-item">
              <span class="live-stat-value">{{ liveJobStats.jd_count }}</span>
              <span class="live-stat-label">在线 JD</span>
            </div>
            <div class="live-stat-item">
              <span class="live-stat-value">{{ liveJobStats.avg_salary_k?.toFixed(1) }}K</span>
              <span class="live-stat-label">月均薪</span>
            </div>
            <div class="live-stat-item">
              <span class="live-stat-value">{{ liveJobStats.last_fetched ? liveJobStats.last_fetched.slice(0, 10) : '-' }}</span>
              <span class="live-stat-label">更新时间</span>
            </div>
          </div>
        </div>

        <!-- B-6: 薪资趋势对比 -->
        <div class="salary-comparison-card" v-if="salaryComparison && !salaryComparison.insufficient_data && salaryComparison.historical_avg_k > 0">
          <div class="salary-cmp-header">
            <h3>薪资趋势对比</h3>
            <span
              class="salary-change-badge"
              :class="salaryComparison.change_pct >= 0 ? 'badge-up' : 'badge-down'"
            >
              {{ salaryComparison.change_pct >= 0 ? '▲' : '▼' }}
              {{ Math.abs(salaryComparison.change_pct) }}%
            </span>
          </div>
          <div class="salary-cmp-row">
            <div class="salary-cmp-item">
              <span class="salary-cmp-value">{{ salaryComparison.live_avg_k.toFixed(1) }}K</span>
              <span class="salary-cmp-label">实时均薪（近7天，{{ salaryComparison.live_count }} 条）</span>
            </div>
            <div class="salary-cmp-divider">vs</div>
            <div class="salary-cmp-item">
              <span class="salary-cmp-value text-muted">{{ salaryComparison.historical_avg_k.toFixed(1) }}K</span>
              <span class="salary-cmp-label">历史均薪（{{ salaryComparison.historical_count }} 条）</span>
            </div>
          </div>
        </div>

        <div class="summary-card" v-if="currentResult.summary">
          <h3>AI分析总结</h3>
          <p>{{ currentResult.summary }}</p>
        </div>

        <!-- 用户满意度反馈 -->
        <FeedbackWidget
          v-if="currentResult?.job_id"
          target-type="match"
          :target-id="currentResult.job_id"
        />

        <!-- 数据来源透明面板 -->
        <div class="data-source-panel">
          <div class="panel-toggle" @click="showDataSource = !showDataSource">
            <span>ℹ️ 数据说明</span>
            <span class="toggle-arrow">{{ showDataSource ? '▲' : '▼' }}</span>
          </div>
          <div class="panel-body" v-if="showDataSource">
            <div class="source-row">
              <span class="source-tag source-rule">规则计算</span>
              <span class="source-desc">维度一（基础要求）、维度二（职业技能）— 基于学历/技能关键词匹配，结果完全可复现</span>
            </div>
            <div class="source-row">
              <span class="source-tag source-ai">AI辅助</span>
              <span class="source-desc">维度三（职业素养）、维度四（发展潜力）— 由大语言模型综合简历证据评分</span>
            </div>
            <div class="source-row">
              <span class="source-tag source-market">真实数据</span>
              <span class="source-desc">
                维度五（市场需求）— 基于 {{ currentResult?.market_demand?.jd_count || 0 }} 条同类招聘JD统计，
                均薪 {{ currentResult?.market_demand?.avg_salary_k ? currentResult.market_demand.avg_salary_k.toFixed(1) + 'k/月' : '暂无数据' }}
              </span>
            </div>
            <div class="source-note">数据集收集于 2026 年 2 月，岗位技能图谱含 {{ allJobs.length || 23 }} 个岗位节点</div>
            <div class="source-note weight-note" v-if="currentResult?.weight_used">
              权重方案：专业技能 {{ Math.round((currentResult.weight_used.skills ?? currentResult.weight_used.professional_skills ?? 0.35) * 100) }}%
              / 基础要求 {{ Math.round((currentResult.weight_used.basic ?? currentResult.weight_used.basic_requirements ?? 0.20) * 100) }}%
              / 职业素养 {{ Math.round((currentResult.weight_used.qualities ?? currentResult.weight_used.professional_qualities ?? 0.25) * 100) }}%
              / 发展潜力 {{ Math.round((currentResult.weight_used.potential ?? currentResult.weight_used.development_potential ?? 0.20) * 100) }}%
            </div>
          </div>
        </div>

        <div class="transfer-paths-card" v-if="currentResult?.transfer_paths && currentResult.transfer_paths.length > 0">
          <div class="transfer-header">
            <h3>🔄 换岗建议</h3>
            <span class="transfer-hint">基于技能重叠度推荐的可转岗方向</span>
          </div>
          <div class="transfer-list">
            <div 
              class="transfer-item" 
              v-for="(path, idx) in currentResult.transfer_paths" 
              :key="`transfer-${idx}`"
              @click="selectJob(path.target)"
            >
              <div class="transfer-main">
                <span class="transfer-target">{{ path.target }}</span>
                <span class="transfer-level" :class="'level-' + path.match_level">
                  {{ path.match_level === '高' ? '高匹配' : path.match_level === '中' ? '中匹配' : '低匹配' }}
                </span>
              </div>
              <div class="transfer-meta">
                <span class="transfer-overlap">技能重叠 {{ ((path.overlap_pct || 0) * 100).toFixed(0) }}%</span>
              </div>
              <div class="transfer-detail" v-if="path.advantage || path.need_learn">
                <p class="transfer-advantage" v-if="path.advantage">
                  <span class="label">优势：</span>{{ path.advantage }}
                </p>
                <p class="transfer-need" v-if="path.need_learn">
                  <span class="label">需学习：</span>{{ path.need_learn }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- D-2: 可解释得分溯源树 -->
        <div class="explanation-tree-card" v-if="currentResult?.explanation_tree?.length">
          <div class="explanation-header" @click="showExplanation = !showExplanation" style="cursor:pointer">
            <h3>得分溯源分析</h3>
            <span class="expand-toggle">{{ showExplanation ? '收起' : '展开' }}</span>
          </div>
          <div v-if="showExplanation" class="explanation-body">
            <div class="explanation-dim" v-for="dim in currentResult.explanation_tree" :key="dim.dim">
              <div class="exp-dim-header">
                <span class="exp-dim-label">{{ dim.label }}</span>
                <span class="exp-dim-score">{{ dim.score != null ? dim.score : '--' }}分</span>
                <span class="exp-dim-weight">权重 {{ dim.weight != null ? (dim.weight * 100).toFixed(0) : '--' }}%</span>
                <span class="exp-dim-contrib">贡献 {{ dim.contribution }}分</span>
              </div>
              <ul class="exp-factors">
                <li v-for="f in dim.factors" :key="f.name">
                  <span class="exp-factor-name">{{ f.name }}：</span>{{ f.value }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <button class="primary-btn report-btn" @click="goToReport">
            <span>📄</span> 生成职业报告
          </button>
          <button class="secondary-btn" @click="goToChat">
            <span>💬</span> 咨询AI
          </button>
        </div>
      </div>

      <div class="history-section" v-if="matchStore.results.length > 0 && !matchStore.loading">
        <div class="history-header">
          <h3>历史匹配记录</h3>
          <div class="history-actions">
            <button 
              v-if="matchStore.results.length >= 2" 
              class="compare-toggle-btn"
              @click="toggleCompareMode"
            >
              {{ compareMode ? '退出比较' : '📊 多岗位比较' }}
            </button>
            <button 
              class="clear-all-btn"
              @click="clearAllHistory"
              title="清空所有历史"
              aria-label="清空所有匹配历史"
            >
              🗑️ 清空
            </button>
          </div>
        </div>
        
        <div v-if="!compareMode" class="history-list">
          <div 
            class="history-item" 
            v-for="result in matchStore.sortedResults" 
            :key="result.job_title"
            :class="{ active: currentResult?.job_title === result.job_title }"
          >
            <div class="history-main" @click="selectHistory(result.job_title)">
              <span class="history-job">{{ result.job_title }}</span>
              <span class="history-score">{{ result.overall_score?.toFixed(0) }}分</span>
            </div>
            <div class="history-item-actions">
              <button 
                class="refresh-btn" 
                @click.stop="selectHistory(result.job_title, true)"
                title="刷新数据"
                aria-label="刷新匹配数据"
              >🔄</button>
              <button 
                class="delete-btn" 
                @click.stop="deleteHistoryItem(result.job_title)"
                title="删除此记录"
                aria-label="删除匹配记录"
              >🗑️</button>
            </div>
          </div>
        </div>
        
        <div v-else class="compare-mode">
          <div class="compare-select">
            <div class="compare-header-row">
              <p class="compare-hint">选择2-4个岗位进行比较分析</p>
              <div class="compare-actions" v-if="compareJobs.length >= 2">
                <button class="export-btn" @click="exportCompareImage" :disabled="exporting">
                  {{ exporting ? '导出中...' : '📷 导出图片' }}
                </button>
                <button class="export-btn pdf" @click="exportComparePDF" :disabled="exporting">
                  {{ exporting ? '导出中...' : '📄 导出PDF' }}
                </button>
              </div>
            </div>
            <div class="compare-checkboxes">
              <label 
                v-for="result in matchStore.sortedResults" 
                :key="result.job_title"
                class="compare-checkbox"
                :class="{ 
                  selected: compareJobs.includes(result.job_title),
                  disabled: !compareJobs.includes(result.job_title) && compareJobs.length >= 4
                }"
              >
                <input 
                  type="checkbox" 
                  :value="result.job_title"
                  v-model="compareJobs"
                  :disabled="!compareJobs.includes(result.job_title) && compareJobs.length >= 4"
                />
                <span class="checkbox-custom"></span>
                <div class="checkbox-info">
                  <span class="checkbox-label">{{ result.job_title }}</span>
                  <div class="checkbox-meta">
                    <span class="checkbox-score" :class="getScoreClass(result.overall_score)">
                      {{ result.overall_score?.toFixed(0) }}分
                    </span>
                    <span class="checkbox-skills">{{ result.matched_skills?.length || 0 }}项匹配</span>
                  </div>
                </div>
              </label>
            </div>
          </div>
          
          <div v-if="compareJobs.length >= 2" ref="compareContentRef" class="compare-content">
            <div class="compare-chart-section">
              <h4>📊 多维度对比雷达图</h4>
              <div ref="compareRadarRef" class="compare-radar"></div>
            </div>
            
            <div class="compare-table-section">
              <h4>📋 详细维度对比</h4>
              <div class="compare-table-wrapper">
                <table class="compare-table">
                  <thead>
                    <tr>
                      <th>维度</th>
                      <th v-for="(job, idx) in compareJobs" :key="`header-${idx}`" class="job-header">
                        <span class="job-name">{{ job }}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="total-row">
                      <td class="dim-name">综合匹配度</td>
                      <td v-for="(job, idx) in compareJobs" :key="`total-${idx}`" class="score-cell">
                        <span :class="getScoreClass(getJobScore(job))" class="score-badge">
                          {{ getJobScore(job).toFixed(0) }}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td class="dim-name">基础要求</td>
                      <td v-for="(job, idx) in compareJobs" :key="`basic-${idx}`">
                        <span :class="getScoreClass(getJobDimension(job, 'basic_requirements'))">
                          {{ getJobDimension(job, 'basic_requirements') }}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td class="dim-name">职业技能</td>
                      <td v-for="(job, idx) in compareJobs" :key="`skill-${idx}`">
                        <span :class="getScoreClass(getJobDimension(job, 'professional_skills'))">
                          {{ getJobDimension(job, 'professional_skills') }}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td class="dim-name">职业素养</td>
                      <td v-for="(job, idx) in compareJobs" :key="`quality-${idx}`">
                        <span :class="getScoreClass(getJobDimension(job, 'professional_qualities'))">
                          {{ getJobDimension(job, 'professional_qualities') }}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td class="dim-name">发展潜力</td>
                      <td v-for="(job, idx) in compareJobs" :key="`potential-${idx}`">
                        <span :class="getScoreClass(getJobDimension(job, 'development_potential'))">
                          {{ getJobDimension(job, 'development_potential') }}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td class="dim-name">市场需求</td>
                      <td v-for="(job, idx) in compareJobs" :key="`market-${idx}`">
                        <span :class="getScoreClass(getJobMarketScore(job))">
                          {{ getJobMarketScore(job) }}
                        </span>
                      </td>
                    </tr>
                    <tr class="skill-row">
                      <td class="dim-name">匹配技能数</td>
                      <td v-for="(job, idx) in compareJobs" :key="`match-${idx}`" class="match-count">
                        <span class="skill-count good">{{ getJobMatchedSkills(job).length }}项</span>
                      </td>
                    </tr>
                    <tr class="skill-row">
                      <td class="dim-name">差距技能数</td>
                      <td v-for="(job, idx) in compareJobs" :key="`gap-${idx}`" class="gap-count">
                        <span class="skill-count warn">{{ getJobGapSkills(job).length }}项</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="gap-compare-section">
              <h4>🔍 技能差距对比分析</h4>
              <div class="gap-compare-table-wrapper">
                <table class="gap-compare-table">
                  <thead>
                    <tr>
                      <th>差距技能</th>
                      <th v-for="(job, idx) in compareJobs" :key="`gap-header-${idx}`">{{ job }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(skill, idx) in allGapSkills" :key="`gap-skill-${idx}`">
                      <td class="skill-name">{{ skill }}</td>
                      <td v-for="(job, jIdx) in compareJobs" :key="`gap-status-${idx}-${jIdx}`" class="gap-status">
                        <span v-if="hasGapSkill(job, skill)" class="gap-badge missing">
                          ✗ 缺失
                        </span>
                        <span v-else class="gap-badge matched">
                          ✓ 具备
                        </span>
                      </td>
                    </tr>
                    <tr v-if="allGapSkills.length === 0">
                      <td colspan="5" class="no-gap">暂无技能差距数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            
            <div class="compare-suggestion" v-if="bestCompareJob">
              <div class="suggestion-icon">💡</div>
              <div class="suggestion-content">
                <strong>推荐建议：</strong>
                基于综合分析，<span class="highlight-job">{{ bestCompareJob }}</span>与您的匹配度最高，
                建议优先考虑该岗位方向。
                <div class="suggestion-detail" v-if="bestCompareJobResult">
                  该岗位匹配技能 {{ bestCompareJobResult.matched_skills?.length || 0 }} 项，
                  差距技能 {{ bestCompareJobResult.gap_skills?.length || 0 }} 项。
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="compare-empty">
            <div class="empty-icon">📊</div>
            <p>请至少选择2个岗位进行比较</p>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📄</div>
      <h3>请先上传简历</h3>
      <p>上传简历后，AI将分析您与各岗位的匹配度</p>
      <button class="primary-btn" @click="$router.push('/upload')">
        去上传简历
      </button>
    </div>

    <Teleport to="body">
      <div class="modal-overlay" v-if="showSkillDetailModal" @click.self="showSkillDetailModal = false">
        <div class="modal-content skill-detail-modal">
          <div class="modal-header">
            <h3>📊 技能匹配详情分析</h3>
            <button class="modal-close" @click="showSkillDetailModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="skill-detail-tabs">
              <button 
                :class="['tab-btn', { active: activeSkillTab === 'all' }]" 
                @click="activeSkillTab = 'all'"
              >
                全部 ({{ currentResult?.skill_match_details?.length || 0 }})
              </button>
              <button 
                :class="['tab-btn', { active: activeSkillTab === 'matched' }]" 
                @click="activeSkillTab = 'matched'"
              >
                匹配 ({{ matchedSkillCount }})
              </button>
              <button 
                :class="['tab-btn', { active: activeSkillTab === 'partial' }]" 
                @click="activeSkillTab = 'partial'"
              >
                部分 ({{ partialSkillCount }})
              </button>
              <button 
                :class="['tab-btn', { active: activeSkillTab === 'missing' }]" 
                @click="activeSkillTab = 'missing'"
              >
                缺失 ({{ missingSkillCount }})
              </button>
            </div>
            <div class="skill-detail-list">
              <div 
                class="skill-detail-item" 
                v-for="(skill, idx) in filteredSkillDetails" 
                :key="`skill-detail-${idx}`"
              >
                <div class="skill-detail-header">
                  <span class="skill-name">{{ skill.skillName }}</span>
                  <div class="skill-badges">
                    <span :class="['status-badge', skill.matchStatus]">
                      {{ getMatchStatusText(skill.matchStatus) }}
                    </span>
                    <span :class="['importance-badge', skill.importance]">
                      {{ skill.importance === 'must_have' ? '必须' : '加分' }}
                    </span>
                  </div>
                </div>
                <div class="skill-detail-body" v-if="skill.jobRequirement || skill.studentEvidence">
                  <div class="detail-row" v-if="skill.jobRequirement">
                    <span class="detail-label">岗位要求：</span>
                    <span class="detail-value">{{ skill.jobRequirement }}</span>
                  </div>
                  <div class="detail-row" v-if="skill.studentEvidence">
                    <span class="detail-label">您的证据：</span>
                    <span class="detail-value evidence">{{ skill.studentEvidence }}</span>
                  </div>
                  <div class="detail-row" v-if="skill.similarityScore">
                    <span class="detail-label">相似度：</span>
                    <div class="similarity-bar">
                      <div class="similarity-fill" :style="{ width: (skill.similarityScore * 100) + '%' }"></div>
                      <span class="similarity-value">{{ (skill.similarityScore * 100).toFixed(0) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="empty-detail" v-if="filteredSkillDetails.length === 0">
                暂无{{ activeSkillTab === 'all' ? '' : getMatchStatusText(activeSkillTab as any) }}技能数据
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-overlay" v-if="showGapDetailModal" @click.self="showGapDetailModal = false">
        <div class="modal-content gap-detail-modal">
          <div class="modal-header">
            <h3>📋 差距分析与改进建议</h3>
            <button class="modal-close" @click="showGapDetailModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="gap-analysis-list">
              <div class="gap-analysis-item" v-for="(gap, idx) in currentResult?.gap_analysis" :key="`gap-analysis-${idx}`">
                <div class="gap-analysis-header">
                  <span class="gap-severity-tag" :class="gap.severity">
                    {{ gap.severity === 'critical' ? '🔴 关键差距' : gap.severity === 'moderate' ? '🟡 中等差距' : '🟢 轻微差距' }}
                  </span>
                </div>
                <div class="gap-analysis-body">
                  <div class="gap-desc-section">
                    <h4>差距描述</h4>
                    <p>{{ gap.gapDescription }}</p>
                  </div>
                  <div class="gap-impact-section">
                    <h4>影响分析</h4>
                    <p>{{ gap.impact }}</p>
                  </div>
                  <div class="gap-suggestions-section" v-if="gap.improvementSuggestions?.length">
                    <h4>改进建议</h4>
                    <div class="suggestion-list">
                      <div class="suggestion-item" v-for="(sug, sIdx) in gap.improvementSuggestions" :key="`sug-${sIdx}`">
                        <div class="suggestion-header">
                          <span class="suggestion-priority" :class="sug.priority">
                            {{ sug.priority === 'high' ? '高优先级' : sug.priority === 'medium' ? '中优先级' : '低优先级' }}
                          </span>
                          <span class="suggestion-timeline" v-if="sug.timeline">{{ sug.timeline }}</span>
                        </div>
                        <p class="suggestion-text">{{ sug.suggestion }}</p>
                        <div class="suggestion-resources" v-if="sug.resources?.length">
                          <span class="resource-label">推荐资源：</span>
                          <span class="resource-tag" v-for="(res, rIdx) in sug.resources" :key="`res-${rIdx}`">{{ res }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-overlay" v-if="showDimensionDetailModal" @click.self="showDimensionDetailModal = false">
        <div class="modal-content dimension-detail-modal">
          <div class="modal-header">
            <h3>📈 维度得分详情</h3>
            <button class="modal-close" @click="showDimensionDetailModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="dimension-detail-list">
              <div class="dimension-detail-item" v-for="dim in dimensionList" :key="dim.key">
                <div class="dim-detail-header">
                  <span class="dim-detail-name">{{ dim.name }}</span>
                  <ScoreDisplay :score="dim.score" show-unit size="small" />
                </div>
                <div class="dim-detail-progress">
                  <ProgressBar :percent="dim.score" size="small" />
                </div>
                <div class="dim-detail-text" v-if="dim.detail">
                  <span class="detail-label">分析说明：</span>
                  <p>{{ dim.detail }}</p>
                </div>
                <div class="dim-detail-evidence" v-if="dim.evidence">
                  <span class="detail-label">评分依据：</span>
                  <div class="evidence-list">
                    <div
                      v-for="(item, idx) in parseEvidence(dim.evidence)"
                      :key="`evidence-${idx}`"
                      :class="['evidence-item', 'evidence-' + item.type]"
                    >
                      <span class="evidence-bullet">{{ item.type === 'match' ? '✓' : item.type === 'gap' ? '✗' : '·' }}</span>
                      <span>{{ item.text }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
    
    <LoginModal
      v-if="showLoginModal"
      @close="showLoginModal = false"
      @success="showLoginModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, onActivated, defineAsyncComponent } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { useMatchStore } from '../stores/useMatchStore'
import { useCrewStore } from '../stores/useCrewStore'
import { usePortraitStore } from '../stores/usePortraitStore'
import { matchApi } from '../api/match'
import { jobApi } from '../api/job'
import { crewApi } from '../api/crew'
import { SKILL_RESOURCES } from '../constants'
import StepProgress from '../components/StepProgress.vue'
import FeedbackWidget from '../components/FeedbackWidget.vue'
import ScoreDisplay from '../components/ScoreDisplay.vue'
import ProgressBar from '../components/ProgressBar.vue'
import EmptyState from '../components/EmptyState.vue'
import AgentProcessPanel from '../components/AgentProcessPanel.vue'
import AsyncTaskProgress from '../components/AsyncTaskProgress.vue'
import GuestLimitHint from '../components/GuestLimitHint.vue'
import LoginModal from '../components/LoginModal.vue'
import * as echarts from 'echarts'

const MarketTrendChart = defineAsyncComponent(() => import('../components/MarketTrendChart.vue'))
const LearningResourceCard = defineAsyncComponent(() => import('../components/LearningResourceCard.vue'))

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const matchStore = useMatchStore()
const crewStore = useCrewStore()
const portraitStore = usePortraitStore()

// 权重方案
const selectedWeightPreset = ref('default')
const weightPresets = [
  { key: 'default',    label: '通用方案' },
  { key: 'tech',       label: '技术岗' },
  { key: 'management', label: '管理岗' },
  { key: 'research',   label: '研究岗' },
  { key: 'operation',  label: '运营岗' },
]

// ECharts 雷达图
const radarRef = ref<HTMLElement | null>(null)
let radarChart: echarts.ECharts | null = null
let radarObserver: ResizeObserver | null = null

function renderRadar(dims: any) {
  if (!radarRef.value) return
  if (!radarChart) {
    radarChart = echarts.init(radarRef.value)
    radarObserver = new ResizeObserver(() => radarChart?.resize())
    radarObserver.observe(radarRef.value)
  }
  const hasMarket = dims.market_demand && dims.market_demand.score > 0
  const indicator = [
    { name: '基础要求', max: 100 },
    { name: '职业技能', max: 100 },
    { name: '职业素养', max: 100 },
    { name: '发展潜力', max: 100 },
    ...(hasMarket ? [{ name: '市场需求', max: 100 }] : []),
  ]
  const values = [
    Math.round(dims.basic_requirements?.score || 0),
    Math.round(dims.professional_skills?.score || 0),
    Math.round(dims.professional_qualities?.score || 0),
    Math.round(dims.development_potential?.score || 0),
    ...(hasMarket ? [Math.round(dims.market_demand.score || 0)] : []),
  ]
  radarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 5,
      axisName: { color: '#555', fontSize: 12, fontWeight: 500 },
      splitArea: {
        areaStyle: {
          color: ['rgba(102,126,234,0.04)', 'rgba(102,126,234,0.08)',
                  'rgba(102,126,234,0.12)', 'rgba(102,126,234,0.16)'],
        },
      },
      axisLine: { lineStyle: { color: '#dde0f0' } },
      splitLine: { lineStyle: { color: '#dde0f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '匹配度',
        areaStyle: { color: 'rgba(102,126,234,0.28)', shadowBlur: 4 },
        lineStyle: { color: '#667eea', width: 2.5 },
        itemStyle: { color: '#764ba2' },
        symbol: 'circle',
        symbolSize: 6,
      }],
    }],
  }, true)
}

// 真实招聘样本
const showRealJobs = ref(false)
const realJobSamples = ref<any[]>([])
const realJobsLoading = ref(false)

// B-5: 实时岗位市场统计
const liveJobStats = ref<any>(null)

// B-6: 薪资趋势对比
const salaryComparison = ref<any>(null)

const showConfidenceDetail = ref(false)
const showSkillDetailModal = ref(false)
const showGapDetailModal = ref(false)
const showDimensionDetailModal = ref(false)
const showLoginModal = ref(false)
const activeSkillTab = ref<'all' | 'matched' | 'partial' | 'missing' | 'semantic_matched'>('all')

const matchedSkillCount = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  return details.filter(s => s.matchStatus === 'matched').length
})

const partialSkillCount = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  return details.filter(s => s.matchStatus === 'partial').length
})

const semanticMatchedCount = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  return details.filter(s => s.matchStatus === 'semantic_matched').length
})

const missingSkillCount = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  return details.filter(s => s.matchStatus === 'missing').length
})

const skillHitRate = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  if (!details.length) return null
  const hit = details.filter(s => s.matchStatus === 'matched' || s.matchStatus === 'partial' || s.matchStatus === 'semantic_matched').length
  return Math.round(hit / details.length * 100)
})

const filteredSkillDetails = computed(() => {
  const details = currentResult.value?.skill_match_details || []
  if (activeSkillTab.value === 'all') return details
  return details.filter(s => s.matchStatus === activeSkillTab.value)
})

const topImprovementSuggestions = computed(() => {
  const gapAnalysis = currentResult.value?.gap_analysis || []
  const allSuggestions: any[] = []
  gapAnalysis.forEach(gap => {
    if (gap.improvementSuggestions) {
      gap.improvementSuggestions.forEach(sug => {
        allSuggestions.push(sug)
      })
    }
  })
  return allSuggestions
    .sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 }
      return priorityOrder[a.priority as keyof typeof priorityOrder] - priorityOrder[b.priority as keyof typeof priorityOrder]
    })
    .slice(0, 3)
})

function getMatchStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    matched: '完全匹配',
    partial: '部分匹配',
    missing: '缺失',
    semantic_matched: '语义匹配'
  }
  return statusMap[status] || status
}

async function toggleRealJobs() {
  showRealJobs.value = !showRealJobs.value
  if (showRealJobs.value && realJobSamples.value.length === 0 && currentResult.value) {
    realJobsLoading.value = true
    try {
      const data = await jobApi.getRealJobs(currentResult.value.job_title, 5)
      realJobSamples.value = data.samples || []
    } catch {
      realJobSamples.value = []
    } finally {
      realJobsLoading.value = false
    }
  }
}

async function fetchLiveJobStats(jobTitle: string) {
  try {
    const data = await jobApi.getLiveJobStats([jobTitle])
    const found = (data.stats || []).find((s: any) => s.job_name === jobTitle)
    liveJobStats.value = found || null
  } catch {
    liveJobStats.value = null
  }
}

async function fetchSalaryComparison(jobTitle: string) {
  try {
    salaryComparison.value = await jobApi.getSalaryComparison(jobTitle)
  } catch {
    salaryComparison.value = null
  }
}

const showExplanation = ref(false)
const showDataSource = ref(false)
const showCrewAIPanel = ref(false)
const showDeepAnalysis = ref(false)
const crewAIEnabled = ref(false)
const learningResources = ref<{skill: string, priority: 'high' | 'medium' | 'low', resources?: any}[]>([])
const marketTrendData = ref<any[]>([])
const searchJob = ref('')
const recommendLoading = ref(false)
const recommendations = ref<{job_title: string, score: number, matched_skills: string[], summary: string}[]>([])
const allJobs = ref<string[]>([])
const showJobSuggestions = ref(false)
const batchMatching = ref(false)
const batchProgress = ref(0)
function hideJobSuggestions() { setTimeout(() => { showJobSuggestions.value = false }, 200) }

const jobCategories = [
  { label: '全部', value: '' },
  { label: '技术', value: 'tech' },
  { label: '产品', value: 'product' },
  { label: '运营', value: 'operation' },
  { label: '销售', value: 'sales' },
  { label: '设计', value: 'design' },
  { label: '市场', value: 'marketing' },
  { label: '人事', value: 'hr' },
  { label: '财务', value: 'finance' },
]

const skillTypes = [
  { label: '全部', value: '' },
  { label: '后端开发', value: 'backend' },
  { label: '前端开发', value: 'frontend' },
  { label: '移动开发', value: 'mobile' },
  { label: '数据分析', value: 'data' },
  { label: '人工智能', value: 'ai' },
  { label: '测试', value: 'test' },
  { label: '运维', value: 'devops' },
]

const selectedCategory = ref('')
const selectedSkillType = ref('')

const jobCategoryMap: Record<string, string[]> = {
  tech: ['后端开发工程师', '前端开发工程师', 'Java开发工程师', 'Python开发工程师', '全栈工程师', '移动开发工程师', '测试工程师', '运维工程师', '大数据工程师', '算法工程师', '架构师', '技术经理'],
  product: ['产品经理', '产品助理', '产品总监', '需求分析师'],
  operation: ['运营专员', '运营经理', '内容运营', '用户运营', '活动运营'],
  sales: ['销售代表', '销售经理', '客户经理', '商务拓展'],
  design: ['UI设计师', 'UX设计师', '视觉设计师', '交互设计师'],
  marketing: ['市场专员', '市场经理', '品牌经理', '推广专员'],
  hr: ['HR专员', 'HRBP', '招聘专员', '培训专员'],
  finance: ['财务专员', '会计', '财务经理', '审计'],
}

const skillTypeMap: Record<string, string[]> = {
  backend: ['后端开发工程师', 'Java开发工程师', 'Python开发工程师', 'Go开发工程师', 'Node.js开发工程师'],
  frontend: ['前端开发工程师', 'Web前端开发', 'Vue开发工程师', 'React开发工程师'],
  mobile: ['移动开发工程师', 'iOS开发工程师', 'Android开发工程师', 'Flutter开发工程师'],
  data: ['大数据工程师', '数据分析师', '数据挖掘工程师', 'BI工程师'],
  ai: ['算法工程师', '机器学习工程师', '深度学习工程师', 'NLP工程师', '计算机视觉工程师'],
  test: ['测试工程师', '自动化测试工程师', '测试开发工程师', 'QA工程师'],
  devops: ['运维工程师', 'DevOps工程师', 'SRE工程师', '云计算工程师'],
}

const searchHistory = ref<string[]>([])
const SEARCH_HISTORY_KEY = 'job_search_history'
const MAX_HISTORY = 10

function loadSearchHistory() {
  try {
    const saved = localStorage.getItem(SEARCH_HISTORY_KEY)
    if (saved) {
      searchHistory.value = JSON.parse(saved)
    }
  } catch {
    searchHistory.value = []
  }
}

function saveSearchHistory(job: string) {
  const history = searchHistory.value.filter(item => item !== job)
  history.unshift(job)
  searchHistory.value = history.slice(0, MAX_HISTORY)
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(searchHistory.value))
}

function clearSearchHistory() {
  searchHistory.value = []
  localStorage.removeItem(SEARCH_HISTORY_KEY)
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const debounceSearch = ref('')

function onSearchInput() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  debounceTimer = setTimeout(() => {
    debounceSearch.value = searchJob.value
  }, 300)
}

function onSearchFocus() {
  showJobSuggestions.value = true
  loadSearchHistory()
}

function clearSearch() {
  searchJob.value = ''
  debounceSearch.value = ''
}

function selectCategory(cat: string) {
  selectedCategory.value = cat
}

function selectSkillType(skill: string) {
  selectedSkillType.value = skill
}

function getJobCategory(job: string): string {
  for (const [cat, jobs] of Object.entries(jobCategoryMap)) {
    if (jobs.some(j => job.includes(j) || j.includes(job))) {
      const category = jobCategories.find(c => c.value === cat)
      return category?.label || ''
    }
  }
  return ''
}

const compareMode = ref(false)
const compareJobs = ref<string[]>([])
const compareRadarRef = ref<HTMLElement | null>(null)
const compareContentRef = ref<HTMLElement | null>(null)
let compareRadarChart: echarts.ECharts | null = null
const exporting = ref(false)

function toggleCompareMode() {
  compareMode.value = !compareMode.value
  if (!compareMode.value) {
    compareJobs.value = []
  }
}

function getJobMarketScore(jobTitle: string): number {
  const result = matchStore.getResultByJob(jobTitle)
  return Math.round(result?.market_demand?.score || 0)
}

const allGapSkills = computed(() => {
  const skills = new Set<string>()
  for (const job of compareJobs.value) {
    const gaps = getJobGapSkills(job)
    for (const gap of gaps) {
      if (typeof gap === 'string') {
        skills.add(gap)
      } else if (gap.skill) {
        skills.add(gap.skill)
      }
    }
  }
  return Array.from(skills)
})

function hasGapSkill(jobTitle: string, skill: string): boolean {
  const gaps = getJobGapSkills(jobTitle)
  return gaps.some((g: any) => (typeof g === 'string' ? g === skill : g.skill === skill))
}

const bestCompareJobResult = computed(() => {
  if (!bestCompareJob.value) return null
  return matchStore.getResultByJob(bestCompareJob.value)
})

async function exportCompareImage() {
  if (!compareContentRef.value || exporting.value) return
  exporting.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(compareContentRef.value, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
    })
    const link = document.createElement('a')
    link.download = `岗位对比_${new Date().toLocaleDateString()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    Message.success('图片导出成功')
  } catch (e) {
    Message.error('导出图片失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

async function exportComparePDF() {
  if (!compareContentRef.value || exporting.value) return
  exporting.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const jspdf = (await import('jspdf')).default
    const canvas = await html2canvas(compareContentRef.value, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jspdf('p', 'mm', 'a4')
    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)
    pdf.save(`岗位对比报告_${new Date().toLocaleDateString()}.pdf`)
    Message.success('PDF导出成功')
  } catch (e) {
    Message.error('导出PDF失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

function getJobScore(jobTitle: string): number {
  const result = matchStore.getResultByJob(jobTitle)
  return result?.overall_score || 0
}

function getJobDimension(jobTitle: string, dimKey: string): number {
  const result = matchStore.getResultByJob(jobTitle)
  const dimensions = result?.dimensions as Record<string, { score?: number }> | undefined
  return Math.round(dimensions?.[dimKey]?.score || 0)
}

function getJobMatchedSkills(jobTitle: string): string[] {
  const result = matchStore.getResultByJob(jobTitle)
  return result?.matched_skills || []
}

function getJobGapSkills(jobTitle: string): any[] {
  const result = matchStore.getResultByJob(jobTitle)
  return result?.gap_skills || []
}

function getScoreClass(score: number): string {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-mid'
  return 'score-low'
}

const bestCompareJob = computed(() => {
  if (compareJobs.value.length < 2) return null
  let best = ''
  let maxScore = 0
  for (const job of compareJobs.value) {
    const score = getJobScore(job)
    if (score > maxScore) {
      maxScore = score
      best = job
    }
  }
  return best
})

watch(compareJobs, async (jobs) => {
  if (jobs.length >= 2) {
    await nextTick()
    renderCompareRadar()
  }
}, { flush: 'post' })

watch(
  () => userStore.studentId,
  async (newId, oldId) => {
    if (newId && newId !== oldId) {
      matchStore.clearResults()
      await matchStore.loadHistory(newId)
    }
  },
  { immediate: false }
)

watch(
  () => userStore.profile?.completeness,
  async (newVal, oldVal) => {
    if (newVal !== oldVal && userStore.studentId) {
      matchStore.clearResults()
      // 画像更新后重新拉取历史记录，保证之前的匹配结果可以继续查看
      await matchStore.loadHistory(userStore.studentId).catch(() => {})
    }
  }
)

function renderCompareRadar() {
  if (!compareRadarRef.value || compareJobs.value.length < 2) return
  
  if (!compareRadarChart) {
    compareRadarChart = echarts.init(compareRadarRef.value)
  }
  
  const hasMarket = compareJobs.value.some(job => getJobMarketScore(job) > 0)
  
  const indicator = [
    { name: '基础要求', max: 100 },
    { name: '职业技能', max: 100 },
    { name: '职业素养', max: 100 },
    { name: '发展潜力', max: 100 },
    ...(hasMarket ? [{ name: '市场需求', max: 100 }] : []),
  ]
  
  const colors = ['#667eea', '#52c41a', '#fa8c16', '#1890ff']
  const series = compareJobs.value.map((job, idx) => {
    return {
      value: [
        getJobDimension(job, 'basic_requirements'),
        getJobDimension(job, 'professional_skills'),
        getJobDimension(job, 'professional_qualities'),
        getJobDimension(job, 'development_potential'),
        ...(hasMarket ? [getJobMarketScore(job)] : []),
      ],
      name: job,
      areaStyle: { color: colors[idx % colors.length] + '30' },
      lineStyle: { color: colors[idx % colors.length], width: 2.5 },
      itemStyle: { color: colors[idx % colors.length] },
      symbol: 'circle',
      symbolSize: 6,
    }
  })
  
  compareRadarChart.setOption({
    tooltip: { 
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data
        let html = `<strong>${data.name}</strong><br/>`
        const names = ['基础要求', '职业技能', '职业素养', '发展潜力']
        if (hasMarket) names.push('市场需求')
        data.value.forEach((v: number, i: number) => {
          html += `${names[i]}: ${v}分<br/>`
        })
        return html
      }
    },
    legend: {
      data: compareJobs.value,
      bottom: 0,
      itemWidth: 16,
      itemHeight: 10,
      textStyle: { fontSize: 12 },
    },
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 5,
      axisName: { 
        color: '#555', 
        fontSize: 12,
        fontWeight: 500,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(102,126,234,0.04)', 'rgba(102,126,234,0.08)',
                  'rgba(102,126,234,0.12)', 'rgba(102,126,234,0.16)'],
        },
      },
      axisLine: { lineStyle: { color: '#dde0f0' } },
      splitLine: { lineStyle: { color: '#dde0f0' } },
    },
    series: [{
      type: 'radar',
      data: series,
    }],
  }, true)
}

const filteredHotJobs = computed(() => {
  let jobs = allJobs.value.slice(0, 12)
  if (selectedCategory.value) {
    const categoryJobs = jobCategoryMap[selectedCategory.value] || []
    jobs = jobs.filter(job => categoryJobs.some(cj => job.includes(cj) || cj.includes(job)))
  }
  if (selectedSkillType.value) {
    const skillJobs = skillTypeMap[selectedSkillType.value] || []
    jobs = jobs.filter(job => skillJobs.some(sj => job.includes(sj) || sj.includes(job)))
  }
  return jobs.length > 0 ? jobs : allJobs.value.slice(0, 8)
})

const filteredJobSuggestions = computed(() => {
  let jobs = allJobs.value
  if (selectedCategory.value) {
    const categoryJobs = jobCategoryMap[selectedCategory.value] || []
    jobs = jobs.filter(job => categoryJobs.some(cj => job.includes(cj) || cj.includes(job)))
  }
  if (selectedSkillType.value) {
    const skillJobs = skillTypeMap[selectedSkillType.value] || []
    jobs = jobs.filter(job => skillJobs.some(sj => job.includes(sj) || sj.includes(job)))
  }
  if (!debounceSearch.value.trim()) return jobs.slice(0, 10)
  const q = debounceSearch.value.toLowerCase()
  return jobs.filter(j => j.toLowerCase().includes(q)).slice(0, 10)
})

const currentResult = computed(() => {
  if (!matchStore.currentJob) return null
  return matchStore.getResultByJob(matchStore.currentJob)
})

// B-5 + B-6: 岗位切换时刷新实时统计和薪资对比
watch(() => currentResult.value?.job_title, (title) => {
  if (title) {
    fetchLiveJobStats(title)
    fetchSalaryComparison(title)
  }
}, { immediate: true })

const dimensionList = computed(() => {
  const dims = currentResult.value?.dimensions || {}
  const md = currentResult.value?.market_demand
  const list: any[] = [
    { key: 'basic',    name: '基础要求', score: Math.round(dims.basic_requirements?.score || 0),      detail: dims.basic_requirements?.detail,      evidence: dims.basic_requirements?.evidence },
    {
      key: 'skill',    name: '职业技能', score: Math.round(dims.professional_skills?.score || 0),     detail: dims.professional_skills?.detail,     evidence: dims.professional_skills?.evidence,
      jd_sources: (currentResult.value?.gap_skills || [])
        .filter((g: any) => g.jd_source)
        .map((g: any) => ({ skill: g.skill, source: g.jd_source, importance: g.importance }))
        .slice(0, 3),
    },
    { key: 'quality',  name: '职业素养', score: Math.round(dims.professional_qualities?.score || 0),  detail: dims.professional_qualities?.detail,  evidence: dims.professional_qualities?.evidence },
    { key: 'potential',name: '发展潜力', score: Math.round(dims.development_potential?.score || 0),   detail: dims.development_potential?.detail,   evidence: dims.development_potential?.evidence },
  ]
  if (md) {
    list.push({
      key: 'market',
      name: '市场需求',
      score: Math.round(md.score || 0),
      detail: md.detail || '',
      evidence: md.avg_salary_k > 0
        ? `均薪约 ${md.avg_salary_k.toFixed(1)}k/月 · 真实JD ${md.jd_count} 条`
        : `真实JD ${md.jd_count} 条`,
    })
  }
  return list
})

// 雷达图：currentResult 就绪后渲染；切换岗位时重置JD样本
watch(
  currentResult,
  async (result) => {
    showRealJobs.value = false
    realJobSamples.value = []
    if (!result?.dimensions) return
    await nextTick()
    renderRadar(result.dimensions)
  },
  { flush: 'post' },
)

onUnmounted(() => {
  radarObserver?.disconnect()
  radarObserver = null
  radarChart?.dispose()
  radarChart = null
  compareRadarChart?.dispose()
  compareRadarChart = null
})

function selectJob(job: string) {
  if (matchStore.loading) return
  searchJob.value = job
  debounceSearch.value = job
  saveSearchHistory(job)
  matchStore.computeMatch(job, true)
}

async function fetchRecommendations() {
  if (!userStore.studentId || recommendLoading.value) return
  recommendLoading.value = true
  try {
    const data = await matchApi.recommend(userStore.studentId)
    recommendations.value = data.recommendations || []
    if (recommendations.value.length === 0) {
      Message.info('暂无推荐岗位，请先完善简历信息')
    } else if (!searchJob.value && recommendations.value[0]) {
      // 自动填入最高推荐岗位
      searchJob.value = recommendations.value[0].job_title
    }
  } catch {
    recommendations.value = []
    Message.error('获取推荐失败，请稍后重试')
  } finally {
    recommendLoading.value = false
  }
}

function parseEvidence(evidence: string): { type: 'match' | 'gap' | 'info'; text: string }[] {
  if (!evidence) return []
  return evidence.split(/\s*[|｜]\s*|\n/).map(part => {
    part = part.trim()
    if (!part) return null
    if (part.includes('✓') || /^匹配/.test(part) || part.includes('符合')) return { type: 'match' as const, text: part }
    if (part.includes('✗') || /^缺/.test(part)) return { type: 'gap' as const, text: part }
    return { type: 'info' as const, text: part }
  }).filter(Boolean) as { type: 'match' | 'gap' | 'info'; text: string }[]
}

async function doMatch(forceRefresh: boolean | Event = false) {
  if (forceRefresh instanceof Event) forceRefresh = false
  if (!searchJob.value.trim() || matchStore.loading) return
  saveSearchHistory(searchJob.value.trim())
  // 已有结果时默认强制刷新（搜索框点击"分析匹配"或"重新分析"按钮）
  const shouldForce = forceRefresh || !!matchStore.getResultByJob(searchJob.value.trim())
  await matchStore.computeMatch(searchJob.value.trim(), shouldForce, selectedWeightPreset.value)
}

async function batchMatch() {
  const jobsToMatch = filteredHotJobs.value
  if (batchMatching.value || jobsToMatch.length === 0) return
  
  batchMatching.value = true
  batchProgress.value = 0
  
  for (let i = 0; i < jobsToMatch.length; i++) {
    const job = jobsToMatch[i]
    try {
      await matchStore.computeMatch(job)
      batchProgress.value = i + 1
    } catch (e) {
    }
  }
  
  batchMatching.value = false
  Message.success(`批量匹配完成！共分析 ${jobsToMatch.length} 个岗位`)
}

function selectHistory(jobTitle: string, forceRefresh: boolean = false) {
  matchStore.setCurrentJob(jobTitle)
  searchJob.value = jobTitle
  showRealJobs.value = false
  realJobSamples.value = []
  
  if (forceRefresh) {
    matchStore.computeMatch(jobTitle, true)
  }
}

function deleteHistoryItem(jobTitle: string) {
  matchStore.deleteResult(jobTitle)
  if (currentResult.value?.job_title === jobTitle) {
    matchStore.setCurrentJob('')
    searchJob.value = ''
  }
  Message.success(`已删除 "${jobTitle}" 的匹配记录`)
}

function clearAllHistory() {
  Modal.confirm({
    title: '确认清空',
    content: '确定要清空所有匹配历史记录吗？此操作不可恢复。',
    okText: '确认清空',
    cancelText: '取消',
    onOk: () => {
    matchStore.clearResults()
    matchStore.setCurrentJob('')
    searchJob.value = ''
    Message.success('已清空所有匹配历史')
  }
  })
}

function goToReport() {
  if (currentResult.value?.job_title) {
    matchStore.setCurrentJob(currentResult.value.job_title)
  }
  router.push('/report')
}

function goToChat() {
  if (currentResult.value?.job_title) {
    router.push(`/chat?job=${encodeURIComponent(currentResult.value.job_title)}`)
  } else {
    router.push('/chat')
  }
}

function getMatchLevel(score: number): string {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  return 'normal'
}

function getMatchLevelText(score: number): string {
  if (score >= 80) return '高度匹配'
  if (score >= 60) return '基本匹配'
  return '需要提升'
}

async function checkCrewAIStatus() {
  try {
    const status = await crewApi.getStatus()
    crewAIEnabled.value = status.crewai_installed && status.llm_configured
  } catch {
    crewAIEnabled.value = false
  }
}

async function startDeepAnalysis() {
  if (!currentResult.value || crewStore.isProcessing) return
  
  showDeepAnalysis.value = true
  showCrewAIPanel.value = true
  
  try {
    const result = await crewStore.runWorkflow({
      resume_content: '',
      parsed_data: {
        student_id: userStore.studentId,
        skills: currentResult.value.matched_skills || [],
        gap_skills: currentResult.value.gap_skills?.map((g: any) => g.skill) || []
      },
      target_jobs: [currentResult.value.job_title]
    })
    
    if (result.success && result.results) {
      if (result.results.learning_resources) {
        learningResources.value = result.results.learning_resources
      }
      if (result.results.market_trends) {
        marketTrendData.value = result.results.market_trends
      }
      Message.success('深度分析完成！')
    }
  } catch (e: any) {
    Message.error(e.message || '深度分析失败')
  }
}

function cancelDeepAnalysis() {
  crewStore.cancelTask()
  showDeepAnalysis.value = false
}

function getAgentStatesForPanel() {
  const states: Record<string, 'idle' | 'running' | 'completed' | 'failed'> = {}
  for (const [key, state] of Object.entries(crewStore.agentStates)) {
    states[key] = state.status
  }
  return states
}

// Show match errors as toast
watch(() => matchStore.error, (err) => {
  if (err) Message.error(err)
})

onMounted(async () => {
  loadSearchHistory()
  checkCrewAIStatus()
  const [, jobs] = await Promise.all([
    userStore.studentId
      ? matchStore.loadHistory(userStore.studentId).catch(() => {
          Message.error('历史记录加载失败，请刷新重试')
        })
      : Promise.resolve(null),
    matchApi.getJobs().catch(() => {
      Message.warning('岗位列表加载失败，已使用默认热门岗位')
      return [] as string[]
    }),
  ])
  allJobs.value = (jobs as string[]) || []

  if (!matchStore.currentJob && matchStore.bestMatch) {
    matchStore.setCurrentJob(matchStore.bestMatch.job_title)
  }

  if (matchStore.currentJob) {
    searchJob.value = matchStore.currentJob
    debounceSearch.value = matchStore.currentJob
  }

  if (userStore.studentId && recommendations.value.length === 0) {
    fetchRecommendations()
  }
  
  const jobFromQuery = route.query.job as string
  if (jobFromQuery && userStore.studentId) {
    searchJob.value = jobFromQuery
    debounceSearch.value = jobFromQuery
    await selectJob(jobFromQuery)
  }
})

onActivated(async () => {
  const lastUpdate = localStorage.getItem('portrait_update_time')
  const lastLoad = localStorage.getItem('match_load_time')

  if (lastUpdate && (!lastLoad || parseInt(lastUpdate) > parseInt(lastLoad || '0'))) {
    if (userStore.studentId) {
      // 画像已更新，强制刷新画像缓存和匹配历史
      portraitStore.clearPortrait()
      await portraitStore.loadPortrait()
      matchStore.clearResults()
      await matchStore.loadHistory(userStore.studentId)
      localStorage.setItem('match_load_time', Date.now().toString())
    }
  }
})
</script>

<style scoped>
.match-page {
  min-height: 100vh;
  background: #f8fafc;
}
.empty-state-page {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 80px 24px; text-align: center;
}
.empty-state-icon { font-size: 64px; margin-bottom: 16px; }
.empty-state-page h2 { font-size: 20px; color: #1d2129; margin: 0 0 8px; }
.empty-state-page p { color: #86909c; margin: 0 0 24px; }
/* O4-b: 移动端匹配页适配 */
@media (max-width: 768px) {
  .match-container { padding: 12px; }
  .result-grid { grid-template-columns: 1fr !important; }
  .radar-wrapper { max-width: 100%; overflow-x: auto; }
  .weight-row { flex-direction: column !important; }
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

.match-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.search-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
}

.filter-row {
  margin-bottom: 12px;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  min-width: 60px;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-option {
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
  color: #666;
  border: 1px solid #e8e8e8;
}

.filter-option:hover {
  border-color: #667eea;
  color: #667eea;
}

.filter-option.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.weight-preset-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.weight-preset-section > label {
  align-self: flex-start;
}

.weight-detail {
  font-size: 12px;
  color: #667eea;
  background: #f0f4ff;
  padding: 4px 10px;
  border-radius: 6px;
  align-self: flex-start;
}

.weight-preset-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.weight-preset-btn {
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
  color: #666;
  border: 1px solid #e8e8e8;
}

.weight-preset-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.weight-preset-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  font-weight: 500;
}

.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 14px;
  font-size: 16px;
  pointer-events: none;
}

.search-input-wrapper input {
  width: 100%;
  padding: 14px 40px 14px 40px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  font-size: 15px;
  outline: none;
  transition: all 0.2s;
}

.search-input-wrapper input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.clear-btn {
  position: absolute;
  right: 12px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: #e8e8e8;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #ccc;
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 80px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 100;
  overflow: hidden;
  margin-top: 4px;
}

.dropdown-section {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.dropdown-section:last-child {
  border-bottom: none;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px 8px;
  font-size: 12px;
  color: #999;
  font-weight: 500;
}

.match-count {
  background: #f0f4ff;
  color: #667eea;
  padding: 2px 8px;
  border-radius: 10px;
}

.clear-history-btn {
  background: none;
  border: none;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.clear-history-btn:hover {
  background: #f5f5f5;
  color: #f5222d;
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px;
}

.history-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #f5f5f5;
  border-radius: 16px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.history-tag:hover {
  background: #e6f7ff;
  color: #1890ff;
}

.job-suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  transition: background 0.15s;
}

.job-suggestion-item:hover {
  background: #f0f4ff;
}

.job-name {
  flex: 1;
}

.job-category-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: #f0f4ff;
  color: #667eea;
  border-radius: 10px;
}

.no-result {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.search-btn {
  padding: 14px 28px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.search-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hot-jobs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-jobs .label {
  font-size: 13px;
  color: #999;
}

.job-tag {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f5f5f5;
  color: #666;
  border: none;
}

.job-tag:hover {
  background: #667eea;
  color: white;
}

.loading-section {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.loading-card {
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
}

.loading-card p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.score-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  text-align: center;
}

.score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.score-header h2 {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.score-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.reanalyze-btn {
  padding: 5px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1.5px solid #667eea;
  color: #667eea;
  background: transparent;
  transition: all 0.2s;
}

.reanalyze-btn:hover:not(:disabled) {
  background: #f0f4ff;
}

.reanalyze-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.deep-analysis-btn {
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.deep-analysis-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.deep-analysis-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.confidence {
  font-size: 13px;
  color: #999;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 10px;
}

.score-circle-container {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 0 auto 16px;
}

.score-svg {
  transform: rotate(-90deg);
}

.bg-circle {
  fill: none;
  stroke: #f0f0f0;
  stroke-width: 10;
}

.score-circle {
  fill: none;
  stroke: #667eea;
  stroke-width: 10;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 1s ease;
}

.score-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.score-value .number {
  font-size: 42px;
  font-weight: 700;
  color: #667eea;
}

.score-value .unit {
  font-size: 18px;
  color: #667eea;
}

.score-label {
  font-size: 16px;
  color: #666;
  margin-bottom: 12px;
}

.match-level {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.match-level.excellent {
  background: #f6ffed;
  color: #52c41a;
}

.match-level.good {
  background: #e6f7ff;
  color: #1890ff;
}

.match-level.normal {
  background: #fff7e6;
  color: #fa8c16;
}

.quick-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.quick-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid;
}

.quick-action-btn.report-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.quick-action-btn.report-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.quick-action-btn.chat-btn {
  background: white;
  color: #667eea;
  border-color: #667eea;
}

.quick-action-btn.chat-btn:hover {
  background: #f0f4ff;
}

.live-stats-card {
  background: white;
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.live-stats-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.live-stats-header h3 { margin: 0; font-size: 15px; font-weight: 600; }
.live-stats-tag {
  background: #52c41a;
  color: white;
  border-radius: 8px;
  padding: 1px 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
}
.live-stats-row {
  display: flex;
  gap: 24px;
}
.live-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.live-stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #1890ff;
}
.live-stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
}

/* B-6: 薪资趋势对比卡片 */
.salary-comparison-card {
  background: white;
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.salary-cmp-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.salary-cmp-header h3 { margin: 0; font-size: 15px; font-weight: 600; }
.salary-change-badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}
.badge-up { background: #f6ffed; color: #52c41a; }
.badge-down { background: #fff1f0; color: #ff4d4f; }
.salary-cmp-row {
  display: flex;
  align-items: center;
  gap: 20px;
}
.salary-cmp-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}
.salary-cmp-divider {
  font-size: 13px;
  color: #8c8c8c;
  flex-shrink: 0;
}
.salary-cmp-value {
  font-size: 22px;
  font-weight: 700;
  color: #1890ff;
}
.salary-cmp-value.text-muted { color: #8c8c8c; }
.salary-cmp-label {
  font-size: 11px;
  color: #8c8c8c;
  margin-top: 4px;
  text-align: center;
}

.dimensions-card, .skills-card, .gap-card, .summary-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.dimensions-card h3, .skills-card h3, .gap-card h3, .summary-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
}

.dimensions-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 24px;
  align-items: start;
}

.radar-chart-box {
  width: 240px;
  height: 240px;
}

@media (max-width: 640px) {
  .dimensions-layout {
    grid-template-columns: 1fr;
  }
  .radar-chart-box {
    width: 100%;
    height: 220px;
  }
}

.score-high { color: #52c41a !important; }
.score-mid  { color: #667eea !important; }
.score-low  { color: #fa8c16 !important; }

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dimension-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dim-header {
  display: flex;
  justify-content: space-between;
}

.dim-name {
  font-size: 14px;
  font-weight: 500;
}

.dim-score {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

.dim-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.dim-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.dim-detail {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
  line-height: 1.5;
}

.dim-evidence {
  font-size: 11px;
  color: #aaa;
  margin-top: 2px;
  font-style: italic;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag.matched {
  padding: 6px 14px;
  background: #f6ffed;
  color: #52c41a;
  border-radius: 20px;
  font-size: 13px;
}

.gap-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gap-item {
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.gap-skill {
  font-weight: 500;
  font-size: 14px;
}

.gap-importance {
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.gap-importance.must_have {
  background: #fff1f0;
  color: #f5222d;
}

.gap-importance.nice_to_have {
  background: #fff7e6;
  color: #fa8c16;
}

.gap-suggestion {
  font-size: 13px;
  color: #666;
}

.gap-resources {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e8e8e8;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.resource-label {
  font-size: 12px;
  color: #666;
}

.resource-link {
  font-size: 12px;
  color: #1890ff;
  text-decoration: none;
  padding: 2px 8px;
  background: #e6f7ff;
  border-radius: 4px;
  transition: all 0.2s;
}

.resource-link:hover {
  background: #bae7ff;
  color: #096dd9;
}

.summary-card p {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: 12px;
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

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.report-btn {
  flex: 2;
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

.history-section {
  margin-top: 24px;
  background: white;
  border-radius: 16px;
  padding: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.compare-toggle-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #667eea;
  color: #667eea;
  background: transparent;
  transition: all 0.2s;
}

.compare-toggle-btn:hover {
  background: #f0f4ff;
}

.compare-mode {
  margin-top: 16px;
}

.compare-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.compare-actions {
  display: flex;
  gap: 8px;
}

.export-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #667eea;
  color: #667eea;
  background: transparent;
  transition: all 0.2s;
}

.export-btn:hover:not(:disabled) {
  background: #f0f4ff;
}

.export-btn.pdf {
  border-color: #52c41a;
  color: #52c41a;
}

.export-btn.pdf:hover:not(:disabled) {
  background: #f6ffed;
}

.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.compare-hint {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.compare-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.compare-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  min-width: 200px;
}

.compare-checkbox:hover:not(.disabled) {
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.compare-checkbox.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, #f0f4ff 0%, #e6f0ff 100%);
  box-shadow: 0 2px 12px rgba(102, 126, 234, 0.15);
}

.compare-checkbox.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.compare-checkbox input {
  display: none;
}

.checkbox-custom {
  width: 18px;
  height: 18px;
  border: 2px solid #d9d9d9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.compare-checkbox.selected .checkbox-custom {
  background: #667eea;
  border-color: #667eea;
}

.compare-checkbox.selected .checkbox-custom::after {
  content: '✓';
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.checkbox-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.checkbox-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.checkbox-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.checkbox-score {
  font-size: 13px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

.checkbox-score.score-high { 
  color: #52c41a; 
  background: #f6ffed;
}
.checkbox-score.score-mid { 
  color: #667eea; 
  background: #f0f4ff;
}
.checkbox-score.score-low { 
  color: #fa8c16; 
  background: #fff7e6;
}

.checkbox-skills {
  font-size: 11px;
  color: #999;
}

.compare-content {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.compare-chart-section {
  margin-bottom: 24px;
}

.compare-chart-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 16px;
}

.compare-radar {
  width: 100%;
  height: 320px;
}

.compare-table-section {
  margin-top: 24px;
}

.compare-table-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 16px;
}

.compare-table-wrapper {
  overflow-x: auto;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.compare-table th,
.compare-table td {
  padding: 14px 16px;
  text-align: center;
  border-bottom: 1px solid #f0f0f0;
}

.compare-table th {
  background: linear-gradient(135deg, #f8fafc 0%, #f0f4ff 100%);
  font-weight: 600;
  color: #333;
}

.compare-table th:first-child {
  text-align: left;
  background: #f8fafc;
}

.compare-table td:first-child {
  text-align: left;
  font-weight: 500;
  color: #666;
  background: #fafafa;
}

.compare-table .total-row {
  background: #f0f7ff;
}

.compare-table .total-row td {
  font-weight: 600;
}

.score-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
}

.score-badge.score-high { 
  background: #f6ffed; 
  color: #52c41a; 
}
.score-badge.score-mid { 
  background: #f0f4ff; 
  color: #667eea; 
}
.score-badge.score-low { 
  background: #fff7e6; 
  color: #fa8c16; 
}

.compare-table .skill-row td {
  background: #fafafa;
}

.skill-count {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
}

.skill-count.good {
  background: #f6ffed;
  color: #52c41a;
}

.skill-count.warn {
  background: #fff2e8;
  color: #fa8c16;
}

.gap-compare-section {
  margin-top: 24px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8e8e8;
}

.gap-compare-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 16px;
}

.gap-compare-table-wrapper {
  overflow-x: auto;
}

.gap-compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.gap-compare-table th,
.gap-compare-table td {
  padding: 12px 14px;
  text-align: center;
  border-bottom: 1px solid #f0f0f0;
}

.gap-compare-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #333;
  font-size: 12px;
}

.gap-compare-table th:first-child,
.gap-compare-table td:first-child {
  text-align: left;
}

.skill-name {
  font-weight: 500;
  color: #333;
}

.gap-status {
  text-align: center;
}

.gap-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.gap-badge.missing {
  background: #fff1f0;
  color: #f5222d;
}

.gap-badge.matched {
  background: #f6ffed;
  color: #52c41a;
}

.no-gap {
  text-align: center;
  color: #999;
  padding: 20px;
}

.compare-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-top: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f7ff 100%);
  border-radius: 12px;
  border-left: 4px solid #1890ff;
}

.suggestion-icon {
  font-size: 24px;
}

.suggestion-content {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}

.suggestion-detail {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.highlight-job {
  color: #1890ff;
  font-weight: 600;
}

.compare-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
}

.compare-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.compare-empty p {
  margin: 0;
  font-size: 14px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: white;
  border-radius: 10px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.history-item:hover {
  background: #f5f5f5;
}

.history-item.active {
  background: #f0f4ff;
  border: 1px solid #667eea;
}

.history-main {
  display: flex;
  align-items: center;
  flex: 1;
  cursor: pointer;
}

.history-job {
  font-size: 14px;
  font-weight: 500;
  flex: 1;
}

.history-score {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
  margin-right: 8px;
}

.history-item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.history-item:hover .history-item-actions {
  opacity: 1;
}

.history-item .refresh-btn,
.history-item .delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 4px;
  transition: all 0.2s;
}

.history-item .delete-btn:hover {
  transform: scale(1.1);
}

.history-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.clear-all-btn {
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #ff7875;
  border-radius: 6px;
  color: #ff4d4f;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-all-btn:hover {
  background: #fff1f0;
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

.primary-btn {
  padding: 12px 32px;
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

/* 骨架屏 */
@keyframes shimmer {
  0% { background-position: -468px 0; }
  100% { background-position: 468px 0; }
}

.skeleton-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px 0;
}

.skeleton-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.skel {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 468px 100%;
  animation: shimmer 1.2s ease-in-out infinite;
  border-radius: 6px;
  width: 100%;
}

.skel-title { height: 24px; width: 60%; }
.skel-circle { width: 100px; height: 100px; border-radius: 50%; }
.skel-bar { height: 16px; }
.skel-bar.short { width: 70%; }

.skeleton-hint {
  color: #999;
  font-size: 14px;
}

.no-result-hint {
  text-align: center;
  padding: 48px 24px;
  color: #aaa;
  font-size: 15px;
}

.review-hint {
  background: #fff2e8;
  border: 1px solid #ffbb96;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 13px;
  color: #d4380d;
  margin-top: 8px;
}

.review-warning {
  margin-top: 10px;
  padding: 8px 14px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  font-size: 13px;
  color: #d46b08;
  font-weight: 500;
}

.competitive-context {
  margin-top: 10px;
  padding: 8px 14px;
  background: #f0f7ff;
  border-left: 3px solid #4096ff;
  border-radius: 0 8px 8px 0;
  font-size: 13px;
  color: #1677ff;
  line-height: 1.6;
}

.recommend-bar {
  margin-bottom: 16px;
  text-align: right;
}

.recommend-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.recommend-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.recommend-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #e8eaed;
}

.recommend-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 14px;
}

.rec-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.rec-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.rec-card:hover {
  border-color: #667eea;
  box-shadow: 0 2px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.rec-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.rec-title {
  font-weight: 600;
  font-size: 14px;
  color: #1a1a2e;
}

.rec-score {
  font-size: 14px;
  font-weight: 700;
  color: #667eea;
}

.rec-summary {
  font-size: 12px;
  color: #666;
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 真实招聘样本卡片 */
.real-jobs-card {
  background: white;
  border-radius: 16px;
  padding: 0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  overflow: hidden;
}

.real-jobs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.real-jobs-header:hover {
  background: #f8faff;
}

.real-jobs-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.market-icon {
  font-size: 18px;
}

.jd-badge {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.real-jobs-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.salary-tag {
  font-size: 13px;
  color: #52c41a;
  font-weight: 600;
  background: #f6ffed;
  padding: 2px 10px;
  border-radius: 8px;
  border: 1px solid #b7eb8f;
}

.toggle-icon {
  font-size: 12px;
  color: #999;
}

.real-jobs-body {
  padding: 0 20px 16px;
  border-top: 1px solid #f0f0f0;
}

.top-companies {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 12px 0;
}

.meta-label {
  font-size: 12px;
  color: #999;
}

.company-tag {
  font-size: 12px;
  color: #667eea;
  background: #f0f2ff;
  padding: 2px 8px;
  border-radius: 6px;
}

.top-regions, .culture-types {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}

.region-tag {
  font-size: 12px;
  color: #0d9488;
  background: #f0fdf9;
  padding: 2px 8px;
  border-radius: 6px;
}

.culture-tag {
  font-size: 12px;
  color: #d97706;
  background: #fffbeb;
  padding: 2px 8px;
  border-radius: 6px;
}

.sample-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.sample-item {
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #eef0f8;
}

.sample-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.sample-company {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.sample-salary {
  font-size: 13px;
  color: #52c41a;
  font-weight: 600;
}

.sample-addr,
.sample-size {
  font-size: 12px;
  color: #888;
  margin-bottom: 3px;
}

.sample-desc {
  font-size: 12px;
  color: #666;
  margin-top: 6px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.samples-loading {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 16px 0;
}

/* 评分解释 */
.dim-evidence-detail {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.evidence-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.evidence-bullet {
  font-weight: 700;
  width: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

.evidence-match { color: #389e0d; }
.evidence-gap { color: #cf1322; }
.evidence-info { color: #666; }

/* JD来源标注 */
.dim-jd-sources {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 6px;
  border-left: 3px solid #faad14;
  font-size: 12px;
}

.jd-source-header {
  color: #8c6d00;
  font-weight: 600;
  margin-bottom: 5px;
}

.jd-source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 3px 0;
  flex-wrap: wrap;
}

.src-importance {
  padding: 1px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.src-must { background: #fff1f0; color: #cf1322; }
.src-nice { background: #e6f7ff; color: #0958d9; }

.src-skill { font-weight: 500; color: #333; }
.src-from { color: #888; font-style: italic; font-size: 11px; }

/* 数据说明折叠面板 */
.data-source-panel {
  background: white;
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
}

.panel-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  user-select: none;
  transition: background 0.2s;
}

.panel-toggle:hover { background: #f8f9fa; }

.toggle-arrow { font-size: 11px; color: #999; }

.panel-body {
  padding: 4px 18px 14px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
}

.source-tag {
  flex-shrink: 0;
  padding: 2px 9px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  margin-top: 1px;
}

.source-rule { background: #e6fffb; color: #08979c; }
.source-ai { background: #f9f0ff; color: #531dab; }
.source-market { background: #fff7e6; color: #d46b08; }

.source-desc { color: #555; line-height: 1.5; }

.source-note {
  font-size: 11px;
  color: #aaa;
  padding-top: 4px;
  border-top: 1px dashed #f0f0f0;
}

.card-header-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header-with-action h3 {
  margin: 0;
}

.detail-toggle-btn {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.detail-toggle-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.skill-match-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.summary-label {
  font-size: 13px;
  color: #666;
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
}

.summary-value.matched { color: #52c41a; }
.summary-value.partial { color: #1890ff; }
.summary-value.semantic { color: #722ed1; }
.summary-value.missing { color: #fa8c16; }

.skill-tag.more {
  background: #f0f0f0;
  color: #666;
  cursor: pointer;
}

.skill-tag.more:hover {
  background: #e6e6e6;
}

.gap-summary {
  margin-bottom: 16px;
}

.gap-summary-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 10px;
  margin-bottom: 10px;
  border-left: 3px solid #ddd;
}

.gap-summary-item:last-child {
  margin-bottom: 0;
}

.gap-severity-badge {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.gap-severity-badge.critical {
  background: #fff1f0;
  color: #cf1322;
}

.gap-severity-badge.moderate {
  background: #fff7e6;
  color: #d46b08;
}

.gap-severity-badge.minor {
  background: #f6ffed;
  color: #389e0d;
}

.gap-summary-content {
  flex: 1;
}

.gap-summary-desc {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 0 0 4px;
}

.gap-summary-impact {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.improvement-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.improvement-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  color: #333;
}

.improvement-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.improvement-item {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.improvement-priority {
  flex-shrink: 0;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.improvement-priority.high {
  background: #fff1f0;
  color: #cf1322;
}

.improvement-priority.medium {
  background: #fff7e6;
  color: #d46b08;
}

.improvement-priority.low {
  background: #f6ffed;
  color: #389e0d;
}

.improvement-content {
  flex: 1;
}

.improvement-text {
  font-size: 13px;
  color: #333;
  margin: 0 0 4px;
  line-height: 1.5;
}

.improvement-timeline {
  font-size: 12px;
  color: #888;
  margin: 0;
}

.confidence-breakdown-section {
  margin-top: 16px;
  background: #f8fafc;
  border-radius: 10px;
  overflow: hidden;
}

.breakdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.breakdown-header:hover {
  background: #f0f4f8;
}

.breakdown-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.breakdown-body {
  padding: 0 16px 16px;
}

.breakdown-item {
  margin-bottom: 12px;
}

.breakdown-item:last-child {
  margin-bottom: 0;
}

.breakdown-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}

.breakdown-value {
  font-weight: 600;
  color: #667eea;
}

.breakdown-bar {
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.breakdown-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.breakdown-factors {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e8e8e8;
}

.factor-item {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.factor-item:last-child {
  margin-bottom: 0;
}

.factor-name {
  flex-shrink: 0;
  font-weight: 500;
  color: #666;
}

.factor-desc {
  color: #888;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  max-width: 90vw;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.skill-detail-modal {
  width: 700px;
}

.gap-detail-modal {
  width: 700px;
}

.dimension-detail-modal {
  width: 600px;
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
  color: #1a1a2e;
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: #f5f5f5;
  color: #666;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  background: #e8e8e8;
  color: #333;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.skill-detail-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  background: white;
  color: #666;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-color: transparent;
}

.skill-detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-detail-item {
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e8e8e8;
}

.skill-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.skill-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.skill-badges {
  display: flex;
  gap: 8px;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.matched {
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.partial {
  background: #e6f7ff;
  color: #1890ff;
}

.status-badge.missing {
  background: #fff7e6;
  color: #fa8c16;
}

.status-badge.semantic_matched {
  background: #f9f0ff;
  color: #722ed1;
}

.importance-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.importance-badge.must_have {
  background: #fff1f0;
  color: #cf1322;
}

.importance-badge.nice_to_have {
  background: #f0f5ff;
  color: #2f54eb;
}

.skill-detail-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.detail-row .detail-label {
  flex-shrink: 0;
  color: #888;
  min-width: 70px;
}

.detail-row .detail-value {
  color: #333;
  line-height: 1.5;
}

.detail-row .detail-value.evidence {
  color: #52c41a;
}

.similarity-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.similarity-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.5s ease;
}

.similarity-value {
  position: absolute;
  right: 8px;
  font-size: 11px;
  font-weight: 600;
  color: #667eea;
}

.empty-detail {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  font-size: 14px;
}

.gap-analysis-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.gap-analysis-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e8e8e8;
}

.gap-analysis-header {
  margin-bottom: 12px;
}

.gap-severity-tag {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.gap-severity-tag.critical {
  background: #fff1f0;
  color: #cf1322;
}

.gap-severity-tag.moderate {
  background: #fff7e6;
  color: #d46b08;
}

.gap-severity-tag.minor {
  background: #f6ffed;
  color: #389e0d;
}

.gap-analysis-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gap-desc-section h4,
.gap-impact-section h4,
.gap-suggestions-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #333;
}

.gap-desc-section p,
.gap-impact-section p {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.6;
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.suggestion-priority {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.suggestion-priority.high {
  background: #fff1f0;
  color: #cf1322;
}

.suggestion-priority.medium {
  background: #fff7e6;
  color: #d46b08;
}

.suggestion-priority.low {
  background: #f6ffed;
  color: #389e0d;
}

.suggestion-timeline {
  font-size: 12px;
  color: #888;
}

.suggestion-text {
  font-size: 13px;
  color: #333;
  margin: 0 0 8px;
  line-height: 1.5;
}

.suggestion-resources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.resource-label {
  font-size: 12px;
  color: #888;
}

.resource-tag {
  padding: 2px 8px;
  background: #f0f4ff;
  color: #667eea;
  border-radius: 4px;
  font-size: 11px;
}

.dimension-detail-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dimension-detail-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e8e8e8;
}

.dim-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.dim-detail-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.dim-detail-score {
  font-size: 16px;
  font-weight: 700;
}

.dim-detail-progress {
  margin-bottom: 12px;
}

.progress-bar {
  height: 10px;
  background: #e8e8e8;
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.5s ease;
}

.dim-detail-text,
.dim-detail-evidence {
  margin-top: 12px;
}

.dim-detail-text .detail-label,
.dim-detail-evidence .detail-label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.dim-detail-text p {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.6;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

@media (max-width: 768px) {
  .modal-content {
    width: 95vw !important;
    max-height: 90vh;
  }

  .skill-match-summary {
    flex-direction: column;
  }

  .summary-item {
    width: 100%;
  }
}

.explanation-tree-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.explanation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.explanation-header h3 { margin: 0; font-size: 16px; }
.expand-toggle { color: #1890ff; font-size: 13px; }
.explanation-body { margin-top: 14px; display: flex; flex-direction: column; gap: 12px; }
.explanation-dim { border: 1px solid #f0f0f0; border-radius: 10px; padding: 12px 16px; }
.exp-dim-header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.exp-dim-label { font-weight: 600; font-size: 14px; color: #262626; }
.exp-dim-score { color: #1890ff; font-weight: 700; }
.exp-dim-weight { color: #8c8c8c; font-size: 12px; }
.exp-dim-contrib { color: #52c41a; font-size: 12px; font-weight: 600; }
.exp-factors { margin: 0; padding-left: 18px; font-size: 13px; color: #595959; line-height: 1.9; }
.exp-factor-name { color: #434343; font-weight: 500; }

.transfer-paths-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.transfer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.transfer-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.transfer-hint {
  font-size: 12px;
  color: #888;
}

.transfer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.transfer-item {
  padding: 14px 16px;
  background: #f8fafc;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.transfer-item:hover {
  border-color: #667eea;
  box-shadow: 0 2px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.transfer-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.transfer-target {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.transfer-level {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
}

.transfer-level.level-高 {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.transfer-level.level-中 {
  background: #fff7e6;
  color: #fa8c16;
  border: 1px solid #ffd591;
}

.transfer-level.level-低 {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.transfer-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.transfer-overlap {
  font-size: 13px;
  color: #667eea;
  font-weight: 500;
}

.transfer-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e8e8e8;
}

.transfer-detail p {
  margin: 0 0 6px;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.transfer-detail p:last-child {
  margin-bottom: 0;
}

.transfer-detail .label {
  color: #888;
  font-weight: 500;
}

.transfer-advantage {
  color: #52c41a !important;
}

.transfer-need {
  color: #fa8c16 !important;
}

/* ====== E-2: 移动端适配 ====== */
@media (max-width: 768px) {
  .match-layout {
    flex-direction: column !important;
    padding: 12px;
  }
  .job-sidebar {
    width: 100% !important;
    max-height: 200px;
    overflow-y: auto;
  }
  .match-content {
    padding: 0 !important;
  }
  .score-ring-section {
    flex-direction: column;
    align-items: center;
  }
  .dimensions-grid {
    grid-template-columns: 1fr !important;
  }
  .live-stats-row {
    justify-content: space-around;
  }
  .explanation-dim {
    padding: 8px 12px;
  }
  .exp-dim-header {
    gap: 6px;
  }
  .transfer-list {
    grid-template-columns: 1fr !important;
  }
  .compare-panel {
    overflow-x: auto;
  }
  .action-buttons {
    flex-direction: column;
    gap: 8px;
  }
  .action-buttons button {
    width: 100%;
  }
  .batch-panel {
    grid-template-columns: 1fr !important;
  }
}
</style>
