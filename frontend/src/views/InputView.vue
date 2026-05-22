<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left" style="border-left: 3px solid var(--accent-cyan); padding-left: 14px;">
      <h2 class="section-title">智能研判输入</h2>
      <p class="section-desc">输入案件描述或粘贴聊天记录，AI 自动分析提取关键信息</p>
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

  <div class="header-divider"></div>

  <div class="input-layout">
    <div class="input-main-card">
      <div class="input-zone">
        <div class="input-icon-ring">
          <span class="input-big-icon">📝</span>
        </div>
        <div class="input-title">案件文本录入</div>
        <div class="input-subtitle">粘贴 <span class="input-link">聊天记录</span>、<span class="input-link">报警笔录</span> 或 <span class="input-link">涉案描述</span></div>
        <div class="input-area">
          <textarea
            v-model="inputText"
            :rows="14"
            placeholder="粘贴聊天记录、报警笔录或涉案描述…"
            class="input-textarea"
          ></textarea>
        </div>
        <div class="input-toolbar-row">
          <div class="input-toolbar-left">
            <el-button size="small" @click="clearInput">
              <span style="font-size:14px">🗑️</span> 清空
            </el-button>
            <el-button size="small" type="primary" @click="loadDemo" plain>
              <span style="font-size:14px">📋</span> 加载测试案情
            </el-button>
          </div>
          <div class="input-toolbar-right">
            <span class="input-hint">💡 建议包含：涉案时间、金额、联系方式、作案手法等关键信息</span>
          </div>
        </div>
      </div>

      <div class="input-features">
        <div class="input-feature-item">
          <span class="input-feature-icon">🔍</span>
          <div class="input-feature-info">
            <span class="input-feature-title">关键词提取</span>
            <span class="input-feature-desc">自动识别涉案要素</span>
          </div>
        </div>
        <div class="input-feature-divider"></div>
        <div class="input-feature-item">
          <span class="input-feature-icon">🤖</span>
          <div class="input-feature-info">
            <span class="input-feature-title">AI 研判分析</span>
            <span class="input-feature-desc">多智能体协同推理</span>
          </div>
        </div>
        <div class="input-feature-divider"></div>
        <div class="input-feature-item">
          <span class="input-feature-icon">📊</span>
          <div class="input-feature-info">
            <span class="input-feature-title">结构化输出</span>
            <span class="input-feature-desc">自动归类案件要素</span>
          </div>
        </div>
      </div>
    </div>

    <div class="input-sidebar">
      <div class="input-tips-card">
        <div class="input-tips-header">
          <span class="input-tips-icon">💡</span>
          <span class="input-tips-title">录入要点检测</span>
        </div>
        <div class="input-tips-list">
          <div class="input-tips-item" :class="{ active: hasTime }">
            <span class="input-tips-num">{{ hasTime ? '✅' : '⬜' }}</span>
            <span>涉案时间</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasAmount }">
            <span class="input-tips-num">{{ hasAmount ? '✅' : '⬜' }}</span>
            <span>涉案金额</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasPhone }">
            <span class="input-tips-num">{{ hasPhone ? '✅' : '⬜' }}</span>
            <span>联系方式</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasMethod }">
            <span class="input-tips-num">{{ hasMethod ? '✅' : '⬜' }}</span>
            <span>作案手法</span>
          </div>
        </div>
      </div>

      <div class="input-tips-card">
        <div class="input-tips-header">
          <span class="input-tips-icon">🔍</span>
          <span class="input-tips-title">关键词预览</span>
        </div>
        <div class="input-tips-body">
          <div v-if="inputText.length > 0" class="input-keywords">
            <el-tag v-for="kw in extractedKeywords" :key="kw" size="small" type="info" style="margin:2px">{{ kw }}</el-tag>
          </div>
          <div v-else class="input-keywords-empty">
            <span class="input-keywords-empty-icon">📝</span>
            <span class="input-keywords-empty-text">输入文本后自动分析</span>
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
.header-divider { height: 2px; background: linear-gradient(90deg, transparent 0%, var(--accent-cyan) 20%, var(--accent-blue) 80%, transparent 100%); margin-bottom: 20px; border-radius: 1px; }

.input-layout { display: grid; grid-template-columns: 1fr 280px; gap: 20px; }

.input-main-card { background: var(--bg-card); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); overflow: hidden; display: flex; flex-direction: column; }

.input-zone { padding: 32px 32px 20px; text-align: center; }

.input-icon-ring {
  width: 72px; height: 72px; margin: 0 auto 16px;
  background: linear-gradient(135deg, rgba(0,198,255,0.15), rgba(0,132,255,0.1));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid rgba(0,198,255,0.2);
  animation: input-pulse-ring 2s ease-in-out infinite;
}

.input-big-icon { font-size: 32px; }

.input-title { font-size: 17px; color: var(--text-primary); font-weight: 600; margin-bottom: 6px; }

.input-subtitle { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.input-link { color: var(--accent-cyan); font-weight: 500; }

.input-area { margin-bottom: 16px; }

.input-textarea {
  width: 100%;
  min-height: 340px;
  padding: 18px 20px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(0,198,255,0.15);
  border-radius: var(--radius-md);
  color: #e2e8f0;
  font-size: 14px;
  line-height: 1.9;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
  font-family: inherit;
}

.input-textarea::placeholder { color: #475569; }

.input-textarea:focus {
  border-color: #00d4ff;
  box-shadow: 0 0 20px rgba(0,212,255,0.12);
  background: rgba(255,255,255,0.06);
}

.input-toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 0;
  border-top: 1px solid rgba(0,198,255,0.08);
  flex-wrap: wrap;
  gap: 10px;
}

.input-toolbar-left { display: flex; gap: 8px; align-items: center; }

.input-toolbar-right { display: flex; align-items: center; }

.input-hint { font-size: 12px; color: var(--text-muted); }

.input-features {
  display: flex; align-items: center;
  padding: 14px 24px;
  border-top: 1px solid var(--border-primary);
  background: rgba(0,0,0,0.15);
  gap: 0;
}

.input-feature-item { display: flex; align-items: center; gap: 10px; flex: 1; justify-content: center; }

.input-feature-icon { font-size: 18px; }

.input-feature-info { display: flex; flex-direction: column; gap: 1px; }

.input-feature-title { font-size: 12px; color: var(--text-primary); font-weight: 500; }

.input-feature-desc { font-size: 10px; color: var(--text-muted); }

.input-feature-divider { width: 1px; height: 30px; background: var(--border-primary); }

.input-sidebar { display: flex; flex-direction: column; gap: 16px; }

.input-tips-card { background: var(--bg-card); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); overflow: hidden; }

.input-tips-header { display: flex; align-items: center; gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--border-primary); background: rgba(0,0,0,0.15); }

.input-tips-icon { font-size: 16px; }

.input-tips-title { font-size: 13px; color: var(--text-primary); font-weight: 500; }

.input-tips-list { padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }

.input-tips-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.input-tips-item.active {
  border-color: rgba(16,185,129,0.3);
  background: rgba(16,185,129,0.08);
  color: #10b981;
}

.input-tips-num { flex-shrink: 0; font-size: 14px; }

.input-tips-body { padding: 14px 16px; }

.input-keywords { display: flex; flex-wrap: wrap; gap: 4px; }

.input-keywords-empty { text-align: center; padding: 16px 0; }

.input-keywords-empty-icon { display: block; font-size: 28px; margin-bottom: 6px; opacity: 0.4; }

.input-keywords-empty-text { font-size: 12px; color: var(--text-muted); }

.action-bar { display: flex; justify-content: center; margin-top: 24px; }

.analyze-btn { min-width: 220px; height: 48px; font-size: 16px; animation: input-pulse-glow 2s ease-in-out infinite; }

.btn-icon { margin-right: 6px; }

@keyframes input-pulse-ring {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,198,255,0.2); }
  50% { box-shadow: 0 0 0 12px rgba(0,198,255,0); }
}

@keyframes input-pulse-glow {
  0%, 100% { box-shadow: 0 0 10px rgba(0, 198, 255, 0.3); }
  50% { box-shadow: 0 0 25px rgba(0, 198, 255, 0.6), 0 0 50px rgba(0, 198, 255, 0.2); }
}
</style>