import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { useRouter, useRoute } from 'vue-router'
import { store } from '../store.js'
import api, {
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
  importExcel
} from '../api.js'

export function useFraudLens() {
  const router = useRouter()
  const route = useRoute()

  const activeMenu = computed(() => route.name || 'input')
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
        store.login(data.user || { username: loginForm.value.username }, data.token)
        loginForm.value = { username: '', password: '' }
        ElMessage.success('登录成功')
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

  const navigateTo = (name) => {
    router.push({ name })
  }

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

  const caseTypeStats = computed(() => {
    const typeMap = {}
    cases.value.forEach(c => {
      const t = c.type || c.scam_type || '其他'
      typeMap[t] = (typeMap[t] || 0) + 1
    })
    const entries = Object.entries(typeMap)
    if (!entries.length) return [
      { name: '冒充客服诈骗', count: 45, percent: 35, color: '#ef4444' },
      { name: '刷单返利诈骗', count: 32, percent: 25, color: '#f59e0b' },
      { name: '贷款诈骗', count: 28, percent: 22, color: '#8b5cf6' },
      { name: '投资理财诈骗', count: 23, percent: 18, color: '#00d4ff' }
    ]
    const total = entries.reduce((s, [, v]) => s + v, 0)
    const colors = ['#ef4444','#f59e0b','#8b5cf6','#00d4ff','#10b981','#ec4899']
    return entries.map(([name, count], i) => ({
      name, count,
      percent: Math.round(count / total * 100),
      color: colors[i % colors.length]
    }))
  })

  const regionStats = ref([
    { name: '广东', count: 25, percent: 30 },
    { name: '浙江', count: 18, percent: 22 },
    { name: '江苏', count: 15, percent: 18 },
    { name: '北京', count: 12, percent: 14 },
    { name: '上海', count: 10, percent: 12 }
  ])

  const semanticFingerprints = computed(() => {
    if (!cases.value.length) return []
    const types = {}
    cases.value.forEach(c => {
      const t = c.type || c.scam_type || '其他'
      if (!types[t]) types[t] = { type: t, count: 0, totalAmount: 0, keywords: [] }
      types[t].count++
      types[t].totalAmount += Math.abs(c.amount_value || 0)
      if (c.keywords && Array.isArray(c.keywords)) {
        types[t].keywords = [...new Set([...types[t].keywords, ...c.keywords])].slice(0, 6)
      }
    })
    return Object.values(types)
  })

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
        uploadedImages.value.push({ url: '', name: file.name, type: 'text', content: e.target.result, _file: file })
      }
      reader.readAsText(file)
    } else if (isImage) {
      const reader = new FileReader()
      reader.onload = (e) => {
        uploadedImages.value.push({ url: e.target.result, name: file.name, type: 'image', content: '', _file: file })
      }
      reader.readAsDataURL(file)
    } else {
      uploadedImages.value.push({ url: '', name: file.name, type: 'docx', content: '', _file: file })
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
        router.push({ name: 'overview' })
      } else {
        showProgress.value = false
        ElMessage.error('分析失败: ' + (response.message || '服务器返回异常'))
      }
    } catch (err) {
      showProgress.value = false
      ElMessage.error('分析请求异常: ' + (err.message || '网络错误'))
    } finally {
      loading.value = false
    }
  }

  const goToResults = () => {
    showResult.value = false
    router.push({ name: 'overview' })
  }

  const getCaseGang = (caseId) => {
    return gangs.value.find(g => {
      if (!g.id && !g.gang_id) return false
      return g.caseIds?.includes(caseId) || g.case_ids?.includes(caseId)
    })
  }

  const getCaseTitle = (caseId) => {
    const c = cases.value.find(c => (c.id === caseId || c.case_id === caseId))
    return c ? c.title : '未知案件'
  }

  const startImageAnalysis = () => {
    loading.value = true
    setTimeout(() => {
      loading.value = false
      ElMessage.success('图片识别完成，已提取关键信息')
      startAnalysis()
    }, 2000)
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
        dashboardData.value = {
          total_cases: data.total_cases ?? data.data?.total_cases ?? '-',
          total_gangs: data.total_gangs ?? data.data?.total_gangs ?? '-',
          total_amount: data.total_amount ?? data.data?.total_amount ?? '-',
          active_alerts: data.active_alerts ?? data.data?.active_alerts ?? '-',
          risk_distribution: data.risk_distribution ?? data.data?.risk_distribution ?? [],
          status_distribution: data.status_distribution ?? data.data?.status_distribution ?? [],
          top_scam_types: data.top_scam_types ?? data.data?.top_scam_types ?? [],
          monthly_trend: data.monthly_trend ?? data.data?.monthly_trend ?? [],
          recent_cases: data.recent_cases ?? data.data?.recent_cases ?? []
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
                color: new echarts.graphic.LinearGradient(0,0,0,1, [
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
    nextTick(() => {
      if (pieChartRef.value) {
        if (pieChart) {
          pieChart.dispose()
        }
        pieChart = echarts.init(pieChartRef.value)
        pieChart.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item', formatter: '{b}: {c}起 ({d}%)' },
          legend: {
            orient: 'vertical',
            right: 10,
            top: 'center',
            textStyle: { color: '#94a3b8' }
          },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
            label: { show: false },
            emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
            data: [
              { value: 45, name: '冒充客服', itemStyle: { color: '#ef4444' } },
              { value: 32, name: '刷单返利', itemStyle: { color: '#f59e0b' } },
              { value: 28, name: '贷款诈骗', itemStyle: { color: '#8b5cf6' } },
              { value: 23, name: '投资理财', itemStyle: { color: '#00d4ff' } }
            ]
          }]
        })
        pieChart.resize()
      }
      if (lineChartRef.value) {
        if (lineChart) {
          lineChart.dispose()
        }
        lineChart = echarts.init(lineChartRef.value)
        lineChart.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'axis' },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: ['1月', '2月', '3月', '4月', '5月', '6月'],
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
            name: '涉案金额',
            type: 'line',
            smooth: true,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
              ])
            },
            lineStyle: { color: '#00d4ff', width: 2 },
            itemStyle: { color: '#00d4ff' },
            data: [120, 182, 191, 234, 290, 330]
          }]
        })
        lineChart.resize()
      }
    })
  }

  watch(() => route.name, (newVal) => {
    if (newVal === 'overview' && gangs.value.length) {
      nextTick(() => initCharts())
    }
    if (newVal === 'dashboard') {
      loadDashboard()
    }
    if (newVal === 'alerts') {
      loadAlerts()
    }
  })

  onMounted(async () => {
    const routeName = route.name
    if (routeName === 'dashboard') loadDashboard()
    if (routeName === 'alerts') loadAlerts()
    try {
      const [casesRes, gangsRes] = await Promise.all([fetchCases(), fetchGangs()])
      if (casesRes.success) {
        const caseData = casesRes.cases || casesRes.data || []
        cases.value = caseData.map(c => ({
          id: c.case_id, case_id: c.case_id,
          title: c.title || (c.victim || c.victim_name || '当事人') + '被诈骗案',
          amount: c.amount, amount_value: c.amount_value || 0,
          scam_type: c.scam_type || '', type: c.scam_type || '',
          status: c.status || '已立案', risk_level: c.risk_level || '',
          victimName: c.victim || c.victim_name || '',
          victimGender: c.victim_gender || '', victimAge: c.victim_age || '',
          victimPhone: c.victim_phone || '', victimJob: c.victim_job || '',
          victimAddress: c.victim_address || '',
          description: c.description || '',
          keywords: Array.isArray(c.keywords) ? c.keywords : [],
          date: c.created_at || ''
        }))
      }
      if (gangsRes.success) {
        const gangData = gangsRes.gangs || gangsRes.data || []
        gangs.value = gangData.map((g, idx) => ({
          id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
          gang_id: g.gang_id || '',
          name: g.gang_name || '未知团伙',
          gang_name: g.gang_name || '',
          icon: gangIcons[idx % gangIcons.length],
          riskLevel: g.risk_level || 'B',
          risk_label: g.risk_label || '',
          amount: formatAmount(g.total_amount_involved || g.total_amount),
          total_amount_involved: g.total_amount_involved || g.total_amount || '',
          total_cases: g.total_cases || 0, cases: g.total_cases || 0,
          tags: Array.isArray(g.fingerprint) ? g.fingerprint.filter(Boolean) : [],
          members: [], score: g.comprehensive_score || 0,
          comprehensive_score: g.comprehensive_score || 0,
          confidence: g.confidence || 0,
          member_count_estimate: g.member_count_estimate || '',
          tech_level: g.tech_level || '', script_type: g.script_type || '',
          description: g.description || '',
          fingerprint: Array.isArray(g.fingerprint) ? g.fingerprint : [],
          related_cases: Array.isArray(g.related_cases) ? g.related_cases : [],
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

  return {
    store,
    activeMenu,
    loading,
    showProgress, showResult, progressPercent, progressMessage, resultStats,
    inputText,
    uploadedImages,
    gangs,
    cases,
    selectedGang,
    selectedCase,
    viewMode,
    gangSearchKeyword,
    riskFilter,
    detailTab,
    networkView,
    generatingReport,
    parsedReport,
    flowSearchCaseId,
    capitalFlows,
    flowGraphData,
    dispatchOrders,
    dispatchStatusFilter,
    showCreateDispatch,
    keyPersons,
    personSearch,
    personTypeFilter,
    showCreatePerson,
    dashboardData,
    dashboardLoading,
    alerts,
    alertsLoading,
    resolvingAlert,
    dashboardRiskChartRef,
    dashboardStatusChartRef,
    dashboardBarChartRef,
    dashboardTrendChartRef,
    reportConfig,
    reportPreview,
    loginForm,
    loginLoading,
    loginError,
    apiSources,
    apiDataPreview,
    pieChartRef,
    lineChartRef,
    totalAmount,
    totalAmountFormatted,
    successRate,
    textLineCount,
    extractedKeywords,
    hasTime, hasAmount, hasPhone, hasMethod,
    connectedSources,
    hasApiData,
    filteredGangs,
    features,
    relationNodes,
    relationLines,
    caseEvidence,
    investigationSteps,
    defaultMethodFlow,
    defaultKeywords,
    caseTypeStats,
    regionStats,
    semanticFingerprints,
    gangIcons,
    formatAmount,
    navigateTo,
    getParticleStyle,
    getRiskType,
    getEventType,
    getGangById,
    getFeatureIcon,
    getReportTitle,
    handleMenuSelect,
    selectGang,
    viewGangDetail,
    viewCaseDetail,
    viewRelatedGang,
    clearInput,
    clearImages,
    removeImage,
    loadDemo,
    handleBeforeUpload,
    handleLogin,
    handleLogout,
    startAnalysis,
    goToResults,
    getCaseGang,
    getCaseTitle,
    startImageAnalysis,
    toggleApiSource,
    syncApiData,
    fetchBankData,
    fetchPoliceData,
    fetchAntiFraudData,
    importApiData,
    startApiAnalysis,
    generateReport,
    printReport,
    downloadReport,
    loadDashboard,
    loadAlerts,
    loadCapitalFlows,
    loadFlowGraph,
    loadFlowData,
    addFlowRecord,
    loadDispatchOrders,
    signDispatch,
    showCompleteDispatch,
    loadKeyPersons,
    deleteKeyPerson,
    handleResolveAlert,
    getAlertType,
    getConfidenceColor,
    viewCaseFromDashboard,
    initCharts
  }
}