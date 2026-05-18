import { ref, computed } from 'vue'
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
  importExcel
} from './api.js'
import { ElMessage } from 'element-plus'

export function useAppState() {
  const activeMenu = ref('input')
  const loading = ref(false)
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

  // P1 features
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
    total_cases: null, total_gangs: null, total_amount: null, active_alerts: null,
    risk_distribution: [], status_distribution: [],
    top_scam_types: [], monthly_trend: [], recent_cases: []
  })
  const dashboardLoading = ref(false)
  const alerts = ref([])
  const alertsLoading = ref(false)
  const resolvingAlert = ref(null)
  const loginForm = ref({ username: '', password: '' })
  const loginLoading = ref(false)
  const loginError = ref('')

  const textLineCount = computed(() => inputText.value.split('\n').filter(l => l.trim()).length)

  const extractedKeywords = computed(() => {
    const ks = []
    const t = inputText.value
    if (t.includes('诈骗') || t.includes('被骗')) ks.push('诈骗')
    if (t.includes('转账') || t.includes('汇款')) ks.push('转账')
    if (t.includes('客服') || t.includes('京东')) ks.push('冒充客服')
    if (t.includes('征信') || t.includes('贷款')) ks.push('征信诈骗')
    if (t.includes('刷单') || t.includes('返利')) ks.push('刷单诈骗')
    if (/\d{11}/.test(t)) ks.push('手机号')
    if (/¥|万元|元/.test(t)) ks.push('涉案金额')
    return ks.slice(0, 6)
  })

  const hasTime = computed(() => /\d{4}年|\d{1,2}月|\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}/.test(inputText.value))
  const hasAmount = computed(() => /¥|万元|元|\d+万/.test(inputText.value))
  const hasPhone = computed(() => /\d{11}/.test(inputText.value))
  const hasMethod = computed(() => /诈骗|被骗|转账|汇款|客服|征信|贷款|刷单/.test(inputText.value))

  function handleMenuSelect(index) {
    activeMenu.value = index
  }

  return {
    activeMenu, loading, inputText, uploadedImages, gangs, cases,
    selectedGang, selectedCase, viewMode, gangSearchKeyword, riskFilter,
    detailTab, networkView, generatingReport, parsedReport,
    flowSearchCaseId, capitalFlows, flowGraphData, dispatchOrders,
    dispatchStatusFilter, showCreateDispatch, keyPersons, personSearch,
    personTypeFilter, showCreatePerson, dashboardData, dashboardLoading,
    alerts, alertsLoading, resolvingAlert, loginForm, loginLoading, loginError,
    textLineCount, extractedKeywords, hasTime, hasAmount, hasPhone, hasMethod,
    handleMenuSelect
  }
}