<template>
<div v-if="activeMenu === 'input'" class="view-section">
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
                <el-input
                  v-model="inputText"
                  type="textarea"
                  :rows="16"
                  placeholder="请粘贴聊天记录、报警文本或涉案信息...&#10;&#10;支持格式：&#10;• 聊天记录截图转文字&#10;• 报警笔录&#10;• 涉案资金流水描述&#10;• 诈骗话术文本"
                  class="dark-textarea"
                ></el-input>
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
import { inject } from "vue"
const state = inject("appState")
</script>
