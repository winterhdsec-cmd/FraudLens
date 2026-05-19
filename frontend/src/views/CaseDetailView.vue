<template>
<div class="view-section">
          <div class="breadcrumb">
            <el-breadcrumb>
              <el-breadcrumb-item :to="{ path: '/overview' }">案件总览</el-breadcrumb-item>
              <el-breadcrumb-item v-if="selectedCase">{{ selectedCase.title }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div v-if="!selectedCase" class="empty-state" style="margin-top: 60px;">
            <div class="empty-content">
              <div class="empty-icon">🔍</div>
              <h3 class="empty-title">请先选择案件</h3>
              <p class="empty-desc">请前往"案件总览"页面选择具体案件，查看详细分析</p>
              <el-button type="primary" size="large" @click="router.push({ name: 'overview' })">
                <span>📊</span> 前往案件总览
              </el-button>
            </div>
          </div>
          <template v-else>
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🔍</span>
                案件详情
              </h2>
              <p class="section-desc">查看选中案件的详细信息、受害人和证据材料</p>
            </div>
          </div>

          <div class="case-detail-content">
            <div class="detail-main">
              <div class="case-header-card tech-card">
                <div class="case-header-top">
                  <div class="case-icon-wrapper">
                    <span class="case-icon">🔍</span>
                  </div>
                  <div class="case-header-info">
                    <h3 class="case-title">{{ selectedCase.title }}</h3>
                    <div class="case-meta">
                      <el-tag type="warning" effect="dark" size="large">
                        {{ selectedCase.status }}
                      </el-tag>
                      <span class="meta-item">
                        <span class="meta-icon">📋</span>
                        案件编号：{{ selectedCase.id }}
                      </span>
                      <span class="meta-item">
                        <span class="meta-icon">📅</span>
                        立案时间：{{ selectedCase.date || '2024-03-20' }}
                      </span>
                    </div>
                  </div>
                  <div class="case-header-actions">
                    <el-button type="primary" @click="router.push({ name: 'report', query: { gangId: selectedCase.gang } })">
                      <span>📄</span> 生成报告
                    </el-button>
                  </div>
                </div>
                <div class="case-header-stats">
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.amount }}</span>
                    <span class="header-stat-label">涉案金额</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.victims || 1 }}人</span>
                    <span class="header-stat-label">受害人数</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.region || '广东省' }}</span>
                    <span class="header-stat-label">案发地区</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.type || '冒充客服' }}</span>
                    <span class="header-stat-label">案件类型</span>
                  </div>
                </div>
              </div>

              <div class="detail-tabs">
                <el-tabs v-model="detailTab">
                  <el-tab-pane label="案件概述" name="overview">
                    <div class="timeline-section tech-card">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">📝 AI 研判结论</h4>
                          <div v-if="parsedReport.partA" class="report-part-a">
                            <div v-for="(line, li) in parsedReport.partA.split('\n')" :key="li" class="report-line" :class="{ 'report-heading': line.startsWith('###'), 'report-item': line.match(/^\d+\./) }">
                              <template v-if="line.startsWith('###')">
                                <span class="report-section-title">{{ line.replace('### ', '') }}</span>
                              </template>
                              <template v-else-if="line.match(/^\d+\./)">
                                <span class="report-bullet">{{ line }}</span>
                              </template>
                              <template v-else>
                                <span>{{ line }}</span>
                              </template>
                            </div>
                          </div>
                          <div v-if="parsedReport.partB" class="report-part-b">
                            <div class="report-json-grid">
                              <div v-for="(val, key) in parsedReport.partB" :key="key" class="report-json-item">
                                <span class="report-json-key">{{ key }}</span>
                                <span class="report-json-value">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                              </div>
                            </div>
                          </div>
                          <p v-else class="overview-content">{{ selectedCase.description }}</p>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">👤 受害人信息</h4>
                          <div class="info-grid">
                            <div class="info-item">
                              <span class="info-label">姓名</span>
                              <span class="info-value">{{ selectedCase.victimName || '王女士' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">性别</span>
                              <span class="info-value">{{ selectedCase.victimGender || '女' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">年龄</span>
                              <span class="info-value">{{ selectedCase.victimAge || '32' }}岁</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">联系方式</span>
                              <span class="info-value">{{ selectedCase.victimPhone || '138****5678' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">职业</span>
                              <span class="info-value">{{ selectedCase.victimJob || '公司职员' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">户籍地址</span>
                              <span class="info-value">{{ selectedCase.victimAddress || '广东省深圳市' }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">📞 涉案通讯信息</h4>
                          <div class="info-grid">
                            <div class="info-item">
                              <span class="info-label">诈骗号码</span>
                              <span class="info-value danger">{{ selectedCase.scamPhone || '0755-8888****' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">归属地</span>
                              <span class="info-value">{{ selectedCase.phoneLocation || '广东深圳' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">诈骗网址</span>
                              <span class="info-value danger">{{ selectedCase.scamUrl || 'jd-security.com' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">IP地址</span>
                              <span class="info-value">{{ selectedCase.ipAddress || '192.168.***.***' }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="资金流向" name="money">
                    <div class="money-section tech-card">
                      <div class="money-header">
                        <span class="money-icon">💰</span>
                        <span class="money-title">资金流向追踪</span>
                      </div>
                      <div class="money-flow">
                        <div class="flow-diagram">
                          <div class="flow-node source">
                            <span class="node-icon">👤</span>
                            <span class="node-label">受害人账户</span>
                            <span class="node-amount">{{ selectedCase.amount }}</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">转账</span>
                          </div>
                          <div class="flow-node gang">
                            <span class="node-icon">💳</span>
                            <span class="node-label">涉案账户</span>
                            <span class="node-amount">***1234</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">分散</span>
                          </div>
                          <div class="flow-node middle">
                            <span class="node-icon">🏦</span>
                            <span class="node-label">中转账户</span>
                            <span class="node-amount">多层分散</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">出境</span>
                          </div>
                          <div class="flow-node target">
                            <span class="node-icon">🌍</span>
                            <span class="node-label">境外取现</span>
                            <span class="node-amount">最终去向</span>
                          </div>
                        </div>
                      </div>
                      <div class="money-stats">
                        <div class="money-stat">
                          <span class="ms-label">涉案账户数</span>
                          <span class="ms-value">23个</span>
                        </div>
                        <div class="money-stat">
                          <span class="ms-label">资金层级</span>
                          <span class="ms-value">3-5层</span>
                        </div>
                        <div class="money-stat">
                          <span class="ms-label">境外流向</span>
                          <span class="ms-value">85%</span>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="调查进展" name="progress">
                    <div class="method-section tech-card">
                      <div class="method-header">
                        <span class="method-icon">📊</span>
                        <span class="method-title">案件调查进展</span>
                      </div>
                      <div class="investigation-timeline">
                        <div class="timeline-item" v-for="(step, idx) in investigationSteps" :key="idx">
                          <div class="timeline-marker">
                            <div class="timeline-dot" :class="{ completed: step.completed, current: step.current }"></div>
                            <div class="timeline-line" v-if="idx < investigationSteps.length - 1"></div>
                          </div>
                          <div class="timeline-content">
                            <div class="timeline-header">
                              <span class="timeline-date">{{ step.date }}</span>
                              <el-tag :type="step.completed ? 'success' : 'warning'" size="small">{{ step.status }}</el-tag>
                            </div>
                            <div class="timeline-title">{{ step.title }}</div>
                            <div class="timeline-desc">{{ step.description }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>

            <div class="detail-sidebar">
              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">📋</span>
                  <span class="section-title-text">证据材料</span>
                </div>
                <div class="evidence-list">
                  <div v-for="(ev, idx) in selectedCase.evidence || caseEvidence" :key="idx" class="evidence-item">
                    <span class="evidence-icon">{{ ev.icon }}</span>
                    <div class="evidence-info">
                      <div class="evidence-name">{{ ev.name }}</div>
                      <div class="evidence-meta">
                        <el-tag :type="ev.status === '已验证' ? 'success' : 'warning'" size="small">
                          {{ ev.status }}
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">🕵️</span>
                  <span class="section-title-text">办案民警</span>
                </div>
                <div class="member-list">
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">张警官</span>
                      <span class="member-role">主办民警</span>
                    </div>
                  </div>
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">李警官</span>
                      <span class="member-role">协办民警</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">🔗</span>
                  <span class="section-title-text">关联团伙</span>
                </div>
                <div class="tag-cloud">
                  <el-tag v-if="selectedCase.gang" type="danger" size="small" @click="viewRelatedGang(selectedCase.gang)">
                    {{ getGangById(selectedCase.gang)?.name || '未知团伙' }}
                  </el-tag>
                  <el-tag v-else type="info" size="small">待关联</el-tag>
                </div>
              </div>
            </div>
          </div>

          </template>
        </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const state = useAppState()
const {
  activeMenu, caseEvidence, detailTab, getGangById, investigationSteps,
  parsedReport, selectGang, selectedCase, viewRelatedGang
} = state
</script>
