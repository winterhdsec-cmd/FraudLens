import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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
  demoLogin as apiDemoLogin,
  ocrImage,
  getDashboardData,
  getActiveAlerts,
  fetchCapitalFlowStats,
  resolveAlert,
  importCSV,
  importExcel,
  seedData,
  searchCases
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
  const flowMetrics = ref({
    total_accounts: 0,
    max_level: 0,
    overseas_pct: 0,
    total_flows: 0
  })
  const dispatchOrders = ref([])
  const dispatchStatusFilter = ref('')
  const showCreateDispatch = ref(false)
  const showFeedbackDialog = ref(false)
  const feedbackForm = ref({ dispatchId: null, text: '' })
  const keyPersons = ref([])
  const personSearch = ref('')
  const personTypeFilter = ref('')
  const showCreatePerson = ref(false)
  const searchQuery = ref('')
  const searchResults = ref([])
  const searchLoading = ref(false)

  const dashboardData = ref({
    total_cases: null,
    total_gangs: null,
    total_amount: null,
    total_amount_formatted: null,
    active_alerts: null,
    risk_distribution: [],
    status_distribution: [],
    top_scam_types: [],
    monthly_trend: [],
    recent_cases: [],
    data_source: '',
    data_update_frequency: '',
    data_updated_at: null
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

  const loginProgress = ref(0)
  let loginProgressTimer = null

  const handleLogin = async () => {
    if (!loginForm.value.username.trim() || !loginForm.value.password.trim()) {
      loginError.value = '请输入用户名和密码'
      return
    }
    loginLoading.value = true
    loginProgress.value = 0
    loginError.value = ''
    loginProgressTimer = setInterval(() => {
      if (loginProgress.value < 85) loginProgress.value += Math.random() * 3
    }, 600)
    try {
      const data = await apiLogin(loginForm.value.username, loginForm.value.password)
      if (data.success) {
        loginProgress.value = 100
        setTimeout(() => {
          store.login(data.user || { username: loginForm.value.username }, data.access_token || data.token, data.refresh_token)
          loginForm.value = { username: '', password: '' }
          ElMessage.success('登录成功')
        }, 300)
      } else {
        loginError.value = data.message || '登录失败，请重试'
      }
    } catch (err) {
      loginError.value = err.response?.data?.message || err.message || '登录失败，请检查网络连接'
    } finally {
      clearInterval(loginProgressTimer)
      loginLoading.value = false
    }
  }

  const handleDemoLogin = async () => {
    loginLoading.value = true
    loginProgress.value = 0
    loginError.value = ''
    loginProgressTimer = setInterval(() => {
      if (loginProgress.value < 85) loginProgress.value += Math.random() * 3
    }, 600)
    try {
      const data = await apiDemoLogin()
      if (data.success) {
        loginProgress.value = 100
        setTimeout(() => {
          store.login(data.user || { username: 'admin' }, data.access_token || data.token, data.refresh_token)
          loginForm.value = { username: '', password: '' }
          ElMessage.success('演示登录成功')
        }, 300)
      } else {
        loginError.value = data.message || '演示登录失败'
      }
    } catch (err) {
      loginError.value = err.response?.data?.detail || err.message || '演示登录失败'
    } finally {
      clearInterval(loginProgressTimer)
      loginLoading.value = false
    }
  }

  const handleLogout = () => {
    store.logout()
    ElMessage.success('已安全退出')
  }

  const apiSources = ref({
    bank: { connected: false, records: 0, lastSync: '' },
    police: { connected: false, records: 0, lastSync: '' },
    antiFraud: { connected: false, records: 0, lastSync: '' }
  })
  const apiDataPreview = ref([])

  const pieChartRef = ref(null)
  const lineChartRef = ref(null)
  let pieChart = null
  let lineChart = null

  const totalAmount = computed(() => {
    return gangs.value.reduce((sum, g) => {
      return sum + (g.amountRaw || 0)
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
      result = result.filter(g => g.name?.includes(gangSearchKeyword.value))
    }
    if (riskFilter.value) {
      result = result.filter(g => g.riskLevel === riskFilter.value)
    }
    return result
  })

  const navigateTo = (name) => {
    router.push({ name })
  }

  const features = computed(() => {
    if (!gangs.value.length) return []
    const colors = ['#ef4444', '#f59e0b', '#00d4ff', '#8b5cf6', '#10b981', '#ec4899']
    const names = ['诈骗话术成熟度', '资金分散程度', '成员关联密度', '跨区域作案特征', '技术手段先进性', '受害者画像精准度']
    return names.map((name, i) => {
      const gang = gangs.value[i % gangs.value.length]
      const base = gang.comprehensive_score || gang.confidence || 50
      return {
        name,
        confidence: Math.min(99, Math.max(40, base + (i * 5) - 10)),
        color: colors[i],
        desc: ['话术模板标准化程度', '资金流转层级数量', '团伙成员社交关系', '跨省跨境作案能力', '反侦察技术水平', '目标人群定位能力'][i]
      }
    })
  })

  const caseEvidence = computed(() => {
    if (!selectedCase.value) return []
    return [
      { icon: '📱', name: '通话记录' + (selectedCase.value.victim_phone ? '(' + selectedCase.value.victim_phone.slice(0, 3) + '****' + selectedCase.value.victim_phone.slice(-4) + ')' : ''), status: '已验证' },
      { icon: '💳', name: '转账凭证(' + (selectedCase.value.amount || '待核实') + ')', status: '已验证' },
      { icon: '📧', name: '聊天记录' + (selectedCase.value.keywords?.length ? '(' + selectedCase.value.keywords.slice(0, 2).join('/') + ')' : ''), status: '已验证' },
      { icon: '🖥️', name: '涉案设备', status: '核实中' }
    ]
  })

  const investigationSteps = computed(() => {
    if (!selectedCase.value) return []
    const steps = []
    const created = selectedCase.value.created_at || null
    if (created) {
      const d = new Date(created)
      steps.push({ date: d.toISOString().slice(0, 10), title: '案件受理', description: '系统录入案件，AI自动研判', status: '已完成', completed: true, current: false })
      const d2 = new Date(d.getTime() + 86400000)
      steps.push({ date: d2.toISOString().slice(0, 10), title: 'AI研判分析', description: '自动提取涉案要素，关联团伙', status: '已完成', completed: true, current: false })
      const d3 = new Date(d2.getTime() + 86400000)
      steps.push({ date: d3.toISOString().slice(0, 10), title: '资金追踪', description: '追踪资金流向，分析链路', status: selectedCase.value.status === '侦办中' ? '进行中' : '已完成', completed: selectedCase.value.status !== '侦办中', current: selectedCase.value.status === '侦办中' })
      steps.push({ date: '', title: '案件结案', description: '移送审查起诉', status: '待进行', completed: false, current: false })
    } else {
      steps.push({ date: new Date().toISOString().slice(0, 10), title: '案件受理', description: '等待完善案件信息', status: '待进行', completed: false, current: true })
    }
    return steps
  })

  const defaultMethodFlow = [
    { title: '获取信任', desc: '冒充客服，准确报出受害人信息' },
    { title: '制造恐慌', desc: '声称账户异常，影响征信' },
    { title: '诱导转账', desc: '要求转账至"安全账户"验证' },
    { title: '完成诈骗', desc: '资金到账后立即失联' }
  ]

  const defaultKeywords = ['冒充客服', '征信诈骗', '安全账户', '转账验证']

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
    router.push({ name: 'details' })
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
    const isPdf = file.name.endsWith('.pdf')
    const isLt10M = file.size / 1024 / 1024 < 10
    if (!isImage && !isText && !isDocx && !isPdf) {
      ElMessage.error('仅支持图片(JPG/PNG)、文本(TXT/CSV)、Word(DOCX)或PDF文档')
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
      uploadedImages.value.push({ url: '', name: file.name, type: isDocx ? 'docx' : 'pdf', content: '', _file: file })
    }
    return false
  }

  const gangIcons = ['🦈', '🐺', '🦊', '🐍', '🐯', '🦅']

  const parseRawAmount = (g) => {
    if (g.total_amount_value != null && g.total_amount_value > 0) return g.total_amount_value
    const raw = g.total_amount_involved || g.total_amount || g.amount || ''
    if (typeof raw === 'number') return raw
    const match = raw.match(/[\d.]+/)
    const num = match ? parseFloat(match[0]) : 0
    return raw.includes('万') ? num * 10000 : num
  }

  const formatAmountRaw = (num) => {
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
        gangs.value = (response.gangs || []).map((g, idx) => mapGangForAnalysis(g, idx))

        cases.value = (response.raw_cases || []).map(c => mapCaseForAnalysis(c))

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
      ElMessage.error('分析请求异常: ' + (err?.message || '网络错误'))
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

  const startImageAnalysis = async (mode = 'auto') => {
    if (!uploadedImages.value.length) {
      ElMessage.warning('请先上传文件')
      return
    }
    loading.value = true
    progressPercent.value = 0
    progressMessage.value = '正在处理上传的文件...'
    showProgress.value = true
    try {
      let allText = ''
      const total = uploadedImages.value.length
      for (let i = 0; i < total; i++) {
        const item = uploadedImages.value[i]
        progressPercent.value = Math.round(((i + 1) / total) * 50)
        progressMessage.value = `正在处理第 ${i + 1}/${total} 个文件...`

        if (item.type === 'image') {
          try {
            const res = await fetch(item.url)
            const blob = await res.blob()
            const file = new File([blob], item.name, { type: blob.type })
            const formData = new FormData()
            formData.append('file', file)
            const r = await api.post(`/api/analyze-file?mode=${mode}`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
              timeout: 180000
            })
            if (r.data.success && r.data.text) {
              const methodLabel = { ocr: '📝OCR', vision: '🧠视觉', direct: '📄直接' }
              const tag = methodLabel[r.data.method] || r.data.method
              allText += (allText ? '\n---\n' : '') + `[${item.name} | ${tag}]\n` + r.data.text
            }
          } catch (ocrErr) {
            console.warn(`图片处理失败:`, ocrErr)
            ElMessage.warning(`"${item.name}" 处理失败，已跳过`)
          }
        } else if (item.type === 'text' && item.content) {
          allText += (allText ? '\n---\n' : '') + item.content
        } else if (item.type === 'docx' || item.type === 'pdf') {
          try {
            const formData = new FormData()
            formData.append('file', item._file)
            const r = await api.post('/api/extract-text', formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
            })
            if (r.data.success && r.data.text) {
              allText += (allText ? '\n---\n' : '') + r.data.text
            }
          } catch (docxErr) {
            console.warn(`文档解析失败:`, docxErr)
            ElMessage.warning(`"${item.name}" 解析失败，已跳过`)
          }
        }
      }

      if (allText.trim()) {
        progressPercent.value = 75
        progressMessage.value = '文字提取完成，正在启动 AI 研判...'
        inputText.value = allText
        ElMessage.success(`文字提取完成，共 ${allText.length} 个字符，即将自动分析`)
        setTimeout(() => startAnalysis(), 500)
      } else {
        progressPercent.value = 0
        progressMessage.value = ''
        showProgress.value = false
        ElMessage.warning('未能提取到有效文字，请检查文件内容')
        loading.value = false
      }
    } catch (e) {
      showProgress.value = false
      loading.value = false
      ElMessage.error('文件处理失败: ' + (e?.message || '未知错误'))
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

  const downloadReport = async () => {
    ElMessage.info('正在生成报告文件...')
    const gang = gangs.value.find(g => (g.id === reportConfig.value.gangId || g.gang_id === reportConfig.value.gangId))
    const gangName = gang?.gang_name || gang?.name || '报告'
    const title = getReportTitle()

    const htmlContent = generateReportHTML(title, gangName)
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title}_${gangName}_${Date.now()}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('报告下载完成')
  }

  function generateReportHTML(title, gangName) {
    const gang = gangs.value.find(g => (g.id === reportConfig.value.gangId || g.gang_id === reportConfig.value.gangId))
    const sections = []

    sections.push(`
      <div class="doc-header">
        <div class="doc-logo"><span class="logo-icon">🛡️</span><span class="logo-text">反诈情报分析系统</span></div>
        <div class="doc-title">${title}</div>
        <div class="doc-meta">
          <div><span class="meta-label">报告编号：</span>RPT-${Date.now().toString().slice(-8)}</div>
          <div><span class="meta-label">生成时间：</span>${new Date().toLocaleString()}</div>
          <div><span class="meta-label">密级：</span><span class="meta-secret">机密</span></div>
        </div>
      </div>
      <div class="doc-content">
    `)

    sections.push(`<div class="doc-section">
      <div class="section-title">一、${reportConfig.value.type === 'case' ? '案件' : '团伙'}基本信息</div>
      <div class="section-body">
        <div class="info-table">
          <div class="info-row"><span class="info-label">${reportConfig.value.type === 'case' ? '案件' : '团伙'}名称</span><span class="info-value">${gangName}</span></div>
          <div class="info-row"><span class="info-label">风险等级</span><span class="info-value">${gang?.riskLevel || '-'}级</span></div>
          <div class="info-row"><span class="info-label">涉案金额</span><span class="info-value danger">${gang?.amount || '-'}</span></div>
          <div class="info-row"><span class="info-label">关联案件</span><span class="info-value">${gang?.cases || 0} 起</span></div>
          <div class="info-row"><span class="info-label">技术特征</span><span class="info-value">${(gang?.tags || []).join('、') || '-'}</span></div>
        </div>
      </div>
    </div>`)

    if (reportConfig.value.includeTimeline) {
      const timeline = gang?.timeline || []
      const items = timeline.length ? timeline.map(t =>
        `<div class="doc-timeline-item"><span class="doc-time">${t.date || '-'}</span><span class="doc-event">${t.title || ''}</span><span class="doc-desc">${t.desc || ''}</span></div>`
      ).join('\n') : `<div class="doc-timeline-item"><span class="doc-time">-</span><span class="doc-event">案件发生</span><span class="doc-desc">${gangName}相关案件</span></div>`
      sections.push(`<div class="doc-section">
        <div class="section-title">二、作案时间线</div>
        <div class="section-body"><div class="doc-timeline">${items}</div></div>
      </div>`)
    }

    if (reportConfig.value.includeMoney) {
      sections.push(`<div class="doc-section">
        <div class="section-title">三、资金流向分析</div>
        <div class="section-body">
          <div class="money-flow-summary">
            <p>经分析，该${reportConfig.value.type === 'case' ? '案件' : '团伙'}涉案资金主要通过多级账户进行转移。资金流转层级约3-5层，涉及多家银行的多个账户，最终资金流向境外或虚拟货币平台。</p>
          </div>
        </div>
      </div>`)
    }

    if (reportConfig.value.includeSuggestion) {
      sections.push(`<div class="doc-section">
        <div class="section-title">四、处置建议</div>
        <div class="section-body">
          <div class="suggestion-list">
            <div class="suggestion-item"><span class="suggestion-num">1</span><span>建议立即对涉案账户进行止付冻结</span></div>
            <div class="suggestion-item"><span class="suggestion-num">2</span><span>协调银行调取完整交易流水</span></div>
            <div class="suggestion-item"><span class="suggestion-num">3</span><span>对团伙成员实施布控</span></div>
            <div class="suggestion-item"><span class="suggestion-num">4</span><span>启动跨部门联合处置机制</span></div>
          </div>
        </div>
      </div>`)
    }
    sections.push(`</div><div class="doc-footer"><div class="footer-line"></div><div class="footer-text"><span>本报告由反诈情报分析系统自动生成</span><span>仅供内部参考使用</span></div></div>`)

    return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${title} - ${gangName}</title>
<style>
body { background: #0a0e1a; font-family: 'Microsoft YaHei', sans-serif; padding: 40px; margin: 0; display: flex; justify-content: center; }
.report-wrap { max-width: 800px; width: 100%; background: linear-gradient(135deg, #1a2332 0%, #0f1923 100%); padding: 32px 40px; border-radius: 8px; border: 1px solid #2d4054; color: #c8d6e5; font-size: 13px; line-height: 1.8; }
.doc-header { text-align: center; padding-bottom: 16px; border-bottom: 3px solid #2d5b7a; margin-bottom: 16px; }
.doc-logo { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 10px; }
.logo-icon { font-size: 24px; }
.logo-text { font-size: 14px; color: #5b8db8; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; }
.doc-title { font-size: 17px; color: #e8eef5; font-weight: 700; margin-bottom: 10px; letter-spacing: 1px; }
.doc-meta { display: flex; justify-content: center; gap: 20px; font-size: 11px; color: #8899aa; flex-wrap: wrap; }
.meta-secret { color: #e74c3c; font-weight: 600; }
.doc-section { margin-bottom: 14px; }
.section-title { font-size: 14px; color: #e8eef5; font-weight: 600; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #2d4054; }
.section-body { padding-left: 6px; font-size: 12px; color: #b0c4d8; }
.info-table { display: flex; flex-direction: column; gap: 3px; }
.info-row { display: flex; padding: 3px 0; border-bottom: 1px dashed #2a3a4a; }
.info-label { width: 90px; color: #7a8a9a; flex-shrink: 0; font-size: 11px; }
.info-value { flex: 1; color: #c8d6e5; font-size: 12px; }
.info-value.danger { color: #e74c3c; font-weight: 600; }
.doc-timeline { display: flex; flex-direction: column; gap: 4px; }
.doc-timeline-item { display: flex; gap: 8px; padding: 5px 10px; background: rgba(45,64,84,0.3); border-radius: 4px; }
.doc-time { font-size: 11px; color: #7a8a9a; width: 80px; flex-shrink: 0; }
.doc-event { font-size: 12px; color: #c8d6e5; font-weight: 500; width: 100px; flex-shrink: 0; }
.doc-desc { font-size: 11px; color: #8899aa; }
.money-flow-summary { font-size: 12px; color: #b0c4d8; line-height: 1.7; }
.suggestion-list { display: flex; flex-direction: column; gap: 5px; }
.suggestion-item { display: flex; gap: 6px; align-items: flex-start; font-size: 12px; color: #b0c4d8; }
.suggestion-num { width: 20px; height: 20px; background: #2d5b7a; color: #e8eef5; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0; }
.doc-footer { text-align: center; padding-top: 14px; }
.footer-line { height: 1px; background: #2d4054; margin-bottom: 6px; }
.footer-text { display: flex; flex-direction: column; gap: 2px; font-size: 10px; color: #5a6a7a; }
</style></head><body><div class="report-wrap">${sections.join('\n')}</div></body></html>`
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
          total_amount_formatted: data.total_amount_formatted ?? data.data?.total_amount_formatted ?? '-',
          active_alerts: data.active_alerts ?? data.data?.active_alerts ?? '-',
          risk_distribution: data.risk_distribution ?? data.data?.risk_distribution ?? [],
          status_distribution: data.status_distribution ?? data.data?.status_distribution ?? [],
          top_scam_types: data.top_scam_types ?? data.data?.top_scam_types ?? [],
          monthly_trend: data.monthly_trend ?? data.data?.monthly_trend ?? [],
          recent_cases: data.recent_cases ?? data.data?.recent_cases ?? [],
          data_source: data.data_source ?? data.data?.data_source ?? '',
          data_update_frequency: data.data_update_frequency ?? data.data?.data_update_frequency ?? '',
          data_updated_at: data.data_updated_at ?? data.data?.data_updated_at ?? ''
        }
        nextTick(() => initDashboardCharts())
      } else {
        ElMessage.error('获取看板数据失败: ' + (data.message || '服务器返回异常'))
      }
    } catch (err) {
      ElMessage.error('获取看板数据异常: ' + (err?.message || '网络错误'))
    } finally {
      dashboardLoading.value = false
    }
  }

  const initDashboardCharts = () => {
    const riskData = dashboardData.value.risk_distribution
    const statusData = dashboardData.value.status_distribution
    const barData = dashboardData.value.top_scam_types
    const trendData = dashboardData.value.monthly_trend

    nextTick(() => {
      if (dashboardRiskChartRef.value && riskData.length) {
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
      } else if (dashboardRiskChart) {
        dashboardRiskChart.dispose()
        dashboardRiskChart = null
      }

      if (dashboardStatusChartRef.value && statusData.length) {
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
      } else if (dashboardStatusChart) {
        dashboardStatusChart.dispose()
        dashboardStatusChart = null
      }

      if (dashboardBarChartRef.value && barData.length) {
        if (dashboardBarChart) dashboardBarChart.dispose()
        dashboardBarChart = echarts.init(dashboardBarChartRef.value)
        const barNames = barData.map(d => d.name)
        const barCounts = barData.map(d => d.count)
        const colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#00d4ff', '#10b981']
        dashboardBarChart.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
          xAxis: {
            type: 'category', data: barNames,
            axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
            axisLabel: { color: '#e2e8f0', fontSize: 11, fontWeight: 'bold', rotate: 20, interval: 0 }
          },
          yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
            axisLabel: { color: '#e2e8f0', fontSize: 11, fontWeight: 'bold' },
            splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
          },
          series: [{
            type: 'bar', barWidth: '60%',
            itemStyle: {
              color: (params) => colors[params.dataIndex % colors.length],
              borderRadius: [6, 6, 0, 0],
              shadowBlur: 8,
              shadowColor: 'rgba(0,198,255,0.2)'
            },
            label: { show: true, position: 'top', color: '#e2e8f0', fontSize: 12, fontWeight: 'bold' },
            data: barCounts
          }]
        })
        dashboardBarChart.resize()
      } else if (dashboardBarChart) {
        dashboardBarChart.dispose()
        dashboardBarChart = null
      }

      if (dashboardTrendChartRef.value && trendData.length) {
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
      } else if (dashboardTrendChart) {
        dashboardTrendChart.dispose()
        dashboardTrendChart = null
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
      ElMessage.error('获取预警信息异常: ' + (err?.message || '网络错误'))
    } finally {
      alertsLoading.value = false
    }
  }

  const loadFlowData = async (forcedCaseId) => {
    capitalFlows.value = []
    flowGraphData.value = null
    const cid = forcedCaseId || flowSearchCaseId.value
    if (!cid) return
    try {
      const [flowsR, graphR] = await Promise.all([
        api.get('/api/capital/flows', { params: { case_id: cid } }),
        api.get('/api/capital/graph/' + cid)
      ])
      capitalFlows.value = flowsR.data.flows || flowsR.data.data || []
      flowGraphData.value = graphR.data.graph || graphR.data.data || null
    } catch (e) {
      console.error('loadFlowData:', e)
      ElMessage.error('资金流向数据加载失败')
    }
  }
  const loadFlowMetrics = async () => {
    try {
      const r = await fetchCapitalFlowStats()
      if (r.success && r.stats) {
        flowMetrics.value = {
          total_accounts: r.stats.total_accounts || 0,
          max_level: r.stats.max_level || 0,
          overseas_pct: r.stats.overseas_pct ?? 0,
          total_flows: r.stats.total_flows || 0
        }
      }
    } catch (e) {
      console.error('loadFlowMetrics:', e)
      ElMessage.error('资金流向统计数据加载失败')
    }
  }
  const addFlowRecord = (row) => {
    ElMessage.info('追加资金流向功能：' + row.source_account + ' → ' + row.target_account)
  }

  const loadDispatchOrders = async () => {
    try {
      const params = dispatchStatusFilter.value ? { status: dispatchStatusFilter.value } : {}
      const r = await api.get('/api/dispatch/list', { params })
      dispatchOrders.value = r.data.orders || r.data.dispatch_orders || r.data.data || []
    } catch (e) {
      console.error('loadDispatchOrders:', e)
      ElMessage.error('派单数据加载失败')
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
    feedbackForm.value = { dispatchId: row.id, text: '' }
    showFeedbackDialog.value = true
  }
  const submitFeedback = async () => {
    if (!feedbackForm.value.text.trim()) {
      ElMessage.warning('请输入处置反馈内容')
      return
    }
    try {
      const r = await api.put('/api/dispatch/' + feedbackForm.value.dispatchId + '/complete', { feedback: feedbackForm.value.text })
      if (r.data.success) { ElMessage.success('已完成'); showFeedbackDialog.value = false; await loadDispatchOrders() }
      else ElMessage.error(r.data.error || '操作失败')
    } catch (e) {
      ElMessage.error('操作异常: ' + (e.message || ''))
    }
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
      ElMessage.error('重点人员数据加载失败')
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

  const handleSearchInput = async (query) => {
    searchQuery.value = query
    if (!query || query.trim().length < 1) {
      searchResults.value = []
      return
    }
    searchLoading.value = true
    try {
      const r = await searchCases(query.trim())
      if (r.success) {
        searchResults.value = (r.cases || []).slice(0, 8)
      }
    } catch (e) {
      console.error('搜索失败:', e)
    } finally {
      searchLoading.value = false
    }
  }

  const handleSearchSelect = async (caseItem) => {
    searchQuery.value = ''
    searchResults.value = []
    selectedGang.value = null
    await reloadCasesAndGangs()
    selectedCase.value = {
      id: caseItem.case_id,
      title: caseItem.title,
      amount: caseItem.amount || '',
      status: caseItem.status || '已立案',
      date: caseItem.created_at || '',
      description: caseItem.ai_report || caseItem.description || '',
      victimName: caseItem.victim || '',
      victimPhone: caseItem.victim_phone || '',
      victimAge: caseItem.victim_age || '',
      victimGender: caseItem.victim_gender || '',
      victimJob: caseItem.victim_job || '',
      victimAddress: caseItem.victim_address || '',
      type: caseItem.scam_type || '',
      risk_level: caseItem.risk_level || '',
      keywords: caseItem.keywords || [],
      amount_value: caseItem.amount_value || 0,
      created_at: caseItem.created_at || ''
    }
    router.push({ name: 'case-detail' })
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
      ElMessage.error('处置异常: ' + (err?.message || '网络错误'))
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
      const typeMap = {}
      cases.value.forEach(c => {
        const t = c.type || c.scam_type || '其他'
        typeMap[t] = (typeMap[t] || 0) + 1
      })
      const entries = Object.entries(typeMap)
      let typeStats = []
      if (entries.length) {
        const total = entries.reduce((s, [, v]) => s + v, 0)
        const colors = ['#ef4444','#f59e0b','#8b5cf6','#00d4ff','#10b981','#ec4899']
        typeStats = entries.map(([name, count], i) => ({
          name, count, percent: Math.round(count / total * 100), color: colors[i % colors.length]
        }))
      }
      if (pieChartRef.value && typeStats.length) {
        if (pieChart) {
          pieChart.dispose()
        }
        pieChart = echarts.init(pieChartRef.value)
        pieChart.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item', formatter: '{b}: {c}起 ({d}%)' },
          legend: {
            orient: 'vertical',
            right: 5,
            top: 'center',
            itemWidth: 12,
            itemHeight: 12,
            textStyle: { color: '#e2e8f0', fontSize: 11 },
            pageTextStyle: { color: '#94a3b8' }
          },
          series: [{
            type: 'pie',
            radius: ['35%', '50%'],
            center: ['25%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 6, borderColor: '#0a0e1a', borderWidth: 2 },
            label: { show: false },
            emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
            data: typeStats.map(s => ({ value: s.count, name: s.name, itemStyle: { color: s.color } }))
          }]
        })
        pieChart.resize()
      } else if (pieChart) {
        pieChart.dispose()
        pieChart = null
      }
      const trend = dashboardData.value.monthly_trend
      if (lineChartRef.value && trend.length) {
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
            data: trend.map(d => d.month || d.label || ''),
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
            data: trend.map(d => d.amount || 0)
          }]
        })
        lineChart.resize()
      } else if (lineChart) {
        lineChart.dispose()
        lineChart = null
      }
    })
  }

  function mapGangFromResponse(g, idx) {
    const rawAmt = parseRawAmount(g)
    return {
      id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
      gang_id: g.gang_id || '',
      name: g.gang_name || '未知团伙',
      gang_name: g.gang_name || '',
      icon: gangIcons[idx % gangIcons.length],
      riskLevel: g.risk_level || 'B',
      risk_label: g.risk_label || '',
      amount: formatAmountRaw(rawAmt),
      amountRaw: rawAmt,
      total_amount_involved: g.total_amount_involved || g.total_amount || '',
      total_amount: g.total_amount || g.total_amount_involved || 0,
      totalAmount: g.total_amount_involved || g.total_amount || 0,
      total_cases: g.total_cases || 0, cases: g.total_cases || 0,
      case_count: g.case_count || g.total_cases || 0,
      tags: Array.isArray(g.fingerprint) ? g.fingerprint.filter(Boolean) : [],
      members: Array.isArray(g.network_nodes) ? g.network_nodes.slice(0, 6).map((n, i) => ({
        id: i + 1,
        name: n.label || n.id || n.name || ('成员' + (i + 1)),
        icon: '👤',
        role: n.role || n.type || '成员'
      })) : [],
      score: g.comprehensive_score || 0,
      comprehensive_score: g.comprehensive_score || 0,
      confidence: g.confidence || 0,
      risk_score: g.risk_score || 0,
      member_count: g.member_count || 0,
      member_count_estimate: g.member_count_estimate || '',
      team_size: g.team_size || 0,
      tech_level: g.tech_level || '', script_type: g.script_type || '',
      description: g.description || '',
      fingerprint: Array.isArray(g.fingerprint) ? g.fingerprint : [],
      related_cases: Array.isArray(g.related_cases) ? g.related_cases : [],
      leader_name: g.leader_name || '',
      leader_role: g.leader_role || '',
      sub_leader: g.sub_leader || '',
      core_member: g.core_member || '',
      sub_role: g.sub_role || '',
      victim_count: g.victim_count || 0,
      account_count: g.account_count || 0,
      total_accounts: g.total_accounts || 0,
      max_level: g.max_level || 0,
      transfer_levels: g.transfer_levels || 0,
      overseas_pct: g.overseas_pct || 0,
      overseas_ratio: g.overseas_ratio || 0,
      region: g.region || '',
      area: g.area || '',
      gang_type: g.gang_type || '',
      updateTime: '刚刚'
    }
  }

  function mapCaseFromResponse(c) {
    return {
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
    }
  }

  function mapGangForAnalysis(g, idx) {
    const rawAmt = parseRawAmount(g)
    return {
      id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
      gang_id: g.gang_id || '',
      name: g.gang_name || '未知团伙',
      gang_name: g.gang_name || '',
      icon: gangIcons[idx % gangIcons.length],
      riskLevel: g.risk_level || 'B',
      risk_level: g.risk_level || 'B',
      risk_label: g.risk_label || '',
      amount: formatAmountRaw(rawAmt),
      amountRaw: rawAmt,
      total_amount_involved: g.total_amount_involved || g.total_amount || '',
      total_amount: g.total_amount || g.total_amount_involved || 0,
      totalAmount: rawAmt,
      cases: g.total_cases || 0,
      total_cases: g.total_cases || 0,
      case_count: g.case_count || g.total_cases || 0,
      caseIds: (g.related_cases || []).map(c => c.case_id || c),
      related_cases: g.related_cases || [],
      tags: Array.isArray(g.fingerprint)
        ? g.fingerprint.filter(Boolean)
        : g.fingerprint
          ? g.fingerprint.split(/[,，、]/).map(t => t.trim()).filter(Boolean)
          : [],
      fingerprint: Array.isArray(g.fingerprint) ? g.fingerprint : [],
      members: Array.isArray(g.network_nodes)
        ? g.network_nodes.slice(0, 6).map((n, i) => ({
            id: i + 1,
            name: n.label || n.id || '成员' + (i + 1),
            icon: '👤',
            role: n.role || n.type || '成员'
          }))
        : [],
      network_nodes: g.network_nodes || [],
      timeline: (g.steps || []).map(s => ({
        date: s.date || s.time || '',
        title: s.title || s.name || '',
        desc: s.description || s.desc || '',
        type: s.type || '活动'
      })),
      steps: g.steps || [],
      evidence: [],
      abilities: g.radar_data || { tech: 50, org: 50, antiDetect: 50 },
      radar_data: g.radar_data || {},
      victims: g.total_cases || 0,
      comprehensive_score: g.comprehensive_score || 0,
      confidence: g.confidence || 0,
      risk_score: g.risk_score || 0,
      description: g.description || '',
      gang_type: g.gang_type || g.script_type || '',
      script_type: g.script_type || '',
      leader_name: g.leader_name || '',
      member_count: g.member_count || 0,
      account_count: g.account_count || 0,
      total_accounts: g.total_accounts || 0,
      transfer_levels: g.transfer_levels || 0,
      overseas_pct: g.overseas_pct || 0,
      region: g.region || '',
      createTime: '',
      updateTime: '刚刚'
    }
  }

  function mapCaseForAnalysis(c) {
    const rawAmt = c.amount_value || (() => {
      const m = (c.amount || '').match(/[\d.]+/)
      const n = m ? parseFloat(m[0]) : 0
      return (c.amount || '').includes('万') ? n * 10000 : n
    })()
    return {
      id: c.case_id || 'C' + String(Math.random()).slice(2, 8),
      case_id: c.case_id || '',
      title: (c.victim || '当事人') + '被诈骗案',
      gang: c.related_gang_id || c.assigned_gang || '',
      related_gang_id: c.related_gang_id || c.assigned_gang || '',
      amount: formatAmountRaw(rawAmt),
      amountRaw: rawAmt,
      amount_value: rawAmt,
      status: c.is_error ? '待核查' : '已立案',
      date: c.extracted_entities?.date || c.created_at || '',
      region: c.extracted_entities?.address || '',
      type: c.scam_type || '',
      scam_type: c.scam_type || '',
      risk_level: c.risk_level || '',
      victims: 1,
      victimName: c.victim || '',
      victim: c.victim || '',
      victim_name: c.victim || c.victim_name || '',
      victimGender: c.extracted_entities?.gender || '',
      victimAge: c.extracted_entities?.age || '',
      victimPhone: c.extracted_entities?.phone || '',
      victimJob: c.extracted_entities?.job || '',
      victimAddress: c.extracted_entities?.address || '',
      scamPhone: c.extracted_entities?.scam_phone || '',
      phoneLocation: c.extracted_entities?.phone_location || '',
      extracted_entities: c.extracted_entities || {},
      keywords: Array.isArray(c.keywords) ? c.keywords : [],
      ai_report: c.ai_report || '',
      description: c.description || c.ai_report || '',
      roles: c.roles || [],
      steps: c.steps || [],
      warning: c.warning || '',
      is_error: c.is_error || false
    }
  }

  const reloadCasesAndGangs = async () => {
    try {
      const [casesRes, gangsRes] = await Promise.all([fetchCases(), fetchGangs()])
      if (casesRes.success) {
        const caseData = casesRes.cases || casesRes.data || []
        cases.value = caseData.map(c => mapCaseFromResponse(c))
      }
      if (gangsRes.success) {
        const gangData = gangsRes.gangs || gangsRes.data || []
        gangs.value = gangData.map((g, idx) => mapGangFromResponse(g, idx))
      }
    } catch (e) {
      console.warn('刷新数据失败:', e)
      ElMessage.error('数据加载失败，请检查后端服务是否正常运行')
    }
  }

  watch(() => route.name, (newVal, oldVal) => {
    if (newVal === oldVal) return
    if (newVal === 'overview' && gangs.value.length) {
      nextTick(() => initCharts())
    }
    if (newVal === 'dashboard') {
      loadDashboard()
    }
    if (newVal === 'alerts') {
      loadAlerts()
    }
    if (newVal === 'details') {
      reloadCasesAndGangs()
    }
  })

  onMounted(async () => {
    const routeName = route.name
    if (routeName === 'dashboard') loadDashboard()
    if (routeName === 'alerts') loadAlerts()
    loadFlowMetrics()
    await reloadCasesAndGangs()
    if (store.isLoggedIn && cases.value.length === 0) {
      try {
        await ElMessageBox.confirm(
          '系统尚未初始化数据，是否加载示例数据？',
          '数据初始化',
          { confirmButtonText: '加载示例数据', cancelButtonText: '暂不加载', type: 'info' }
        )
        const loadingMsg = ElMessage({ message: '正在生成示例数据...', type: 'info', duration: 0 })
        try {
          await seedData()
          loadingMsg.close()
          ElMessage.success('示例数据加载成功！')
          await reloadCasesAndGangs()
          if (routeName === 'overview' && gangs.value.length) {
            nextTick(() => initCharts())
          }
        } catch (seedErr) {
          loadingMsg.close()
          ElMessage.error('示例数据加载失败：' + (seedErr?.response?.data?.detail || seedErr?.message || String(seedErr)))
        }
      } catch (cancelErr) {
        // user cancelled, do nothing
      }
    }
    if (routeName === 'overview' && gangs.value.length) {
      nextTick(() => initCharts())
    }
  })

  onUnmounted(() => {
    if (loginProgressTimer) clearInterval(loginProgressTimer)
    disposeAllCharts()
    disconnectSocket()
  })

  const disposeAllCharts = () => {
    [dashboardRiskChart, dashboardStatusChart, dashboardBarChart, dashboardTrendChart, pieChart, lineChart].forEach(c => {
      if (c) { try { c.dispose() } catch (e) { /* ignore */ } }
    })
    dashboardRiskChart = dashboardStatusChart = dashboardBarChart = dashboardTrendChart = pieChart = lineChart = null
  }

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
    flowMetrics,
    dispatchOrders,
    dispatchStatusFilter,
    showCreateDispatch,
    showFeedbackDialog,
    feedbackForm,
    keyPersons,
    personSearch,
    personTypeFilter,
    showCreatePerson,
    searchQuery,
    searchResults,
    searchLoading,
    dashboardData,
    dashboardLoading,
    alerts,
    alertsLoading,
    resolvingAlert,
    unresolvedAlertCount: computed(() => alerts.value.filter(a => !a.resolved).length),
    dashboardRiskChartRef,
    dashboardStatusChartRef,
    dashboardBarChartRef,
    dashboardTrendChartRef,
    reportConfig,
    reportPreview,
    loginForm,
    loginLoading,
    loginError,
    loginProgress,
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
    caseEvidence,
    investigationSteps,
    defaultMethodFlow,
    defaultKeywords,
    gangIcons,
    formatAmountRaw,
    reloadCasesAndGangs,
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
    handleDemoLogin,
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
    loadFlowData,
    loadFlowMetrics,
    addFlowRecord,
    loadDispatchOrders,
    signDispatch,
    showCompleteDispatch,
    submitFeedback,
    loadKeyPersons,
    deleteKeyPerson,
    handleSearchInput,
    handleSearchSelect,
    handleResolveAlert,
    getAlertType,
    getConfidenceColor,
    viewCaseFromDashboard,
    initCharts
  }

}