<template>
  <div class="async-task-progress" v-if="visible">
    <div class="progress-header">
      <span class="progress-icon">🚀</span>
      <span class="progress-title">{{ title }}</span>
      <button class="close-btn" @click="handleCancel" v-if="cancellable && status !== 'completed'">
        ✕
      </button>
    </div>
    
    <div class="progress-body">
      <p class="progress-desc" v-if="description">{{ description }}</p>
      
      <div class="progress-bar-container">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: progressPercent + '%' }"
            :class="status"
          ></div>
        </div>
        <span class="progress-percent">{{ progressPercent.toFixed(0) }}%</span>
      </div>
      
      <div class="progress-status">
        <span :class="['status-badge', status]">
          {{ getStatusText(status) }}
        </span>
        <span class="status-message" v-if="statusMessage">{{ statusMessage }}</span>
      </div>
      
      <div class="progress-steps" v-if="steps.length > 0">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          :class="['step', { active: currentStep === index, done: currentStep > index }]"
        >
          <span class="step-dot">{{ currentStep > index ? '✓' : index + 1 }}</span>
          <span class="step-label">{{ step }}</span>
        </div>
      </div>
      
      <div class="progress-meta" v-if="duration">
        <span class="meta-item">
          <span class="meta-icon">⏱️</span>
          <span>已耗时: {{ duration.toFixed(1) }}s</span>
        </span>
      </div>
    </div>
    
    <div class="progress-actions" v-if="status === 'completed'">
      <button class="action-btn primary" @click="handleViewResult">
        查看结果
      </button>
    </div>
    
    <div class="progress-actions" v-else-if="status === 'failed'">
      <button class="action-btn secondary" @click="handleRetry">
        重试
      </button>
      <button class="action-btn secondary" @click="handleCancel">
        关闭
      </button>
    </div>
    
    <div class="progress-actions" v-else-if="cancellable">
      <button class="action-btn secondary" @click="handleCancel">
        取消任务
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  visible: boolean
  title?: string
  description?: string
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  statusMessage?: string
  steps?: string[]
  currentStep?: number
  duration?: number
  cancellable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '任务执行中',
  description: '',
  steps: () => [],
  currentStep: 0,
  cancellable: true
})

const emit = defineEmits<{
  cancel: []
  retry: []
  viewResult: []
}>()

const progressPercent = computed(() => {
  return Math.min(100, Math.max(0, props.progress * 100))
})

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '执行失败'
  }
  return map[status] || status
}

function handleCancel() {
  emit('cancel')
}

function handleRetry() {
  emit('retry')
}

function handleViewResult() {
  emit('viewResult')
}
</script>

<style scoped>
.async-task-progress {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e8e8e8;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.progress-icon {
  font-size: 24px;
}

.progress-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  flex: 1;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #f5f5f5;
  color: #999;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #e8e8e8;
  color: #666;
}

.progress-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-desc {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 12px;
  background: #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.3s ease;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.progress-fill.running {
  background: linear-gradient(90deg, #faad14 0%, #fa8c16 100%);
  animation: progress-pulse 1.5s ease-in-out infinite;
}

.progress-fill.completed {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.progress-fill.failed {
  background: linear-gradient(90deg, #f5222d 0%, #ff4d4f 100%);
}

@keyframes progress-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
  min-width: 45px;
  text-align: right;
}

.progress-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-badge {
  font-size: 12px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 12px;
}

.status-badge.pending {
  background: #f0f0f0;
  color: #999;
}

.status-badge.running {
  background: #fff7e6;
  color: #d46b08;
}

.status-badge.completed {
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.failed {
  background: #fff1f0;
  color: #f5222d;
}

.status-message {
  font-size: 13px;
  color: #666;
}

.progress-steps {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #999;
  transition: all 0.2s;
}

.step.active {
  background: #fff7e6;
  color: #d46b08;
  font-weight: 500;
}

.step.done {
  background: #f6ffed;
  color: #52c41a;
}

.step-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}

.step.active .step-dot {
  background: #faad14;
  color: white;
}

.step.done .step-dot {
  background: #52c41a;
  color: white;
}

.step-label {
  white-space: nowrap;
}

.progress-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.progress-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.action-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
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
  color: #666;
  border: 1px solid #e8e8e8;
}

.action-btn.secondary:hover {
  background: #f8f9fa;
  border-color: #ccc;
}
</style>
