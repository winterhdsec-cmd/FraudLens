// ============================================
// useAuth — 认证与会话模块
// 依赖注入：store/route/api 登录函数/ElMessage/onLoginSuccess(登录后初始化回调)
// ============================================
import { ref } from 'vue'

export function useAuth({ store, route, apiLogin, apiDemoLogin, ElMessage, onLoginSuccess }) {
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
        store.login(data.user || { username: loginForm.value.username }, data.access_token || data.token, data.refresh_token)
        loginForm.value = { username: '', password: '' }
        clearInterval(loginProgressTimer)
        loginLoading.value = false
        loginError.value = ''
        ElMessage.success('登录成功')
        if (onLoginSuccess) await onLoginSuccess()
        return
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
        store.login(data.user || { username: 'admin' }, data.access_token || data.token, data.refresh_token)
        loginForm.value = { username: '', password: '' }
        clearInterval(loginProgressTimer)
        loginLoading.value = false
        loginError.value = ''
        ElMessage.success('演示登录成功')
        if (onLoginSuccess) await onLoginSuccess()
        return
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

  const clearLoginProgressTimer = () => {
    if (loginProgressTimer) clearInterval(loginProgressTimer)
    loginProgressTimer = null
  }

  return {
    loginForm,
    loginLoading,
    loginError,
    loginProgress,
    handleLogin,
    handleDemoLogin,
    handleLogout,
    clearLoginProgressTimer
  }
}
