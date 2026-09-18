<template>
  <div class="gang-radar">
    <div v-if="loading" class="gr-loading">
      <span class="gr-loading-text">评估维度计算中…</span>
    </div>
    <div v-else-if="dims.length" ref="chartEl" class="gr-chart" :style="{ height: height + 'px' }"></div>
    <div v-else class="gr-empty">暂无能力评估数据</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { getEcharts } from '../composables/useEcharts.js'
import { getGangRadar } from '../api.js'

const props = defineProps({
  radar: { type: Object, default: () => ({}) },
  gangId: { type: String, default: '' },
  height: { type: Number, default: 220 }
})

const chartEl = ref(null)
const loading = ref(false)
let chartInstance = null
let echarts = null
let resizeObs = null
let disposed = false
let reqId = 0

// 同 gangId 去重：避免多卡同时请求同一个团伙的雷达接口
const inFlight = new Map()

const radarData = ref(props.radar || {})

const dims = computed(() => {
  const rd = radarData.value || {}
  return Object.entries(rd)
    .filter(([, v]) => typeof v === 'number' && v > 0)
    .map(([k, v]) => ({ name: k, value: Math.round(Math.min(100, Number(v))) }))
})

function renderChart() {
  if (!chartEl.value || !echarts || disposed) return
  if (!dims.value.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  }

  const names = dims.value.map(d => d.name)
  const values = dims.value.map(d => d.value)
  const colors = ['#00d4ff', '#f59e0b', '#8b5cf6', '#10b981', '#ec4899', '#ef4444', '#fbbf24']

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(10,14,26,0.94)',
      borderColor: 'rgba(0,198,255,0.25)',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter: (params) => {
        if (!params.value) return ''
        return names.map((n, i) =>
          `<span style="color:${colors[i % colors.length]};font-weight:700">${n}</span>: ${params.value[i]} 分`
        ).join('<br/>')
      }
    },
    radar: {
      indicator: names.map(n => ({ name: n, max: 100 })),
      shape: 'polygon',
      radius: '68%',
      center: ['50%', '54%'],
      splitNumber: 4,
      axisName: {
        color: '#94a3b8',
        fontSize: 11,
        fontWeight: 500
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(0,198,255,0.02)',
            'rgba(0,198,255,0.045)',
            'rgba(0,198,255,0.07)',
            'rgba(0,198,255,0.095)'
          ]
        }
      },
      splitLine: {
        lineStyle: { color: 'rgba(0,198,255,0.12)', width: 1 }
      },
      axisLine: {
        lineStyle: { color: 'rgba(0,198,255,0.14)' }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '团伙能力',
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: {
          color: '#00d4ff',
          width: 2,
          shadowColor: 'rgba(0,212,255,0.35)',
          shadowBlur: 6
        },
        areaStyle: {
          color: 'rgba(0,212,255,0.18)'
        },
        itemStyle: {
          color: '#00d4ff',
          borderColor: '#00d4ff',
          borderWidth: 1.5
        }
      }],
      animationDuration: 700,
      animationEasing: 'cubicOut'
    }]
  }, true)
}

async function loadFromApi() {
  if (!props.gangId || dims.value.length) return
  if (inFlight.get(props.gangId)) return
  loading.value = true
  const myReq = ++reqId
  inFlight.set(props.gangId, true)
  try {
    const res = await getGangRadar(props.gangId)
    if (disposed || myReq !== reqId) return
    const rd = res?.data?.radar || {}
    if (Object.keys(rd).length) {
      radarData.value = rd
      renderChart()
    }
  } catch (e) {
    // 雷达接口不可用时保持空态即可，不阻塞画像卡片
  } finally {
    inFlight.delete(props.gangId)
    if (!disposed && myReq === reqId) loading.value = false
  }
}

watch(() => props.radar, (v) => {
  radarData.value = v || {}
  if (dims.value.length) {
    renderChart()
  } else {
    loadFromApi()
  }
}, { immediate: true })

onMounted(() => {
  getEcharts().then(mod => {
    if (disposed) return
    echarts = mod
    if (dims.value.length) renderChart()
  })
  if (chartEl.value && typeof ResizeObserver !== 'undefined') {
    resizeObs = new ResizeObserver(() => {
      chartInstance?.resize()
    })
    resizeObs.observe(chartEl.value)
  }
})

onBeforeUnmount(() => {
  disposed = true
  reqId++
  resizeObs?.disconnect()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.gang-radar {
  width: 100%;
  min-height: 40px;
}
.gr-chart {
  width: 100%;
}
.gr-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60px;
  font-size: 12px;
  color: var(--text-secondary, #64748b);
}
.gr-loading-text {
  position: relative;
  padding-left: 18px;
}
.gr-loading-text::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 12px;
  height: 12px;
  margin-top: -6px;
  border: 2px solid rgba(0, 212, 255, 0.25);
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: gr-spin 0.7s linear infinite;
}
@keyframes gr-spin {
  to { transform: rotate(360deg); }
}
.gr-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60px;
  font-size: 12px;
  color: var(--text-secondary, #64748b);
  background: rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  border: 1px dashed rgba(148, 163, 184, 0.25);
}
</style>
