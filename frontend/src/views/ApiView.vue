<template>
  <div class="view-section">
    <div class="section-header">
      <div class="header-left">
        <h2 class="section-title">
          <span class="title-icon">🔌</span>
          多源数据API接入
        </h2>
        <p class="section-desc">对接银行风控、110报警平台、反诈平台等外部数据源</p>
      </div>
    </div>

    <el-alert
      title="功能开发中"
      type="warning"
      :closable="false"
      show-icon
      class="todo-alert"
    >
      <template #default>
        外部数据源（银行风控、110报警平台、反诈平台）接入功能正在开发中，暂未提供真实数据对接能力。正式上线后将支持真实数据获取、同步与研判分析。
      </template>
    </el-alert>

    <div class="todo-placeholder tech-card">
      <el-empty description="暂无可用数据源，功能开发中" :image-size="80">
        <template #image>
          <span class="placeholder-emoji">🚧</span>
        </template>
      </el-empty>

      <div class="placeholder-hint">以下数据源计划接入，敬请期待：</div>

      <div class="placeholder-sources">
        <div class="placeholder-source-item">
          <span class="source-emoji bank">🏦</span>
          <div class="source-text">
            <div class="source-name">银行风控系统</div>
            <div class="source-status-text">待接入</div>
          </div>
          <span class="status-tag todo">待接入</span>
        </div>
        <div class="placeholder-source-item">
          <span class="source-emoji police">🚔</span>
          <div class="source-text">
            <div class="source-name">110报警平台</div>
            <div class="source-status-text">待接入</div>
          </div>
          <span class="status-tag todo">待接入</span>
        </div>
        <div class="placeholder-source-item">
          <span class="source-emoji antiFraud">🛡️</span>
          <div class="source-text">
            <div class="source-name">反诈平台接入</div>
            <div class="source-status-text">待接入</div>
          </div>
          <span class="status-tag todo">待接入</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const { activeMenu } = state
</script>

<style scoped>
.todo-alert { margin-bottom: 16px; }
.todo-placeholder { padding: 32px 20px; text-align: center; }
.placeholder-emoji { font-size: 64px; display: inline-block; }
.placeholder-hint { margin-top: 8px; font-size: 13px; color: var(--text-secondary); }
.placeholder-sources { display: flex; flex-direction: column; gap: 10px; max-width: 520px; margin: 20px auto 0; text-align: left; }
.placeholder-source-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-primary); border-radius: 8px; }
.source-emoji { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.source-emoji.bank { background: rgba(245,158,11,0.15); }
.source-emoji.police { background: rgba(0,212,255,0.15); }
.source-emoji.antiFraud { background: rgba(139,92,246,0.15); }
.source-text { flex: 1; }
.source-text .source-name { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.source-text .source-status-text { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.status-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
.status-tag.todo { background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }
</style>
