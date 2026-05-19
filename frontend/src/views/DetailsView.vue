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

          <div class="analysis-row">
            <div class="analysis-card tech-card full-width">
              <div class="analysis-header">
                <span class="analysis-icon">🧬</span>
                <span class="analysis-title">语义指纹分析</span>
                <span class="analysis-subtitle">跨案件话术模式识别</span>
              </div>
              <div class="analysis-content">
                <div v-if="semanticFingerprints.length" class="fingerprint-grid">
                  <div v-for="fp in semanticFingerprints" :key="fp.type" class="fingerprint-card tech-card">
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
          </div>
        </div>
        </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const state = useAppState()
const {
  activeMenu, caseTypeStats, features, gangs, getFeatureIcon, regionStats, relationLines,
  relationNodes, semanticFingerprints, totalAmount, totalAmountFormatted
} = state
</script>

<style scoped>
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
</style>
