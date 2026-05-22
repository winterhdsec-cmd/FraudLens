<template>
  <div class="police-system-layout">
    <div v-if="!store.isLoggedIn && !isFullPage" class="login-overlay">
      <div class="login-container tech-card">
        <div class="login-header">
          <div class="login-logo-wrapper">
            <div class="login-logo-ring"></div>
            <div class="login-logo-icon">🛡️</div>
          </div>
          <h2 class="login-title">反诈情报分析系统</h2>
          <p class="login-subtitle">AI INTELLIGENT SYSTEM</p>
        </div>
        <div class="login-form">
          <div class="login-field">
            <span class="login-field-icon">👤</span>
            <el-input v-model="loginForm.username" placeholder="用户名" size="large" class="login-input" @keyup.enter="handleLogin" />
          </div>
          <div class="login-field">
            <span class="login-field-icon">🔑</span>
            <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" class="login-input" show-password @keyup.enter="handleLogin" />
          </div>
          <div v-if="loginError" class="login-error">{{ loginError }}</div>
          <el-progress v-if="loginLoading" :percentage="loginProgress" :stroke-width="4" color="#00d4ff" :show-text="false" style="margin-bottom:12px" />
          <el-button class="login-btn" type="primary" size="large" :loading="loginLoading" @click="handleLogin">
            <span>{{ loginLoading ? '正在加载研判模型...' : '登 录' }}</span>
          </el-button>
        </div>
        <div class="login-footer">
          <span class="login-footer-text">智能研判平台 v3.0</span>
        </div>
      </div>
    </div>
    <div class="particle-bg" v-if="!isFullPage">
      <div v-for="i in 15" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>
    <div class="grid-overlay" v-if="!isFullPage"></div>
    <div class="scan-line" v-if="!isFullPage"></div>

    <el-dialog v-model="showProgress" :close-on-click-modal="false" :show-close="false" width="420px" class="progress-dialog">
      <div class="progress-body">
        <div class="progress-animation"><span class="pulse-dot"></span></div>
        <div class="progress-title">正在智能研判</div>
        <div class="progress-status">{{ progressMessage }}</div>
        <el-progress :percentage="progressPercent" :stroke-width="6" striped striped-flow />
        <div class="progress-hint">AI 正在分析案情数据，请耐心等待</div>
      </div>
    </el-dialog>

    <el-dialog v-model="showResult" width="480px" class="result-dialog">
      <div class="result-body">
        <div class="result-icon">✅</div>
        <div class="result-title">研判完成</div>
        <div class="result-stats">
          <div class="result-stat"><div class="rs-value">{{ resultStats.cases }}</div><div class="rs-label">发现案件</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.gangs }}</div><div class="rs-label">识别团伙</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.time }}</div><div class="rs-label">用时</div></div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showResult = false" size="large">留在当前页</el-button>
        <el-button type="primary" @click="goToResults" size="large">查看分析结果 →</el-button>
      </template>
    </el-dialog>

    <aside class="sidebar" v-if="!isFullPage">
      <div class="logo-area">
        <div class="logo-icon-wrapper"><div class="logo-ring"></div><div class="logo-icon">🛡️</div></div>
        <h2>反诈情报分析</h2>
        <span class="sub-title">AI INTELLIGENT SYSTEM</span>
        <div class="logo-badge"><span class="badge-dot"></span><span>智能研判平台</span></div>
      </div>
      <el-menu :default-active="activeMenu" class="side-menu" @select="handleMenuSelect">
        <div class="menu-group"><div class="menu-group-title">数据采集</div>
          <el-menu-item index="input"><template #title><div class="menu-item-content"><span class="menu-icon">📝</span><span class="menu-text">文本录入</span></div></template></el-menu-item>
          <el-menu-item index="upload"><template #title><div class="menu-item-content"><span class="menu-icon">📂</span><span class="menu-text">文件上传</span></div></template></el-menu-item>
          <el-menu-item index="api"><template #title><div class="menu-item-content"><span class="menu-icon">🔌</span><span class="menu-text">API接入</span></div></template></el-menu-item>
        </div>
        <div class="menu-group"><div class="menu-group-title">系统总览</div>
          <el-menu-item index="dashboard"><template #title><div class="menu-item-content"><span class="menu-icon">📊</span><span class="menu-text">数据看板</span></div></template></el-menu-item>
          <el-menu-item index="alerts" @click="navigateTo('alerts')"><template #title><div class="menu-item-content"><span class="menu-icon">🔔</span><span class="menu-text">预警中心</span><span v-if="unresolvedAlertCount > 0" class="menu-badge">{{ unresolvedAlertCount > 99 ? '99+' : unresolvedAlertCount }}</span></div></template></el-menu-item>
        </div>
        <div class="menu-group"><div class="menu-group-title">研判分析</div>
          <el-menu-item index="overview"><template #title><div class="menu-item-content"><span class="menu-icon">📊</span><span class="menu-text">案件总览</span></div></template></el-menu-item>
          <el-menu-item index="case-detail"><template #title><div class="menu-item-content"><span class="menu-icon">🔍</span><span class="menu-text">案件详情</span></div></template></el-menu-item>
          <el-menu-item index="groups"><template #title><div class="menu-item-content"><span class="menu-icon">👥</span><span class="menu-text">团伙画像</span></div></template></el-menu-item>
          <el-menu-item index="details"><template #title><div class="menu-item-content"><span class="menu-icon">📈</span><span class="menu-text">深度分析</span></div></template></el-menu-item>
          <el-menu-item index="network"><template #title><div class="menu-item-content"><span class="menu-icon">🕸️</span><span class="menu-text">关联网络</span></div></template></el-menu-item>
        </div>
        <div class="menu-group"><div class="menu-group-title">深度研判</div>
          <el-menu-item index="capital-flow"><template #title><div class="menu-item-content"><span class="menu-icon">💰</span><span class="menu-text">资金流向</span></div></template></el-menu-item>
          <el-menu-item index="dispatch"><template #title><div class="menu-item-content"><span class="menu-icon">📋</span><span class="menu-text">预警派单</span></div></template></el-menu-item>
          <el-menu-item index="key-persons"><template #title><div class="menu-item-content"><span class="menu-icon">👤</span><span class="menu-text">重点人员</span></div></template></el-menu-item>
        </div>
        <div class="menu-group"><div class="menu-group-title">输出报告</div>
          <el-menu-item index="report"><template #title><div class="menu-item-content"><span class="menu-icon">📄</span><span class="menu-text">报告生成</span></div></template></el-menu-item>
        </div>
        <div class="menu-group"><div class="menu-group-title">系统管理</div>
          <el-menu-item index="status"><template #title><div class="menu-item-content"><span class="menu-icon">📊</span><span class="menu-text">系统监控</span></div></template></el-menu-item>
          <el-menu-item index="admin"><template #title><div class="menu-item-content"><span class="menu-icon">⚙️</span><span class="menu-text">系统管理</span></div></template></el-menu-item>
        </div>
      </el-menu>
      <div class="system-status">
        <div class="status-row"><div class="status-indicator"><div class="status-dot"></div><span>系统运行正常</span></div><div class="version">v3.0</div></div>
        <div class="status-details">
          <div class="status-item"><span class="status-label">AI引擎</span><span class="status-value online">在线</span></div>
          <div class="status-item"><span class="status-label">数据库</span><span class="status-value online">已连接</span></div>
        </div>
        <div class="logout-area" v-if="store.isLoggedIn">
          <el-button class="logout-btn" size="small" @click="handleLogout"><span>🚪</span> 退出登录</el-button>
        </div>
      </div>
    </aside>
    <main class="main-content" :class="{ 'main-full': isFullPage }" v-loading="loading" element-loading-text="AI 正在进行深度研判分析...">
      <div class="search-bar" v-if="store.isLoggedIn && !isFullPage">
        <div class="search-wrapper">
          <span class="search-icon">🔍</span>
          <el-input
            v-model="searchQuery"
            placeholder="搜索案件编号、受害人、诈骗类型..."
            size="default"
            @input="handleSearchDebounced"
            @blur="onSearchBlur"
            class="global-search-input"
          >
            <template #suffix>
              <span v-if="searchLoading" class="search-loading">⏳</span>
            </template>
          </el-input>
          <div v-if="searchResults.length" class="search-dropdown">
            <div v-for="item in searchResults" :key="item.case_id" class="search-result-item" @mousedown.prevent="handleSearchSelect(item)">
              <span class="search-result-id">{{ item.case_id }}</span>
              <span class="search-result-title">{{ item.title }}</span>
              <span class="search-result-type">
                <el-tag size="small" type="info">{{ item.scam_type || '其他' }}</el-tag>
              </span>
            </div>
          </div>
        </div>
      </div>
      <div class="content-wrapper"><RouterView /></div>
    </main>
  </div>
</template>

<script setup>
import { provide, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useFraudLens } from './composables/useFraudLens.js'
import NetworkGraph from './components/NetworkGraph.vue'

const route = useRoute()
const isFullPage = computed(() => route.meta?.fullPage)

const appState = useFraudLens()
provide('appState', appState)

const {
  store, activeMenu, loading,
  showProgress, showResult, progressPercent, progressMessage, resultStats,
  loginForm, loginLoading, loginError, loginProgress,
  handleLogin, handleLogout, handleMenuSelect,
  getParticleStyle, goToResults,
  searchQuery, searchResults, searchLoading,
  handleSearchInput, handleSearchSelect,
  navigateTo, unresolvedAlertCount
} = appState

let searchTimer = null
const handleSearchDebounced = (val) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => handleSearchInput(val), 300)
}
const onSearchBlur = () => {
  setTimeout(() => { searchResults.value = [] }, 200)
}
</script>

<style scoped>
.police-system-layout { display: flex; height: 100vh; width: 100vw; background: var(--bg-primary); position: relative; }
.sidebar { width: 240px; min-width: 240px; height: 100vh; background: linear-gradient(180deg, #0f1525 0%, #1a1f2e 100%); border-right: 1px solid rgba(0, 198, 255, 0.12); box-shadow: inset -1px 0 0 rgba(0, 198, 255, 0.1); display: flex; flex-direction: column; overflow-y: auto; z-index: 10; }
.logo-area { padding: 24px 20px 16px; text-align: center; border-bottom: 1px solid rgba(0, 198, 255, 0.1); }
.logo-icon-wrapper { position: relative; width: 52px; height: 52px; margin: 0 auto 12px; }
.logo-ring { position: absolute; inset: -4px; border: 2px solid var(--accent-cyan); border-radius: 50%; animation: spin 8s linear infinite; opacity: 0.5; will-change: transform; }
.logo-icon { position: relative; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 28px; background: var(--gradient-primary); border-radius: 50%; }
.logo-area h2 { font-size: 16px; color: var(--text-primary); margin: 0; font-weight: 600; }
.sub-title { font-size: 10px; color: var(--text-muted); letter-spacing: 3px; display: block; margin-top: 2px; }
.logo-badge { display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; padding: 2px 10px; background: rgba(0, 198, 255, 0.1); border: 1px solid rgba(0, 198, 255, 0.2); border-radius: 10px; font-size: 11px; color: var(--accent-cyan); }
.badge-dot { width: 5px; height: 5px; background: var(--accent-cyan); border-radius: 50%; animation: pulse 3s infinite; }
.side-menu { flex: 1; background: transparent; border: none; padding: 8px 0; }
.menu-group { margin: 6px 0; position: relative; }
.menu-group + .menu-group::before { content: ''; display: block; height: 1px; margin: 4px 12px; background: rgba(0, 198, 255, 0.06); }
.menu-group-title { padding: 10px 20px 4px; font-size: 11px; color: rgba(0, 212, 255, 0.5); text-transform: uppercase; letter-spacing: 2px; font-weight: 700; }
.side-menu .el-menu-item { height: 42px; line-height: 42px; color: var(--text-secondary) !important; background: transparent !important; border: none; margin: 1px 8px; border-radius: 8px; padding-left: 16px !important; transition: all 0.25s ease; }
.side-menu .el-menu-item:hover { background: rgba(0, 198, 255, 0.1) !important; color: #ffffff !important; border-left: 2px solid rgba(0, 198, 255, 0.4); }
.side-menu .el-menu-item.is-active { background: linear-gradient(90deg, rgba(0, 198, 255, 0.2) 0%, rgba(0, 198, 255, 0.02) 100%) !important; color: #ffffff !important; border-left: 3px solid var(--accent-cyan) !important; box-shadow: 0 0 12px rgba(0, 198, 255, 0.1); }
.menu-item-content { display: flex; align-items: center; gap: 12px; }
.menu-icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
.menu-text { font-size: 13px; }
.menu-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; background: #ef4444; color: white; font-size: 11px; font-weight: 700; border-radius: 9px; margin-left: auto; box-shadow: 0 0 8px rgba(239,68,68,0.5); }
.system-status { padding: 14px 16px; border-top: 1px solid rgba(0, 198, 255, 0.1); background: rgba(0, 0, 0, 0.15); }
.status-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.status-indicator { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.status-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px rgba(16, 185, 129, 0.7); }
.version { font-size: 10px; color: var(--text-muted); font-family: 'JetBrains Mono', 'Consolas', monospace; letter-spacing: 1px; }
.status-details { display: flex; flex-direction: column; gap: 5px; }
.status-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
.status-label { color: var(--text-muted); }
.status-value { color: var(--text-secondary); }
.status-value.online { color: #10b981; }
.logout-area { margin-top: 10px; }
.logout-btn { width: 100%; border-color: rgba(239, 68, 68, 0.3) !important; color: var(--accent-red) !important; font-size: 12px; }
.main-content { flex: 1; height: 100vh; overflow-y: auto; position: relative; z-index: 1; }
.search-bar { padding: 12px 20px 0; }
.search-wrapper { position: relative; max-width: 500px; }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); z-index: 2; font-size: 14px; }
.global-search-input :deep(.el-input__wrapper) { padding-left: 36px; background: rgba(10, 14, 26, 0.6) !important; border: 1px solid rgba(0, 198, 255, 0.2); border-radius: 8px; }
.global-search-input :deep(.el-input__wrapper:hover) { border-color: rgba(0, 198, 255, 0.4); }
.global-search-input :deep(.el-input__wrapper.is-focus) { border-color: var(--accent-cyan); box-shadow: 0 0 10px rgba(0, 198, 255, 0.15); }
.global-search-input :deep(.el-input__inner) { color: #e2e8f0; }
.global-search-input :deep(.el-input__inner::placeholder) { color: #64748b; }
.search-loading { font-size: 12px; }
.search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: var(--bg-secondary); border: 1px solid rgba(0, 198, 255, 0.3); border-radius: 0 0 8px 8px; max-height: 320px; overflow-y: auto; z-index: 100; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5); }
.search-result-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; border-bottom: 1px solid rgba(0, 198, 255, 0.06); transition: background 0.15s; }
.search-result-item:hover { background: rgba(0, 198, 255, 0.08); }
.search-result-item:last-child { border-bottom: none; }
.search-result-id { font-size: 11px; color: var(--accent-cyan); background: rgba(0, 198, 255, 0.1); padding: 1px 6px; border-radius: 3px; white-space: nowrap; }
.search-result-title { flex: 1; font-size: 13px; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-result-type { flex-shrink: 0; }
.content-wrapper { padding: 20px; max-width: 1600px; margin: 0 auto; }
.main-full .content-wrapper { padding: 0; max-width: none; margin: 0; }
.login-overlay { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 1000; background: var(--bg-primary); }
.login-container { width: 400px; padding: 40px; text-align: center; }
.login-header { margin-bottom: 32px; }
.login-logo-wrapper { position: relative; width: 72px; height: 72px; margin: 0 auto 16px; }
.login-logo-ring { position: absolute; inset: -6px; border: 2px solid var(--accent-cyan); border-radius: 50%; animation: spin 6s linear infinite; }
.login-logo-icon { position: relative; width: 72px; height: 72px; display: flex; align-items: center; justify-content: center; font-size: 36px; background: var(--gradient-primary); border-radius: 50%; }
.login-title { font-size: 24px; color: var(--text-primary); margin: 0 0 4px; }
.login-subtitle { font-size: 12px; color: var(--text-muted); letter-spacing: 4px; }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.login-field { position: relative; }
.login-field-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); z-index: 2; font-size: 16px; }
.login-input :deep(.el-input__wrapper) { padding-left: 42px; }
.login-error { color: var(--accent-red); font-size: 13px; text-align: center; }
.login-btn { width: 100%; height: 48px; font-size: 16px; margin-top: 8px; }
.login-footer { margin-top: 24px; }
.login-footer-text { font-size: 12px; color: var(--text-muted); }
.particle-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
.particle { position: absolute; background: var(--accent-cyan); border-radius: 50%; opacity: 0.08; animation: float linear infinite; will-change: transform; }
.grid-overlay { position: fixed; inset: 0; background-image: linear-gradient(rgba(0,198,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,198,255,0.03) 1px, transparent 1px); background-size: 40px 40px; pointer-events: none; z-index: 0; }
.scan-line { position: fixed; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent); opacity: 0.15; z-index: 0; animation: scan 4s ease-in-out infinite; pointer-events: none; }
:deep(.progress-dialog .el-dialog) { background: var(--bg-secondary); border: 1px solid var(--border-primary); border-radius: var(--radius-xl); }
.progress-body { padding: 20px; text-align: center; }
.progress-animation { margin-bottom: 16px; }
.pulse-dot { display: inline-block; width: 16px; height: 16px; background: var(--accent-cyan); border-radius: 50%; animation: pulse 1s ease-in-out infinite; box-shadow: 0 0 20px rgba(0, 198, 255, 0.6); }
.progress-title { font-size: 18px; color: var(--text-primary); margin-bottom: 8px; }
.progress-status { font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; }
.progress-hint { font-size: 12px; color: var(--text-muted); margin-top: 12px; }
.result-body { text-align: center; padding: 20px; }
.result-icon { font-size: 48px; margin-bottom: 12px; }
.result-title { font-size: 22px; color: var(--text-primary); margin-bottom: 20px; }
.result-stats { display: flex; justify-content: center; gap: 32px; }
.result-stat { text-align: center; }
.rs-value { font-size: 28px; color: var(--accent-cyan); font-weight: 700; }
.rs-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes float { 0% { transform: translateY(100vh) rotate(0deg); opacity: 0; } 10% { opacity: 0.15; } 90% { opacity: 0.15; } 100% { transform: translateY(-10vh) rotate(720deg); opacity: 0; } }
@keyframes scan { 0% { top: -2px; } 100% { top: 100%; } }
</style>