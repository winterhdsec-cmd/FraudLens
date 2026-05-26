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

    <div class="upload-layout">
      <div class="upload-main-card tech-card">
        <div class="upload-dropzone">
          <el-upload
            :before-upload="handleBeforeUpload"
            :show-file-list="false"
            accept="image/*,.txt,.csv,.docx,.pdf"
            class="upload-area"
            drag
            multiple
          >
            <div class="upload-content">
              <div class="upload-icon-ring">
                <span class="upload-big-icon">📤</span>
              </div>
              <div class="upload-title">拖拽文件到此处</div>
              <div class="upload-subtitle">或 <span class="upload-link">点击选择文件</span></div>
              <div class="upload-hints">
                <span class="uh-item">📷 图片 JPG/PNG</span>
                <span class="uh-divider">|</span>
                <span class="uh-item">📄 文档 TXT/CSV</span>
                <span class="uh-divider">|</span>
                <span class="uh-item">📝 Word DOCX</span>
                <span class="uh-divider">|</span>
                <span class="uh-item">📑 PDF 文档</span>
              </div>
              <div class="upload-limit">单文件最大 10MB</div>
            </div>
          </el-upload>
        </div>

        <div class="upload-features">
          <div class="uf-item">
            <span class="uf-icon">🔍</span>
            <div class="uf-info">
              <span class="uf-title">OCR 文字识别</span>
              <span class="uf-desc">自动提取图片中的文字</span>
            </div>
          </div>
          <div class="uf-divider"></div>
          <div class="uf-item">
            <span class="uf-icon">🧠</span>
            <div class="uf-info">
              <span class="uf-title">多模态视觉理解</span>
              <span class="uf-desc">复杂截图/表格直接交给AI</span>
            </div>
          </div>
          <div class="uf-divider"></div>
          <div class="uf-item">
            <span class="uf-icon">🤖</span>
            <div class="uf-info">
              <span class="uf-title">AI 研判分析</span>
              <span class="uf-desc">提取内容自动进入研判</span>
            </div>
          </div>
        </div>

        <div class="mode-selector">
          <span class="mode-label">图片分析模式：</span>
          <el-radio-group v-model="analyzeMode" size="small">
            <el-radio-button value="auto">
              <span class="mode-opt">🤖 智能选择</span>
            </el-radio-button>
            <el-radio-button value="ocr">
              <span class="mode-opt">📝 快速OCR</span>
            </el-radio-button>
            <el-radio-button value="vision">
              <span class="mode-opt">🧠 多模态理解</span>
            </el-radio-button>
          </el-radio-group>
          <span class="mode-hint" v-if="analyzeMode === 'auto'">自动判断：简单文字用OCR，复杂截图用视觉模型</span>
          <span class="mode-hint" v-else-if="analyzeMode === 'ocr'">始终使用 OCR 识别图片文字（速度快）</span>
          <span class="mode-hint" v-else>始终使用多模态大模型理解图片（理解力强）</span>
        </div>
      </div>

      <div class="upload-side">
        <div v-if="uploadedFiles.length" class="uploaded-list">
          <div class="ul-header">
            <span class="ul-title">已上传文件 ({{ uploadedFiles.length }})</span>
            <el-button size="small" text @click="clearImages" style="color:var(--accent-red)">清空全部</el-button>
          </div>
          <div class="ul-grid">
            <div v-for="(item, idx) in uploadedFiles" :key="idx" class="ul-card">
              <div class="ul-preview">
                <img v-if="item.type === 'image'" :src="item.url" alt="preview" />
                <div v-else class="ul-file-icon">
                  <span class="ulf-icon">{{ item.type === 'pdf' ? '📑' : '📄' }}</span>
                  <span class="ulf-ext">{{ item.name.split('.').pop().toUpperCase() }}</span>
                </div>
              </div>
              <div class="ul-meta">
                <span class="ul-name">{{ item.name }}</span>
                <span class="ul-type-badge">{{ item.type === 'image' ? '图片' : item.type === 'docx' ? '文档' : item.type === 'pdf' ? 'PDF' : '文本' }}</span>
                <span class="ul-size">{{ item._file?.size ? (item._file.size / 1024).toFixed(1) + ' KB' : '' }}</span>
              </div>
              <button class="ul-remove" @click="removeImage(idx)">✕</button>
            </div>
          </div>
        </div>

        <div v-else class="upload-tips-card tech-card">
          <div class="ut-header">
            <span class="ut-icon">💡</span>
            <span class="ut-title">上传提示</span>
          </div>
          <div class="ut-list">
            <div class="ut-item">
              <span class="ut-num">1</span>
              <span>上传聊天截图或警情文档，系统自动提取文字</span>
            </div>
            <div class="ut-item">
              <span class="ut-num">2</span>
              <span>图片使用 OCR 识别，文档自动解析文字内容</span>
            </div>
            <div class="ut-item">
              <span class="ut-num">3</span>
              <span>提取的文字自动进入 AI 研判分析流程</span>
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
        :disabled="!uploadedFiles.length"
        @click="runAnalysis"
      >
        <span class="btn-icon">🔍</span>
        <span>{{ loading ? 'AI 正在处理文件...' : '开始识别分析' }}</span>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, clearImages, handleBeforeUpload, loading, removeImage, startImageAnalysis,
  uploadedImages: uploadedFiles
} = state
const analyzeMode = ref('auto')
const runAnalysis = () => {
  startImageAnalysis(analyzeMode.value)
}
</script>

<style scoped>
.upload-layout { display: grid; grid-template-columns: 1fr 320px; gap: 20px; }
.upload-main-card { padding: 0; }
.upload-dropzone { padding: 32px; }
.upload-dropzone :deep(.el-upload-dragger) {
  width: 100%; padding: 40px 20px;
  background: linear-gradient(135deg, rgba(0,198,255,0.03) 0%, rgba(0,132,255,0.06) 100%) !important;
  border: 2px dashed rgba(0,198,255,0.25) !important;
  border-radius: 16px !important;
  transition: all 0.3s ease !important;
}
.upload-dropzone :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-cyan) !important;
  border-style: solid !important;
  background: linear-gradient(135deg, rgba(0,198,255,0.06) 0%, rgba(0,132,255,0.1) 100%) !important;
  box-shadow: 0 0 30px rgba(0,198,255,0.15) !important;
  transform: translateY(-2px);
  animation: border-flow 3s ease infinite;
}
.upload-content { text-align: center; }
.upload-icon-ring {
  width: 72px; height: 72px; margin: 0 auto 16px;
  background: linear-gradient(135deg, rgba(0,198,255,0.15), rgba(0,132,255,0.1));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid rgba(0,198,255,0.2);
  animation: pulse-ring 2s ease-in-out infinite;
}
.upload-big-icon { font-size: 32px; }
.upload-title { font-size: 17px; color: var(--text-primary); font-weight: 600; margin-bottom: 6px; }
.upload-subtitle { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; }
.upload-link { color: var(--accent-cyan); font-weight: 500; cursor: pointer; }
.upload-hints { display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 8px; }
.uh-item { font-size: 12px; color: var(--text-muted); }
.uh-divider { font-size: 12px; color: rgba(255,255,255,0.1); }
.upload-limit { font-size: 11px; color: rgba(255,255,255,0.2); }
.upload-features {
  display: flex; align-items: center;
  padding: 14px 24px;
  border-top: 1px solid var(--border-primary);
  background: rgba(0,0,0,0.15);
  gap: 0;
}
.uf-item { display: flex; align-items: center; gap: 10px; flex: 1; justify-content: center; }
.uf-icon { font-size: 18px; }
.uf-info { display: flex; flex-direction: column; gap: 1px; }
.uf-title { font-size: 12px; color: var(--text-primary); font-weight: 500; }
.uf-desc { font-size: 10px; color: var(--text-muted); }
.uf-divider { width: 1px; height: 30px; background: var(--border-primary); }

.upload-side { display: flex; flex-direction: column; gap: 16px; }
.uploaded-list { background: var(--bg-card); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); padding: 16px; }
.ul-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.ul-title { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.ul-grid { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; }
.ul-card {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 8px;
  position: relative;
  transition: all 0.2s ease;
}
.ul-card:hover { border-color: rgba(0,198,255,0.2); background: rgba(0,0,0,0.3); }
.ul-preview { width: 40px; height: 40px; border-radius: 6px; overflow: hidden; flex-shrink: 0; }
.ul-preview img { width: 100%; height: 100%; object-fit: cover; }
.ul-file-icon { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(0,198,255,0.05); border-radius: 6px; }
.ulf-icon { font-size: 16px; line-height: 1; }
.ulf-ext { font-size: 7px; color: var(--text-muted); margin-top: 1px; }
.ul-meta { flex: 1; min-width: 0; }
.ul-name { font-size: 12px; color: var(--text-primary); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ul-type-badge { font-size: 9px; padding: 1px 6px; background: rgba(0,198,255,0.1); border-radius: 3px; color: var(--accent-cyan); }
.ul-size { font-size: 10px; color: var(--text-muted); }
.ul-remove {
  position: absolute; top: 4px; right: 4px;
  width: 18px; height: 18px; border-radius: 50%;
  border: none; background: rgba(239,68,68,0.2);
  color: var(--accent-red); font-size: 10px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.2s;
  line-height: 1;
}
.ul-card:hover .ul-remove { opacity: 1; }

.upload-tips-card { padding: 0; }
.ut-header { display: flex; align-items: center; gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--border-primary); }
.ut-icon { font-size: 16px; }
.ut-title { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.ut-list { padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; }
.ut-item { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.ut-num {
  width: 20px; height: 20px; border-radius: 50%;
  background: rgba(0,198,255,0.1); color: var(--accent-cyan);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; flex-shrink: 0;
}

@keyframes pulse-ring {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,198,255,0.2); }
  50% { box-shadow: 0 0 0 12px rgba(0,198,255,0); }
}

@keyframes border-flow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.mode-selector {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 12px 24px;
  border-top: 1px solid var(--border-primary);
  background: transparent;
}
.mode-label { font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.mode-opt { font-size: 12px; }
.mode-selector :deep(.el-radio-group) { gap: 0; }
.mode-selector :deep(.el-radio-button) { background: transparent !important; }
.mode-selector :deep(.el-radio-button__inner) {
  background: rgba(0,0,0,0.4) !important;
  border-color: var(--border-primary) !important;
  color: var(--text-secondary) !important;
  padding: 5px 14px;
  font-size: 12px;
  transition: all 0.2s;
}
.mode-selector :deep(.el-radio-button__inner:hover) {
  color: var(--text-primary) !important;
  border-color: rgba(0,198,255,0.3) !important;
}
.mode-selector :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: linear-gradient(135deg, rgba(0,198,255,0.2), rgba(0,132,255,0.15)) !important;
  border-color: var(--accent-cyan) !important;
  color: var(--accent-cyan) !important;
  box-shadow: none !important;
}
.mode-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, rgba(0,198,255,0.2), rgba(0,132,255,0.15)) !important;
  border-color: var(--accent-cyan) !important;
  color: var(--accent-cyan) !important;
}
.mode-selector :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-left-color: var(--border-primary) !important;
}
.mode-selector :deep(.el-radio-button:focus:not(.is-focus):not(:active):not(.is-active) .el-radio-button__inner) {
  box-shadow: none !important;
}
.mode-hint { font-size: 11px; color: var(--text-muted); flex: 1; min-width: 180px; }
</style>