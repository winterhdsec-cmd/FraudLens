<template>
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title">
        <el-icon v-if="icon" class="title-icon"><component :is="icon" /></el-icon>
        {{ title }}
      </h2>
      <p v-if="desc" class="section-desc">{{ desc }}</p>
    </div>
    <div v-if="$slots.default" class="header-right">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  desc: { type: String, default: '' },
  // Element Plus 图标组件名，如 'DataAnalysis'
  icon: { type: String, default: '' }
})
</script>

<!-- 样式复用全局 style.css 的 .section-header/.section-title/.section-desc -->
