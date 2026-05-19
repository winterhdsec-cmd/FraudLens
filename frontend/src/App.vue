<template>
  <div class="police-system-layout">
    <div v-if="!store.isLoggedIn" class="login-overlay">
      <div class="login-container tech-card">
        <div class="login-header">
          <div class="login-logo-wrapper">
            <div class="login-logo-ring"></div>
            <div class="login-logo-icon">🛡️</div>
          </div>
          <h2 class="login-title">反诈情报分析系统</h2>
          <p class="login-subtitle">AI INTELLIGENT SYSTEM</p>
        </div>
        <div class="login-form">
          <div class="login-field">
            <span class="login-field-icon">👤</span>
            <el-input
              v-model="loginForm.username"
              placeholder="用户名"
              size="large"
              class="login-input"
              @keyup.enter="handleLogin"
            />
          </div>
          <div class="login-field">
            <span class="login-field-icon">🔑</span>
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              size="large"
              class="login-input"
              show-password
              @keyup.enter="handleLogin"
            />
          </div>
          <div v-if="loginError" class="login-error">{{ loginError }}</div>
          <el-button
            class="login-btn"
            type="primary"
            size="large"
            :loading="loginLoading"
            @click="handleLogin"
          >
            <span>{{ loginLoading ? '验证中...' : '登 录' }}</span>
          </el-button>
        </div>
        <div class="login-footer">
          <span class="login-footer-text">智能研判平台 v2.0</span>
        </div>
      </div>
    </div>
    <div class="particle-bg">
      <div v-for="i in 60" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>
    <div class="grid-overlay"></div>
    <div class="scan-line"></div>

    <!-- 分析进度弹窗 -->
    <el-dialog v-model="showProgress" :close-on-click-modal="false" :show-close="false" width="420px" class="progress-dialog">
      <div class="progress-body">
        <div class="progress-animation">
          <span class="pulse-dot"></span>
        </div>
        <div class="progress-title">正在智能研判</div>
        <div class="progress-status">{{ progressMessage }}</div>
        <el-progress :percentage="progressPercent" :stroke-width="6" striped striped-flow />
        <div class="progress-hint">AI 正在分析案情数据，请耐心等待</div>
      </div>
    </el-dialog>

    <!-- 研判完成弹窗 -->
    <el-dialog v-model="showResult" width="480px" class="result-dialog">
      <div class="result-body">
        <div class="result-icon">✅</div>
        <div class="result-title">研判完成</div>
        <div class="result-stats">
          <div class="result-stat">
            <div class="rs-value">{{ resultStats.cases }}</div>
            <div class="rs-label">发现案件</div>
          </div>
          <div class="result-stat">
            <div class="rs-value">{{ resultStats.gangs }}</div>
            <div class="rs-label">识别团伙</div>
          </div>
          <div class="result-stat">
            <div class="rs-value">{{ resultStats.time }}</div>
            <div class="rs-label">用时</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showResult = false" size="large">留在当前页</el-button>
        <el-button type="primary" @click="goToResults" size="large">查看分析结果 →</el-button>
      </template>
    </el-dialog>

    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-icon-wrapper">
          <div class="logo-ring"></div>
          <div class="logo-icon">🛡️</div>
        </div>
        <h2>反诈情报分析</h2>
        <span class="sub-title">AI INTELLIGENT SYSTEM</span>
        <div class="logo-badge">
          <span class="badge-dot"></span>
          <span>智能研判平台</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="side-menu" @select="handleMenuSelect">
        <div class="menu-group">
          <div class="menu-group-title">数据采集</div>
          <el-menu-item index="input">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📝</span>
                <span class="menu-text">文本录入</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="upload">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📂</span>
                <span class="menu-text">文件上传</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="api">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔌</span>
                <span class="menu-text">API接入</span>
                
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">系统总览</div>
          <el-menu-item index="dashboard">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📊</span>
                <span class="menu-text">数据看板</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="alerts">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔔</span>
                <span class="menu-text">预警中心</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">研判分析</div>
          <el-menu-item index="overview">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📊</span>
                <span class="menu-text">案件总览</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="case-detail">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔍</span>
                <span class="menu-text">案件详情</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="groups">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">👥</span>
                <span class="menu-text">团伙画像</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="details">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📈</span>
                <span class="menu-text">深度分析</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="network">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🕸️</span>
                <span class="menu-text">关联网络</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">深度研判</div>
          <el-menu-item index="capital-flow">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">💰</span>
                <span class="menu-text">资金流向</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="dispatch">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📋</span>
                <span class="menu-text">预警派单</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="key-persons">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">👤</span>
                <span class="menu-text">重点人员</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">输出报告</div>
          <el-menu-item index="report">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📄</span>
                <span class="menu-text">报告生成</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">系统管理</div>
          <el-menu-item index="admin">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">⚙️</span>
                <span class="menu-text">系统管理</span>
              </div>
            </template>
          </el-menu-item>
        </div>
      </el-menu>

      <div class="system-status">
        <div class="status-row">
          <div class="status-indicator">
            <div class="status-dot"></div>
            <span>系统运行正常</span>
          </div>
          <div class="version">v2.0</div>
        </div>
        <div class="status-details">
          <div class="status-item">
            <span class="status-label">AI引擎</span>
            <span class="status-value online">在线</span>
          </div>
          <div class="status-item">
            <span class="status-label">数据库</span>
            <span class="status-value online">已连接</span>
          </div>
        </div>
        <div class="logout-area" v-if="store.isLoggedIn">
          <el-button class="logout-btn" size="small" @click="handleLogout">
            <span>🚪</span> 退出登录
          </el-button>
        </div>
      </div>
    </aside>

    <main class="main-content" v-loading="loading" element-loading-text="AI 正在进行深度研判分析...">
      <div class="content-wrapper">
        <RouterView />
      </div>
</main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, provide } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import NetworkGraph from './components/NetworkGraph.vue'
import { store } from './store.js'
import {
  startAnalysis as apiStartAnalysis,
  fetchCases,
  fetchGangs,
  fetchGangDetail,
  connectSocket,
  disconnectSocket,
  login as apiLogin,
  getDashboardData,
  getActiveAlerts,
  resolveAlert,
  importCSV,
  importExcel,
  ocrImage,
  extractText
} from './api.js'

const router = useRouter()

const activeMenu = computed(() => router.currentRoute.value.name || 'input')
const loading = ref(false)
const showProgress = ref(false)
const showResult = ref(false)
const progressPercent = ref(0)
const progressMessage = ref('正在初始化...')
const resultStats = ref({ cases: 0, gangs: 0, time: '0s' })
const analysisStartTime = ref(0)
const inputText = ref('')
const uploadedImages = ref([])
const gangs = ref([])
const cases = ref([])
const selectedGang = ref(null)
const selectedCase = ref(null)
const viewMode = ref('card')
const gangSearchKeyword = ref('')
const riskFilter = ref('')
const detailTab = ref('overview')
const networkView = ref('all')
const generatingReport = ref(false)

const parsedReport = computed(() => {
  const desc = selectedCase.value?.description || ''
  if (!desc || !desc.includes('### Part A')) return { partA: '', partB: null }
  const parts = desc.split('### Part B')
  const partA = parts[0].replace('### Part A: 《案件研判结论》', '').trim()
  let partB = null
  if (parts[1]) {
    const jsonStr = parts[1].replace('结构化数据 (JSON)', '').replace('```json', '').replace('```', '').trim()
    try { partB = JSON.parse(jsonStr) } catch (e) { partB = null }
  }
  return { partA, partB }
})

// P1 features state
const flowSearchCaseId = ref('')
const capitalFlows = ref([])
const flowGraphData = ref(null)
const dispatchOrders = ref([])
const dispatchStatusFilter = ref('')
const showCreateDispatch = ref(false)
const keyPersons = ref([])
const personSearch = ref('')
const personTypeFilter = ref('')
const showCreatePerson = ref(false)

const dashboardData = ref({
  total_cases: null,
  total_gangs: null,
  total_amount: null,
  active_alerts: null,
  risk_distribution: [],
  status_distribution: [],
  top_scam_types: [],
  monthly_trend: [],
  recent_cases: []
})
const dashboardLoading = ref(false)

const alerts = ref([])
const alertsLoading = ref(false)
const resolvingAlert = ref(null)

const dashboardRiskChartRef = ref(null)
const dashboardStatusChartRef = ref(null)
const dashboardBarChartRef = ref(null)
const dashboardTrendChartRef = ref(null)
let dashboardRiskChart = null
let dashboardStatusChart = null
let dashboardBarChart = null
let dashboardTrendChart = null

const reportConfig = ref({
  type: 'gang',
  gangId: '',
  format: 'pdf',
  includeTimeline: true,
  includeMoney: true,
  includeNetwork: true,
  includeSuggestion: true
})
const reportPreview = ref(false)

const loginForm = ref({ username: '', password: '' })
const loginLoading = ref(false)
const loginError = ref('')

const handleLogin = async () => {
  if (!loginForm.value.username.trim() || !loginForm.value.password.trim()) {
    loginError.value = '请输入用户名和密码'
    return
  }
  loginLoading.value = true
  loginError.value = ''
  try {
    const data = await apiLogin(loginForm.value.username, loginForm.value.password)
    if (data.success) {
      store.login(data.user || { username: loginForm.value.username }, data.access_token, data.refresh_token)
      loginForm.value = { username: '', password: '' }
      ElMessage.success('登录成功')
      router.push({ name: 'input' })
    } else {
      loginError.value = data.message || '登录失败，请重试'
    }
  } catch (err) {
    loginError.value = err.response?.data?.message || err.message || '登录失败，请检查网络连接'
  } finally {
    loginLoading.value = false
  }
}

const handleLogout = () => {
  store.logout()
  ElMessage.success('已安全退出')
}

const apiSources = ref({
  bank: { connected: false, records: 1256, lastSync: '10分钟前' },
  police: { connected: false, records: 89, lastSync: '5分钟前' },
  antiFraud: { connected: false, records: 3567, lastSync: '刚刚' }
})
const apiDataPreview = ref([])

const pieChartRef = ref(null)
const lineChartRef = ref(null)
let pieChart = null
let lineChart = null

const totalAmount = computed(() => {
  return gangs.value.reduce((sum, g) => {
    const num = parseFloat(g.amount?.replace(/[^0-9.]/g, '') || 0)
    return sum + (isNaN(num) ? 0 : num)
  }, 0)
})

const totalAmountFormatted = computed(() => {
  const amount = totalAmount.value
  if (amount >= 100) {
    return `¥${amount.toFixed(1)}万`
  }
  return `¥${amount.toFixed(2)}万`
})

const successRate = ref(92)

const textLineCount = computed(() => {
  return inputText.value.split('\n').filter(line => line.trim()).length
})

const extractedKeywords = computed(() => {
  const keywords = []
  const text = inputText.value
  if (text.includes('诈骗') || text.includes('被骗')) keywords.push('诈骗')
  if (text.includes('转账') || text.includes('汇款')) keywords.push('转账')
  if (text.includes('客服') || text.includes('京东')) keywords.push('冒充客服')
  if (text.includes('征信') || text.includes('贷款')) keywords.push('征信诈骗')
  if (text.includes('刷单') || text.includes('返利')) keywords.push('刷单诈骗')
  if (/\d{11}/.test(text)) keywords.push('手机号')
  if (/¥|万元|元/.test(text)) keywords.push('涉案金额')
  return keywords.slice(0, 6)
})

const hasTime = computed(() => /\d{4}年|\d{1,2}月|\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}/.test(inputText.value))
const hasAmount = computed(() => /¥|万元|元|\d+万/.test(inputText.value))
const hasPhone = computed(() => /\d{11}/.test(inputText.value))
const hasMethod = computed(() => /诈骗|被骗|转账|汇款|客服|征信|贷款|刷单/.test(inputText.value))

const connectedSources = computed(() => {
  return Object.values(apiSources.value).filter(s => s.connected).length
})

const hasApiData = computed(() => {
  return apiDataPreview.value.length > 0
})

const filteredGangs = computed(() => {
  let result = gangs.value
  if (gangSearchKeyword.value) {
    result = result.filter(g => g.name.includes(gangSearchKeyword.value))
  }
  if (riskFilter.value) {
    result = result.filter(g => g.riskLevel === riskFilter.value)
  }
  return result
})

const features = ref([
  { name: '诈骗话术成熟度', confidence: 92, color: '#ef4444', desc: '话术模板标准化程度' },
  { name: '资金分散程度', confidence: 85, color: '#f59e0b', desc: '资金流转层级数量' },
  { name: '成员关联密度', confidence: 78, color: '#00d4ff', desc: '团伙成员社交关系' },
  { name: '跨区域作案特征', confidence: 88, color: '#8b5cf6', desc: '跨省跨境作案能力' },
  { name: '技术手段先进性', confidence: 73, color: '#10b981', desc: '反侦察技术水平' },
  { name: '受害者画像精准度', confidence: 89, color: '#ec4899', desc: '目标人群定位能力' }
])

const relationNodes = ref([
  { id: 1, type: 'gang', icon: '👥', label: '团伙A', style: { left: '50%', top: '25%' } },
  { id: 2, type: 'case', icon: '📋', label: '案件1', style: { left: '25%', top: '45%' } },
  { id: 3, type: 'case', icon: '📋', label: '案件2', style: { left: '75%', top: '45%' } },
  { id: 4, type: 'money', icon: '💰', label: '资金', style: { left: '35%', top: '70%' } },
  { id: 5, type: 'money', icon: '💰', label: '资金', style: { left: '65%', top: '70%' } }
])
const relationLines = ref([
  { id: 1, x1: '50%', y1: '25%', x2: '25%', y2: '45%' },
  { id: 2, x1: '50%', y1: '25%', x2: '75%', y2: '45%' },
  { id: 3, x1: '25%', y1: '45%', x2: '35%', y2: '70%' },
  { id: 4, x1: '75%', y1: '45%', x2: '65%', y2: '70%' }
])

const caseEvidence = ref([
  { icon: '📱', name: '通话记录', status: '已验证' },
  { icon: '💳', name: '转账凭证', status: '已验证' },
  { icon: '📧', name: '聊天记录', status: '已验证' },
  { icon: '🖥️', name: '涉案设备', status: '核实中' }
])

const investigationSteps = ref([
  { date: '2024-03-15', title: '案件受理', description: '受害人报案，记录案情经过', status: '已完成', completed: true, current: false },
  { date: '2024-03-16', title: '初步调查', description: '调取银行流水、通话记录', status: '已完成', completed: true, current: false },
  { date: '2024-03-18', title: '案件分析', description: 'AI研判分析，关联涉案团伙', status: '已完成', completed: true, current: false },
  { date: '2024-03-20', title: '资金追踪', description: '追踪资金流向，冻结涉案账户', status: '进行中', completed: false, current: true },
  { date: '', title: '抓捕行动', description: '根据线索实施抓捕', status: '待进行', completed: false, current: false },
  { date: '', title: '案件结案', description: '移送审查起诉', status: '待进行', completed: false, current: false }
])

const defaultMethodFlow = [
  { title: '获取信任', desc: '冒充客服，准确报出受害人信息' },
  { title: '制造恐慌', desc: '声称账户异常，影响征信' },
  { title: '诱导转账', desc: '要求转账至"安全账户"验证' },
  { title: '完成诈骗', desc: '资金到账后立即失联' }
]

const defaultKeywords = ['冒充客服', '征信诈骗', '安全账户', '转账验证']

const caseTypeStats = ref([
  { name: '冒充客服诈骗', count: 45, percent: 35, color: '#ef4444' },
  { name: '刷单返利诈骗', count: 32, percent: 25, color: '#f59e0b' },
  { name: '贷款诈骗', count: 28, percent: 22, color: '#8b5cf6' },
  { name: '投资理财诈骗', count: 23, percent: 18, color: '#00d4ff' }
])

const regionStats = ref([
  { name: '广东', count: 25, percent: 30 },
  { name: '浙江', count: 18, percent: 22 },
  { name: '江苏', count: 15, percent: 18 },
  { name: '北京', count: 12, percent: 14 },
  { name: '上海', count: 10, percent: 12 }
])

const getParticleStyle = (i) => {
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

const getRiskType = (level) => {
  const map = { S: 'danger', A: 'warning', B: 'info', C: 'success' }
  return map[level] || 'info'
}

const getEventType = (type) => {
  const map = { '作案': 'danger', '转移': 'warning', '洗钱': 'warning', '活动': 'info' }
  return map[type] || 'info'
}

const getGangById = (id) => gangs.value.find(g => g.id === id)

const getFeatureIcon = (idx) => {
  const icons = ['💬', '💰', '🔗', '🌍', '🔧', '🎯']
  return icons[idx] || '📊'
}

const getReportTitle = () => {
  const titles = {
    gang: '团伙分析报告',
    case: '案件分析报告',
    comprehensive: '综合研判报告'
  }
  return titles[reportConfig.value.type] || '分析报告'
}

const handleMenuSelect = (index) => {
  router.push({ name: index })
}

const selectGang = (gang) => {
  selectedGang.value = gang
}

const viewGangDetail = (gang) => {
  selectGang(gang)
  router.push({ name: 'groups' })
}

const viewCaseDetail = (caseItem) => {
  selectedCase.value = caseItem
  router.push({ name: 'case-detail' })
}

const viewRelatedGang = (gangId) => {
  const gang = gangs.value.find(g => g.id === gangId)
  if (gang) {
    selectGang(gang)
    router.push({ name: 'groups' })
  }
}

const clearInput = () => {
  inputText.value = ''
}

const clearImages = () => {
  uploadedImages.value = []
}

const removeImage = (idx) => {
  uploadedImages.value.splice(idx, 1)
}

const loadDemo = () => {
  inputText.value = `【案情描述】
受害人王女士报警称：2024年3月15日接到自称"京东客服"电话，对方准确报出其个人信息后称其开通了"京东金条"服务，如不取消将影响征信。王女士在对方指导下通过手机银行转账至"安全账户"共计 125,800 元。

受害人李先生报警称：2024年3月18日接到同样手法诈骗，对方冒充"京东金融"客服，诱骗其转账 89,600 元。

【资金流向】
被骗资金通过多个一级账户迅速分散转入二级账户，最终在境外取现。账户信息显示开户人均为"张伟"等人，但实际控制人信息被层层掩盖。

【作案手法分析】
1. 开场白："您好，我是京东金融/京东客服，您名下有一笔账户异常..."
2. 制造恐慌："如不处理，您的征信将受到严重影响"
3. 诱导转账："请将资金转入安全账户进行验证，稍后会全额返还"
4. 消失：验证后即失联

【初步结论】
初步判断为同一诈骗团伙所为，具有"注销校园贷"类诈骗特征，建议并案侦查。`
}

const handleBeforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isText = file.type === 'text/plain' || file.name.endsWith('.csv')
  const isDocx = file.name.endsWith('.docx')
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isImage && !isText && !isDocx) {
    ElMessage.error('仅支持图片(JPG/PNG)、文本文件(TXT/CSV)或Word文档(DOCX)')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }

  if (isText) {
    const reader = new FileReader()
    reader.onload = (e) => {
      uploadedImages.value.push({
        url: '', name: file.name, type: 'text',
        content: e.target.result, _file: file
      })
    }
    reader.readAsText(file)
  } else if (isImage) {
    const reader = new FileReader()
    reader.onload = (e) => {
      uploadedImages.value.push({
        url: e.target.result, name: file.name, type: 'image',
        content: '', _file: file
      })
    }
    reader.readAsDataURL(file)
  } else {
    uploadedImages.value.push({
      url: '', name: file.name, type: 'docx',
      content: '', _file: file
    })
  }
  return false
}

const gangIcons = ['🦈', '🐺', '🦊', '🐍', '🐯', '🦅']

const formatAmount = (amount) => {
  const num = typeof amount === 'number' ? amount : parseFloat(amount) || 0
  if (num >= 10000) {
    return '¥' + (num / 10000).toFixed(1) + '万'
  }
  return '¥' + num.toLocaleString()
}

const startAnalysis = async () => {
  if (!inputText.value.trim()) return
  loading.value = true

  const sessionId = 'session_' + Date.now()
  const messages = [{ role: 'user', content: inputText.value }]

  try {
    analysisStartTime.value = Date.now()
    showProgress.value = true
    progressPercent.value = 0
    progressMessage.value = '正在初始化分析引擎...'
    connectSocket(sessionId, {
      onProgress: (data) => {
        const pct = data.progress_percent || data.progress || 0
        progressPercent.value = Math.min(pct, 99)
        progressMessage.value = data.message || data.stage_name || '分析中...'
      },
      onComplete: (data) => {
        progressPercent.value = 100
        progressMessage.value = '分析完成'
      }
    })

    const response = await apiStartAnalysis(messages, sessionId)

    if (response.success) {
      if (response.task_id) {
        progressMessage.value = '分析任务已提交到队列，请稍后查看总览页'
        progressPercent.value = 100
        setTimeout(() => {
          showProgress.value = false
          ElMessage.success('分析任务已提交，可前往案件总览查看结果')
          router.push({ name: 'overview' })
        }, 2000)
        return
      }
      gangs.value = (response.gangs || []).map((g, idx) => ({
        id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
        name: g.gang_name || '未知团伙',
        icon: gangIcons[idx % gangIcons.length],
        riskLevel: g.risk_level || 'B',
        amount: formatAmount(g.total_amount_involved),
        cases: g.total_cases || 0,
        tags: Array.isArray(g.fingerprint)
          ? g.fingerprint.filter(Boolean)
          : g.fingerprint
            ? g.fingerprint.split(/[,，、]/).map(t => t.trim()).filter(Boolean)
            : [],
        members: Array.isArray(g.network_nodes)
          ? g.network_nodes.slice(0, 6).map((n, i) => ({
              id: i + 1,
              name: n.label || n.id || '成员' + (i + 1),
              icon: '👤',
              role: n.role || n.type || '成员'
            }))
          : [],
        timeline: (g.steps || []).map(s => ({
          date: s.date || s.time || '',
          title: s.title || s.name || '',
          desc: s.description || s.desc || '',
          type: s.type || '活动'
        })),
        evidence: [],
        abilities: g.radar_data || { tech: 50, org: 50, antiDetect: 50 },
        victims: g.total_cases || 0,
        createTime: '',
        updateTime: '刚刚'
      }))

      cases.value = (response.raw_cases || []).map(c => ({
        id: c.case_id || 'C' + String(Math.random()).slice(2, 8),
        title: (c.victim || '当事人') + '被诈骗案',
        gang: c.related_gang_id || c.assigned_gang || '',
        amount: formatAmount(c.amount),
        status: c.is_error ? '待核查' : '已立案',
        date: c.extracted_entities?.date || '',
        region: c.extracted_entities?.address || '',
        type: c.scam_type || '',
        victims: 1,
        victimName: c.victim || '',
        victimGender: c.extracted_entities?.gender || '',
        victimAge: c.extracted_entities?.age || '',
        victimPhone: c.extracted_entities?.phone || '',
        victimJob: c.extracted_entities?.job || '',
        victimAddress: c.extracted_entities?.address || '',
        scamPhone: c.extracted_entities?.scam_phone || '',
        phoneLocation: c.extracted_entities?.phone_location || '',
        scamUrl: c.extracted_entities?.url || '',
        ipAddress: c.extracted_entities?.ip || '',
        description: c.ai_report || ''
      }))

      selectedCase.value = cases.value[0] || null
      const gangCount = response.gangs?.length || 0
      showProgress.value = false
      const elapsed = Math.round((Date.now() - analysisStartTime.value) / 1000)
      resultStats.value = { cases: cases.value.length, gangs: gangCount, time: elapsed > 0 ? elapsed + 's' : '< 1s' }
      showResult.value = true
    } else {
      ElMessage.error('分析失败: ' + (response.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('分析请求异常: ' + (err.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

const goToResults = () => {
  showResult.value = false
  router.push({ name: 'overview' })
}

const startImageAnalysis = async () => {
  if (!uploadedImages.value.length) return
  loading.value = true
  ElMessage.info('正在处理上传文件...')
  try {
    const texts = []
    for (const item of uploadedImages.value) {
      if (item.type === 'text') {
        texts.push(item.content || '')
      } else if (item.type === 'docx') {
        const data = await extractText(item._file)
        if (data.text) texts.push(data.text)
      } else if (item.type === 'image' && item._file) {
        const data = await ocrImage(item._file)
        if (data.text) texts.push(data.text)
      }
    }
    const allText = texts.filter(Boolean).join('\n\n---\n\n')
    if (allText) {
      inputText.value = allText
      ElMessage.success('文件处理完成，共提取 ' + allText.length + ' 个字符')
      await startAnalysis()
    } else {
      ElMessage.warning('未能从文件中提取到文字')
    }
  } catch (err) {
    ElMessage.error('文件处理失败: ' + (err.message || ''))
  } finally {
    loading.value = false
  }
}

const toggleApiSource = (source) => {
  if (apiSources.value[source].connected) {
    ElMessage.success(`${source === 'bank' ? '银行风控' : source === 'police' ? '110报警平台' : '反诈平台'}已连接`)
  }
}

const syncApiData = (source) => {
  ElMessage.success('数据同步中...')
  setTimeout(() => {
    apiSources.value[source].lastSync = '刚刚'
    ElMessage.success('数据同步完成')
  }, 1500)
}

const fetchBankData = () => {
  apiDataPreview.value.push(
    { source: '银行风控', type: '交易流水', content: '账户 ***1234 异常转账记录', time: '2024-03-20 14:30', status: '已验证' },
    { source: '银行风控', type: '账户信息', content: '涉案账户开户人信息', time: '2024-03-20 14:25', status: '待验证' }
  )
  ElMessage.success('已获取银行风控数据')
}

const fetchPoliceData = () => {
  apiDataPreview.value.push(
    { source: '110平台', type: '警情信息', content: '诈骗类警情推送 #20240320001', time: '2024-03-20 10:15', status: '已验证' }
  )
  ElMessage.success('已获取110报警平台数据')
}

const fetchAntiFraudData = () => {
  apiDataPreview.value.push(
    { source: '反诈平台', type: '黑名单', content: '涉案号码 138****5678 已入库', time: '2024-03-20 09:00', status: '已验证' },
    { source: '反诈平台', type: '涉案账户', content: '账户 ***5678 已标记', time: '2024-03-20 09:05', status: '已验证' }
  )
  ElMessage.success('已获取反诈平台数据')
}

const importApiData = () => {
  ElMessage.success('数据已导入系统')
  apiDataPreview.value = []
}

const startApiAnalysis = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    startAnalysis()
  }, 1500)
}

const generateReport = () => {
  if (!reportConfig.value.gangId) {
    ElMessage.warning('请先选择一个团伙')
    return
  }
  generatingReport.value = true
  setTimeout(() => {
    generatingReport.value = false
    reportPreview.value = true
    ElMessage.success('报告生成成功')
  }, 1500)
}

const printReport = () => {
  ElMessage.success('正在准备打印...')
}

const downloadReport = () => {
  ElMessage.success('报告下载中...')
}

const loadDashboard = async () => {
  dashboardLoading.value = true
  try {
    const data = await getDashboardData()
    if (data.success) {
      const raw = data.data || data
      const toArray = (obj, nameKey, valKey) =>
        Object.entries(obj || {}).map(([k, v]) => ({ [nameKey]: k, [valKey]: v }))
      const colorMap = {
        'HIGH': '#ef4444', 'MEDIUM': '#f59e0b', 'LOW': '#00d4ff', 'S': '#ef4444',
        'A': '#f59e0b', 'B': '#00d4ff', 'C': '#10b981', 'UNKNOWN': '#94a3b8'
      }
      const riskArr = toArray(raw.risk_distribution, 'name', 'value').map(d =>
        ({ ...d, itemStyle: { color: colorMap[d.name] || '#94a3b8' } }))
      const statusArr = toArray(raw.status_distribution, 'name', 'value').map(d =>
        ({ name: d.name, value: d.value, itemStyle: { color: ['#f59e0b','#00d4ff','#10b981'][Math.floor(Math.random()*3)] } }))
      const barArr = (raw.top_scam_types || []).map(d => ({ name: d.name, count: d.count || d.value }))
      const trendMonths = (raw.trend_data?.dates || []).map((d, i) => ({
        month: d, amount: (raw.trend_data?.amounts || [])[i] || 0,
        cases: (raw.trend_data?.counts || [])[i] || 0
      }))
      const gangThreatArr = toArray(raw.gang_threat_distribution, 'name', 'value').map(d =>
        ({ ...d, itemStyle: { color: colorMap[d.name] || '#94a3b8' } }))

      dashboardData.value = {
        total_cases: raw.total_cases ?? '-',
        total_gangs: raw.total_gangs ?? '-',
        total_amount: raw.total_amount ?? '-',
        active_alerts: raw.active_alerts ?? '-',
        risk_distribution: riskArr,
        status_distribution: statusArr,
        top_scam_types: barArr,
        monthly_trend: trendMonths,
        gang_threat_distribution: gangThreatArr,
        recent_cases: raw.recent_cases || []
      }
      nextTick(() => initDashboardCharts())
    } else {
      ElMessage.error('获取看板数据失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('获取看板数据异常: ' + (err.message || '网络错误'))
  } finally {
    dashboardLoading.value = false
  }
}

const initDashboardCharts = () => {
  const riskData = dashboardData.value.risk_distribution.length
    ? dashboardData.value.risk_distribution
    : [
        { name: 'S级', value: 8, itemStyle: { color: '#ef4444' } },
        { name: 'A级', value: 15, itemStyle: { color: '#f59e0b' } },
        { name: 'B级', value: 22, itemStyle: { color: '#00d4ff' } },
        { name: 'C级', value: 18, itemStyle: { color: '#10b981' } }
      ]

  const statusData = dashboardData.value.status_distribution.length
    ? dashboardData.value.status_distribution
    : [
        { name: '已立案', value: 35, itemStyle: { color: '#f59e0b' } },
        { name: '侦办中', value: 28, itemStyle: { color: '#00d4ff' } },
        { name: '已结案', value: 15, itemStyle: { color: '#10b981' } },
        { name: '待核查', value: 12, itemStyle: { color: '#8b5cf6' } }
      ]

  const barData = dashboardData.value.top_scam_types.length
    ? dashboardData.value.top_scam_types
    : [
        { name: '冒充客服', count: 45 },
        { name: '刷单返利', count: 32 },
        { name: '贷款诈骗', count: 28 },
        { name: '投资理财', count: 23 },
        { name: '冒充公检法', count: 12 }
      ]

  const trendData = dashboardData.value.monthly_trend.length
    ? dashboardData.value.monthly_trend
    : [
        { month: '1月', amount: 120, cases: 8 },
        { month: '2月', amount: 182, cases: 12 },
        { month: '3月', amount: 191, cases: 15 },
        { month: '4月', amount: 234, cases: 18 },
        { month: '5月', amount: 290, cases: 22 },
        { month: '6月', amount: 330, cases: 25 }
      ]

  nextTick(() => {
    if (dashboardRiskChartRef.value) {
      if (dashboardRiskChart) dashboardRiskChart.dispose()
      dashboardRiskChart = echarts.init(dashboardRiskChartRef.value)
      dashboardRiskChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: {
          orient: 'vertical', right: 10, top: 'center',
          textStyle: { color: '#94a3b8' }
        },
        series: [{
          type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: riskData
        }]
      })
      dashboardRiskChart.resize()
    }

    if (dashboardStatusChartRef.value) {
      if (dashboardStatusChart) dashboardStatusChart.dispose()
      dashboardStatusChart = echarts.init(dashboardStatusChartRef.value)
      dashboardStatusChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: {
          orient: 'vertical', right: 10, top: 'center',
          textStyle: { color: '#94a3b8' }
        },
        series: [{
          type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: statusData
        }]
      })
      dashboardStatusChart.resize()
    }

    if (dashboardBarChartRef.value) {
      if (dashboardBarChart) dashboardBarChart.dispose()
      dashboardBarChart = echarts.init(dashboardBarChartRef.value)
      const barNames = barData.map(d => d.name)
      const barCounts = barData.map(d => d.count)
      const colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#00d4ff', '#10b981']
      dashboardBarChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category', data: barNames,
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
        },
        series: [{
          type: 'bar', barWidth: '60%',
          itemStyle: {
            color: (params) => colors[params.dataIndex % colors.length],
            borderRadius: [4, 4, 0, 0]
          },
          data: barCounts
        }]
      })
      dashboardBarChart.resize()
    }

    if (dashboardTrendChartRef.value) {
      if (dashboardTrendChart) dashboardTrendChart.dispose()
      dashboardTrendChart = echarts.init(dashboardTrendChartRef.value)
      dashboardTrendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: {
          data: ['涉案金额', '案件数量'],
          textStyle: { color: '#94a3b8' }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category', boundaryGap: false,
          data: trendData.map(d => d.month),
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
        },
        series: [
          {
            name: '涉案金额', type: 'line', smooth: true,
            yAxisIndex: 0,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
              ])
            },
            lineStyle: { color: '#00d4ff', width: 2 },
            itemStyle: { color: '#00d4ff' },
            data: trendData.map(d => d.amount)
          },
          {
            name: '案件数量', type: 'line', smooth: true,
            yAxisIndex: 0,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(239, 68, 68, 0.2)' },
                { offset: 1, color: 'rgba(239, 68, 68, 0.02)' }
              ])
            },
            lineStyle: { color: '#ef4444', width: 2 },
            itemStyle: { color: '#ef4444' },
            data: trendData.map(d => d.cases)
          }
        ]
      })
      dashboardTrendChart.resize()
    }
  })
}

const loadAlerts = async () => {
  alertsLoading.value = true
  try {
    const data = await getActiveAlerts()
    if (data.success) {
      alerts.value = data.alerts || data.data || []
    } else {
      ElMessage.error('获取预警信息失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('获取预警信息异常: ' + (err.message || '网络错误'))
  } finally {
    alertsLoading.value = false
  }
}

// ========== P1 API Methods ==========
const loadCapitalFlows = async () => {
  try {
    const params = flowSearchCaseId.value ? { case_id: flowSearchCaseId.value } : {}
    const r = await api.get('/api/capital/flows', { params })
    capitalFlows.value = r.data.flows || r.data.data || []
  } catch (e) {
    console.error('loadCapitalFlows:', e)
  }
}
const loadFlowGraph = async () => {
  if (!flowSearchCaseId.value) return
  try {
    const r = await api.get('/api/capital/graph/' + flowSearchCaseId.value)
    flowGraphData.value = r.data
  } catch (e) {
    console.error('loadFlowGraph:', e)
  }
}
const loadFlowData = async () => {
  await loadCapitalFlows()
  await loadFlowGraph()
}
const addFlowRecord = (row) => {
  ElMessage.info('追加资金流向功能：' + row.source_account + ' → ' + row.target_account)
}

const loadDispatchOrders = async () => {
  try {
    const params = dispatchStatusFilter.value ? { status: dispatchStatusFilter.value } : {}
    const r = await api.get('/api/dispatch/list', { params })
    dispatchOrders.value = r.data.dispatch_orders || r.data.data || []
  } catch (e) {
    console.error('loadDispatchOrders:', e)
  }
}
const signDispatch = async (id) => {
  try {
    const r = await api.put('/api/dispatch/' + id + '/sign')
    if (r.data.success) { ElMessage.success('签收成功'); await loadDispatchOrders() }
    else ElMessage.error(r.data.error || '签收失败')
  } catch (e) {
    ElMessage.error('签收异常: ' + (e.message || ''))
  }
}
const showCompleteDispatch = (row) => {
  ElMessageBox.prompt('处置反馈内容', '完成派单', { inputType: 'textarea', inputPlaceholder: '请描述处置情况...' })
    .then(async ({ value }) => {
      const r = await api.put('/api/dispatch/' + row.id + '/complete', { feedback: value })
      if (r.data.success) { ElMessage.success('已完成'); await loadDispatchOrders() }
    }).catch(() => {})
}

const loadKeyPersons = async () => {
  try {
    const params = {}
    if (personSearch.value) params.search = personSearch.value
    if (personTypeFilter.value) params.person_type = personTypeFilter.value
    const r = await api.get('/api/persons/key', { params })
    keyPersons.value = r.data.persons || r.data.data || []
  } catch (e) {
    console.error('loadKeyPersons:', e)
  }
}
const deleteKeyPerson = async (id) => {
  try {
    const r = await api.delete('/api/persons/key/' + id)
    if (r.data.success) { ElMessage.success('已移除'); await loadKeyPersons() }
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

const handleResolveAlert = async (alertId) => {
  resolvingAlert.value = alertId
  try {
    const data = await resolveAlert(alertId)
    if (data.success) {
      alerts.value = alerts.value.filter(a => a.id !== alertId)
      ElMessage.success('预警已处置')
    } else {
      ElMessage.error('处置失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('处置异常: ' + (err.message || '网络错误'))
  } finally {
    resolvingAlert.value = null
  }
}

const getAlertType = (confidence) => {
  if (confidence >= 80) return 'danger'
  if (confidence >= 60) return 'warning'
  return 'info'
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 80) return '#ef4444'
  if (confidence >= 60) return '#f59e0b'
  return '#00d4ff'
}

const viewCaseFromDashboard = (caseItem) => {
  selectedCase.value = caseItem
  router.push({ name: 'case-detail' })
}

const initCharts = () => {
  const scamTypeStats = {}
  cases.value.forEach(c => {
    const t = c.scam_type || c.type || '其他'
    scamTypeStats[t] = (scamTypeStats[t] || 0) + 1
  })
  const pieColors = ['#ef4444', '#f59e0b', '#8b5cf6', '#00d4ff', '#10b981', '#ec4899']
  const pieData = Object.entries(scamTypeStats).length
    ? Object.entries(scamTypeStats).map(([name, value], i) => ({
        name, value, itemStyle: { color: pieColors[i % pieColors.length] }
      }))
    : [
        { name: '冒充客服', value: 45, itemStyle: { color: '#ef4444' } },
        { name: '刷单返利', value: 32, itemStyle: { color: '#f59e0b' } },
        { name: '贷款诈骗', value: 28, itemStyle: { color: '#8b5cf6' } },
        { name: '投资理财', value: 23, itemStyle: { color: '#00d4ff' } }
      ]

  const lineData = dashboardData.value.monthly_trend.length
    ? dashboardData.value.monthly_trend
    : [
        { month: '1月', amount: 120, cases: 8 },
        { month: '2月', amount: 182, cases: 12 },
        { month: '3月', amount: 191, cases: 15 },
        { month: '4月', amount: 234, cases: 18 },
        { month: '5月', amount: 290, cases: 22 },
        { month: '6月', amount: 330, cases: 25 }
      ]

  nextTick(() => {
    if (pieChartRef.value) {
      if (pieChart) pieChart.dispose()
      pieChart = echarts.init(pieChartRef.value)
      pieChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c}起 ({d}%)' },
        legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { color: '#94a3b8' } },
        series: [{ type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
          avoidLabelOverlap: false, itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: pieData }]
      })
      pieChart.resize()
    }
    if (lineChartRef.value) {
      if (lineChart) lineChart.dispose()
      lineChart = echarts.init(lineChartRef.value)
      lineChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false,
          data: lineData.map(d => d.month),
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } } },
        series: [{
          name: '涉案金额', type: 'line', smooth: true,
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }]) },
          lineStyle: { color: '#00d4ff', width: 2 },
          itemStyle: { color: '#00d4ff' },
          data: lineData.map(d => d.amount) }]
      })
      lineChart.resize()
    }
  })
}

watch(() => router.currentRoute.value.name, (routeName) => {
  if (!routeName) return
  if (routeName === 'overview' && gangs.value.length) {
    nextTick(() => initCharts())
  }
  if (routeName === 'dashboard') {
    loadDashboard()
  }
  if (routeName === 'alerts') {
    loadAlerts()
  }
})

onMounted(async () => {
  const routeName = router.currentRoute.value.name
  if (routeName) {
    if (routeName === 'dashboard') {
      loadDashboard()
    }
    if (routeName === 'alerts') {
      loadAlerts()
    }
  }
  try {
    const [casesRes, gangsRes] = await Promise.all([fetchCases(), fetchGangs()])
    if (casesRes.success) {
      cases.value = (casesRes.data || []).map(c => ({
        id: c.case_id,
        title: c.title || (c.victim || '当事人') + '被诈骗案',
        amount: c.amount,
        amount_value: c.amount_value,
        status: c.status || '已立案',
        type: c.scam_type || '',
        risk_level: c.risk_level,
        victimName: c.victim || c.victim_name || '',
        victimGender: c.victim_gender || '',
        victimAge: c.victim_age || '',
        description: c.description || '',
        keywords: Array.isArray(c.keywords) ? c.keywords : [],
        date: c.created_at || ''
      }))
    }
    if (gangsRes.success) {
      gangs.value = (gangsRes.data || []).map((g, idx) => ({
        id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
        name: g.gang_name || '未知团伙',
        icon: gangIcons[idx % gangIcons.length],
        riskLevel: g.risk_level || 'B',
        risk_label: g.risk_label || '',
        amount: formatAmount(g.total_amount_involved || g.total_amount),
        cases: g.total_cases || 0,
        tags: Array.isArray(g.fingerprint) ? g.fingerprint.filter(Boolean) : [],
        members: [],
        score: g.comprehensive_score || 0,
        updateTime: '刚刚'
      }))
    }
  } catch (e) {
    console.warn('加载初始数据失败:', e)
  }
  if (routeName === 'overview' && gangs.value.length) {
    nextTick(() => initCharts())
  }
})


const appState = {
  store, activeMenu, loading, inputText, uploadedImages,
  gangs, cases, selectedGang, selectedCase, viewMode,
  gangSearchKeyword, riskFilter, detailTab, networkView,
  generatingReport, parsedReport,
  flowSearchCaseId, capitalFlows, flowGraphData,
  dispatchOrders, dispatchStatusFilter, showCreateDispatch,
  keyPersons, personSearch, personTypeFilter, showCreatePerson,
  dashboardData, dashboardLoading,
  alerts, alertsLoading, resolvingAlert,
  reportConfig, reportPreview,
  loginForm, loginLoading, loginError,
  apiSources, apiDataPreview,
  pieChartRef, lineChartRef,
  dashboardRiskChartRef, dashboardStatusChartRef,
  dashboardBarChartRef, dashboardTrendChartRef,
  totalAmount, totalAmountFormatted, successRate,
  textLineCount, extractedKeywords,
  hasTime, hasAmount, hasPhone, hasMethod,
  connectedSources, hasApiData, filteredGangs,
  getParticleStyle, handleMenuSelect,
  handleLogin, handleLogout,
  clearInput, clearImages, removeImage, loadDemo,
  handleBeforeUpload, startAnalysis,
  loadDashboard, loadAlerts,
  selectGang, viewGangDetail, viewCaseDetail, viewRelatedGang,
  viewCaseFromDashboard,
  generateReport, printReport, downloadReport,
  loadCapitalFlows, loadFlowGraph, loadFlowData,
  loadDispatchOrders, signDispatch, showCompleteDispatch,
  loadKeyPersons, deleteKeyPerson,
  handleResolveAlert, getAlertType, getConfidenceColor,
  features, relationNodes, relationLines,
  caseEvidence, investigationSteps,
  defaultMethodFlow, defaultKeywords,
  caseTypeStats, regionStats,
  gangIcons, formatAmount
}
provide('appState', appState)
</script>

<style>
.police-system-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.particle-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.particle {
  position: absolute;
  background: var(--accent-cyan);
  border-radius: 50%;
  opacity: 0.3;
  animation: float 20s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  25% { transform: translateY(-30px) translateX(20px); opacity: 0.5; }
  50% { transform: translateY(-60px) translateX(-20px); opacity: 0.3; }
  75% { transform: translateY(-30px) translateX(10px); opacity: 0.5; }
}

.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image:
    linear-gradient(rgba(0, 198, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 198, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
  animation: scan 8s linear infinite;
  opacity: 0.5;
  z-index: 1;
}

@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}

.sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: 10;
  flex-shrink: 0;
}

.logo-area {
  padding: 24px 20px;
  text-align: center;
  border-bottom: 1px solid var(--border-primary);
  background: linear-gradient(180deg, rgba(0, 198, 255, 0.05) 0%, transparent 100%);
}

.logo-icon-wrapper {
  position: relative;
  width: 60px;
  height: 60px;
  margin: 0 auto 12px;
}

.logo-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}

.logo-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 32px;
}

.logo-area h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 2px;
}

.sub-title {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  margin-top: 4px;
  display: block;
}

.logo-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 4px 12px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: var(--accent-cyan);
}

.badge-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-cyan);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.side-menu {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}

.menu-group {
  margin-bottom: 8px;
}

.menu-group-title {
  padding: 8px 20px;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.menu-icon {
  font-size: 16px;
}

.menu-text {
  flex: 1;
}

.menu-badge {
  background: var(--accent-cyan);
  color: var(--bg-primary);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.system-status {
  padding: 16px 20px;
  border-top: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.active {
  background: var(--accent-cyan);
  box-shadow: 0 0 8px var(--accent-cyan);
}

.version {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 8px;
  background: rgba(0, 198, 255, 0.1);
  border-radius: 4px;
}

.status-details {
  display: flex;
  gap: 16px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-label {
  font-size: 10px;
  color: var(--text-muted);
}

.status-value {
  font-size: 11px;
  color: var(--text-secondary);
}

.status-value.online {
  color: var(--accent-green);
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  position: relative;
  z-index: 5;
}

.content-wrapper {
  max-width: 1600px;
  margin: 0 auto;
}

.fade-in {
  animation: fadeIn 0.5s ease;
}

.view-section {
  animation: fadeIn 0.5s ease;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 28px;
}

.section-desc {
  color: var(--text-secondary);
  margin: 0;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.quick-stats {
  display: flex;
  gap: 16px;
}

.quick-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
}

.qs-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-cyan);
}

.qs-label {
  font-size: 11px;
  color: var(--text-muted);
}

.input-container {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  margin-bottom: 24px;
}

.input-main {
  padding: 20px;
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-icon {
  font-size: 20px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.input-area {
  margin-bottom: 12px;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.format-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.tip-icon {
  font-size: 14px;
}

.input-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-card {
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 18px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-content {
  min-height: 60px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-label {
  font-size: 12px;
  color: var(--text-muted);
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.empty-text {
  font-size: 12px;
}

.checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.check-item.active {
  background: rgba(16, 185, 129, 0.1);
  color: var(--accent-green);
}

.check-icon {
  font-size: 14px;
}

.action-bar {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.analyze-btn {
  padding: 16px 48px;
  font-size: 16px;
  font-weight: 600;
  height: auto;
  background: linear-gradient(135deg, #00d4ff 0%, #0084ff 100%) !important;
  border: none !important;
  border-radius: 12px;
  color: #0a0e1a !important;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
}

.analyze-btn:hover {
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.6);
  transform: translateY(-2px);
}

.btn-icon {
  font-size: 20px;
}

.upload-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 24px;
}

.upload-main {
  padding: 20px;
}

.upload-toolbar {
  margin-bottom: 16px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  background: rgba(10, 14, 26, 0.8) !important;
  border: 2px dashed rgba(0, 198, 255, 0.4) !important;
  border-radius: 16px !important;
  width: 100% !important;
  height: auto !important;
  transition: all 0.3s ease !important;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-cyan) !important;
  background: rgba(0, 198, 255, 0.05) !important;
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.2) !important;
}

.upload-content {
  padding: 48px 24px;
  text-align: center;
}

.upload-icon-wrapper {
  margin-bottom: 16px;
}

.upload-icon {
  font-size: 56px;
  color: var(--accent-cyan);
}

.upload-text {
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-size: 15px;
}

.upload-text .highlight {
  color: var(--accent-cyan);
  font-weight: 600;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.upload-formats {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.format-tag {
  padding: 4px 12px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: var(--accent-cyan);
}

.upload-preview {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.preview-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-primary);
  background: rgba(10, 14, 26, 0.9);
}

.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.9));
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.preview-name {
  font-size: 10px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.preview-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
}

.upload-tips {
  padding: 20px;
}

.tip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.tip-icon {
  font-size: 18px;
}

.tip-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.tip-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tip-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 198, 255, 0.2);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.tip-text {
  font-size: 13px;
  color: var(--text-secondary);
}

.api-sources-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.api-source-card {
  padding: 20px;
  transition: all 0.3s ease;
}

.api-source-card.active {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.2);
}

.source-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.source-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  border-radius: 12px;
}

.source-icon.bank {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.source-icon.police {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.source-icon.antiFraud {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
}

.source-info {
  flex: 1;
}

.source-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.source-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.source-content {
  margin-bottom: 16px;
}

.source-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}

.source-features {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.feature-icon {
  font-size: 14px;
}

.source-stats {
  display: flex;
  gap: 24px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.source-actions {
  display: flex;
  gap: 8px;
}

.api-data-preview {
  padding: 20px;
  margin-bottom: 24px;
}

.api-data-preview .preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.api-data-preview .preview-icon {
  font-size: 18px;
}

.api-data-preview .preview-title {
  flex: 1;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 28px;
}

.stat-icon-wrapper.danger {
  background: rgba(239, 68, 68, 0.15);
}

.stat-icon-wrapper.warning {
  background: rgba(245, 158, 11, 0.15);
}

.stat-icon-wrapper.success {
  background: rgba(16, 185, 129, 0.15);
}

.stat-icon-wrapper.info {
  background: rgba(0, 198, 255, 0.15);
}

.stat-content {
  flex: 1;
}

.stat-content .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-content .stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.stat-trend.up {
  color: var(--accent-green);
}

.overview-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  padding: 20px;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-content {
  height: 250px;
}

.gangs-section {
  margin-bottom: 24px;
}

.section-sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.sub-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.sub-icon {
  font-size: 18px;
}

.filter-bar {
  display: flex;
  gap: 12px;
}

.search-input {
  width: 200px;
}

.gangs-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.gang-card {
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.gang-card:hover,
.gang-card.selected {
  transform: translateY(-4px);
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.2);
}

.gang-card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.gang-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 28px;
}

.gang-icon-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.gang-icon-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.gang-icon-wrapper.risk-b {
  background: rgba(0, 198, 255, 0.2);
  border: 1px solid rgba(0, 198, 255, 0.4);
}

.gang-info {
  flex: 1;
}

.gang-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.gang-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gang-id {
  font-size: 11px;
  color: var(--text-muted);
}

.gang-card-body {
  margin-bottom: 16px;
}

.gang-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.gang-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.gang-stat .stat-icon {
  font-size: 16px;
}

.gang-stat .stat-content {
  display: flex;
  flex-direction: column;
}

.gang-stat .stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.gang-stat .stat-label {
  font-size: 10px;
  color: var(--text-muted);
}

.gang-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gang-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
}

.update-time {
  font-size: 11px;
  color: var(--text-muted);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.empty-content {
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.case-detail-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
}

.detail-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.case-header-card {
  padding: 24px;
}

.case-header-top {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 20px;
}

.case-icon-wrapper {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  font-size: 32px;
}

.case-icon-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 2px solid rgba(239, 68, 68, 0.4);
}

.case-icon-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 2px solid rgba(245, 158, 11, 0.4);
}

.case-header-info {
  flex: 1;
}

.case-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.case-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-icon {
  font-size: 14px;
}

.case-header-actions {
  display: flex;
  gap: 8px;
}

.case-header-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.header-stat {
  text-align: center;
}

.header-stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  display: block;
}

.header-stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.detail-tabs {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.detail-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: rgba(0, 0, 0, 0.2);
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.detail-tabs :deep(.el-tabs__item) {
  color: var(--text-secondary);
  padding: 16px 20px;
  height: auto;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-cyan);
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background: var(--accent-cyan);
}

.detail-tabs :deep(.el-tabs__content) {
  padding: 20px;
}

.timeline-section {
  padding: 24px;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent-cyan);
  border: 3px solid var(--bg-primary);
  box-shadow: 0 0 10px var(--accent-cyan);
}

.timeline-dot.dot-0 { background: #ef4444; box-shadow: 0 0 10px #ef4444; }
.timeline-dot.dot-1 { background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }
.timeline-dot.dot-2 { background: #8b5cf6; box-shadow: 0 0 10px #8b5cf6; }
.timeline-dot.dot-3 { background: #00d4ff; box-shadow: 0 0 10px #00d4ff; }

.timeline-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(to bottom, var(--border-secondary), transparent);
  margin-top: 8px;
}

.timeline-content {
  flex: 1;
  padding-bottom: 8px;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.timeline-date {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.timeline-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.timeline-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.timeline-details {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.detail-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 6px;
}

.detail-label {
  color: var(--text-muted);
}

.detail-value {
  color: var(--text-primary);
}

.method-section,
.money-section {
  padding: 24px;
}

.method-header,
.money-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.method-icon,
.money-icon {
  font-size: 24px;
}

.method-title,
.money-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.method-flow {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  overflow-x: auto;
  padding: 16px 0;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: max-content;
}

.step-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}

.step-content {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.step-desc {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 150px;
}

.step-arrow {
  font-size: 20px;
  color: var(--text-muted);
}

.method-keywords {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.keyword-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.money-flow {
  margin-bottom: 20px;
}

.flow-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 24px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  flex-wrap: wrap;
}

.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-radius: 12px;
  min-width: 100px;
}

.flow-node.source {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.flow-node.gang {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
}

.flow-node.middle {
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.flow-node.target {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.node-icon {
  font-size: 24px;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.node-amount {
  font-size: 11px;
  color: var(--text-muted);
}

.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 24px;
  color: var(--text-muted);
}

.arrow-label {
  font-size: 10px;
  color: var(--text-muted);
}

.money-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.money-stat {
  text-align: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.ms-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.ms-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-section {
  padding: 16px;
}

.section-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-icon {
  font-size: 16px;
}

.section-title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.evidence-icon {
  font-size: 20px;
}

.evidence-info {
  flex: 1;
}

.evidence-name {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.member-avatar {
  font-size: 20px;
}

.member-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.member-name {
  font-size: 13px;
  color: var(--text-primary);
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feature-tag {
  margin: 0;
}

.profiles-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.profile-card {
  padding: 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-primary);
}

.profile-avatar-wrapper {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  font-size: 32px;
}

.profile-avatar-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 2px solid rgba(239, 68, 68, 0.4);
}

.profile-avatar-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 2px solid rgba(245, 158, 11, 0.4);
}

.profile-basic {
  flex: 1;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.profile-id {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.profile-quick-stats {
  display: flex;
  gap: 16px;
}

.quick-stat-item {
  text-align: right;
}

.qsi-value {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.qsi-label {
  font-size: 11px;
  color: var(--text-muted);
}

.profile-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-section {
  margin-bottom: 0;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--accent-cyan);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.label-icon {
  font-size: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.info-label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.info-value.danger {
  color: var(--accent-red);
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.member-details {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ability-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ability-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ability-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.profile-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.analysis-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.analysis-card {
  padding: 20px;
}

.analysis-card.full-width {
  grid-column: span 2;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.analysis-icon {
  font-size: 20px;
}

.analysis-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.analysis-subtitle {
  font-size: 12px;
  color: var(--accent-cyan);
  margin-left: auto;
  padding: 2px 8px;
  background: rgba(0, 198, 255, 0.1);
  border-radius: 4px;
}

.flow-badge {
  font-size: 11px;
  color: #f59e0b;
  margin-left: auto;
  padding: 3px 10px;
  background: rgba(245, 158, 11, 0.15);
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.flow-chart {
  margin-bottom: 20px;
}

.flow-path {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 0;
  flex-wrap: wrap;
}

.flow-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stage-node {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 2px solid;
}

.stage-node.source {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.5);
}

.stage-node.gang {
  background: rgba(139, 92, 246, 0.15);
  border-color: rgba(139, 92, 246, 0.5);
}

.stage-node.middle {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.5);
}

.stage-node.target {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
}

.stage-node .node-glow {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  animation: pulse-glow 2s ease-in-out infinite;
}

.stage-node.source .node-glow {
  background: rgba(239, 68, 68, 0.3);
}

.stage-node.gang .node-glow {
  background: rgba(139, 92, 246, 0.3);
}

.stage-node.middle .node-glow {
  background: rgba(245, 158, 11, 0.3);
}

.stage-node.target .node-glow {
  background: rgba(16, 185, 129, 0.3);
}

.stage-node .node-icon {
  font-size: 22px;
  position: relative;
  z-index: 1;
}

.stage-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.stage-desc {
  font-size: 10px;
  color: var(--text-muted);
}

.flow-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 5px;
}

.connector-line {
  width: 40px;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-cyan), rgba(0, 198, 255, 0.3));
}

.connector-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid var(--accent-cyan);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
}

.connector-label {
  font-size: 10px;
  color: var(--text-muted);
}

.flow-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.metric-icon {
  font-size: 20px;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
}

.metric-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.feature-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: var(--feature-color, var(--accent-cyan));
  transform: translateY(-2px);
}

.feature-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(0, 198, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-icon {
  font-size: 18px;
}

.feature-info {
  flex: 1;
}

.feature-card .feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-card .feature-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.feature-card .feature-value {
  font-size: 13px;
  font-weight: 600;
}

.feature-desc {
  font-size: 10px;
  color: var(--text-muted);
}

.feature-bar-wrap {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.feature-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s ease;
}

@keyframes pulse-glow {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 0; }
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-name {
  font-size: 13px;
  color: var(--text-secondary);
}

.feature-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.relation-map {
  min-height: 300px;
}

.relation-viz {
  position: relative;
  height: 300px;
}

.rel-node {
  position: absolute;
  width: 60px;
  height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: all 0.3s ease;
}

.rel-node.gang {
  background: rgba(139, 92, 246, 0.3);
  border: 2px solid var(--accent-purple);
}

.rel-node.case {
  background: rgba(0, 198, 255, 0.3);
  border: 2px solid var(--accent-cyan);
}

.rel-node.money {
  background: rgba(245, 158, 11, 0.3);
  border: 2px solid var(--accent-orange);
}

.rel-node:hover {
  transform: translate(-50%, -50%) scale(1.2);
}

.rel-icon {
  font-size: 20px;
}

.rel-label {
  font-size: 10px;
  color: var(--text-primary);
}

.relation-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.relation-lines line {
  stroke: var(--border-secondary);
  stroke-width: 2;
}

.type-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.type-item {
  position: relative;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.type-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  opacity: 0.3;
  border-radius: 8px;
}

.type-info {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-name {
  font-size: 13px;
  color: var(--text-primary);
}

.type-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.region-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.region-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.region-name {
  width: 50px;
  font-size: 12px;
  color: var(--text-secondary);
}

.region-bar-wrapper {
  flex: 1;
  height: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.region-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  border-radius: 4px;
}

.region-count {
  width: 50px;
  text-align: right;
  font-size: 12px;
  color: var(--text-primary);
}

.network-container {
  height: calc(100vh - 320px);
  min-height: 500px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.network-legend {
  display: flex;
  justify-content: center;
  gap: 30px;
  padding: 16px;
  margin-top: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.gang-s {
  background: #ff3860;
  box-shadow: 0 0 8px rgba(255, 56, 96, 0.5);
}

.legend-dot.gang-a {
  background: #ffd700;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
}

.legend-dot.case {
  background: #00c6ff;
  box-shadow: 0 0 8px rgba(0, 198, 255, 0.5);
}

.legend-dot.money {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
}

.legend-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.report-container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
}

.report-config-panel {
  padding: 20px;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary);
}

.config-icon {
  font-size: 20px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-footer {
  padding-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.generate-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
}

.report-preview-panel {
  padding: 20px;
}

.report-preview-panel .preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.report-preview-panel .preview-icon {
  font-size: 18px;
}

.report-preview-panel .preview-title {
  flex: 1;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.preview-body {
  min-height: 500px;
}

.report-document {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #e2e8f0;
  padding: 40px;
  border-radius: 12px;
  font-family: "Microsoft YaHei", "SimHei", serif;
  border: 1px solid rgba(0, 198, 255, 0.2);
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.1);
}

.doc-header {
  text-align: center;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 2px solid rgba(0, 198, 255, 0.3);
  position: relative;
}

.doc-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
}

.doc-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.doc-logo .logo-icon {
  font-size: 24px;
  position: static;
  transform: none;
}

.doc-logo .logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.doc-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
  text-shadow: 0 0 20px rgba(0, 198, 255, 0.3);
}

.doc-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 12px;
  color: var(--text-secondary);
}

.doc-meta .meta-item {
  color: var(--text-secondary);
}

.doc-meta .meta-value {
  color: var(--text-primary);
}

.doc-meta .meta-value.secret {
  color: var(--accent-red);
  font-weight: 600;
}

.doc-content {
  margin-bottom: 32px;
}

.doc-section {
  margin-bottom: 24px;
}

.doc-section .section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-cyan);
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 4px solid var(--accent-cyan);
}

.doc-section .section-body {
  padding-left: 16px;
}

.info-table {
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.info-row {
  display: flex;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .info-label {
  width: 120px;
  padding: 10px 12px;
  background: rgba(0, 198, 255, 0.1);
  font-size: 13px;
  color: var(--text-secondary);
}

.info-row .info-value {
  flex: 1;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
}

.info-row .info-value.danger {
  color: var(--accent-red);
  font-weight: 600;
}

.doc-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-timeline-item {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.doc-time {
  width: 80px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.doc-event {
  width: 120px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.doc-desc {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.money-flow-summary {
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.money-flow-summary p {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.suggestion-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
}

.suggestion-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.doc-footer {
  text-align: center;
  padding-top: 24px;
}

.footer-line {
  height: 1px;
  background: #ddd;
  margin-bottom: 16px;
}

.footer-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #999;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: var(--text-muted);
}

.preview-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.preview-empty .empty-text {
  font-size: 14px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1400px) {
  .api-sources-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .profiles-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1200px) {
  .input-container {
    grid-template-columns: 1fr;
  }
  
  .case-detail-content {
    grid-template-columns: 1fr;
  }
  
  .detail-sidebar {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .sidebar-section {
    flex: 1;
    min-width: 280px;
  }
  
  .report-container {
    grid-template-columns: 1fr;
  }
}

.login-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(10, 14, 26, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(8px);
}

.login-container {
  width: 420px;
  padding: 0;
  overflow: visible;
}

.login-header {
  text-align: center;
  padding: 40px 40px 24px;
  border-bottom: 1px solid var(--border-primary);
  background: linear-gradient(180deg, rgba(0, 198, 255, 0.05) 0%, transparent 100%);
}

.login-logo-wrapper {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
}

.login-logo-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

.login-logo-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 36px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 3px;
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 3px;
  margin: 0;
}

.login-form {
  padding: 32px 40px 24px;
}

.login-field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.login-field-icon {
  font-size: 20px;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: var(--radius-md);
}

.login-input {
  flex: 1;
}

.login-input .el-input__wrapper {
  background: rgba(0, 0, 0, 0.4) !important;
}

.login-error {
  color: var(--accent-red);
  font-size: 13px;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  text-align: center;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 6px;
}

.login-btn .el-button--primary {
  height: 44px;
}

.login-footer {
  text-align: center;
  padding: 16px 40px 32px;
}

.login-footer-text {
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.logout-area {
  border-top: 1px solid var(--border-primary);
  padding: 8px 12px;
}

.logout-btn {
  width: 100%;
  justify-content: center;
}

.alert-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.alert-card:hover {
  border-color: rgba(0, 198, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.05);
}

.alert-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 24px 16px;
}

.alert-icon-wrapper {
  width: 44px;
  height: 44px;
  background: rgba(239, 68, 68, 0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.alert-icon {
  font-size: 22px;
}

.alert-info {
  flex: 1;
  min-width: 0;
}

.alert-type {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.alert-id {
  font-size: 12px;
  color: var(--text-muted);
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.alert-meta .meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.alert-meta .meta-icon {
  font-size: 14px;
}

.alert-actions {
  flex-shrink: 0;
}

.alert-body {
  padding: 0 24px 12px;
}

.alert-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.alert-footer {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--border-primary);
}

.confidence-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.confidence-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.confidence-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.confidence-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.recent-cases-section {
  margin-top: 32px;
}

.recent-cases-section .section-sub-header {
  margin-bottom: 16px;
}

.recent-cases-section .sub-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

/* ────────────── 结构优化 ────────────── */

/* KPI 数字更突出 */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  min-height: 120px;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 24px;
}

.stat-icon-wrapper.danger { background: rgba(239, 68, 68, 0.15); }
.stat-icon-wrapper.warning { background: rgba(245, 158, 11, 0.15); }
.stat-icon-wrapper.success { background: rgba(16, 185, 129, 0.15); }
.stat-icon-wrapper.info { background: rgba(0, 198, 255, 0.15); }

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  margin-bottom: 4px;
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  padding-top: 8px;
  border-top: 1px solid rgba(0, 198, 255, 0.1);
}

.stat-trend.up {
  color: var(--accent-green);
}

/* 案件详情信息网格 - 3列 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.08);
}

.info-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.danger {
  color: var(--accent-red);
}

/* 案件详情布局优化 */
.case-detail-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  margin-top: 20px;
}

.detail-tabs :deep(.el-tabs__content) {
  padding: 20px 0;
}

.detail-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 20px;
}

.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-section {
  padding: 16px;
}

.section-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.section-title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 团伙画像卡片优化 */
.gangs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.gang-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gang-card .card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gang-card .gang-icon {
  font-size: 28px;
}

.gang-card .gang-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.gang-card .card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.gang-card .card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 198, 255, 0.08);
}

/* 空状态居中优化 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  padding: 40px 20px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 400px;
}

.empty-content .empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
  line-height: 1.5;
}

/* 内容区边距优化 */
.main-content {
  padding: 32px;
}

.section-header {
  margin-bottom: 28px;
}

.overview-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  padding: 20px;
}

.chart-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-content {
  height: 280px;
}

/* 报警卡片置信度条 */
.confidence-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.confidence-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.confidence-value {
  font-size: 12px;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}

/* 证据列表 */
.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.evidence-icon {
  font-size: 20px;
}

.evidence-info {
  flex: 1;
}

.evidence-name {
  font-size: 13px;
  color: var(--text-primary);
}

.evidence-meta {
  margin-top: 2px;
}

/* 办案民警列表 */
.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.member-avatar {
  font-size: 24px;
}

.member-info {
  display: flex;
  flex-direction: column;
}

.member-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.member-role {
  font-size: 11px;
  color: var(--text-muted);
}

/* 资金流向可视化 */
.money-section {
  padding: 20px;
}

.money-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.money-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.flow-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  overflow-x: auto;
}

.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 20px;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 12px;
  min-width: 100px;
  text-align: center;
}

.flow-node .node-icon {
  font-size: 24px;
}

.flow-node .node-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.flow-node .node-amount {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  font-size: 20px;
}

.arrow-label {
  font-size: 10px;
}

.money-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}

.money-stat {
  text-align: center;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.money-stat .ms-label {
  font-size: 11px;
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.money-stat .ms-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

/* 调查时间线 */
.investigation-timeline {
  padding: 16px 0;
}

.timeline-item {
  display: flex;
  gap: 16px;
  position: relative;
  padding-left: 24px;
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-muted);
  z-index: 1;
  flex-shrink: 0;
}

.timeline-dot.completed {
  background: var(--accent-green);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}

.timeline-dot.current {
  background: var(--accent-cyan);
  box-shadow: 0 0 8px rgba(0, 198, 255, 0.5);
}

.timeline-line {
  width: 2px;
  flex: 1;
  background: rgba(0, 198, 255, 0.15);
  margin: 4px 0;
}

.timeline-content {
  padding-bottom: 24px;
  flex: 1;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.timeline-date {
  font-size: 11px;
  color: var(--text-muted);
}

.timeline-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.timeline-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 告警列表布局 */
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-card {
  padding: 16px;
}

.alert-header {
  display: flex;
  gap: 16px;
}

.alert-icon-wrapper {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(239, 68, 68, 0.15);
  border-radius: 10px;
  flex-shrink: 0;
}

.alert-icon {
  font-size: 20px;
}

.alert-info {
  flex: 1;
}

.alert-type {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.alert-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.alert-actions {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
}

.alert-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 198, 255, 0.08);
}

/* 分析看板 */
.analysis-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-card {
  padding: 20px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.analysis-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.flow-badge {
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(0, 198, 255, 0.15);
  border-radius: 8px;
  color: var(--accent-cyan);
  font-weight: 500;
}

/* 章节子标题 */
.section-sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.sub-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-icon {
  font-size: 22px;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  width: 200px;
}

/* 能力评估条 */
.profile-section {
  margin-top: 12px;
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.ability-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ability-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ability-label {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 80px;
}

.ability-item :deep(.el-progress) {
  flex: 1;
}

/* 案件详情头部 */
.case-detail-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  flex-wrap: wrap;
}

.case-detail-badge {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.case-detail-info {
  flex: 1;
}

.case-detail-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.case-detail-meta {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  gap: 16px;
}

.case-header-stats {
  display: flex;
  gap: 24px;
}

.header-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.header-stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

/* 概述内容排版 */
.case-overview {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-section {
  padding: 0 4px;
}

.overview-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.overview-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
}

/* 能力评估进度条 */
.profile-section .el-progress,
.profile-section :deep(.el-progress) {
  --el-progress-text-color: var(--text-secondary);
}

/* 团伙画像页布局 */
.gang-profiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
  gap: 20px;
}

.gang-profile-card {
  padding: 0;
}

.profile-content {
  padding: 20px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.profile-body {
  display: grid;
  gap: 16px;
}

.profile-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 198, 255, 0.08);
}

.profile-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.profile-chip .chip-icon {
  font-size: 14px;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.risk-badge.S { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.risk-badge.A { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.risk-badge.B { background: rgba(0, 198, 255, 0.2); color: #00d4ff; }
.risk-badge.C { background: rgba(16, 185, 129, 0.2); color: #10b981; }

/* 标签云 */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* 仪表盘进度等 misc */
.cases-table {
  overflow: hidden;
}

.cases-table :deep(.el-table) {
  border-radius: 8px;
}

/* 案情模拟卡片 */
.method-section {
  padding: 20px;
}

.method-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.method-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.method-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.method-step {
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  border: 1px solid rgba(0, 198, 255, 0.08);
}

.method-step .step-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--accent-cyan);
  opacity: 0.5;
  margin-bottom: 8px;
}

.method-step .step-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.method-step .step-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 看板最近案件 */
.recent-cases-section {
  margin-top: 24px;
}

/* 退出按钮 */
.logout-btn {
  width: 100%;
  margin-top: 12px;
}

/* AI研判结论展示 */
.report-part-a {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.report-part-b {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 198, 255, 0.1);
}

.report-line {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.report-line.report-heading {
  margin-top: 12px;
  margin-bottom: 8px;
}

.report-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--accent-cyan);
  display: block;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.report-line.report-item {
  padding-left: 8px;
  border-left: 2px solid rgba(0, 198, 255, 0.15);
  margin: 4px 0;
}

.report-bullet {
  color: var(--text-primary);
}

.report-json-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}

.report-json-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  border: 1px solid rgba(0, 198, 255, 0.08);
}

.report-json-key {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.report-json-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  word-break: break-all;
}

/* 系统管理页面 */
.admin-tabs {
  margin-top: 16px;
}

.admin-toolbar {
  margin-bottom: 16px;
}

.admin-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.info-card {
  padding: 20px;
}

.info-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--accent-cyan);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 198, 255, 0.05);
  font-size: 13px;
  color: var(--text-secondary);
}

.info-row span:last-child {
  color: var(--text-primary);
  font-weight: 500;
}

.status-online {
  color: #10b981 !important;
}

.log-detail {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.admin-form .el-form-item {
  margin-bottom: 12px;
}

.progress-dialog .el-dialog__body { padding: 32px; text-align: center; }
.progress-body { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.progress-animation { width: 48px; height: 48px; border-radius: 50%; background: rgba(0,198,255,0.1); display: flex; align-items: center; justify-content: center; }
.pulse-dot { width: 16px; height: 16px; border-radius: 50%; background: var(--accent-cyan); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.5); } }
.progress-title { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.progress-status { font-size: 13px; color: var(--text-secondary); }
.progress-hint { font-size: 12px; color: var(--text-muted); }
.result-body { text-align: center; padding: 16px 0; }
.result-icon { font-size: 48px; margin-bottom: 12px; }
.result-title { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-bottom: 20px; }
.result-stats { display: flex; justify-content: center; gap: 32px; }
.result-stat { text-align: center; }
.rs-value { font-size: 28px; font-weight: 700; color: var(--accent-cyan); }
.rs-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.result-dialog .el-dialog__footer { border-top: 1px solid rgba(0,198,255,0.1); padding: 16px 24px; }
</style>