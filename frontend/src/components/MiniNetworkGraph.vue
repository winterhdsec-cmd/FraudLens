<template>
  <div class="mini-network-graph">
    <div class="mini-controls">
      <div class="mini-status">
        <div class="status-dot"></div>
        <span class="status-label">{{ title }}</span>
      </div>
      <div class="mini-buttons">
        <el-button size="small" @click="fitView">适应屏幕</el-button>
        <el-button size="small" @click="togglePhysics">{{ physicsEnabled ? '暂停布局' : '恢复布局' }}</el-button>
        <el-button size="small" type="primary" @click="exportGraph">导出</el-button>
      </div>
    </div>
    <div class="mini-canvas" ref="containerRef"></div>
    <div v-if="legends.length" class="mini-legend">
      <div v-for="item in legends" :key="item.label" class="legend-item">
        <span class="legend-dot" :style="{ background: item.color, borderColor: item.border || item.color }"></span>
        <span>{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const props = defineProps({
  title: { type: String, default: '关联图谱' },
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  legends: { type: Array, default: () => [] },
  layout: { type: Object, default: null },
  physics: { type: Object, default: () => ({
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -200,
      centralGravity: 0.003,
      springLength: 150,
      springConstant: 0.02,
      damping: 0.4
    },
    stabilization: { iterations: 60, updateInterval: 50, fit: true }
  })},
  nodeDefaults: { type: Object, default: () => ({
    shape: 'dot',
    font: { color: '#e2e8f0', size: 10, face: 'sans-serif', strokeWidth: 2, strokeColor: '#0a0e1a' },
    borderWidth: 2,
    shadow: { enabled: true, size: 6, color: 'rgba(0,0,0,0.3)' }
  })},
  edgeDefaults: { type: Object, default: () => ({
    smooth: { type: 'continuous' },
    arrows: { to: { enabled: true, scaleFactor: 0.8 } },
    color: { color: 'rgba(0,212,255,0.3)', highlight: '#00d4ff', hover: '#00d4ff' },
    width: 1.5,
    font: { color: 'rgba(0,212,255,0.7)', size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#0a0e1a' }
  })}
})

const emit = defineEmits(['nodeClick'])

const containerRef = ref(null)
const physicsEnabled = ref(true)
let network = null
let visNodes = new DataSet()
let visEdges = new DataSet()

watch(() => props.nodes, () => { nextTick(buildGraph) }, { deep: true })
watch(() => props.edges, () => { nextTick(buildGraph) }, { deep: true })

function buildGraph() {
  if (!containerRef.value) return
  visNodes.clear()
  visEdges.clear()

  if (!props.nodes.length && !props.edges.length) return

  props.nodes.forEach(n => {
    visNodes.add({
      ...props.nodeDefaults,
      ...n,
      id: n.id,
      label: n.label || n.name || '',
      title: n.title || n.label || n.name || '',
      color: n.color || props.nodeDefaults.color,
      size: n.size || n.symbolSize || 20
    })
  })

  props.edges.forEach(e => {
    visEdges.add({
      ...props.edgeDefaults,
      ...e,
      id: e.id || `e_${e.from || e.source}_${e.to || e.target}`,
      from: e.from || e.source,
      to: e.to || e.target,
      label: e.label || ''
    })
  })

  const options = {
    physics: physicsEnabled.value ? props.physics : false,
    interaction: {
      hover: true,
      tooltipDelay: 200,
      dragNodes: true,
      dragView: true,
      zoomView: true,
      navigationButtons: true,
      selectable: true,
      keyboard: true
    },
    configure: { filter: () => false, showButton: false }
  }
  if (props.layout) options.layout = props.layout

  if (network) network.destroy()
  try {
    network = new Network(containerRef.value, { nodes: visNodes, edges: visEdges }, options)

    let fitCount = 0
    network.once('stabilizationIterationsDone', () => {
      try { network.fit({ animation: true }) } catch (e) {}
    })
    network.on('stabilized', () => {
      if (fitCount < 1) { try { network.fit({ animation: true }) } catch (e) {}; fitCount++ }
    })
    network.on('resize', () => { try { network.fit() } catch (e) {} })

    network.on('click', (params) => {
      if (params.nodes.length) {
        const node = visNodes.get(params.nodes[0])
        if (node) emit('nodeClick', { node, rawId: params.nodes[0] })
      }
    })
  } catch (e) {
    console.warn('MiniNetworkGraph init error:', e)
  }
}

function fitView() { if (network) try { network.fit({ animation: true }) } catch (e) {} }
function togglePhysics() {
  physicsEnabled.value = !physicsEnabled.value
  if (network) network.setOptions({ physics: physicsEnabled.value })
  if (physicsEnabled.value) setTimeout(() => fitView(), 500)
}
function exportGraph() {
  if (containerRef.value) {
    const canvas = containerRef.value.querySelector('canvas')
    if (canvas) {
      const link = document.createElement('a')
      link.download = 'graph-' + Date.now() + '.png'
      link.href = canvas.toDataURL()
      link.click()
    }
  }
}

onMounted(() => { nextTick(buildGraph) })
onUnmounted(() => { if (network) { network.destroy(); network = null } })
</script>

<style scoped>
.mini-network-graph {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(10,14,26,0.5);
  border-radius: 10px;
  overflow: hidden;
}
.mini-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: rgba(15,23,42,0.8);
  border-bottom: 1px solid rgba(0,198,255,0.15);
  gap: 8px;
  flex-wrap: wrap;
}
.mini-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00c6ff;
  box-shadow: 0 0 8px #00c6ff;
  animation: miniPulse 2s ease-in-out infinite;
  flex-shrink: 0;
}
.status-label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  white-space: nowrap;
}
.mini-buttons {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.mini-buttons :deep(.el-button) {
  padding: 4px 10px;
  font-size: 11px;
  --el-border-radius-base: 6px;
}
.mini-canvas {
  flex: 1;
  min-height: 0;
  background: rgba(10,14,26,0.8);
}
.mini-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 8px 14px;
  background: rgba(15,23,42,0.85);
  border-top: 1px solid rgba(0,198,255,0.1);
  flex-wrap: wrap;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #94a3b8;
}
.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
  border: 1px solid;
}
@keyframes miniPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
</style>