<template>
  <div class="experience-timeline">
    <div class="timeline-header">
      <h4>{{ title }}</h4>
      <div class="timeline-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.key"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span class="count" v-if="getCount(tab.key)">{{ getCount(tab.key) }}</span>
        </button>
      </div>
    </div>

    <div class="timeline-content">
      <div v-if="currentItems.length === 0" class="empty-state">
        <span class="empty-icon">📝</span>
        <p>暂无{{ activeTab === 'internships' ? '实习' : '项目' }}经历</p>
        <button class="add-btn" @click="$router.push('/upload')">添加经历</button>
      </div>

      <div v-else class="timeline-list">
        <div 
          v-for="(item, index) in currentItems" 
          :key="index"
          class="timeline-item"
          :class="{ 'has-detail': item.description }"
        >
          <div class="timeline-dot" :class="activeTab"></div>
          <div class="timeline-line" v-if="index < currentItems.length - 1"></div>
          
          <div class="item-content">
            <div class="item-header">
              <h5 class="item-title">{{ getItemTitle(item) }}</h5>
              <span class="item-time" v-if="item.duration_months || item.duration">
                {{ item.duration_months ? `${item.duration_months}个月` : item.duration }}
              </span>
            </div>
            
            <div class="item-subtitle" v-if="getItemSubtitle(item)">
              {{ getItemSubtitle(item) }}
            </div>
            
            <p class="item-description" v-if="item.description">
              {{ item.description }}
            </p>

            <div class="item-tags" v-if="item.tech_stack?.length">
              <span 
                v-for="tech in item.tech_stack" 
                :key="tech"
                class="tech-tag"
              >
                {{ tech }}
              </span>
            </div>

            <div class="item-skills" v-if="item.skills?.length">
              <span 
                v-for="skill in item.skills.slice(0, 5)" 
                :key="skill"
                class="skill-tag"
              >
                {{ skill }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="timeline-summary" v-if="currentItems.length > 0">
      <div class="summary-stat">
        <span class="stat-value">{{ currentItems.length }}</span>
        <span class="stat-label">{{ activeTab === 'internships' ? '段实习' : '个项目' }}</span>
      </div>
      <div class="summary-stat" v-if="totalDuration > 0">
        <span class="stat-value">{{ totalDuration }}</span>
        <span class="stat-label">个月总时长</span>
      </div>
      <div class="summary-stat" v-if="totalSkills > 0">
        <span class="stat-value">{{ totalSkills }}</span>
        <span class="stat-label">项技能</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Internship {
  company: string
  role: string
  duration_months?: number
  duration?: string
  description?: string
  skills?: string[]
  tech_stack?: string[]
}

interface Project {
  name: string
  description?: string
  tech_stack?: string[]
  duration?: string
  role?: string
  duration_months?: number
  skills?: string[]
}

const props = withDefaults(defineProps<{
  title?: string
  internships?: Internship[]
  projects?: Project[]
}>(), {
  title: '经历时间线',
  internships: () => [],
  projects: () => []
})

const activeTab = ref('internships')

const tabs = [
  { key: 'internships', label: '实习经历' },
  { key: 'projects', label: '项目经历' }
]

const currentItems = computed(() => {
  if (activeTab.value === 'internships') {
    return props.internships
  }
  return props.projects
})

const totalDuration = computed(() => {
  if (activeTab.value === 'internships') {
    return props.internships.reduce((sum, item) => sum + (item.duration_months || 0), 0)
  }
  return 0
})

const totalSkills = computed(() => {
  const skillSet = new Set<string>()
  if (activeTab.value === 'internships') {
    props.internships.forEach(item => {
      item.skills?.forEach(s => skillSet.add(s))
    })
  } else {
    props.projects.forEach(item => {
      item.tech_stack?.forEach(s => skillSet.add(s))
    })
  }
  return skillSet.size
})

function getCount(key: string): number {
  return key === 'internships' ? props.internships.length : props.projects.length
}

function getItemTitle(item: Internship | Project): string {
  if (activeTab.value === 'internships') {
    return (item as Internship).company || '未知公司'
  }
  return (item as Project).name || '未命名项目'
}

function getItemSubtitle(item: Internship | Project): string {
  if (activeTab.value === 'internships') {
    return (item as Internship).role || ''
  }
  return (item as Project).role || ''
}
</script>

<style scoped>
.experience-timeline {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.timeline-header {
  margin-bottom: 20px;
}

.timeline-header h4 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.timeline-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px solid #e5e5e5;
  background: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.tab-btn .count {
  background: rgba(255, 255, 255, 0.2);
  padding: 0 6px;
  border-radius: 10px;
  font-size: 11px;
}

.tab-btn:not(.active) .count {
  background: #f0f0f0;
}

.timeline-content {
  min-height: 150px;
}

.empty-state {
  text-align: center;
  padding: 30px 20px;
}

.empty-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 12px;
}

.empty-state p {
  color: #999;
  margin: 0 0 12px;
}

.add-btn {
  padding: 8px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  font-size: 13px;
  cursor: pointer;
}

.timeline-list {
  position: relative;
}

.timeline-item {
  position: relative;
  padding-left: 28px;
  padding-bottom: 20px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: 0;
  top: 4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid;
}

.timeline-dot.internships {
  border-color: #667eea;
  background: #f0f4ff;
}

.timeline-dot.projects {
  border-color: #52c41a;
  background: #f6ffed;
}

.timeline-line {
  position: absolute;
  left: 6px;
  top: 20px;
  width: 2px;
  height: calc(100% - 10px);
  background: #f0f0f0;
}

.item-content {
  background: #f8fafc;
  border-radius: 10px;
  padding: 14px;
  transition: all 0.2s;
}

.timeline-item.has-detail .item-content:hover {
  background: #f0f4ff;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}

.item-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.item-time {
  font-size: 12px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.item-subtitle {
  font-size: 13px;
  color: #667eea;
  margin-bottom: 8px;
}

.item-description {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin: 0 0 10px;
}

.item-tags,
.item-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tech-tag {
  padding: 3px 10px;
  background: #e6f7ff;
  color: #1890ff;
  border-radius: 10px;
  font-size: 11px;
}

.skill-tag {
  padding: 3px 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  font-size: 11px;
}

.timeline-summary {
  display: flex;
  justify-content: space-around;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

@media (max-width: 768px) {
  .timeline-tabs {
    flex-direction: column;
  }
  
  .tab-btn {
    justify-content: center;
  }
  
  .timeline-summary {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
