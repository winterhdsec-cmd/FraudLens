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
          <el-icon class="input-big-icon"><EditPen /></el-icon>
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
              <el-icon><Delete /></el-icon> 清空
            </el-button>
            <el-button size="small" type="primary" @click="loadDemo" plain>
              <el-icon><Files /></el-icon> 加载测试案情
            </el-button>
          </div>
          <div class="input-toolbar-right">
            <span class="input-hint"><el-icon style="vertical-align:-2px"><InfoFilled /></el-icon> 建议包含：涉案时间、金额、联系方式、作案手法等关键信息</span>
          </div>
        </div>
      </div>

      <div class="input-features">
        <div class="input-feature-item">
          <el-icon class="input-feature-icon"><Search /></el-icon>
          <div class="input-feature-info">
            <span class="input-feature-title">关键词提取</span>
            <span class="input-feature-desc">自动识别涉案要素</span>
          </div>
        </div>
        <div class="input-feature-divider"></div>
        <div class="input-feature-item">
          <el-icon class="input-feature-icon"><Cpu /></el-icon>
          <div class="input-feature-info">
            <span class="input-feature-title">AI 研判分析</span>
            <span class="input-feature-desc">模块化协同分析推理</span>
          </div>
        </div>
        <div class="input-feature-divider"></div>
        <div class="input-feature-item">
          <el-icon class="input-feature-icon"><DataAnalysis /></el-icon>
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
          <el-icon class="input-tips-icon"><InfoFilled /></el-icon>
          <span class="input-tips-title">录入要点检测</span>
        </div>
        <div class="input-tips-list">
          <div class="input-tips-item" :class="{ active: hasTime }">
            <span class="input-tips-num">{{ hasTime ? '✓' : '○' }}</span>
            <span>涉案时间</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasAmount }">
            <span class="input-tips-num">{{ hasAmount ? '✓' : '○' }}</span>
            <span>涉案金额</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasPhone }">
            <span class="input-tips-num">{{ hasPhone ? '✓' : '○' }}</span>
            <span>联系方式</span>
          </div>
          <div class="input-tips-item" :class="{ active: hasMethod }">
            <span class="input-tips-num">{{ hasMethod ? '✓' : '○' }}</span>
            <span>作案手法</span>
          </div>
        </div>
      </div>

      <div class="input-tips-card">
        <div class="input-tips-header">
          <el-icon class="input-tips-icon"><Search /></el-icon>
          <span class="input-tips-title">关键词预览</span>
        </div>
        <div class="input-tips-body">
          <div v-if="inputText.length > 0" class="input-keywords">
            <el-tag v-for="kw in extractedKeywords" :key="kw" size="small" type="info" style="margin:2px">{{ kw }}</el-tag>
          </div>
          <div v-else class="input-keywords-empty">
            <el-icon class="input-keywords-empty-icon"><EditPen /></el-icon>
            <span class="input-keywords-empty-text">输入文本后自动提取关键词</span>
            <span class="input-keywords-empty-hint">例如：冒充客服 · 征信 · 安全账户 · 转账验证</span>
          </div>
        </div>
      </div>
      <div class="input-tips-card">
        <div class="input-tips-header">
          <el-icon class="input-tips-icon"><Money /></el-icon>
          <span class="input-tips-title">资金流水（可选）</span>
        </div>
        <div class="input-tips-body">
          <el-upload
            :auto-upload="true"
            :show-file-list="false"
            accept=".csv,.txt,.xlsx"
            :http-request="handleFundFlowUpload"
            class="ff-upload"
          >
            <el-button size="small" type="warning" plain>
              <el-icon><Money /></el-icon> 上传资金流水 CSV
            </el-button>
          </el-upload>
          <div v-if="fundFlowFileName" class="ff-status">
            <el-tag size="small" type="success">已附加 {{ fundFlowTx.length }} 笔 · {{ fundFlowFileName }}</el-tag>
            <el-button size="small" text type="danger" @click="clearFundFlow">清除</el-button>
          </div>
          <div v-else class="input-keywords-empty-text" style="margin-top:8px">
            上传银行/AMLSim 流水，自动参与资金链与回流闭环研判
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="action-bar">
    <div v-if="fundFlowFileName" class="ff-action-hint"><el-icon style="vertical-align:-2px"><Money /></el-icon> 已附加 {{ fundFlowTx.length }} 笔资金流水，将参与资金链/回流闭环研判</div>
    <el-button
      class="analyze-btn"
      type="primary"
      size="large"
      :loading="loading"
      :disabled="!inputText.trim()"
      @click="startAnalysis"
    >
      <span class="btn-icon"><el-icon><Promotion /></el-icon></span>
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
  hasTime, inputText, loadDemo, loading, startAnalysis, textLineCount,
  fundFlowTx, fundFlowFileName, importFundFlowFile, clearFundFlow
} = state

const handleFundFlowUpload = (options) => {
  importFundFlowFile(options.file)
}
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

.input-textarea::placeholder { color: var(--color-text-3); }

.input-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
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
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-1);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-text-2);
  transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
}

.input-tips-item.active {
  border-color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.input-tips-num { flex-shrink: 0; font-size: 14px; }

.input-tips-body { padding: 14px 16px; }

.input-keywords { display: flex; flex-wrap: wrap; gap: 4px; }

.input-keywords-empty { text-align: center; padding: 18px 0; }

.input-keywords-empty-icon { display: block; font-size: 26px; margin-bottom: 6px; color: var(--color-text-4); opacity: 0.8; }

.input-keywords-empty-text { font-size: 12px; color: var(--color-text-3); display: block; }

.input-keywords-empty-hint { font-size: 11px; color: var(--color-text-4); display: block; margin-top: 4px; line-height: 1.5; }

.action-bar { display: flex; justify-content: center; margin-top: 24px; }

.analyze-btn { min-width: 220px; height: 48px; font-size: 16px; font-weight: 500; }

.btn-icon { margin-right: 6px; }

.ff-upload { display: inline-block; }

.ff-status { display: flex; align-items: center; gap: 8px; margin-top: 10px; flex-wrap: wrap; }

.ff-action-hint {
  font-size: 12px;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  padding: 6px 12px;
  margin-bottom: 12px;
}

@keyframes input-pulse-ring {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,198,255,0.2); }
  50% { box-shadow: 0 0 0 12px rgba(0,198,255,0); }
}

@keyframes input-pulse-glow {
  0%, 100% { box-shadow: 0 0 10px rgba(0, 198, 255, 0.3); }
  50% { box-shadow: 0 0 25px rgba(0, 198, 255, 0.6), 0 0 50px rgba(0, 198, 255, 0.2); }
}
</style>