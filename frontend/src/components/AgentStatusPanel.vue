<template>
  <div class="agent-status-panel">
    <div class="panel-header">
      <span class="panel-icon">🤖</span>
      <h4>AI分析状态</h4>
    </div>
    
    <div class="agent-list">
      <div 
        v-for="agent in agentList" 
        :key="agent.key"
        :class="['agent-item', agentStates[agent.key] || 'idle']"
      >
        <div class="agent-status-icon">
          <span v-if="agentStates[agent.key] === 'completed'" class="icon-done">✓</span>
          <span v-else-if="agentStates[agent.key] === 'running'" class="icon-running">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </span>
          <span v-else-if="agentStates[agent.key] === 'failed'" class="icon-fail">✗</span>
          <span v-else class="icon-idle">○</span>
        </div>
        <div class="agent-info">
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-status-text">{{ getStatusText(agentStates[agent.key]) }}</span>
        </div>
        <div class="agent-confidence" v-if="confidences[agent.key]">
          <span class="confidence-value">{{ (confidences[agent.key] * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
    
    <div class="panel-footer" v-if="currentTask">
      <div class="current-task">
        <span class="task-label">当前任务:</span>
        <span class="task-value">{{ currentTask }}</span>
      </div>
    </div>
    
    <div class="tool-calls" v-if="toolCalls.length > 0">
      <div class="tool-header">
        <span class="tool-icon">🔧</span>
        <span class="tool-title">工具调用记录</span>
      </div>
      <div class="tool-list">
        <div 
          v-for="(call, index) in toolCalls.slice(0, 5)" 
          :key="index"
          class="tool-item"
        >
          <span class="tool-name">{{ call.name }}</span>
          <span class="tool-time">{{ call.time }}</span>
        </div>
        <div class="tool-more" v-if="toolCalls.length > 5">
          还有 {{ toolCalls.length - 5 }} 次调用...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface AgentInfo {
  key: string
  name: string
}

interface ToolCall {
  name: string
  time: string
}

interface Props {
  agentStates?: Record<string, 'idle' | 'running' | 'completed' | 'failed'>
  confidences?: Record<string, number>
  currentTask?: string
  toolCalls?: ToolCall[]
}

const props = withDefaults(defineProps<Props>(), {
  agentStates: () => ({}),
  confidences: () => ({}),
  toolCalls: () => []
})

const agentList: AgentInfo[] = [
  { key: 'resume_analyzer', name: '简历分析' },
  { key: 'job_matcher', name: '岗位匹配' },
  { key: 'career_advisor', name: '职业建议' },
  { key: 'report_generator', name: '报告生成' }
]

function getStatusText(status?: string): string {
  const map: Record<string, string> = {
    idle: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '执行失败'
  }
  return map[status || 'idle'] || '待执行'
}
</script>

<style scoped>
.agent-status-panel {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.panel-icon {
  font-size: 20px;
}

.panel-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  transition: all 0.2s;
}

.agent-item.running {
  background: #fff7e6;
  border-color: #ffd591;
}

.agent-item.completed {
  background: #f6ffed;
  border-color: #b7eb8f;
}

.agent-item.failed {
  background: #fff1f0;
  border-color: #ffccc7;
}

.agent-status-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.icon-done {
  color: #52c41a;
  font-weight: bold;
}

.icon-running {
  display: flex;
  gap: 3px;
}

.icon-running .dot {
  width: 4px;
  height: 4px;
  background: #faad14;
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.icon-running .dot:nth-child(1) { animation-delay: 0s; }
.icon-running .dot:nth-child(2) { animation-delay: 0.2s; }
.icon-running .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.icon-fail {
  color: #f5222d;
  font-weight: bold;
}

.icon-idle {
  color: #d9d9d9;
}

.agent-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.agent-status-text {
  font-size: 11px;
  color: #999;
}

.agent-confidence {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  background: #f0f4ff;
  padding: 2px 8px;
  border-radius: 10px;
}

.panel-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e8e8e8;
}

.current-task {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.task-label {
  color: #999;
}

.task-value {
  color: #667eea;
  font-weight: 500;
}

.tool-calls {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e8e8e8;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.tool-icon {
  font-size: 14px;
}

.tool-title {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tool-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: white;
  border-radius: 6px;
  font-size: 11px;
}

.tool-name {
  color: #333;
}

.tool-time {
  color: #999;
}

.tool-more {
  font-size: 11px;
  color: #999;
  text-align: center;
  padding: 4px 0;
}
</style>
