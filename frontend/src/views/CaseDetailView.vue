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
                  <el-tab-pane label="行为特征" name="behavior">
                    <div class="timeline-section tech-card">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">🎯 行为特征分析</h4>
                          <div class="info-grid">
                            <div class="info-item"><span class="info-label">作案时段</span><span class="info-value">工作日 9:00-17:00</span></div>
                            <div class="info-item"><span class="info-label">目标群体</span><span class="info-value">25-45岁女性为主</span></div>
                            <div class="info-item"><span class="info-label">作案工具</span><span class="info-value">社交软件+远程控制APP</span></div>
                            <div class="info-item"><span class="info-label">沟通方式</span><span class="info-value">电话诱导+即时通讯</span></div>
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
                    <div class="timeline-section tech-card">
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
                    <div class="timeline-section tech-card">
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
                    <div class="timeline-section tech-card">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">📋 建议处置措施</h4>
                          <div class="suggestion-list">
                            <div class="suggestion-item"><span class="suggestion-icon">1️⃣</span><span>立即启动紧急止付，冻结涉案账户</span></div>
                            <div class="suggestion-item"><span class="suggestion-icon">2️⃣</span><span>调取银行流水，追踪资金流向</span></div>
                            <div class="suggestion-item"><span class="suggestion-icon">3️⃣</span><span>提取通讯记录，溯源诈骗号码</span></div>
                            <div class="suggestion-item"><span class="suggestion-icon">4️⃣</span><span>固定电子证据，制作询问笔录</span></div>
                            <div class="suggestion-item"><span class="suggestion-icon">5️⃣</span><span>串并关联案件，锁定犯罪团伙</span></div>
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
  activeMenu, caseEvidence, detailTab, gangs, getGangById, investigationSteps,
  parsedReport, selectGang, selectedCase, viewRelatedGang
} = state
</script>

<style scoped>
.case-detail-content { display: grid; grid-template-columns: 1fr 280px; gap: 20px; }
.detail-main { display: flex; flex-direction: column; gap: 16px; }
.breadcrumb { margin-bottom: 16px; }
.case-header-card { padding: 20px; }
.case-header-top { display: flex; gap: 16px; align-items: flex-start; }
.case-icon-wrapper { width: 52px; height: 52px; border-radius: 12px; background: rgba(0,198,255,0.12); display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
.case-header-info { flex: 1; }
.case-title { font-size: 18px; color: #e2e8f0; font-weight: 600; margin: 0 0 6px; }
.case-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.meta-item { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #94a3b8; }
.meta-icon { font-size: 12px; }
.case-header-actions { flex-shrink: 0; }
.case-header-stats { display: flex; gap: 24px; margin-top: 14px; padding-top: 14px; border-top: 1px solid rgba(0,198,255,0.1); }
.header-stat { text-align: center; }
.header-stat-value { display: block; font-size: 20px; font-weight: 700; color: var(--accent-cyan); }
.header-stat-label { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.detail-tabs { margin-top: 0; }
.detail-tabs :deep(.el-tabs__header) { margin: 0 0 16px; border-bottom: 1px solid rgba(0,198,255,0.1); }
.detail-tabs :deep(.el-tabs__item) { color: #94a3b8 !important; font-size: 13px; }
.detail-tabs :deep(.el-tabs__item.is-active) { color: var(--accent-cyan) !important; }
.timeline-section { padding: 20px; }
.case-overview { display: flex; flex-direction: column; gap: 20px; }
.overview-section { }
.overview-title { font-size: 14px; color: #e2e8f0; font-weight: 600; margin: 0 0 12px; }
.overview-content { font-size: 13px; color: #94a3b8; line-height: 1.8; margin: 0; }
.info-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 8px; }
.info-item { display: flex; flex-direction: column; padding: 10px 14px; background: rgba(0,0,0,0.15); border-radius: 8px; }
.info-label { font-size: 11px; color: #94a3b8; }
.info-value { font-size: 14px; color: #e2e8f0; font-weight: 500; }
.info-value.danger { color: #ef4444; }
.report-line { font-size: 13px; color: #94a3b8; line-height: 1.8; padding: 2px 0; }
.report-heading { font-size: 15px; color: var(--accent-cyan); font-weight: 600; }
.report-bullet { color: #e2e8f0; }
.report-section-title { color: var(--accent-cyan); font-weight: 600; }
.report-part-b { margin-top: 12px; }
.report-json-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 6px; }
.report-json-item { display: flex; justify-content: space-between; padding: 6px 10px; background: rgba(0,0,0,0.1); border-radius: 4px; font-size: 12px; }
.report-json-key { color: #94a3b8; }
.report-json-value { color: #e2e8f0; font-weight: 500; }
.money-section { padding: 20px; }
.money-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.money-icon { font-size: 18px; }
.money-title { font-size: 15px; color: #e2e8f0; font-weight: 600; }
.flow-diagram { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 20px 0; flex-wrap: wrap; }
.flow-node { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 12px 18px; border-radius: 10px; min-width: 80px; }
.flow-node.source { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.25); }
.flow-node.gang { background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.25); }
.flow-node.middle { background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.25); }
.flow-node.target { background: rgba(0,212,255,0.12); border: 1px solid rgba(0,212,255,0.25); }
.flow-node .node-icon { font-size: 22px; }
.flow-node .node-label { font-size: 12px; color: #e2e8f0; font-weight: 500; }
.flow-node .node-amount { font-size: 11px; color: #94a3b8; }
.flow-arrow { display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 18px; color: var(--accent-cyan); }
.arrow-label { font-size: 10px; color: #94a3b8; }
.money-stats { display: flex; gap: 16px; justify-content: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(0,198,255,0.1); }
.money-stat { text-align: center; }
.ms-label { font-size: 11px; color: #94a3b8; display: block; }
.ms-value { font-size: 16px; font-weight: 700; color: var(--accent-cyan); }
.method-section { padding: 20px; }
.method-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.method-icon { font-size: 18px; }
.method-title { font-size: 15px; color: #e2e8f0; font-weight: 600; }
.investigation-timeline { display: flex; flex-direction: column; gap: 0; position: relative; padding-left: 20px; }
.timeline-item { display: flex; gap: 14px; position: relative; padding-bottom: 20px; }
.timeline-marker { display: flex; flex-direction: column; align-items: center; width: 14px; flex-shrink: 0; }
.timeline-dot { width: 12px; height: 12px; border-radius: 50%; background: #334155; border: 2px solid #475569; }
.timeline-dot.completed { background: #10b981; border-color: #34d399; }
.timeline-dot.current { background: var(--accent-cyan); border-color: #38bdf8; box-shadow: 0 0 8px rgba(0,198,255,0.4); }
.timeline-line { width: 2px; flex: 1; background: rgba(0,198,255,0.1); margin-top: 4px; }
.timeline-content { flex: 1; }
.timeline-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.timeline-date { font-size: 11px; color: #94a3b8; }
.timeline-title { font-size: 13px; color: #e2e8f0; font-weight: 500; }
.timeline-desc { font-size: 12px; color: #94a3b8; line-height: 1.5; margin-top: 2px; }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 4px; }
.suggestion-list { display: flex; flex-direction: column; gap: 12px; }
.suggestion-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: rgba(0,198,255,0.03); border-radius: 6px; border-left: 3px solid #00d4ff; color: #e2e8f0; font-size: 14px; }
.suggestion-icon { font-size: 18px; }
.detail-sidebar { display: flex; flex-direction: column; gap: 16px; }
.sidebar-section { padding: 16px; }
.section-title-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid rgba(0,198,255,0.1); }
.section-icon { font-size: 14px; }
.section-title-text { font-size: 13px; color: #e2e8f0; font-weight: 500; }
.evidence-list { display: flex; flex-direction: column; gap: 8px; }
.evidence-item { display: flex; gap: 10px; padding: 8px 10px; background: rgba(0,0,0,0.15); border-radius: 6px; align-items: center; }
.evidence-icon { font-size: 18px; }
.evidence-info { flex: 1; }
.evidence-name { font-size: 12px; color: #e2e8f0; }
.evidence-meta { margin-top: 2px; }
.member-list { display: flex; flex-direction: column; gap: 8px; }
.member-item { display: flex; gap: 10px; padding: 8px 10px; background: rgba(0,0,0,0.15); border-radius: 6px; align-items: center; }
.member-avatar { font-size: 20px; }
.member-info { flex: 1; }
.member-name { font-size: 13px; color: #e2e8f0; }
.member-role { font-size: 11px; color: #94a3b8; }
</style>
