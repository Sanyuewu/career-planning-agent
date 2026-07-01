<template>
  <div class="advisor">
    <header class="hd">
      <div>
        <h1>🤖 AI 职业顾问</h1>
        <p class="u-muted">随便问，或让我帮你跑一遍完整规划</p>
      </div>
      <AppButton size="sm" :disabled="busy || !studentId" @click="runPlanning">🚀 帮我做完整规划</AppButton>
    </header>

    <div ref="scroller" class="stream">
      <div v-if="!messages.length" class="welcome">
        <div class="w-emoji">💬</div>
        <p class="u-muted">问我「我适合什么岗位」「前端要补什么技能」，或点右上角一键规划</p>
        <div class="quick">
          <button v-for="q in QUICK" :key="q" @click="send(q)">{{ q }}</button>
        </div>
      </div>

      <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
        <!-- 普通文本 -->
        <div v-if="m.kind === 'text'" class="bubble">{{ m.content || '…' }}</div>

        <!-- 规划管线 -->
        <div v-else class="pipeline">
          <div class="pl-head">
            <span class="pl-stage">{{ stageLabel(m.pipeline!.state) }}</span>
            <span v-if="!m.pipeline!.done" class="pl-dot"></span>
          </div>
          <div v-for="(s, i) in m.pipeline!.steps" :key="i" class="pl-step" :class="s.type">
            <span class="pl-ico">{{ stepIcon(s.type) }}</span>{{ s.text }}
          </div>
          <div v-if="m.pipeline!.live" class="pl-live">{{ m.pipeline!.live }}</div>
          <div v-if="m.pipeline!.done && m.pipeline!.summary" class="pl-summary">{{ m.pipeline!.summary }}</div>
        </div>
      </div>
    </div>

    <div class="composer">
      <a-input v-model="input" placeholder="问点什么…" size="large" :disabled="busy" @keyup.enter="() => send()" />
      <AppButton :loading="busy" :disabled="!input.trim()" @click="() => send()">发送</AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import AppButton from '@/design/components/AppButton.vue'
import { advisorApi } from '@/api/advisor'
import { useSession } from '@/stores/session'

const session = useSession()
const studentId = session.studentId

const QUICK = ['我适合什么岗位？', '前端开发要补哪些技能？', '我的竞争力怎么样？']
const STAGE: Record<string, string> = {
  GREETING: '开始', PROFILING: '分析画像', MATCHING: '人岗匹配',
  PLANNING: '路径规划', REPORTING: '生成报告', DONE: '完成',
}

interface PipelineState { state: string; live: string; steps: { type: string; text: string }[]; done: boolean; summary: string }
interface Msg { id: string; role: 'user' | 'assistant'; kind: 'text' | 'pipeline'; content: string; pipeline?: PipelineState }

const messages = ref<Msg[]>([])
const input = ref('')
const busy = ref(false)
const scroller = ref<HTMLElement | null>(null)
let sessionId = ''

function uid() { return Math.random().toString(36).slice(2) }
function stageLabel(s: string) { return STAGE[s] || s || '进行中' }
function stepIcon(t: string) { return ({ thought: '💭', tool: '🔧', result: '✅', blocked: '⛔', error: '⚠️' } as Record<string, string>)[t] || '·' }

async function scrollDown() { await nextTick(); scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' }) }

async function ensureSession() {
  if (sessionId) return sessionId
  const s = await advisorApi.createSession(studentId || undefined)
  sessionId = s.session_id
  return sessionId
}

async function send(preset?: string) {
  const text = (preset ?? input.value).trim()
  if (!text || busy.value) return
  input.value = ''
  messages.value.push({ id: uid(), role: 'user', kind: 'text', content: text })
  const am: Msg = { id: uid(), role: 'assistant', kind: 'text', content: '' }
  messages.value.push(am)
  busy.value = true
  await scrollDown()
  try {
    const sid = await ensureSession()
    advisorApi.streamChat(sid, text, (ev) => {
      if (ev.token) am.content += ev.token
      else if (ev.full_response !== undefined) am.content = ev.full_response
      else if (ev.error) am.content = '出错了：' + ev.error
      scrollDown()
    }, { onDone: () => { busy.value = false }, onError: (e) => { am.content = am.content || ('连接失败：' + e); busy.value = false } })
  } catch { am.content = '会话创建失败'; busy.value = false }
}

function runPlanning() {
  if (busy.value || !studentId) return
  const pipe: PipelineState = { state: 'GREETING', live: '', steps: [], done: false, summary: '' }
  messages.value.push({ id: uid(), role: 'assistant', kind: 'pipeline', content: '', pipeline: pipe })
  busy.value = true
  scrollDown()
  advisorApi.runAgent(studentId, '帮我完成职业规划：分析画像、推荐岗位、规划发展路径、生成报告', (ev) => {
    switch (ev.type) {
      case 'state': pipe.state = ev.state; break
      case 'token': pipe.live += ev.delta || ''; break
      case 'thought_end': if (pipe.live.trim()) pipe.steps.push({ type: 'thought', text: pipe.live.trim() }); pipe.live = ''; break
      case 'tool_call': pipe.steps.push({ type: 'tool', text: `调用 ${ev.name}` }); break
      case 'tool_result': if (ev.summary) pipe.steps.push({ type: 'result', text: ev.summary }); break
      case 'blocked': pipe.steps.push({ type: 'blocked', text: ev.reason || '受阻' }); break
      case 'done': pipe.done = true; pipe.summary = ev.content || ''; pipe.state = 'DONE'; break
      case 'error': pipe.steps.push({ type: 'error', text: ev.content || '出错' }); break
    }
    scrollDown()
  }, { onDone: () => { busy.value = false }, onError: (e) => { pipe.steps.push({ type: 'error', text: e }); busy.value = false } })
}

onMounted(() => { /* 懒创建会话 */ })
</script>

<style scoped>
.advisor { display: flex; flex-direction: column; height: calc(100vh - var(--topbar-h) - var(--sp-12)); }
.hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--sp-4); }
.hd h1 { font-size: var(--fz-5); font-weight: 800; }
.hd p { margin-top: 2px; font-size: var(--fz-2); }
.stream { flex: 1; overflow-y: auto; padding: var(--sp-2) 2px; display: flex; flex-direction: column; gap: var(--sp-4); }
.welcome { text-align: center; margin: auto; }
.w-emoji { font-size: 44px; }
.quick { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: var(--sp-4); }
.quick button { border: 1px solid var(--c-border-2); background: var(--c-surface); border-radius: var(--r-full);
  padding: 7px 14px; font-size: var(--fz-2); cursor: pointer; transition: all .18s; }
.quick button:hover { border-color: var(--c-primary); color: var(--c-primary); }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 76%; padding: 11px 15px; border-radius: var(--r-lg); font-size: var(--fz-3); line-height: 1.7; white-space: pre-wrap; }
.msg.user .bubble { background: var(--grad-brand); color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: var(--c-surface); border: 1px solid var(--c-border); border-bottom-left-radius: 4px; }
.pipeline { max-width: 80%; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--r-lg); padding: var(--sp-4); }
.pl-head { display: flex; align-items: center; gap: 8px; margin-bottom: var(--sp-3); }
.pl-stage { background: var(--c-primary-weak); color: var(--c-primary); border-radius: var(--r-full); padding: 3px 12px; font-size: var(--fz-1); font-weight: 700; }
.pl-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--c-primary); animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: .3; } }
.pl-step { font-size: var(--fz-2); color: var(--c-text-2); padding: 3px 0; }
.pl-step .pl-ico { margin-right: 6px; }
.pl-step.error { color: var(--c-danger); }
.pl-live { font-size: var(--fz-2); color: var(--c-text-3); font-style: italic; padding: 4px 0; }
.pl-summary { margin-top: var(--sp-3); padding-top: var(--sp-3); border-top: 1px solid var(--c-border); font-size: var(--fz-3); line-height: 1.7; white-space: pre-wrap; }
.composer { display: flex; gap: var(--sp-3); padding-top: var(--sp-4); }
.composer :deep(.arco-input-wrapper) { flex: 1; }
</style>
