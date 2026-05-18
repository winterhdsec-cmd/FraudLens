import { reactive } from 'vue'

const savedToken = localStorage.getItem('fraudlens_token')
const savedUser = localStorage.getItem('fraudlens_user')
const savedRefreshToken = localStorage.getItem('fraudlens_refresh')

export const store = reactive({
  user: savedUser ? JSON.parse(savedUser) : null,
  token: savedToken || null,
  refreshToken: savedRefreshToken || null,
  isLoggedIn: !!savedToken,
  login(user, token, refreshToken) {
    this.user = user
    this.token = token
    this.refreshToken = refreshToken || null
    this.isLoggedIn = true
    localStorage.setItem('fraudlens_token', token)
    localStorage.setItem('fraudlens_user', JSON.stringify(user))
    if (refreshToken) localStorage.setItem('fraudlens_refresh', refreshToken)
  },
  logout() {
    this.user = null
    this.token = null
    this.refreshToken = null
    this.isLoggedIn = false
    localStorage.removeItem('fraudlens_token')
    localStorage.removeItem('fraudlens_user')
    localStorage.removeItem('fraudlens_refresh')
  }
})