<template>
  <div class="police-system-layout">
    <div v-if="!store.isLoggedIn" class="login-overlay">
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
          <el-button class="login-btn" type="primary" size="large" :loading="loginLoading" @click="handleLogin">
            <span>{{ loginLoading ? '验证中...' : '登 录' }}</span>
          </el-button>
        </div>
        <div class="login-footer">
          <span class="login-footer-text">智能研判平台 v2.0</span>
        </div>
      </div>
    </div>
    <div class="particle-bg">
      <div v-for="i in 60" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>
    <div class="grid-overlay"></div>
    <div class="scan-line"></div>

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

    <aside class="sidebar">
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
          <el-menu-item index="alerts"><template #title><div class="menu-item-content"><span class="menu-icon">🔔</span><span class="menu-text">预警中心</span></div></template></el-menu-item>
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
        <div class="status-row"><div class="status-indicator"><div class="status-dot"></div><span>系统运行正常</span></div><div class="version">v2.0</div></div>
        <div class="status-details">
          <div class="status-item"><span class="status-label">AI引擎</span><span class="status-value online">在线</span></div>
          <div class="status-item"><span class="status-label">数据库</span><span class="status-value online">已连接</span></div>
        </div>
        <div class="logout-area" v-if="store.isLoggedIn">
          <el-button class="logout-btn" size="small" @click="handleLogout"><span>🚪</span> 退出登录</el-button>
        </div>
      </div>
    </aside>
    <main class="main-content" v-loading="loading" element-loading-text="AI 正在进行深度研判分析...">
      <div class="content-wrapper"><RouterView /></div>
    </main>
  </div>
</template>

<script setup>
import { provide } from 'vue'
import { useFraudLens } from './composables/useFraudLens.js'
import NetworkGraph from './components/NetworkGraph.vue'

const appState = useFraudLens()
provide('appState', appState)

const {
  store, activeMenu, loading,
  showProgress, showResult, progressPercent, progressMessage, resultStats,
  loginForm, loginLoading, loginError,
  handleLogin, handleLogout, handleMenuSelect,
  getParticleStyle, goToResults
} = appState
</script>

<style scoped>
.police-system-layout { display: flex; height: 100vh; width: 100vw; background: var(--bg-primary); position: relative; overflow: hidden; }
.sidebar { width: 240px; min-width: 240px; height: 100vh; background: var(--bg-secondary); border-right: 1px solid var(--border-primary); display: flex; flex-direction: column; overflow-y: auto; z-index: 10; }
.logo-area { padding: 24px 20px 16px; text-align: center; border-bottom: 1px solid var(--border-primary); }
.logo-icon-wrapper { position: relative; width: 52px; height: 52px; margin: 0 auto 12px; }
.logo-ring { position: absolute; inset: -4px; border: 2px solid var(--accent-cyan); border-radius: 50%; animation: spin 4s linear infinite; opacity: 0.5; }
.logo-icon { position: relative; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 28px; background: var(--gradient-primary); border-radius: 50%; }
.logo-area h2 { font-size: 16px; color: var(--text-primary); margin: 0; font-weight: 600; }
.sub-title { font-size: 10px; color: var(--text-muted); letter-spacing: 3px; display: block; margin-top: 2px; }
.logo-badge { display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; padding: 2px 10px; background: rgba(0, 198, 255, 0.1); border: 1px solid rgba(0, 198, 255, 0.2); border-radius: 10px; font-size: 11px; color: var(--accent-cyan); }
.badge-dot { width: 5px; height: 5px; background: var(--accent-cyan); border-radius: 50%; animation: pulse 2s infinite; }
.side-menu { flex: 1; background: transparent; border: none; padding: 8px 0; }
.menu-group { margin: 4px 0; }
.menu-group-title { padding: 8px 20px 4px; font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.side-menu .el-menu-item { height: 40px; line-height: 40px; color: var(--text-secondary) !important; background: transparent !important; border: none; margin: 1px 8px; border-radius: 8px; }
.side-menu .el-menu-item:hover { background: rgba(0, 198, 255, 0.08) !important; color: var(--text-primary) !important; }
.side-menu .el-menu-item.is-active { background: rgba(0, 198, 255, 0.15) !important; color: var(--accent-cyan) !important; }
.menu-item-content { display: flex; align-items: center; gap: 10px; }
.menu-icon { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; }
.menu-text { font-size: 13px; }
.system-status { padding: 16px 20px; border-top: 1px solid var(--border-primary); }
.status-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.status-indicator { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.status-dot { width: 6px; height: 6px; background: #10b981; border-radius: 50%; box-shadow: 0 0 6px rgba(16, 185, 129, 0.6); }
.version { font-size: 11px; color: var(--text-muted); }
.status-details { display: flex; flex-direction: column; gap: 4px; }
.status-item { display: flex; justify-content: space-between; font-size: 12px; }
.status-label { color: var(--text-muted); }
.status-value { color: var(--text-secondary); }
.status-value.online { color: #10b981; }
.logout-area { margin-top: 8px; }
.logout-btn { width: 100%; border-color: rgba(239, 68, 68, 0.3) !important; color: var(--accent-red) !important; font-size: 12px; }
.main-content { flex: 1; height: 100vh; overflow-y: auto; position: relative; z-index: 1; }
.content-wrapper { padding: 20px; max-width: 1600px; margin: 0 auto; }
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
.particle { position: absolute; background: var(--accent-cyan); border-radius: 50%; opacity: 0.15; animation: float linear infinite; }
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