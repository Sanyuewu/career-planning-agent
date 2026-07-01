<template>
  <div class="config">
    <header class="hd"><h1>⚙️ 院校配置</h1><p class="u-muted">本校的匹配权重 / 岗位库 / 报告模板</p></header>

    <!-- 四维权重（红线） -->
    <AppCard>
      <SectionTitle title="四维匹配权重" sub="默认即系统红线，非必要不改" />
      <div v-if="weightsChanged" class="warn">
        ⚠️ 你修改了匹配权重——这会改变全校所有学生的人岗匹配结果。请确认是教学需要。
        <button class="reset" @click="resetWeights">恢复默认</button>
      </div>
      <div class="weights">
        <label v-for="w in WEIGHT_KEYS" :key="w.key" class="wfield">
          <span>{{ w.label }}</span>
          <a-input-number v-model="weights[w.key]" :min="0" :max="1" :step="0.05" size="small" />
        </label>
      </div>
      <div class="wsum u-faint">合计 {{ weightSum.toFixed(2) }}（保存时自动归一）</div>
    </AppCard>

    <!-- 岗位库 -->
    <AppCard>
      <SectionTitle title="岗位库白名单" sub="留空 = 开放全部岗位；填写则只允许这些岗位参与匹配" />
      <a-textarea v-model="jobLibText" placeholder="每行一个岗位名，留空表示全部" :auto-size="{ minRows: 3, maxRows: 8 }" />
    </AppCard>

    <!-- 报告模板 -->
    <AppCard>
      <SectionTitle title="报告定制要求" sub="追加到生成报告的提示词（如校训、特色专业方向）" />
      <a-textarea v-model="reportExtra" placeholder="例如：结合我校『新工科』培养方向给出建议" :auto-size="{ minRows: 3, maxRows: 8 }" />
    </AppCard>

    <div class="actions">
      <AppButton size="lg" :loading="saving" @click="save">保存配置</AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import { adminApi } from '@/api/staff'

const DEFAULT_W: Record<string, number> = { basic: 0.25, skill: 0.35, quality: 0.25, potential: 0.15 }
const WEIGHT_KEYS = [
  { key: 'basic', label: '基础要求' }, { key: 'skill', label: '专业技能' },
  { key: 'quality', label: '职业素养' }, { key: 'potential', label: '发展潜力' },
]

const weights = reactive<Record<string, number>>({ ...DEFAULT_W })
const jobLibText = ref('')
const reportExtra = ref('')
const saving = ref(false)

const weightSum = computed(() => WEIGHT_KEYS.reduce((s, w) => s + (weights[w.key] || 0), 0))
const weightsChanged = computed(() => WEIGHT_KEYS.some(w => Math.abs((weights[w.key] || 0) - DEFAULT_W[w.key]) > 1e-6))

function resetWeights() { Object.assign(weights, DEFAULT_W) }

onMounted(async () => {
  try {
    const cfg = await adminApi.getTenantConfig()
    if (cfg.match_weights) Object.assign(weights, { ...DEFAULT_W, ...cfg.match_weights })
    if (cfg.job_library?.length) jobLibText.value = cfg.job_library.join('\n')
    reportExtra.value = cfg.report_extra_instructions || ''
  } catch { /* toasted */ }
})

async function save() {
  saving.value = true
  try {
    const jobs = jobLibText.value.split('\n').map(s => s.trim()).filter(Boolean)
    await adminApi.putTenantConfig({
      match_weights: weightsChanged.value ? { ...weights } : null,   // 未改 = 用红线默认
      job_library: jobs.length ? jobs : null,
      report_extra_instructions: reportExtra.value.trim(),
    })
    Message.success('配置已保存')
  } catch { /* toasted */ } finally { saving.value = false }
}
</script>

<style scoped>
.config { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.warn { background: #fff4e6; color: #c2630a; border-radius: var(--r-md); padding: 10px 14px; font-size: var(--fz-2); margin-bottom: var(--sp-4); }
.reset { margin-left: 10px; border: none; background: none; color: var(--c-primary); cursor: pointer; text-decoration: underline; }
.weights { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--sp-4); }
.wfield { display: flex; flex-direction: column; gap: 6px; font-size: var(--fz-2); color: var(--c-text-2); }
.wsum { margin-top: var(--sp-3); font-size: var(--fz-2); }
.actions { text-align: center; }
@media (max-width: 720px) { .weights { grid-template-columns: 1fr 1fr; } }
</style>
