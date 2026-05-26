import { reactive } from 'vue'

const STORAGE_KEYS = {
  token: 'fraudlens_token',
  user: 'fraudlens_user',
  refresh: 'fraudlens_refresh'
}

function loadSavedUser() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEYS.user)
    return raw ? JSON.parse(raw) : null
  } catch {
    sessionStorage.removeItem(STORAGE_KEYS.user)
    return null
  }
}

function isValidToken(val) {
  return typeof val === 'string' && val.length > 0
}

export const store = reactive({
  user: loadSavedUser(),
  token: sessionStorage.getItem(STORAGE_KEYS.token) || null,
  refreshToken: sessionStorage.getItem(STORAGE_KEYS.refresh) || null,
  isLoggedIn: !!sessionStorage.getItem(STORAGE_KEYS.token),
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
    sessionStorage.setItem(STORAGE_KEYS.token, token)
    sessionStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user))
    if (this.refreshToken) {
      sessionStorage.setItem(STORAGE_KEYS.refresh, this.refreshToken)
    }
  },
  logout() {
    this.user = null
    this.token = null
    this.refreshToken = null
    this.isLoggedIn = false
    Object.values(STORAGE_KEYS).forEach(k => sessionStorage.removeItem(k))
  }
})