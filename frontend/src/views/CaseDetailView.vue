<template>
<div class="view-section">
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
              <div class="case-header-card">
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
                        立案时间：{{ selectedCase.date || '—' }}
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
                    <span class="header-stat-value">{{ selectedCase.region || '—' }}</span>
                    <span class="header-stat-label">案发地区</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.type || '—' }}</span>
                    <span class="header-stat-label">案件类型</span>
                  </div>
                </div>
              </div>

              <div class="detail-tabs">
                <el-tabs v-model="detailTab">
                  <el-tab-pane label="案件概述" name="overview">
                    <div class="timeline-section">
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
                              <span class="info-value">{{ selectedCase.victimName || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">性别</span>
                              <span class="info-value">{{ selectedCase.victimGender || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">年龄</span>
                              <span class="info-value">{{ selectedCase.victimAge ? selectedCase.victimAge + '岁' : '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">联系方式</span>
                              <span class="info-value">{{ selectedCase.victimPhone || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">职业</span>
                              <span class="info-value">{{ selectedCase.victimJob || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">户籍地址</span>
                              <span class="info-value">{{ selectedCase.victimAddress || '—' }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">📞 涉案通讯信息</h4>
                          <div class="info-grid">
                            <div class="info-item">
                              <span class="info-label">诈骗号码</span>
                              <span class="info-value danger">{{ selectedCase.scamPhone || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">归属地</span>
                              <span class="info-value">{{ selectedCase.phoneLocation || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">诈骗网址</span>
                              <span class="info-value danger">{{ selectedCase.scamUrl || '—' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">IP地址</span>
                              <span class="info-value">{{ selectedCase.ipAddress || '—' }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="资金流向" name="money">
                    <div class="money-section">
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
                    <div class="method-section">
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
                  <el-tab-pane label="行为特征" name="behavior">
                    <div class="timeline-section">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">🎯 行为特征分析</h4>
                          <div class="info-grid">
                            <div class="info-item"><span class="info-label">作案时段</span><span class="info-value">{{ selectedCase.peakHours || '—' }}</span></div>
                            <div class="info-item"><span class="info-label">目标群体</span><span class="info-value">{{ selectedCase.targetGroup || '—' }}</span></div>
                            <div class="info-item"><span class="info-label">作案工具</span><span class="info-value">{{ selectedCase.tools || '—' }}</span></div>
                            <div class="info-item"><span class="info-label">沟通方式</span><span class="info-value">{{ selectedCase.commMethod || '—' }}</span></div>
                          </div>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">🧠 话术特征</h4>
                          <div class="tag-cloud">
                            <el-tag v-for="(kw, i) in (selectedCase.keywords || ['冒充客服','征信诈骗','屏幕共享','安全账户','转账验证'])" :key="i" :type="i % 3 === 0 ? 'danger' : i % 3 === 1 ? 'warning' : 'info'" size="small" style="margin: 4px">{{ kw }}</el-tag>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="关联关系" name="relation">
                    <div class="timeline-section">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">🔗 关联案件</h4>
                          <p class="overview-content" v-if="gangs.length">当前案件所属团伙共关联 {{ gangs.length }} 个案件</p>
                          <p class="overview-content" v-else>暂无关联案件信息</p>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">👥 关联团伙</h4>
                          <div class="tag-cloud">
                            <el-tag v-for="gang in gangs.slice(0,10)" :key="gang.id || gang.gang_id" type="danger" size="small" style="margin:4px;cursor:pointer" @click="viewRelatedGang(gang.gang_id || gang.id)">{{ gang.name || gang.gang_name }}</el-tag>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="风险评估" name="risk">
                    <div class="timeline-section">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">⚠️ 风险等级评估</h4>
                          <div class="info-grid">
                            <div class="info-item"><span class="info-label">案件风险等级</span><span class="info-value"><el-tag :type="selectedCase.risk_level === 'HIGH' ? 'danger' : selectedCase.risk_level === 'MEDIUM' ? 'warning' : 'info'" effect="dark">{{ selectedCase.risk_level || 'MEDIUM' }}</el-tag></span></div>
                            <div class="info-item"><span class="info-label">涉案金额风险</span><span class="info-value">{{ parseFloat(selectedCase.amount_value || selectedCase.amount || 0) > 50000 ? '高危' : parseFloat(selectedCase.amount_value || selectedCase.amount || 0) > 10000 ? '中危' : '低危' }}</span></div>
                            <div class="info-item"><span class="info-label">证据完整性</span><span class="info-value">部分完整</span></div>
                            <div class="info-item"><span class="info-label">追损可能性</span><span class="info-value">{{ parseFloat(selectedCase.amount_value || selectedCase.amount || 0) > 100000 ? '较低' : '中等' }}</span></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="处置建议" name="suggestion">
                    <div class="timeline-section">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">📋 建议处置措施</h4>
                          <div class="suggestion-list">
                            <div class="suggestion-item" v-if="parsedReport.partA">
                              <span class="suggestion-icon">📋</span>
                              <span>根据AI研判结论，系统已自动生成处置建议。请结合实际情况制定具体措施。</span>
                            </div>
                            <div class="suggestion-item" v-for="(item, idx) in (selectedCase.suggestions || defaultSuggestions)" :key="idx">
                              <span class="suggestion-icon">{{ ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣'][idx] }}</span>
                              <span>{{ item }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>

            <div class="detail-sidebar">
              <div class="sidebar-section">
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

              <div class="sidebar-section">
                <div class="section-title-bar">
                  <span class="section-icon">🕵️</span>
                  <span class="section-title-text">办案民警</span>
                </div>
                <div class="member-list">
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">张警官 <span style="font-size:10px;color:#94a3b8">(演示)</span></span>
                      <span class="member-role">主办民警</span>
                    </div>
                  </div>
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">李警官 <span style="font-size:10px;color:#94a3b8">(演示)</span></span>
                      <span class="member-role">协办民警</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="sidebar-section">
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
  activeMenu, caseEvidence, detailTab, gangs, getGangById, investigationSteps,
  parsedReport, selectGang, selectedCase, viewRelatedGang
} = state
const defaultSuggestions = ['立即启动紧急止付，冻结涉案账户', '调取银行流水，追踪资金流向', '提取通讯记录，追踪诈骗号码', '固定电子证据，制作询问笔录', '串并关联案件，锁定犯罪团伙']
</script>

<style scoped>
.case-detail-content { display: grid; grid-template-columns: 1fr 280px; gap: 20px; }
.detail-main { display: flex; flex-direction: column; gap: 16px; }

/* ====== 案件头卡片 ====== */
.case-header-card {
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(20,35,60,0.85));
  border: 1px solid rgba(0,198,255,0.15);
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  transition: all 0.4s ease;
}
.case-header-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-blue), var(--accent-purple), transparent);
  opacity: 0.8;
}
.case-header-card::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(ellipse at 30% 20%, rgba(0,198,255,0.03) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}
.case-header-card:hover {
  border-color: rgba(0,198,255,0.3);
  box-shadow: 0 0 30px rgba(0,198,255,0.08);
  transform: translateY(-1px);
}
.case-header-top {
  display: flex;
  gap: 18px;
  align-items: flex-start;
  position: relative;
  z-index: 1;
}
.case-icon-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(0,198,255,0.25), rgba(0,132,255,0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
  border: 1px solid rgba(0,198,255,0.3);
  box-shadow: 0 0 20px rgba(0,198,255,0.1);
  transition: all 0.3s ease;
}
.case-header-card:hover .case-icon-wrapper {
  box-shadow: 0 0 30px rgba(0,198,255,0.2);
  transform: scale(1.05);
}
.case-header-info { flex: 1; }
.case-title {
  font-size: 22px;
  color: #e2e8f0;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: 0.5px;
  text-shadow: 0 0 20px rgba(0,198,255,0.1);
}
.case-meta { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.meta-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #94a3b8; }
.meta-icon { font-size: 13px; }
.case-header-actions { flex-shrink: 0; }

.case-header-stats {
  display: flex;
  gap: 0;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(0,198,255,0.1);
  position: relative;
  z-index: 1;
}
.header-stat {
  flex: 1;
  text-align: center;
  position: relative;
  padding: 8px 0;
  transition: all 0.3s ease;
}
.header-stat:hover { transform: translateY(-2px); }
.header-stat:not(:first-child)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 1px;
  background: linear-gradient(to bottom, transparent, rgba(0,198,255,0.2), transparent);
}
.header-stat-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--accent-cyan);
  text-shadow: 0 0 16px rgba(0,198,255,0.25);
  transition: all 0.3s ease;
}
.header-stat:hover .header-stat-value {
  text-shadow: 0 0 28px rgba(0,198,255,0.4);
}
.header-stat-label {
  font-size: 11px;
  color: #64748b;
  margin-top: 3px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

/* ====== 标签页 ====== */
.detail-tabs { margin-top: 0; }
.detail-tabs :deep(.el-tabs__header) {
  margin: 0 0 18px;
  border-bottom: 1px solid rgba(0,198,255,0.08);
  background: transparent;
}
.detail-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  height: 2.5px;
  border-radius: 2px;
  transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}
.detail-tabs :deep(.el-tabs__item) {
  color: #64748b !important;
  font-size: 13px;
  transition: all 0.3s;
  padding: 0 18px;
  height: 40px;
  line-height: 40px;
  letter-spacing: 0.3px;
}
.detail-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-cyan) !important;
  font-weight: 600;
  text-shadow: 0 0 10px rgba(0,198,255,0.15);
}
.detail-tabs :deep(.el-tabs__item:hover) {
  color: #cbd5e1 !important;
}
.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  background: rgba(0,198,255,0.06);
}

/* ====== 通用卡片区块 ====== */
.timeline-section, .money-section, .method-section {
  padding: 22px;
  background: linear-gradient(135deg, rgba(15,23,42,0.7), rgba(18,28,50,0.6));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}
.timeline-section:hover, .money-section:hover, .method-section:hover {
  border-color: rgba(0,198,255,0.2);
  box-shadow: 0 0 28px rgba(0,198,255,0.06);
  transform: translateY(-1px);
}

.case-overview { display: flex; flex-direction: column; gap: 24px; }
.overview-section { }

.overview-title {
  font-size: 15px;
  color: #e2e8f0;
  font-weight: 600;
  margin: 0 0 14px;
  border-left: 3px solid var(--accent-cyan);
  padding-left: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.3px;
}
.overview-content {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.9;
  margin: 0;
  padding: 16px 18px;
  background: rgba(0,0,0,0.15);
  border-radius: 8px;
  border: 1px solid rgba(0,198,255,0.04);
}

/* ====== 信息网格 ====== */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.info-item {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  background: rgba(0,0,0,0.2);
  border-radius: 10px;
  border: 1px solid rgba(0,198,255,0.06);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.info-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(to bottom, var(--accent-cyan), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.info-item:hover {
  background: rgba(0,0,0,0.3);
  border-color: rgba(0,198,255,0.18);
  transform: translateX(2px);
}
.info-item:hover::before { opacity: 0.6; }
.info-label {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
  letter-spacing: 0.3px;
}
.info-value {
  font-size: 14px;
  color: #e2e8f0;
  font-weight: 500;
  text-shadow: 0 0 8px rgba(0,0,0,0.3);
}
.info-value.danger { color: #ef4444; }

/* ====== AI报告样式 ====== */
.report-line {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.9;
  padding: 3px 0;
  transition: all 0.2s;
}
.report-line:hover { color: #cbd5e1; }
.report-heading {
  font-size: 16px;
  color: var(--accent-cyan);
  font-weight: 600;
  margin: 10px 0 6px;
  text-shadow: 0 0 10px rgba(0,198,255,0.1);
}
.report-bullet { color: #e2e8f0; font-weight: 500; }
.report-section-title {
  color: var(--accent-cyan);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.report-part-a {
  padding: 16px 18px;
  background: rgba(0,0,0,0.15);
  border-radius: 10px;
  border: 1px solid rgba(0,198,255,0.05);
}
.report-part-b { margin-top: 16px; }
.report-json-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.report-json-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(0,0,0,0.15);
  border-radius: 6px;
  font-size: 12px;
  transition: all 0.3s;
  border: 1px solid rgba(0,198,255,0.04);
}
.report-json-item:hover {
  background: rgba(0,198,255,0.05);
  border-color: rgba(0,198,255,0.12);
}
.report-json-key { color: #64748b; }
.report-json-value { color: #e2e8f0; font-weight: 500; }

/* ====== 资金流向图 ====== */
.money-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  border-left: 3px solid #f59e0b;
  padding-left: 12px;
}
.money-icon { font-size: 20px; }
.money-title { font-size: 15px; color: #e2e8f0; font-weight: 600; letter-spacing: 0.3px; }
.flow-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 24px 0;
  flex-wrap: wrap;
}
.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 24px;
  border-radius: 12px;
  min-width: 100px;
  transition: all 0.3s ease;
  position: relative;
}
.flow-node:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}
.flow-node.source {
  background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05));
  border: 1px solid rgba(239,68,68,0.3);
}
.flow-node.source:hover { border-color: rgba(239,68,68,0.5); box-shadow: 0 8px 24px rgba(239,68,68,0.15); }
.flow-node.gang {
  background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05));
  border: 1px solid rgba(245,158,11,0.3);
}
.flow-node.gang:hover { border-color: rgba(245,158,11,0.5); box-shadow: 0 8px 24px rgba(245,158,11,0.15); }
.flow-node.middle {
  background: linear-gradient(135deg, rgba(139,92,246,0.15), rgba(139,92,246,0.05));
  border: 1px solid rgba(139,92,246,0.3);
}
.flow-node.middle:hover { border-color: rgba(139,92,246,0.5); box-shadow: 0 8px 24px rgba(139,92,246,0.15); }
.flow-node.target {
  background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(0,212,255,0.05));
  border: 1px solid rgba(0,212,255,0.3);
}
.flow-node.target:hover { border-color: rgba(0,212,255,0.5); box-shadow: 0 8px 24px rgba(0,212,255,0.15); }
.flow-node .node-icon { font-size: 26px; }
.flow-node .node-label { font-size: 13px; color: #e2e8f0; font-weight: 600; }
.flow-node .node-amount { font-size: 11px; color: #94a3b8; }

.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 22px;
  color: var(--accent-cyan);
  animation: flow-arrow-pulse 2s ease-in-out infinite;
}
@keyframes flow-arrow-pulse {
  0%, 100% { opacity: 0.7; transform: translateX(0); }
  50% { opacity: 1; transform: translateX(4px); }
}
.flow-arrow:nth-child(4) { animation-delay: 0.3s; }
.flow-arrow:nth-child(6) { animation-delay: 0.6s; }
.flow-arrow:nth-child(8) { animation-delay: 0.9s; }
.arrow-label { font-size: 10px; color: #64748b; }

.money-stats {
  display: flex;
  gap: 24px;
  justify-content: center;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(0,198,255,0.08);
}
.money-stat { text-align: center; padding: 8px 16px; background: rgba(0,0,0,0.1); border-radius: 8px; transition: all 0.3s; }
.money-stat:hover { background: rgba(0,0,0,0.2); transform: translateY(-1px); }
.ms-label { font-size: 11px; color: #64748b; display: block; margin-bottom: 4px; }
.ms-value { font-size: 18px; font-weight: 700; color: var(--accent-cyan); text-shadow: 0 0 10px rgba(0,198,255,0.15); }

/* ====== 调查进展时间线 ====== */
.method-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  border-left: 3px solid #8b5cf6;
  padding-left: 12px;
}
.method-icon { font-size: 20px; }
.method-title { font-size: 15px; color: #e2e8f0; font-weight: 600; letter-spacing: 0.3px; }

.investigation-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  padding-left: 24px;
}
.timeline-item {
  display: flex;
  gap: 16px;
  position: relative;
  padding-bottom: 24px;
}
.timeline-item:last-child { padding-bottom: 0; }
.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}
.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1e293b;
  border: 2.5px solid #475569;
  transition: all 0.3s;
  position: relative;
  z-index: 1;
}
.timeline-dot.completed {
  background: #10b981;
  border-color: #34d399;
  box-shadow: 0 0 12px rgba(16,185,129,0.35);
}
.timeline-dot.current {
  background: var(--accent-cyan);
  border-color: #38bdf8;
  box-shadow: 0 0 14px rgba(0,198,255,0.45);
  animation: tl-pulse 2s ease-in-out infinite;
}
.timeline-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(to bottom, rgba(0,198,255,0.15), rgba(0,198,255,0.04));
  margin-top: 4px;
}
.timeline-content { flex: 1; padding-top: 0; }
.timeline-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.timeline-date { font-size: 11px; color: #64748b; letter-spacing: 0.3px; }
.timeline-title { font-size: 14px; color: #e2e8f0; font-weight: 600; margin-bottom: 4px; }
.timeline-desc { font-size: 12px; color: #94a3b8; line-height: 1.6; }

/* ====== 标签云 ====== */
.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; }

/* ====== 处置建议 ====== */
.suggestion-list { display: flex; flex-direction: column; gap: 12px; }
.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(0,198,255,0.03);
  border-radius: 8px;
  border-left: 3px solid #00d4ff;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.6;
  transition: all 0.3s;
}
.suggestion-item:hover {
  background: rgba(0,198,255,0.07);
  transform: translateX(3px);
  box-shadow: 0 2px 12px rgba(0,198,255,0.06);
}
.suggestion-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }

/* ====== 侧边栏 ====== */
.detail-sidebar { display: flex; flex-direction: column; gap: 16px; }
.sidebar-section {
  padding: 18px;
  background: linear-gradient(135deg, rgba(15,23,42,0.7), rgba(18,28,50,0.6));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}
.sidebar-section:hover {
  border-color: rgba(0,198,255,0.2);
  box-shadow: 0 0 22px rgba(0,198,255,0.05);
  transform: translateY(-1px);
}
.sidebar-section::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0,198,255,0.3), transparent);
  opacity: 0.5;
}
.section-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0,198,255,0.08);
}
.section-icon { font-size: 15px; }
.section-title-text { font-size: 14px; color: #e2e8f0; font-weight: 600; letter-spacing: 0.3px; }

.evidence-list { display: flex; flex-direction: column; gap: 10px; }
.evidence-item {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  align-items: center;
  transition: all 0.3s;
  border: 1px solid rgba(0,198,255,0.04);
}
.evidence-item:hover {
  background: rgba(0,0,0,0.35);
  border-color: rgba(0,198,255,0.15);
  transform: translateX(2px);
}
.evidence-icon { font-size: 20px; width: 28px; text-align: center; }
.evidence-info { flex: 1; }
.evidence-name { font-size: 13px; color: #e2e8f0; font-weight: 500; }
.evidence-meta { margin-top: 3px; }

.member-list { display: flex; flex-direction: column; gap: 10px; }
.member-item {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  align-items: center;
  transition: all 0.3s;
  border: 1px solid rgba(0,198,255,0.04);
}
.member-item:hover {
  background: rgba(0,0,0,0.35);
  border-color: rgba(0,198,255,0.15);
  transform: translateX(2px);
}
.member-avatar { font-size: 22px; }
.member-info { flex: 1; }
.member-name { font-size: 13px; color: #e2e8f0; font-weight: 500; }
.member-role { font-size: 11px; color: #94a3b8; margin-top: 2px; }

@keyframes tl-pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(0,198,255,0.3); }
  50% { box-shadow: 0 0 22px rgba(0,198,255,0.6); }
}
</style>
