<template>
  <div class="main-layout">
    <!-- 进度对话框 -->
    <el-dialog v-model="showProgress" :close-on-click-modal="false" :show-close="false" width="420px" class="progress-dialog">
      <div class="progress-body">
        <div class="progress-animation"><span class="pulse-dot"></span></div>
        <div class="progress-title">正在智能研判</div>
        <div class="progress-status">{{ progressMessage }}</div>
        <el-progress :percentage="progressPercent" :stroke-width="6" striped striped-flow />
        <div class="progress-hint">AI 正在分析案情数据，请耐心等待</div>
      </div>
    </el-dialog>

    <!-- 结果对话框 -->
    <el-dialog v-model="showResult" width="560px" class="result-dialog">
      <div class="result-body">
        <div class="result-icon"><el-icon :size="48"><CircleCheckFilled /></el-icon></div>
        <div class="result-title">研判完成</div>
        <div class="result-stats">
          <div class="result-stat"><div class="rs-value">{{ resultStats.cases }}</div><div class="rs-label">发现案件</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.gangs }}</div><div class="rs-label">识别团伙</div></div>
          <div class="result-stat"><div class="rs-value">{{ resultStats.time }}</div><div class="rs-label">用时</div></div>
        </div>
        <div v-if="importedCaseRows.length" class="result-cases-list">
          <div class="rcl-header">本次导入案件（点击编号跳转详情）：</div>
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
        <el-button @click="goToCapitalFlowAll" size="large"><el-icon><Money /></el-icon> 查看资金流向</el-button>
        <el-button type="primary" @click="goToResults" size="large"><el-icon><DataAnalysis /></el-icon> 查看分析结果 →</el-button>
      </template>
    </el-dialog>

    <!-- 顶栏（一级分组导航） -->
    <header class="app-header" v-if="!isFullPage">
      <div class="header-left">
        <div class="mini-logo" @click="router.push({ name: 'dashboard' })">
          <div class="logo-icon-wrapper small"><div class="logo-ring"></div><div class="logo-icon"><el-icon><Aim /></el-icon></div></div>
          <span class="mini-logo-text">反诈情报<span class="mini-logo-accent">FraudLens</span></span>
        </div>
        <el-menu mode="horizontal" :default-active="activeGroup" class="top-menu" :ellipsis="false" @select="handleGroupSelect">
          <el-menu-item v-for="g in menuGroups" :key="g.key" :index="g.key">
            <el-icon><component :is="g.icon" /></el-icon>
            <span class="top-menu-label">{{ g.label }}</span>
          </el-menu-item>
        </el-menu>
      </div>
      <div class="header-right">
        <span class="top-time">{{ nowStr }}</span>
        <span class="top-user"><el-icon><User /></el-icon> {{ currentUsername }}</span>
        <el-icon class="collapse-btn" :size="18" @click="collapsed = !collapsed">
          <Expand v-if="collapsed" /><Fold v-else />
        </el-icon>
      </div>
    </header>

    <!-- 侧边栏（当前分组二级菜单） -->
    <aside class="sidebar" v-if="!isFullPage" :class="{ collapsed }">
      <div class="logo-area">
        <div class="logo-icon-wrapper"><div class="logo-ring"></div><div class="logo-icon"><el-icon><Aim /></el-icon></div></div>
        <h2>反诈情报分析</h2>
        <span class="sub-title">AI INTELLIGENT SYSTEM</span>
        <div class="logo-badge"><span class="badge-dot"></span><span>智能研判平台</span></div>
      </div>
      <el-menu :default-active="activeMenu" class="side-menu" :collapse="collapsed" :collapse-transition="false" @select="handleMenuSelect">
        <div class="menu-group">
          <div class="menu-group-title">{{ menuGroups.find(g => g.key === activeGroup)?.label }}</div>
          <el-menu-item v-for="item in activeGroupItems" :key="item.name" :index="item.name">
            <template #title>
              <div class="menu-item-content">
                <el-icon class="menu-icon"><component :is="item.icon" /></el-icon>
                <span class="menu-text">{{ item.label }}</span>
                <span v-if="item.badge === 'alerts' && unresolvedAlertCount > 0" class="menu-badge">{{ unresolvedAlertCount > 99 ? '99+' : unresolvedAlertCount }}</span>
              </div>
            </template>
          </el-menu-item>
        </div>
      </el-menu>
      <div class="system-status">
        <div class="status-row"><div class="status-indicator"><div class="status-dot"></div><span>系统运行正常</span></div><div class="version">v3.0</div></div>
        <div class="status-details">
          <div class="status-item"><span class="status-label">AI引擎</span><span class="status-value online">在线</span></div>
          <div class="status-item"><span class="status-label">数据库</span><span class="status-value online">已连接</span></div>
        </div>
        <div class="logout-area" v-if="store.isLoggedIn">
          <el-button class="logout-btn" size="small" @click="handleLogout"><el-icon><SwitchButton /></el-icon> 退出登录</el-button>
        </div>
      </div>
    </aside>

    <!-- 主区 -->
    <main class="main-content" :class="{ 'main-full': isFullPage }" v-loading="loading" element-loading-text="AI 正在进行深度研判分析...">
      <div class="tabs-bar" v-if="!isFullPage">
        <div class="tabs-list">
          <div
            v-for="tab in tabs"
            :key="tab.name"
            class="tab-item"
            :class="{ active: activeTab === tab.name }"
            @click="selectTab(tab.name)"
          >
            <span class="tab-title">{{ tab.title }}</span>
            <el-icon v-if="!tab.fixed" class="tab-close" :size="12" @click.stop="closeTab(tab.name)"><Close /></el-icon>
          </div>
        </div>
      </div>
      <div class="search-bar" v-if="store.isLoggedIn && !isFullPage">
        <div class="search-wrapper">
          <el-icon class="search-icon"><Search /></el-icon>
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
      <div class="content-wrapper">
        <RouterView v-slot="{ Component, route: r }">
          <KeepAlive>
            <transition name="page-fade">
              <component :is="Component" :key="r.name" />
            </transition>
          </KeepAlive>
        </RouterView>
      </div>
    </main>
  </div>
</template>

<script setup>
import { inject, computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const appState = inject('appState')

// 侧边栏折叠
const collapsed = ref(false)
const currentTitle = computed(() => router.currentRoute.value.meta?.title || '')

// ===== 导航架构：顶栏一级分组 + 侧边栏二级菜单 =====
const menuGroups = [
  { key: 'data', label: '数据采集', icon: 'UploadFilled', items: [
    { name: 'input', label: '文本录入', icon: 'EditPen' },
    { name: 'upload', label: '文件上传', icon: 'Upload' }
  ]},
  { key: 'center', label: '总览中心', icon: 'DataAnalysis', items: [
    { name: 'dashboard', label: '数据看板', icon: 'DataAnalysis' },
    { name: 'alerts', label: '预警中心', icon: 'Bell', badge: 'alerts' }
  ]},
  { key: 'case', label: '案件研判', icon: 'Files', items: [
    { name: 'overview', label: '案件管理', icon: 'Files' },
    { name: 'groups', label: '团伙画像', icon: 'User' }
  ]},
  { key: 'tools', label: '办案工具', icon: 'Tools', items: [
    { name: 'workbench', label: '办案工作台', icon: 'Tools' },
    { name: 'capital-flow', label: '资金流向', icon: 'Money' },
    { name: 'key-persons', label: '重点人员', icon: 'Avatar' }
  ]},
  { key: 'assist', label: '输出与助手', icon: 'Document', items: [
    { name: 'report', label: '报告生成', icon: 'Document' },
    { name: 'chat', label: 'AI对话助手', icon: 'ChatDotRound' }
  ]},
  { key: 'system', label: '系统管理', icon: 'Setting', items: [
    { name: 'admin', label: '系统管理', icon: 'Setting' }
  ]}
]
// 当前路由所属分组
const activeGroup = computed(() => {
  const g = menuGroups.find(grp => grp.items.some(it => it.name === activeMenu.value))
  return g ? g.key : 'center'
})
// 侧边栏显示当前分组的二级菜单
const activeGroupItems = computed(() => {
  const g = menuGroups.find(grp => grp.key === activeGroup.value)
  return g ? g.items : []
})
// 点击顶栏分组 → 跳到该组第一个页面
const handleGroupSelect = (key) => {
  const g = menuGroups.find(grp => grp.key === key)
  if (g && g.items.length) {
    router.push({ name: g.items[0].name })
  }
}
const currentUsername = computed(() => store?.user?.display_name || store?.user?.username || '用户')

// ===== 多标签页（tabs） =====
const tabs = ref([{ name: 'dashboard', title: '数据看板', fixed: true }])
const activeTab = ref('dashboard')
watch(() => router.currentRoute.value.name, (name) => {
  if (!name) return
  const title = router.currentRoute.value.meta?.title || '页面'
  const exists = tabs.value.find(t => t.name === name)
  if (!exists) {
    tabs.value.push({ name, title })
  }
  activeTab.value = name
}, { immediate: true })
const selectTab = (tabName) => {
  if (router.currentRoute.value.name !== tabName) {
    router.push({ name: tabName })
  }
}
const closeTab = (tabName) => {
  const idx = tabs.value.findIndex(t => t.name === tabName)
  if (idx === -1 || tabs.value[idx].fixed) return
  tabs.value.splice(idx, 1)
  if (activeTab.value === tabName) {
    const last = tabs.value[tabs.value.length - 1]
    router.push({ name: last ? last.name : 'dashboard' })
  }
}

// 顶栏实时时间
const nowStr = ref('')
let timeTimer = null
const updateTime = () => {
  const d = new Date()
  nowStr.value = d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', weekday: 'short' }) + ' ' + d.toLocaleTimeString('zh-CN', { hour12: false })
}
onMounted(() => { updateTime(); timeTimer = setInterval(updateTime, 1000) })
onUnmounted(() => { if (timeTimer) clearInterval(timeTimer) })

const {
  store, activeMenu, loading,
  showProgress, showResult, progressPercent, progressMessage, resultStats,
  handleLogout, handleMenuSelect,
  navigateTo, unresolvedAlertCount,
  searchQuery, searchResults, searchLoading,
  handleSearchInput, handleSearchSelect,
  lastImportedCaseIds, cases, getCaseTitle, gangs,
  goToResults, goToCapitalFlowAll
} = appState

const isFullPage = computed(() => router.currentRoute.value.meta?.fullPage)

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
.main-layout {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto 1fr;
  height: 100vh; width: 100vw;
  position: relative;
}

/* ====== 顶栏（一级导航） ====== */
.app-header {
  grid-column: 1 / -1; grid-row: 1;
  height: 52px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 14px 0 10px;
  background: linear-gradient(180deg, var(--color-bg-layout) 0%, var(--color-bg-hover) 100%);
  border-bottom: 1px solid var(--color-border-1);
  position: relative;
  z-index: 20;
}
/* 顶栏底部 cyan 光带 */
.app-header::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.35), transparent);
  pointer-events: none;
}
.header-left { display: flex; align-items: center; height: 100%; min-width: 0; gap: 4px; }
.mini-logo { cursor: pointer; display: flex; align-items: center; padding: 0 14px 0 4px; height: 100%; gap: 10px; border-right: 1px solid var(--color-divider); margin-right: 8px; }
.logo-icon-wrapper.small { position: relative; width: 30px; height: 30px; margin: 0; flex-shrink: 0; }
.logo-icon-wrapper.small .logo-icon { width: 30px; height: 30px; font-size: 16px; border-radius: 8px; box-shadow: var(--shadow-sm), 0 0 14px var(--dark-color-primary-glow-soft); }
.mini-logo-text { font-size: 13px; font-weight: var(--font-weight-semibold); color: var(--color-text-1); white-space: nowrap; display: flex; align-items: center; gap: 8px; }
.mini-logo-accent { font-size: 10px; color: var(--color-primary); letter-spacing: 1px; font-family: var(--font-family-mono); }
.top-menu {
  border-bottom: none !important;
  height: 52px;
  background: transparent;
  display: flex !important;
  align-items: center;
}
.top-menu .el-menu-item,
.top-menu .el-submenu {
  float: none !important;
  display: inline-flex !important;
  align-items: center;
  height: 52px;
  line-height: 1;
  padding: 0 16px;
  font-size: 13px;
  border-radius: 6px;
  margin: 4px 2px;
  color: var(--color-text-2) !important;
  transition: color var(--transition-fast), background var(--transition-fast);
}
.top-menu .el-menu-item:hover {
  background: var(--color-primary-light) !important;
  color: var(--color-primary) !important;
}
.top-menu .el-menu-item.is-active {
  background: var(--color-primary-light) !important;
  color: var(--color-primary) !important;
  border-bottom: none !important;
  box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.2);
}
.top-menu .el-menu-item.is-active::after {
  content: '';
  position: absolute;
  left: 50%; bottom: 3px;
  transform: translateX(-50%);
  width: 20px; height: 2px;
  border-radius: 2px;
  background: var(--color-primary);
  box-shadow: 0 0 6px var(--dark-color-primary-glow);
}
.top-menu .el-submenu__title { float: none !important; height: 52px; line-height: 52px; padding: 0 14px; }
.header-right { display: flex; align-items: center; gap: 16px; color: var(--color-text-3); font-size: 12px; white-space: nowrap; }
.header-right .top-time { font-variant-numeric: tabular-nums; }
.header-right .collapse-btn { cursor: pointer; color: var(--color-text-2); transition: color var(--transition-fast); }
.header-right .collapse-btn:hover { color: var(--color-primary); }

/* ====== 顶栏（面包屑） ====== */
/* ====== 多标签页 ====== */
.tabs-bar {
  display: flex; align-items: flex-end;
  padding: 6px 16px 0;
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border-1);
}
.tabs-list {
  display: flex; gap: 4px; align-items: flex-end;
  overflow-x: auto; flex: 1;
  scrollbar-width: none;
}
.tabs-list::-webkit-scrollbar { display: none; }
.tab-item {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-1);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  font-size: 12px;
  color: var(--color-text-2);
  cursor: pointer;
  white-space: nowrap;
  transition: color var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
  position: relative;
}
.tab-item::after {
  content: '';
  position: absolute;
  top: -1px; left: 8px; right: 8px;
  height: 2px;
  border-radius: 0 0 2px 2px;
  background: var(--color-primary);
  opacity: 0;
  box-shadow: 0 0 8px var(--dark-color-primary-glow);
  transition: opacity var(--transition-fast);
}
.tab-item:hover { color: var(--color-text-1); }
.tab-item.active {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: linear-gradient(180deg, var(--color-primary-light), var(--color-bg-card));
}
.tab-item.active::after { opacity: 1; }
.tab-item.active .tab-title { font-weight: 600; }
.tab-close { border-radius: 50%; padding: 1px; color: var(--color-text-2); }
.tab-close:hover { background: var(--color-bg-hover); color: var(--color-danger); }

/* ====== 侧边栏 ====== */
.sidebar {
  grid-column: 1; grid-row: 2;
  width: 232px; min-width: 232px; height: 100%;
  background: linear-gradient(180deg, var(--color-bg-layout), var(--color-bg-page) 100%);
  border-right: 1px solid var(--color-border-1);
  display: flex; flex-direction: column; overflow-y: auto; z-index: 10;
  transition: border-color var(--transition-base);
}
.logo-area { padding: 14px 16px 10px; text-align: center; border-bottom: 1px solid var(--color-divider); }
.logo-icon-wrapper { position: relative; width: 36px; height: 36px; margin: 0 auto 6px; }
.logo-ring { display: none; }
.logo-icon { position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 18px; background: var(--gradient-primary); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm), 0 0 16px var(--dark-color-primary-glow-soft); color: #fff; }
.logo-area h2 { font-size: 14px; color: var(--color-text-1); margin: 0; font-weight: var(--font-weight-semibold); }
.sub-title { font-size: 9px; color: var(--color-text-4); letter-spacing: 2px; display: block; margin-top: 1px; }
.logo-badge { display: none; }
.badge-dot { width: 5px; height: 5px; background: var(--color-success); border-radius: 50%; }
.side-menu { flex: 1; background: transparent; border: none; padding: 6px 0; }
.menu-group { margin: 4px 0; position: relative; }
.menu-group + .menu-group::before { content: ''; display: block; height: 1px; margin: 4px 12px; background: var(--color-divider); }
.menu-group-title {
  padding: 10px 20px 4px;
  font-size: 11px;
  color: var(--color-text-4);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: var(--font-weight-semibold);
}
.side-menu .el-menu-item {
  height: 38px; line-height: 38px;
  color: var(--color-text-2) !important;
  background: transparent !important;
  border: none;
  margin: 2px 8px;
  border-radius: var(--radius-md);
  padding-left: 14px !important;
  transition: all var(--transition-fast);
  position: relative;
}
.side-menu .el-menu-item::before { display: none; }
.side-menu .el-menu-item:hover {
  background: var(--color-primary-light) !important;
  color: var(--color-primary) !important;
  transform: none;
  box-shadow: 0 0 12px var(--dark-color-primary-glow-soft);
}
.side-menu .el-menu-item.is-active {
  background: var(--color-primary-light) !important;
  color: var(--color-primary) !important;
  border-left: none;
  box-shadow: inset 3px 0 0 var(--color-primary);
  font-weight: var(--font-weight-medium);
}
.menu-item-content { display: flex; align-items: center; gap: 10px; position: relative; z-index: 1; }
.menu-icon { font-size: 16px; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.menu-text { font-size: 13px; font-weight: var(--font-weight-regular); }
.menu-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; background: var(--color-danger); color: #fff; font-size: 11px; font-weight: var(--font-weight-semibold); border-radius: 9px; margin-left: auto; }
.system-status { padding: 12px 14px; border-top: 1px solid var(--color-divider); background: var(--color-bg-layout); }
.status-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.status-indicator { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-2); }
.status-dot { width: 6px; height: 6px; background: var(--color-success); border-radius: 50%; }
.version { font-size: 10px; color: var(--color-text-3); font-family: var(--font-family-mono); letter-spacing: 1px; }
.status-details { display: flex; flex-direction: column; gap: 4px; }
.status-item { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
.status-label { color: var(--color-text-2); }
.status-value { color: var(--color-text-1); }
.status-value.online { color: var(--color-success); }
.logout-area { margin-top: 8px; }
.logout-btn { width: 100%; border-color: var(--color-border-1) !important; color: var(--color-text-2) !important; font-size: 12px; }
.logout-btn:hover { border-color: var(--color-danger) !important; color: var(--color-danger) !important; background: var(--color-bg-hover) !important; }

/* ====== 侧边栏折叠态 ====== */
.sidebar.collapsed { width: 64px; min-width: 64px; }
.sidebar.collapsed .logo-area { padding: 16px 0 12px; }
.sidebar.collapsed .logo-area h2,
.sidebar.collapsed .sub-title,
.sidebar.collapsed .logo-badge,
.sidebar.collapsed .menu-group-title { display: none; }
.sidebar.collapsed .system-status { padding: 12px 10px; }
.sidebar.collapsed .status-row { justify-content: center; }
.sidebar.collapsed .status-row .status-indicator span,
.sidebar.collapsed .version,
.sidebar.collapsed .status-details { display: none; }
.sidebar.collapsed .logout-btn { font-size: 0; }
.sidebar.collapsed .logout-btn .el-icon { margin: 0; font-size: 15px; }

/* ====== 主区 ====== */
.main-content { grid-column: 2; grid-row: 2; height: 100%; overflow-y: auto; position: relative; z-index: 1; background: var(--color-bg-page); }
.search-bar { padding: 12px 20px 0; }
.search-wrapper { position: relative; max-width: 520px; }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); z-index: 2; font-size: 14px; }
.global-search-input :deep(.el-input__wrapper) {
  padding-left: 36px;
  background: var(--color-bg-card) !important;
  border: 1px solid var(--color-border-1);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}
.global-search-input :deep(.el-input__wrapper:hover) { border-color: var(--color-primary); }
.global-search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}
.global-search-input :deep(.el-input__inner) { color: var(--color-text-1); }
.global-search-input :deep(.el-input__inner::placeholder) { color: var(--color-text-4); }
.search-loading { font-size: 12px; }
.search-dropdown {
  position: absolute; top: 100%; left: 0; right: 0;
  background: var(--color-bg-overlay);
  border: 1px solid var(--color-border-1);
  border-radius: var(--radius-md);
  max-height: 340px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: var(--shadow-lg);
}
.search-result-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--color-divider);
  transition: background var(--transition-fast);
}
.search-result-item:hover {
  background: var(--color-bg-hover);
}
.search-result-item:last-child { border-bottom: none; }
.search-result-id {
  font-size: 11px;
  color: var(--color-primary);
  background: var(--color-primary-light);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  font-family: var(--font-family-mono);
}
.search-result-title { flex: 1; font-size: 13px; color: var(--color-text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-result-type { flex-shrink: 0; }
.content-wrapper { padding: 16px; max-width: 1600px; margin: 0 auto; }
.main-full .content-wrapper { padding: 0; max-width: none; margin: 0; }

/* ====== 页面过渡（淡入） ====== */
.page-fade-enter-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-fade-leave-active { transition: opacity 0.08s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(3px); }
.page-fade-leave-to { opacity: 0; }

/* ====== 对话框 ====== */
:deep(.progress-dialog .el-dialog) { background: var(--color-bg-card); border: 1px solid var(--color-border-1); border-radius: var(--radius-xl); }
.progress-body { padding: 20px; text-align: center; }
.progress-animation { margin-bottom: 16px; }
.pulse-dot { display: inline-block; width: 14px; height: 14px; background: var(--color-primary); border-radius: 50%; animation: pulse 1s ease-in-out infinite; }
.progress-title { font-size: 18px; color: var(--color-text-1); margin-bottom: 8px; }
.progress-status { font-size: 13px; color: var(--color-text-2); margin-bottom: 16px; }
.progress-hint { font-size: 12px; color: var(--color-text-3); margin-top: 12px; }
.result-body { text-align: center; padding: 20px; }
.result-icon { font-size: 48px; margin-bottom: 12px; display: inline-block; }
.result-title { font-size: 22px; color: var(--color-text-1); margin-bottom: 20px; font-weight: var(--font-weight-bold); }
.result-stats { display: flex; justify-content: center; gap: 32px; }
.result-stat { text-align: center; }
.rs-value { font-size: 28px; color: var(--color-primary); font-weight: var(--font-weight-bold); }
.rs-label { font-size: 12px; color: var(--color-text-3); margin-top: 4px; }
.result-cases-list {
  margin-top: 16px; padding: 12px 16px;
  background: var(--color-bg-hover); border-radius: var(--radius-md);
  border: 1px solid var(--color-border-1);
}
.rcl-header { font-size: 12px; color: var(--color-text-3); margin-bottom: 10px; }
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
</style>
