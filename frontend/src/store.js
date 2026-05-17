import { reactive } from 'vue'

export const store = reactive({
  user: null,
  token: null,
  isLoggedIn: false,
  login(user, token) {
    this.user = user
    this.token = token
    this.isLoggedIn = true
  },
  logout() {
    this.user = null
    this.token = null
    this.isLoggedIn = false
  }
})