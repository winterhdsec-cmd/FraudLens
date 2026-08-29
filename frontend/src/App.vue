<template>
  <div class="police-system-layout">
    <RouteProgress />
    <ErrorFallback
      v-if="renderError"
      :error="renderError"
      @retry="handleRetry"
      @home="handleGoHome"
    />
    <template v-else>
      <MainLayout />
      <LoginPanel v-if="!store.isLoggedIn && !isFullPage" />
    </template>
  </div>
</template>

<script setup>
import { computed, provide, ref, onErrorCaptured } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFraudLens } from './composables/useFraudLens.js'
import LoginPanel from './components/LoginPanel.vue'
import MainLayout from './layouts/MainLayout.vue'
import ErrorFallback from './components/ErrorFallback.vue'
import RouteProgress from './components/RouteProgress.vue'

const route = useRoute()
const router = useRouter()
const isFullPage = computed(() => route.meta?.fullPage)

const appState = useFraudLens()
provide('appState', appState)

const { store } = appState

// 错误边界：任一子孙组件在渲染/生命周期里抛错时兜住，
// 否则 Vue 会卸载整棵组件树，用户看到的是一片空白。
const renderError = ref(null)
onErrorCaptured((err, _instance, info) => {
  console.error('[FraudLens] 组件渲染异常:', err, info)
  renderError.value = err instanceof Error ? err : new Error(String(err))
  return false   // 不再向上冒泡，避免重复处理
})

// 出错后的组件状态往往已经不可信，整页重载比局部恢复可靠
const handleRetry = () => { window.location.reload() }
const handleGoHome = () => {
  renderError.value = null
  router.push({ name: 'dashboard' }).catch(() => window.location.reload())
}
</script>

<style scoped>
.police-system-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--color-bg-page);
  position: relative;
}
</style>
