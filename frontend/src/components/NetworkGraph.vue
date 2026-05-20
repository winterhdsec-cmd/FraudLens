<template>
  <div class="network-graph">
    <div class="graph-header">
      <div class="engine-status">
        <div class="status-dot"></div>
        <span class="status-text">AI 研判引擎运行中</span>
      </div>
      <div class="graph-tabs" v-if="hasFlowData">
        <el-radio-group v-model="graphMode" size="small">
          <el-radio-button value="gang">团伙关系</el-radio-button>
          <el-radio-button value="flow">资金流向</el-radio-button>
        </el-radio-group>
      </div>
      <div class="graph-controls">
        <el-button size="small" @click="fitView">适应屏幕</el-button>
        <el-button size="small" @click="togglePhysics">{{ physicsEnabled ? '暂停布局' : '恢复布局' }}</el-button>
        <el-button size="small" type="primary" @click="exportGraph">导出</el-button>
        <el-button size="small" @click="clusterAll" :disabled="!props.gangs.length">聚合</el-button>
        <el-button size="small" @click="expandAll" :disabled="!props.gangs.length">展开</el-button>
      </div>
    </div>
    <div class="graph-canvas" ref="containerRef"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { ElMessage } from 'element-plus'

const props = defineProps({
  gangs: { type: Array, default: () => [] },
  selectedGang: { type: Object, default: null },
  flowData: { type: Object, default: null }
})

const emit = defineEmits(['select'])
const containerRef = ref(null)
const graphMode = ref('gang')
const physicsEnabled = ref(true)

let network = null
let nodes = new DataSet()
let edges = new DataSet()

const hasFlowData = computed(() => props.flowData && props.flowData.nodes && props.flowData.nodes.length > 0)

watch(() => props.gangs, () => { nextTick(buildGangGraph) }, { deep: true })
watch(() => props.flowData, () => { nextTick(buildFlowGraph) }, { deep: true })
watch(graphMode, (mode) => { mode === 'flow' ? buildFlowGraph() : buildGangGraph() })

const NODE_COLORS = {
  S: { background: '#ff3860', border: '#ff6b8a', highlight: { background: '#ff1744', border: '#ff5252' } },
  A: { background: '#ffd700', border: '#ffe047', highlight: { background: '#ffc107', border: '#ffd54f' } },
  B: { background: '#ff9800', border: '#ffb74d', highlight: { background: '#f57c00', border: '#ff9800' } },
  C: { background: '#00c6ff', border: '#00a0d4', highlight: { background: '#0091ea', border: '#40c4ff' } },
  money: { background: '#f59e0b', border: '#fbbf24', highlight: { background: '#d97706', border: '#f59e0b' } }
}

function buildGangGraph() {
  if (!containerRef.value || !props.gangs.length) return

  nodes.clear(); edges.clear()

  const displayGangs = props.gangs.slice(0, 20)

  displayGangs.forEach((gang, idx) => {
    const tl = gang.riskLevel || gang.threat_level || 'C'
    const nodeId = 'gang_' + (gang.gang_id || idx)
    const colors = NODE_COLORS[tl] || NODE_COLORS.C
    const shortName = (gang.gang_name || '团伙' + (idx + 1)).length > 8
      ? (gang.gang_name || '团伙' + (idx + 1)).slice(0, 7) + '…'
      : (gang.gang_name || '团伙' + (idx + 1))

    nodes.add({
      id: nodeId,
      label: shortName,
      title: '<b>' + (gang.gang_name || '团伙') + '</b><br>威胁等级: ' + tl + '<br>案件数: ' + (gang.total_cases || 0) + '<br>金额: ' + (gang.total_amount_involved || '-'),
      shape: 'dot',
      size: tl === 'S' ? 24 : tl === 'A' ? 20 : 18,
      color: colors,
      font: { color: '#e2e8f0', size: 9, face: 'sans-serif', strokeWidth: 2, strokeColor: '#0a0e1a' },
      borderWidth: 2,
      shadow: { enabled: true, size: 6, color: colors.background + '44' },
      group: 'gang',
      gangData: gang
    })

    const cases = gang.related_cases || []
    cases.slice(0, 3).forEach((c, ci) => {
      const caseId = 'case_' + nodeId + '_' + ci
      nodes.add({
        id: caseId,
        label: '',
        title: '<b>案件 ' + c.case_id + '</b><br>受害人: ' + (c.victim || '未知') + '<br>金额: ' + (c.amount || '-'),
        shape: 'dot',
        size: 8,
        color: NODE_COLORS.C,
        font: { color: '#94a3b8', size: 8 },
        group: 'case'
      })
      edges.add({
        id: 'e_' + nodeId + '_' + caseId,
        from: nodeId,
        to: caseId,
        color: { color: 'rgba(0,198,255,0.3)', highlight: '#00c6ff' },
        width: 1,
        smooth: { type: 'curvedCW', roundness: 0.1 }
      })
    })
  })

  const options = {
    physics: physicsEnabled.value ? {
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -200, centralGravity: 0.005, springLength: 150, springConstant: 0.03, damping: 0.5 },
      stabilization: { iterations: 100, updateInterval: 50 }
    } : false,
    edges: { smooth: { type: 'continuous' } },
    interaction: { hover: true, tooltipDelay: 200, dragNodes: true, dragView: true, zoomView: true, navigationButtons: true, selectable: true },
    groups: {
      gang: { shape: 'dot' },
      case: { shape: 'dot' }
    },
    configure: { filter: function (option, path) { return false }, showButton: false }
  }

  if (network) network.destroy()
  network = new Network(containerRef.value, { nodes, edges }, options)

  let fitAttempts = 0
  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: true, minZoomLevel: 0.3 })
  })
  network.on('stabilized', () => {
    if (fitAttempts < 1) {
      network.fit({ animation: true, minZoomLevel: 0.3 })
      fitAttempts++
    }
  })
  network.on('resize', () => { network.fit({ minZoomLevel: 0.3 }) })

  network.on('click', (params) => {
    if (params.nodes.length) {
      const node = nodes.get(params.nodes[0])
      if (node && node.group === 'gang' && node.gangData) {
        emit('select', node.gangData)
      }
    }
  })

  network.on('zoom', () => {
    const scale = network.getScale()
    if (scale < 0.4) {
      network.clustering.clusterByConnection(2)
    } else {
      network.clustering.openAllClusters()
    }
  })
}

function clusterAll() {
  if (!network) return
  network.clustering.clusterByConnection(2)
  setTimeout(() => network.fit({ animation: true }), 100)
}

function expandAll() {
  if (!network) return
  network.clustering.openAllClusters()
  setTimeout(() => network.fit({ animation: true }), 100)
}

function buildFlowGraph() {
  if (!containerRef.value || !props.flowData) return
  nodes.clear(); edges.clear()

  const flowNodes = props.flowData.nodes || []
  const flowEdges = props.flowData.edges || []

  flowNodes.forEach(n => {
    nodes.add({
      id: n.id,
      label: n.label || n.name,
      title: n.title || n.label,
      shape: 'dot',
      size: n.size || 20,
      color: n.type === 'source'
        ? { background: '#f59e0b', border: '#fbbf24', highlight: { background: '#d97706', border: '#f59e0b' } }
        : { background: '#ef4444', border: '#f87171', highlight: { background: '#dc2626', border: '#ef4444' } },
      font: { color: '#e2e8f0', size: 12 }
    })
  })

  flowEdges.forEach(e => {
    edges.add({
      id: e.id,
      from: e.from || e.source,
      to: e.to || e.target,
      label: e.label || (e.amount ? '¥' + e.amount : ''),
      color: { color: 'rgba(245,158,11,0.6)', highlight: '#f59e0b' },
      width: 2 + Math.min(Math.floor(e.amount || 0) / 50000, 5),
      arrows: { to: { enabled: true, scaleFactor: 0.8 } },
      font: { color: '#f59e0b', size: 10, align: 'middle' },
      smooth: { type: 'curvedCW', roundness: 0.2 }
    })
  })

  const options = {
    physics: {
      solver: 'barnesHut',
      barnesHut: { gravitationalConstant: -300, centralGravity: 0.008, springLength: 120 },
      stabilization: { iterations: 60, updateInterval: 50 }
    },
    edges: { smooth: true },
    interaction: { hover: true, tooltipDelay: 200, dragNodes: true, navigationButtons: true }
  }

  if (network) network.destroy()
  network = new Network(containerRef.value, { nodes, edges }, options)
  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: true })
  })
}

function fitView() { if (network) network.fit({ animation: true }) }
function togglePhysics() {
  physicsEnabled.value = !physicsEnabled.value
  if (network) network.setOptions({ physics: physicsEnabled.value })
  if (physicsEnabled.value) setTimeout(() => network.fit({ animation: true }), 500)
}
function exportGraph() {
  if (containerRef.value) {
    const canvas = containerRef.value.querySelector('canvas')
    if (canvas) {
      const link = document.createElement('a')
      link.download = 'network-' + Date.now() + '.png'
      link.href = canvas.toDataURL()
      link.click()
    }
  }
}

onMounted(() => { nextTick(() => { buildGangGraph() }) })
onUnmounted(() => { if (network) network.destroy() })
</script>

<style scoped>
.network-graph {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  background: rgba(10,14,26,0.5);
  border-radius: 12px;
}
.graph-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px;
  background: rgba(15,23,42,0.8);
  border-bottom: 1px solid rgba(0,198,255,0.2);
  gap: 8px; flex-wrap: wrap;
}
.engine-status { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #00c6ff;
  box-shadow: 0 0 10px #00c6ff;
  animation: pulse 2s ease-in-out infinite;
}
.status-text { font-size: 12px; color: #94a3b8; font-weight: 500; }
.graph-controls { display: flex; gap: 6px; flex-wrap: wrap; }
.graph-canvas { flex: 1; height: 800px; min-height: 800px; background: rgba(10,14,26,0.8); }
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.9); }
}
</style>