<template>
  <div class="login-overlay">
    <div class="login-bg-glow"></div>
    <div class="login-container">
      <div class="login-brand-panel">
        <div class="lbp-top">
          <div class="lbp-logo-wrapper">
            <div class="lbp-ring"></div>
            <div class="lbp-logo">
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2l8 3v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5l8-3z"/>
                <path d="M9 12l2 2 4-4"/>
              </svg>
            </div>
          </div>
          <h2 class="lbp-title">FraudLens 反诈智能研判系统</h2>
          <p class="lbp-subtitle">AI INTELLIGENT SYSTEM</p>
          <div class="lbp-desc">自动串并案 · 团伙发现 · 冻卡决策辅助<br>数据不出域的本地化反诈研判平台</div>
        </div>
        <div class="lbp-stats">
          <div class="lbp-stat">
            <span class="lbs-value">智能串并</span>
            <span class="lbs-label">自动关联同类案件</span>
          </div>
          <div class="lbp-stat">
            <span class="lbs-value">团伙发现</span>
            <span class="lbs-label">拓扑还原资金链路</span>
          </div>
          <div class="lbp-stat">
            <span class="lbs-value">冻卡辅助</span>
            <span class="lbs-label">可解释决策建议</span>
          </div>
          <div class="lbp-stat">
            <span class="lbs-value">安全可控</span>
            <span class="lbs-label">数据本地不出域</span>
          </div>
        </div>
        <div class="lbp-footer">
          <div class="lbp-tag" v-for="tag in loginTags" :key="tag">{{ tag }}</div>
        </div>
      </div>
      <div class="login-form-panel">
        <div class="lfp-header">
          <h3 class="lfp-title">用户登录</h3>
          <p class="lfp-desc">请输入您的账号信息以进入系统</p>
        </div>
        <div class="login-form">
          <div class="login-field">
            <el-icon class="login-field-icon"><User /></el-icon>
            <el-input v-model="loginForm.username" placeholder="用户名" size="large" class="login-input" @keyup.enter="handleLogin" />
          </div>
          <div class="login-field">
            <el-icon class="login-field-icon"><Lock /></el-icon>
            <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" class="login-input" show-password @keyup.enter="handleLogin" />
          </div>
          <div v-if="loginError" class="login-error">{{ loginError }}</div>
          <el-progress v-if="loginLoading" :percentage="loginProgress" :stroke-width="4" color="#00d4ff" :show-text="false" style="margin-bottom:12px" />
          <el-button class="login-btn" type="primary" size="large" :loading="loginLoading" @click="handleLogin">
            <span>{{ loginLoading ? '正在加载研判模型...' : '登 录' }}</span>
          </el-button>
        </div>
        <div class="lfp-security">
          <el-icon class="sec-icon"><Lock /></el-icon>
          <span class="sec-text">数据全程加密 · 安全可靠</span>
        </div>
      </div>
    </div>
    <div class="login-version">v3.0 · 大创项目成果展示</div>
  </div>
</template>

<script setup>
import { inject } from 'vue'

const appState = inject('appState')
const { loginForm, loginLoading, loginError, loginProgress, handleLogin } = appState

// 登录页能力标签（面向民警的价值语言，非技术指标）
const loginTags = ['自动串并案', '团伙发现', '冻卡决策辅助', '数据本地化']
</script>

<style scoped>
/* ====== 登录页面 ====== */
.login-overlay {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  background: var(--color-bg-page);
  overflow: hidden;
}

/* 背景光晕（与 showcase 风格一致：深底 + 青色光晕） */
.login-bg-glow {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at 30% 30%, rgba(0, 212, 255, 0.18), transparent 55%),
    radial-gradient(ellipse at 75% 75%, rgba(99, 102, 241, 0.14), transparent 55%),
    radial-gradient(ellipse at 50% 100%, rgba(139, 92, 246, 0.10), transparent 60%);
  pointer-events: none;
}

.login-container {
  display: flex;
  width: 880px;
  min-height: 520px;
  border-radius: var(--radius-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-1);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  position: relative;
}

.login-container::before, .login-container::after { display: none; }

/* ====== 左侧品牌面板（深色 cyan 科技风，与 showcase 风格一致） ====== */
.login-brand-panel {
  width: 420px;
  min-width: 420px;
  padding: 48px 40px 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(160deg, #0d1a2e 0%, #122441 55%, #0a1729 100%);
  border-right: 1px solid rgba(0, 212, 255, 0.12);
  position: relative;
  overflow: hidden;
}

/* 左侧面板装饰光晕 */
.login-brand-panel::before {
  content: '';
  position: absolute;
  top: -40%; left: -30%;
  width: 200%; height: 200%;
  background:
    radial-gradient(circle at 30% 30%, rgba(0, 212, 255, 0.12), transparent 45%),
    radial-gradient(circle at 70% 70%, rgba(139, 92, 246, 0.08), transparent 50%);
  pointer-events: none;
}

/* Logo区域 */
.lbp-top { text-align: center; }

.lbp-logo-wrapper {
  position: relative;
  width: 72px; height: 72px;
  margin: 0 auto 20px;
}

.lbp-ring { display: none; }

.lbp-logo {
  position: relative;
  width: 72px; height: 72px;
  display: flex; align-items: center; justify-content: center;
  font-size: 32px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.25), rgba(0, 212, 255, 0.05));
  border-radius: var(--radius-xl);
  border: 1px solid rgba(0, 212, 255, 0.4);
  color: #fff;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.25);
}

.lbp-title {
  font-size: 22px;
  color: #fff;
  margin: 0 0 6px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 2px;
  background: linear-gradient(180deg, #ffffff 0%, #e0f2ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
}

.lbp-subtitle {
  font-size: 11px;
  color: rgba(0, 212, 255, 0.75);
  letter-spacing: 4px;
  margin: 0 0 14px;
  font-weight: var(--font-weight-medium);
}

.lbp-desc {
  font-size: 13px;
  color: rgba(224, 242, 255, 0.78);
  line-height: 1.8;
  margin: 0;
}

/* 统计数据 */
.lbp-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 20px 0;
  border-top: 1px solid rgba(0, 212, 255, 0.12);
  border-bottom: 1px solid rgba(0, 212, 255, 0.12);
}

.lbp-stat {
  text-align: center;
  padding: 8px 4px;
  background: rgba(0, 212, 255, 0.04);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 212, 255, 0.12);
}

.lbp-stat:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.3);
}

.lbs-value {
  display: block;
  font-size: 22px;
  font-weight: var(--font-weight-bold);
  color: #fff;
  line-height: 1.2;
}

.lbs-label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 2px;
}

/* 底部标签 */
.lbp-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 14px;
  justify-content: center;
}

.lbp-tag {
  padding: 3px 10px;
  font-size: 11px;
  color: rgba(0, 212, 255, 0.85);
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  letter-spacing: 1px;
}

.lbp-tag:hover {
  background: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
}

/* ====== 右侧表单面板 ====== */
.login-form-panel {
  flex: 1;
  padding: 48px 44px 36px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: var(--color-bg-card);
}

.lfp-header {
  text-align: center;
  margin-bottom: 32px;
}

.lfp-title {
  font-size: 22px;
  color: var(--color-text-1);
  margin: 0 0 6px;
  font-weight: var(--font-weight-semibold);
  letter-spacing: 1px;
}

.lfp-desc {
  font-size: 13px;
  color: var(--color-text-3);
  margin: 0;
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login-field {
  position: relative;
}

.login-field-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  font-size: 16px;
  color: var(--color-text-3);
}

.login-input :deep(.el-input__wrapper) {
  padding-left: 44px;
  border-radius: var(--radius-md);
  background: var(--color-bg-card) !important;
  border: 1px solid var(--color-border-1);
  transition: all var(--transition-base);
  box-shadow: none !important;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 2px var(--color-primary-light) !important;
}

.login-input :deep(.el-input__inner) {
  color: var(--color-text-1);
  font-size: var(--font-size-base);
}

.login-input :deep(.el-input__inner::placeholder) {
  color: var(--color-text-4);
  font-size: var(--font-size-sm);
}

.login-input :deep(.el-input__suffix) {
  color: var(--color-text-3);
}

/* 错误提示 */
.login-error {
  color: var(--color-danger);
  font-size: 13px;
  text-align: center;
  background: var(--color-bg-hover);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-danger);
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  margin-top: 4px;
  border-radius: var(--radius-md);
  letter-spacing: 4px;
  font-weight: var(--font-weight-semibold);
}

.login-btn :deep(span) {
  letter-spacing: 4px;
}

/* 安全提示 */
.lfp-security {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--color-divider);
}

.sec-icon {
  font-size: 13px;
}

.sec-text {
  font-size: 12px;
  color: var(--color-text-3);
}

/* 底部版本号 */
.login-version {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: var(--color-text-4);
  letter-spacing: 2px;
  z-index: 1001;
  font-family: var(--font-family-mono);
}
</style>
