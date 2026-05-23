import axios from 'axios'
import { io } from 'socket.io-client'
import { store } from './store.js'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5003'
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

// ========== WebSocket ==========
let socket = null

export function connectSocket(sessionId, callbacks = {}) {
  if (socket) {
    socket.disconnect()
  }

  socket = io(WS_URL, {
    transports: ['websocket', 'polling'],
    query: { session_id: sessionId }
  })

  socket.on('connect', () => {
    if (isDev) console.log('🔌 WebSocket connected:', socket.id)
    callbacks.onConnect?.(socket.id)
  })

  socket.on('analysis_progress', (data) => {
    if (isDev) console.log('📊 Progress:', data)
    callbacks.onProgress?.(data)
  })

  socket.on('analysis_complete', (data) => {
    if (isDev) console.log('✅ Analysis complete:', data)
    callbacks.onComplete?.(data)
  })

  socket.on('disconnect', () => {
    if (isDev) console.log('🔌 WebSocket disconnected')
    callbacks.onDisconnect?.()
  })

  socket.on('connect_error', (err) => {
    console.warn('⚠️ WebSocket connection error:', err.message)
    callbacks.onError?.(err)
  })

  return socket
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect()
    socket = null
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
  const response = await api.put('/api/admin/users/' + user_id, data)
  return response.data
}

export async function deleteUser(user_id) {
  const response = await api.delete('/api/admin/users/' + user_id)
  return response.data
}

export async function getOperationLogs() {
  const response = await api.get('/api/auth/logs')
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
export async function startAnalysis(messages, sessionId) {
  const response = await api.post('/agent-analyze', { messages: messages, session_id: sessionId, platform_data: {} })
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

// ========== Merges ==========
export async function suggestMerges() {
  const response = await api.post('/api/merges/suggest')
  return response.data
}

export async function confirmMerge(caseIdA, caseIdB, gangId) {
  const response = await api.post('/api/merges/confirm', { case_id_a: caseIdA, case_id_b: caseIdB, gang_id: gangId })
  return response.data
}

export async function getPendingMerges() {
  const response = await api.get('/api/merges/pending')
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

export default api