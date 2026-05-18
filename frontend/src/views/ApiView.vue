<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🔌</span>
                多源数据API接入
              </h2>
              <p class="section-desc">对接银行风控、110报警平台、反诈平台等外部数据源</p>
            </div>
            <div class="header-right">
              <div class="connection-status">
                <span class="status-indicator">
                  <span class="status-dot active"></span>
                  <span>{{ connectedSources }} 个数据源已连接</span>
                </span>
              </div>
            </div>
          </div>

          <div class="api-sources-grid">
            <div class="api-source-card tech-card" :class="{ active: apiSources.bank.connected }">
              <div class="source-header">
                <div class="source-icon bank">🏦</div>
                <div class="source-info">
                  <div class="source-name">银行风控系统</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.bank.connected }"></span>
                    <span>{{ apiSources.bank.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.bank.connected" @change="toggleApiSource('bank')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入银行风控数据，获取涉案账户交易流水、异常交易预警等信息</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">💰</span>
                    <span>账户交易流水</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">⚠️</span>
                    <span>异常交易预警</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🔒</span>
                    <span>账户冻结状态</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.bank.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.bank.records }}</span>
                    <span class="stat-label">数据记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.bank.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.bank.connected">
                <el-button size="small" @click="syncApiData('bank')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchBankData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>

            <div class="api-source-card tech-card" :class="{ active: apiSources.police.connected }">
              <div class="source-header">
                <div class="source-icon police">🚔</div>
                <div class="source-info">
                  <div class="source-name">110报警平台</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.police.connected }"></span>
                    <span>{{ apiSources.police.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.police.connected" @change="toggleApiSource('police')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入110报警平台，实时获取诈骗类警情信息，支持案件串并分析</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">📞</span>
                    <span>警情实时推送</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">📋</span>
                    <span>案件基本信息</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🔗</span>
                    <span>串并案分析</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.police.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.police.records }}</span>
                    <span class="stat-label">警情记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.police.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.police.connected">
                <el-button size="small" @click="syncApiData('police')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchPoliceData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>

            <div class="api-source-card tech-card" :class="{ active: apiSources.antiFraud.connected }">
              <div class="source-header">
                <div class="source-icon antiFraud">🛡️</div>
                <div class="source-info">
                  <div class="source-name">反诈平台接入</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.antiFraud.connected }"></span>
                    <span>{{ apiSources.antiFraud.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.antiFraud.connected" @change="toggleApiSource('antiFraud')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入国家反诈中心平台，获取诈骗号码库、涉案账户库等核心数据</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">📱</span>
                    <span>诈骗号码库</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">💳</span>
                    <span>涉案账户库</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🌐</span>
                    <span>诈骗网址库</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.antiFraud.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.antiFraud.records }}</span>
                    <span class="stat-label">黑名单记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.antiFraud.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.antiFraud.connected">
                <el-button size="small" @click="syncApiData('antiFraud')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchAntiFraudData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>
          </div>

          <div class="api-data-preview tech-card" v-if="apiDataPreview.length">
            <div class="preview-header">
              <span class="preview-icon">📊</span>
              <span class="preview-title">接入数据预览</span>
              <el-button size="small" @click="importApiData" type="primary">
                <span>📥</span> 导入系统
              </el-button>
            </div>
            <div class="preview-table">
              <el-table :data="apiDataPreview" style="width: 100%">
                <el-table-column prop="source" label="数据来源" width="120" />
                <el-table-column prop="type" label="数据类型" width="120" />
                <el-table-column prop="content" label="内容摘要" />
                <el-table-column prop="time" label="时间" width="180" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === '已验证' ? 'success' : 'warning'" size="small">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div class="action-bar">
            <el-button
              class="analyze-btn"
              type="primary"
              size="large"
              :loading="loading"
              :disabled="!hasApiData"
              @click="startApiAnalysis"
            >
              <span class="btn-icon">🚀</span>
              <span>{{ loading ? 'AI 正在分析接入数据...' : '开始数据分析' }}</span>
            </el-button>
          </div>
        </div>
</template>

<script setup>
import { inject } from "vue"
const state = inject("appState")
const {
  activeMenu, apiDataPreview, apiSources, connectedSources, features, fetchAntiFraudData,
  fetchBankData, fetchPoliceData, importApiData, syncApiData, toggleApiSource
} = state
</script>
