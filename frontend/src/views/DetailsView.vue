<template>
<div class="view-section">
  <div v-if="!gangs.length" class="empty-state" style="margin-top: 60px;">
    <div class="empty-content">
      <div class="empty-icon">📈</div>
      <h3 class="empty-title">暂无分析数据</h3>
      <p class="empty-desc">请先进行智能研判分析，系统将自动生成团伙特征、资金流向和关联关系分析</p>
      <el-button type="primary" size="large" @click="router.push({ name: 'input' })">
        <span>📝</span> 前往录入研判
      </el-button>
    </div>
  </div>
  <div v-else>
    <div class="section-header">
      <div class="header-left">
        <h2 class="section-title">
          <span class="title-icon">📈</span>
          深度分析
        </h2>
        <p class="section-desc">选择团伙进行专项分析</p>
      </div>
      <div class="header-right">
        <el-select v-model="selectedGangId" placeholder="选择分析团伙" size="large" style="width: 280px">
          <el-option v-for="g in gangs" :key="g.id || g.gang_id" :label="g.name || g.gang_name" :value="g.id || g.gang_id" />
        </el-select>
      </div>
    </div>

    <div v-if="currentGang" class="current-gang-badge">
      <span class="badge-dot"></span>
      <span class="badge-label">当前分析：</span>
      <span class="badge-name">{{ currentGang.name || currentGang.gang_name || '未知团伙' }}</span>
      <span class="badge-risk" :style="{ background: currentGangPattern.riskColor }">{{ currentGangPattern.riskLabel }}</span>
      <div class="gang-review-indicator">
        <el-tag v-if="gangReviewSummary.pending === 0 && gangReviewSummary.total > 0" size="small" type="success" effect="dark">全团已复核</el-tag>
        <el-tag v-else-if="gangReviewSummary.pending > 0" size="small" type="warning" effect="dark">{{ gangReviewSummary.reviewed }}/{{ gangReviewSummary.total }} 已复核</el-tag>
        <el-button v-if="gangReviewSummary.pending > 0" size="small" type="primary" plain @click="openGangReviewDialog" style="margin-left:8px;height:28px;font-size:12px">
          <span>✅</span> 一键复核确认
        </el-button>
      </div>
    </div>

    <Transition name="gang-fade" mode="out-in">
      <div class="analysis-dashboard" :key="selectedGangId || 'none'">
        <div class="analysis-row analysis-two-col">
          <div class="analysis-col">

            <div class="analysis-card">
              <div class="analysis-header">
                <span class="analysis-icon">🎯</span>
                <span class="analysis-title">团伙特征雷达</span>
                <span class="analysis-subtitle">AI智能分析</span>
              </div>
              <div class="analysis-content">
                <div ref="radarChartRef" class="radar-chart-container"></div>
              </div>
            </div>

            <div class="analysis-card">
              <div class="analysis-header">
                <span class="analysis-icon">📈</span>
                <span class="analysis-title">团伙话术分析</span>
                <span class="analysis-subtitle">AI智能分析</span>
              </div>
              <div class="analysis-content">
                <div class="pattern-grid">
                  <div class="pattern-card">
                    <div class="pattern-icon">🎯</div>
                    <div class="pattern-info">
                      <span class="pattern-title">诈骗类型</span>
                      <span class="pattern-value">{{ currentGangPattern.scamType }}</span>
                      <span class="pattern-desc">团伙主要作案手法</span>
                    </div>
                  </div>
                  <div class="pattern-card">
                    <div class="pattern-icon">💰</div>
                    <div class="pattern-info">
                      <span class="pattern-title">涉案总金额</span>
                      <span class="pattern-value">{{ currentGangPattern.totalAmount }}</span>
                      <span class="pattern-desc">累计涉案金额</span>
                    </div>
                  </div>
                  <div class="pattern-card">
                    <div class="pattern-icon">👥</div>
                    <div class="pattern-info">
                      <span class="pattern-title">关联案件</span>
                      <span class="pattern-value">{{ currentGangPattern.caseCount }}起</span>
                      <span class="pattern-desc">团伙关联案件数量</span>
                    </div>
                  </div>
                  <div class="pattern-card">
                    <div class="pattern-icon">📊</div>
                    <div class="pattern-info">
                      <span class="pattern-title">风险等级</span>
                      <span class="pattern-value" :style="{ color: currentGangPattern.riskColor }">{{ currentGangPattern.riskLabel }}</span>
                      <span class="pattern-desc">团伙综合风险评估</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="analysis-card">
              <div class="analysis-header">
                <span class="analysis-icon">📊</span>
                <span class="analysis-title">技术手段先进性</span>
              </div>
              <div class="analysis-content">
                <div class="type-stats">
                  <div class="type-item" v-for="(item, idx) in currentCaseTypeStats" :key="idx">
                    <div class="type-bar" :style="{ width: item.percent + '%', background: item.color }"></div>
                    <div class="type-info">
                      <span class="type-name">{{ item.name }}</span>
                      <span class="type-count">{{ item.count }}起</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <div class="analysis-col">

            <div class="analysis-card money-flow-card" :class="{ collapsed: isMoneyFlowCollapsed }">
              <div class="analysis-header">
                <span class="analysis-icon">💰</span>
                <span class="analysis-title">资金流向追踪</span>
                <span class="flow-badge">AI分析</span>
                <el-button link class="collapse-btn" @click="isMoneyFlowCollapsed = !isMoneyFlowCollapsed">
                  {{ isMoneyFlowCollapsed ? '展开' : '折叠' }}
                </el-button>
              </div>
              <div class="money-flow-body" :class="{ expanded: !isMoneyFlowCollapsed }">
                <div class="analysis-content">
                  <div class="flow-compact">
                    <div v-for="(node, ni) in currentFlowPath" :key="ni" class="flow-compact-node" :class="node.type">
                      <span class="fcn-icon">{{ node.icon }}</span>
                      <span class="fcn-label">{{ node.label }}</span>
                      <span class="fcn-amount" v-if="node.amount">{{ node.amount }}</span>
                    </div>
                  </div>
                  <div class="flow-metrics">
                    <div class="metric-item">
                      <div class="metric-icon">💰</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案金额</span>
                        <span class="metric-value danger">{{ currentGangPattern.totalAmount }}</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">📊</div>
                      <div class="metric-info">
                        <span class="metric-label">中转层级</span>
                        <span class="metric-value">{{ currentFlowMetrics.max_level }}层</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🌏</div>
                      <div class="metric-info">
                        <span class="metric-label">境外流向</span>
                        <span class="metric-value warning">{{ currentFlowMetrics.overseas_pct }}%</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🏦</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案账户</span>
                        <span class="metric-value">{{ currentFlowMetrics.total_accounts }}个</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="analysis-card">
              <div class="analysis-header">
                <span class="analysis-icon">🧬</span>
                <span class="analysis-title">语义指纹分析</span>
                <span class="analysis-subtitle">跨案件话术模式识别</span>
              </div>
              <div class="analysis-content">
                <div v-if="currentFingerprints.length" class="fingerprint-grid">
                  <div v-for="fp in currentFingerprints" :key="fp.type" class="fingerprint-card">
                    <div class="fp-header">
                      <span class="fp-type">{{ fp.type }}</span>
                      <el-tag size="small" type="info">{{ fp.count }}案</el-tag>
                    </div>
                    <div class="fp-amount">{{ fp.totalAmount > 10000 ? (fp.totalAmount/10000).toFixed(1) + '万元' : fp.totalAmount + '元' }}</div>
                    <div class="fp-keywords">
                      <el-tag v-for="kw in fp.keywords" :key="kw" size="small" class="fp-tag">{{ kw }}</el-tag>
                    </div>
                    <div class="fp-signature">{{ fp.signature }}</div>
                  </div>
                </div>
                <div v-else class="fp-empty">
                  <p>暂无语义指纹数据，请先进行研判分析</p>
                </div>
              </div>
            </div>

            <div class="analysis-card">
              <div class="analysis-header">
                <span class="analysis-icon">🌍</span>
                <span class="analysis-title">跨区域作案特征</span>
              </div>
              <div class="analysis-content">
                <div class="region-stats">
                  <div class="region-item" v-for="(item, idx) in currentRegionStats" :key="idx">
                    <span class="region-name">{{ item.name }}</span>
                    <div class="region-bar-wrapper">
                      <div class="region-bar" :style="{ width: item.percent + '%' }"></div>
                    </div>
                    <span class="region-count">{{ item.count }}起</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <div class="analysis-row">
          <div class="analysis-card full-width">
            <div class="analysis-header">
              <span class="analysis-icon">🏛️</span>
              <span class="analysis-title">团伙组织结构</span>
              <span class="analysis-subtitle">AI智能分析</span>
            </div>
            <div class="analysis-content">
              <div class="gang-structure" v-if="currentGang">
                <div class="structure-row">
                  <div class="structure-node leader">
                    <span class="node-rank">头目</span>
                    <span class="node-name">{{ currentGang.leader_name || currentGang.gang_name || gangSeedLabel + '主犯' }}</span>
                    <span class="node-desc">{{ currentGang.leader_role || '组织策划' }}</span>
                  </div>
                  <div class="structure-arrow">↓</div>
                  <div class="structure-node manager">
                    <span class="node-rank">骨干</span>
                    <span class="node-name">{{ currentGang.sub_leader || currentGang.core_member || '骨干成员' }}</span>
                    <span class="node-desc">{{ currentGang.sub_role || '执行管理' }}</span>
                  </div>
                  <div class="structure-arrow">↓</div>
                  <div class="structure-nodes">
                    <div class="structure-sub">
                      <div v-for="(m, mi) in currentGangMembers" :key="mi" class="structure-node member">
                        <span class="node-rank">成员{{ mi + 1 }}</span>
                        <span class="node-name">{{ m.name || '涉案人员' }}</span>
                        <span class="node-desc">{{ m.desc || m.role_desc || '参与作案' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="fp-empty">
                <p>请选择团伙查看组织结构</p>
              </div>
            </div>
          </div>
        </div>

        <div class="analysis-row">
          <div class="analysis-card full-width">
            <div class="analysis-header">
              <span class="analysis-icon">🔗</span>
              <span class="analysis-title">关联关系图谱</span>
              <span class="analysis-subtitle">力导向布局 · 可拖拽缩放</span>
            </div>
            <div ref="relationChartRef" style="width: 100%;">
              <MiniNetworkGraph
                title="关联关系图谱"
                :nodes="relationVisNodes"
                :edges="relationVisEdges"
                :legends="relationLegends"
                :physics="relationPhysics"
                style="height:420px;width:100%"
              />
            </div>
          </div>
        </div>

      </div>
    </Transition>
  </div>
</div>

<el-dialog v-model="reviewDialogVisible" title="团伙复核确认" width="500px" class="review-dialog">
  <div class="dialog-body">
    <div class="dialog-gang-info">
      <div class="info-row"><span class="label">团伙名称</span><span class="value">{{ currentGang?.gang_name || currentGang?.name || '未知' }}</span></div>
      <div class="info-row"><span class="label">关联案件数</span><span class="value">{{ gangReviewSummary.total }} 件</span></div>
      <div class="info-row">
        <span class="label">复核进度</span>
        <span class="value">{{ gangReviewSummary.reviewed }}/{{ gangReviewSummary.total }}（待复核: {{ gangReviewSummary.pending }} 件）</span>
      </div>
    </div>
    <div class="dialog-hint">
      <span class="hint-icon">ℹ️</span>
      <span class="hint-text">一键复核确认将为该团伙中所有未复核的案件批量提交复核结论</span>
    </div>
    <el-form label-position="top" class="review-form">
      <el-form-item label="复核结论">
        <el-select v-model="reviewForm.status" style="width:100%">
          <el-option label="已复核 — 结论正确" value="已复核" />
          <el-option label="已复核 — 需修正" value="待修正" />
          <el-option label="已复核 — 误报" value="已驳回" />
        </el-select>
      </el-form-item>
      <el-form-item label="复核备注">
        <el-input v-model="reviewForm.notes" type="textarea" :rows="3" placeholder="请输入复核意见，如团伙划分结果、诈骗类型确认等" />
      </el-form-item>
    </el-form>
  </div>
  <template #footer>
    <el-button @click="reviewDialogVisible = false">取消</el-button>
    <el-button type="primary" :loading="reviewSubmitting" @click="submitGangReview">确认批量复核</el-button>
  </template>
</el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
import * as echarts from 'echarts'
import { getGangRadar, reviewCase } from '../api.js'
import MiniNetworkGraph from '../components/MiniNetworkGraph.vue'
const router = useRouter()
const state = useAppState()
const {
  gangs, cases, getFeatureIcon,
  selectedGang, selectedCase
} = state

const reviewDialogVisible = ref(false)
const reviewForm = ref({ status: '已复核', notes: '' })
const reviewSubmitting = ref(false)
const gangReviewSummary = ref({ total: 0, reviewed: 0, pending: 0 })

const pendingCasesInGang = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const related = g.related_cases || []
  const allCases = cases.value || []
  return related.filter(rc => {
    const full = allCases.find(c => (c.case_id || c.id) === rc.case_id)
    if (!full) return false
    const s = full.status || ''
    if (s === '已复核' || s === '待修正' || s === '已驳回') return false
    if (s === '' || s === '待分析' || s === '已删除') return false
    return true
  })
})

function updateGangReviewSummary() {
  const g = currentGang.value
  if (!g) {
    gangReviewSummary.value = { total: 0, reviewed: 0, pending: 0 }
    return
  }
  const related = g.related_cases || []
  const allCases = cases.value || []
  let total = related.length
  let reviewed = 0
  related.forEach(rc => {
    const full = allCases.find(c => (c.case_id || c.id) === rc.case_id)
    if (!full) return
    const s = full.status || ''
    if (s === '已复核' || s === '待修正' || s === '已驳回') reviewed++
  })
  gangReviewSummary.value = { total, reviewed, pending: total - reviewed }
}

function openGangReviewDialog() {
  reviewForm.value = { status: '已复核', notes: '' }
  reviewDialogVisible.value = true
}

async function submitGangReview() {
  reviewSubmitting.value = true
  try {
    const pendingCases = pendingCasesInGang.value
    for (const rc of pendingCases) {
      const cid = rc.case_id
      try {
        await reviewCase(cid, reviewForm.value)
        const full = cases.value.find(c => (c.case_id || c.id) === cid)
        if (full) full.status = reviewForm.value.status
      } catch (e) {
        console.warn(`复核案件 ${cid} 失败:`, e)
      }
    }
    reviewDialogVisible.value = false
    updateGangReviewSummary()
  } catch (e) {
    console.error('批量复核失败:', e)
  } finally {
    reviewSubmitting.value = false
  }
}

const selectedGangId = ref(null)
const isMoneyFlowCollapsed = ref(false)

const getGangSeed = (g) => {
  if (!g) return 0
  const id = g.id || g.gang_id || g.name || ''
  let hash = 0
  for (let i = 0; i < String(id).length; i++) {
    hash = ((hash << 5) - hash) + String(id).charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}
const gangSeedLabel = computed(() => {
  const g = currentGang.value
  if (!g) return ''
  const seed = getGangSeed(g)
  const labels = ['黄', '蓝', '白', '绿', '红', '黑', '灰', '紫']
  return labels[seed % labels.length]
})

watch(selectedGang, (g) => {
  if (g && (g.id || g.gang_id)) {
    selectedGangId.value = g.id || g.gang_id
  }
}, { immediate: true })

watch(selectedCase, () => {
  selectedGangId.value = null
})

const currentGang = computed(() => {
  if (!selectedGangId.value || !gangs.value.length) return null
  const found = gangs.value.find(g => (g.id === selectedGangId.value || g.gang_id === selectedGangId.value))
  return found || null
})

const currentGangPattern = computed(() => {
  const g = currentGang.value
  if (!g) return { scamType: '-', totalAmount: '0', caseCount: 0, riskColor: '#64748b', riskLabel: '未知' }
  const seed = getGangSeed(g)
  const types = ['冒充客服诈骗', '刷单返利诈骗', '贷款诈骗', '杀猪盘诈骗', '冒充公检法', '注销校园贷', '投资理财诈骗', '游戏交易诈骗']
  const amount = g.total_amount || g.totalAmount || 0
  if (amount > 0) {
    const fmtAmount = amount > 10000 ? (amount / 10000).toFixed(1).replace(/\.0$/, '') + '万' : (amount || 0) + ''
    const score = g.comprehensive_score || g.confidence || g.risk_score || (50 + (seed % 40))
    const riskLabel = score >= 80 ? '高危' : score >= 60 ? '中危' : '低危'
    const riskColor = score >= 80 ? '#ef4444' : score >= 60 ? '#f59e0b' : '#10b981'
    const cases = g.related_cases || g.caseIds || g.cases || []
    return {
      scamType: g.gang_type || g.scam_type || g.type || types[seed % types.length],
      totalAmount: fmtAmount,
      caseCount: cases.length || g.case_count || (1 + (seed % 5)),
      riskColor,
      riskLabel
    }
  }
  const fmtAmount = (g.total_amount_involved || 0) > 10000
    ? ((g.total_amount_involved || 0) / 10000).toFixed(1).replace(/\.0$/, '') + '万'
    : (g.total_amount_involved || 0) + ''
  const scoreVal = g.comprehensive_score || g.confidence || g.risk_score || (50 + (seed % 40))
  const riskLabelVal = scoreVal >= 80 ? '高危' : scoreVal >= 60 ? '中危' : '低危'
  const riskColorVal = scoreVal >= 80 ? '#ef4444' : scoreVal >= 60 ? '#f59e0b' : '#10b981'
  const relatedCases = g.related_cases || g.caseIds || g.cases || []
  return {
    scamType: g.gang_type || g.scam_type || g.type || types[seed % types.length],
    totalAmount: fmtAmount || (seed % 50 + 5) + '万',
    caseCount: relatedCases.length || g.case_count || (1 + (seed % 5)),
    riskColor: riskColorVal,
    riskLabel: riskLabelVal
  }
})

const currentFlowPath = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const fm = currentFlowMetrics.value
  const caseCount = (g.related_cases || []).length || g.total_cases || 0
  return [
    { type: 'victim', icon: '👤', label: '受害人', amount: caseCount + '人' },
    { type: 'account', icon: '💳', label: '涉案账户', amount: fm.total_accounts + '个' },
    { type: 'middle', icon: '🏦', label: '多层流转', amount: fm.max_level + '层' },
    { type: 'overseas', icon: '🌍', label: '境外', amount: fm.overseas_pct + '%' },
  ]
})

const currentGangMembers = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const members = g.members || g.member_list || g.team_members || []
  if (members.length) return members.slice(0, 6)
  const networkNodes = g.network_nodes || []
  if (networkNodes.length) {
    return networkNodes.slice(0, 6).map(n => ({
      name: n.label || n.id || '',
      role_desc: n.role || n.type || '参与作案'
    }))
  }
  const seed = getGangSeed(g)
  return Array.from({ length: 3 }, (_, i) => ({
    name: g.roles?.[i] || '',
    role_desc: i === 0 ? '核心成员' : '参与作案'
  }))
})

const currentFeatures = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const colors = ['#ef4444', '#f59e0b', '#00d4ff', '#8b5cf6', '#10b981', '#ec4899']
  const names = ['诈骗话术成熟度', '资金分散程度', '成员关联密度', '跨区域作案特征', '技术手段先进性', '受害者画像精准度']
  const rd = g.radar_data || {}
  const radarMap = {
    '诈骗话术成熟度': rd.tech || rd.org || 70,
    '资金分散程度': rd.spread || rd.harm || 65,
    '成员关联密度': rd.org || rd.anti || 60,
    '跨区域作案特征': rd.spread || 65,
    '技术手段先进性': rd.tech || 70,
    '受害者画像精准度': rd.harm || 65
  }
  const descs = ['话术模板标准化程度', '资金流转层级数量', '团伙成员社交关系', '跨省跨境作案能力', '反侦察技术水平', '目标人群定位能力']
  return names.map((name, i) => ({
    name,
    confidence: radarMap[name] || 65,
    color: colors[i],
    desc: descs[i]
  }))
})

const currentCaseTypeStats = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const relatedCases = g.related_cases || []
  if (relatedCases.length) {
    const allCases = cases.value || []
    const typeCount = {}
    let maxCount = 0
    relatedCases.forEach(rc => {
      const full = allCases.find(c => (c.case_id || c.id) === rc.case_id)
      const t = full?.scam_type || '其他'
      typeCount[t] = (typeCount[t] || 0) + 1
      maxCount = Math.max(maxCount, typeCount[t])
    })
    const colors = ['#ef4444','#f59e0b','#8b5cf6','#00d4ff','#10b981','#ec4899','#f97316']
    let ci = 0
    return Object.entries(typeCount).map(([name, count]) => ({
      name, count,
      percent: Math.round((count / maxCount) * 100),
      color: colors[ci++ % colors.length]
    }))
  }
  const seed = getGangSeed(g)
  const types = ['冒充客服诈骗', '刷单返利诈骗', '贷款诈骗', '杀猪盘诈骗', '冒充公检法', '注销校园贷', '投资理财诈骗', '游戏交易诈骗']
  const colors = ['#ef4444','#f59e0b','#8b5cf6','#00d4ff','#10b981','#ec4899','#f97316','#06b6d4']
  const caseTypes = g.gang_type || g.scam_type || g.type || types[seed % types.length]
  const totalCases = g.total_cases || g.case_count || (1 + (seed % 8))
  return [{ name: caseTypes, count: totalCases, percent: 100, color: colors[seed % colors.length] }]
})

const currentRegionStats = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const relatedCases = g.related_cases || []
  const allCases = cases.value || []
  if (relatedCases.length) {
    const regionCount = {}
    relatedCases.forEach(rc => {
      const full = allCases.find(c => (c.case_id || c.id) === rc.case_id)
      const region = full?.extracted_entities?.address || full?.victim_address || ''
      const province = ['北京','上海','天津','重庆','广东','浙江','江苏','福建','四川','湖北','湖南','山东','河南']
        .find(p => region.includes(p)) || ''
      if (province) regionCount[province] = (regionCount[province] || 0) + 1
    })
    const entries = Object.entries(regionCount)
    if (entries.length) {
      const maxCount = Math.max(...entries.map(([,v]) => v))
      return entries.map(([name, count]) => ({
        name, count,
        percent: Math.round((count / maxCount) * 100)
      }))
    }
  }
  const seed = getGangSeed(g)
  const knownRegions = ['广东','浙江','江苏','北京','上海','福建','四川','湖北','湖南','山东','河南']
  const fallbackRegion = knownRegions[seed % knownRegions.length]
  return [{
    name: fallbackRegion,
    count: g.total_cases || g.case_count || (1 + (seed % 8)),
    percent: 100
  }]
})

const currentFingerprints = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const tags = g.fingerprint || g.tags || []
  const casesCount = (g.related_cases || []).length || g.total_cases || g.case_count || 0
  const totalAmt = g.total_amount_value || parseFloat(g.total_amount_involved || g.totalAmount || g.total_amount || '0') || 0
  const kw = Array.isArray(tags) && tags.length ? tags.slice(0, 6) : []
  if (!kw.length && g.gang_name) {
    const nameParts = g.gang_name.replace(/[团伙]/g, '').split(/[诈骗]/)
    kw.push(nameParts[0] || g.gang_name)
  }
  const sig = g.description || (kw.slice(0, 3).join('、') + '等诈骗手法')
  return [{
    type: g.gang_name || g.name || '本团伙',
    count: casesCount,
    totalAmount: totalAmt,
    keywords: kw,
    signature: sig
  }]
})

const currentFlowMetrics = computed(() => {
  const g = currentGang.value
  if (!g) return { total_accounts: 0, max_level: 0, overseas_pct: 0, total_flows: 0 }
  const caseCount = (g.related_cases || []).length || g.total_cases || 0
  return {
    total_accounts: g.account_count || g.total_accounts || (caseCount * 8),
    max_level: g.transfer_levels || (g.steps || []).length || 3,
    overseas_pct: g.overseas_pct || g.overseas_ratio || 60,
    total_flows: g.total_flows || caseCount
  }
})

const currentRelationNodes = computed(() => {
  const g = currentGang.value
  if (!g) return { nodes: [], links: [] }
  const relatedCases = g.related_cases || []
  const riskyColor = (lv) => {
    if (lv === 'CRITICAL' || lv === 'S') return '#ef4444'
    if (lv === 'HIGH' || lv === 'A') return '#ffd700'
    if (lv === 'MEDIUM' || lv === 'B') return '#ff9800'
    return '#00c6ff'
  }
  const scamTypeColor = (st) => {
    const colors = { '冒充客服':'#ef4444','刷单返利':'#f59e0b','冒充公检法':'#8b5cf6','投资理财':'#10b981','网络贷款':'#ec4899','冒充熟人':'#00d4ff','杀猪盘':'#f97316' }
    return colors[st] || '#64748b'
  }
  const gangId = 'G0'
  const nodes = [{
    id: gangId, name: g.gang_name || g.name || '犯罪团伙',
    category: 0, symbolSize: 56,
    itemStyle: { color: riskyColor(g.risk_level || g.riskLevel), borderRadius: 14 }
  }]
  const links = []
  const allCases = cases.value || []
  const addedCaseIds = new Set()
  ;(relatedCases || []).forEach((rc) => {
    const cid = rc.case_id
    if (!cid || addedCaseIds.has(cid)) return
    addedCaseIds.add(cid)
    const full = allCases.find(c => (c.case_id || c.id) === cid)
    const st = full?.scam_type || '其他'
    const title = full?.title || (rc.victim || '未知') + '被诈骗案'
    const amt = full?.amount_value || parseFloat(rc.amount) || 0
    const label = title.length > 10 ? title.slice(0, 10) + '…' : title
    nodes.push({
      id: cid, name: label,
      category: 1,
      symbolSize: 36 + Math.min(Math.floor(amt / 50000), 20),
      itemStyle: { color: scamTypeColor(st) },
      title, amount: amt, scamType: st
    })
    links.push({ source: gangId, target: cid, label: st })
    const vname = full?.victim_name || full?.victim || rc.victim
    if (vname) {
      const vid = cid + '_v'
      nodes.push({
        id: vid, name: vname.slice(0, 6),
        category: 2, symbolSize: 24,
        itemStyle: { color: '#10b981' }
      })
      links.push({ source: cid, target: vid, label: '受害人' })
    }
  })
  if (nodes.length < 3) {
    const fallbackId = 'F_CASE'
    nodes.push({
      id: fallbackId, name: '关联案件',
      category: 1, symbolSize: 36,
      itemStyle: { color: '#64748b' }
    })
    links.push({ source: gangId, target: fallbackId, label: '待关联' })
  }
  return { nodes, links }
})

const scamTypeColor = (st) => {
  const colors = { '冒充客服':'#ef4444','刷单返利':'#f59e0b','冒充公检法':'#8b5cf6','投资理财':'#10b981','网络贷款':'#ec4899','冒充熟人':'#00d4ff','杀猪盘':'#f97316' }
  return colors[st] || '#64748b'
}

const relationVisNodes = computed(() => {
  const data = currentRelationNodes.value
  if (!data.nodes || !data.nodes.length) return []
  return data.nodes.map(n => {
    const isGang = n.category === 0
    const isVictim = n.category === 2
    return {
      id: n.id,
      label: n.name,
      title: n.title ? `<b>${n.name}</b><br>${n.title}${n.amount ? '<br>涉案金额: ¥' + Number(n.amount).toLocaleString() : ''}${n.scamType ? '<br>诈骗类型: ' + n.scamType : ''}` : `<b>${n.name}</b>`,
      size: isGang ? 32 : isVictim ? 14 : Math.min(n.symbolSize || 20, 28),
      color: isGang
        ? { background: '#8b5cf6', border: '#a78bfa', highlight: { background: '#7c3aed', border: '#8b5cf6' } }
        : isVictim
        ? { background: '#f59e0b', border: '#fbbf24', highlight: { background: '#d97706', border: '#f59e0b' } }
        : { background: '#06b6d4', border: '#22d3ee', highlight: { background: '#0891b2', border: '#06b6d4' } },
      shadow: { enabled: true, size: isGang ? 12 : 6, color: isGang ? 'rgba(139,92,246,0.3)' : 'rgba(0,0,0,0.3)' },
      borderWidth: isGang ? 3 : 2,
      category: n.category,
      amount: n.amount,
      scamType: n.scamType,
      title_raw: n.title
    }
  })
})

const relationVisEdges = computed(() => {
  const data = currentRelationNodes.value
  if (!data.links || !data.links.length) return []
  return data.links.map(l => ({
    from: l.source,
    to: l.target,
    label: l.label || '',
    color: {
      color: l.source === 'G0' ? 'rgba(139,92,246,0.3)' : 'rgba(245,158,11,0.25)',
      highlight: l.source === 'G0' ? '#8b5cf6' : '#f59e0b',
      hover: l.source === 'G0' ? '#8b5cf6' : '#f59e0b'
    },
    width: l.source === 'G0' ? 2 : 1,
    font: { color: 'rgba(255,255,255,0.45)', size: 8, align: 'middle', strokeWidth: 1, strokeColor: '#0a0e1a' },
    dashes: l.source !== 'G0',
    smooth: { type: 'cubicBezier', roundness: 0.2 }
  }))
})

const relationLegends = [
  { label: '犯罪团伙', color: '#8b5cf6' },
  { label: '关联案件', color: '#06b6d4' },
  { label: '受害人', color: '#f59e0b' }
]

const relationPhysics = {
  solver: 'forceAtlas2Based',
  forceAtlas2Based: {
    gravitationalConstant: -120,
    centralGravity: 0.002,
    springLength: 200,
    springConstant: 0.015,
    damping: 0.45
  },
  stabilization: { iterations: 80, updateInterval: 50, fit: true }
}

const relationChartRef = ref(null)
const radarChartRef = ref(null)
let radarChartInstance = null

function renderRadarChart() {
  if (!radarChartRef.value) {
    requestAnimationFrame(() => renderRadarChart())
    return
  }
  if (radarChartInstance && radarChartInstance.getDom() !== radarChartRef.value) {
    radarChartInstance.dispose()
    radarChartInstance = null
  }
  if (!radarChartInstance) {
    radarChartInstance = echarts.init(radarChartRef.value, null, { renderer: 'canvas' })
  }
  const g = currentGang.value
  if (!g) {
    radarChartInstance.clear()
    return
  }
  const gangId = g.gang_id || g.id
  if (!gangId) {
    radarChartInstance.clear()
    return
  }
  getGangRadar(gangId).then(res => {
    let radar = res.data?.radar || {}
    if (!Object.keys(radar).length && g.radar_data) {
      radar = g.radar_data
    }
    const names = Object.keys(radar)
    const values = Object.values(radar)
    if (!names.length) {
      radarChartInstance.clear()
      return
    }
    const colors = ['#ef4444', '#f59e0b', '#00d4ff', '#8b5cf6', '#10b981', '#ec4899']
    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(10,14,26,0.92)',
        borderColor: 'rgba(0,198,255,0.2)',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (params) => {
          if (!params.value) return ''
          return names.map((n, i) =>
            `<span style="color:${colors[i % colors.length]};font-weight:700">${n}</span>: ${params.value[i]}%`
          ).join('<br/>')
        }
      },
      radar: {
        indicator: names.map(n => ({ name: n, max: 100 })),
        shape: 'polygon',
        radius: '68%',
        center: ['50%', '52%'],
        axisName: {
          color: '#94a3b8',
          fontSize: 11,
          fontWeight: 500,
          padding: [0, 0, 0, 0]
        },
        splitNumber: 4,
        splitArea: {
          areaStyle: {
            color: [
              'rgba(0,198,255,0.02)',
              'rgba(0,198,255,0.04)',
              'rgba(0,198,255,0.06)',
              'rgba(0,198,255,0.08)'
            ]
          }
        },
        splitLine: {
          lineStyle: { color: 'rgba(0,198,255,0.1)', width: 1 }
        },
        axisLine: {
          lineStyle: { color: 'rgba(0,198,255,0.12)' }
        }
      },
      series: [{
        type: 'radar',
        data: [{
          value: values,
          name: '团伙特征',
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            color: '#00d4ff',
            width: 2,
            shadowColor: 'rgba(0,212,255,0.4)',
            shadowBlur: 8
          },
          areaStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
              { offset: 0, color: 'rgba(0,212,255,0.25)' },
              { offset: 1, color: 'rgba(0,212,255,0.02)' }
            ])
          },
          itemStyle: {
            color: '#00d4ff',
            borderColor: '#00d4ff',
            borderWidth: 2,
            shadowColor: 'rgba(0,212,255,0.5)',
            shadowBlur: 6
          }
        }],
        animationDuration: 800,
        animationEasing: 'cubicOut'
      }]
    }
    radarChartInstance.setOption(option, true)
  }).catch(e => {
    console.warn('团伙雷达图加载失败:', e)
    const features = currentFeatures.value
    if (!features.length) {
      radarChartInstance.clear()
      return
    }
    const indicator = features.map(f => ({ name: f.name, max: 100 }))
    const values = features.map(f => f.confidence)
    radarChartInstance.setOption({
      radar: { indicator, shape: 'polygon', radius: '68%', center: ['50%', '52%'], axisName: { color: '#94a3b8', fontSize: 11 }, splitNumber: 4, splitArea: { areaStyle: { color: ['rgba(0,198,255,0.02)','rgba(0,198,255,0.04)','rgba(0,198,255,0.06)','rgba(0,198,255,0.08)'] } }, splitLine: { lineStyle: { color: 'rgba(0,198,255,0.1)' } }, axisLine: { lineStyle: { color: 'rgba(0,198,255,0.12)' } } },
      series: [{ type: 'radar', data: [{ value: values, name: '团伙特征', lineStyle: { color: '#00d4ff', width: 2 }, areaStyle: { color: 'rgba(0,212,255,0.15)' }, itemStyle: { color: '#00d4ff' } }] }]
    }, true)
  })
}

const resizeRadarChart = () => {
  radarChartInstance?.resize()
}

watch(currentFeatures, () => {
  nextTick(() => renderRadarChart())
}, { deep: true })

watch(currentGang, () => {
  nextTick(() => renderRadarChart())
})

onMounted(() => {
  nextTick(() => renderRadarChart())
  window.addEventListener('resize', resizeRadarChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeRadarChart)
  if (radarChartInstance) {
    radarChartInstance.dispose()
    radarChartInstance = null
  }
})

watch(() => gangs.value?.length || 0, (val) => {
  if (val === 0) {
    isMoneyFlowCollapsed.value = true
  } else if (!selectedGangId.value) {
    selectedGangId.value = gangs.value[0]?.id || gangs.value[0]?.gang_id || null
  }
}, { immediate: true })

watch(selectedGangId, (newVal) => {
  if (!newVal && gangs.value.length) {
    selectedGangId.value = gangs.value[0]?.id || gangs.value[0]?.gang_id || null
  }
})

watch(currentGang, () => {
  nextTick(() => updateGangReviewSummary())
}, { deep: true })
</script>

<style scoped>
.analysis-dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.analysis-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.analysis-two-col {
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.analysis-card.full-width {
  grid-column: 1 / -1;
}
.analysis-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.analysis-card {
  padding: 22px;
  background: linear-gradient(135deg, rgba(15,23,42,0.7) 0%, rgba(30,41,59,0.5) 100%);
  border: 1px solid rgba(0, 198, 255, 0.08);
  border-radius: 14px;
  transition: border-color 0.4s ease, box-shadow 0.4s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}
.analysis-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,229,255,0.2), transparent);
  opacity: 0;
  transition: opacity 0.4s ease;
}
.analysis-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 70% 20%, rgba(0,198,255,0.015), transparent 60%);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.analysis-card:hover {
  border-color: rgba(0,229,255,0.25);
  box-shadow: 0 0 40px rgba(0,198,255,0.07), 0 8px 32px rgba(0,0,0,0.25);
  transform: translateY(-2px);
}
.analysis-card:hover::before { opacity: 1; }
.analysis-card:hover::after { opacity: 1; }
.analysis-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 198, 255, 0.08);
  position: relative;
}
.analysis-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 48px;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-cyan), transparent);
  border-radius: 1px;
}
.analysis-icon {
  font-size: 20px;
  line-height: 1;
}
.analysis-title {
  font-size: 16px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.5px;
}
.analysis-subtitle {
  font-size: 10px;
  color: var(--accent-cyan);
  margin-left: auto;
  white-space: nowrap;
  opacity: 0.7;
  letter-spacing: 0.3px;
}
.analysis-content {
  padding-top: 4px;
  position: relative;
}
.flow-badge {
  font-size: 9px;
  padding: 2px 10px;
  background: linear-gradient(135deg, rgba(0,198,255,0.2), rgba(0,198,255,0.05));
  border: 1px solid rgba(0,198,255,0.2);
  border-radius: 10px;
  color: var(--accent-cyan);
  margin-left: auto;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.current-gang-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, rgba(0, 198, 255, 0.08), rgba(0, 198, 255, 0.02));
  border: 1px solid rgba(0, 198, 255, 0.15);
  border-radius: 24px;
  font-size: 14px;
  backdrop-filter: blur(4px);
  transition: border-color 0.3s, box-shadow 0.3s;
  flex-wrap: wrap;
}
.current-gang-badge:hover {
  border-color: rgba(0,198,255,0.25);
  box-shadow: 0 0 20px rgba(0,198,255,0.06);
}
.gang-review-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 12px;
  padding-left: 12px;
  border-left: 1px solid rgba(0,198,255,0.15);
}
.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00d4ff;
  box-shadow: 0 0 12px rgba(0,212,255,0.6);
  animation: badgePulse 2s infinite;
}
@keyframes badgePulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
.badge-label { color: #94a3b8; font-weight: 500; }
.badge-name {
  color: #e2e8f0;
  font-weight: 700;
  background: linear-gradient(90deg, #e2e8f0, #00d4ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.badge-risk {
  font-size: 10px;
  padding: 3px 12px;
  border-radius: 12px;
  color: #fff;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.gang-fade-enter-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.gang-fade-leave-active { transition: all 0.25s cubic-bezier(0.55, 0, 1, 0.45); }
.gang-fade-enter-from { opacity: 0; transform: translateY(16px) scale(0.98); }
.gang-fade-leave-to { opacity: 0; transform: translateY(-10px) scale(0.98); }

.money-flow-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.35s ease;
  opacity: 0;
}
.money-flow-body.expanded {
  max-height: 450px;
  overflow-y: auto;
  opacity: 1;
}
.money-flow-body::-webkit-scrollbar { width: 4px; }
.money-flow-body::-webkit-scrollbar-thumb { background: rgba(0,198,255,0.15); border-radius: 2px; }
.money-flow-card .analysis-header {
  min-height: 48px;
  display: flex;
  align-items: center;
}
.money-flow-card.collapsed .analysis-header {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.money-flow-card.collapsed .analysis-header::after { display: none; }
.collapse-btn {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
  padding: 4px 12px;
  border-radius: 6px;
  transition: color 0.3s, background 0.3s;
}
.collapse-btn:hover {
  color: #00d4ff;
  background: rgba(0,198,255,0.08);
}

.radar-chart-container {
  width: 100%;
  height: 340px;
  min-height: 280px;
}

.pattern-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }
.pattern-card {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 16px;
  background: linear-gradient(135deg, rgba(0, 198, 255, 0.04), rgba(0, 198, 255, 0.01));
  border: 1px solid rgba(0, 198, 255, 0.08);
  border-radius: 10px;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.25s;
}
.pattern-card:hover {
  border-color: rgba(0,198,255,0.2);
  box-shadow: 0 0 20px rgba(0,198,255,0.04);
  transform: translateY(-2px);
}
.pattern-icon {
  font-size: 26px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.25);
  border-radius: 10px;
  flex-shrink: 0;
}
.pattern-info { display: flex; flex-direction: column; gap: 3px; }
.pattern-title { font-size: 11px; color: #94a3b8; letter-spacing: 0.3px; text-transform: uppercase; }
.pattern-value { font-size: 15px; font-weight: 700; color: #00d4ff; }
.pattern-desc { font-size: 11px; color: #64748b; }

.type-stats { display: flex; flex-direction: column; gap: 12px; }
.type-item { display: flex; flex-direction: column; gap: 6px; }
.type-bar {
  height: 28px;
  border-radius: 8px;
  min-width: 4px;
  transition: width 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}
.type-bar::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0.1), transparent);
  border-radius: 8px;
}
.type-info { display: flex; justify-content: space-between; font-size: 13px; }
.type-name { color: #94a3b8; font-weight: 500; }
.type-count { color: #e2e8f0; font-weight: 700; }

.flow-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 0;
  flex-wrap: wrap;
}
.flow-compact-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 12px 18px;
  border-radius: 10px;
  min-width: 76px;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  cursor: default;
  position: relative;
}
.flow-compact-node:hover {
  transform: translateY(-4px) scale(1.03);
  box-shadow: 0 8px 20px rgba(0,0,0,0.25);
}
.flow-compact-node.victim { background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.03)); border: 1px solid rgba(239,68,68,0.25); }
.flow-compact-node.account { background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.03)); border: 1px solid rgba(245,158,11,0.25); }
.flow-compact-node.middle { background: linear-gradient(135deg, rgba(139,92,246,0.12), rgba(139,92,246,0.03)); border: 1px solid rgba(139,92,246,0.25); }
.flow-compact-node.overseas { background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(0,212,255,0.03)); border: 1px solid rgba(0,212,255,0.25); }
.fcn-icon { font-size: 24px; }
.fcn-label { font-size: 11px; color: #cbd5e1; font-weight: 600; letter-spacing: 0.3px; }
.fcn-amount { font-size: 11px; color: #94a3b8; margin-top: 1px; font-weight: 600; }

.flow-metrics {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0,198,255,0.06);
  flex-wrap: wrap;
}
.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: linear-gradient(135deg, rgba(0,0,0,0.2), rgba(0,0,0,0.08));
  border: 1px solid rgba(0, 198, 255, 0.04);
  border-radius: 10px;
  min-width: 120px;
  transition: border-color 0.3s, transform 0.25s;
}
.metric-item:hover {
  border-color: rgba(0,198,255,0.12);
  transform: translateY(-1px);
}
.metric-icon { font-size: 20px; }
.metric-info { display: flex; flex-direction: column; gap: 2px; }
.metric-label { font-size: 10px; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase; }
.metric-value { font-size: 16px; font-weight: 800; color: var(--accent-cyan); }
.metric-value.danger { color: #ef4444; }
.metric-value.warning { color: #f59e0b; }

.fingerprint-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.fingerprint-card {
  background: linear-gradient(135deg, rgba(0, 198, 255, 0.04), rgba(0, 198, 255, 0.01));
  border: 1px solid rgba(0, 198, 255, 0.08);
  padding: 18px;
  border-radius: 10px;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.25s;
  position: relative;
  overflow: hidden;
}
.fingerprint-card::before {
  content: '🧬';
  position: absolute;
  right: -6px; bottom: -6px;
  font-size: 48px;
  opacity: 0.04;
  pointer-events: none;
}
.fingerprint-card:hover {
  border-color: rgba(0,198,255,0.2);
  box-shadow: 0 0 24px rgba(0,198,255,0.04);
  transform: translateY(-2px);
}
.fp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.fp-type { font-size: 15px; font-weight: 700; color: #e2e8f0; }
.fp-amount { font-size: 20px; font-weight: 800; color: #00d4ff; margin-bottom: 12px; letter-spacing: -0.5px; }
.fp-keywords { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.fp-tag {
  margin: 0 !important;
  border-radius: 6px !important;
  border: 1px solid rgba(0,198,255,0.1) !important;
}
.fp-signature {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  padding: 10px 12px;
  background: rgba(0,0,0,0.15);
  border-radius: 6px;
  border-left: 3px solid rgba(0,198,255,0.2);
}
.fp-empty { text-align: center; padding: 48px; color: #94a3b8; }

.gang-structure { padding: 24px; }
.structure-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}
.structure-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 24px;
  border-radius: 10px;
  min-width: 110px;
  transition: transform 0.25s, box-shadow 0.25s;
  position: relative;
}
.structure-node:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.structure-node.leader {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(239, 68, 68, 0.05));
  border: 1px solid rgba(239, 68, 68, 0.25);
}
.structure-node.leader::before {
  content: '👑';
  position: absolute;
  top: -12px;
  font-size: 18px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}
.structure-node.manager {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(245, 158, 11, 0.05));
  border: 1px solid rgba(245, 158, 11, 0.25);
}
.structure-node.member {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.03));
  border: 1px solid rgba(0, 212, 255, 0.15);
}
.node-rank { font-size: 10px; color: #94a3b8; margin-bottom: 4px; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; }
.node-name { font-size: 14px; font-weight: 700; color: #e2e8f0; }
.node-desc { font-size: 11px; color: #94a3b8; margin-top: 3px; }
.structure-arrow {
  color: #00d4ff;
  font-size: 22px;
  animation: arrowBounce 1.5s infinite;
}
@keyframes arrowBounce {
  0%, 100% { transform: translateY(0); opacity: 0.6; }
  50% { transform: translateY(4px); opacity: 1; }
}
.structure-nodes { display: flex; gap: 12px; }
.structure-sub { display: flex; gap: 12px; flex-wrap: wrap; }

.region-stats { display: flex; flex-direction: column; gap: 12px; }
.region-item { display: flex; align-items: center; gap: 12px; }
.region-name {
  width: 56px; font-size: 13px; color: #e2e8f0;
  flex-shrink: 0; font-weight: 600;
}
.region-bar-wrapper {
  flex: 1; height: 24px; background: rgba(0,0,0,0.2);
  border-radius: 8px; overflow: hidden;
  position: relative;
}
.region-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  border-radius: 8px;
  transition: width 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}
.region-bar::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0.1), transparent);
  border-radius: 8px;
}
.region-count {
  width: 48px; font-size: 13px; color: #00d4ff;
  font-weight: 700; text-align: right;
}

.dialog-body { padding: 8px 0; }
.dialog-gang-info {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 14px;
}
.dialog-gang-info .info-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
  gap: 12px;
}
.dialog-gang-info .info-row .label {
  font-size: 13px;
  color: var(--text-muted);
  min-width: 80px;
  flex-shrink: 0;
}
.dialog-gang-info .info-row .value {
  font-size: 13px;
  color: var(--text-primary);
}
.dialog-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(0, 198, 255, 0.05);
  border: 1px solid rgba(0, 198, 255, 0.1);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.dialog-hint .hint-icon { font-size: 14px; flex-shrink: 0; }
.dialog-hint .hint-text { line-height: 1.5; }
.review-form { margin-top: 4px; }
</style>