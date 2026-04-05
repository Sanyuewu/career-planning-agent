<template>
  <div class="chat-page">
    <div class="chat-container">
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>对话进度</h3>
        </div>
        
        <div class="progress-steps">
          <div 
            v-for="(step, index) in STATE_STEPS" 
            :key="step.key"
            :class="['step-item', { 
              active: currentStepIndex === index,
              done: currentStepIndex > index 
            }]"
          >
            <div class="step-dot">{{ index + 1 }}</div>
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>
        
        <div class="emotion-section" v-if="emotionData">
          <h4>情绪状态</h4>
          <div class="emotion-badge" :class="getEmotionClass(emotionData.label)">
            {{ emotionData.label }}
          </div>
        </div>
        
        <div class="stats-section" v-if="messages.length > 0">
          <h4>对话统计</h4>
          <div class="stat-item">
            <span class="stat-label">对话轮次</span>
            <span class="stat-value">{{ Math.floor(messages.length / 2) }}</span>
          </div>
          <div class="stat-item" v-if="emotionData?.score">
            <span class="stat-label">情绪指数</span>
            <span class="stat-value">{{ (emotionData.score * 100).toFixed(0) }}</span>
          </div>
        </div>
        
        <div class="history-section" v-if="sessionHistory.length > 0">
          <h4>历史会话</h4>
          <div class="history-list">
            <div 
              v-for="session in sortedSessionHistory" 
              :key="session.id"
              :class="['history-item', { active: sessionId === session.id, pinned: isPinned(session.id) }]"
            >
              <div class="history-main" @click="loadSession(session.id)">
                <div class="history-title">
                  <span v-if="isPinned(session.id)" class="pin-icon">📌</span>
                  {{ session.title || '新对话' }}
                </div>
                <div class="history-time">{{ formatSessionTime(session.updatedAt) }}</div>
              </div>
              <div class="history-actions">
                <button class="history-action-btn pin-btn" @click.stop="togglePin(session.id)" :title="isPinned(session.id) ? '取消置顶' : '置顶'">
                  {{ isPinned(session.id) ? '📍' : '📌' }}
                </button>
                <button class="history-action-btn delete-btn" @click.stop="confirmDelete(session.id)" title="删除">
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- CrewAI Agent状态面板 -->
        <AgentStatusPanel
          v-if="crewAIEnabled"
          :agent-states="getAgentStatesForPanel()"
          :current-task="crewStore.isProcessing ? '正在分析...' : undefined"
        />
        
        <div class="sidebar-actions">
          <button class="action-btn" @click="startNewSession">
            <span>🔄</span> 新对话
          </button>
          <button class="action-btn" @click="$router.push('/report')">
            <span>📊</span> 生成报告
          </button>
        </div>
      </div>
      
      <div class="chat-main">
        <!-- FSM 状态指示条 -->
        <div
          v-if="messages.length > 0"
          class="state-indicator-bar"
          :style="{ borderLeftColor: currentStateLabel.color }"
        >
          <span class="state-icon">{{ currentStateLabel.icon }}</span>
          <span class="state-text">{{ currentStateLabel.text }}</span>
          <span v-if="streaming" class="state-thinking">...</span>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div class="welcome-message" v-if="messages.length === 0">
            <div class="welcome-icon">🤖</div>
            <h2>AI职业规划顾问</h2>
            <p class="welcome-sub">👋 你好！我是你的专属职业规划顾问，已接入岗位知识图谱、真实市场数据，可以帮你：</p>
            <div class="welcome-features">
              <div class="wf-item">📄 <span>解读你的简历画像，找出核心竞争力</span></div>
              <div class="wf-item">🎯 <span>五维度精准匹配最适合的岗位方向</span></div>
              <div class="wf-item">📈 <span>生成个性化职业报告，30天冲刺计划</span></div>
              <div class="wf-item">💬 <span>随时解答职业规划中的困惑和焦虑</span></div>
            </div>
            <p class="welcome-hint">你可以直接告诉我你的专业和求职目标，或点击下方快捷操作开始。</p>
            <div class="welcome-quick-actions">
              <button v-for="a in QUICK_ACTIONS" :key="a.label" class="wqa-btn" @click="sendQuickMessage(a.message)">{{ a.label }}</button>
            </div>
            <!-- 游客提示暂时隐藏
            <div class="guest-notice" v-if="!userStore.isLoggedIn">
              <div class="notice-icon">ℹ️</div>
              <div class="notice-content">
                <p><strong>游客模式</strong></p>
                <p>当前为游客模式，部分功能受限：简历解析、画像展示、报告生成等核心功能需要登录后使用。</p>
                <button class="login-hint-btn" @click="$router.push('/login')">
                  立即登录，解锁完整功能
                </button>
              </div>
            </div>
            -->
          </div>
          
          <div 
            v-for="msg in messages" 
            :key="msg.id" 
            :class="['message', msg.role]"
          >
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
              <button 
                v-if="msg.failed" 
                class="retry-btn" 
                @click="retryMessage(msg.id, msg.content)"
              >
                🔄 重试
              </button>
            </div>
          </div>
          
          <div v-if="streaming" class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(streamBuffer)"></div>
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="currentState === 'REPORT_REVIEW'" class="report-ready-banner">
          <p>✅ 您的职业规划报告已就绪</p>
          <router-link to="/report" class="view-report-btn">查看完整报告 →</router-link>
        </div>

        <div class="input-area">
          <div class="quick-actions">
            <button v-for="a in QUICK_ACTIONS" :key="a.label" class="quick-btn" @click="sendQuickMessage(a.message)">
              {{ a.label.replace(/^[^\s]+\s/, '') }}
            </button>
          </div>
          
          <div class="input-row">
            <textarea
              v-model="inputText"
              placeholder="输入消息，Enter发送，Shift+Enter换行..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="streaming"
              rows="1"
              ref="inputRef"
            ></textarea>
            <button 
              class="send-btn" 
              @click="sendMessage" 
              :disabled="!inputText.trim() || streaming"
              aria-label="发送消息"
            >
              {{ streaming ? '...' : '发送' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { useCrewStore } from '../stores/useCrewStore'
import { useRoute } from 'vue-router'
import { useSSE } from '../composables/useSSE'
import { chatApi } from '../api/chat'
import { crewApi } from '../api/crew'
import { STATE_STEPS, QUICK_ACTIONS, STATE_LABELS } from '../constants'
import { sanitizeHtml } from '../utils/sanitize'
import AgentStatusPanel from '../components/AgentStatusPanel.vue'

const userStore = useUserStore()
const crewStore = useCrewStore()
const route = useRoute()
const { streaming, buffer: streamBuffer, stateChange, emotionData, sendMessageStream } = useSSE()

const messages = ref<any[]>([])
const inputText = ref('')
const sessionId = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const crewAIEnabled = ref(false)
const sessionHistory = ref<{ id: string; title: string; updatedAt: string; messageCount: number }[]>([])


const currentState = computed(() => stateChange.value?.to || 'GREETING')

const currentStepIndex = computed(() => {
  return STATE_STEPS.findIndex(s => s.key === currentState.value)
})

const currentStateLabel = computed(() => {
  return STATE_LABELS[currentState.value] || { icon: '🤖', text: '对话进行中', color: '#6b7280' }
})

function formatMessage(content: string): string {
  if (!content) return ''
  const formatted = content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
  return sanitizeHtml(formatted)
}

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getEmotionClass(label: string): string {
  const emotionMap: Record<string, string> = {
    'positive': 'positive',
    'neutral': 'neutral',
    'negative': 'negative',
    'anxious': 'anxious',
    'confident': 'confident',
  }
  return emotionMap[label] || 'neutral'
}

async function checkCrewAIStatus() {
  try {
    const status = await crewApi.getStatus()
    crewAIEnabled.value = status.crewai_installed && status.llm_configured
  } catch {
    crewAIEnabled.value = false
  }
}

function getAgentStatesForPanel() {
  const states: Record<string, 'idle' | 'running' | 'completed' | 'failed'> = {}
  for (const [key, state] of Object.entries(crewStore.agentStates)) {
    states[key] = state.status
  }
  return states
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function startNewSession() {
  try {
    const result = await chatApi.createSession(userStore.studentId || undefined)
    sessionId.value = result.session_id
    messages.value = []
    
    if (result.messages && result.messages.length > 0) {
      messages.value = result.messages
    }
    
    await loadSessionHistory()
    Message.success('新对话已开始')
  } catch (e: any) {
    Message.error('创建对话失败: ' + (e.message || '未知错误'))
  }
}

async function loadSessionHistory() {
  try {
    const sessions = await chatApi.listSessions(userStore.studentId || undefined)
    sessionHistory.value = sessions.slice(0, 10)
  } catch (e) {
  }
}

async function loadSession(sessionIdToLoad: string) {
  try {
    const session = await chatApi.getSession(sessionIdToLoad)
    sessionId.value = session.session_id
    messages.value = session.messages || []
    await scrollToBottom()
  } catch (e: any) {
    Message.error('加载会话失败: ' + (e.message || '未知错误'))
  }
}

function formatSessionTime(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const pinnedSessions = ref<Set<string>>(new Set())

function loadPinnedSessions() {
  try {
    const saved = localStorage.getItem('pinned_sessions')
    if (saved) {
      pinnedSessions.value = new Set(JSON.parse(saved))
    }
  } catch {
    pinnedSessions.value = new Set()
  }
}

function savePinnedSessions() {
  localStorage.setItem('pinned_sessions', JSON.stringify([...pinnedSessions.value]))
}

function isPinned(sessionId: string): boolean {
  return pinnedSessions.value.has(sessionId)
}

function togglePin(sessionId: string) {
  if (isPinned(sessionId)) {
    pinnedSessions.value.delete(sessionId)
    Message.success('已取消置顶')
  } else {
    pinnedSessions.value.add(sessionId)
    Message.success('已置顶')
  }
  savePinnedSessions()
}

const sortedSessionHistory = computed(() => {
  const pinned = sessionHistory.value.filter(s => isPinned(s.id))
  const unpinned = sessionHistory.value.filter(s => !isPinned(s.id))
  return [...pinned, ...unpinned]
})

async function confirmDelete(sessionIdToDelete: string) {
  const confirmed = confirm('确定要删除这个对话吗？此操作不可恢复。')
  if (!confirmed) return
  
  try {
    await chatApi.deleteSession(sessionIdToDelete)
    sessionHistory.value = sessionHistory.value.filter(s => s.id !== sessionIdToDelete)
    pinnedSessions.value.delete(sessionIdToDelete)
    savePinnedSessions()
    if (sessionId.value === sessionIdToDelete) {
      sessionId.value = ''
      messages.value = []
    }
    Message.success('对话已删除')
  } catch (e: any) {
    Message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

async function sendMessage() {
  const content = inputText.value.trim()
  if (!content || streaming.value) return
  
  if (!sessionId.value) {
    await startNewSession()
    if (!sessionId.value) return
  }
  
  const userMsgId = Date.now().toString()
  messages.value.push({
    id: userMsgId,
    role: 'user',
    content,
    timestamp: new Date().toISOString(),
  })
  
  inputText.value = ''
  await scrollToBottom()
  
  try {
    await sendMessageStream(
      sessionId.value,
      content,
      () => {
        scrollToBottom()
      },
      (fullResponse) => {
        messages.value.push({
          id: Date.now().toString(),
          role: 'assistant',
          content: fullResponse,
          timestamp: new Date().toISOString(),
        })
        scrollToBottom()
      }
    )
  } catch (e: any) {
    // 标记用户消息为失败，允许重试
    const msgIndex = messages.value.findIndex(m => m.id === userMsgId)
    if (msgIndex !== -1) {
      messages.value[msgIndex] = {
        ...messages.value[msgIndex],
        failed: true,
        error: e.message || '未知错误',
      }
    }
    Message.error('发送失败，点击消息重试')
  }
}

async function retryMessage(msgId: string, content: string) {
  // 移除失败的消息
  messages.value = messages.value.filter(m => m.id !== msgId)
  // 重新发送
  inputText.value = content
  await sendMessage()
}

function sendQuickMessage(text: string) {
  inputText.value = text
  sendMessage()
}

onMounted(async () => {
  loadPinnedSessions()
  checkCrewAIStatus()
  await loadSessionHistory()
  // 若从匹配页携带 job 参数跳转，自动创建带匹配上下文的新 session
  const jobFromMatch = route.query.job as string | undefined
  if (jobFromMatch && !sessionId.value) {
    try {
      const result = await chatApi.createSession(userStore.studentId || undefined, jobFromMatch)
      sessionId.value = result.session_id
      messages.value = []
    } catch (e) {
    }
  }
  scrollToBottom()
})

watch(streaming, () => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  background: #f8fafc;
}

.chat-container {
  display: flex;
  height: calc(100vh - 0px);
}

.sidebar {
  width: 260px;
  background: white;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.sidebar-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 20px;
  color: #1a1a2e;
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  opacity: 0.5;
  transition: all 0.3s;
}

.step-item.active {
  opacity: 1;
}

.step-item.done {
  opacity: 0.8;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  transition: all 0.3s;
}

.step-item.active .step-dot {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.step-item.done .step-dot {
  background: #52c41a;
  color: white;
}

.step-label {
  font-size: 14px;
  color: #333;
}

.emotion-section {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  margin-bottom: 20px;
}

.emotion-section h4 {
  font-size: 13px;
  color: #666;
  margin: 0 0 8px;
}

.emotion-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.emotion-badge.positive {
  background: #f6ffed;
  color: #52c41a;
}

.emotion-badge.neutral {
  background: #f0f0f0;
  color: #666;
}

.emotion-badge.negative {
  background: #fff1f0;
  color: #f5222d;
}

.emotion-badge.anxious {
  background: #fff7e6;
  color: #fa8c16;
}

.emotion-badge.confident {
  background: #e6f7ff;
  color: #1890ff;
}

.stats-section {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  margin-bottom: 20px;
}

.stats-section h4 {
  font-size: 13px;
  color: #666;
  margin: 0 0 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 13px;
  color: #666;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

.sidebar-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  background: #f8fafc;
  color: #333;
  border: 1px solid #eee;
}

.action-btn:hover {
  background: #f0f0f0;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.state-indicator-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fff;
  border-left: 3px solid #6b7280;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
  color: #374151;
  transition: border-left-color 0.3s ease;
}
.state-icon { font-size: 15px; }
.state-text { font-weight: 500; }
.state-thinking { color: #9ca3af; letter-spacing: 2px; animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0.3 } }

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-message {
  text-align: center;
  padding: 40px 20px;
}

.welcome-sub {
  font-size: 15px;
  color: #444;
  margin: 12px 0 16px;
  line-height: 1.6;
}

.welcome-features {
  display: inline-flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
  background: #f8f9ff;
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 16px;
}

.wf-item {
  font-size: 14px;
  color: #555;
  display: flex;
  align-items: center;
  gap: 8px;
}

.welcome-hint {
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.welcome-quick-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.wqa-btn {
  padding: 8px 18px;
  border-radius: 20px;
  border: 1.5px solid #667eea;
  background: white;
  color: #667eea;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.wqa-btn:hover {
  background: #667eea;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.welcome-message h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1a1a2e;
}

.welcome-message p {
  font-size: 15px;
  color: #666;
  margin-bottom: 20px;
}

.welcome-message ul {
  list-style: none;
  padding: 0;
  text-align: left;
  max-width: 300px;
  margin: 0 auto;
}

.welcome-message li {
  padding: 10px 16px;
  background: white;
  border-radius: 10px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-content {
  max-width: 70%;
  background: white;
  padding: 14px 18px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-text {
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
}

.message-time {
  font-size: 11px;
  color: #999;
  margin-top: 6px;
}

.message.user .message-time {
  color: rgba(255, 255, 255, 0.7);
}

.typing-indicator {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #667eea;
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.input-area {
  padding: 20px 24px;
  background: white;
  border-top: 1px solid #eee;
}

.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.quick-btn {
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f8fafc;
  color: #667eea;
  border: 1px solid #e5e5e5;
}

.quick-btn:hover {
  background: #f0f4ff;
  border-color: #667eea;
}

.input-row {
  display: flex;
  gap: 12px;
}

.input-row textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  font-size: 15px;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
}

.input-row textarea:focus {
  border-color: #667eea;
}

.send-btn {
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.report-ready-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 16px;
  margin: 0 16px 12px;
  text-align: center;
}

.report-ready-banner p {
  margin: 0 0 10px;
  color: #15803d;
  font-weight: 500;
}

.view-report-btn {
  display: inline-block;
  padding: 8px 20px;
  background: #16a34a;
  color: #fff;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  font-size: 14px;
  transition: background 0.2s;
}

.view-report-btn:hover {
  background: #15803d;
}

.history-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.history-section h4 {
  font-size: 13px;
  color: #666;
  margin: 0 0 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.history-item:hover {
  background: #f0f4ff;
  border-color: #667eea;
}

.history-item.active {
  background: #f0f4ff;
  border-color: #667eea;
}

.history-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    height: auto;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid #eee;
    overflow-y: auto;
    padding: 16px;
  }
  
  .sidebar.collapsed {
    max-height: 60px;
    overflow: hidden;
  }
  
  .progress-steps {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .step-item {
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  
  .step-dot {
    width: 24px;
    height: 24px;
    font-size: 11px;
  }
  
  .step-label {
    font-size: 11px;
  }
  
  .chat-main {
    flex: 1;
    min-height: 60vh;
  }
  
  .messages-container {
    padding: 16px;
  }
  
  .welcome-message {
    padding: 20px 16px;
  }
  
  .welcome-icon {
    font-size: 48px;
  }
  
  .welcome-message h2 {
    font-size: 20px;
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .input-area {
    padding: 12px 16px;
  }
  
  .quick-actions {
    flex-wrap: wrap;
  }
  
  .quick-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
  
  .input-row textarea {
    font-size: 14px;
    padding: 10px 12px;
  }
  
  .send-btn {
    padding: 10px 16px;
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    padding: 12px;
    max-height: 35vh;
  }
  
  .emotion-section,
  .stats-section {
    padding: 12px;
  }
  
  .history-section {
    margin-top: 12px;
    padding-top: 12px;
  }
  
  .history-list {
    max-height: 150px;
  }
  
  .sidebar-actions {
    flex-direction: row;
    gap: 8px;
  }
  
  .action-btn {
    flex: 1;
    justify-content: center;
  }
  
  .message-avatar {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }
  
  .message-content {
    padding: 10px 14px;
  }
  
  .message-text {
    font-size: 14px;
  }
}
</style>
