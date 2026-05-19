<template>
  <div class="view-section">
    <div class="section-header">
      <div class="header-left">
        <h2 class="section-title">
          <span class="title-icon">📂</span>
          文件证据上传
        </h2>
        <p class="section-desc">上传聊天截图、转账凭证、警情文档，系统自动提取文字并研判</p>
      </div>
      <div class="header-right">
        <div class="quick-stats">
          <div class="quick-stat">
            <span class="qs-value">{{ uploadedFiles.length }}</span>
            <span class="qs-label">已上传</span>
          </div>
        </div>
      </div>
    </div>

    <div class="upload-container">
      <div class="upload-main tech-card">
        <div class="upload-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-icon">📂</span>
            <span class="toolbar-title">文件上传区</span>
          </div>
        </div>
        <el-upload
          :before-upload="handleBeforeUpload"
          :show-file-list="false"
          accept="image/*,.txt,.csv,.docx"
          class="upload-area"
          drag
          multiple
        >
          <div class="upload-content">
            <div class="upload-icon-wrapper">
              <i class="el-icon-upload upload-icon"></i>
            </div>
            <div class="upload-text">将文件拖到此处，或<span class="highlight">点击上传</span></div>
            <div class="upload-hint">支持图片(JPG/PNG)、文本(TXT/CSV)、Word(DOCX)，单文件最大 10MB</div>
            <div class="upload-formats">
              <span class="format-tag">📷 聊天截图</span>
              <span class="format-tag">📄 警情文档</span>
              <span class="format-tag">📝 转账凭证</span>
              <span class="format-tag">📋 报案笔录</span>
            </div>
          </div>
        </el-upload>
      </div>

      <div class="upload-preview" v-if="uploadedFiles.length">
        <div class="preview-header">
          <span class="preview-title">已上传文件 ({{ uploadedFiles.length }})</span>
          <el-button size="small" @click="clearImages">清空全部</el-button>
        </div>
        <div class="preview-grid">
          <div v-for="(item, idx) in uploadedFiles" :key="idx" class="preview-item">
            <img v-if="item.type === 'image'" :src="item.url" alt="预览" />
            <div v-else class="file-icon-wrapper">
              <span class="file-icon">{{ item.type === 'docx' ? '📄' : '📝' }}</span>
              <span class="file-type-label">{{ item.name.split('.').pop().toUpperCase() }}</span>
            </div>
            <div class="preview-overlay">
              <span class="preview-name">{{ item.name }}</span>
              <el-button size="small" type="danger" @click="removeImage(idx)">删除</el-button>
            </div>
            <div class="preview-badge">{{ item.type === 'image' ? '图片' : item.type === 'docx' ? '文档' : '文本' }}</div>
          </div>
        </div>
      </div>

      <div class="upload-tips tech-card" v-if="!uploadedFiles.length">
        <div class="tip-header">
          <span class="tip-icon">💡</span>
          <span class="tip-title">上传提示</span>
        </div>
        <div class="tip-content">
          <div class="tip-item">
            <span class="tip-num">1</span>
            <span class="tip-text">上传聊天截图或警情文档，系统自动提取文字</span>
          </div>
          <div class="tip-item">
            <span class="tip-num">2</span>
            <span class="tip-text">图片使用 OCR 识别，文档自动解析文字内容</span>
          </div>
          <div class="tip-item">
            <span class="tip-num">3</span>
            <span class="tip-text">提取的文字自动进入 AI 研判分析流程</span>
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
        :disabled="!uploadedFiles.length"
        @click="startImageAnalysis"
      >
        <span class="btn-icon">🔍</span>
        <span>{{ loading ? 'AI 正在处理文件...' : '开始识别分析' }}</span>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, clearImages, handleBeforeUpload, loading, removeImage, startImageAnalysis,
  uploadedImages: uploadedFiles
} = state
</script>