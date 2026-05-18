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

          <div v-if="alerts.length" class="alerts-list">
            <div v-for="alert in alerts" :key="alert.id" class="alert-card tech-card">
              <div class="alert-header">
                <div class="alert-icon-wrapper">
                  <span class="alert-icon">🔔</span>
                </div>
                <div class="alert-info">
                  <div class="alert-type">
                    <el-tag :type="getAlertType(alert.confidence)" effect="dark" size="small">
                      {{ alert.alert_type || '未知预警' }}
                    </el-tag>
                    <span class="alert-id">ID: {{ alert.id }}</span>
                  </div>
                  <div class="alert-meta">
                    <span class="meta-item">
                      <span class="meta-icon">📋</span>
                      关联案件: {{ alert.matched_case_id || '未关联' }}
                    </span>
                    <span class="meta-item">
                      <span class="meta-icon">🎯</span>
                      置信度: {{ alert.confidence }}%
                    </span>
                    <span class="meta-item">
                      <span class="meta-icon">📅</span>
                      {{ alert.created_at }}
                    </span>
                  </div>
                </div>
                <div class="alert-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :loading="resolvingAlert === alert.id"
                    @click="handleResolveAlert(alert.id)"
                  >
                    <span>✅</span> 处置
                  </el-button>
                </div>
              </div>
              <div class="alert-body" v-if="alert.description">
                <p class="alert-desc">{{ alert.description }}</p>
              </div>
              <div class="alert-footer">
                <div class="confidence-bar">
                  <div class="confidence-label">威胁指数</div>
                  <div class="confidence-track">
                    <div class="confidence-fill" :style="{ width: alert.confidence + '%', background: getConfidenceColor(alert.confidence) }"></div>
                  </div>
                  <span class="confidence-value">{{ alert.confidence }}%</span>
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
import { inject } from "vue"
const state = inject("appState")
const {
  activeMenu, alerts, alertsLoading, getAlertType, getConfidenceColor, handleResolveAlert,
  loadAlerts, loading, resolvingAlert
} = state
</script>
