<template>
  <div class="network-graph">
    <div class="graph-header">
      <div class="engine-status">
        <div class="status-dot"></div>
        <span class="status-text">AI 研判引擎运行中</span>
      </div>
      <div class="search-box">
        <el-input v-model="searchKeyword" placeholder="搜索案件/团伙名称..." size="small" clearable style="width:220px" @input="onSearch">
          <template #prefix><span>🔍</span></template>
        </el-input>
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
    <div class="graph-legend" v-if="graphMode === 'gang'">
      <div class="legend-item"><span class="dot s"></span>S级团伙</div>
      <div class="legend-item"><span class="dot a"></span>A级团伙</div>
      <div class="legend-item"><span class="dot b"></span>B级团伙</div>
      <div class="legend-item"><span class="dot c"></span>C级团伙</div>
      <div class="legend-item"><span class="dot case"></span>案件</div>
      <div class="legend-item"><span class="dot money"></span>资金流向</div>
    </div>
    <div class="graph-legend" v-if="graphMode === 'flow'">
      <div class="legend-item"><span class="dot money"></span>转出账户</div>
      <div class="legend-item"><span class="dot target"></span>转入账户</div>
      <div class="legend-item"><span class="dot flow"></span>资金流向</div>
    </div>
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
  flowData: { type: Object, default: null },
  searchKeyword: { type: String, default: '' },
  cases: { type: Array, default: () => [] }
})

const emit = defineEmits(['select', 'update:searchKeyword'])
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
watch(() => props.searchKeyword, () => { highlightSearch() })

const NODE_COLORS = {
  S: { background: '#ff3860', border: '#ff6b8a', highlight: { background: '#ff1744', border: '#ff5252' } },
  A: { background: '#ffd700', border: '#ffe047', highlight: { background: '#ffc107', border: '#ffd54f' } },
  B: { background: '#ff9800', border: '#ffb74d', highlight: { background: '#f57c00', border: '#ff9800' } },
  C: { background: '#00c6ff', border: '#00a0d4', highlight: { background: '#0091ea', border: '#40c4ff' } },
  money: { background: '#f59e0b', border: '#fbbf24', highlight: { background: '#d97706', border: '#f59e0b' } }
}

function buildGangGraph() {
  if (!containerRef.value) return
  nodes.clear(); edges.clear()

  const gangCaseIds = new Set()
  const caseGangMap = {}

  props.gangs.forEach((gang, idx) => {
    const tl = gang.riskLevel || gang.threat_level || 'C'
    const nodeId = 'gang_' + (gang.gang_id || idx)
    const colors = NODE_COLORS[tl] || NODE_COLORS.C
    const num = gang.number || (idx + 1)
    const shortName = num + ':' + (gang.gang_name || '团伙' + (idx + 1)).slice(0, 8)

    nodes.add({
      id: nodeId,
      label: shortName,
      title: '<b>' + (gang.gang_name || '团伙') + '</b><br>编号: ' + num + '<br>威胁等级: ' + tl + '<br>案件数: ' + (gang.total_cases || 0) + '<br>金额: ' + (gang.total_amount_involved || '-'),
      shape: 'dot',
      size: tl === 'S' ? 32 : tl === 'A' ? 26 : 22,
      color: colors,
      font: { color: '#e2e8f0', size: 10, face: 'sans-serif', strokeWidth: 2, strokeColor: '#0a0e1a' },
      borderWidth: 2,
      shadow: { enabled: true, size: 8, color: colors.background + '55' },
      group: 'gang',
      gangData: gang,
      searchText: (gang.gang_name || '') + ' ' + num
    })

    const cases = gang.related_cases || []
    cases.forEach((c) => {
      const cid = c.case_id || ''
      if (cid) {
        gangCaseIds.add(cid)
        if (!caseGangMap[cid]) caseGangMap[cid] = []
        caseGangMap[cid].push(nodeId)
      }
    })
  })

  const addCaseNode = (c, caseId) => {
    const cNum = c.number || ''
    const nodeLabel = cNum ? '案' + cNum : (caseId || '').slice(-6)
    nodes.add({
      id: caseId,
      label: nodeLabel,
      title: '<b>案件 ' + (caseId || '') + '</b><br>编号: ' + cNum + '<br>受害人: ' + (c.victim || c.victim_name || '未知') + '<br>类型: ' + (c.scam_type || c.type || '-') + '<br>金额: ' + (c.amount || '-'),
      shape: 'dot',
      size: 14,
      color: { background: 'rgba(0,198,255,0.3)', border: 'rgba(0,198,255,0.7)', highlight: { background: 'rgba(0,198,255,0.5)', border: '#00c6ff' } },
      font: { color: '#94a3b8', size: 9, face: 'sans-serif', strokeWidth: 1, strokeColor: '#0a0e1a' },
      group: 'case',
      searchText: (caseId || '') + ' ' + (c.victim || c.victim_name || '') + ' ' + cNum + ' ' + (c.scam_type || c.type || '')
    })
  }

  props.gangs.forEach((gang, idx) => {
    const nodeId = 'gang_' + (gang.gang_id || idx)
    const cases = gang.related_cases || []
    cases.forEach((c, ci) => {
      const caseId = 'case_' + (c.case_id || (nodeId + '_' + ci))
      const exists = nodes.get(caseId)
      if (!exists) {
        addCaseNode(c, caseId)
      }
      const edgeId = 'e_' + nodeId + '_' + caseId
      if (!edges.get(edgeId)) {
        edges.add({
          id: edgeId, from: nodeId, to: caseId,
          label: c.amount || (c.amount_value ? '¥' + c.amount_value : ''),
          color: { color: 'rgba(0,198,255,0.4)', highlight: '#00c6ff' },
          width: 1.5,
          font: { color: 'rgba(0,198,255,0.7)', size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#0a0e1a' },
          smooth: { type: 'curvedCW', roundness: 0.15 }
        })
      }
    })
  })

  props.cases.forEach((c) => {
    const caseId = 'case_' + (c.case_id || '')
    const exists = nodes.get(caseId)
    if (!exists) {
      addCaseNode(c, caseId)
    }
  })

  const gangNodes = props.gangs.map((g, idx) => 'gang_' + (g.gang_id || idx))
  for (let i = 0; i < gangNodes.length; i++) {
    for (let j = i + 1; j < gangNodes.length; j++) {
      const g1 = props.gangs[i]; const g2 = props.gangs[j]
      const c1 = (g1.related_cases || []).map(c => c.case_id).filter(Boolean)
      const c2 = (g2.related_cases || []).map(c => c.case_id).filter(Boolean)
      const shared = c1.filter(c => c2.includes(c))
      if (shared.length > 0) {
        const edgeId = 'cross_' + i + '_' + j
        if (!edges.get(edgeId)) {
          edges.add({
            id: edgeId, from: gangNodes[i], to: gangNodes[j],
            label: shared.length + '案关联',
            color: { color: 'rgba(245,158,11,0.3)', highlight: '#f59e0b' },
            width: 1 + shared.length * 0.5,
            font: { color: 'rgba(245,158,11,0.6)', size: 8, align: 'middle', strokeWidth: 2, strokeColor: '#0a0e1a' },
            dashes: true, smooth: { type: 'curvedCW', roundness: 0.2 }
          })
        }
      }
    }
  }

  const options = {
    physics: physicsEnabled.value ? {
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -200, centralGravity: 0.003, springLength: 150, springConstant: 0.02, damping: 0.4 },
      stabilization: { iterations: 60, updateInterval: 50, fit: true }
    } : false,
    edges: { smooth: { type: 'continuous' } },
    interaction: { hover: true, tooltipDelay: 200, dragNodes: true, dragView: true, zoomView: true, navigationButtons: true, selectable: true, keyboard: true },
    groups: { gang: { shape: 'dot' }, case: { shape: 'dot' } },
    configure: { filter: () => false, showButton: false }
  }

  if (network) network.destroy()
  network = new Network(containerRef.value, { nodes, edges }, options)

  let fitCount = 0
  network.once('stabilizationIterationsDone', () => { network.fit({ animation: true }) })
  network.on('stabilized', () => { if (fitCount < 1) { network.fit({ animation: true }); fitCount++ } })
  network.on('resize', () => { network.fit() })

  network.on('click', (params) => {
    if (params.nodes.length) {
      const node = nodes.get(params.nodes[0])
      if (node && node.group === 'gang' && node.gangData) emit('select', node.gangData)
    }
  })
}

function highlightSearch() {
  if (!network) return
  const kw = (props.searchKeyword || '').trim().toLowerCase()
  if (!kw) {
    nodes.forEach(n => {
      nodes.update({ id: n.id, opacity: 1.0 })
    })
    edges.forEach(e => {
      edges.update({ id: e.id, color: { ...e.color, opacity: 1.0 } })
    })
    return
  }
  const matchedNodeIds = []
  nodes.forEach(n => {
    const text = (n.searchText || n.label || '').toLowerCase()
    if (text.includes(kw)) {
      matchedNodeIds.push(n.id)
      nodes.update({ id: n.id, opacity: 1.0, size: (n.group === 'gang' ? 36 : 18) })
    } else {
      nodes.update({ id: n.id, opacity: 0.15, size: (n.group === 'gang' ? 22 : 10) })
    }
  })
  edges.forEach(e => {
    const connected = matchedNodeIds.includes(e.from) || matchedNodeIds.includes(e.to)
    edges.update({ id: e.id, color: { ...e.color, opacity: connected ? 1.0 : 0.08 } })
  })
  if (matchedNodeIds.length) {
    network.selectNodes(matchedNodeIds, false)
    network.fit({ nodes: matchedNodeIds, animation: true })
  }
}

function clusterAll() {
  if (!network) return
  try { network.clustering.clusterByConnection(2); setTimeout(() => { try { network.fit({ animation: true }) } catch(e) {} }, 200) } catch(e) {}
}
function expandAll() {
  if (!network) return
  try { network.clustering.openAllClusters(); setTimeout(() => { try { network.fit({ animation: true }) } catch(e) {} }, 200) } catch(e) {}
}

function buildFlowGraph() {
  if (!containerRef.value || !props.flowData) return
  nodes.clear(); edges.clear()
  const flowNodes = props.flowData.nodes || []; const flowEdges = props.flowData.edges || []
  flowNodes.forEach(n => {
    nodes.add({ id: n.id, label: n.label || n.name, title: n.title || n.label, shape: 'dot', size: n.size || 20,
      color: n.type === 'source' ? { background: '#f59e0b', border: '#fbbf24', highlight: { background: '#d97706', border: '#f59e0b' } } : { background: '#ef4444', border: '#f87171', highlight: { background: '#dc2626', border: '#ef4444' } },
      font: { color: '#e2e8f0', size: 12 } })
  })
  flowEdges.forEach(e => {
    edges.add({ id: e.id, from: e.from || e.source, to: e.to || e.target, label: e.label || (e.amount ? '¥' + e.amount : ''),
      color: { color: 'rgba(245,158,11,0.6)', highlight: '#f59e0b' }, width: 2 + Math.min(Math.floor(e.amount || 0) / 50000, 5),
      arrows: { to: { enabled: true, scaleFactor: 0.8 } }, font: { color: '#f59e0b', size: 10, align: 'middle' }, smooth: { type: 'curvedCW', roundness: 0.2 } })
  })
  const options = { physics: { solver: 'barnesHut', barnesHut: { gravitationalConstant: -200, centralGravity: 0.005, springLength: 100 }, stabilization: { iterations: 40, updateInterval: 50 } }, edges: { smooth: true }, interaction: { hover: true, tooltipDelay: 200, dragNodes: true, navigationButtons: true } }
  if (network) network.destroy()
  network = new Network(containerRef.value, { nodes, edges }, options)
  network.once('stabilizationIterationsDone', () => { network.fit({ animation: true }); network.setOptions({ physics: false }) })
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
    if (canvas) { const link = document.createElement('a'); link.download = 'network-' + Date.now() + '.png'; link.href = canvas.toDataURL(); link.click() }
  }
}
const searchKeyword = computed({
  get: () => props.searchKeyword,
  set: (v) => emit('update:searchKeyword', v)
})
function onSearch() { highlightSearch() }

onMounted(() => { nextTick(() => { buildGangGraph() }) })
onUnmounted(() => { if (network) network.destroy() })
</script>

<style scoped>
.network-graph { width: 100%; height: 100%; display: flex; flex-direction: column; background: rgba(10,14,26,0.5); border-radius: 12px; }
.graph-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: rgba(15,23,42,0.8); border-bottom: 1px solid rgba(0,198,255,0.2); gap: 8px; flex-wrap: wrap; }
.engine-status { display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #00c6ff; box-shadow: 0 0 10px #00c6ff; animation: pulse 2s ease-in-out infinite; }
.status-text { font-size: 12px; color: #94a3b8; font-weight: 500; }
.graph-controls { display: flex; gap: 6px; flex-wrap: wrap; }
.graph-canvas { flex: 1; min-height: 0; background: rgba(10,14,26,0.8); }
.graph-legend { display: flex; justify-content: center; gap: 20px; padding: 10px 16px; background: rgba(15,23,42,0.85); border-top: 1px solid rgba(0,198,255,0.2); flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #94a3b8; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.dot.s { background: #ff3860; box-shadow: 0 0 6px #ff3860; }
.dot.a { background: #ffd700; box-shadow: 0 0 6px #ffd700; }
.dot.b { background: #ff9800; box-shadow: 0 0 6px #ff9800; }
.dot.c { background: #00c6ff; box-shadow: 0 0 6px #00c6ff; }
.dot.case { background: rgba(0,198,255,0.3); border: 2px solid rgba(0,198,255,0.7); }
.dot.money { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }
.dot.target { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
.dot.flow { background: transparent; border: 2px solid #f59e0b; width: 6px; height: 6px; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.9); } }
</style>