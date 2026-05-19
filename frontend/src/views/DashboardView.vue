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
                <div class="stat-value">{{ dashboardData.total_amount ?? '-' }}</div>
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

          <div class="recent-cases-section" v-if="dashboardData.recent_cases?.length">
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
import { useRouter } from 'vue-router'
const state = useAppState()
const router = useRouter()
const {
  activeMenu, alerts, cases, dashboardBarChartRef, dashboardData, dashboardLoading,
  dashboardRiskChartRef, dashboardStatusChartRef, dashboardTrendChartRef, gangs, loadDashboard, loading,
  viewCaseFromDashboard
} = state
</script>
