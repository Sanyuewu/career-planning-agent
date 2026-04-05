<template>
  <div class="learning-resource-card" v-if="resources.length > 0">
    <div class="card-header">
      <span class="card-icon">📚</span>
      <h3>学习资源推荐</h3>
      <span class="resource-count">{{ resources.length }}项技能</span>
    </div>
    
    <div class="resource-list">
      <div 
        v-for="(item, index) in resources" 
        :key="index"
        class="resource-item"
        :class="'priority-' + item.priority"
      >
        <div class="resource-header">
          <span class="skill-name">{{ item.skill }}</span>
          <span :class="['priority-badge', item.priority]">
            {{ getPriorityText(item.priority) }}
          </span>
        </div>
        
        <div class="resource-body" v-if="item.resources">
          <div class="resource-row" v-if="item.resources.official">
            <span class="row-label">📖 官方文档:</span>
            <a :href="item.resources.official" target="_blank" class="row-link">
              {{ item.resources.official }}
            </a>
          </div>
          
          <div class="resource-row" v-if="item.resources.courses?.length">
            <span class="row-label">🎓 推荐课程:</span>
            <span class="row-value">{{ item.resources.courses.join(' | ') }}</span>
          </div>
          
          <div class="resource-row" v-if="item.resources.books?.length">
            <span class="row-label">📕 推荐书籍:</span>
            <span class="row-value">{{ item.resources.books.join(' | ') }}</span>
          </div>
          
          <div class="resource-row" v-if="item.resources.estimated_hours">
            <span class="row-label">⏱️ 预计时长:</span>
            <span class="row-value highlight">{{ item.resources.estimated_hours }}小时</span>
          </div>
        </div>
        
        <div class="resource-actions">
          <button class="action-btn primary" @click="startLearning(item.skill)">
            开始学习
          </button>
          <button class="action-btn secondary" @click="addToPlan(item.skill)">
            加入计划
          </button>
        </div>
      </div>
    </div>
    
    <div class="card-footer" v-if="totalHours > 0">
      <span class="footer-text">总计学习时长约 <strong>{{ totalHours }}</strong> 小时</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Message } from '@arco-design/web-vue'

interface LearningResource {
  official?: string
  courses?: string[]
  books?: string[]
  estimated_hours?: number
}

interface ResourceItem {
  skill: string
  priority: 'high' | 'medium' | 'low'
  resources?: LearningResource
}

interface Props {
  resources: ResourceItem[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  startLearning: [skill: string]
  addToPlan: [skill: string]
}>()

const totalHours = computed(() => {
  return props.resources.reduce((sum, item) => {
    return sum + (item.resources?.estimated_hours || 0)
  }, 0)
})

function getPriorityText(priority: string): string {
  const map: Record<string, string> = {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级'
  }
  return map[priority] || priority
}

function startLearning(skill: string) {
  emit('startLearning', skill)
  Message.info(`即将跳转到 ${skill} 学习资源`)
}

function addToPlan(skill: string) {
  emit('addToPlan', skill)
  Message.success(`${skill} 已加入学习计划`)
}
</script>

<style scoped>
.learning-resource-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.card-icon {
  font-size: 24px;
}

.card-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.resource-count {
  margin-left: auto;
  font-size: 13px;
  color: #667eea;
  background: #f0f4ff;
  padding: 4px 12px;
  border-radius: 12px;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.resource-item {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  border-left: 4px solid #e8e8e8;
  transition: all 0.2s;
}

.resource-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.resource-item.priority-high {
  border-left-color: #f5222d;
  background: linear-gradient(135deg, #fff1f0 0%, #fff 100%);
}

.resource-item.priority-medium {
  border-left-color: #fa8c16;
  background: linear-gradient(135deg, #fff7e6 0%, #fff 100%);
}

.resource-item.priority-low {
  border-left-color: #52c41a;
  background: linear-gradient(135deg, #f6ffed 0%, #fff 100%);
}

.resource-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.skill-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.priority-badge {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
}

.priority-badge.high {
  background: #fff1f0;
  color: #cf1322;
}

.priority-badge.medium {
  background: #fff7e6;
  color: #d46b08;
}

.priority-badge.low {
  background: #f6ffed;
  color: #389e0d;
}

.resource-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.resource-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}

.row-label {
  color: #888;
  flex-shrink: 0;
  min-width: 80px;
}

.row-value {
  color: #555;
  line-height: 1.5;
}

.row-value.highlight {
  color: #667eea;
  font-weight: 600;
}

.row-link {
  color: #1890ff;
  text-decoration: none;
  word-break: break-all;
}

.row-link:hover {
  text-decoration: underline;
}

.resource-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px dashed #e8e8e8;
}

.action-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.action-btn.secondary {
  background: white;
  color: #667eea;
  border: 1px solid #667eea;
}

.action-btn.secondary:hover {
  background: #f0f4ff;
}

.card-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}

.footer-text {
  font-size: 14px;
  color: #666;
}

.footer-text strong {
  color: #667eea;
  font-size: 18px;
}
</style>
