<template>
  <div class="error-fallback">
    <div class="ef-card glass-card">
      <div class="ef-icon">
        <el-icon :size="56"><WarningFilled /></el-icon>
      </div>
      <h2 class="ef-title">页面出错了</h2>
      <p class="ef-desc">
        界面在渲染时遇到异常。可以先重试刷新，若反复出现请返回看板。
      </p>

      <details v-if="detail" class="ef-detail">
        <summary>技术细节</summary>
        <pre class="ef-pre">{{ detail }}</pre>
      </details>

      <div class="ef-actions">
        <el-button type="primary" @click="$emit('retry')">
          <el-icon><Refresh /></el-icon> 刷新重试
        </el-button>
        <el-button @click="$emit('home')">
          <el-icon><HomeFilled /></el-icon> 返回看板
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  error: { type: [Error, Object, String], default: null }
})
defineEmits(['retry', 'home'])

// 只在开发环境下展开技术细节，演示时保持界面干净
const detail = computed(() => {
  if (!import.meta.env.DEV) return ''
  const e = props.error
  if (!e) return ''
  if (typeof e === 'string') return e
  return [e.message, e.stack].filter(Boolean).join('\n').slice(0, 800)
})
</script>

<style scoped>
.error-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.ef-card {
  max-width: 520px;
  width: 100%;
  padding: 40px 36px;
  text-align: center;
  border: 1px solid rgba(255, 107, 107, 0.25);
}

.ef-icon {
  color: #ff6b6b;
  margin-bottom: 16px;
  opacity: 0.9;
}

.ef-title {
  margin: 0 0 10px;
  font-size: 20px;
  font-weight: 600;
  color: var(--dark-color-text-1, #e2e8f0);
}

.ef-desc {
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--dark-color-text-3, #94a3b8);
}

.ef-detail {
  margin: 0 0 20px;
  text-align: left;
  font-size: 12px;
}

.ef-detail summary {
  cursor: pointer;
  color: var(--dark-color-text-3, #94a3b8);
  padding: 6px 0;
}

.ef-pre {
  max-height: 200px;
  overflow: auto;
  margin: 8px 0 0;
  padding: 12px;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 8px;
  color: #ffb4b4;
  font-size: 11px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.ef-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
