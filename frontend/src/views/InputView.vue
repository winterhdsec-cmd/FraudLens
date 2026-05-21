<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📝</span>
                涉案文本录入
              </h2>
              <p class="section-desc">支持聊天记录、报警文本、涉案信息等多种文本格式录入</p>
            </div>
            <div class="header-right">
              <div class="quick-stats">
                <div class="quick-stat">
                  <span class="qs-value">{{ inputText.length }}</span>
                  <span class="qs-label">字符</span>
                </div>
                <div class="quick-stat">
                  <span class="qs-value">{{ textLineCount }}</span>
                  <span class="qs-label">行</span>
                </div>
              </div>
            </div>
          </div>

          <div class="input-container">
            <div class="input-main tech-card">
              <div class="input-toolbar">
                <div class="toolbar-left">
                  <span class="toolbar-icon">📝</span>
                  <span class="toolbar-title">文本输入区</span>
                </div>
                <div class="toolbar-right">
                  <el-button size="small" @click="clearInput">
                    <span>🗑️</span> 清空
                  </el-button>
                  <el-button size="small" type="primary" @click="loadDemo">
                    <span>📋</span> 加载测试案情
                  </el-button>
                </div>
              </div>
              <div class="input-area">
                <textarea
                v-model="inputText"
                :rows="16"
                placeholder="请粘贴聊天记录、报警文本或涉案信息...

支持格式：
• 聊天记录截图转文字
• 报警笔录
• 涉案资金流水描述
• 诈骗话术文本"
                class="native-textarea"
              ></textarea>
              </div>
              <div class="input-footer">
                <div class="format-tips">
                  <span class="tip-icon">💡</span>
                  <span>建议包含：涉案时间、金额、联系方式、作案手法等关键信息</span>
                </div>
              </div>
            </div>

            <div class="input-sidebar">
              <div class="sidebar-card tech-card">
                <div class="card-header">
                  <span class="card-icon">📊</span>
                  <span class="card-title">文本分析预览</span>
                </div>
                <div class="card-content">
                  <div class="preview-item" v-if="inputText.length > 0">
                    <span class="preview-label">识别关键词</span>
                    <div class="preview-tags">
                      <el-tag v-for="kw in extractedKeywords" :key="kw" size="small" type="info">{{ kw }}</el-tag>
                    </div>
                  </div>
                  <div class="preview-empty" v-else>
                    <span class="empty-icon">📝</span>
                    <span class="empty-text">输入文本后自动分析</span>
                  </div>
                </div>
              </div>

              <div class="sidebar-card tech-card">
                <div class="card-header">
                  <span class="card-icon">🎯</span>
                  <span class="card-title">录入要点</span>
                </div>
                <div class="card-content">
                  <div class="checklist">
                    <div class="check-item" :class="{ active: hasTime }">
                      <span class="check-icon">{{ hasTime ? '✅' : '⬜' }}</span>
                      <span>涉案时间</span>
                    </div>
                    <div class="check-item" :class="{ active: hasAmount }">
                      <span class="check-icon">{{ hasAmount ? '✅' : '⬜' }}</span>
                      <span>涉案金额</span>
                    </div>
                    <div class="check-item" :class="{ active: hasPhone }">
                      <span class="check-icon">{{ hasPhone ? '✅' : '⬜' }}</span>
                      <span>联系方式</span>
                    </div>
                    <div class="check-item" :class="{ active: hasMethod }">
                      <span class="check-icon">{{ hasMethod ? '✅' : '⬜' }}</span>
                      <span>作案手法</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="action-bar">
            <el-button
              class="analyze-btn"
              type="primary"
              size="large"
              :loading="loading"
              :disabled="!inputText.trim()"
              @click="startAnalysis"
            >
              <span class="btn-icon">🚀</span>
              <span>{{ loading ? 'AI 正在深度研判...' : '开始智能研判' }}</span>
            </el-button>
          </div>
        </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, clearInput, extractedKeywords, hasAmount, hasMethod, hasPhone,
  hasTime, inputText, loadDemo, loading, startAnalysis, textLineCount
} = state
</script>

<style scoped>
.input-container { display: grid; grid-template-columns: 1fr 260px; gap: 20px; }
.input-main { padding: 0; display: flex; flex-direction: column; }
.input-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; background: rgba(0,0,0,0.2); border-bottom: 1px solid var(--border-primary); }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; }
.toolbar-icon { font-size: 16px; }
.toolbar-title { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.input-area { padding: 0; flex: 1; }
.native-textarea { width: 100%; min-height: 400px; padding: 16px 18px; background: rgba(10,14,26,0.6); border: none; border-radius: 0; color: #e2e8f0; font-size: 14px; line-height: 1.8; resize: vertical; outline: none; box-sizing: border-box; }
.native-textarea::placeholder { color: #475569; }
.native-textarea:focus { background: rgba(10,14,26,0.7); box-shadow: inset 0 0 20px rgba(0,198,255,0.05); }
.input-footer { padding: 12px 18px; border-top: 1px solid var(--border-primary); }
.format-tips { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
.tip-icon { flex-shrink: 0; }
.input-sidebar { display: flex; flex-direction: column; gap: 16px; }
.sidebar-card { padding: 0; }
.sidebar-card .card-header { display: flex; align-items: center; gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--border-primary); background: rgba(0,0,0,0.15); }
.card-icon { font-size: 14px; }
.card-title { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.card-content { padding: 14px 16px; }
.preview-item { margin-bottom: 8px; }
.preview-label { font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 6px; }
.preview-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.preview-empty { text-align: center; padding: 24px 0; }
.preview-empty .empty-icon { display: block; font-size: 28px; margin-bottom: 6px; opacity: 0.4; }
.preview-empty .empty-text { font-size: 12px; color: var(--text-muted); }
.checklist { display: flex; flex-direction: column; gap: 8px; }
.check-item { display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: rgba(0,0,0,0.2); border: 1px solid rgba(0,198,255,0.08); border-radius: 8px; font-size: 13px; color: var(--text-muted); transition: all 0.3s ease; }
.check-item.active { border-color: rgba(16,185,129,0.3); background: rgba(16,185,129,0.08); color: #10b981; }
.check-icon { flex-shrink: 0; }
.action-bar { display: flex; justify-content: center; margin-top: 24px; }
.analyze-btn { min-width: 220px; height: 48px; font-size: 16px; }
.btn-icon { margin-right: 6px; }
</style>
