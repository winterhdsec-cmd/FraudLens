<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title">
        <span class="title-icon">🔔</span>
        预警中心
      </h2>
      <p class="section-desc">实时监控诈骗预警信息，快速响应处置</p>
    </div>
    <div class="header-right">
      <el-button size="small" @click="loadAlerts" :loading="alertsLoading">
        <span>🔄</span> 刷新
      </el-button>
    </div>
  </div>

  <div class="alert-filter-bar">
    <div class="filter-left">
      <span class="filter-label">置信度筛选:</span>
      <el-select v-model="confidenceFilter" size="small" style="width:160px">
        <el-option label="全部预警" value="all" />
        <el-option label="高危 (≥80%)" value="high" />
        <el-option label="中危 (≥60%)" value="medium" />
        <el-option label="低危 (<60%)" value="low" />
      </el-select>
    </div>
    <div class="filter-right">
      <span class="alert-count">共 {{ filteredAlerts.length }} 条预警</span>
      <span class="sort-indicator">按置信度降序排列</span>
    </div>
  </div>

  <div v-if="filteredAlerts.length" class="alerts-list">
    <div
      v-for="alert in filteredAlerts"
      :key="alert.id"
      class="alert-card"
      :class="[getSeverityClass(alert.confidence), { 'is-resolved': alert.resolved }]"
    >
      <div class="card-top">
        <div class="card-left">
          <div class="card-title-row">
            <h3 class="case-name">{{ getCaseTitle(alert.case_id) }}</h3>
            <el-tag
              v-if="alert.resolved"
              type="success"
              size="small"
              effect="dark"
            >已处置</el-tag>
            <el-tag
              v-else
              type="danger"
              size="small"
              effect="dark"
            >待处置</el-tag>
          </div>
          <div class="alert-meta-row">
            <el-tag :type="getAlertType(alert.confidence * 100)" size="small" effect="dark">
              {{ getConfidenceLabel(alert.confidence) }}
            </el-tag>
            <span class="meta-separator">|</span>
            <span class="alert-type-label">{{ getAlertTypeLabel(alert.alert_type) }}</span>
            <span class="meta-separator">|</span>
            <span class="case-id-ref">编号: {{ alert.case_id }}</span>
          </div>
        </div>
        <div class="card-right">
          <el-button
            size="small"
            type="primary"
            :loading="resolvingAlert === alert.id"
            @click="handleResolveAlert(alert.id)"
            :disabled="alert.resolved"
          ><span>✅</span> 处置</el-button>
        </div>
      </div>

      <div v-if="alert.matched_entities && alert.matched_entities.length" class="entities-section">
        <div class="entities-title">匹配实体:</div>
        <div class="entities-list">
          <div v-for="(entity, idx) in alert.matched_entities" :key="idx" class="entity-item">
            <span class="entity-icon">🔗</span>
            <span class="entity-text">{{ getEntityLabel(entity) }}</span>
          </div>
        </div>
      </div>

      <div class="confidence-section">
        <div class="confidence-header">
          <span class="confidence-title">置信度评分</span>
          <span class="confidence-value" :style="{ color: getConfidenceColor(alert.confidence * 100) }">
            {{ (alert.confidence * 100).toFixed(0) }}%
          </span>
        </div>
        <el-progress
          :percentage="Math.round(alert.confidence * 100)"
          :stroke-width="8"
          :color="getConfidenceColor(alert.confidence * 100)"
          :format="() => ''"
        />
      </div>

      <div class="card-footer">
        <div class="footer-left">
          <span class="footer-icon">🕐</span>
          <span class="footer-time">{{ formatTime(alert.created_at) }}</span>
        </div>
        <div v-if="alert.matched_case_id" class="footer-right">
          <span class="related-case-label">关联案件:</span>
          <span class="related-case-name">{{ getCaseTitle(alert.matched_case_id) }}</span>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="!alertsLoading" class="empty-state">
    <div class="empty-content">
      <div class="empty-icon">🔔</div>
      <h3 class="empty-title">暂无预警信息</h3>
      <p class="empty-desc">系统运行正常，暂无待处理的诈骗预警</p>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, alerts, alertsLoading, cases, getAlertType, getConfidenceColor, handleResolveAlert,
  loadAlerts, loading, resolvingAlert
} = state

onMounted(() => loadAlerts())

const getCaseTitle = (caseId) => {
  if (!caseId) return '未知案件'
  const found = cases.value?.find(c => c.id === caseId || c.case_id === caseId)
  return found?.title || caseId
}

const alertTypeLabels = {
  phone_match: '手机号匹配',
  bank_match: '银行卡匹配',
  ip_match: 'IP地址匹配',
  email_match: '邮箱匹配',
  id_card_match: '身份证匹配',
  device_match: '设备指纹匹配',
  face_match: '人脸匹配',
  voice_match: '声纹匹配',
  address_match: '地址匹配',
  social_match: '社交账号匹配',
  wechat_match: '微信账号匹配',
  alipay_match: '支付宝匹配',
  account_match: '账号匹配',
  transaction_match: '交易匹配',
  behavior_match: '行为匹配',
  location_match: '位置匹配',
  gang_match: '团伙匹配',
  case_match: '案件串并',
  similar_case: '相似案件'
}

const getAlertTypeLabel = (type) => {
  return alertTypeLabels[type] || type || '未知类型'
}

const getEntityLabel = (entity) => {
  if (!entity) return ''
  if (entity.includes('****')) {
    if (entity.length >= 11 && /^\d/.test(entity)) return `匹配电话号码: ${entity}`
    if (entity.includes('@')) return `匹配邮箱: ${entity}`
    return `匹配: ${entity}`
  }
  if (/^\d{11}$/.test(entity)) return `匹配电话号码: ${entity}`
  if (entity.includes('@')) return `匹配邮箱: ${entity}`
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(entity)) return `匹配IP地址: ${entity}`
  if (/^\d{16,19}$/.test(entity)) return `匹配银行卡: ${entity}`
  return `匹配: ${entity}`
}

const getConfidenceLabel = (confidence) => {
  const pct = confidence * 100
  if (pct >= 80) return '高危'
  if (pct >= 60) return '中危'
  return '低危'
}

const getSeverityClass = (confidence) => {
  const pct = confidence * 100
  if (pct >= 80) return 'severity-high'
  if (pct >= 60) return 'severity-medium'
  return 'severity-low'
}

const confidenceFilter = ref('all')

const filteredAlerts = computed(() => {
  let list = [...alerts.value]
  if (confidenceFilter.value === 'high') {
    list = list.filter(a => a.confidence * 100 >= 80)
  } else if (confidenceFilter.value === 'medium') {
    list = list.filter(a => a.confidence * 100 >= 60 && a.confidence * 100 < 80)
  } else if (confidenceFilter.value === 'low') {
    list = list.filter(a => a.confidence * 100 < 60)
  }
  list.sort((a, b) => b.confidence - a.confidence)
  return list
})

const formatTime = (t) => {
  if (!t) return ''
  return t.replace('T', ' ')
}
</script>

<style scoped>
.alert-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
}
.filter-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.filter-label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.filter-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.alert-count {
  font-size: 13px;
  color: var(--text-muted);
}
.sort-indicator {
  font-size: 12px;
  color: var(--text-muted);
  padding: 3px 10px;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid rgba(0, 198, 255, 0.15);
  border-radius: 6px;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.alert-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}
.alert-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  border-radius: 12px 0 0 12px;
}
.alert-card.severity-high::before {
  background: #ef4444;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.3);
}
.alert-card.severity-medium::before {
  background: #f59e0b;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
}
.alert-card.severity-low::before {
  background: #00d4ff;
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.15);
}
.alert-card.is-resolved {
  opacity: 0.65;
}
.alert-card.is-resolved::before {
  background: #10b981;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}
.alert-card:hover {
  border-color: rgba(0, 198, 255, 0.3);
  box-shadow: 0 0 24px rgba(0, 198, 255, 0.06);
  transform: translateY(-1px);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 24px 0 28px;
}
.card-left {
  flex: 1;
  min-width: 0;
}
.card-right {
  flex-shrink: 0;
  margin-left: 16px;
  padding-top: 2px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.case-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
}

.alert-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.meta-separator {
  color: var(--text-muted);
  font-size: 12px;
  opacity: 0.4;
}
.alert-type-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.case-id-ref {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

.entities-section {
  padding: 12px 24px 4px 28px;
}
.entities-title {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.entities-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.entity-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(0, 198, 255, 0.08);
  border-radius: 6px;
  font-size: 12px;
}
.entity-icon {
  font-size: 11px;
  opacity: 0.6;
}
.entity-text {
  color: var(--text-secondary);
}

.confidence-section {
  padding: 12px 24px 8px 28px;
}
.confidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.confidence-title {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.confidence-section .confidence-value {
  font-size: 14px;
  font-weight: 700;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 24px 16px 28px;
  border-top: 1px solid var(--border-primary);
  margin-top: 4px;
}
.footer-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.footer-icon {
  font-size: 12px;
  opacity: 0.6;
}
.footer-time {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.footer-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.related-case-label {
  font-size: 12px;
  color: var(--text-muted);
}
.related-case-name {
  font-size: 12px;
  color: var(--accent-cyan);
  font-weight: 500;
}
</style>
