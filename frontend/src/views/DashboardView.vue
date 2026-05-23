<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📊</span>
                数据看板
              </h2>
              <p class="section-desc">系统运行数据总览，实时监控诈骗态势</p>
            </div>
            <div class="header-right">
              <el-button size="small" @click="loadDashboard" :loading="dashboardLoading">
                <span>🔄</span> 刷新数据
              </el-button>
            </div>
          </div>

          <div class="stats-overview">
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper danger">
                <span class="stat-icon">📋</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_cases ?? '-' }}</div>
                <div class="stat-label">案件总数</div>
                <div class="stat-trend up">
                  <span>累计录入</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper warning">
                <span class="stat-icon">👥</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_gangs ?? '-' }}</div>
                <div class="stat-label">涉案团伙</div>
                <div class="stat-trend up">
                  <span>已识别</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper success">
                <span class="stat-icon">💰</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_amount_formatted ?? dashboardData.total_amount ?? '-' }}</div>
                <div class="stat-label">涉案金额</div>
                <div class="stat-trend">
                  <span>累计金额</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper info">
                <span class="stat-icon">🔔</span>
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
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">风险等级分布</span>
              </div>
              <div class="chart-content" ref="dashboardRiskChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">案件状态分布</span>
              </div>
              <div class="chart-content" ref="dashboardStatusChartRef"></div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">诈骗类型排行</span>
              </div>
              <div class="chart-content" ref="dashboardBarChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">月度趋势</span>
              </div>
              <div class="chart-content" ref="dashboardTrendChartRef"></div>
            </div>
          </div>

          <template v-if="dashboardData.recent_cases?.length">
            <div class="recent-cases-section">
              <div class="section-sub-header">
                <h3 class="sub-title">
                  <span class="sub-icon">📋</span>
                  最新案件
                </h3>
              </div>
              <div class="cases-table tech-card">
                <el-table :data="dashboardData.recent_cases" style="width: 100%" @row-click="viewCaseFromDashboard" :highlight-current-row="true">
                  <el-table-column prop="case_id" label="案件编号" width="100" />
                  <el-table-column prop="title" label="案件名称" />
                  <el-table-column prop="scam_type" label="案件类型" width="100">
                    <template #default="scope">
                      <el-tag type="info" size="small">{{ scope.row.scam_type }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="amount" label="涉案金额" width="120" />
                  <el-table-column prop="status" label="案件状态" width="100">
                    <template #default="scope">
                      <el-tag :type="scope.row.status === '已立案' ? 'warning' : scope.row.status === '侦办中' ? 'primary' : 'success'" size="small">
                        {{ scope.row.status }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="created_at" label="立案时间" width="120" />
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
              <div class="empty-icon">📊</div>
              <h3 class="empty-title">暂无看板数据</h3>
              <p class="empty-desc">请先录入案情数据，系统将自动生成数据看板</p>
              <el-button type="primary" size="large" @click="router.push({ name: 'input' })">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, alerts, cases, dashboardBarChartRef, dashboardData, dashboardLoading,
  dashboardRiskChartRef, dashboardStatusChartRef, dashboardTrendChartRef, gangs, loadDashboard, loading,
  viewCaseFromDashboard
} = state

const formatTimestamp = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.stat-card {
  padding: 22px 24px;
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  opacity: 0.6;
  transition: opacity 0.35s ease;
}
.stat-card:nth-child(1)::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.stat-card:nth-child(2)::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.stat-card:nth-child(3)::before { background: linear-gradient(90deg, #10b981, #34d399); }
.stat-card:nth-child(4)::before { background: linear-gradient(90deg, #00d4ff, #38bdf8); }
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,198,255,0.12);
}
.stat-card:hover::before { opacity: 1; }
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
  padding: 18px;
  transition: all 0.35s ease;
  position: relative;
  overflow: hidden;
}
.chart-card:hover {
  border-color: rgba(0,198,255,0.2);
  box-shadow: 0 0 30px rgba(0,198,255,0.05);
  transform: translateY(-2px);
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
</style>
