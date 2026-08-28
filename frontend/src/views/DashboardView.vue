<template>
<div class="view-section">
          <SectionHeader icon="DataAnalysis" title="数据看板" desc="系统运行数据总览，实时监控诈骗态势">
            <el-button size="small" @click="loadDashboard" :loading="dashboardLoading">
              <el-icon><Refresh /></el-icon> 刷新数据
            </el-button>
          </SectionHeader>

          <div class="quick-nav">
            <div class="quick-card" @click="router.push({ name: 'input' })">
              <el-icon class="qc-icon"><EditPen /></el-icon>
              <div class="qc-text"><span class="qc-title">文本录入</span><span class="qc-desc">粘贴案情一键研判</span></div>
            </div>
            <div class="quick-card" @click="router.push({ name: 'upload' })">
              <el-icon class="qc-icon"><Upload /></el-icon>
              <div class="qc-text"><span class="qc-title">文件上传</span><span class="qc-desc">截图/转账/文档取证</span></div>
            </div>
            <div class="quick-card" @click="router.push({ name: 'overview' })">
              <el-icon class="qc-icon"><Files /></el-icon>
              <div class="qc-text"><span class="qc-title">案件管理</span><span class="qc-desc">查看全部录入案件</span></div>
            </div>
            <div class="quick-card" @click="router.push({ name: 'groups' })">
              <el-icon class="qc-icon"><User /></el-icon>
              <div class="qc-text"><span class="qc-title">团伙画像</span><span class="qc-desc">组织架构与特征</span></div>
            </div>
            <div class="quick-card" @click="router.push({ name: 'capital-flow' })">
              <el-icon class="qc-icon"><Money /></el-icon>
              <div class="qc-text"><span class="qc-title">资金流向</span><span class="qc-desc">层级追踪资金链路</span></div>
            </div>
            <div class="quick-card" @click="router.push({ name: 'chat' })">
              <el-icon class="qc-icon"><ChatDotRound /></el-icon>
              <div class="qc-text"><span class="qc-title">AI 助手</span><span class="qc-desc">案情问答与检索</span></div>
            </div>
          </div>

          <div class="stats-overview">
            <div class="stat-card">
              <div class="stat-icon-wrapper danger">
                <el-icon class="stat-icon"><Files /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_cases ?? '-' }}</div>
                <div class="stat-label">案件总数</div>
                <div class="stat-trend up">
                  <span>累计录入</span>
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon-wrapper warning">
                <el-icon class="stat-icon"><User /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_gangs ?? '-' }}</div>
                <div class="stat-label">涉案团伙</div>
                <div class="stat-trend up">
                  <span>已识别</span>
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon-wrapper success">
                <el-icon class="stat-icon"><Money /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_amount_formatted ?? dashboardData.total_amount ?? '-' }}</div>
                <div class="stat-label">涉案金额</div>
                <div class="stat-trend">
                  <span>累计金额</span>
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon-wrapper info">
                <el-icon class="stat-icon"><Bell /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.active_alerts ?? '-' }}</div>
                <div class="stat-label">活跃预警</div>
                <div class="stat-trend up">
                  <span>待处理</span>
                </div>
              </div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">风险等级分布</span>
              </div>
              <div class="chart-content" ref="dashboardRiskChartRef"></div>
            </div>
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">案件状态分布</span>
              </div>
              <div class="chart-content" ref="dashboardStatusChartRef"></div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">诈骗类型排行</span>
              </div>
              <div class="chart-content" ref="dashboardBarChartRef"></div>
            </div>
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">月度趋势</span>
              </div>
              <div class="chart-content" ref="dashboardTrendChartRef"></div>
            </div>
          </div>

          <div class="overview-charts" v-show="gangRadarData.length">
            <div class="chart-card chart-card-wide">
              <div class="chart-header">
                <span class="chart-title">团伙能力画像</span>
                <span class="chart-sub">基于 AI 语义聚类计算的 7 维核心能力</span>
              </div>
              <div class="chart-content" ref="dashboardRadarChartRef"></div>
            </div>
          </div>

          <template v-if="dashboardData.recent_cases?.length">
            <div class="recent-cases-section">
              <div class="section-sub-header">
                <h3 class="sub-title">
                  <el-icon class="sub-icon"><Files /></el-icon>
                  最新案件
                </h3>
                <div v-if="hasFilter" class="filter-tag">
                  <span>已筛选：{{ dashboardRiskFilter || '' }}{{ dashboardStatusFilter ? ' / ' + dashboardStatusFilter : '' }}</span>
                  <el-icon class="filter-clear" @click="clearFilters"><Close /></el-icon>
                </div>
              </div>
              <div class="cases-table">
                <el-table :data="filteredRecentCases" style="width: 100%" @row-click="viewCaseFromDashboard" :highlight-current-row="true">
                  <el-table-column prop="case_id" label="案件编号" width="100" />
                  <el-table-column prop="title" label="案件名称" />
                  <el-table-column prop="scam_type" label="案件类型" width="100">
                    <template #default="scope">
                      <el-tag type="info" size="small">{{ scope.row.scam_type }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="amount" label="涉案金额" width="120">
                    <template #default="scope">
                      {{ formatAmountRaw(Number(scope.row.amount_value) || Number(scope.row.amount) || 0) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="案件状态" width="100">
                    <template #default="scope">
                      <el-tag :type="scope.row.status === '已立案' ? 'warning' : scope.row.status === '侦办中' ? 'primary' : 'success'" size="small">
                        {{ scope.row.status }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="created_at" label="立案时间" width="120">
                    <template #default="scope">
                      {{ (scope.row.date || (scope.row.created_at || '')).slice(0, 10) || '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="100">
                    <template #default="scope">
                      <el-button size="small" type="primary" @click="viewCaseFromDashboard(scope.row)">
                        查看
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>

            <div class="data-source-bar">
              <span class="ds-icon">ℹ️</span>
              <span class="ds-text">数据来源：{{ dashboardData.data_source || '系统实时计算' }}</span>
              <span class="ds-separator">|</span>
              <span class="ds-text">更新频率：{{ dashboardData.data_update_frequency || '实时' }}</span>
              <span class="ds-separator">|</span>
              <span class="ds-text">更新时间：{{ dashboardData.data_updated_at ? formatTimestamp(dashboardData.data_updated_at) : '-' }}</span>
            </div>
          </template>

          <div v-else-if="!dashboardLoading" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon"><el-icon :size="64"><DataAnalysis /></el-icon></div>
              <h3 class="empty-title">暂无看板数据</h3>
              <p class="empty-desc">请先录入案情数据，系统将自动生成数据看板</p>
              <el-button type="primary" size="large" @click="router.push({ name: 'input' })">
                <el-icon><EditPen /></el-icon> 前往录入
              </el-button>
            </div>
          </div>
        </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
import { formatAmountRaw } from '../composables/utils.js'
import SectionHeader from '../components/SectionHeader.vue'
const router = useRouter()
const state = useAppState()
const {
  activeMenu, alerts, cases, dashboardBarChartRef, dashboardData, dashboardLoading,
  dashboardRadarChartRef, dashboardRiskChartRef, dashboardStatusChartRef, dashboardTrendChartRef, gangs, loadDashboard, loading,
  dashboardRiskFilter, dashboardStatusFilter,
  viewCaseFromDashboard
} = state

const gangRadarData = computed(() => dashboardData.value.gang_radar || [])

// 饼图联动：按风险等级 / 案件状态过滤最新案件
const filteredRecentCases = computed(() => {
  const list = dashboardData.value.recent_cases || []
  const rf = dashboardRiskFilter.value
  const sf = dashboardStatusFilter.value
  if (!rf && !sf) return list
  return list.filter(c => {
    const okRisk = !rf || (c.risk_level === rf || c.riskLabel === rf || c.risk_label === rf)
    const okStatus = !sf || (c.status === sf)
    return okRisk && okStatus
  })
})
const hasFilter = computed(() => !!(dashboardRiskFilter.value || dashboardStatusFilter.value))
const clearFilters = () => { dashboardRiskFilter.value = ''; dashboardStatusFilter.value = '' }

const formatTimestamp = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
/* ====== 快捷入口 ====== */
.quick-nav {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.quick-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 14px;
  background: linear-gradient(180deg, var(--color-bg-card), var(--color-bg-page));
  border: 1px solid var(--color-border-1);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.quick-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.quick-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md), 0 0 16px var(--dark-color-primary-glow-soft);
  transform: translateY(-2px);
}
.quick-card:hover::after { opacity: 1; }
.qc-icon {
  font-size: 22px;
  color: var(--color-primary);
  flex-shrink: 0;
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 212, 255, 0.2);
}
.qc-text { display: flex; flex-direction: column; min-width: 0; }
.qc-title { font-size: 14px; font-weight: 600; color: var(--color-text-1); }
.qc-desc { font-size: 11px; color: var(--color-text-3); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 1400px) {
  .quick-nav { grid-template-columns: repeat(3, 1fr); }
}

.stat-card {
  padding: 16px 18px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border-1);
  background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent 55%);
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  opacity: 0.8;
  transition: opacity 0.3s ease;
}
.stat-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 60px;
  background: linear-gradient(180deg, var(--color-primary-light), transparent);
  opacity: 0.25;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.stat-card:nth-child(1)::before { background: var(--color-danger); }
.stat-card:nth-child(2)::before { background: var(--color-warning); }
.stat-card:nth-child(3)::before { background: var(--color-success); }
.stat-card:nth-child(4)::before { background: var(--color-info); }
.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-border-2);
  box-shadow: var(--shadow-md), 0 0 18px var(--dark-color-primary-glow-soft);
}
.stat-card:hover::before { opacity: 1; }
.stat-card:hover::after { opacity: 0.45; }
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  letter-spacing: -0.5px;
}
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.stat-trend { font-size: 11px; margin-top: 4px; color: var(--text-muted); }
.stat-trend.up { color: #10b981; }

.chart-card {
  padding: 16px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border-1);
  background: linear-gradient(180deg, rgba(255,255,255,0.015), transparent 45%);
}
.chart-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 42px;
  background: linear-gradient(180deg, var(--color-primary-light), transparent);
  opacity: 0.15;
  pointer-events: none;
}
.chart-card:hover {
  border-color: var(--color-border-2);
  box-shadow: var(--shadow-md);
}
.chart-header {
  border-left: 3px solid var(--accent-cyan);
  padding-left: 12px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.chart-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.chart-sub { font-size: 11px; color: var(--color-text-3); }

.overview-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.chart-card-wide {
  grid-column: 1 / -1;
}
.chart-content {
  width: 100%;
  height: 240px;
}
.chart-card-wide .chart-content { height: 260px; }
@media (max-width: 1100px) {
  .overview-charts { grid-template-columns: 1fr; }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}
.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.empty-icon { font-size: 64px; opacity: 0.5; }
.empty-title { font-size: 20px; color: var(--text-primary); font-weight: 600; margin: 0; }
.empty-desc { font-size: 14px; color: var(--text-muted); max-width: 400px; }
.data-source-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  margin-top: 16px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 10px;
  font-size: 12px;
  color: var(--text-muted);
  transition: border-color 0.3s ease;
}
.data-source-bar:hover {
  border-color: rgba(0,198,255,0.15);
}
.ds-icon { font-size: 14px; }
.ds-text { }
.ds-separator { opacity: 0.3; }

.recent-cases-section {
  animation: fadeIn 0.5s ease;
}
.filter-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border: 1px solid rgba(0, 212, 255, 0.25);
  border-radius: 12px;
}
.filter-clear { cursor: pointer; font-size: 13px; color: var(--color-text-3); transition: color 0.15s; }
.filter-clear:hover { color: var(--color-danger); }
</style>
