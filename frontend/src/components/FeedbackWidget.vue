<template>
  <div class="feedback-widget">
    <div class="feedback-row" v-if="!submitted">
      <span class="feedback-label">这个分析对你有帮助吗？</span>
      <button class="thumb-btn thumb-yes" @click="submit(1)" :disabled="submitting">
        👍 有帮助
      </button>
      <button class="thumb-btn thumb-no" @click="submit(0)" :disabled="submitting">
        👎 没帮助
      </button>
    </div>
    <div class="feedback-done" v-else>
      <span class="done-icon">✓</span>
      <span class="done-text">感谢反馈！</span>
      <span class="satisfaction-rate" v-if="stats.satisfaction_pct !== null">
        {{ stats.satisfaction_pct }}% 的用户觉得准确
        <span class="stats-count">（{{ stats.total }} 次反馈）</span>
      </span>
    </div>
    <div class="feedback-stats-only" v-if="!submitted && stats.total > 0">
      <span class="stats-preview">{{ stats.satisfaction_pct }}% 的用户觉得有帮助（{{ stats.total }} 次）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { request } from '../api/http'
import { useUserStore } from '../stores/useUserStore'

const props = defineProps<{
  targetType: string
  targetId: string
}>()

const emit = defineEmits<{
  (e: 'low-rating'): void
  (e: 'feedback', rating: number, comment: string): void
}>()

const userStore = useUserStore()
const submitted = ref(false)
const submitting = ref(false)
const stats = ref<{ total: number; positive: number; satisfaction_pct: number | null }>({
  total: 0,
  positive: 0,
  satisfaction_pct: null,
})

onMounted(async () => {
  // 检查本地是否已提交过
  if (localStorage.getItem(`fb_${props.targetId}`)) {
    submitted.value = true
  }
  // 加载聚合统计
  try {
    const data = await request.get<any>(`/feedback/stats/${props.targetType}?target_id=${encodeURIComponent(props.targetId)}`)
    stats.value = data
  } catch {
    // 静默失败
  }
})

async function submit(rating: number) {
  if (submitting.value) return
  submitting.value = true
  try {
    await request.post('/feedback', {
      student_id: userStore.studentId || null,
      target_type: props.targetType,
      target_id: props.targetId,
      rating,
    })
    // 乐观更新统计
    const newTotal = stats.value.total + 1
    const newPositive = stats.value.positive + rating
    stats.value = {
      total: newTotal,
      positive: newPositive,
      satisfaction_pct: Math.round(newPositive / newTotal * 100),
    }
    localStorage.setItem(`fb_${props.targetId}`, '1')
    submitted.value = true
    Message.success('感谢您的反馈！')
    if (rating === 0) {
      emit('low-rating')
    }
  } catch (e: any) {
    if (e?.status === 409 || e?.response?.status === 409) {
      localStorage.setItem(`fb_${props.targetId}`, '1')
      submitted.value = true
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.feedback-widget {
  background: white;
  border-radius: 12px;
  padding: 14px 18px;
  border: 1px solid #e8e8e8;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.feedback-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.feedback-label {
  font-size: 13px;
  color: #555;
  flex-shrink: 0;
}

.thumb-btn {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  background: white;
  color: #555;
  transition: all 0.2s;
  font-weight: 500;
}

.thumb-btn:hover:not(:disabled) {
  border-color: #667eea;
  color: #667eea;
  background: #f0f4ff;
}

.thumb-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-done {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.done-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #52c41a;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.done-text {
  font-size: 13px;
  color: #555;
}

.satisfaction-rate {
  font-size: 13px;
  font-weight: 600;
  color: #389e0d;
}

.stats-count {
  font-weight: 400;
  color: #888;
  font-size: 12px;
}

.feedback-stats-only {
  border-top: 1px dashed #f0f0f0;
  padding-top: 6px;
}

.stats-preview {
  font-size: 12px;
  color: #aaa;
}
</style>
