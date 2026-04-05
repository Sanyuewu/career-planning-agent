<template>
  <div class="agent-process-panel">
    <div class="panel-header">
      <span class="panel-icon">🤖</span>
      <span class="panel-title">AI智能分析</span>
      <span class="panel-duration" v-if="duration">{{ duration.toFixed(1) }}s</span>
    </div>
    
    <div class="agents-flow">
      <div 
        v-for="agent in agents" 
        :key="agent.key"
        :class="['agent-item', getAgentStatus(agent.key)]"
      >
        <div class="agent-icon">
          <span v-if="getAgentStatus(agent.key) === 'completed'">✓</span>
          <span v-else-if="getAgentStatus(agent.key) === 'running'" class="running-icon">●</span>
          <span v-else class="pending-icon">○</span>
        </div>
        <div class="agent-info">
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-desc" v-if="getAgentStatus(agent.key) === 'running'">{{ agent.currentTask || '分析中...' }}</span>
        </div>
        <div class="agent-time" v-if="agent.duration">{{ agent.duration }}s</div>
      </div>
      
      <div class="flow-arrow" v-if="currentIndex < agents.length - 1">
        <span>→</span>
      </div>
    </div>
    
    <div class="process-meta" v-if="currentTask">
      <span class="meta-item">
        <span class="meta-label">当前任务:</span>
        <span class="meta-value">{{ currentTask }}</span>
      </span>
      <span class="meta-item" v-if="confidence">
        <span class="meta-label">置信度:</span>
        <span class="meta-value confidence">{{ (confidence * 100).toFixed(0) }}%</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface AgentInfo {
  key: string
  name: string
  currentTask?: string
  duration?: number
}

interface Props {
  agentStates: Record<string, 'idle' | 'running' | 'completed' | 'failed'>
  currentAgent?: string
  duration?: number
  confidence?: number
}

const props = defineProps<Props>()

const agents: AgentInfo[] = [
  { key: 'resume_analyzer', name: '简历分析', currentTask: '解析简历信息...' },
  { key: 'job_matcher', name: '岗位匹配', currentTask: '匹配岗位需求...' },
  { key: 'career_advisor', name: '职业建议', currentTask: '生成职业建议...' },
  { key: 'report_generator', name: '报告生成', currentTask: '生成分析报告...' },
]

const currentIndex = computed(() => {
  const runningIndex = Object.keys(props.agentStates).findIndex(
    key => props.agentStates[key] === 'running'
  )
  return runningIndex >= 0 ? runningIndex : -1
})

const currentTask = computed(() => {
  if (!props.currentAgent) return ''
  const agent = agents.find(a => a.key === props.currentAgent)
  return agent?.currentTask || ''
})

function getAgentStatus(key: string): string {
  return props.agentStates[key] || 'idle'
}
</script>

<style scoped>
.agent-process-panel {
  background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
  border: 1px solid #e0e8ff;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.panel-icon {
  font-size: 24px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.panel-duration {
  margin-left: auto;
  font-size: 13px;
  color: #667eea;
  font-weight: 500;
  background: #e8f0ff;
  padding: 4px 12px;
  border-radius: 12px;
}

.agents-flow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.agent-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e8e8e8;
  min-width: 100px;
  transition: all 0.3s ease;
}

.agent-item.completed {
  background: #f6ffed;
  border-color: #b7eb8f;
}

.agent-item.running {
  background: #fff7e6;
  border-color: #faad14;
  animation: pulse 1.5s ease-in-out infinite;
}

.agent-item.failed {
  background: #fff1f0;
  border-color: #ffccc7;
}

.agent-item.idle {
  opacity: 0.6;
}

.agent-icon {
  font-size: 20px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.running-icon {
  color: #faad14;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

.agent-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.agent-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.agent-desc {
  font-size: 11px;
  color: #999;
}

.agent-time {
  font-size: 11px;
  color: #667eea;
  font-weight: 500;
}

.flow-arrow {
  font-size: 18px;
  color: #ccc;
}

.process-meta {
  display: flex;
  gap: 20px;
  padding-top: 12px;
  border-top: 1px dashed #e8e8e8;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.meta-label {
  color: #999;
}

.meta-value {
  color: #333;
  font-weight: 500;
}

.meta-value.confidence {
  color: #52c41a;
}
</style>
