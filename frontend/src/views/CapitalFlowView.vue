<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title"><span class="title-icon">💰</span>资金流向追踪</h2>
      <p class="section-desc">按层级展示涉案资金流转链路，支持截图导出</p>
    </div>
    <div class="header-actions">
      <el-select v-model="selectedCaseId" placeholder="选择案件" size="small" style="width:260px" filterable @change="onCaseSelect" clearable>
        <el-option v-for="c in caseList" :key="c.case_id || c.id" :label="(c.case_id || c.id) + ' - ' + (c.title || c.victim_name || '未知')" :value="c.case_id || c.id" />
      </el-select>
      <el-input v-model="flowSearchCaseId" placeholder="输入案件编号" style="width:170px" size="small" clearable @clear="loadFlowData" @keyup.enter="loadFlowData" />
      <el-button type="primary" size="small" @click="loadFlowData">查询</el-button>
      <el-button v-if="capitalFlows.length" :type="screenshotMode ? 'success' : 'default'" size="small" @click="toggleScreenshotMode">
        <span>{{ screenshotMode ? '📷 退出截图' : '📷 截图模式' }}</span>
      </el-button>
    </div>
  </div>

  <div class="flow-container">
    <!-- 未选择案件时：展示所有案件列表供选择 -->
    <template v-if="!flowSearchCaseId">
      <div class="browser-panel">
        <div class="browser-header">
          <div class="bh-left">
            <div class="bh-tabs">
              <span class="bh-tab" :class="{ active: caseFilterMode === 'recent' }" @click="caseFilterMode = 'recent'">
                🆕 最近导入
                <span v-if="recentCount" class="bh-tab-count">{{ recentCount }}</span>
              </span>
              <span class="bh-tab" :class="{ active: caseFilterMode === 'all' }" @click="caseFilterMode = 'all'">
                📋 全部案件
                <span class="bh-tab-count">{{ (cases.value || []).length }}</span>
              </span>
            </div>
          </div>
          <div class="bh-right">
            <el-button size="small" @click="loadCases" :loading="caseLoading">🔄 刷新列表</el-button>
          </div>
        </div>
        <div v-if="caseLoading" class="empty-state" style="padding:60px 20px">
          <div class="empty-content"><div class="empty-icon" style="animation:pulse 1.5s infinite">🔍</div><h3 class="empty-title">加载中...</h3><p class="empty-desc">正在获取案件数据</p></div>
        </div>
        <div v-else-if="!caseList.length" class="empty-state" style="padding:60px 20px">
          <div class="empty-content"><div class="empty-icon">📂</div><h3 class="empty-title">暂无案件数据</h3><p class="empty-desc">请先通过文本录入或文件上传导入案件</p></div>
        </div>
        <div v-else class="case-browser-table">
          <div class="cbt-header">
            <span class="cbt-col col-id">案件编号</span>
            <span class="cbt-col col-title">案件名称</span>
            <span class="cbt-col col-type">诈骗类型</span>
            <span class="cbt-col col-status">状态</span>
            <span class="cbt-col col-victim">受害人</span>
            <span class="cbt-col col-action">操作</span>
          </div>
          <div v-for="c in caseList" :key="c.case_id || c.id" class="cbt-row" :class="{ 'cbt-row-recent': recentIdSet.has(c.case_id || c.id) }" @dblclick="browseToCase(c.case_id || c.id)">
            <span class="cbt-col col-id">
              <code>{{ c.case_id || c.id }}</code>
              <span v-if="recentIdSet.has(c.case_id || c.id)" class="recent-badge">新</span>
            </span>
            <span class="cbt-col col-title">{{ c.title || c.victim_name || '未知' }}</span>
            <span class="cbt-col col-type"><el-tag size="small" type="info" effect="dark">{{ c.scam_type || '其他' }}</el-tag></span>
            <span class="cbt-col col-status">
              <el-tag :type="c.status === '已复核' ? 'success' : 'warning'" size="small" effect="dark">{{ c.status || '待分析' }}</el-tag>
            </span>
            <span class="cbt-col col-victim">{{ c.victim_name || '—' }}</span>
            <span class="cbt-col col-action">
              <el-button size="small" type="primary" plain @click="browseToCase(c.case_id || c.id)">💰 查看资金流向</el-button>
            </span>
          </div>
        </div>
      </div>
    </template>
    <!-- 已选择案件但无资金流向数据 -->
    <template v-else-if="!capitalFlows.length">
      <div class="empty-state">
        <div class="empty-content">
          <div class="empty-icon">💰</div>
          <h3 class="empty-title">暂无资金流向数据</h3>
          <p class="empty-desc">案件 <strong>{{ flowSearchCaseId }}</strong> 暂无资金流向记录</p>
          <el-button size="small" @click="flowSearchCaseId = ''" style="margin-top:12px">← 返回案件列表</el-button>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="flow-summary" :class="{ 'screenshot-mode': screenshotMode }">
        <div class="summary-row">
          <div class="summary-item">
            <span class="si-icon">📋</span>
            <div class="si-body">
              <span class="si-label">案件编号</span>
              <span class="si-value">{{ flowSearchCaseId || '—' }}</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon">📄</span>
            <div class="si-body">
              <span class="si-label">案件名称</span>
              <span class="si-value">{{ currentCaseTitle }}</span>
            </div>
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-item">
            <span class="si-icon">🏦</span>
            <div class="si-body">
              <span class="si-label">涉案账户</span>
              <span class="si-value accent">{{ graphNodes.length }}个</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon">📊</span>
            <div class="si-body">
              <span class="si-label">资金层级</span>
              <span class="si-value accent">{{ maxFlowLevel }}层</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon">💰</span>
            <div class="si-body">
              <span class="si-label">总涉案金额</span>
              <span class="si-value accent">{{ formatTotalAmount }}</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon">🔄</span>
            <div class="si-body">
              <span class="si-label">交易笔数</span>
              <span class="si-value accent">{{ capitalFlows.length }}笔</span>
            </div>
          </div>
        </div>
      </div>

      <div class="network-container" :class="{ 'screenshot-mode': screenshotMode }">
        <MiniNetworkGraph
          v-if="graphNodes.length > 0"
          title="资金流向图谱"
          :nodes="graphNodes"
          :edges="graphEdges"
          :legends="graphLegends"
          :physics="graphPhysics"
          :node-defaults="graphNodeDefaults"
          :edge-defaults="graphEdgeDefaults"
          style="height:500px;width:100%"
        />
        <div v-else class="empty-state" style="height:540px;display:flex;align-items:center;justify-content:center">
          <div class="empty-content">
            <div class="empty-icon">📊</div>
            <h3 class="empty-title">暂无链路图数据</h3>
            <p class="empty-desc">请先查询案件以生成资金流向链路图</p>
          </div>
        </div>
      </div>
      <div v-if="!screenshotMode" class="flow-table-wrapper">
        <el-table :data="capitalFlows" style="width:100%" stripe size="small" max-height="280">
          <el-table-column prop="source_account" label="转出账户" min-width="140" />
          <el-table-column prop="target_account" label="转入账户" min-width="140" />
          <el-table-column prop="bank_name" label="开户行" width="120" />
          <el-table-column prop="amount" label="金额" width="110">
             <template #default="{row}">¥{{ Number(row.amount || 0).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="direction" label="方向" width="70">
            <template #default="{row}"><el-tag :type="row.direction==='out' ? 'warning' : 'danger'" size="small">{{row.direction === 'out' ? '转出' : '转入'}}</el-tag></template>
          </el-table-column>
          <el-table-column prop="level" label="层级" width="60" />
          <el-table-column prop="transaction_time" label="交易时间" width="160" />
        </el-table>
      </div>
      </template>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import MiniNetworkGraph from '../components/MiniNetworkGraph.vue'

const state = useAppState()
const {
  capitalFlows, flowSearchCaseId, loadFlowData,
  cases, lastImportedCaseIds
} = state

const selectedCaseId = ref('')
const screenshotMode = ref(false)
const caseLoading = ref(false)
const caseFilterMode = ref('recent') // 'all' | 'recent'
const recentIdSet = computed(() => new Set(lastImportedCaseIds.value))
const recentCount = computed(() => {
  if (!lastImportedCaseIds.value.length) return 0
  return (cases.value || []).filter(c => lastImportedCaseIds.value.includes(c.case_id || c.id)).length
})
const caseList = computed(() => {
  const all = cases.value || []
  if (caseFilterMode.value === 'recent' && lastImportedCaseIds.value.length) {
    return all.filter(c => lastImportedCaseIds.value.includes(c.case_id || c.id))
  }
  return all
})

async function loadCases() {
  caseLoading.value = true
  try {
    const { fetchCases } = await import('../api.js')
    const data = await fetchCases()
    if (data && Array.isArray(data)) {
      cases.value = data
    }
  } catch (e) {
    console.warn('加载案件列表失败:', e)
  } finally {
    caseLoading.value = false
  }
}

const currentCaseTitle = computed(() => {
  if (!flowSearchCaseId.value) return '—'
  const found = cases.value.find(c => (c.case_id || c.id) === flowSearchCaseId.value)
  return found?.title || found?.victim_name || '未知'
})

const maxFlowLevel = computed(() => {
  if (!capitalFlows.value.length) return 0
  return Math.max(...capitalFlows.value.map(f => f.level || 0))
})

const formatTotalAmount = computed(() => {
  if (!capitalFlows.value.length) return '¥0'
  const total = capitalFlows.value.reduce((s, f) => s + Number(f.amount || 0), 0)
  if (total >= 10000) return '¥' + (total / 10000).toFixed(1).replace(/\.0$/, '') + '万'
  return '¥' + total.toLocaleString()
})

const onCaseSelect = (val) => {
  if (val) {
    flowSearchCaseId.value = val
    loadFlowData()
  }
}

function browseToCase(caseId) {
  selectedCaseId.value = caseId
  flowSearchCaseId.value = caseId
  loadFlowData()
}

function toggleScreenshotMode() {
  screenshotMode.value = !screenshotMode.value
  if (screenshotMode.value) {
    nextTick(() => {
      document.querySelector('.network-container')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }
}

const formatAccountName = (name) => {
  if (!name || name.length <= 8) return name || ''
  return name.slice(0, 4) + '***' + name.slice(-4)
}

const getLevelColor = (level) => {
  if (level === 1) return { background: '#f43f5e', border: '#fb7185', highlight: { background: '#e11d48', border: '#f43f5e' } }
  if (level === 2) return { background: '#f97316', border: '#fb923c', highlight: { background: '#ea580c', border: '#f97316' } }
  return { background: '#06b6d4', border: '#22d3ee', highlight: { background: '#0891b2', border: '#06b6d4' } }
}

const getLevelLabel = (level) => {
  if (level === 1) return '一级卡'
  if (level === 2) return '二级卡'
  return '三级卡'
}

const graphNodes = computed(() => {
  if (!capitalFlows.value.length) return []
  const nodeMap = new Map()
  const addNode = (account, level, amount) => {
    if (!nodeMap.has(account)) {
      nodeMap.set(account, { level: level || 1, totalAmount: 0 })
    }
    const node = nodeMap.get(account)
    node.totalAmount += Number(amount || 0)
  }
  capitalFlows.value.forEach(flow => {
    const srcLevel = flow.level || (flow.source_level || 1)
    const tgtLevel = flow.level ? flow.level + 1 : (flow.target_level || 2)
    addNode(flow.source_account, srcLevel, flow.amount)
    addNode(flow.target_account, tgtLevel, flow.amount)
  })
  const maxAmount = Math.max(...Array.from(nodeMap.values()).map(n => n.totalAmount), 1)
  return Array.from(nodeMap.entries()).map(([account, data]) => {
    const ratio = data.totalAmount / maxAmount
    const sz = 18 + ratio * 22
    const amt = data.totalAmount
    return {
      id: account,
      label: formatAccountName(account),
      title: `<b>${formatAccountName(account)}</b><br>层级: ${getLevelLabel(data.level)}<br>涉案金额: ¥${amt.toLocaleString()}`,
      size: Math.round(sz),
      color: getLevelColor(data.level),
      level: data.level,
      amount: data.totalAmount,
      font: { color: '#e2e8f0', size: 11, face: 'sans-serif', strokeWidth: 3, strokeColor: '#0a0e1a' },
      shape: 'dot',
      borderWidth: 2,
      shadow: { enabled: true, size: 10, color: getLevelColor(data.level).background + '66' }
    }
  })
})

const graphEdges = computed(() => {
  if (!capitalFlows.value.length) return []
  return capitalFlows.value.map(flow => {
    const amt = Number(flow.amount || 0)
    return {
      from: flow.source_account,
      to: flow.target_account,
      width: Math.max(1.5, Math.min(2 + (amt / 500000) * 2, 4.5)),
      color: {
        color: 'rgba(0,198,255,0.25)',
        highlight: '#00c6ff',
        hover: '#00c6ff'
      },
      smooth: { type: 'curvedCW', roundness: 0.1 },
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      label: '¥' + (amt >= 10000 ? (amt / 10000).toFixed(1) + '万' : amt.toLocaleString()),
      font: { color: 'rgba(0,198,255,0.8)', size: 10, align: 'middle', strokeWidth: 2, strokeColor: '#0a0e1a' }
    }
  })
})

const graphLegends = [
  { label: '一级卡（受害人→嫌疑人）', color: '#f43f5e' },
  { label: '二级卡（中间层）', color: '#f97316' },
  { label: '三级卡（归集/境外）', color: '#06b6d4' }
]

const graphPhysics = {
  solver: 'forceAtlas2Based',
  forceAtlas2Based: {
    gravitationalConstant: -150,
    centralGravity: 0.005,
    springLength: 180,
    springConstant: 0.03,
    damping: 0.5
  },
  stabilization: { iterations: 40, updateInterval: 30, fit: true }
}

const graphNodeDefaults = {
  shape: 'dot',
  font: { color: '#e2e8f0', size: 11, face: 'sans-serif', strokeWidth: 3, strokeColor: '#0a0e1a' },
  borderWidth: 2,
  shadow: { enabled: true, size: 8, color: 'rgba(0,0,0,0.3)' }
}

const graphEdgeDefaults = {
  smooth: { type: 'curvedCW', roundness: 0.1 },
  arrows: { to: { enabled: true, scaleFactor: 0.6 } },
  width: 2,
  color: { color: 'rgba(0,198,255,0.25)', highlight: '#00c6ff', hover: '#00c6ff' },
  font: { color: 'rgba(0,198,255,0.8)', size: 10, align: 'middle', strokeWidth: 2, strokeColor: '#0a0e1a' }
}

const tryLoadFirstCase = () => {
  if (caseList.value.length === 0) {
    loadCases()
  }
}

watch(() => cases.value?.length, (len) => {
  if (len === 0) loadCases()
})

onMounted(() => {
  if (caseList.value.length === 0) loadCases()
})
</script>

<style scoped>
.view-section { padding: 20px; }
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.section-title { margin: 0; font-size: 20px; font-weight: 700; color: #e2e8f0; display: flex; align-items: center; gap: 8px; }
.title-icon { font-size: 22px; }
.section-desc { margin: 0; font-size: 13px; color: #94a3b8; }
.header-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.flow-container { width: 100%; }

/* 统计摘要面板 */
.flow-summary {
  background: rgba(15,23,42,0.6);
  border: 1px solid rgba(0,198,255,0.12);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 14px;
  transition: all 0.3s ease;
}
.flow-summary.screenshot-mode {
  background: rgba(10,14,26,0.9);
  border-color: rgba(0,198,255,0.2);
  margin-bottom: 10px;
}
.summary-row {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.summary-row:last-child { margin-bottom: 0; }
.summary-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 150px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  border: 1px solid rgba(0,198,255,0.04);
}
.si-icon { font-size: 20px; flex-shrink: 0; }
.si-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.si-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.si-value { font-size: 14px; color: #e2e8f0; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.si-value.accent { color: #00d4ff; font-size: 16px; }

.network-container {
  border-radius: 12px;
  overflow: hidden;
  width: 100%;
  background: rgba(15,23,42,0.6);
  border: 1px solid rgba(0,212,255,0.12);
  min-height: 540px;
  transition: all 0.3s ease;
}
.network-container.screenshot-mode {
  border-color: rgba(0,212,255,0.25);
  box-shadow: 0 0 30px rgba(0,212,255,0.06);
  min-height: 480px;
}
.flow-table-wrapper {
  margin-top: 14px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border-primary);
}

/* 案件浏览器 */
.browser-panel {
  background: rgba(15,23,42,0.5);
  border: 1px solid rgba(0,198,255,0.1);
  border-radius: 12px;
  overflow: hidden;
}
.browser-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(0,198,255,0.08);
}
.bh-left { display: flex; align-items: center; gap: 10px; }
.bh-title { margin:0; font-size:15px; font-weight:600; color:#e2e8f0; }
.bh-count { font-size:12px; color:#64748b; }
.bh-right { display:flex; gap:8px; }
.case-browser-table { }
.cbt-header {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid rgba(0,198,255,0.06);
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.cbt-row {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(0,198,255,0.04);
  transition: background 0.2s;
  cursor: pointer;
}
.cbt-row:last-child { border-bottom: none; }
.cbt-row:hover { background: rgba(0,198,255,0.04); }
.cbt-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 6px;
  font-size: 13px;
  color: #cbd5e1;
}
.col-id { width: 18%; }
.col-id code { font-size:12px; color:#00d4ff; font-family:'JetBrains Mono',monospace; }
.col-title { width: 24%; font-weight:500; }
.col-type { width: 13%; }
.col-status { width: 13%; }
.col-victim { width: 14%; }
.col-action { width: 18%; text-align: right; }

.empty-state { text-align: center; padding: 40px 20px; }
.empty-content { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.empty-icon { font-size: 48px; opacity: 0.6; }
.empty-title { margin: 0; font-size: 18px; font-weight: 600; color: #cbd5e1; }
.empty-desc { margin: 0; font-size: 13px; color: #64748b; max-width: 360px; line-height: 1.5; }

/* 切换标签 */
.bh-tabs { display: flex; gap: 0; background: rgba(0,0,0,0.25); border-radius: 8px; padding: 3px; }
.bh-tab {
  padding: 6px 14px; font-size: 13px; color: #64748b; cursor: pointer;
  border-radius: 6px; transition: all 0.2s; white-space: nowrap;
  display: flex; align-items: center; gap: 6px;
}
.bh-tab:hover { color: #94a3b8; background: rgba(0,198,255,0.06); }
.bh-tab.active { color: #e2e8f0; background: rgba(0,198,255,0.15); font-weight: 500; }
.bh-tab-count {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
  background: rgba(0,198,255,0.1); color: #00d4ff; min-width: 18px; text-align: center;
}
.bh-tab.active .bh-tab-count { background: rgba(0,198,255,0.2); }

/* 新导入标记 */
.recent-badge {
  display: inline-block; font-size: 9px; padding: 1px 5px; border-radius: 4px;
  background: rgba(239,68,68,0.2); color: #ef4444; font-weight: 700; margin-left: 4px;
  vertical-align: middle; animation: recentPulse 2s ease-in-out infinite;
}
.cbt-row-recent {
  background: rgba(0,198,255,0.03);
  border-left: 3px solid #00d4ff;
}
.cbt-row-recent:hover { background: rgba(0,198,255,0.07); }

@keyframes recentPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>