<template>
  <div class="tenants">
    <header class="hd"><h1>🏛️ 租户管理</h1><p class="u-muted">学校入驻与下钻</p></header>

    <!-- 开通新校 -->
    <AppCard>
      <SectionTitle title="开通新学校" sub="建租户 + 初始管理员（之后由该 admin 自管）" />
      <div class="onboard">
        <a-input v-model="nt.name" placeholder="学校名称" size="small" />
        <a-input v-model="nt.tenant_id" placeholder="学校代码（可空，自动生成）" size="small" />
        <a-input v-model="nt.admin_username" placeholder="管理员用户名" size="small" />
        <a-input-password v-model="nt.admin_password" placeholder="管理员密码" size="small" />
        <AppButton size="sm" :loading="creating" @click="onboard">开通</AppButton>
      </div>
    </AppCard>

    <!-- 学校列表 -->
    <AppCard>
      <SectionTitle title="已入驻学校" :sub="`${tenants.length} 所`" />
      <div class="table" v-if="tenants.length">
        <div class="tr th"><span>学校</span><span>代码</span><span>学生</span><span>教师</span><span>均竞争力</span><span>提升%</span><span></span></div>
        <div class="tr" v-for="t in tenants" :key="t.id">
          <span class="u-ellipsis">{{ t.name }}</span>
          <span class="u-faint">{{ t.id }}</span>
          <span>{{ t.student_count }}</span>
          <span>{{ t.teacher_count }}</span>
          <span>{{ t.avg_competitiveness }}</span>
          <span :class="t.improvement_pct !== null && t.improvement_pct >= 0 ? 'u-up' : 'u-down'">
            {{ t.improvement_pct === null ? '—' : (t.improvement_pct >= 0 ? '+' : '') + t.improvement_pct + '%' }}
          </span>
          <button class="drill" @click="drill(t.id)">下钻 →</button>
        </div>
      </div>
      <EmptyState v-else text="还没有学校" />
    </AppCard>

    <!-- 下钻面板 -->
    <AppCard v-if="detail">
      <SectionTitle :title="`${detail.tenant.name} · 学生名册`" :sub="`${detail.students.length} 人`">
        <template #action><button class="close" @click="detail = null">收起</button></template>
      </SectionTitle>
      <div class="table">
        <div class="tr2 th"><span>姓名</span><span>完整度</span><span>竞争力</span></div>
        <div class="tr2" v-for="s in detail.students" :key="s.student_id">
          <span class="u-ellipsis">{{ s.name || '未命名' }}</span><span>{{ s.completeness }}%</span><span>{{ s.competitiveness }}</span>
        </div>
      </div>
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { platformApi, type TenantStat, type TenantDetail } from '@/api/platform'

const tenants = ref<TenantStat[]>([])
const detail = ref<TenantDetail | null>(null)
const creating = ref(false)
const nt = reactive({ name: '', tenant_id: '', admin_username: '', admin_password: '' })

async function load() {
  try { tenants.value = (await platformApi.tenants()).tenants } catch { /* toasted */ }
}
async function onboard() {
  if (!nt.name.trim() || !nt.admin_username.trim() || !nt.admin_password.trim()) { Message.warning('填学校名 + 管理员账号'); return }
  creating.value = true
  try {
    await platformApi.createTenant(nt.name.trim(), nt.admin_username.trim(), nt.admin_password.trim(), nt.tenant_id.trim() || undefined)
    Message.success('学校已开通')
    nt.name = ''; nt.tenant_id = ''; nt.admin_username = ''; nt.admin_password = ''
    await load()
  } catch { /* toasted */ } finally { creating.value = false }
}
async function drill(id: string) {
  try { detail.value = await platformApi.tenantDetail(id) } catch { /* toasted */ }
}

onMounted(load)
</script>

<style scoped>
.tenants { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.onboard { display: grid; grid-template-columns: 1.4fr 1.2fr 1.2fr 1.2fr auto; gap: 8px; align-items: center; }
.table { font-size: var(--fz-2); }
.tr { display: grid; grid-template-columns: 1.5fr 1fr 0.6fr 0.6fr 0.9fr 0.9fr auto; gap: var(--sp-2); padding: 9px 0; border-bottom: 1px solid var(--c-border); align-items: center; }
.tr2 { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: var(--sp-2); padding: 8px 0; border-bottom: 1px solid var(--c-border); }
.th { color: var(--c-text-3); font-weight: 700; border-bottom: 2px solid var(--c-border-2); }
.drill { border: none; background: none; color: var(--c-primary); cursor: pointer; font-size: var(--fz-2); }
.close { border: none; background: none; color: var(--c-text-3); cursor: pointer; font-size: var(--fz-2); }
@media (max-width: 860px) { .onboard { grid-template-columns: 1fr 1fr; } }
</style>
