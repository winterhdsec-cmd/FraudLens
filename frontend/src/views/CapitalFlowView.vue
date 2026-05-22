<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title"><span class="title-icon">💰</span>资金流向追踪</h2>
      <p class="section-desc">按层级展示涉案资金流转链路</p>
    </div>
    <div class="header-actions">
      <el-input v-model="flowSearchCaseId" placeholder="按案件编号搜索" style="width:200px" size="small" clearable @clear="loadFlowData" @keyup.enter="loadFlowData" />
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
            <span class="legend-color" style="background:#ef4444"></span>
            <span>一级卡</span>
          </div>
          <div class="flow-legend-item">
            <span class="legend-color" style="background:#f59e0b"></span>
            <span>二级卡</span>
          </div>
          <div class="flow-legend-item">
            <span class="legend-color" style="background:#00d4ff"></span>
            <span>三级卡</span>
          </div>
          <div class="flow-legend-item">
            <span class="legend-color" style="background:rgba(0,212,255,0.3);width:14px;height:4px;border-radius:2px"></span>
            <span>资金流向</span>
          </div>
        </div>
        <div v-if="echartNodes.length === 0" class="empty-state" style="height:100%;display:flex;align-items:center;justify-content:center">
          <div class="empty-content">
            <div class="empty-icon">📊</div>
            <h3 class="empty-title">暂无链路图数据</h3>
            <p class="empty-desc">请先查询案件以生成资金流向链路图</p>
          </div>
        </div>
        <div ref="flowChartRef" class="flow-echart-container"></div>
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
import * as echarts from 'echarts'
import { useAppState } from '../composables/useAppState.js'

const state = useAppState()
const {
  capitalFlows, flowSearchCaseId, loadFlowData, addFlowRecord
} = state

const flowChartRef = ref(null)
let flowChartInstance = null

const echartNodes = computed(() => {
  if (!capitalFlows.value.length) return []
  const nodeMap = new Map()
  const addNode = (account, level, amount) => {
    if (!nodeMap.has(account)) {
      nodeMap.set(account, {
        name: account,
        level: level || 1,
        totalAmount: 0
      })
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
  return Array.from(nodeMap.values())
})

const echartLinks = computed(() => {
  if (!capitalFlows.value.length) return []
  return capitalFlows.value.map(flow => ({
    source: flow.source_account,
    target: flow.target_account,
    value: Number(flow.amount || 0)
  }))
})

const getLevelShape = (level) => {
  if (level === 1) return 'circle'
  if (level === 2) return 'roundRect'
  return 'diamond'
}

const getLevelColor = (level) => {
  if (level === 1) return '#ef4444'
  if (level === 2) return '#f59e0b'
  return '#00d4ff'
}

const getLevelLabel = (level) => {
  if (level === 1) return '一级卡'
  if (level === 2) return '二级卡'
  return '三级卡'
}

const getNodeSize = (amount, maxAmount) => {
  if (maxAmount === 0) return 40
  const ratio = amount / maxAmount
  return 36 + ratio * 48
}

const formatAccountName = (name) => {
  if (!name || name.length <= 8) return name || ''
  return name.slice(0, 4) + '***' + name.slice(-4)
}

const initFlowChart = () => {
  if (!flowChartRef.value) return
  const nodes = echartNodes.value
  if (nodes.length === 0) return

  const maxAmount = Math.max(...nodes.map(n => n.totalAmount), 1)

  if (flowChartInstance) {
    flowChartInstance.dispose()
    flowChartInstance = null
  }

  flowChartInstance = echarts.init(flowChartRef.value)

  const levelGroups = {}
  nodes.forEach(n => {
    if (!levelGroups[n.level]) levelGroups[n.level] = []
    levelGroups[n.level].push(n)
  })

  const sortedLevels = Object.keys(levelGroups).sort((a, b) => a - b)
  const levelCount = sortedLevels.length

  const graphNodes = []
  sortedLevels.forEach((level, li) => {
    const group = levelGroups[level]
    const x = 5 + (li / Math.max(levelCount - 1, 1)) * 90
    group.forEach((node, ni) => {
      const total = group.length
      const y = total > 1 ? 5 + (ni / (total - 1)) * 90 : 50
      const sz = getNodeSize(node.totalAmount, maxAmount)
      const amt = node.totalAmount
      const amtStr = amt >= 10000 ? (amt / 10000).toFixed(1) + '万' : amt.toFixed(0)
      graphNodes.push({
        name: node.name,
        x,
        y,
        symbol: getLevelShape(node.level),
        symbolSize: sz,
        itemStyle: {
          color: getLevelColor(node.level),
          borderColor: 'rgba(255,255,255,0.3)',
          borderWidth: 2,
          shadowBlur: 20,
          shadowColor: getLevelColor(node.level) + '99'
        },
        label: {
          show: true,
          color: '#f1f5f9',
          fontSize: 12,
          fontWeight: 'bold',
          textShadowBlur: 6,
          textShadowColor: 'rgba(0,0,0,0.9)',
          lineHeight: 18,
          formatter: () => formatAccountName(node.name) + '\n¥' + amtStr
        },
        category: node.level - 1,
        level: node.level,
        amount: node.totalAmount
      })
    })
  })

  const maxLinkValue = Math.max(...echartLinks.value.map(l => l.value), 1)

  const graphLinks = echartLinks.value.map(link => ({
    source: link.source,
    target: link.target,
    value: link.value,
    lineStyle: {
      color: '#00d4ff',
      width: Math.max(2, Math.min(4 + (link.value / maxLinkValue) * 4, 8)),
      curveness: 0.2,
      opacity: 0.8
    },
    label: {
      show: false,
      formatter: () => '¥' + Number(link.value || 0).toLocaleString(),
      fontSize: 10,
      color: '#94a3b8',
      backgroundColor: 'rgba(10,14,26,0.8)',
      padding: [2, 6],
      borderRadius: 4
    }
  }))

  const levelZoneColors = {
    1: { bg: 'rgba(239,68,68,0.04)', border: 'rgba(239,68,68,0.15)' },
    2: { bg: 'rgba(245,158,11,0.04)', border: 'rgba(245,158,11,0.15)' },
    3: { bg: 'rgba(0,212,255,0.04)', border: 'rgba(0,212,255,0.15)' }
  }

  const graphicElements = sortedLevels.map((level, li) => ({
    type: 'rect',
    left: (5 + li * 30) + '%',
    top: '2%',
    width: '28%',
    bottom: '2%',
    style: {
      fill: levelZoneColors[level]?.bg || 'rgba(255,255,255,0.02)',
      stroke: levelZoneColors[level]?.border || 'rgba(255,255,255,0.05)',
      lineWidth: 1
    },
    shape: { r: 6 },
    z: 0,
    silent: true
  }))

  flowChartInstance.setOption({
    backgroundColor: 'transparent',
    graphic: graphicElements,
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'edge') {
          return `<div style="color:#e2e8f0">
            <span style="color:#f87171">${formatAccountName(params.data.source)}</span>
            <span style="color:#64748b;margin:0 4px">→</span>
            <span style="color:#60a5fa">${formatAccountName(params.data.target)}</span><br/>
            金额: <strong style="color:#fbbf24">¥${Number(params.data.value || 0).toLocaleString()}</strong>
          </div>`
        }
        const d = params.data
        return `<div style="color:#e2e8f0">
          <strong style="color:#ffffff">${d.name}</strong><br/>
          层级: ${getLevelLabel(d.level)}<br/>
          涉案金额: <strong style="color:#fbbf24">¥${Number(d.amount || 0).toLocaleString()}</strong>
        </div>`
      },
      backgroundColor: 'rgba(10, 14, 26, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.4)',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0' }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      force: {
        repulsion: 6000,
        edgeLength: [250, 500],
        gravity: 0.008,
        friction: 0.1,
        layoutAnimation: true
      },
      categories: [
        { name: '一级卡', itemStyle: { color: '#ef4444' } },
        { name: '二级卡', itemStyle: { color: '#f59e0b' } },
        { name: '三级卡', itemStyle: { color: '#00d4ff' } }
      ],
      data: graphNodes,
      links: graphLinks,
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 30],
      edgeLabel: { show: true },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3, opacity: 1, color: '#00d4ff' },
        itemStyle: { borderWidth: 3, borderColor: '#fff', shadowBlur: 24, shadowColor: 'rgba(255,255,255,0.35)' },
        label: { show: true, fontWeight: 'bold', fontSize: 13 }
      },
      lineStyle: {
        color: '#00d4ff',
        opacity: 0.8,
        curveness: 0.2
      }
    }]
  })

  flowChartInstance.resize()
}

const handleResize = () => {
  if (flowChartInstance) {
    flowChartInstance.resize()
  }
}

watch(capitalFlows, () => {
  nextTick(() => initFlowChart())
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (flowChartInstance) {
    flowChartInstance.dispose()
    flowChartInstance = null
  }
})
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

.flow-echart-container {
  width: 100%;
  height: 540px;
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