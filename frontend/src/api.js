import axios from 'axios'
import { store } from './store.js'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:5003'
const WS_URL = import.meta.env.VITE_WS_URL || API_BASE
const isDev = import.meta.env.DEV

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  if (store.isLoggedIn && store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && store.isLoggedIn) {
      const url = error.config?.url || ''
      if (!url.includes('/auth/login') && !url.includes('/auth/register') && !url.includes('/auth/demo-login')) {
        store.logout()
        window.location.href = '/'
      }
    }
    return Promise.reject(error)
  }
)

// ========== WebSocket ==========
// 后端提供的是原生 FastAPI WebSocket（/ws/{session_id}，见 backend/routes/system.py:
// `@router.websocket('/ws/{session_id}')`），扇出进度消息为 {event, data, ts}。
// 这里用原生 WebSocket 客户端对接，避免 socket.io-client 与后端 socket.io 缺失导致握手 403。
let socket = null
let wsManuallyClosed = false
let wsReconnectTimer = null
let wsRetry = 0

const WS_MAX_RETRY = 5

function buildWsUrl(sessionId) {
  const base = WS_URL.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:').replace(/\/+$/, '')
  return `${base}/ws/${encodeURIComponent(sessionId)}`
}

export function connectSocket(sessionId, callbacks = {}) {
  if (socket) {
    wsManuallyClosed = true
    socket.close()
  }
  wsManuallyClosed = false
  wsRetry = 0

  const open = () => {
    if (wsManuallyClosed || socket) return
    let ws
    try {
      ws = new WebSocket(buildWsUrl(sessionId))
    } catch (e) {
      console.warn('⚠️ WebSocket 创建失败:', e.message)
      callbacks.onError?.(e)
      return
    }
    socket = ws

    ws.onopen = () => {
      if (isDev) console.log('🔌 WebSocket connected (native)')
      callbacks.onConnect?.(sessionId)
    }

    ws.onmessage = (ev) => {
      let msg
      try { msg = JSON.parse(ev.data) } catch { return }
      if (msg && msg.event === 'analysis_progress') {
        callbacks.onProgress?.(msg.data)
      } else if (msg && msg.event === 'analysis_complete') {
        callbacks.onComplete?.(msg.data)
      }
    }

    ws.onerror = (e) => {
      console.warn('⚠️ WebSocket 错误:', e)
      callbacks.onError?.(e)
    }

    ws.onclose = () => {
      if (ws === socket) socket = null
      callbacks.onDisconnect?.()
      if (!wsManuallyClosed && wsRetry < WS_MAX_RETRY) {
        wsRetry += 1
        wsReconnectTimer = setTimeout(open, Math.min(3000 * wsRetry, 10000))
      }
    }
  }

  open()
  return socket
}

export function disconnectSocket() {
  wsManuallyClosed = true
  if (socket) {
    socket.close()
    socket = null
  }
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
}

// ========== Auth ==========
export async function login(username, password) {
  const response = await api.post('/api/auth/login', { username, password })
  return response.data
}

export async function demoLogin() {
  const response = await api.post('/api/auth/demo-login')
  return response.data
}

export async function register(username, password, display_name) {
  const response = await api.post('/api/auth/register', { username, password, display_name })
  return response.data
}

export async function getMe() {
  const response = await api.get('/api/auth/me')
  return response.data
}

export async function changePassword(old_password, new_password) {
  const response = await api.put('/api/auth/change-password', { old_password, new_password })
  return response.data
}

export async function updateUser(user_id, data) {
  // 注意：路由挂在 /api/auth 前缀下（backend/routes/auth.py）
  const response = await api.put('/api/auth/admin/users/' + user_id, data)
  return response.data
}

export async function deleteUser(user_id) {
  const response = await api.delete('/api/auth/admin/users/' + user_id)
  return response.data
}

export async function createUser({ username, password, display_name, department, phone }) {
  const response = await api.post('/api/auth/register', { username, password, display_name, department, phone })
  return response.data
}

export async function getOperationLogs() {
  const response = await api.get('/api/auth/logs')
  return response.data
}

export async function fetchCaseById(caseId) {
  const response = await api.get(`/api/cases/${caseId}`)
  return response.data
}

export async function fetchGangById(gangId) {
  const response = await api.get(`/api/gangs/${gangId}`)
  return response.data
}

// Add 401 interceptor for auto refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && store.refreshToken) {
      try {
        const res = await axios.post(API_BASE + '/api/auth/refresh', { refresh_token: store.refreshToken })
        if (res.data?.success && res.data?.access_token) {
          store.token = res.data.access_token
          error.config.headers.Authorization = 'Bearer ' + res.data.access_token
          return api(error.config)
        }
      } catch {
        store.logout()
      }
      return Promise.reject(error)
    }
    if (error.response?.status === 401) {
      store.logout()
    }
    return Promise.reject(error)
  }
)

// ========== Analysis ==========
export async function startAnalysis(messages, sessionId, accountsTx) {
  const body = { messages: messages, session_id: sessionId, platform_data: {} }
  if (accountsTx && accountsTx.length) {
    body.accounts_tx = accountsTx
  }
  // 多智能体研判流水线（BGE 嵌入+GNN 团伙发现）实测可达 120s+，单独放宽超时避免偶发超时
  const response = await api.post('/agent-analyze', body, { timeout: 300000 })
  return response.data
}

// ========== Fund flow import (真实材料接入 Phase4) ==========
export async function importFundFlow(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post('/api/import-fund-flow', form, { timeout: 120000 })
  return response.data
}

export async function ocrImage(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post('/api/ocr', form, { timeout: 120000 })
  return response.data
}

export async function extractText(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post('/api/extract-text', form, { timeout: 120000 })
  return response.data
}

// ========== Cases ==========
export async function fetchCases() {
  const response = await api.get('/api/cases')
  return response.data
}

export async function fetchCaseDetail(caseId) {
  const response = await api.get(`/api/cases/${caseId}`)
  return response.data
}

export async function getCaseStats() {
  const response = await api.get('/api/cases/stats')
  return response.data
}

export async function updateCaseStatus(caseId, status) {
  const response = await api.put(`/api/cases/${caseId}/status`, { status })
  return response.data
}

export async function deleteCase(caseId) {
  const response = await api.delete(`/api/cases/${caseId}`)
  return response.data
}

export async function updateCase(caseId, data) {
  const response = await api.put(`/api/cases/${caseId}`, data)
  return response.data
}

// ========== Gangs ==========
export async function fetchGangs() {
  const response = await api.get('/api/gangs')
  return response.data
}

export async function fetchGangDetail(gangId) {
  const response = await api.get(`/api/gangs/${gangId}`)
  return response.data
}

// AI 并案复核层（Skill A 解释 + Skill B 误并探测）
export async function fetchGangReviewResults(useLlm = false) {
  const response = await api.get('/api/gangs/review-results', { params: { use_llm: useLlm ? 1 : 0 }, timeout: 150000 })
  return response.data
}

// ========== Merges（串并案建议） ==========
export async function fetchMergeSuggestions(status = 'pending', limit = 200, offset = 0) {
  const response = await api.get('/api/merges', { params: { status, limit, offset } })
  return response.data
}

export async function generateMergeSuggestions() {
  const response = await api.post('/api/merges/suggest')
  return response.data
}

export async function rejectMergeSuggestion(suggestionId, reason = '') {
  const response = await api.post(`/api/merges/${suggestionId}/reject`, { reason })
  return response.data
}

export async function confirmMergeSuggestion(caseIdA, caseIdB, gangId) {
  const response = await api.post('/api/merges/confirm', {
    case_id_a: caseIdA,
    case_id_b: caseIdB,
    gang_id: gangId,
  })
  return response.data
}

// ========== Sessions ==========
export async function fetchSessions() {
  const response = await api.get('/api/sessions')
  return response.data
}

export async function fetchSessionDetail(sessionId) {
  const response = await api.get(`/api/sessions/${sessionId}`)
  return response.data
}

export async function deleteSession(sessionId) {
  const response = await api.delete(`/api/sessions/${sessionId}`)
  return response.data
}

// ========== Reports ==========
export async function generateCaseReport(caseId, format) {
  const response = await api.get(`/api/reports/case/${caseId}`, { params: { format } })
  return response.data
}

export async function generateGangReport(gangId) {
  const response = await api.get(`/api/reports/gang/${gangId}`)
  return response.data
}

// ========== 资金流水导入留痕（合规审计） ==========
export async function fetchFundFlowImportHistory(params = {}) {
  const response = await api.get('/api/import-fund-flow/history', { params })
  return response.data
}

// ========== 止付冻结工单详情（含审批链与执行回执） ==========
export async function fetchFreezeOrderDetail(orderId) {
  const response = await api.get(`/api/workflow/freeze-orders/${orderId}`)
  return response.data
}

// ========== Search ==========
export async function searchCases(query) {
  const response = await api.get('/api/search', { params: { q: query } })
  return response.data
}

export async function advancedSearch(type, value) {
  const response = await api.get('/api/search/advanced', { params: { type, value } })
  return response.data
}

// ========== Health ==========
export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

// ========== Dashboard ==========
export async function getDashboardData() {
  const response = await api.get('/api/dashboard')
  return response.data
}

// ========== Alerts ==========
export async function getActiveAlerts() {
  const response = await api.get('/api/alerts')
  return response.data
}

export async function fetchCapitalFlowStats() {
  const response = await api.get('/api/capital/stats')
  return response.data
}

export async function seedData() {
  const response = await api.post('/api/seed')
  return response.data
}

export async function resolveAlert(alertId) {
  const response = await api.post(`/api/alerts/${alertId}/resolve`)
  return response.data
}

// ========== Batch Import ==========
export async function importCSV(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/api/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
  return response.data
}

export async function importExcel(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/api/import/excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
  return response.data
}

// ========== Smart File Analysis ==========
export async function analyzeFile(file, mode = 'auto') {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/api/analyze-file?mode=${mode}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
  return response.data
}

export async function visionAnalyze(file, prompt = '请详细描述这张图片的内容') {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/api/vision-analyze?prompt=${encodeURIComponent(prompt)}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
  return response.data
}

// ========== AI Config ==========
export async function getAiConfig() {
  return api.get('/api/settings/api-key')
}

export async function saveAiConfig(data) {
  return api.put('/api/settings/api-key', data)
}

// ========== Reviews ==========
export async function getPendingReviews() {
  const response = await api.get('/api/reviews/pending')
  return response.data
}

export async function reviewCase(caseId, data) {
  const response = await api.put(`/api/reviews/${caseId}`, data)
  return response.data
}

// ========== Radar ==========
export async function getCaseRadar(caseId) {
  return api.get(`/api/cases/${caseId}/radar`)
}

export async function getGangRadar(gangId) {
  return api.get(`/api/gangs/${gangId}/radar`)
}

// ========== Chat ==========
export async function sendChatMessage(message, sessionId = null) {
  const response = await api.post('/api/chat/message', {
    message,
    session_id: sessionId
  })
  return response.data
}

export async function getChatHistory(sessionId) {
  const response = await api.get(`/api/chat/sessions/${sessionId}/history`)
  return response.data
}

export async function clearChatSession(sessionId) {
  const response = await api.delete(`/api/chat/sessions/${sessionId}`)
  return response.data
}

export async function listChatIntents() {
  const response = await api.get('/api/chat/intents')
  return response.data
}

// ========== 办案工作流（Phase R1/E2） ==========

// 案件生命周期
export async function getCaseLifecycle(caseId) {
  const response = await api.get(`/api/workflow/cases/${caseId}/lifecycle`)
  return response.data
}

export async function transitionCaseStatus(caseId, toStatus, reason = '') {
  const response = await api.post(`/api/workflow/cases/${caseId}/transition`, { to_status: toStatus, reason })
  return response.data
}

export async function getCaseTimeline(caseId) {
  const response = await api.get(`/api/workflow/cases/${caseId}/timeline`)
  return response.data
}

// 研判任务
export async function listInvestigations(caseId = '', limit = 50) {
  const response = await api.get('/api/workflow/investigations', { params: { case_id: caseId, limit } })
  return response.data
}

export async function getInvestigation(taskId) {
  const response = await api.get(`/api/workflow/investigations/${taskId}`)
  return response.data
}

export async function createInvestigation(caseId, payload = {}) {
  const response = await api.post(`/api/workflow/cases/${caseId}/investigations`, payload)
  return response.data
}

export async function downloadInvestigationReport(taskId, format = 'pdf') {
  // 文件下载：用 blob
  const response = await api.get(`/api/workflow/investigations/${taskId}/report`, {
    params: { format },
    responseType: 'blob'
  })
  return response
}

// 止付冻结工单
export async function listFreezeOrders(caseId = '', status = '', limit = 50) {
  const response = await api.get('/api/workflow/freeze-orders', { params: { case_id: caseId, status, limit } })
  return response.data
}

export async function getFreezeOrder(orderId) {
  const response = await api.get(`/api/workflow/freeze-orders/${orderId}`)
  return response.data
}

export async function createFreezeOrder(payload) {
  const response = await api.post('/api/workflow/freeze-orders', payload)
  return response.data
}

export async function submitFreezeOrder(orderId, approvalChain = null) {
  const response = await api.post(`/api/workflow/freeze-orders/${orderId}/submit`, { approval_chain: approvalChain })
  return response.data
}

export async function executeFreezeOrder(orderId) {
  const response = await api.post(`/api/workflow/freeze-orders/${orderId}/execute`)
  return response.data
}

export async function cancelFreezeOrder(orderId, reason = '') {
  const response = await api.post(`/api/workflow/freeze-orders/${orderId}/cancel`, { reason })
  return response.data
}

export async function getFreezeReceipts(orderId) {
  const response = await api.get(`/api/workflow/freeze-orders/${orderId}/receipts`)
  return response.data
}

export async function downloadFreezeDoc(orderId, format = 'pdf') {
  const response = await api.get(`/api/workflow/freeze-orders/${orderId}/document`, {
    params: { format },
    responseType: 'blob'
  })
  return response
}

// HITL 复核任务
export async function listReviews(caseId = '', status = '', limit = 50) {
  const response = await api.get('/api/workflow/reviews', { params: { case_id: caseId, status, limit } })
  return response.data
}

export async function getReviewTask(reviewId) {
  const response = await api.get(`/api/workflow/reviews/${reviewId}`)
  return response.data
}

export async function assignReview(reviewId, payload) {
  const response = await api.post(`/api/workflow/reviews/${reviewId}/assign`, payload)
  return response.data
}

export async function addReviewOpinion(reviewId, payload) {
  const response = await api.post(`/api/workflow/reviews/${reviewId}/opinions`, payload)
  return response.data
}

export async function resolveReview(reviewId, payload) {
  const response = await api.post(`/api/workflow/reviews/${reviewId}/resolve`, payload)
  return response.data
}

// 通用审批流
export async function listPendingApprovals() {
  const response = await api.get('/api/workflow/approvals/pending')
  return response.data
}

export async function getApprovalFlow(flowId) {
  const response = await api.get(`/api/workflow/approvals/${flowId}`)
  return response.data
}

export async function approveFlow(flowId, comment = '') {
  const response = await api.post(`/api/workflow/approvals/${flowId}/approve`, { comment })
  return response.data
}

export async function rejectFlow(flowId, comment = '') {
  const response = await api.post(`/api/workflow/approvals/${flowId}/reject`, { comment })
  return response.data
}

export async function cancelApprovalFlow(flowId, reason = '') {
  const response = await api.post(`/api/workflow/approvals/${flowId}/cancel`, { reason })
  return response.data
}

export async function listApprovals(businessType = '', status = '', limit = 50) {
  const response = await api.get('/api/workflow/approvals', { params: { business_type: businessType, status, limit } })
  return response.data
}

export default api