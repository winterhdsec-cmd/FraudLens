<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📄</span>
                分析报告生成
              </h2>
              <p class="section-desc">一键生成标准化的案件分析报告，支持多种格式导出</p>
            </div>
          </div>

          <div class="report-container">
            <div class="report-config-panel tech-card">
              <div class="config-header">
                <span class="config-icon">⚙️</span>
                <span class="config-title">报告配置</span>
              </div>
              <div class="config-body">
                <div class="config-item">
                  <label class="config-label">报告类型</label>
                  <el-select v-model="reportConfig.type" class="dark-select">
                    <el-option label="团伙分析报告" value="gang" />
                    <el-option label="案件分析报告" value="case" />
                    <el-option label="综合研判报告" value="comprehensive" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">选择团伙</label>
                  <el-select v-model="reportConfig.gangId" class="dark-select" placeholder="请选择团伙">
                    <el-option label="-- 不限 --" value="" />
                    <el-option v-for="gang in gangs" :key="gang.id || gang.gang_id" :label="gang.name || gang.gang_name" :value="gang.id || gang.gang_id" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">导出格式</label>
                  <el-select v-model="reportConfig.format" class="dark-select">
                    <el-option label="PDF 文档" value="pdf" />
                    <el-option label="Word 文档" value="docx" />
                    <el-option label="HTML 网页" value="html" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">报告内容</label>
                  <div class="checkbox-group">
                    <el-checkbox v-model="reportConfig.includeTimeline">时间线</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeMoney">资金分析</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeNetwork">关联网络</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeSuggestion">处置建议</el-checkbox>
                  </div>
                </div>
              </div>
              <div class="config-footer">
                <el-button type="primary" class="generate-btn" @click="generateReport" :loading="generatingReport">
                  <span>🚀</span> 生成报告
                </el-button>
              </div>
            </div>

            <div class="report-preview-panel tech-card">
              <div class="preview-header">
                <span class="preview-icon">👁️</span>
                <span class="preview-title">报告预览</span>
                <div class="preview-actions" v-if="reportPreview">
                  <el-button size="small" @click="printReport">
                    <span>🖨️</span> 打印
                  </el-button>
                  <el-button size="small" type="primary" @click="downloadReport">
                    <span>📥</span> 下载
                  </el-button>
                </div>
              </div>
              <div class="preview-body">
                <div class="report-document" v-if="reportPreview">
                  <div class="doc-header">
                    <div class="doc-logo">
                      <span class="logo-icon">🛡️</span>
                      <span class="logo-text">反诈情报分析系统</span>
                    </div>
                    <div class="doc-title">{{ getReportTitle() }}</div>
                    <div class="doc-meta">
                      <div class="meta-item">
                        <span class="meta-label">报告编号：</span>
                        <span class="meta-value">RPT-{{ Date.now().toString().slice(-8) }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">生成时间：</span>
                        <span class="meta-value">{{ new Date().toLocaleString() }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">密级：</span>
                        <span class="meta-value secret">机密</span>
                      </div>
                    </div>
                  </div>

                  <div class="doc-content">
                    <div class="doc-section">
                      <div class="section-title">{{ reportConfig.type === 'case' ? '一、案件基本信息' : '一、团伙基本信息' }}</div>
                      <div class="section-body">
                        <div class="info-table" v-if="reportConfig.type === 'case' && selectedCase">
                          <div class="info-row">
                            <span class="info-label">案件编号</span>
                            <span class="info-value">{{ selectedCase.id || '-' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">案件名称</span>
                            <span class="info-value">{{ selectedCase.title || '未选择' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">案件类型</span>
                            <span class="info-value">{{ selectedCase.type || '-' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">涉案金额</span>
                            <span class="info-value danger">{{ selectedCase.amount || '-' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">案件状态</span>
                            <span class="info-value">{{ selectedCase.status || '-' }}</span>
                          </div>
                        </div>
                        <div class="info-table" v-else-if="reportConfig.gangId">
                          <div class="info-row">
                            <span class="info-label">团伙名称</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.name || getGangById(reportConfig.gangId)?.gang_name || '未选择' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">风险等级</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.riskLevel || '-' }}级</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">涉案金额</span>
                            <span class="info-value danger">{{ getGangById(reportConfig.gangId)?.amount || '-' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">关联案件</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.cases || 0 }} 起</span>
                          </div>
                        </div>
                        <div class="info-table" v-else>
                          <div class="info-row">
                            <span class="info-label">报告范围</span>
                            <span class="info-value">全量案件综合分析</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">案件总数</span>
                            <span class="info-value">{{ selectedCase?.id ? '聚焦单案' : (state.cases?.length || 0) + ' 起' }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeTimeline">
                      <div class="section-title">二、作案时间线</div>
                      <div class="section-body">
                        <div class="doc-timeline">
                          <div v-for="(event, idx) in reportConfig.type === 'case' ? [] : (getGangById(reportConfig.gangId)?.timeline || [])" :key="idx" class="doc-timeline-item">
                            <span class="doc-time">{{ event.date }}</span>
                            <span class="doc-event">{{ event.title }}</span>
                            <span class="doc-desc">{{ event.desc }}</span>
                          </div>
                          <div v-if="reportConfig.type === 'case' && selectedCase?.description" class="doc-timeline-item">
                            <span class="doc-time">{{ selectedCase.date || '-' }}</span>
                            <span class="doc-event">案件发生</span>
                            <span class="doc-desc">{{ selectedCase.title }}，涉及受害人{{ selectedCase.victimName || '未知' }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeMoney">
                      <div class="section-title">三、资金流向分析</div>
                      <div class="section-body">
                        <div class="money-flow-summary">
                          <p v-if="reportConfig.type === 'case' && selectedCase">经分析，该案件涉案金额为 {{ selectedCase.amount || '未知' }}，资金流向正在进一步调查中。</p>
                          <p v-else>经分析，该团伙涉案资金主要通过多级账户进行转移，最终流向境外。资金流转层级约3-5层，境外资金占比约85%。</p>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeSuggestion">
                      <div class="section-title">四、处置建议</div>
                      <div class="section-body">
                        <div class="suggestion-list">
                          <div class="suggestion-item">
                            <span class="suggestion-num">1</span>
                            <span class="suggestion-text">建议立即对涉案账户进行止付冻结，防止资金进一步转移</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">2</span>
                            <span class="suggestion-text">协调银行调取完整交易流水，追踪资金去向</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">3</span>
                            <span class="suggestion-text">对团伙成员实施布控，择机收网</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">4</span>
                            <span class="suggestion-text">联系境外执法机构，开展国际协作</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="doc-footer">
                    <div class="footer-line"></div>
                    <div class="footer-text">
                      <span>本报告由反诈情报分析系统自动生成</span>
                      <span>仅供内部参考使用</span>
                    </div>
                  </div>
                </div>

                <div class="preview-empty" v-else>
                  <div class="empty-icon">📄</div>
                  <div class="empty-text">请配置报告参数并点击"生成报告"</div>
                </div>
              </div>
            </div>
          </div>
        </div>

</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { onMounted } from 'vue'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const route = useRoute()
const state = useAppState()
const {
  activeMenu, cases, downloadReport, gangs, generateReport, generatingReport,
  getGangById, getReportTitle, loading, printReport, reportConfig, reportPreview,
  selectedCase
} = state

onMounted(() => {
  if (route.query.gangId) {
    reportConfig.gangId = route.query.gangId
    reportConfig.includeTimeline = true
    reportConfig.includeMoney = true
  }
})
</script>
