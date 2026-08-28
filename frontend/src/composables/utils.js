// ============================================
// 纯函数与常量工具模块（无内部状态依赖，可安全复用/测试）
// 从 useFraudLens.js 抽出，行为不变
// ============================================

/** 默认作案手法流程（演示用） */
export const defaultMethodFlow = [
  { title: '获取信任', desc: '冒充客服，准确报出受害人信息' },
  { title: '制造恐慌', desc: '声称账户异常，影响征信' },
  { title: '诱导转账', desc: '要求转账至"安全账户"验证' },
  { title: '完成诈骗', desc: '资金到账后立即失联' }
]

/** 默认关键词（演示用） */
export const defaultKeywords = ['冒充客服', '征信诈骗', '安全账户', '转账验证']

/** 团伙头像图标池 */
export const gangIcons = ['🦈', '🐺', '🦊', '🐍', '🐯', '🦅']

/** 登录页粒子动画样式（随机生成） */
export function getParticleStyle(i) {
  const size = Math.random() * 4 + 2
  const duration = Math.random() * 20 + 10
  const delay = Math.random() * 10
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`
  }
}

/** 风险等级 → 标签类型 */
export function getRiskType(level) {
  const map = { S: 'danger', A: 'warning', B: 'info', C: 'success' }
  return map[level] || 'info'
}

/** 事件类型 → 标签类型 */
export function getEventType(type) {
  const map = { '作案': 'danger', '转移': 'warning', '洗钱': 'warning', '活动': 'info' }
  return map[type] || 'info'
}

/** 特征索引 → 图标 */
export function getFeatureIcon(idx) {
  const icons = ['💬', '💰', '🔗', '🌍', '🔧', '🎯']
  return icons[idx] || '📊'
}

/** 解析团伙涉案金额（兼容多种字段格式） */
export function parseRawAmount(g) {
  if (g.total_amount_value != null && g.total_amount_value > 0) return g.total_amount_value
  const raw = g.total_amount_involved || g.total_amount || g.amount || ''
  if (typeof raw === 'number') return raw
  const match = raw.match(/[\d.]+/)
  const num = match ? parseFloat(match[0]) : 0
  return raw.includes('万') ? num * 10000 : num
}

/** 金额格式化（万单位缩写） */
export function formatAmountRaw(num) {
  if (num >= 10000) {
    return '¥' + (num / 10000).toFixed(1) + '万'
  }
  return '¥' + num.toLocaleString()
}

/** 案件金额显示文本：优先 amount_value（元）；为 0 时回退后端原始 amount 字符串 */
export function formatCaseAmountText(c) {
  const v = Number(c.amount_value) || 0
  if (v > 0) return formatAmountRaw(v)
  return c.amount != null && c.amount !== '' ? String(c.amount) : '-'
}
