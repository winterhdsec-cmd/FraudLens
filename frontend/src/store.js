import { reactive } from 'vue'

const savedToken = localStorage.getItem('fraudlens_token')
const savedUser = localStorage.getItem('fraudlens_user')

export const store = reactive({
  user: savedUser ? JSON.parse(savedUser) : null,
  token: savedToken || null,
  isLoggedIn: !!savedToken,
  login(user, token) {
    this.user = user
    this.token = token
    this.isLoggedIn = true
    localStorage.setItem('fraudlens_token', token)
    localStorage.setItem('fraudlens_user', JSON.stringify(user))
  },
  logout() {
    this.user = null
    this.token = null
    this.isLoggedIn = false
    localStorage.removeItem('fraudlens_token')
    localStorage.removeItem('fraudlens_user')
  }
})