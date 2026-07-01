<template>
  <div class="manage">
    <header class="hd"><h1>🏫 组织管理</h1><p class="u-muted">班级 · 账号 · 带班 · 分班（仅本校）</p></header>

    <div class="grid2">
      <!-- 班级 -->
      <AppCard>
        <SectionTitle title="班级" :sub="`${classes.length} 个`" />
        <div class="row-add">
          <a-input v-model="newClass" placeholder="新建班级名…" size="small" @keyup.enter="addClass" />
          <AppButton size="sm" variant="soft" :loading="busy.cls" @click="addClass">新建</AppButton>
        </div>
        <div v-for="c in classes" :key="c.id" class="line">
          <span>{{ c.name }}</span>
          <span class="u-faint">{{ c.student_count }} 人</span>
          <button class="del" @click="delClass(c)">删除</button>
        </div>
        <EmptyState v-if="!classes.length" text="还没有班级" />
      </AppCard>

      <!-- 建账号 -->
      <AppCard>
        <SectionTitle title="新建账号" sub="教师 / 管理员 / 学生" />
        <a-input v-model="nu.username" placeholder="用户名" size="small" class="fld" />
        <a-input-password v-model="nu.password" placeholder="初始密码" size="small" class="fld" />
        <a-select v-model="nu.role" size="small" class="fld">
          <a-option value="teacher">教师</a-option>
          <a-option value="admin">管理员</a-option>
          <a-option value="student">学生</a-option>
        </a-select>
        <AppButton size="sm" block :loading="busy.usr" @click="addUser">创建账号</AppButton>
      </AppCard>
    </div>

    <!-- 教师带班 -->
    <AppCard>
      <SectionTitle title="教师带班" />
      <div class="row-add">
        <a-select v-model="tc.teacher_id" placeholder="选教师" size="small" style="flex:1">
          <a-option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.username }}</a-option>
        </a-select>
        <a-select v-model="tc.class_id" placeholder="选班级" size="small" style="flex:1">
          <a-option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</a-option>
        </a-select>
        <AppButton size="sm" variant="soft" :loading="busy.tc" @click="assignTC">指派</AppButton>
      </div>
      <div v-for="l in teacherClasses" :key="l.teacher_id + l.class_id" class="line">
        <span>{{ l.teacher_name }}</span><span class="u-faint">带</span><span>{{ l.class_name }}</span>
        <button class="del" @click="unassignTC(l)">解除</button>
      </div>
      <EmptyState v-if="!teacherClasses.length" text="还没有带班关系" />
    </AppCard>

    <!-- 学生分班 -->
    <AppCard>
      <SectionTitle title="学生分班" :sub="`${roster.length} 名学生`" />
      <div v-for="s in roster" :key="s.student_id" class="line">
        <span class="u-ellipsis" style="flex:1">{{ s.name || '未命名' }}（竞争力 {{ s.competitiveness }}）</span>
        <a-select :model-value="studentClass[s.student_id] || ''" placeholder="未分班" size="mini"
                  style="width:140px" @change="(v:any) => assignStudent(s.student_id, v)">
          <a-option value="">未分班</a-option>
          <a-option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</a-option>
        </a-select>
      </div>
      <EmptyState v-if="!roster.length" text="暂无学生" />
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import AppCard from '@/design/components/AppCard.vue'
import AppButton from '@/design/components/AppButton.vue'
import SectionTitle from '@/design/components/SectionTitle.vue'
import EmptyState from '@/design/components/EmptyState.vue'
import { adminApi, type ClassItem, type UserItem, type TeacherClassItem } from '@/api/staff'

const classes = ref<ClassItem[]>([])
const users = ref<UserItem[]>([])
const teacherClasses = ref<TeacherClassItem[]>([])
const roster = ref<Array<{ student_id: string; name: string; competitiveness: number; class_id?: string | null }>>([])

const teachers = computed(() => users.value.filter(u => u.role === 'teacher'))
const studentClass = reactive<Record<string, string>>({})

const newClass = ref('')
const nu = reactive({ username: '', password: '', role: 'teacher' })
const tc = reactive({ teacher_id: '', class_id: '' })
const busy = reactive({ cls: false, usr: false, tc: false })

async function loadAll() {
  const [c, u, l, r] = await Promise.allSettled([
    adminApi.listClasses(), adminApi.listUsers(), adminApi.listTeacherClasses(), adminApi.roster(),
  ])
  if (c.status === 'fulfilled') classes.value = c.value
  if (u.status === 'fulfilled') {
    users.value = u.value
    u.value.forEach(usr => { if (usr.student_id) studentClass[usr.student_id] = usr.class_id || '' })
  }
  if (l.status === 'fulfilled') teacherClasses.value = l.value
  if (r.status === 'fulfilled') roster.value = r.value.students
}

async function addClass() {
  if (!newClass.value.trim()) return
  busy.cls = true
  try { await adminApi.createClass(newClass.value.trim()); newClass.value = ''; await loadAll(); Message.success('已新建') }
  catch { /* toasted */ } finally { busy.cls = false }
}
async function delClass(c: ClassItem) {
  try { await adminApi.deleteClass(c.id); await loadAll(); Message.success('已删除') } catch { /* toasted */ }
}
async function addUser() {
  if (!nu.username.trim() || !nu.password.trim()) { Message.warning('填用户名和密码'); return }
  busy.usr = true
  try { await adminApi.createUser(nu.username.trim(), nu.password.trim(), nu.role); nu.username = ''; nu.password = ''; await loadAll(); Message.success('账号已创建') }
  catch { /* toasted */ } finally { busy.usr = false }
}
async function assignTC() {
  if (!tc.teacher_id || !tc.class_id) { Message.warning('选教师和班级'); return }
  busy.tc = true
  try { await adminApi.assignTeacherClass(tc.teacher_id, tc.class_id); await loadAll(); Message.success('已指派') }
  catch { /* toasted */ } finally { busy.tc = false }
}
async function unassignTC(l: TeacherClassItem) {
  try { await adminApi.unassignTeacherClass(l.teacher_id, l.class_id); await loadAll() } catch { /* toasted */ }
}
async function assignStudent(sid: string, classId: string) {
  try { await adminApi.assignStudentClass(sid, classId || null); studentClass[sid] = classId; await loadAll(); Message.success('已更新分班') }
  catch { /* toasted */ }
}

onMounted(loadAll)
</script>

<style scoped>
.manage { display: flex; flex-direction: column; gap: var(--sp-5); }
.hd h1 { font-size: var(--fz-6); font-weight: 800; }
.hd p { margin-top: 4px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); }
.row-add { display: flex; gap: 8px; margin-bottom: var(--sp-3); }
.fld { margin-bottom: var(--sp-3); }
.line { display: flex; align-items: center; gap: var(--sp-3); padding: 8px 0; border-bottom: 1px solid var(--c-border); font-size: var(--fz-3); }
.line > span:first-child { font-weight: 600; }
.del { margin-left: auto; border: none; background: none; color: var(--c-text-3); cursor: pointer; font-size: var(--fz-2); }
.del:hover { color: var(--c-danger); }
@media (max-width: 860px) { .grid2 { grid-template-columns: 1fr; } }
</style>
