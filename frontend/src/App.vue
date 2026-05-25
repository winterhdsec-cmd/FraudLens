<template>
  <div class="police-system-layout">
    <div v-if="!store.isLoggedIn && !isFullPage" class="login-overlay">
      <div class="login-bg-glow"></div>
      <div class="login-container">
        <div class="login-brand-panel">
          <div class="lbp-top">
            <div class="lbp-logo-wrapper">
              <div class="lbp-ring"></div>
              <div class="lbp-logo">🛡️</div>
            </div>
            <h2 class="lbp-title">反诈情报分析系统</h2>
            <p class="lbp-subtitle">AI INTELLIGENT SYSTEM</p>
            <div class="lbp-desc">基于大模型语义理解与无监督聚类的<br>诈骗情报智能研判平台</div>
          </div>
          <div class="lbp-stats">
            <div class="lbp-stat">
              <span class="lbs-value">77+</span>
              <span class="lbs-label">分析案件</span>
            </div>
            <div class="lbp-stat">
              <span class="lbs-value">12</span>
              <span class="lbs-label">识别团伙</span>
            </div>
            <div class="lbp-stat">
              <span class="lbs-value">92%</span>
              <span class="lbs-label">准确率</span>
            </div>
            <div class="lbp-stat">
              <span class="lbs-value">12s</span>
              <span class="lbs-label">平均响应</span>
            </div>
          </div>
          <div class="lbp-footer">
            <div class="lbp-tag" v-for="tag in loginTags" :key="tag">{{ tag }}</div>
          </div>
        </div>
        <div class="login-form-panel">
          <div class="lfp-header">
            <h3 class="lfp-title">用户登录</h3>
            <p class="lfp-desc">请输入您的账号信息以进入系统</p>
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
          <div class="lfp-security">
            <span class="sec-icon">🔒</span>
            <span class="sec-text">数据全程加密 · 安全可靠</span>
          </div>
        </div>
      </div>
      <div class="login-version">v3.0 · 大创项目成果展示</div>
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

    <el-dialog v-model="showResult" width="560px" class="result-dialog">
      <div class="result-body">
        <div class="result-icon">✅</div>
        <div class="result-title">研判完成</div>
        <div class="result-stats">
          <div class="result-stat"><div class="rs-value">{{ resultStats.cases }}</div><div class="rs-label">发现案件</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.gangs }}</div><div class="rs-label">识别团伙</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.time }}</div><div class="rs-label">用时</div></div>
        </div>
        <div v-if="importedCaseRows.length" class="result-cases-list">
          <div class="rcl-header">📋 本次导入案件（点击编号跳转详情）：</div>
          <div class="rcl-table">
            <div v-for="row in importedCaseRows" :key="row.id" class="rcl-row" @click="goToCaseDetail(row.id)">
              <span class="rcl-id">{{ row.id }}</span>
              <span class="rcl-title">{{ row.title }}</span>
              <span class="rcl-gang">
                <el-tag v-if="row.gangName" size="small" type="danger">{{ row.gangName }}</el-tag>
                <el-tag v-else size="small" type="info">未关联</el-tag>
              </span>
              <span class="rcl-arrow">→</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showResult = false" size="large">留在当前页</el-button>
        <el-button @click="goToCapitalFlowAll" size="large">💰 查看资金流向</el-button>
        <el-button type="primary" @click="goToResults" size="large">📊 查看分析结果 →</el-button>
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
              <span class="search-result-title">{{ item.title || '未知案件' }}</span>
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
import { useRoute, useRouter } from 'vue-router'
import { useFraudLens } from './composables/useFraudLens.js'
import NetworkGraph from './components/NetworkGraph.vue'

const route = useRoute()
const router = useRouter()
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
  navigateTo, unresolvedAlertCount,
  lastImportedCaseIds, cases, getCaseTitle, gangs
} = appState

const importedCaseRows = computed(() => {
  const ids = lastImportedCaseIds.value || []
  const caseList = cases.value || []
  return ids.map(id => {
    const c = caseList.find(x => (x.case_id === id || x.id === id))
    const gang = gangs.value?.find(g => {
      const related = g.related_cases || g.caseIds || g.case_ids || []
      return related.includes(id)
    })
    return {
      id: id,
      title: c?.title || c?.victim_name || '未知案件',
      gangName: gang?.gang_name || gang?.name || ''
    }
  })
})

let searchTimer = null
const handleSearchDebounced = (val) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => handleSearchInput(val), 300)
}
const onSearchBlur = () => {
  setTimeout(() => { searchResults.value = [] }, 200)
}
const goToCapitalFlow = (caseId) => {
  showResult.value = false
  if (appState.flowSearchCaseId !== undefined) {
    appState.flowSearchCaseId = caseId
  }
  router.push({ name: 'capital-flow' })
}
const goToCapitalFlowAll = () => {
  showResult.value = false
  if (appState.flowSearchCaseId !== undefined) {
    appState.flowSearchCaseId = ''
  }
  router.push({ name: 'capital-flow' })
}
const goToCaseDetail = (caseId) => {
  showResult.value = false
  const found = cases.value?.find(c => (c.case_id === caseId || c.id === caseId))
  if (found && appState.selectedCase) {
    appState.selectedCase.value = found
  }
  router.push({ name: 'case-detail' })
}
</script>

<style scoped>
.police-system-layout { display: flex; height: 100vh; width: 100vw; background: var(--bg-primary); position: relative; }
.sidebar {
  width: 240px; min-width: 240px; height: 100vh;
  background: linear-gradient(180deg, #0f1525 0%, #111827 50%, #0d1320 100%);
  border-right: 1px solid rgba(0, 198, 255, 0.12);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3), inset -1px 0 0 rgba(0, 198, 255, 0.1);
  display: flex; flex-direction: column; overflow-y: auto; z-index: 10;
  transition: box-shadow 0.3s ease;
}
.logo-area { padding: 24px 20px 16px; text-align: center; border-bottom: 1px solid rgba(0, 198, 255, 0.1); }
.logo-icon-wrapper { position: relative; width: 52px; height: 52px; margin: 0 auto 12px; }
.logo-ring { position: absolute; inset: -4px; border: 2px solid var(--accent-cyan); border-radius: 50%; animation: spin 8s linear infinite; opacity: 0.5; will-change: transform; }
.logo-icon { position: relative; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 28px; background: var(--gradient-primary); border-radius: 50%; box-shadow: 0 0 20px rgba(0, 198, 255, 0.2); }
.logo-area h2 { font-size: 16px; color: var(--text-primary); margin: 0; font-weight: 600; }
.sub-title { font-size: 10px; color: var(--text-muted); letter-spacing: 3px; display: block; margin-top: 2px; }
.logo-badge { display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; padding: 2px 10px; background: rgba(0, 198, 255, 0.1); border: 1px solid rgba(0, 198, 255, 0.2); border-radius: 10px; font-size: 11px; color: var(--accent-cyan); transition: all 0.3s ease; }
.logo-badge:hover { background: rgba(0, 198, 255, 0.18); border-color: rgba(0, 198, 255, 0.35); box-shadow: 0 0 12px rgba(0, 198, 255, 0.1); }
.badge-dot { width: 5px; height: 5px; background: var(--accent-cyan); border-radius: 50%; animation: pulse 3s infinite; }
.side-menu { flex: 1; background: transparent; border: none; padding: 8px 0; }
.menu-group { margin: 6px 0; position: relative; }
.menu-group + .menu-group::before { content: ''; display: block; height: 1px; margin: 4px 12px; background: rgba(0, 198, 255, 0.06); }
.menu-group-title {
  padding: 10px 20px 4px;
  font-size: 10px;
  color: rgba(0, 212, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 2.5px;
  font-weight: 800;
  font-family: 'SF Mono', 'Consolas', monospace;
}
.side-menu .el-menu-item {
  height: 42px; line-height: 42px;
  color: var(--text-secondary) !important;
  background: transparent !important;
  border: none;
  margin: 2px 8px;
  border-radius: 10px;
  padding-left: 16px !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}
.side-menu .el-menu-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(0, 198, 255, 0.03), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.side-menu .el-menu-item:hover::before { opacity: 1; }
.side-menu .el-menu-item:hover {
  background: rgba(0, 198, 255, 0.1) !important;
  color: #ffffff !important;
  transform: translateX(3px);
}
.side-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, rgba(0, 198, 255, 0.2) 0%, rgba(0, 198, 255, 0.02) 100%) !important;
  color: #ffffff !important;
  border-left: 3px solid var(--accent-cyan) !important;
  box-shadow: 0 0 16px rgba(0, 198, 255, 0.12), inset 0 0 20px rgba(0, 198, 255, 0.03);
  transform: translateX(0);
}
.menu-item-content { display: flex; align-items: center; gap: 12px; position: relative; z-index: 1; }
.menu-icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
.menu-text { font-size: 13px; font-weight: 500; }
.menu-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; background: #ef4444; color: white; font-size: 11px; font-weight: 700; border-radius: 9px; margin-left: auto; box-shadow: 0 0 8px rgba(239,68,68,0.5); animation: pulse 3s infinite; }
.system-status { padding: 14px 16px; border-top: 1px solid rgba(0, 198, 255, 0.1); background: rgba(0, 0, 0, 0.2); }
.status-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.status-indicator { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.status-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px rgba(16, 185, 129, 0.7); animation: pulse 3s infinite; }
.version { font-size: 10px; color: var(--text-muted); font-family: 'JetBrains Mono', 'Consolas', monospace; letter-spacing: 1px; }
.status-details { display: flex; flex-direction: column; gap: 5px; }
.status-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; transition: all 0.2s ease; }
.status-item:hover { padding-left: 4px; }
.status-label { color: var(--text-muted); }
.status-value { color: var(--text-secondary); }
.status-value.online { color: #10b981; text-shadow: 0 0 8px rgba(16,185,129,0.3); }
.logout-area { margin-top: 10px; }
.logout-btn { width: 100%; border-color: rgba(239, 68, 68, 0.3) !important; color: var(--accent-red) !important; font-size: 12px; transition: all 0.3s ease !important; }
.logout-btn:hover { border-color: rgba(239, 68, 68, 0.6) !important; background: rgba(239, 68, 68, 0.1) !important; box-shadow: 0 0 12px rgba(239,68,68,0.15) !important; }
.main-content { flex: 1; height: 100vh; overflow-y: auto; position: relative; z-index: 1; }
.search-bar { padding: 12px 20px 0; animation: fadeIn 0.5s ease; }
.search-wrapper { position: relative; max-width: 520px; }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); z-index: 2; font-size: 14px; }
.global-search-input :deep(.el-input__wrapper) {
  padding-left: 36px;
  background: rgba(10, 14, 26, 0.7) !important;
  border: 1px solid rgba(0, 198, 255, 0.15);
  border-radius: 10px;
  transition: all 0.3s ease;
}
.global-search-input :deep(.el-input__wrapper:hover) { border-color: rgba(0, 198, 255, 0.35); }
.global-search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 16px rgba(0, 198, 255, 0.15), 0 2px 12px rgba(0,0,0,0.2);
}
.global-search-input :deep(.el-input__inner) { color: #e2e8f0; }
.global-search-input :deep(.el-input__inner::placeholder) { color: #64748b; }
.search-loading { font-size: 12px; }
.search-dropdown {
  position: absolute; top: 100%; left: 0; right: 0;
  background: rgba(10, 14, 26, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 198, 255, 0.25);
  border-radius: 0 0 12px 12px;
  max-height: 340px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 198, 255, 0.05);
  animation: fadeInScale 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.search-result-item {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 198, 255, 0.06);
  transition: all 0.15s ease;
}
.search-result-item:hover {
  background: rgba(0, 198, 255, 0.08);
  padding-left: 20px;
}
.search-result-item:last-child { border-bottom: none; }
.search-result-id {
  font-size: 11px;
  color: var(--accent-cyan);
  background: rgba(0, 198, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  font-family: 'SF Mono', 'Consolas', monospace;
}
.search-result-title { flex: 1; font-size: 13px; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-result-type { flex-shrink: 0; }
.content-wrapper { padding: 20px; max-width: 1600px; margin: 0 auto; }
.main-full .content-wrapper { padding: 0; max-width: none; margin: 0; }
/* ====== 登录页面 - 公安科技风 ====== */

/* 全屏遮罩背景 */
.login-overlay {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  background:
    radial-gradient(ellipse 80% 60% at 50% 40%, rgba(0, 100, 200, 0.08) 0%, transparent 70%),
    radial-gradient(ellipse 60% 50% at 30% 60%, rgba(0, 212, 255, 0.05) 0%, transparent 60%),
    radial-gradient(ellipse at center, #0f1525 0%, #070b14 80%);
  overflow: hidden;
}

/* 背景光晕 */
.login-bg-glow {
  position: absolute;
  width: 600px; height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.06) 0%, transparent 70%);
  top: 5%; left: -10%;
  pointer-events: none;
  animation: breathe 6s ease-in-out infinite;
}

/* 主容器 - 双面板布局 */
.login-container {
  display: flex;
  width: 820px;
  min-height: 520px;
  border-radius: var(--radius-xl);
  background: rgba(10, 14, 26, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 198, 255, 0.15);
  box-shadow:
    0 0 60px rgba(0, 198, 255, 0.05),
    0 20px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
  overflow: hidden;
  animation: fadeInScale 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

/* 左上角装饰光 */
.login-container::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px;
  width: 180px; height: 180px;
  background: radial-gradient(circle at 0 0, rgba(0, 212, 255, 0.15) 0%, transparent 70%);
  pointer-events: none;
}

/* 右下角装饰光 */
.login-container::after {
  content: '';
  position: absolute;
  bottom: -1px; right: -1px;
  width: 180px; height: 180px;
  background: radial-gradient(circle at 100% 100%, rgba(0, 212, 255, 0.1) 0%, transparent 70%);
  pointer-events: none;
}

/* ====== 左侧品牌面板 ====== */
.login-brand-panel {
  width: 400px;
  min-width: 400px;
  padding: 44px 36px 32px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background:
    linear-gradient(160deg, rgba(0, 100, 200, 0.08) 0%, transparent 50%),
    linear-gradient(135deg, rgba(10, 18, 40, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%);
  border-right: 1px solid rgba(0, 198, 255, 0.1);
  position: relative;
  overflow: hidden;
}

/* 左侧面板装饰 - 竖线 */
.login-brand-panel::before {
  content: '';
  position: absolute;
  top: 40px; bottom: 40px; right: -1px;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(0, 198, 255, 0.2), transparent);
}

/* Logo区域 */
.lbp-top { text-align: center; }

.lbp-logo-wrapper {
  position: relative;
  width: 80px; height: 80px;
  margin: 0 auto 20px;
}

.lbp-ring {
  position: absolute;
  inset: -8px;
  border: 2px solid rgba(0, 212, 255, 0.3);
  border-radius: 50%;
  animation: spin 8s linear infinite;
  box-shadow:
    0 0 20px rgba(0, 198, 255, 0.1),
    inset 0 0 20px rgba(0, 198, 255, 0.05);
}

.lbp-ring::before {
  content: '';
  position: absolute;
  top: -2px; left: 50%;
  transform: translateX(-50%);
  width: 6px; height: 6px;
  background: var(--accent-cyan);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(0, 198, 255, 0.8);
}

.lbp-logo {
  position: relative;
  width: 80px; height: 80px;
  display: flex; align-items: center; justify-content: center;
  font-size: 38px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.2) 0%, rgba(0, 132, 255, 0.1) 100%);
  border-radius: 50%;
  box-shadow:
    0 0 30px rgba(0, 198, 255, 0.15),
    inset 0 0 20px rgba(0, 198, 255, 0.05);
}

.lbp-title {
  font-size: 22px;
  color: var(--text-primary);
  margin: 0 0 6px;
  font-weight: 700;
  letter-spacing: 2px;
}

.lbp-subtitle {
  font-size: 11px;
  color: var(--accent-cyan);
  letter-spacing: 5px;
  margin: 0 0 14px;
  font-weight: 500;
  opacity: 0.7;
}

.lbp-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.8;
  margin: 0;
}

/* 统计数据 */
.lbp-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 24px 0;
  border-top: 1px solid rgba(0, 198, 255, 0.08);
  border-bottom: 1px solid rgba(0, 198, 255, 0.08);
}

.lbp-stat {
  text-align: center;
  padding: 8px 4px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 198, 255, 0.06);
  transition: all 0.3s ease;
}

.lbp-stat:hover {
  background: rgba(0, 198, 255, 0.06);
  border-color: rgba(0, 198, 255, 0.15);
  transform: translateY(-1px);
}

.lbs-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--accent-cyan);
  line-height: 1.2;
  text-shadow: 0 0 20px rgba(0, 198, 255, 0.2);
}

.lbs-label {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 底部标签 */
.lbp-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 16px;
  justify-content: center;
}

.lbp-tag {
  padding: 3px 12px;
  font-size: 11px;
  color: var(--text-secondary);
  background: rgba(0, 198, 255, 0.06);
  border: 1px solid rgba(0, 198, 255, 0.1);
  border-radius: 12px;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}

.lbp-tag:hover {
  background: rgba(0, 198, 255, 0.12);
  border-color: rgba(0, 198, 255, 0.25);
  color: var(--accent-cyan);
}

/* ====== 右侧表单面板 ====== */
.login-form-panel {
  flex: 1;
  padding: 44px 40px 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.lfp-header {
  text-align: center;
  margin-bottom: 32px;
}

.lfp-title {
  font-size: 20px;
  color: var(--text-primary);
  margin: 0 0 6px;
  font-weight: 600;
  letter-spacing: 1px;
}

.lfp-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login-field {
  position: relative;
}

.login-field-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  font-size: 16px;
  filter: grayscale(0.3);
}

.login-input :deep(.el-input__wrapper) {
  padding-left: 44px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.35) !important;
  border: 1px solid rgba(0, 198, 255, 0.12);
  transition: all 0.3s ease;
  box-shadow: none !important;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 198, 255, 0.25);
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-cyan) !important;
  box-shadow: 0 0 12px rgba(0, 198, 255, 0.15), inset 0 0 0 1px rgba(0, 198, 255, 0.1) !important;
  background: rgba(0, 0, 0, 0.5) !important;
}

.login-input :deep(.el-input__inner) {
  color: var(--text-primary);
  font-size: 14px;
}

.login-input :deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
  font-size: 13px;
}

.login-input :deep(.el-input__suffix) {
  color: var(--text-muted);
}

/* 错误提示 */
.login-error {
  color: var(--accent-red);
  font-size: 13px;
  text-align: center;
  background: rgba(239, 68, 68, 0.1);
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  animation: fadeIn 0.3s ease;
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-top: 4px;
  border-radius: 10px;
  letter-spacing: 4px;
  font-weight: 700;
  transition: all 0.3s ease !important;
}

.login-btn :deep(span) {
  letter-spacing: 4px;
}



/* 安全提示 */
.lfp-security {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(0, 198, 255, 0.06);
}

.sec-icon {
  font-size: 13px;
}

.sec-text {
  font-size: 12px;
  color: var(--text-muted);
}

/* 底部版本号 */
.login-version {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: rgba(100, 116, 139, 0.5);
  letter-spacing: 2px;
  z-index: 1001;
  font-family: 'SF Mono', 'Consolas', monospace;
}
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
.result-body { text-align: center; padding: 20px; animation: fadeInScale 0.4s ease; }
.result-icon { font-size: 48px; margin-bottom: 12px; display: inline-block; animation: floatUp 2s ease-in-out infinite; }
.result-title { font-size: 22px; color: var(--text-primary); margin-bottom: 20px; font-weight: 700; }
.result-stats { display: flex; justify-content: center; gap: 32px; }
.result-stat { text-align: center; }
.rs-value { font-size: 28px; color: var(--accent-cyan); font-weight: 700; }
.rs-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.result-cases-list {
  margin-top: 16px; padding: 12px 16px;
  background: rgba(0,0,0,0.2); border-radius: 8px;
  border: 1px solid rgba(0,198,255,0.08);
}
.rcl-header { font-size: 12px; color: #94a3b8; margin-bottom: 10px; }
.rcl-table { display: flex; flex-direction: column; gap: 4px; }
.rcl-row {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 6px;
  background: rgba(0,0,0,0.15); cursor: pointer;
  transition: all 0.15s;
}
.rcl-row:hover { background: rgba(0,198,255,0.08); }
.rcl-id { font-family: monospace; font-size: 12px; color: var(--accent-cyan); font-weight: 600; min-width: 80px; }
.rcl-title { flex: 1; font-size: 13px; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rcl-gang { min-width: 60px; text-align: center; }
.rcl-arrow { color: #475569; font-size: 14px; min-width: 16px; text-align: right; }
.rcl-row:hover .rcl-arrow { color: var(--accent-cyan); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes float { 0% { transform: translateY(100vh) rotate(0deg); opacity: 0; } 10% { opacity: 0.15; } 90% { opacity: 0.15; } 100% { transform: translateY(-10vh) rotate(720deg); opacity: 0; } }
@keyframes scan { 0% { top: -2px; } 100% { top: 100%; } }
</style>