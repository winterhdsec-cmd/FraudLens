<template>
  <div class="network-graph">
    <div class="graph-header">
      <div class="engine-status">
        <div class="status-ring"></div>
        <div class="status-dot"></div>
        <span class="status-text">AI 研判引擎运行中</span>
      </div>
      <div class="graph-controls">
        <el-button size="small" @click="refreshGraph">
          <span>🔄</span> 刷新
        </el-button>
        <el-button size="small" type="primary" @click="exportGraph">
          <span>📥</span> 导出
        </el-button>
      </div>
    </div>

    <div class="graph-canvas">
      <div class="grid-bg"></div>
      <svg ref="svgRef" class="关系图谱" :width="svgWidth" :height="svgHeight">
        <defs>
          <radialGradient id="nodeGradientGangS" cx="30%" cy="30%" r="70%">
            <stop offset="0%" style="stop-color:#ff3860;stop-opacity:0.9" />
            <stop offset="50%" style="stop-color:#ff6b6b;stop-opacity:0.8" />
            <stop offset="100%" style="stop-color:#c0392b;stop-opacity:0.6" />
          </radialGradient>
          <radialGradient id="nodeGradientGangA" cx="30%" cy="30%" r="70%">
            <stop offset="0%" style="stop-color:#ffd700;stop-opacity:0.9" />
            <stop offset="50%" style="stop-color:#ffb800;stop-opacity:0.8" />
            <stop offset="100%" style="stop-color:#f39c12;stop-opacity:0.6" />
          </radialGradient>
          <radialGradient id="nodeGradientCase" cx="30%" cy="30%" r="70%">
            <stop offset="0%" style="stop-color:#00c6ff;stop-opacity:0.8" />
            <stop offset="50%" style="stop-color:#00a8ff;stop-opacity:0.7" />
            <stop offset="100%" style="stop-color:#0984e3;stop-opacity:0.5" />
          </radialGradient>
          <radialGradient id="nodeGradientMoney" cx="30%" cy="30%" r="70%">
            <stop offset="0%" style="stop-color:#f59e0b;stop-opacity:0.8" />
            <stop offset="100%" style="stop-color:#d69e2e;stop-opacity:0.6" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="glowStrong">
            <feGaussianBlur stdDeviation="10" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <g class="links">
          <line
            v-for="edge in edges"
            :key="'glow-' + edge.id"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            :stroke="edge.color"
            stroke-width="8"
            stroke-opacity="0.3"
            stroke-linecap="round"
            class="link-line-glow"
          />
          <line
            v-for="edge in edges"
            :key="edge.id"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            :stroke="edge.color"
            stroke-width="3"
            stroke-linecap="round"
            class="link-line"
            :class="{ active: edge.active }"
          />
          <polygon
            v-for="edge in edges"
            :key="'arrow-' + edge.id"
            :points="getArrowPoints(edge.x1, edge.y1, edge.x2, edge.y2)"
            :fill="edge.color"
            class="link-arrow"
          />
        </g>

        <g class="nodes">
          <g
            v-for="node in nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="node-group"
            :class="{ 
              selected: selectedGang?.id === node.id,
              highlighted: hoverNode?.id === node.id 
            }"
            @click="handleNodeClick(node)"
            @mouseenter="hoverNode = node"
            @mouseleave="hoverNode = null"
          >
            <circle
              :r="node.size + (hoverNode?.id === node.id ? 15 : 10)"
              :fill="getNodeGlowColor(node)"
              :opacity="hoverNode?.id === node.id ? 0.4 : 0.25"
              class="node-glow"
            />
            <circle
              :r="node.size + 5"
              :fill="getNodeStroke(node)"
              opacity="0.3"
              class="node-ring"
            />
            <circle
              :r="node.size"
              :fill="getNodeFill(node)"
              :stroke="getNodeStroke(node)"
              stroke-width="2"
              :filter="hoverNode?.id === node.id ? 'url(#glowStrong)' : 'url(#glow)'"
              class="node-body"
            />
            <text
              text-anchor="middle"
              dominant-baseline="middle"
              :font-size="node.size * 0.4"
              class="node-icon"
            >{{ node.icon }}</text>
            <g :transform="getLabelTransform(node)">
              <text
                text-anchor="middle"
                font-size="11"
                fill="#e2e8f0"
                class="node-label"
              >{{ node.label }}</text>
            </g>
            <g v-if="node.amount" :transform="getAmountTransform(node)">
              <text
                text-anchor="middle"
                font-size="10"
                fill="#94a3b8"
                class="node-amount"
              >{{ node.amount }}</text>
            </g>
          </g>
        </g>
      </svg>

      <div v-if="hoverNode" class="node-tooltip" :style="tooltipStyle">
        <div class="tooltip-header">
          <div class="tooltip-icon">{{ hoverNode.icon }}</div>
          <div class="tooltip-title">{{ hoverNode.name }}</div>
        </div>
        <div class="tooltip-info" v-if="hoverNode.type === 'gang'">
          <div class="tooltip-row">
            <span class="tooltip-label">风险等级</span>
            <span class="tooltip-value" :class="hoverNode.riskLevel.toLowerCase()">{{ hoverNode.riskLevel }}级</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-label">涉案金额</span>
            <span class="tooltip-value danger">{{ hoverNode.amount }}</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-label">关联案件</span>
            <span class="tooltip-value">{{ hoverNode.cases || 0 }}起</span>
          </div>
        </div>
        <div class="tooltip-info" v-if="hoverNode.type === 'case'">
          <div class="tooltip-row">
            <span class="tooltip-label">案件编号</span>
            <span class="tooltip-value">{{ hoverNode.id }}</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-label">涉案金额</span>
            <span class="tooltip-value danger">{{ hoverNode.amount }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="graph-legend">
      <div class="legend-item">
        <span class="legend-icon gang-s">👥</span>
        <span class="legend-text">S级团伙</span>
      </div>
      <div class="legend-item">
        <span class="legend-icon gang-a">👥</span>
        <span class="legend-text">A级团伙</span>
      </div>
      <div class="legend-item">
        <span class="legend-icon case">📋</span>
        <span class="legend-text">案件节点</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  gangs: {
    type: Array,
    default: () => []
  },
  selectedGang: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select'])

const svgRef = ref(null)
const svgWidth = ref(900)
const svgHeight = ref(550)
const hoverNode = ref(null)
const tooltipStyle = ref({})

const nodes = computed(() => {
  const result = []
  const centerX = svgWidth.value / 2
  const centerY = svgHeight.value / 2
  
  const gangCount = Math.max(props.gangs.length, 2)
  const subgraphSpacing = Math.min(280, svgWidth.value / (gangCount + 1))
  
  const gangsData = props.gangs.length > 0 
    ? props.gangs 
    : [
        { id: 'demo-gang-s', name: 'S级诈骗团伙', icon: '🦈', riskLevel: 'S', amount: '¥500万', cases: 8 },
        { id: 'demo-gang-a', name: 'A级诈骗团伙', icon: '🐺', riskLevel: 'A', amount: '¥200万', cases: 4 }
      ]

  gangsData.forEach((gang, idx) => {
    const subgraphX = subgraphSpacing * (idx + 1)
    const subgraphY = centerY
    
    const gangSize = gang.riskLevel === 'S' ? 32 : 28
    result.push({
      id: gang.id,
      type: 'gang',
      name: gang.name,
      icon: gang.icon,
      label: gang.name.length > 6 ? gang.name.slice(0, 6) + '...' : gang.name,
      x: subgraphX,
      y: subgraphY,
      size: gangSize,
      riskLevel: gang.riskLevel,
      amount: gang.amount,
      cases: gang.cases
    })

    const caseCount = Math.min(gang.cases, 4)
    const casePositions = [
      { dx: 0, dy: -130 },
      { dx: 120, dy: -80 },
      { dx: 120, dy: 80 },
      { dx: 0, dy: 130 }
    ]
    
    for (let i = 0; i < caseCount; i++) {
      const pos = casePositions[i]
      result.push({
        id: `${gang.id}-case-${i}`,
        type: 'case',
        name: `案件 ${i + 1}`,
        icon: '📋',
        label: `C${String(i + 1).padStart(3, '0')}`,
        x: subgraphX + pos.dx,
        y: subgraphY + pos.dy,
        size: 18
      })
    }
  })

  return result
})

const edges = computed(() => {
  const result = []
  const gangNodes = nodes.value.filter(n => n.type === 'gang')

  gangNodes.forEach(gang => {
    const relatedCases = nodes.value.filter(n => n.type === 'case' && n.id.includes(gang.id))
    relatedCases.forEach(caseNode => {
      result.push({
        id: `${gang.id}-${caseNode.id}`,
        x1: gang.x,
        y1: gang.y,
        x2: caseNode.x,
        y2: caseNode.y,
        color: 'rgba(0, 198, 255, 0.7)'
      })
    })
  })

  return result
})

const getNodeFill = (node) => {
  if (node.type === 'gang') {
    return node.riskLevel === 'S' ? 'url(#nodeGradientGangS)' : 'url(#nodeGradientGangA)'
  }
  return 'url(#nodeGradientCase)'
}

const getNodeStroke = (node) => {
  if (node.type === 'gang') {
    return node.riskLevel === 'S' ? '#ff3860' : '#ffd700'
  }
  return '#00c6ff'
}

const getNodeGlowColor = (node) => {
  if (node.type === 'gang') {
    return node.riskLevel === 'S' ? '#ff3860' : '#ffd700'
  }
  return '#00c6ff'
}

const getArrowPoints = (x1, y1, x2, y2) => {
  const angle = Math.atan2(y2 - y1, x2 - x1)
  const arrowLength = 10
  const arrowWidth = 6
  const px = x2 - arrowLength * Math.cos(angle)
  const py = y2 - arrowLength * Math.sin(angle)
  const p1x = px - arrowWidth * Math.sin(angle)
  const p1y = py + arrowWidth * Math.cos(angle)
  const p2x = px + arrowWidth * Math.sin(angle)
  const p2y = py - arrowWidth * Math.cos(angle)
  return `${p1x},${p1y} ${p2x},${p2y} ${x2},${y2}`
}

const handleNodeClick = (node) => {
  if (node.type === 'gang') {
    const gang = props.gangs.find(g => g.id === node.id)
    if (gang) {
      emit('select', gang)
    }
  }
}

const handleResize = () => {
  if (svgRef.value) {
    const parent = svgRef.value.parentElement
    if (parent) {
      svgWidth.value = Math.min(parent.clientWidth, 900)
      svgHeight.value = Math.min(parent.clientHeight, 550)
    }
  }
}

const refreshGraph = () => {
  handleResize()
}

const getLabelTransform = (node) => {
  const centerX = svgWidth.value / 2
  const centerY = svgHeight.value / 2
  
  if (node.type === 'gang') {
    return `translate(0, ${node.size + 20})`
  }
  
  const dx = node.x - centerX
  const dy = node.y - centerY
  const angle = Math.atan2(dy, dx)
  
  if (Math.abs(Math.cos(angle)) > Math.abs(Math.sin(angle))) {
    if (dx > 0) {
      return `translate(${node.size + 15}, 0)`
    } else {
      return `translate(-${node.size + 15}, 0)`
    }
  } else {
    if (dy > 0) {
      return `translate(0, ${node.size + 20})`
    } else {
      return `translate(0, -${node.size + 25})`
    }
  }
}

const getAmountTransform = (node) => {
  const centerY = svgHeight.value / 2
  const dy = node.y - centerY
  
  if (dy > 0) {
    return `translate(0, ${node.size + 36})`
  } else {
    return `translate(0, -${node.size + 40})`
  }
}

const exportGraph = () => {
  if (svgRef.value) {
    const svgData = svgRef.value.outerHTML
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `network-graph-${Date.now()}.svg`
    link.click()
    URL.revokeObjectURL(url)
  }
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.network-graph {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(10, 14, 26, 0.5);
  border-radius: 12px;
  overflow: hidden;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(0, 198, 255, 0.2);
  position: relative;
}

.graph-header::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 2px;
  background: var(--accent-cyan);
  box-shadow: 0 0 10px var(--accent-cyan);
}

.engine-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-ring {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid #00c6ff;
  border-radius: 50%;
  animation: ring-pulse 2s ease-out infinite;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #00c6ff;
  box-shadow: 0 0 15px #00c6ff, 0 0 30px rgba(0, 198, 255, 0.5);
  animation: pulse 2s ease-in-out infinite;
}

.status-text {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
}

.graph-controls {
  display: flex;
  gap: 10px;
}

.graph-canvas {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.grid-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image:
    radial-gradient(circle, rgba(0, 198, 255, 0.15) 1px, transparent 1px),
    linear-gradient(rgba(0, 198, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 198, 255, 0.05) 1px, transparent 1px);
  background-size: 50px 50px, 50px 50px, 50px 50px;
  animation: grid-move 20s linear infinite;
}

.关系图谱 {
  width: 100%;
  height: 100%;
}

.node-group {
  cursor: pointer;
  transition: all 0.3s ease;
}

.node-group:hover {
  transform: scale(1.05);
}

.node-group.highlighted .node-glow {
  animation: glow-pulse 1.5s ease-in-out infinite;
}

.node-group.selected .node-ring {
  animation: ring-spin 2s linear infinite;
}

.node-tooltip {
  position: absolute;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%);
  border: 1px solid rgba(0, 198, 255, 0.4);
  border-radius: 12px;
  padding: 16px;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 198, 255, 0.1);
  min-width: 200px;
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.2);
}

.tooltip-icon {
  font-size: 24px;
}

.tooltip-title {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.tooltip-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tooltip-label {
  font-size: 12px;
  color: #94a3b8;
}

.tooltip-value {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
}

.tooltip-value.danger {
  color: #ef4444;
}

.tooltip-value.s {
  color: #ff3860;
}

.tooltip-value.a {
  color: #ffd700;
}

.graph-legend {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 16px;
  background: rgba(15, 23, 42, 0.85);
  border-top: 1px solid rgba(0, 198, 255, 0.2);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.legend-icon.gang-s {
  background: linear-gradient(135deg, #ff3860 0%, #ff6b8a 100%);
  box-shadow: 0 0 10px rgba(255, 56, 96, 0.6);
}

.legend-icon.gang-a {
  background: linear-gradient(135deg, #ffd700 0%, #ffe047 100%);
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.6);
}

.legend-icon.case {
  background: linear-gradient(135deg, #00c6ff 0%, #00e5ff 100%);
  box-shadow: 0 0 10px rgba(0, 198, 255, 0.6);
}

.legend-text {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.95); }
}

@keyframes ring-pulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(2.5); opacity: 0; }
}

@keyframes grid-move {
  0% { background-position: 0 0; }
  100% { background-position: 50px 50px; }
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.2); }
}

@keyframes ring-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
