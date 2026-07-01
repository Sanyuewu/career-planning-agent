// Next-Step 引擎 —— 引导式产品的心脏：依据学生当前状态算出"唯一的下一步"。
// 纯函数，无副作用；输入来自 stores/student，输出驱动主页 NextStepCard。
import type { Portrait } from '@/api/portrait'
import type { ProgressResponse } from '@/api/progress'
import type { MatchResult } from '@/api/match'

export interface NextStep {
  key: string
  icon: string
  title: string
  desc: string
  cta: string
  to: string
}

export function computeNextStep(args: {
  hasStudent: boolean
  portrait: Portrait | null
  progress: ProgressResponse | null
  matches: MatchResult[]
}): NextStep {
  const { hasStudent, portrait, progress, matches } = args

  // 1) 无画像 → 上传简历
  if (!hasStudent || !portrait) {
    return { key: 'upload', icon: '📄', title: '上传你的简历',
      desc: '解析成七维职业画像，开启你的成长规划', cta: '上传简历', to: '/journey/upload' }
  }

  // 2) 画像不完整 → 补全
  if ((portrait.completeness || 0) < 70) {
    return { key: 'profile', icon: '🎨', title: '补全你的画像',
      desc: `当前完整度 ${Math.round(portrait.completeness || 0)}%，补全后匹配更准`,
      cta: '去补全', to: '/journey/portrait' }
  }

  // 3) 没做过匹配 → 匹配
  if (!matches.length) {
    return { key: 'match', icon: '⚡', title: '做一次人岗匹配',
      desc: '看看你最适合哪些岗位，差距在哪', cta: '开始匹配', to: '/journey/match' }
  }

  const best = matches.reduce((a, b) => (b.overall_score > a.overall_score ? b : a))
  const actions = progress?.actions

  // 4a) 有逾期行动 → 优先催（闭环自旋，不静默等用户）
  if (actions?.available && (actions.overdue || 0) > 0) {
    return { key: 'overdue', icon: '⏰', title: `有 ${actions.overdue} 项行动逾期`,
      desc: '补上进度，别让你的计划停下来', cta: '去赶上', to: '/growth' }
  }

  // 4) 有行动计划但未完成 → 推进行动
  if (actions?.available && (actions.done || 0) < (actions.total || 0)) {
    return { key: 'action', icon: '✅', title: '完成你的行动计划',
      desc: `已完成 ${actions.done}/${actions.total} 项，离目标更近一步`, cta: '去成长页', to: '/growth' }
  }

  // 5) 还没生成报告（无行动计划）→ 生成报告
  if (!actions?.available) {
    return { key: 'report', icon: '📝', title: '生成职业发展报告',
      desc: `基于你与「${best.job_title || '目标岗位'}」的匹配，给你完整规划`,
      cta: '生成报告', to: '/journey/report' }
  }

  // 6) 有缺口 → 补技能
  const gap = best.gap_skills?.[0]?.skill || progress?.match_progress?.still_missing?.[0]
  if (gap) {
    return { key: 'skill', icon: '🎯', title: `补齐「${gap}」`,
      desc: `补上后与「${best.job_title || '目标岗位'}」的匹配会更高`, cta: '查看成长', to: '/growth' }
  }

  // 7) 一切就绪 → 保持节奏
  return { key: 'maintain', icon: '🎉', title: '保持你的节奏',
    desc: '规划进展良好，定期回来复评，见证自己变强', cta: '查看成长', to: '/growth' }
}
