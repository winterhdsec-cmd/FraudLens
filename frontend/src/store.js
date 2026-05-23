import { reactive } from 'vue'

const STORAGE_KEYS = {
  token: 'fraudlens_token',
  user: 'fraudlens_user',
  refresh: 'fraudlens_refresh'
}

function loadSavedUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.user)
    return raw ? JSON.parse(raw) : null
  } catch {
    localStorage.removeItem(STORAGE_KEYS.user)
    return null
  }
}

function isValidToken(val) {
  return typeof val === 'string' && val.length > 0
}

export const store = reactive({
  user: loadSavedUser(),
  token: localStorage.getItem(STORAGE_KEYS.token) || null,
  refreshToken: localStorage.getItem(STORAGE_KEYS.refresh) || null,
  isLoggedIn: !!localStorage.getItem(STORAGE_KEYS.token),
  login(user, token, refreshToken) {
    if (!isValidToken(token)) {
      console.warn('[store] login failed: invalid token')
      return
    }
    if (!user || typeof user !== 'object') {
      console.warn('[store] login failed: invalid user object')
      return
    }
    this.user = user
    this.token = token
    this.refreshToken = isValidToken(refreshToken) ? refreshToken : null
    this.isLoggedIn = true
    localStorage.setItem(STORAGE_KEYS.token, token)
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user))
    if (this.refreshToken) {
      localStorage.setItem(STORAGE_KEYS.refresh, this.refreshToken)
    }
  },
  logout() {
    this.user = null
    this.token = null
    this.refreshToken = null
    this.isLoggedIn = false
    Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k))
  }
})