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

          <div class="analysis-dashboard">
            <div class="analysis-row analysis-two-col">
              <div class="analysis-col">
                <div class="analysis-card">
                  <div class="analysis-header">
                    <span class="analysis-icon">🎯</span>
                    <span class="analysis-title">团伙特征提取</span>
                    <span class="analysis-subtitle">AI智能分析</span>
                  </div>
                  <div class="analysis-content">
                    <div class="feature-grid">
                      <div v-for="(feature, idx) in features" :key="feature.name" class="feature-card" :style="{ '--feature-color': feature.color }">
                        <div class="feature-icon-wrap">
                          <span class="feature-icon">{{ getFeatureIcon(idx) }}</span>
                        </div>
                        <div class="feature-info">
                          <div class="feature-header">
                            <span class="feature-name">{{ feature.name }}</span>
                            <span class="feature-value" :style="{ color: feature.color }">{{ feature.confidence }}%</span>
                          </div>
                          <span class="feature-desc">{{ feature.desc }}</span>
                        </div>
                        <div class="feature-bar-wrap">
                          <div class="feature-bar" :style="{ width: feature.confidence + '%', background: feature.color }"></div>
                        </div>
                      </div>
                    </div>
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
                          <span class="pattern-value">{{ currentGangPattern.scamType || '综合诈骗' }}</span>
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
                      <div class="type-item" v-for="(item, idx) in caseTypeStats" :key="idx">
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
                <div class="analysis-card money-flow-card" :class="{ collapsed: isMoneyFlowCollapsed || !currentGang }">
                  <div class="analysis-header">
                    <span class="analysis-icon">💰</span>
                    <span class="analysis-title">资金流向追踪</span>
                    <span class="flow-badge">AI分析</span>
                    <el-button link class="collapse-btn" @click="isMoneyFlowCollapsed = !isMoneyFlowCollapsed">
                      {{ isMoneyFlowCollapsed || !currentGang ? '展开' : '折叠' }}
                    </el-button>
                  </div>
                  <div class="money-flow-body" :class="{ expanded: !(isMoneyFlowCollapsed || !currentGang) }">
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
                            <span class="metric-value">{{ flowMetrics.max_level || 3 }}层</span>
                          </div>
                        </div>
                        <div class="metric-item">
                          <div class="metric-icon">🌏</div>
                          <div class="metric-info">
                            <span class="metric-label">境外流向</span>
                            <span class="metric-value warning">{{ flowMetrics.overseas_pct || 85 }}%</span>
                          </div>
                        </div>
                        <div class="metric-item">
                          <div class="metric-icon">🏦</div>
                          <div class="metric-info">
                            <span class="metric-label">涉案账户</span>
                            <span class="metric-value">{{ flowMetrics.total_accounts || 23 }}个</span>
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
                    <div v-if="semanticFingerprints.length" class="fingerprint-grid">
                      <div v-for="fp in semanticFingerprints" :key="fp.type" class="fingerprint-card">
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
                      <div class="region-item" v-for="(item, idx) in regionStats" :key="idx">
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
                        <span class="node-name">{{ currentGang.leader_name || currentGang.gang_name || '主犯' }}</span>
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
                            <span class="node-name">{{ m.name || m.member_name || m.role || '涉案人员' }}</span>
                            <span class="node-desc">{{ m.desc || m.role_desc || m.position || '参与作案' }}</span>
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
                </div>
                <div class="analysis-content relation-map">
                  <div class="relation-viz">
                    <div v-for="node in relationNodes" :key="node.id" class="rel-node" :class="node.type" :style="node.style">
                      <span class="rel-icon">{{ node.icon }}</span>
                      <span class="rel-label">{{ node.label }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const state = useAppState()
const {
  features, gangs, getFeatureIcon, caseTypeStats,
  regionStats, semanticFingerprints, relationNodes, flowMetrics,
  selectedGang
} = state

const selectedGangId = ref(null)
const isMoneyFlowCollapsed = ref(false)

watch(selectedGang, (g) => {
  if (g && (g.id || g.gang_id)) {
    selectedGangId.value = g.id || g.gang_id
  }
}, { immediate: true })

const currentGang = computed(() => {
  if (!selectedGangId.value || !gangs.value.length) return null
  return gangs.value.find(g => (g.id === selectedGangId.value || g.gang_id === selectedGangId.value)) || gangs.value[0]
})

const currentGangPattern = computed(() => {
  const g = currentGang.value
  if (!g) return { scamType: '', totalAmount: '0', caseCount: 0, riskColor: '#64748b', riskLabel: '未知' }
  const amount = g.total_amount || g.totalAmount || 0
  const fmtAmount = amount > 10000 ? (amount / 10000).toFixed(1).replace(/\.0$/, '') + '万' : (amount || 0) + ''
  const score = g.comprehensive_score || g.confidence || g.risk_score || 50
  const riskLabel = score >= 80 ? '高危' : score >= 60 ? '中危' : '低危'
  const riskColor = score >= 80 ? '#ef4444' : score >= 60 ? '#f59e0b' : '#10b981'
  const cases = g.related_cases || g.caseIds || g.cases || []
  return {
    scamType: g.gang_type || g.scam_type || g.type || '综合诈骗',
    totalAmount: fmtAmount,
    caseCount: cases.length || g.case_count || 1,
    riskColor,
    riskLabel
  }
})

const currentFlowPath = computed(() => {
  const g = currentGang.value
  if (!g) return []
  const path = [
    { type: 'victim', icon: '👤', label: '受害人', amount: g.victim_count ? g.victim_count + '人' : null },
    { type: 'account', icon: '💳', label: '涉案账户', amount: g.account_count ? g.account_count + '个' : null },
    { type: 'middle', icon: '🏦', label: '多层流转', amount: flowMetrics.value.max_level ? flowMetrics.value.max_level + '层' : null },
    { type: 'overseas', icon: '🌍', label: '境外', amount: flowMetrics.value.overseas_pct ? flowMetrics.value.overseas_pct + '%' : null },
  ]
  return path.filter(n => n.label)
})

const currentGangMembers = computed(() => {
  const g = currentGang.value
  const members = g.members || g.member_list || g.team_members || []
  if (members.length) return members.slice(0, 6)
  if (g.member_count || g.team_size) {
    const count = Math.min(parseInt(g.member_count || g.team_size) || 3, 6)
    return Array.from({ length: count }, (_, i) => ({
      name: g.roles?.[i] || `成员${i + 1}`,
      role_desc: g.role_descs?.[i] || (i === 0 ? '核心成员' : '参与作案')
    }))
  }
  return []
})

watch(() => gangs.value?.length || 0, (val) => {
  if (val === 0) isMoneyFlowCollapsed.value = true
  else if (!selectedGangId.value) selectedGangId.value = gangs.value[0]?.id || gangs.value[0]?.gang_id || null
}, { immediate: true })
</script>

<style scoped>
.analysis-two-col {
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.analysis-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.analysis-card {
  padding: 20px;
  transition: border-color 0.3s;
}
.analysis-card:hover {
  border-color: rgba(0,229,255,0.25);
}
.analysis-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}
.flow-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  flex-wrap: wrap;
}
.flow-compact-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border-radius: 8px;
  min-width: 72px;
  transition: transform 0.2s;
}
.flow-compact-node:hover { transform: translateY(-2px); }
.flow-compact-node.victim { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); }
.flow-compact-node.account { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
.flow-compact-node.middle { background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); }
.flow-compact-node.overseas { background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); }
.fcn-icon { font-size: 20px; }
.fcn-label { font-size: 11px; color: #cbd5e1; font-weight: 500; }
.fcn-amount { font-size: 10px; color: #64748b; }
.fcn-arrow { font-size: 16px; color: rgba(0,229,255,0.5); font-weight: bold; }
.flow-metrics { display: flex; gap: 16px; justify-content: center; margin-top: 14px; padding-top: 14px; border-top: 1px solid rgba(0,198,255,0.08); flex-wrap: wrap; }
.metric-item { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: rgba(0,0,0,0.15); border-radius: 8px; min-width: 120px; }
.metric-icon { font-size: 18px; }
.metric-info { display: flex; flex-direction: column; }
.metric-label { font-size: 10px; color: #64748b; letter-spacing: 0.3px; }
.metric-value { font-size: 15px; font-weight: 700; color: var(--accent-cyan); }
.metric-value.danger { color: #ef4444; }
.metric-value.warning { color: #f59e0b; }
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
.collapse-btn {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
  padding: 2px 8px;
}
.money-flow-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease, opacity 0.3s ease;
  opacity: 0;
}
.money-flow-body.expanded {
  max-height: 400px;
  overflow-y: auto;
  opacity: 1;
}
.fingerprint-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.fingerprint-card {
  background: rgba(0, 198, 255, 0.03) !important;
  border: 1px solid rgba(0, 198, 255, 0.1);
  padding: 16px;
  border-radius: 8px;
}
.fp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.fp-type {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}
.fp-amount {
  font-size: 18px;
  font-weight: 700;
  color: #00d4ff;
  margin-bottom: 10px;
}
.fp-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.fp-tag {
  margin: 0 !important;
}
.fp-signature {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}
.fp-empty {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}
.gang-structure {
  padding: 20px;
}
.structure-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.structure-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 20px;
  border-radius: 8px;
  min-width: 100px;
}
.structure-node.leader {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.structure-node.manager {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.structure-node.member {
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
}
.node-rank { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }
.node-name { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.node-desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.structure-arrow { color: #00d4ff; font-size: 20px; }
.structure-nodes { display: flex; gap: 10px; }
.structure-sub { display: flex; gap: 10px; flex-wrap: wrap; }
.pattern-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.pattern-card {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 14px; background: rgba(0, 198, 255, 0.03);
  border-radius: 8px; border: 1px solid rgba(0, 198, 255, 0.1);
}
.pattern-icon { font-size: 24px; }
.pattern-info { display: flex; flex-direction: column; gap: 2px; }
.pattern-title { font-size: 12px; color: #94a3b8; }
.pattern-value { font-size: 14px; font-weight: 600; color: #00d4ff; }
.pattern-desc { font-size: 11px; color: #94a3b8; }
</style>
