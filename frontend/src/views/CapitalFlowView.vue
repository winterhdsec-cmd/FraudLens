<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title"><span class="title-icon">💰</span>资金流向追踪</h2>
      <p class="section-desc">按层级展示涉案资金流转链路</p>
    </div>
    <div class="header-actions">
      <el-select v-model="selectedCaseId" placeholder="选择案件" size="small" style="width:260px" filterable @change="onCaseSelect" clearable>
        <el-option v-for="c in caseList" :key="c.case_id || c.id" :label="(c.case_id || c.id) + ' - ' + (c.title || c.victim_name || '未知')" :value="c.case_id || c.id" />
      </el-select>
      <el-input v-model="flowSearchCaseId" placeholder="输入案件编号" style="width:170px" size="small" clearable @clear="loadFlowData" @keyup.enter="loadFlowData" />
      <el-button type="primary" size="small" @click="loadFlowData">查询</el-button>
    </div>
  </div>

  <div class="flow-container">
    <template v-if="!capitalFlows.length && !flowSearchCaseId">
      <div class="empty-state">
        <div class="empty-content">
          <div class="empty-icon">🔍</div>
          <h3 class="empty-title">请输入案件编号</h3>
          <p class="empty-desc">输入案件编号并点击查询，系统将展示该案件的详细资金流转链路</p>
        </div>
      </div>
    </template>
    <template v-else-if="!capitalFlows.length">
      <div class="empty-state">
        <div class="empty-content">
          <div class="empty-icon">💰</div>
          <h3 class="empty-title">暂无资金流向数据</h3>
          <p class="empty-desc">该案件暂无资金流向记录，请确认案件编号是否正确</p>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="network-container">
        <div class="flow-legend">
          <div class="flow-legend-item">
            <span class="legend-color" style="background:#f43f5e"></span>
            <span>一级卡</span>
          </div>
          <div class="flow-legend-item">
            <span class="legend-color" style="background:#f97316"></span>
            <span>二级卡</span>
          </div>
          <div class="flow-legend-item">
            <span class="legend-color" style="background:#06b6d4"></span>
            <span>三级卡</span>
          </div>
          <div class="flow-legend-item" style="opacity:0.5">
            <span class="legend-arrow">→</span>
            <span>资金流向</span>
          </div>
        </div>
        <MiniNetworkGraph
          v-if="graphNodes.length > 0"
          title="资金流向图谱"
          :nodes="graphNodes"
          :edges="graphEdges"
          :legends="graphLegends"
          :physics="graphPhysics"
          :node-defaults="graphNodeDefaults"
          :edge-defaults="graphEdgeDefaults"
          style="height:480px;width:100%"
        />
        <div v-else class="empty-state" style="height:540px;display:flex;align-items:center;justify-content:center">
          <div class="empty-content">
            <div class="empty-icon">📊</div>
            <h3 class="empty-title">暂无链路图数据</h3>
            <p class="empty-desc">请先查询案件以生成资金流向链路图</p>
          </div>
        </div>
      </div>
        <el-table :data="capitalFlows" style="width:100%;margin-top:12px" stripe size="small" max-height="300">
          <el-table-column prop="source_account" label="转出账户" min-width="140" />
          <el-table-column prop="target_account" label="转入账户" min-width="140" />
          <el-table-column prop="bank_name" label="开户行" width="120" />
          <el-table-column prop="amount" label="金额" width="100">
             <template #default="{row}">¥{{ Number(row.amount || 0).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="direction" label="方向" width="70">
            <template #default="{row}"><el-tag :type="row.direction==='out' ? 'warning' : 'danger'" size="small">{{row.direction === 'out' ? '转出' : '转入'}}</el-tag></template>
          </el-table-column>
          <el-table-column prop="level" label="层级" width="60" />
          <el-table-column prop="transaction_time" label="交易时间" width="160" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{row}">
              <el-button size="small" @click="addFlowRecord(row)">追加</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import MiniNetworkGraph from '../components/MiniNetworkGraph.vue'

const state = useAppState()
const {
  capitalFlows, flowSearchCaseId, loadFlowData, addFlowRecord,
  cases
} = state

const selectedCaseId = ref('')
const caseList = computed(() => cases.value || [])

const onCaseSelect = (val) => {
  if (val) {
    flowSearchCaseId.value = val
    loadFlowData()
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
    const sz = 14 + ratio * 18
    const amt = data.totalAmount
    return {
      id: account,
      label: formatAccountName(account),
      title: `<b>${formatAccountName(account)}</b><br>层级: ${getLevelLabel(data.level)}<br>涉案金额: ¥${amt.toLocaleString()}`,
      size: Math.round(sz),
      color: getLevelColor(data.level),
      level: data.level,
      amount: data.totalAmount,
      font: { color: '#e2e8f0', size: 10, face: 'sans-serif', strokeWidth: 2, strokeColor: '#0a0e1a' },
      shape: 'dot',
      borderWidth: 2,
      shadow: { enabled: true, size: 8, color: getLevelColor(data.level).background + '55' }
    }
  })
})

const graphEdges = computed(() => {
  if (!capitalFlows.value.length) return []
  const maxLinkValue = Math.max(...capitalFlows.value.map(f => Number(f.amount || 0)), 1)
  return capitalFlows.value.map(flow => ({
    from: flow.source_account,
    to: flow.target_account,
    width: Math.max(1, Math.min(1.5 + (Number(flow.amount || 0) / maxLinkValue) * 2.5, 4)),
    color: {
      color: 'rgba(0,198,255,0.3)',
      highlight: '#00c6ff',
      hover: '#00c6ff'
    },
    smooth: { type: 'curvedCW', roundness: 0.15 },
    arrows: { to: { enabled: true, scaleFactor: 0.7 } }
  }))
})

const graphLegends = [
  { label: '一级卡', color: '#f43f5e' },
  { label: '二级卡', color: '#f97316' },
  { label: '三级卡', color: '#06b6d4' }
]

const graphPhysics = {
  solver: 'forceAtlas2Based',
  forceAtlas2Based: {
    gravitationalConstant: -200,
    centralGravity: 0.003,
    springLength: 150,
    springConstant: 0.02,
    damping: 0.4
  },
  stabilization: { iterations: 60, updateInterval: 50, fit: true }
}

const graphNodeDefaults = {
  shape: 'dot',
  font: { color: '#e2e8f0', size: 10, face: 'sans-serif', strokeWidth: 2, strokeColor: '#0a0e1a' },
  borderWidth: 2,
  shadow: { enabled: true, size: 8, color: 'rgba(0,0,0,0.3)' }
}

const graphEdgeDefaults = {
  smooth: { type: 'curvedCW', roundness: 0.15 },
  arrows: { to: { enabled: true, scaleFactor: 0.7 } },
  width: 1.5,
  color: { color: 'rgba(0,198,255,0.3)', highlight: '#00c6ff', hover: '#00c6ff' }
}

const tryLoadFirstCase = () => {
  if (caseList.value.length > 0 && !flowSearchCaseId.value) {
    const first = caseList.value[0]
    selectedCaseId.value = first.case_id || first.id
    flowSearchCaseId.value = selectedCaseId.value
    loadFlowData()
  }
}

watch(() => cases.value?.length, (len) => {
  if (len > 0) tryLoadFirstCase()
})

watch(capitalFlows, () => {})

onMounted(() => {
  tryLoadFirstCase()
})

onUnmounted(() => {})
</script>

<style scoped>
.view-section {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 22px;
}

.section-desc {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.flow-container {
  width: 100%;
}

.network-container {
  border-radius: 12px;
  overflow: hidden;
  width: 100%;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.12);
  min-height: 540px;
}

.flow-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 10px 16px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid rgba(0, 198, 255, 0.08);
}

.flow-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.legend-arrow {
  color: #64748b;
  font-size: 14px;
  font-weight: 300;
}

.header-actions .el-input {
  --el-input-border-radius: 8px;
}

.el-table-column.el-table .cell {
  text-align: right;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.6;
}

.empty-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #cbd5e1;
}

.empty-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  max-width: 360px;
  line-height: 1.5;
}
</style>