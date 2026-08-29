<template>
  <div class="route-progress" :class="{ 'rp-busy': busy }" aria-hidden="true">
    <div class="rp-bar"></div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

// 所有路由都是 () => import(...) 懒加载，首次进入某页要下载 chunk。
// 没有这个条的话点击菜单后界面毫无反馈，像卡死一样。
const router = useRouter()
const busy = ref(false)
let timer = null

const stopBefore = router.beforeEach(() => {
  if (timer) clearTimeout(timer)
  busy.value = true
  return true
})

const stopAfter = router.afterEach(() => {
  // 稍作延迟再收起：立刻消失会闪一下，反而更晃眼
  timer = setTimeout(() => { busy.value = false }, 320)
})

onUnmounted(() => {
  stopBefore?.()
  stopAfter?.()
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.route-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: 3000;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.route-progress.rp-busy { opacity: 1; }

.rp-bar {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, #00c6ff, #00d4ff, #10b981);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.6);
}
.route-progress.rp-busy .rp-bar {
  animation: rp-sweep 0.9s ease-out forwards;
}

@keyframes rp-sweep {
  0%   { width: 0; }
  70%  { width: 72%; }
  100% { width: 100%; }
}
</style>
