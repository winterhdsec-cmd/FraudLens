<template>
<div v-if="activeMenu === 'details'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📈</span>
                深度分析
              </h2>
              <p class="section-desc">AI 智能分析团伙特征、资金流向和关联关系</p>
            </div>
          </div>

          <div class="analysis-dashboard">
            <div class="analysis-row">
              <div class="analysis-card tech-card money-flow-card">
                <div class="analysis-header">
                  <span class="analysis-icon">💰</span>
                  <span class="analysis-title">资金流向追踪</span>
                  <span class="flow-badge">AI分析</span>
                </div>
                <div class="analysis-content">
                  <div class="flow-chart">
                    <div class="flow-path">
                      <div class="flow-stage">
                        <div class="stage-node source">
                          <div class="node-glow"></div>
                          <span class="node-icon">👤</span>
                        </div>
                        <span class="stage-label">受害者</span>
                        <span class="stage-desc">账户资金流出</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">转账</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node gang">
                          <div class="node-glow"></div>
                          <span class="node-icon">💳</span>
                        </div>
                        <span class="stage-label">涉案账户</span>
                        <span class="stage-desc">第一层接收</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">分散</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node middle">
                          <div class="node-glow"></div>
                          <span class="node-icon">🏦</span>
                        </div>
                        <span class="stage-label">中转账户</span>
                        <span class="stage-desc">多层流转</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">出境</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node target">
                          <div class="node-glow"></div>
                          <span class="node-icon">🌍</span>
                        </div>
                        <span class="stage-label">境外取现</span>
                        <span class="stage-desc">最终去向</span>
                      </div>
                    </div>
                  </div>
                  <div class="flow-metrics">
                    <div class="metric-item">
                      <div class="metric-icon">💰</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案金额</span>
                        <span class="metric-value danger">{{ totalAmountFormatted }}</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">📊</div>
                      <div class="metric-info">
                        <span class="metric-label">中转层级</span>
                        <span class="metric-value">3-5层</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🌏</div>
                      <div class="metric-info">
                        <span class="metric-label">境外流向</span>
                        <span class="metric-value warning">85%</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🏦</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案账户</span>
                        <span class="metric-value">23个</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="analysis-card tech-card">
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
            </div>

            <div class="analysis-row">
              <div class="analysis-card tech-card full-width">
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
                    <svg class="relation-lines">
                      <line v-for="line in relationLines" :key="line.id" :x1="line.x1" :y1="line.y1" :x2="line.x2" :y2="line.y2" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div class="analysis-row">
              <div class="analysis-card tech-card">
                <div class="analysis-header">
                  <span class="analysis-icon">📊</span>
                  <span class="analysis-title">案件类型统计</span>
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

              <div class="analysis-card tech-card">
                <div class="analysis-header">
                  <span class="analysis-icon">🌍</span>
                  <span class="analysis-title">地域分布</span>
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
        </div>
</template>

<script setup>
import { inject } from "vue"
const state = inject("appState")
</script>
