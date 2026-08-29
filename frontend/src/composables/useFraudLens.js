import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// echarts 懒加载：App.vue 在根组件注入本 composable，静态 import 会让
// 首屏（Showcase 首页，零图表）也被迫下载 ~1MB 的 echarts chunk。
// 注册逻辑见 ./useEcharts.js，三处共用一份。
import { useRouter, useRoute } from 'vue-router'
import { store } from '../store.js'
import { useCachedLoader } from './useAppState.js'
import {
  defaultMethodFlow, defaultKeywords, gangIcons,
  getParticleStyle, getRiskType, getEventType, getFeatureIcon,
  parseRawAmount, formatAmountRaw, formatCaseAmountText
} from './utils.js'
import { useAuth } from './useAuth.js'
import { getEcharts } from './useEcharts.js'
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
  importFundFlow,
  seedData,
  searchCases,
  getMe,
  fetchGangReviewResults,
  generateCaseReport,
  generateGangReport
} from '../api.js'

// 公安办案文书（红头文件）打印样式：预览组件与打印/下载窗口共用类名 rd-*。
// 白底黑字、宋体、A4 版式，@media print 时去掉屏幕留白。
const REPORT_DOC_CSS = `
* { box-sizing: border-box; }
body { background: #e9edf2; margin: 0; padding: 24px; font-family: 'SimSun', 'Songti SC', 'Microsoft YaHei', serif; }
.report-doc { max-width: 794px; margin: 0 auto; background: #fff; color: #1a1a1a; padding: 46px 56px 40px; box-shadow: 0 2px 14px rgba(0,0,0,.18); line-height: 1.9; font-size: 15px; }
.rd-org { text-align: center; color: #c00000; font-size: 30px; font-weight: 700; letter-spacing: 2px; font-family: 'SimHei', 'Microsoft YaHei', sans-serif; }
.rd-title { text-align: center; font-size: 21px; font-weight: 700; margin: 14px 0 8px; letter-spacing: 3px; }
.rd-meta { text-align: center; font-size: 13px; color: #333; margin-bottom: 6px; }
.rd-meta span { margin: 0 10px; }
.rd-secret { color: #c00000; }
.rd-redline { height: 2.5px; background: #c00000; margin: 6px 0 22px; }
.rd-section { margin-bottom: 18px; }
.rd-sec-title { font-size: 16.5px; font-weight: 700; font-family: 'SimHei', 'Microsoft YaHei', sans-serif; margin-bottom: 8px; }
.doc-table { width: 100%; border-collapse: collapse; }
.doc-table td { border: 1px solid #8a8a8a; padding: 6px 10px; font-size: 14px; vertical-align: middle; }
.dt-label { width: 120px; background: #f4f4f4; font-weight: 700; text-align: center; }
.dt-value.danger { color: #c00000; font-weight: 700; }
.doc-para { text-indent: 2em; margin: 6px 0; }
.doc-ol { margin: 6px 0; padding-left: 26px; }
.doc-ol li { margin-bottom: 4px; }
.rd-sign { margin-top: 34px; text-align: right; font-size: 15px; }
.rd-sign-date { margin-top: 6px; padding-right: 40px; }
.rd-footer { margin-top: 26px; border-top: 1px solid #999; padding-top: 8px; font-size: 11px; color: #888; text-align: center; }
@media print {
  body { background: #fff; padding: 0; }
  .report-doc { box-shadow: none; max-width: none; margin: 0; }
}
`

export function useFraudLens() {
  const router = useRouter()
  const route = useRoute()
  const { cachedLoad, invalidateCache } = useCachedLoader()

  // ===== 认证模块（拆分自 useFraudLens） =====
  // 注意：onLoginSuccess 引用后续定义的加载函数，闭包调用时求值（登录发生在组件挂载后，已定义）
  const auth = useAuth({
    store,
    route,
    apiLogin,
    apiDemoLogin,
    ElMessage,
    onLoginSuccess: async () => {
      reloadCasesAndGangs()
      loadFlowMetrics()
      const name = route.name
      if (name === 'dashboard') loadDashboard()
      if (name === 'alerts') loadAlerts()
      if (name === 'groups') loadGangReview()
    }
  })

  const activeMenu = computed(() => route.name || 'input')
  const loading = ref(false)
  // 案件/团伙首次加载是否完成（登录成功后触发）；未完成前列表页显示骨架屏
  const casesReady = ref(false)
  const showProgress = ref(false)
  const showResult = ref(false)
  const progressPercent = ref(0)
  const progressMessage = ref('正在初始化...')
  const resultStats = ref({ cases: 0, gangs: 0, time: '0s' })
  const analysisStartTime = ref(0)
  const inputText = ref('')
  const uploadedImages = ref([])
  // 资金流水导入（真实材料接入 Phase4）：随 /agent-analyze 的 accounts_tx 提交
  const fundFlowTx = ref([])
  const fundFlowFileName = ref('')
  const gangs = ref([])
  const cases = ref([])
  // ===== 复核解释层（gang_reviewer Skill A/B）=====
  // explanations: 每团伙的并案依据；review: 可疑误并探测结果
  const gangReview = ref({ explanations: [], review: null, llmEnabled: false, error: '' })
  const gangReviewLoading = ref(false)
  // REQ-S7 失败边界诚实提示：后端透传的异常卡 / 告警 / 四单流转
  const analysisAbnormal = ref({ abnormal: 'none', detail: null })
  const analysisWarnings = ref([])
  const analysisSlips = ref(null)
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
  const lastImportedCaseIds = ref([])

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
  const dashboardRadarChartRef = ref(null)
  let dashboardRiskChart = null
  let dashboardStatusChart = null
  let dashboardBarChart = null
  let dashboardTrendChart = null
  let dashboardRadarChart = null
  // 饼图点击联动：risk / status 过滤
  const dashboardRiskFilter = ref('')
  const dashboardStatusFilter = ref('')

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

  const recentCases = computed(() => {
    if (!lastImportedCaseIds.value.length) return []
    return cases.value.filter(c => lastImportedCaseIds.value.includes(c.case_id || c.id))
  })

  const totalAmount = computed(() => {
    return gangs.value.reduce((sum, g) => {
      return sum + (g.amountRaw || 0)
    }, 0)
  })

  const totalAmountFormatted = computed(() => formatAmountRaw(totalAmount.value))

  const successRate = ref(null)

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
        confidence: Math.min(99, Math.max(0, base)),
        color: colors[i],
        desc: ['话术模板标准化程度', '资金流转层级数量', '团伙成员社交关系', '跨省跨境作案能力', '反侦察技术水平', '目标人群定位能力'][i]
      }
    })
  })

  const caseEvidence = computed(() => {
    return []
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

  const getGangById = (id) => gangs.value.find(g => g.id === id)
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
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    const isPdf = file.name.endsWith('.pdf')
    const isLt10M = file.size / 1024 / 1024 < 10
    if (!isImage && !isText && !isDocx && !isPdf) {
      ElMessage.error('仅支持图片(JPG/PNG)、文本(TXT/CSV)、Word(DOCX/DOC)或PDF文档')
      return false
    }
    if (!isLt10M) {
      ElMessage.error('文件大小不能超过 10MB')
      return false
    }
    const reader = new FileReader()
    reader.onload = (e) => {
      const item = {
        url: isImage ? e.target.result : '',
        name: file.name,
        type: isText ? 'text' : isImage ? 'image' : isDocx ? 'docx' : 'pdf',
        content: isText ? e.target.result : (isImage ? '' : e.target.result),
        _file: file
      }
      uploadedImages.value.push(item)
    }
    if (isText) {
      reader.readAsText(file)
    } else if (isImage) {
      reader.readAsDataURL(file)
    } else {
      reader.readAsArrayBuffer(file)
    }
    return false
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

      let lastWsProgress = 0
      let lastWsTime = Date.now()
      connectSocket(sessionId, {
        onProgress: (data) => {
          const pct = data.progress_percent || data.progress || 0
          progressPercent.value = Math.min(pct, 99)
          progressMessage.value = data.message || data.stage_name || '分析中...'
          lastWsProgress = progressPercent.value
          lastWsTime = Date.now()
        },
        onComplete: (data) => {
          progressPercent.value = 100
          progressMessage.value = '分析完成'
        }
      })

      const progressStage = [
        { limit: 8, time: 3000, msg: '正在解析输入内容...' },
        { limit: 15, time: 8000, msg: '正在清洗和标准化数据...' },
        { limit: 25, time: 15000, msg: '正在进行智能分案...' },
        { limit: 45, time: 25000, msg: '正在深度分析各案件...' },
        { limit: 65, time: 40000, msg: '正在深度分析各案件...' },
        { limit: 80, time: 55000, msg: '正在进行团伙聚类分析...' },
        { limit: 90, time: 70000, msg: '正在生成画像增强...' },
      ]
      let progressTimer = setInterval(() => {
        const elapsed = Date.now() - analysisStartTime.value
        if (lastWsProgress > 0 && Date.now() - lastWsTime < 5000) {
          return
        }
        for (const stage of progressStage) {
          if (elapsed >= stage.time && progressPercent.value < stage.limit) {
            progressPercent.value = Math.min(stage.limit, 90)
            progressMessage.value = stage.msg
            break
          }
        }
      }, 1000)

      const response = await apiStartAnalysis(messages, sessionId, fundFlowTx.value)

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

        const rawCases = (response.raw_cases || []).map(c => mapCaseForAnalysis(c))
        cases.value = rawCases
        lastImportedCaseIds.value = rawCases.map(c => c.case_id || c.id).filter(Boolean)

        // REQ-S7：捕获后端透传的失败边界信息（异常卡 / 告警 / 四单流转）
        analysisAbnormal.value = response.abnormal && response.abnormal.abnormal
          ? response.abnormal
          : { abnormal: response.abnormal || 'none', detail: response.abnormal_detail || null }
        analysisWarnings.value = Array.isArray(response.warnings) ? response.warnings : []
        analysisSlips.value = response.slips || null

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
      if (typeof progressTimer !== 'undefined') clearInterval(progressTimer)
      loading.value = false
    }
  }

  const goToResults = () => {
    showResult.value = false
    router.push({ name: 'overview' })
  }

  const getCaseGangMap = computed(() => {
    // 案件->团伙 反查表：原来每张卡片都对 48 个团伙做 find+includes（O(卡片x团伙x案件)），
    // 案件列表页每次响应式重算都放大这个开销，改为建一次索引查一次。
    const map = new Map()
    for (const g of gangs.value) {
      for (const cid of (g.caseIds || g.case_ids || [])) {
        if (!map.has(cid)) map.set(cid, g)
      }
    }
    return map
  })

  const getCaseGang = (caseId) => {
    return getCaseGangMap.value.get(caseId)
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
              const cleanTag = r.data.cleaned ? ' ✨已清洗' : ''
              allText += (allText ? '\n---\n' : '') + `[${item.name} | ${tag}${cleanTag}]\n` + r.data.text
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
            const fileBlob = item.content instanceof ArrayBuffer
              ? new Blob([item.content], { type: 'application/octet-stream' })
              : item._file
            const uploadFile = item.content instanceof ArrayBuffer
              ? new File([fileBlob], item.name)
              : item._file
            formData.append('file', uploadFile)
            const r = await api.post('/api/extract-text', formData, {
              timeout: 180000
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
    ElMessage.info('外部数据源接入功能开发中')
  }

  const syncApiData = (source) => {
    ElMessage.warning('数据同步功能开发中')
  }

  const fetchBankData = () => {
    ElMessage.warning('该数据源接入功能开发中，暂不可用')
  }

  const fetchPoliceData = () => {
    ElMessage.warning('该数据源接入功能开发中，暂不可用')
  }

  const fetchAntiFraudData = () => {
    ElMessage.warning('该数据源接入功能开发中，暂不可用')
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
    if (reportConfig.value.type === 'gang' && !reportConfig.value.gangId) {
      ElMessage.warning('请先选择一个团伙')
      return
    }
    // 预览由前端即时渲染（数据已加载），不再假装 loading 1.5s
    reportPreview.value = true
    ElMessage.success('报告已生成，可打印或下载')
  }

  // 打印：把纸面红头文书 HTML 写入新窗口自动弹出打印框（可"另存为 PDF"）
  const printReport = () => {
    const gang = gangs.value.find(g => (g.id === reportConfig.value.gangId || g.gang_id === reportConfig.value.gangId))
    const subjectName = reportConfig.value.type === 'case'
      ? (selectedCase.value?.title || '案件')
      : (gang?.gang_name || gang?.name || '报告')
    const html = generateReportHTML(getReportTitle(), subjectName)
    const w = window.open('', '_blank', 'width=900,height=800')
    if (!w) {
      ElMessage.error('浏览器拦截了新窗口，请允许弹窗后重试')
      return
    }
    w.document.write(html)
    w.document.close()
    w.focus()
    // 等字体/布局渲染完成后自动弹出打印框
    setTimeout(() => { try { w.print() } catch { /* 用户可手动 Ctrl+P */ } }, 400)
  }

  // 下载：pdf/docx 优先走后端真实文件生成（reportlab/python-docx），
  // 后端不可用或选 html 时降级为本地纸面文书 HTML。
  const downloadReport = async () => {
    const gang = gangs.value.find(g => (g.id === reportConfig.value.gangId || g.gang_id === reportConfig.value.gangId))
    const gangName = gang?.gang_name || gang?.name || '报告'
    const title = getReportTitle()
    const fmt = reportConfig.value.format

    if (fmt === 'pdf' || fmt === 'docx') {
      try {
        let resp
        if (reportConfig.value.type === 'case' && selectedCase.value?.id) {
          resp = await generateCaseReport(selectedCase.value.id, fmt === 'docx' ? 'docx' : 'pdf')
        } else if (reportConfig.value.gangId) {
          if (fmt === 'docx') {
            // 后端暂无团伙 docx 接口，降级本地 HTML
            throw new Error('no gang docx endpoint')
          }
          resp = await generateGangReport(reportConfig.value.gangId)
        } else {
          throw new Error('no target id')
        }
        if (resp?.success && resp.file_path) {
          const fileResp = await api.get(resp.file_path, { responseType: 'blob' })
          const url = URL.createObjectURL(fileResp.data)
          const a = document.createElement('a')
          a.href = url
          a.download = resp.file_path.split('/').pop()
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)
          ElMessage.success('报告已下载')
          return
        }
      } catch {
        ElMessage.warning('后端报告服务不可用，已改用本地文书格式下载')
      }
    }

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
    ElMessage.success('报告下载完成（打开后可打印为 PDF）')
  }

  // ===== 报告：公安办案文书风格（红头 + 文号 + 密级 + 正文 + 落款）=====
  // 数据模型由 buildReportDoc() 产出，在线预览(ReportDocView)与
  // 打印/下载(generateReportHTML)共用，保证所见即所得。
  function buildReportDoc() {
    const gang = gangs.value.find(g => (g.id === reportConfig.value.gangId || g.gang_id === reportConfig.value.gangId))
    const c = selectedCase.value
    const isCase = reportConfig.value.type === 'case'
    const year = new Date().getFullYear()
    const now = new Date()
    const timeStr = `${year}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    const seq = (Date.now() % 9000) + 1000

    const doc = {
      title: getReportTitle(),
      no: `FraudLens〔${year}〕${isCase ? '案研' : '团研'}字第 ${seq} 号`,
      secret: '机密',
      time: timeStr,
      date: `${year}年${now.getMonth() + 1}月${now.getDate()}日`,
      sections: []
    }

    if (isCase && c) {
      doc.subjectName = c.title || '案件'
      doc.subjectNo = c.id || c.case_id || '-'
      doc.sections.push({
        title: '一、案件基本信息',
        rows: [
          ['案件编号', c.id || c.case_id || '-'],
          ['案件名称', c.title || '-'],
          ['诈骗类型', c.type || c.scam_type || '-'],
          ['涉案金额', c.amount || c.amountText || '-', 'danger'],
          ['案件状态', c.status || '-'],
          ['发案时间', c.date ? String(c.date).slice(0, 10) : '-'],
          ['受害人', c.victimName || '-']
        ]
      })
    } else if (gang) {
      doc.subjectName = gang.gang_name || gang.name || '团伙'
      doc.subjectNo = gang.gang_id || gang.id || '-'
      doc.sections.push({
        title: '一、团伙基本信息',
        rows: [
          ['团伙编号', gang.gang_id || gang.id || '-'],
          ['团伙名称', gang.gang_name || gang.name || '-'],
          ['风险等级', (gang.riskLevel || gang.risk_label || '-') + '级'],
          ['威胁等级', gang.threat_level || '-'],
          ['综合评分', gang.score ?? gang.comprehensive_score ?? '-'],
          ['串并置信度', gang.confidence ? Math.round(gang.confidence * 100) + '%' : '-'],
          ['预估成员数', gang.member_count_estimate || gang.member_count || '-'],
          ['技术手段', gang.tech_level || '-'],
          ['话术类型', gang.script_type || '-'],
          ['关联案件', (gang.cases || 0) + ' 起'],
          ['涉案金额', gang.amount || '-', 'danger'],
          ['特征标签', (gang.tags || []).join('、') || '-']
        ]
      })
    } else {
      doc.subjectName = '综合态势'
      doc.subjectNo = '-'
      doc.sections.push({
        title: '一、研判范围',
        rows: [
          ['报告范围', '全量案件综合分析'],
          ['案件总数', (cases.value?.length || 0) + ' 起'],
          ['团伙总数', (gangs.value?.length || 0) + ' 个']
        ]
      })
    }

    // 二、作案流程 / 关联案件
    const sec2 = { title: '二、作案流程与关联案件', rows: [], items: [] }
    if (gang) {
      if (gang.steps && gang.steps.length) {
        sec2.text = '作案流程链：' + gang.steps.map(s => (typeof s === 'string' ? s : (s.title || s.name || s.step || '环节'))).join(' → ')
      }
      const rel = (gang.related_cases || []).slice(0, 5)
      rel.forEach(rc => {
        sec2.items.push(`${rc.case_id}（受害人：${rc.victim || '-'}，涉案：${rc.amount || '-'}${rc.reason ? '，并案依据：' + rc.reason : ''}）`)
      })
      if (sec2.items.length) {
        sec2.text = (sec2.text ? sec2.text + '。' : '') + '经 GNN 图聚类与话术指纹比对，串并关联案件 ' + (gang.cases || sec2.items.length) + ' 起，前 ' + sec2.items.length + ' 起如下：'
      }
    } else if (isCase && c) {
      sec2.text = c.description ? String(c.description).replace(/^###.*$/gm, '').trim().slice(0, 400) : ''
      sec2.title = '二、案件经过'
    }
    if (reportConfig.value.includeTimeline && (sec2.text || sec2.items.length)) {
      doc.sections.push(sec2)
    }

    // 三、资金流向分析
    if (reportConfig.value.includeMoney) {
      let moneyText
      if (gang && (gang.overseas_pct || gang.transfer_levels)) {
        moneyText = `经资金链路分析，该团伙涉案资金 ${gang.amount || '-'}，` +
          `流转层级约 ${gang.transfer_levels || gang.max_level || 3}-${(gang.transfer_levels || 3) + 1} 级，` +
          `涉及账户 ${gang.account_count || gang.total_accounts || '-'} 个` +
          (gang.overseas_pct ? `，境外流向占比约 ${Math.round(gang.overseas_pct * 100)}%` : '') +
          '。资金经多级银行卡快速分散转移，最终疑似归集至境外或虚拟货币平台，建议对末级账户紧急止付。'
      } else if (isCase && c) {
        moneyText = `经分析，该案件涉案金额为 ${c.amount || c.amountText || '未知'}，资金流向正在进一步核查中，建议协调银行调取完整交易流水，追踪资金去向。`
      } else {
        moneyText = '经分析，涉案资金主要通过多级账户快速转移，流转层级约3-5层，涉及多家银行多个账户，最终流向境外或虚拟货币平台。'
      }
      doc.sections.push({ title: '三、资金流向分析', text: moneyText })
    }

    // 四、处置建议
    if (reportConfig.value.includeSuggestion) {
      doc.sections.push({
        title: '四、处置建议',
        items: [
          '立即对涉案银行账户、支付账户发起止付冻结，防止资金进一步转移；',
          '协调相关银行及第三方支付机构调取完整交易流水，固定电子证据；',
          '对团伙成员实施布控，摸清组织架构与落脚点，择机收网；',
          '启动跨部门、跨区域联合处置机制，涉境外线索通报上级协查。'
        ]
      })
    }

    return doc
  }

  const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  function generateReportHTML(title, subjectName) {
    const doc = buildReportDoc()
    if (title) doc.title = title
    if (subjectName) doc.subjectName = subjectName

    const sectionsHtml = doc.sections.map(sec => {
      let inner = ''
      if (sec.rows?.length) {
        inner += `<table class="doc-table"><tbody>${sec.rows.map(r =>
          `<tr><td class="dt-label">${esc(r[0])}</td><td class="dt-value${r[2] === 'danger' ? ' danger' : ''}">${esc(r[1])}</td></tr>`).join('')}</tbody></table>`
      }
      if (sec.text) inner += `<p class="doc-para">${esc(sec.text)}</p>`
      if (sec.items?.length) {
        inner += `<ol class="doc-ol">${sec.items.map(i => `<li>${esc(i)}</li>`).join('')}</ol>`
      }
      return `<div class="doc-section"><div class="rd-sec-title">${esc(sec.title)}</div>${inner}</div>`
    }).join('\n')

    return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${esc(doc.title)} - ${esc(doc.subjectName)}</title>
<style>
${REPORT_DOC_CSS}
</style></head><body><div class="report-doc">
  <div class="rd-org">FraudLens 反诈智能研判系统</div>
  <div class="rd-title">${esc(doc.title)}</div>
  <div class="rd-meta"><span>${esc(doc.no)}</span><span>密级：<b class="rd-secret">${esc(doc.secret)}</b></span><span>生成时间：${esc(doc.time)}</span></div>
  <div class="rd-redline"></div>
  <div class="rd-body">${sectionsHtml}</div>
  <div class="rd-sign"><div>研判民警（承办）：＿＿＿＿＿＿＿＿　复核：＿＿＿＿＿＿＿＿</div><div class="rd-sign-date">${esc(doc.date)}</div></div>
  <div class="rd-footer">本报告由 FraudLens 反诈智能研判系统自动生成，数据来源于本单位授权系统，仅供内部研判参考，严禁外传。</div>
</div></body></html>`
  }

  const loadDashboard = async (forceRefresh = false) => {
    dashboardLoading.value = true
    try {
      const data = await cachedLoad('dashboard', getDashboardData, forceRefresh ? 0 : 30000)
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
        // 从 gangs.radar_data 聚合团伙能力画像（7 维均值）
        const radarMap = {}
        const radarNames = ['诈骗话术成熟度', '资金分散程度', '成员关联密度', '跨区域作案特征', '技术手段先进性', '受害者画像精准度', '反侦察能力']
        for (const g of (gangs.value || [])) {
          const rd = g.radar_data || g.radarData || {}
          for (const [k, v] of Object.entries(rd)) {
            if (typeof v === 'number') {
              if (!radarMap[k]) radarMap[k] = []
              radarMap[k].push(v)
            }
          }
        }
        const gangRadar = radarNames
          .filter(k => radarMap[k] && radarMap[k].length)
          .map(k => ({
            name: k,
            value: Math.round(radarMap[k].reduce((a, b) => a + b, 0) / radarMap[k].length)
          }))
        // 无完整维度时用综合分兜底
        if (!gangRadar.length && gangs.value?.length) {
          const score = gangs.value[0].comprehensive_score || 60
          gangRadar.push({ name: '综合能力', value: Math.min(99, score) })
        }
        dashboardData.value.gang_radar = gangRadar
        nextTick(() => initDashboardCharts())
        // Overview 页的"涉案金额趋势"图依赖 monthly_trend，数据到位后一并渲染
        if (route.name === 'overview') nextTick(() => initCharts())
      } else {
        ElMessage.error('获取看板数据失败: ' + (data.message || '服务器返回异常'))
      }
    } catch (err) {
      ElMessage.error('获取看板数据异常: ' + (err?.message || '网络错误'))
    } finally {
      dashboardLoading.value = false
    }
  }

  const _initDashboardChartsImpl = async () => {
    const echarts = await getEcharts()
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
        // 点击扇区 → 联动过滤最新案件（风险等级）
        dashboardRiskChart.on('click', (params) => {
          const label = params.name
          dashboardRiskFilter.value = dashboardRiskFilter.value === label ? '' : label
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
        // 点击扇区 → 联动过滤最新案件（案件状态）
        dashboardStatusChart.on('click', (params) => {
          const label = params.name
          dashboardStatusFilter.value = dashboardStatusFilter.value === label ? '' : label
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

      // ===== 团伙能力画像雷达图 =====
      const radarSource = (dashboardData.value.gang_radar || [])
      if (dashboardRadarChartRef.value && radarSource.length) {
        if (dashboardRadarChart) dashboardRadarChart.dispose()
        dashboardRadarChart = echarts.init(dashboardRadarChartRef.value)
        const indicators = radarSource.map(d => ({ name: d.name, max: 100 }))
        const seriesData = radarSource.map(d => d.value)
        const maxV = Math.max(...seriesData, 30)
        dashboardRadarChart.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item' },
          radar: {
            indicator: indicators,
            radius: '62%',
            center: ['50%', '52%'],
            splitNumber: 4,
            axisName: { color: '#bcc6d6', fontSize: 11 },
            axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.25)' } },
            splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.12)' } },
            splitArea: {
              areaStyle: {
                color: ['rgba(0, 212, 255, 0.02)', 'rgba(0, 212, 255, 0.05)']
              }
            }
          },
          series: [{
            type: 'radar',
            data: [{
              value: seriesData,
              name: '能力强度',
              areaStyle: { color: 'rgba(0, 212, 255, 0.18)' },
              lineStyle: { color: '#00d4ff', width: 2 },
              itemStyle: { color: '#00d4ff' },
              symbolSize: 4
            }]
          }]
        })
        dashboardRadarChart.resize()
      } else if (dashboardRadarChart) {
        dashboardRadarChart.dispose()
        dashboardRadarChart = null
      }
    })
  }

  // 对外暴露的版本：动态加载 echarts 失败时只告警，不让调用方拿到未捕获的 rejection
  const initDashboardCharts = () => {
    _initDashboardChartsImpl().catch(err => console.warn('[charts] 看板图表初始化失败:', err))
  }

  const loadAlerts = async (forceRefresh = false) => {
    alertsLoading.value = true
    try {
      const data = await cachedLoad('alerts', getActiveAlerts, forceRefresh ? 0 : 15000)
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
  const loadFlowMetrics = async (forceRefresh = false) => {
    if (!store.isLoggedIn) return
    try {
      const r = await cachedLoad('flowMetrics', fetchCapitalFlowStats, forceRefresh ? 0 : 60000)
      if (r.success && r.stats) {
        flowMetrics.value = {
          total_accounts: r.stats.total_accounts || 0,
          max_level: r.stats.max_level || 0,
          overseas_pct: r.stats.overseas_pct ?? 0,
          total_flows: r.stats.total_flows || 0
        }
      } else {
        console.warn('[loadFlowMetrics] API returned not success:', r)
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.response?.data?.error || e?.message || String(e)
      console.error('[loadFlowMetrics] 加载失败:', detail)
    }
  }
  const addFlowRecord = (row) => {
    ElMessage.info('追加资金流向功能：' + row.source_account + ' → ' + row.target_account)
  }

  // ---- 团伙复核解释层（并案依据 / 误并案探测） ----
  // 默认纯规则模式（毫秒级）；useLlm=true 走 LLM 增强（慢，前端需 loading）
  const gangReviewUseLlm = ref(false)
  const loadGangReview = async (forceRefresh = false) => {
    if (!store.isLoggedIn) return
    if (gangReviewLoading.value) return
    gangReviewLoading.value = true
    try {
      const useLlm = gangReviewUseLlm.value
      const key = 'gangReview_' + (useLlm ? 'llm' : 'rule')
      const ttl = useLlm ? 300000 : 180000
      const r = await cachedLoad(key, () => fetchGangReviewResults(useLlm), forceRefresh ? 0 : ttl)
      if (r && r.success) {
        gangReview.value = {
          explanations: Array.isArray(r.explanations) ? r.explanations : [],
          review: r.review || null,
          llmEnabled: !!r.llm_enabled,
          checkedGangs: r.checked_gangs || 0,
          error: r.error || ''
        }
      } else {
        gangReview.value = { explanations: [], review: null, llmEnabled: false, error: (r && r.error) || '复核接口返回异常' }
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.response?.data?.error || e?.message || String(e)
      console.error('[loadGangReview] 加载失败:', detail)
      gangReview.value = { explanations: [], review: null, llmEnabled: false, error: detail }
    } finally {
      gangReviewLoading.value = false
    }
  }
  // gang_id -> explanation（供卡片渲染）
  const gangReviewMap = computed(() => {
    const m = {}
    for (const e of gangReview.value.explanations) {
      if (e && e.gang_id) m[e.gang_id] = e
    }
    return m
  })
  // gang_id -> 可疑误并信息（供卡片告警 + 页顶横幅）
  const suspiciousMergeMap = computed(() => {
    const m = {}
    const list = gangReview.value.review?.suspicious_merges || []
    for (const s of list) {
      if (s && s.gang_id) m[s.gang_id] = s
    }
    return m
  })
  const suspiciousMerges = computed(() => gangReview.value.review?.suspicious_merges || [])
  const toggleGangReviewLlm = async (val) => {
    gangReviewUseLlm.value = !!val
    await loadGangReview(true)
  }

  const loadDispatchOrders = async (forceRefresh = false) => {
    try {
      const params = dispatchStatusFilter.value ? { status: dispatchStatusFilter.value } : {}
      const cacheKey = 'dispatch_' + (params.status || 'all')
      const loader = () => api.get('/api/dispatch/list', { params })
      const r = await cachedLoad(cacheKey, loader, forceRefresh ? 0 : 15000)
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

  const loadKeyPersons = async (forceRefresh = false) => {
    try {
      const params = {}
      if (personSearch.value) params.search = personSearch.value
      if (personTypeFilter.value) params.person_type = personTypeFilter.value
      const cacheKey = 'keyPersons_' + (params.search || '') + '_' + (params.person_type || 'all')
      const loader = () => api.get('/api/persons/key', { params })
      const r = await cachedLoad(cacheKey, loader, forceRefresh ? 0 : 15000)
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

  const _initChartsImpl = async () => {
    const echarts = await getEcharts()
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

  // 对外暴露的版本：动态加载 echarts 失败时只告警，不让调用方拿到未捕获的 rejection
  const initCharts = () => {
    _initChartsImpl().catch(err => console.warn('[charts] 总览图表初始化失败:', err))
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
      // P0 修复：caseIds 必须兼容 case_ids(字符串数组) 与 related_cases(对象数组) 两种格式，
      // 否则 getCaseGang 永远返回 undefined，案件卡片不显示所属团伙。
      caseIds: Array.isArray(g.case_ids) && g.case_ids.length
        ? [...g.case_ids]
        : Array.isArray(g.caseIds) && g.caseIds.length
          ? [...g.caseIds]
          : (Array.isArray(g.related_cases) ? g.related_cases.map(c => c.case_id || c) : []),
      case_ids: Array.isArray(g.case_ids) && g.case_ids.length
        ? [...g.case_ids]
        : (Array.isArray(g.related_cases) ? g.related_cases.map(c => c.case_id || c) : []),
      // 关联可解释性字段：reason / matched_entities / relation_type
      related_cases: Array.isArray(g.related_cases) ? g.related_cases : [],
      relation_reasons: g.relation_reasons || {},
      matched_entities_map: g.matched_entities_map || {},
      radar_data: g.radar_data || g.radarData || {},
      radarData: g.radar_data || g.radarData || {},
      // 团伙画像卡片增强（问题10）：作案流程、威胁等级、话术类型
      steps: Array.isArray(g.steps) ? g.steps : [],
      threat_level: g.threat_level || '',
      tech_level: g.tech_level || '',
      script_type: g.script_type || '',
      member_count_estimate: g.member_count_estimate || '',
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
      amountText: formatCaseAmountText(c),
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
      caseIds: Array.isArray(g.case_ids) && g.case_ids.length
        ? [...g.case_ids]
        : Array.isArray(g.caseIds) && g.caseIds.length
          ? [...g.caseIds]
          : (Array.isArray(g.related_cases) ? g.related_cases.map(c => c.case_id || c) : []),
      case_ids: Array.isArray(g.case_ids) && g.case_ids.length
        ? [...g.case_ids]
        : (Array.isArray(g.related_cases) ? g.related_cases.map(c => c.case_id || c) : []),
      related_cases: g.related_cases || [],
      relation_reasons: g.relation_reasons || {},
      matched_entities_map: g.matched_entities_map || {},
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

  const reloadCasesAndGangs = async (forceRefresh = false) => {
    if (!store.isLoggedIn) return
    try {
      const [casesRes, gangsRes] = await Promise.all([
        // TTL 30s：10s 时切页几乎必重拉（cases+gangs 合计 ~390KB），是"案件总览慢"的主因之一
        cachedLoad('cases', fetchCases, forceRefresh ? 0 : 30000),
        cachedLoad('gangs', fetchGangs, forceRefresh ? 0 : 30000)
      ])
      if (casesRes.success) {
        const caseData = casesRes.cases || casesRes.data || []
        cases.value = caseData.map(c => mapCaseFromResponse(c))
      } else {
        console.error('[reloadCasesAndGangs] fetchCases failed:', casesRes)
      }
      if (gangsRes.success) {
        const gangData = gangsRes.gangs || gangsRes.data || []
        gangs.value = gangData.map((g, idx) => mapGangFromResponse(g, idx))
      } else {
        console.error('[reloadCasesAndGangs] fetchGangs failed:', gangsRes)
      }
      // 案件/团伙数据到位后，若正停留在 overview，重绘饼图（数据源 cases）
      if (route.name === 'overview' && cases.value.length) {
        nextTick(() => initCharts())
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.response?.data?.error || e?.message || String(e)
      console.warn('[reloadCasesAndGangs] 刷新数据失败:', detail)
      if (store.isLoggedIn) {
        ElMessage.error('数据加载失败: ' + detail)
      }
    } finally {
      // 供各页面在数据到位前显示骨架屏，避免先闪「暂无数据」再突然冒出列表
      casesReady.value = true
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
    if (newVal === 'details' && store.isLoggedIn) {
      reloadCasesAndGangs()
    }
    if (newVal === 'groups' && store.isLoggedIn) {
      loadGangReview()
    }
  })

  onMounted(async () => {
    const routeName = route.name
    if (store.isLoggedIn) {
      try {
        await getMe()
      } catch {
        store.logout()
      }
    }
    if (store.isLoggedIn) {
      loadFlowMetrics()
      await reloadCasesAndGangs()
      if (routeName === 'dashboard') loadDashboard()
      if (routeName === 'alerts') loadAlerts()
      if (routeName === 'groups') loadGangReview()
      if (cases.value.length === 0) {
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
          // 强制刷新：绕过缓存，否则命中 seed 前缓存的空列表
          await reloadCasesAndGangs(true)
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
  }
  if (routeName === 'overview' && gangs.value.length) {
      nextTick(() => initCharts())
    }
  })

  onUnmounted(() => {
    auth.clearLoginProgressTimer()
    disposeAllCharts()
    disconnectSocket()
  })

  const disposeAllCharts = () => {
    [dashboardRiskChart, dashboardStatusChart, dashboardBarChart, dashboardTrendChart, pieChart, lineChart].forEach(c => {
      if (c) { try { c.dispose() } catch (e) { /* ignore */ } }
    })
    dashboardRiskChart = dashboardStatusChart = dashboardBarChart = dashboardTrendChart = pieChart = lineChart = null
  }

  // ---- 资金流水导入（真实材料接入 Phase4） ----
  const importFundFlowFile = async (file) => {
    try {
      const res = await importFundFlow(file)
      if (res && res.success) {
        fundFlowTx.value = res.accounts_tx || []
        fundFlowFileName.value = file.name || ''
        ElMessage.success(`已导入 ${fundFlowTx.value.length} 笔资金流水，将参与资金链与回流闭环研判`)
        return res
      }
      ElMessage.error((res && res.error) || '资金流水解析失败')
    } catch (e) {
      ElMessage.error('资金流水导入失败：' + (e.message || e))
    }
    return null
  }

  const clearFundFlow = () => {
    fundFlowTx.value = []
    fundFlowFileName.value = ''
  }

  // 认证模块解构（接口保持与拆分前一致）
  const { loginForm, loginLoading, loginError, loginProgress, handleLogin, handleDemoLogin, handleLogout } = auth

  return {
    store,
    activeMenu,
    loading,
    casesReady,
    showProgress, showResult, progressPercent, progressMessage, resultStats,
    inputText,
    uploadedImages,
    gangs,
    cases,
    gangReview,
    gangReviewLoading,
    gangReviewUseLlm,
    gangReviewMap,
    suspiciousMergeMap,
    suspiciousMerges,
    loadGangReview,
    toggleGangReviewLlm,
    analysisAbnormal,
    analysisWarnings,
    analysisSlips,
    lastImportedCaseIds,
    recentCases,
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
    dashboardRadarChartRef,
    dashboardRiskFilter,
    dashboardStatusFilter,
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
    fundFlowTx,
    fundFlowFileName,
    importFundFlowFile,
    clearFundFlow,
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
    buildReportDoc,
    loadDashboard,
    initCharts,
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