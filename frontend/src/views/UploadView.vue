<template>
<div v-if="activeMenu === 'upload'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📷</span>
                图片证据上传
              </h2>
              <p class="section-desc">支持聊天截图、转账凭证、诈骗页面截图等图片证据上传</p>
            </div>
            <div class="header-right">
              <div class="quick-stats">
                <div class="quick-stat">
                  <span class="qs-value">{{ uploadedImages.length }}</span>
                  <span class="qs-label">已上传</span>
                </div>
              </div>
            </div>
          </div>

          <div class="upload-container">
            <div class="upload-main tech-card">
              <div class="upload-toolbar">
                <div class="toolbar-left">
                  <span class="toolbar-icon">📷</span>
                  <span class="toolbar-title">图片上传区</span>
                </div>
              </div>
              <el-upload
                :before-upload="handleBeforeUpload"
                :show-file-list="false"
                accept="image/*"
                class="upload-area"
                drag
                multiple
              >
                <div class="upload-content">
                  <div class="upload-icon-wrapper">
                    <i class="el-icon-upload upload-icon"></i>
                  </div>
                  <div class="upload-text">将图片拖到此处，或<span class="highlight">点击上传</span></div>
                  <div class="upload-hint">支持 PNG/JPG/JPEG/GIF，单文件最大 10MB</div>
                  <div class="upload-formats">
                    <span class="format-tag">聊天截图</span>
                    <span class="format-tag">转账凭证</span>
                    <span class="format-tag">诈骗页面</span>
                    <span class="format-tag">通话记录</span>
                  </div>
                </div>
              </el-upload>
            </div>

            <div class="upload-preview" v-if="uploadedImages.length">
              <div class="preview-header">
                <span class="preview-title">已上传证据 ({{ uploadedImages.length }})</span>
                <el-button size="small" @click="clearImages">清空全部</el-button>
              </div>
              <div class="preview-grid">
                <div v-for="(img, idx) in uploadedImages" :key="idx" class="preview-item">
                  <img :src="img.url" alt="预览" />
                  <div class="preview-overlay">
                    <span class="preview-name">{{ img.name }}</span>
                    <el-button size="small" type="danger" @click="removeImage(idx)">删除</el-button>
                  </div>
                  <div class="preview-badge">证据 {{ idx + 1 }}</div>
                </div>
              </div>
            </div>

            <div class="upload-tips tech-card" v-if="!uploadedImages.length">
              <div class="tip-header">
                <span class="tip-icon">💡</span>
                <span class="tip-title">上传提示</span>
              </div>
              <div class="tip-content">
                <div class="tip-item">
                  <span class="tip-num">1</span>
                  <span class="tip-text">上传聊天记录截图，系统将自动识别关键信息</span>
                </div>
                <div class="tip-item">
                  <span class="tip-num">2</span>
                  <span class="tip-text">转账凭证可帮助追踪资金流向</span>
                </div>
                <div class="tip-item">
                  <span class="tip-num">3</span>
                  <span class="tip-text">诈骗页面截图有助于分析作案手法</span>
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
              :disabled="!uploadedImages.length"
              @click="startImageAnalysis"
            >
              <span class="btn-icon">🔍</span>
              <span>{{ loading ? 'AI 正在识别图片...' : '开始图片识别' }}</span>
            </el-button>
          </div>
        </div>
</template>

<script setup>
import { inject } from "vue"
const state = inject("appState")
</script>
