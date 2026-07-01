<template>
  <div class="wrap">
    <header class="hd">
      <h1>上传你的简历</h1>
      <p class="u-muted">AI 会把它解析成七维职业画像，作为你成长的起点</p>
    </header>

    <AppCard>
      <div v-if="!parsing" class="drop" :class="{ over }"
           @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop"
           @click="pick">
        <input ref="fileInput" type="file" hidden accept=".pdf,.docx,.txt,.doc" @change="onChange" />
        <div class="drop-ico">📄</div>
        <div class="drop-main">拖拽简历到这里，或<span class="link">点击选择</span></div>
        <div class="drop-sub u-faint">支持 PDF / Word / TXT</div>
      </div>

      <div v-else class="parsing">
        <div class="spin"></div>
        <div class="p-title">正在解析简历…</div>
        <div class="p-sub u-faint">提取技能、经历、证书，并评估七维能力</div>
      </div>
    </AppCard>

    <p class="tip u-faint">解析需要调用 AI，通常 10–30 秒。</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import { portraitApi } from '@/api/portrait'
import { useSession } from '@/stores/session'
import { useStudent } from '@/stores/student'

const router = useRouter()
const session = useSession()
const student = useStudent()

const fileInput = ref<HTMLInputElement | null>(null)
const parsing = ref(false)
const over = ref(false)

function pick() { fileInput.value?.click() }
function onChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) handle(f)
}
function onDrop(e: DragEvent) {
  over.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) handle(f)
}

async function handle(file: File) {
  parsing.value = true
  try {
    const res = await portraitApi.parse(file)
    const p = res.result
    if (!p?.student_id) throw new Error('解析结果为空')
    session.setStudentId(p.student_id, p.basic_info?.name)
    student.setPortrait(p)
    await student.loadAll(true)
    Message.success('画像已生成')
    router.push('/journey/portrait')
  } catch {
    /* http 已弹错误 */
  } finally {
    parsing.value = false
  }
}
</script>

<style scoped>
.wrap { max-width: 640px; margin: 0 auto; }
.hd { text-align: center; margin-bottom: var(--sp-6); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 6px; }
.drop { border: 2px dashed var(--c-border-2); border-radius: var(--r-lg); padding: var(--sp-12) var(--sp-6);
  text-align: center; cursor: pointer; transition: all .2s; }
.drop:hover, .drop.over { border-color: var(--c-primary); background: var(--c-primary-weak); }
.drop-ico { font-size: 46px; }
.drop-main { margin-top: var(--sp-3); font-size: var(--fz-4); font-weight: 600; }
.link { color: var(--c-primary); }
.drop-sub { margin-top: 6px; font-size: var(--fz-2); }
.parsing { text-align: center; padding: var(--sp-12) var(--sp-6); }
.p-title { font-size: var(--fz-4); font-weight: 700; margin-top: var(--sp-4); }
.p-sub { margin-top: 6px; }
.spin { width: 38px; height: 38px; margin: 0 auto; border: 3px solid var(--c-border);
  border-top-color: var(--c-primary); border-radius: 50%; animation: s .8s linear infinite; }
@keyframes s { to { transform: rotate(360deg); } }
.tip { text-align: center; margin-top: var(--sp-4); font-size: var(--fz-2); }
</style>
