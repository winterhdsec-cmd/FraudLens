<template>
  <div class="police-system-layout">
    <MainLayout />
    <LoginPanel v-if="!store.isLoggedIn && !isFullPage" />
  </div>
</template>

<script setup>
import { computed, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useFraudLens } from './composables/useFraudLens.js'
import LoginPanel from './components/LoginPanel.vue'
import MainLayout from './layouts/MainLayout.vue'

const route = useRoute()
const isFullPage = computed(() => route.meta?.fullPage)

const appState = useFraudLens()
provide('appState', appState)

const { store } = appState
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
