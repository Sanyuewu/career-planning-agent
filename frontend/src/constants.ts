// 前端全局常量文件
// 所有硬编码标签、映射、下拉选项统一在此管理，组件内不得重复定义

// ── 学生画像 ──────────────────────────────────────────────

/** 竞争力等级中文显示（后端返回 A/B/C/D） */
export const COMPETITIVENESS_LEVEL_MAP: Record<string, string> = {
  A: '优秀',
  B: '较强',
  C: '一般',
  D: '薄弱',
}

/** 竞争力等级说明 */
export const COMPETITIVENESS_LEVEL_DESC: Record<string, string> = {
  A: '前15% - 表现优秀',
  B: '前35% - 良好水平',
  C: '前65% - 一般水平',
  D: '需要进一步提升',
}

/** 软技能维度中文标签 */
export const SOFT_SKILL_LABELS: Record<string, string> = {
  communication: '沟通能力',
  learning_ability: '学习能力',
  stress_resistance: '抗压能力',
  innovation: '创新能力',
  teamwork: '团队协作',
  leadership: '领导力',
  problem_solving: '问题解决',
}

// ── 首页岗位筛选 ──────────────────────────────────────────

/** 岗位分类列表 */
export const JOB_CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'backend', label: '后端开发' },
  { key: 'frontend', label: '前端开发' },
  { key: 'data', label: '数据分析' },
  { key: 'product', label: '产品运营' },
  { key: 'design', label: '设计类' },
]

/** 岗位分类关键词映射 */
export const CATEGORY_MAPPING: Record<string, string[]> = {
  backend: ['Java', 'Python', 'Go', '后端', '服务端', '架构'],
  frontend: ['前端', 'Vue', 'React', 'Web', 'H5', '小程序'],
  data: ['数据', '分析', '算法', '机器学习', 'AI', '挖掘'],
  product: ['产品', '运营', '项目经理', '需求'],
  design: ['设计', 'UI', 'UX', '视觉', '交互'],
}

/** 市场需求旺盛度标签 */
export const DEMAND_LABELS: Record<string, string> = {
  high: '需求旺盛',
  medium: '需求稳定',
  low: '需求一般',
}

// ── AI 对话顾问 ───────────────────────────────────────────

/** 对话状态进度步骤 */
export const STATE_STEPS = [
  { key: 'GREETING', label: '开始对话' },
  { key: 'RESUME_INGEST', label: '简历信息' },
  { key: 'PORTRAIT_FILLING', label: '补全画像' },
  { key: 'INTENT_CONFIRM', label: '确认意向' },
  { key: 'MATCH_ANALYSIS', label: '匹配分析' },
  { key: 'REPORT_GENERATING', label: '生成报告' },
  { key: 'REPORT_REVIEW', label: '报告确认' },
]

/** FSM 状态对应的进度标签（用于对话区顶部状态条） */
export const STATE_LABELS: Record<string, { icon: string; text: string; color: string }> = {
  GREETING:          { icon: '👋', text: '开始对话', color: '#6b7280' },
  RESUME_INGEST:     { icon: '📄', text: '正在录入简历信息', color: '#3b82f6' },
  PORTRAIT_FILLING:  { icon: '🎨', text: '正在完善您的职业画像', color: '#8b5cf6' },
  INTENT_CONFIRM:    { icon: '🎯', text: '确认求职意向', color: '#f59e0b' },
  MATCH_ANALYSIS:    { icon: '⚡', text: 'AI 正在深度分析匹配度', color: '#10b981' },
  CAREER_PLANNING:   { icon: '🗺️', text: '规划职业发展路径', color: '#10b981' },
  CAREER_GUIDANCE:   { icon: '💡', text: '提供个性化职业建议', color: '#10b981' },
  REPORT_GENERATING: { icon: '📝', text: '正在生成职业规划报告', color: '#f59e0b' },
  REPORT_REVIEW:     { icon: '✅', text: '报告已就绪，可查看或调优', color: '#10b981' },
  REPORT_REFINE:     { icon: '✏️', text: '正在润色报告内容', color: '#f59e0b' },
  EMOTION_SUPPORT:   { icon: '💬', text: '情绪疏导中，随时聊聊', color: '#ec4899' },
  END:               { icon: '🎉', text: '规划对话已完成', color: '#6b7280' },
}

/** 快速操作按钮（欢迎屏和输入框下方共用） */
export const QUICK_ACTIONS = [
  { label: '🔍 分析我的画像', message: '我想了解自己的职业画像和竞争力分析' },
  { label: '🎯 推荐岗位', message: '帮我推荐适合我的岗位方向' },
  { label: '📊 生成报告', message: '我想生成职业规划报告' },
]

// ── 企业端表单选项 ────────────────────────────────────────

/** 公司规模选项 */
export const COMPANY_SIZE_OPTIONS = [
  '1-50人',
  '51-200人',
  '201-500人',
  '501-2000人',
  '2000人以上',
]

/** 学历要求选项（岗位发布 & 候选人筛选） */
export const DEGREE_OPTIONS = ['大专', '本科', '硕士', '博士']

/** 经验要求选项 */
export const EXPERIENCE_OPTIONS = ['1-3年', '3-5年', '5-10年']

// ── 管理端筛选选项 ────────────────────────────────────────

/** 用户角色筛选 */
export const ROLE_FILTER_OPTIONS = [
  { label: '全部', value: '' },
  { label: '学生', value: 'student' },
  { label: '企业', value: 'company' },
  { label: '管理员', value: 'admin' },
]

/** 日志级别筛选 */
export const LOG_LEVEL_OPTIONS = [
  { label: '全部', value: '' },
  { label: 'ERROR', value: 'error' },
  { label: 'WARN', value: 'warn' },
  { label: 'INFO', value: 'info' },
]

/** 技能学习资源推荐 */
export const SKILL_RESOURCES: Record<string, { name: string; resources: { title: string; url: string; type: string }[] }> = {
  'Python': {
    name: 'Python',
    resources: [
      { title: 'Python官方教程', url: 'https://docs.python.org/zh-cn/3/tutorial/', type: '官方文档' },
      { title: '廖雪峰Python教程', url: 'https://www.liaoxuefeng.com/wiki/1016959663602400', type: '中文教程' },
    ]
  },
  'Java': {
    name: 'Java',
    resources: [
      { title: 'Java官方教程', url: 'https://docs.oracle.com/javase/tutorial/', type: '官方文档' },
      { title: '廖雪峰Java教程', url: 'https://www.liaoxuefeng.com/wiki/1252599548343744', type: '中文教程' },
    ]
  },
  'MySQL': {
    name: 'MySQL',
    resources: [
      { title: 'MySQL官方文档', url: 'https://dev.mysql.com/doc/', type: '官方文档' },
      { title: 'MySQL教程', url: 'https://www.runoob.com/mysql/mysql-tutorial.html', type: '中文教程' },
    ]
  },
  'Redis': {
    name: 'Redis',
    resources: [
      { title: 'Redis官方文档', url: 'https://redis.io/documentation', type: '官方文档' },
      { title: 'Redis教程', url: 'https://www.runoob.com/redis/redis-tutorial.html', type: '中文教程' },
    ]
  },
  'Docker': {
    name: 'Docker',
    resources: [
      { title: 'Docker官方文档', url: 'https://docs.docker.com/', type: '官方文档' },
      { title: 'Docker教程', url: 'https://www.runoob.com/docker/docker-tutorial.html', type: '中文教程' },
    ]
  },
  'Git': {
    name: 'Git',
    resources: [
      { title: 'Git官方文档', url: 'https://git-scm.com/doc', type: '官方文档' },
      { title: 'Git教程', url: 'https://www.runoob.com/git/git-tutorial.html', type: '中文教程' },
    ]
  },
  'Linux': {
    name: 'Linux',
    resources: [
      { title: 'Linux教程', url: 'https://www.runoob.com/linux/linux-tutorial.html', type: '中文教程' },
    ]
  },
  'Vue': {
    name: 'Vue',
    resources: [
      { title: 'Vue官方文档', url: 'https://cn.vuejs.org/guide/introduction.html', type: '官方文档' },
    ]
  },
  'React': {
    name: 'React',
    resources: [
      { title: 'React官方文档', url: 'https://react.dev/learn', type: '官方文档' },
    ]
  },
  'TypeScript': {
    name: 'TypeScript',
    resources: [
      { title: 'TypeScript官方文档', url: 'https://www.typescriptlang.org/docs/', type: '官方文档' },
    ]
  },
  'Spring': {
    name: 'Spring',
    resources: [
      { title: 'Spring官方文档', url: 'https://spring.io/guides', type: '官方文档' },
    ]
  },
  '机器学习': {
    name: '机器学习',
    resources: [
      { title: '机器学习教程', url: 'https://www.coursera.org/learn/machine-learning', type: '在线课程' },
    ]
  },
  '数据分析': {
    name: '数据分析',
    resources: [
      { title: '数据分析教程', url: 'https://www.kaggle.com/learn', type: '在线课程' },
    ]
  },
}

/** 常见岗位技能模板 */
export const JOB_SKILL_TEMPLATES: Record<string, string[]> = {
  'Java后端开发': ['Java', 'Spring', 'MySQL', 'Redis', 'Git', 'Linux', 'Docker'],
  'Python后端开发': ['Python', 'Django', 'Flask', 'MySQL', 'Redis', 'Git', 'Linux'],
  '前端开发': ['JavaScript', 'TypeScript', 'Vue', 'React', 'HTML', 'CSS', 'Git'],
  '数据分析师': ['Python', 'SQL', 'Excel', '数据分析', '机器学习'],
  '算法工程师': ['Python', '机器学习', '深度学习', 'SQL', 'Linux'],
  '测试工程师': ['Python', 'Java', 'Selenium', 'JMeter', 'Git', 'Linux'],
  '运维工程师': ['Linux', 'Docker', 'Kubernetes', 'Python', 'MySQL', 'Redis'],
  '产品经理': ['Axure', 'SQL', '数据分析', 'Excel', 'PPT'],
}

// ── 通用配置 ──────────────────────────────────────────────

/** 用户角色 */
export const USER_ROLES = {
  STUDENT: 'student',
  COMPANY: 'company',
  ADMIN: 'admin',
} as const

export type UserRole = typeof USER_ROLES[keyof typeof USER_ROLES]

/** 匹配等级（含颜色和分数阈值） */
export const MATCH_LEVELS = {
  A: { label: '高度匹配', color: '#52c41a', minScore: 80 },
  B: { label: '较好匹配', color: '#1890ff', minScore: 65 },
  C: { label: '基本匹配', color: '#faad14', minScore: 50 },
  D: { label: '差距较大', color: '#ff4d4f', minScore: 0 },
} as const

export type MatchLevel = keyof typeof MATCH_LEVELS

/** 学历等级分值 */
export const DEGREE_LEVELS = {
  '博士': 100,
  '硕士': 85,
  '本科': 70,
  '大专': 50,
  '高中': 30,
} as const

/** 年级选项 */
export const GRADE_OPTIONS = [
  { value: '大一', label: '大一' },
  { value: '大二', label: '大二' },
  { value: '大三', label: '大三' },
  { value: '大四', label: '大四' },
  { value: '研一', label: '研一' },
  { value: '研二', label: '研二' },
  { value: '研三', label: '研三' },
] as const

/** 文件上传限制 */
export const FILE_UPLOAD_LIMITS = {
  MAX_SIZE: 10 * 1024 * 1024,
  MAX_TEXT_SIZE: 100 * 1024,
  ALLOWED_TYPES: ['pdf', 'docx', 'png', 'jpeg', 'jpg'],
  ALLOWED_MIME_TYPES: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
  ],
} as const

/** 分页默认值 */
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const

/** 本地存储键名 */
export const STORAGE_KEYS = {
  TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_INFO: 'user_info',
  THEME: 'app_theme',
  RESUME_DRAFT: 'resume_form_draft',
} as const

/** 消息提示文案 */
export const MESSAGES = {
  SUCCESS: {
    LOGIN: '登录成功',
    REGISTER: '注册成功',
    LOGOUT: '已退出登录',
    SAVE: '保存成功',
    DELETE: '删除成功',
    UPDATE: '更新成功',
    UPLOAD: '上传成功',
    FEEDBACK: '感谢您的反馈！',
  },
  ERROR: {
    LOGIN: '用户名或密码错误',
    NETWORK: '网络错误，请稍后重试',
    TIMEOUT: '请求超时，请稍后重试',
    UNAUTHORIZED: '请先登录',
    FORBIDDEN: '权限不足',
    NOT_FOUND: '资源不存在',
    SERVER: '服务器错误，请稍后重试',
    VALIDATION: '请检查输入信息',
    FILE_TYPE: '不支持的文件类型',
    FILE_SIZE: '文件大小超出限制',
  },
  WARNING: {
    UNSAVED_CHANGES: '有未保存的更改',
    SESSION_EXPIRED: '登录已过期，请重新登录',
  },
} as const

/** 正则表达式 */
export const REGEX = {
  PHONE: /^1[3-9]\d{9}$/,
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  USERNAME: /^[a-zA-Z0-9_\u4e00-\u9fa5]{2,32}$/,
  PASSWORD: /^.{6,64}$/,
} as const

/** 超时时间（毫秒） */
export const TIMEOUTS = {
  API_REQUEST: 30000,
  CHAT_STREAM: 60000,
  DEBOUNCE: 300,
  THROTTLE: 1000,
} as const

/** 兴趣领域选项（学生画像编辑） */
export const INTEREST_OPTIONS = [
  '编程/技术开发',
  '数据分析',
  '人工智能/机器学习',
  '前端/UI设计',
  '运营/市场营销',
  '法律/知识产权',
  '金融/财务',
  '项目/产品管理',
]

export const CITY_OPTIONS = [
  '北京', '上海', '广州', '深圳', '杭州',
  '成都', '武汉', '南京', '西安', '苏州',
  '重庆', '天津', '长沙', '郑州', '合肥',
  '厦门', '青岛', '无锡', '宁波', '东莞',
]

export const CULTURE_OPTIONS = [
  '初创灵活文化',
  '大厂规范体系',
  '国企/外资稳定',
  '创业期高成长',
  '扁平化管理',
  '狼性竞争文化',
  '注重工作生活平衡',
  '技术驱动氛围',
]

/** 图表颜色 */
export const CHART_COLORS = [
  '#667eea', '#764ba2', '#f093fb', '#f5576c',
  '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
  '#fa709a', '#fee140',
] as const
