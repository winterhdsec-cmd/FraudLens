<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon"><el-icon><Document /></el-icon></span>
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
                  <span><el-icon><Promotion /></el-icon></span> 生成报告
                </el-button>
              </div>
            </div>

            <div class="report-preview-panel tech-card">
              <div class="preview-header">
                <span class="preview-icon"><el-icon><View /></el-icon></span>
                <span class="preview-title">报告预览</span>
                <div class="preview-actions" v-if="reportPreview">
                  <el-button size="small" @click="printReport">
                    <span><el-icon><Printer /></el-icon></span> 打印
                  </el-button>
                  <el-button size="small" type="primary" @click="downloadReport">
                    <span><el-icon><Download /></el-icon></span> 下载
                  </el-button>
                </div>
              </div>
              <div class="preview-body">
                <div class="report-paper-wrap" v-if="reportPreview">
                  <ReportDocView :doc="reportDoc" />
                </div>

                <div class="preview-empty" v-else>
                  <div class="empty-icon"><el-icon><Document /></el-icon></div>
                  <div class="empty-text">请配置报告参数并点击"生成报告"</div>
                </div>
              </div>
            </div>
          </div>
        </div>

</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { computed, onMounted } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import ReportDocView from '../components/ReportDocView.vue'
const router = useRouter()
const route = useRoute()
const state = useAppState()
const {
  activeMenu, cases, downloadReport, gangs, generateReport, generatingReport,
  getGangById, getReportTitle, loading, printReport, reportConfig, reportPreview,
  selectedCase, buildReportDoc
} = state

// 文档模型：预览组件与打印/下载共用同一份，保证所见即所得
const reportDoc = computed(() => (reportPreview.value ? buildReportDoc() : null))

onMounted(() => {
  if (route.query.gangId) {
    reportConfig.gangId = route.query.gangId
    reportConfig.includeTimeline = true
    reportConfig.includeMoney = true
  }
})
</script>

<style scoped>
/* 纸面预览容器：深色面板里嵌一张 A4 白纸，与导出/打印版式一致 */
.report-paper-wrap {
  background: #e9edf2;
  border-radius: 6px;
  padding: 18px 10px;
  max-height: 72vh;
  overflow-y: auto;
}
.report-paper-wrap :deep(.report-doc) {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  padding: 34px 40px 30px;
  font-size: 13.5px;
  line-height: 1.8;
}
.report-paper-wrap :deep(.rd-org) { font-size: 24px; }
.report-paper-wrap :deep(.rd-title) { font-size: 18px; }
.report-paper-wrap :deep(.doc-table td) { font-size: 12.5px; padding: 4px 8px; }
</style>
