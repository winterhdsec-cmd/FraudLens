<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title"><span class="title-icon"><el-icon><Money /></el-icon></span>资金流向追踪</h2>
      <p class="section-desc">按层级展示涉案资金流转链路，支持截图导出</p>
    </div>
    <div class="header-actions">
      <el-select v-model="selectedCaseId" placeholder="选择案件" size="small" style="width:260px" filterable @change="onCaseSelect" clearable>
        <el-option v-for="c in caseList" :key="c.case_id || c.id" :label="(c.case_id || c.id) + ' - ' + (c.title || c.victim_name || '未知')" :value="c.case_id || c.id" />
      </el-select>
      <el-input v-model="flowSearchCaseId" placeholder="输入案件编号" style="width:170px" size="small" clearable @clear="loadFlowData" @keyup.enter="loadFlowData" />
      <el-button type="primary" size="small" @click="loadFlowData">查询</el-button>
      <el-button v-if="capitalFlows.length" :type="screenshotMode ? 'success' : 'default'" size="small" @click="toggleScreenshotMode">
        <!-- 旧写法把 <el-icon> 放进了 {{ }} 插值，组件标签被当纯文本渲染出来 -->
        <el-icon><Camera /></el-icon> {{ screenshotMode ? '退出截图' : '截图模式' }}
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
                <el-icon><Files /></el-icon> 全部案件
                <span class="bh-tab-count">{{ (cases.value || []).length }}</span>
              </span>
            </div>
          </div>
          <div class="bh-right">
            <el-button size="small" @click="loadCases" :loading="caseLoading"><el-icon><Refresh /></el-icon> 刷新列表</el-button>
          </div>
        </div>
        <div v-if="caseLoading" class="empty-state" style="padding:60px 20px">
          <div class="empty-content"><div class="empty-icon" style="animation:pulse 1.5s infinite"><el-icon><Search /></el-icon></div><h3 class="empty-title">加载中...</h3><p class="empty-desc">正在获取案件数据</p></div>
        </div>
        <div v-else-if="!caseList.length" class="empty-state" style="padding:60px 20px">
          <div class="empty-content"><div class="empty-icon"><el-icon><Folder /></el-icon></div><h3 class="empty-title">暂无案件数据</h3><p class="empty-desc">请先通过文本录入或文件上传导入案件</p></div>
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
          <div v-for="c in pagedCaseList" :key="c.case_id || c.id" class="cbt-row" :class="{ 'cbt-row-recent': recentIdSet.has(c.case_id || c.id) }" @dblclick="browseToCase(c.case_id || c.id)">
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
              <el-button size="small" type="primary" plain @click="browseToCase(c.case_id || c.id)"><el-icon><Money /></el-icon> 查看资金流向</el-button>
            </span>
          </div>
          <div class="cbt-pagination" v-if="caseList.length > pageSize">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[20, 50, 100]"
              :total="caseList.length"
              layout="total, sizes, prev, pager, next, jumper"
              background
            />
          </div>
        </div>
      </div>
    </template>
    <!-- 已选择案件但无资金流向数据 -->
    <template v-else-if="!capitalFlows.length">
      <div class="empty-state">
        <div class="empty-content">
          <div class="empty-icon"><el-icon><Money /></el-icon></div>
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
            <span class="si-icon"><el-icon><Files /></el-icon></span>
            <div class="si-body">
              <span class="si-label">案件编号</span>
              <span class="si-value">{{ flowSearchCaseId || '—' }}</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon"><el-icon><Document /></el-icon></span>
            <div class="si-body">
              <span class="si-label">案件名称</span>
              <span class="si-value">{{ currentCaseTitle }}</span>
            </div>
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-item">
            <span class="si-icon"><el-icon><OfficeBuilding /></el-icon></span>
            <div class="si-body">
              <span class="si-label">涉案账户</span>
              <span class="si-value accent">{{ graphNodes.length }}个</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon"><el-icon><DataAnalysis /></el-icon></span>
            <div class="si-body">
              <span class="si-label">资金层级</span>
              <span class="si-value accent">{{ maxFlowLevel }}层</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon"><el-icon><Money /></el-icon></span>
            <div class="si-body">
              <span class="si-label">总涉案金额</span>
              <span class="si-value accent">{{ formatTotalAmount }}</span>
            </div>
          </div>
          <div class="summary-item">
            <span class="si-icon"><el-icon><Refresh /></el-icon></span>
            <div class="si-body">
              <span class="si-label">交易笔数</span>
              <span class="si-value accent">{{ capitalFlows.length }}笔</span>
            </div>
          </div>
        </div>
      </div>

      <div class="network-container sankey-container" :class="{ 'screenshot-mode': screenshotMode }">
        <div class="sankey-header">
          <div class="sh-left">
            <span class="status-dot"></span>
            <span class="sh-title">资金流向图谱</span>
            <span class="sh-sub">受害人 → 一级卡 → 二级卡 → 归集/境外，流宽正比于转账金额</span>
          </div>
          <el-button size="small" @click="exportSankey">导出图片</el-button>
        </div>
        <div v-show="sankeyNodes.length" ref="sankeyRef" class="sankey-canvas"></div>
        <div v-if="!sankeyNodes.length" class="empty-state" style="height:420px;display:flex;align-items:center;justify-content:center">
          <div class="empty-content">
            <div class="empty-icon"><el-icon><DataAnalysis /></el-icon></div>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import { getEcharts } from '../composables/useEcharts.js'

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

// 案件浏览器分页：全部案件动辄数百条，全量渲染会堆到数千 DOM 节点
const currentPage = ref(1)
const pageSize = ref(20)
const pagedCaseList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return caseList.value.slice(start, start + pageSize.value)
})
// 切换「最近导入 / 全部案件」或刷新列表后回到第一页，避免停在越界的空白页
watch(() => caseList.value.length, () => { currentPage.value = 1 })
watch(pageSize, () => { currentPage.value = 1 })

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
    const sz = 25 + ratio * 35  // 增大节点尺寸范围
    const amt = data.totalAmount
    const colors = getLevelColor(data.level)
    return {
      id: account,
      label: formatAccountName(account),
      title: `<b>${formatAccountName(account)}</b><br>层级: ${getLevelLabel(data.level)}<br>涉案金额: ¥${amt.toLocaleString()}`,
      size: Math.round(sz),
      color: colors,
      level: data.level,
      amount: data.totalAmount,
      font: { color: '#ffffff', size: 12, face: 'Arial', strokeWidth: 3, strokeColor: '#000000', bold: true },
      shape: 'dot',
      borderWidth: 3,
      shadow: { enabled: true, size: 15, color: colors.background + '88', x: 0, y: 0 }
    }
  })
})

// ===== 桑基图（资金流向可视化，替换原 vis-network 力导向图）=====
// 力导向布局无法体现"层级"语义（节点随机漂浮），资金链路本质是从受害人
// 逐级流向归集卡的分层 DAG，桑基图是这类数据的标准画法。
const sankeyRef = ref(null)
let sankeyChart = null

const LEVEL_NAMES = ['', '① 一级卡', '② 二级卡', '③ 归集/境外']

// 桑基要求节点名全局唯一：同一账号在不同层级出现时加层级前缀
const sankeyData = computed(() => {
  if (!capitalFlows.value.length) return { nodes: [], links: [] }
  const nodeSet = new Map()   // 显示名 -> depth
  const linkMap = new Map()   // src|tgt -> 金额累计
  const depthOf = (lvl) => Math.min(Math.max((lvl || 1), 1), 4)
  capitalFlows.value.forEach(f => {
    const srcLvl = f.level || f.source_level || 1
    const tgtLvl = f.level ? f.level + 1 : (f.target_level || srcLvl + 1)
    const srcIsVictim = /^受害方/.test(f.source_account || '')
    const srcName = srcIsVictim ? f.source_account : `L${depthOf(srcLvl)} ${formatAccountName(f.source_account)}`
    const tgtName = `L${depthOf(tgtLvl)} ${formatAccountName(f.target_account)}`
    nodeSet.set(srcName, srcIsVictim ? 0 : depthOf(srcLvl) - 1)
    nodeSet.set(tgtName, depthOf(tgtLvl) - 1)
    const key = srcName + '|' + tgtName
    linkMap.set(key, (linkMap.get(key) || 0) + Number(f.amount || 0))
  })
  const nodes = Array.from(nodeSet.entries()).map(([name, depth]) => {
    const victim = name.startsWith('受害方')
    const lvl = victim ? 0 : parseInt(name.slice(1), 10)
    return {
      name,
      depth,
      itemStyle: { color: victim ? '#22d3ee' : (LEVEL_COLORS[lvl] || '#06b6d4'), borderColor: 'transparent' }
    }
  })
  const links = Array.from(linkMap.entries()).map(([key, value]) => {
    const [source, target] = key.split('|')
    return { source, target, value: Math.max(value, 1) }
  })
  return { nodes, links }
})
const sankeyNodes = computed(() => sankeyData.value.nodes)

const LEVEL_COLORS = ['#22d3ee', '#f43f5e', '#f97316', '#06b6d4', '#8b5cf6']

async function renderSankey() {
  if (!sankeyRef.value || !sankeyNodes.value.length) return
  const echarts = await getEcharts()
  if (!sankeyChart || sankeyChart.isDisposed()) {
    sankeyChart = echarts.init(sankeyRef.value)
  }
  sankeyChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(10,14,26,0.92)',
      borderColor: 'rgba(0,198,255,0.35)',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter: (p) => {
        if (p.dataType === 'edge') {
          return `${p.data.source.replace(/^L\d /, '')} → ${p.data.target.replace(/^L\d /, '')}<br/>转账金额：<b style="color:#f87171">¥${Number(p.data.value).toLocaleString()}</b>`
        }
        const name = String(p.name).replace(/^L\d /, '')
        return `账户：<b>${name}</b>`
      }
    },
    series: [{
      type: 'sankey',
      left: 24, right: 170, top: 28, bottom: 20,
      nodeWidth: 16,
      nodeGap: 14,
      nodeAlign: 'justify',
      layoutIterations: 64,
      emphasis: { focus: 'adjacency' },
      data: sankeyData.value.nodes,
      links: sankeyData.value.links,
      label: {
        color: '#cbd5e1',
        fontSize: 11,
        fontFamily: 'Consolas, Menlo, monospace',
        formatter: (p) => String(p.name).replace(/^L\d /, '')
      },
      lineStyle: { color: 'gradient', curveness: 0.55, opacity: 0.35 },
      itemStyle: { borderWidth: 0, borderRadius: 3 },
      animationDuration: 800,
      animationDurationUpdate: 500
    }]
  }, true)
}

function exportSankey() {
  if (!sankeyChart) return
  const url = sankeyChart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#0a0e1a' })
  const a = document.createElement('a')
  a.href = url
  a.download = `资金流向_${flowSearchCaseId.value || Date.now()}.png`
  a.click()
}

// 数据变化后重绘（等 DOM 更新，容器可见才能拿到宽高）
watch(sankeyNodes, async (n) => {
  if (!n.length) {
    sankeyChart?.dispose()
    sankeyChart = null
    return
  }
  await nextTick()
  renderSankey()
})

function onSankeyResize() { sankeyChart?.resize() }

onMounted(() => {
  if (caseList.value.length === 0) loadCases()
  window.addEventListener('resize', onSankeyResize)
  // 从别的页面返回时 capitalFlows 已有数据，watch 不会触发，需手动初绘
  if (sankeyNodes.value.length) nextTick(renderSankey)
})
onUnmounted(() => {
  window.removeEventListener('resize', onSankeyResize)
  sankeyChart?.dispose()
  sankeyChart = null
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
/* 桑基图容器 */
.sankey-container { min-height: auto; }
.sankey-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(15,23,42,0.8);
  border-bottom: 1px solid rgba(0,198,255,0.15);
  gap: 8px;
}
.sh-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sh-left .status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #00c6ff; box-shadow: 0 0 8px #00c6ff;
  animation: miniPulse 2s ease-in-out infinite; flex-shrink: 0;
}
@keyframes miniPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
.sh-title { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.sh-sub { font-size: 11px; color: #64748b; }
.sankey-canvas { width: 100%; height: 460px; }
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

.cbt-pagination {
  display: flex;
  justify-content: center;
  padding: 14px 20px 4px;
}
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