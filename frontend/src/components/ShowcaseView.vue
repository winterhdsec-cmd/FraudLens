<template>
  <div class="showcase-page">
    <!-- 导航栏 -->
    <nav class="showcase-nav">
      <div class="nav-brand">
        <span class="brand-icon">🔮</span>
        <span class="brand-text">灵犀智瞳</span>
      </div>
      <div class="nav-links">
        <a href="#hero" @click="scrollToSection('hero')">首页</a>
        <a href="#problem" @click="scrollToSection('problem')">痛点</a>
        <a href="#solution" @click="scrollToSection('solution')">流程</a>
        <a href="#technology" @click="scrollToSection('technology')">技术</a>
        <a href="#value" @click="scrollToSection('value')">价值</a>
      </div>
      <button class="nav-demo-btn" @click="scrollToSection('solution')">流程演示</button>
    </nav>

    <!-- 动态背景粒子 -->
    <div class="particle-container">
      <div v-for="n in 30" :key="n" class="particle" :style="{ left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`, animationDelay: `${Math.random() * 5}s` }"></div>
    </div>

    <!-- 区块A：英雄区 -->
    <section id="hero" class="hero-section">
      <div class="hero-content">
        <div class="hero-text">
          <div class="hero-badge">AI 反诈智能研判系统</div>
          <h1 class="hero-title">灵犀智瞳</h1>
          <p class="hero-subtitle">AI驱动的电信诈骗智能研判系统</p>
          
          <!-- 主统计数据 -->
          <div class="hero-stats">
            <div class="stat-item" v-for="(stat, index) in heroStats" :key="index">
              <div class="stat-icon">{{ stat.icon }}</div>
              <div class="stat-number" :data-target="stat.value">{{ animatedStats[index] || 0 }}{{ stat.suffix }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>

          <!-- 功能亮点 -->
          <div class="hero-highlights">
            <div class="highlight-item" v-for="(item, index) in heroHighlights" :key="index">
              <span class="highlight-icon">{{ item.icon }}</span>
              <span class="highlight-text">{{ item.text }}</span>
            </div>
          </div>

          <!-- 技术标签 -->
          <div class="hero-tech-tags">
            <span class="tech-tag">NLP语义分析</span>
            <span class="tech-tag">图计算聚类</span>
            <span class="tech-tag">知识图谱</span>
            <span class="tech-tag">智能报告生成</span>
          </div>

          <div class="hero-actions">
            <button class="btn-primary" @click="scrollToSection('solution')">核心流程</button>
            <button class="btn-secondary" @click="scrollToSection('technology')">技术能力</button>
          </div>
        </div>
        
        <div class="hero-visual">
          <!-- 动态数据卡片 -->
          <div class="hero-card card-1" :style="{ animationDelay: '0s' }">
            <div class="card-icon">🎯</div>
            <div class="card-text">精准识别</div>
            <div class="card-value">92%</div>
            <div class="card-trend positive">↑ 3.2%</div>
          </div>
          <div class="hero-card card-2" :style="{ animationDelay: '0.3s' }">
            <div class="card-icon">⚡</div>
            <div class="card-text">极速响应</div>
            <div class="card-value">10秒</div>
            <div class="card-trend positive">↓ 45%</div>
          </div>
          <div class="hero-card card-3" :style="{ animationDelay: '0.6s' }">
            <div class="card-icon">🔗</div>
            <div class="card-text">深度关联</div>
            <div class="card-value">8个团伙</div>
            <div class="card-trend neutral">+2 新增</div>
          </div>
          <div class="hero-card card-4" :style="{ animationDelay: '0.9s' }">
            <div class="card-icon">🛡️</div>
            <div class="card-text">风险预警</div>
            <div class="card-value">实时</div>
            <div class="card-trend positive">24/7</div>
          </div>

          <!-- 网络关系预览 -->
          <div class="mini-network">
            <svg width="100%" height="100%" viewBox="0 0 300 300">
              <circle cx="150" cy="150" r="15" fill="#FF3B5C" class="mini-node"/>
              <circle cx="80" cy="100" r="8" fill="#00E5FF" class="mini-node" style="animation-delay: 0.5s"/>
              <circle cx="220" cy="120" r="8" fill="#00E5FF" class="mini-node" style="animation-delay: 1s"/>
              <circle cx="100" cy="200" r="8" fill="#00E5FF" class="mini-node" style="animation-delay: 1.5s"/>
              <circle cx="240" cy="180" r="8" fill="#00E5FF" class="mini-node" style="animation-delay: 2s"/>
              <line x1="150" y1="150" x2="80" y2="100" stroke="rgba(0,229,255,0.4)" stroke-width="2"/>
              <line x1="150" y1="150" x2="220" y2="120" stroke="rgba(0,229,255,0.4)" stroke-width="2"/>
              <line x1="150" y1="150" x2="100" y2="200" stroke="rgba(0,229,255,0.4)" stroke-width="2"/>
              <line x1="150" y1="150" x2="240" y2="180" stroke="rgba(0,229,255,0.4)" stroke-width="2"/>
            </svg>
          </div>
        </div>
      </div>
      <div class="hero-wave"></div>
    </section>

    <!-- 区块B：痛点洞察 -->
    <section id="problem" class="problem-section">
      <div class="section-header">
        <h2 class="section-title">传统研判痛点</h2>
        <p class="section-desc">数据孤岛、人工瓶颈、响应迟缓</p>
      </div>
      <div class="problem-cards">
        <div class="problem-card" v-for="(card, index) in problemCards" :key="index">
          <div class="card-icon-large">{{ card.icon }}</div>
          <h3 class="card-title">{{ card.title }}</h3>
          <p class="card-desc">{{ card.desc }}</p>
          <div v-if="card.progress" class="card-progress">
            <div class="progress-label">{{ card.progress.label }}</div>
            <el-progress :percentage="card.progress.value" :color="card.progress.color" stroke-width="6" :show-text="false" />
            <div class="progress-value">{{ card.progress.text }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 区块C：核心流程演示 -->
    <section id="solution" class="solution-section">
      <div class="section-header">
        <h2 class="section-title">核心研判流程</h2>
        <p class="section-desc">从数据接入到报告生成的完整闭环</p>
      </div>
      
      <div class="flow-container">
        <div class="flow-step" v-for="(step, index) in flowSteps" :key="index" :class="{ active: currentStep === index }">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-icon">{{ step.icon }}</div>
          <h3 class="step-title">{{ step.title }}</h3>
          <p class="step-desc">{{ step.desc }}</p>
          <div class="step-content">
            <div v-if="index === 0" class="step-data-flow">
              <div class="data-item" v-for="(item, i) in dataItems" :key="i">
                {{ item.icon }}
              </div>
            </div>
            <div v-if="index === 1" class="step-architecture">
              <div class="architecture-diagram">
                <div class="arch-node input-layer">数据接入层</div>
                <div class="arch-arrow">→</div>
                <div class="arch-node nlp-layer">NLP语义分析</div>
                <div class="arch-arrow">→</div>
                <div class="arch-node graph-layer">图计算聚类</div>
                <div class="arch-arrow">→</div>
                <div class="arch-node kg-layer">知识图谱</div>
                <div class="arch-arrow">→</div>
                <div class="arch-node output-layer">研判输出层</div>
              </div>
              <p class="arch-desc">融合语义指纹与无监督学习，实现隐性团伙挖掘</p>
            </div>
            <div v-if="index === 2" class="step-report">
              <div class="report-preview">
                <div class="report-header">
                  <span class="report-title">案件研判报告</span>
                  <span class="report-date">{{ currentTime }}</span>
                </div>
                <div class="report-content">
                  <div class="report-section">
                    <span class="section-label">案件定性</span>
                    <span class="section-value">冒充电商物流客服类</span>
                  </div>
                  <div class="report-section">
                    <span class="section-label">风险等级</span>
                    <el-tag type="danger" effect="dark">高风险</el-tag>
                  </div>
                  <div class="report-section">
                    <span class="section-label">处置建议</span>
                    <span class="section-value">立即止付、冻结涉案账户</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="flow-controls">
        <button class="btn-secondary" @click="prevStep" :disabled="currentStep === 0">← 上一步</button>
        <div class="step-indicators">
          <span v-for="i in 3" :key="i" :class="{ active: currentStep === i - 1 }">{{ i }}</span>
        </div>
        <button class="btn-primary" @click="nextStep" v-if="currentStep < 2">下一步 →</button>
        <button class="btn-primary" @click="scrollToSection('technology')" v-else>查看技术 →</button>
      </div>
    </section>

    <!-- 区块D：技术深度 -->
    <section id="technology" class="tech-section">
      <div class="section-header">
        <h2 class="section-title">核心技术能力</h2>
        <p class="section-desc">四大技术支撑，保障研判效能</p>
      </div>
      
      <div class="tech-grid">
        <div class="tech-card" v-for="(tech, index) in techCards" :key="index">
          <div class="tech-header">
            <span class="tech-icon">{{ tech.icon }}</span>
            <div class="tech-title-row">
              <h3 class="tech-title">{{ tech.title }}</h3>
              <span class="tech-subtitle">{{ tech.subtitle }}</span>
            </div>
          </div>
          <div class="tech-content">
            <div v-if="index === 0" ref="radarChartRef" class="tech-chart"></div>
            <div v-if="index === 1" class="architecture-panel">
              <div class="arch-feature" v-for="(feature, i) in tech.features" :key="i">
                <span class="feature-icon">{{ getFeatureIcon(i) }}</span>
                <span class="feature-text">{{ feature }}</span>
              </div>
            </div>
            <div v-if="index === 2" class="quality-panel-mini">
              <div class="quality-item-mini" v-for="(item, i) in qualityData" :key="i">
                <div class="quality-label-mini">{{ item.label }}</div>
                <el-progress :percentage="item.value" :color="item.color" stroke-width="4" :show-text="false" />
                <span class="quality-value-mini">{{ item.value }}%</span>
              </div>
            </div>
            <div v-if="index === 3" class="comparison-chart">
              <div class="comparison-header">研判效能对比</div>
              <div class="comparison-bars">
                <div class="bar-item">
                  <span class="bar-label">传统方式</span>
                  <div class="bar-container">
                    <div class="bar bar-traditional" style="width: 25%"></div>
                  </div>
                  <span class="bar-value">2小时</span>
                </div>
                <div class="bar-item">
                  <span class="bar-label">灵犀智瞳</span>
                  <div class="bar-container">
                    <div class="bar bar-system" style="width: 100%"></div>
                  </div>
                  <span class="bar-value">10秒</span>
                </div>
              </div>
              <div class="comparison-note">经内部测试，研判效率提升约8倍</div>
              <div class="accuracy-display">
                <span>准确率：</span>
                <span class="accuracy-value">92%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 区块E：价值总结 -->
    <section id="value" class="value-section">
      <div class="section-header">
        <h2 class="section-title">助力实战，守护安全</h2>
      </div>
      
      <div class="value-content">
        <div class="testimonials">
          <div class="testimonial-card" v-for="(item, index) in testimonials" :key="index">
            <div class="client-logo">{{ item.logo }}</div>
            <p class="testimonial-text">{{ item.text }}</p>
            <div class="client-name">{{ item.source }}</div>
          </div>
        </div>
        
        <div class="social-value">
          <h3 class="social-title">实战成效</h3>
          <div class="value-stats">
            <div class="value-stat" v-for="(stat, index) in valueStats" :key="index">
              <div class="value-icon">{{ stat.icon }}</div>
              <div class="value-number">{{ stat.value }}</div>
              <div class="value-label">{{ stat.label }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="final-cta">
        <h3>让AI成为反诈最锋利的武器</h3>
        <p>携手共建安全网络环境</p>
        <div class="final-buttons">
          <button class="btn-primary">获取演示</button>
          <button class="btn-secondary">联系我们</button>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="showcase-footer">
      <div class="footer-content">
        <div class="footer-brand">
          <span class="brand-icon">🔮</span>
          <span class="brand-text">灵犀智瞳</span>
          <span class="brand-sub">AI反诈智能研判系统</span>
        </div>
        <div class="footer-links">
          <a href="#">关于我们</a>
          <a href="#">技术文档</a>
          <a href="#">合作伙伴</a>
          <a href="#">联系方式</a>
        </div>
        <div class="footer-copyright">
          © 2024 灵犀智瞳. All rights reserved.
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

// 英雄区数据 - 修改为真实可信的中小规模数据
const heroStats = [
  { icon: '📊', value: 127, suffix: '', label: '累计分析案件' },
  { icon: '👤', value: 8, suffix: '', label: '识别犯罪团伙' },
  { icon: '⏱️', value: 10, suffix: '秒', label: '平均响应时间' },
  { icon: '🎯', value: 92, suffix: '%', label: '模型准确率' }
]

const animatedStats = ref([0, 0, 0, 0])

// 功能亮点
const heroHighlights = [
  { icon: '🔍', text: '智能语义分析' },
  { icon: '🔗', text: '团伙关联挖掘' },
  { icon: '📈', text: '风险等级评估' },
  { icon: '📄', text: '自动报告生成' }
]

// 痛点卡片数据 - 使用专业公安术语
const problemCards = [
  {
    icon: '⏳',
    title: '研判效率瓶颈',
    desc: '传统人工串并案平均耗时约2小时，面对日均数百条报警记录力不从心',
    progress: { label: '平均研判周期', value: 120, color: '#FF6B35', text: '2小时/案' }
  },
  {
    icon: '🔒',
    title: '数据孤岛严重',
    desc: '涉案数据分散在接处警、银行、运营商等多个系统，难以形成完整证据链',
    progress: { label: '跨系统数据打通率', value: 45, color: '#FFB800', text: '45%' }
  },
  {
    icon: '🎭',
    title: '犯罪手段迭代',
    desc: '诈骗话术持续变种，传统规则引擎漏报率高达18%，难以应对新型手法',
    progress: { label: '规则引擎漏报率', value: 18, color: '#FF3B5C', text: '18%' }
  }
]

// 流程步骤数据 - 使用专业术语描述输入-处理-输出
const flowSteps = [
  {
    icon: '📥',
    title: '多源数据智能注入',
    desc: '支持聊天记录、语音转写、图片证据、结构化数据等多格式接入',
    input: '报案记录、涉案截图、通话录音',
    process: '数据清洗、格式标准化、特征提取',
    output: '统一数据湖、特征向量库'
  },
  {
    icon: '🤖',
    title: 'AI深度研判与团伙聚类',
    desc: '基于Transformer语义指纹提取 + HDBSCAN无监督图聚类算法',
    input: '清洗后的涉案数据、历史案件库',
    process: '语义分析、实体识别、关联挖掘、团伙发现',
    output: '团伙画像、风险评级、关联图谱'
  },
  {
    icon: '📄',
    title: '智能报告生成与处置建议',
    desc: '自动化生成研判报告，包含案件定性、风险评估、处置建议',
    input: '团伙画像、关联证据、风险指标',
    process: '报告模板匹配、内容自动填充、建议生成',
    output: '标准化研判报告、处置预案、督办清单'
  }
]

const dataItems = [
  { icon: '💬' },
  { icon: '📞' },
  { icon: '📷' },
  { icon: '📊' }
]

const currentStep = ref(0)

// 技术卡片数据 - 添加详细技术描述
const techCards = [
  {
    icon: '🎯',
    title: '团伙画像分析',
    subtitle: '多维能力评估',
    features: ['技术能力评估', '组织严密性分析', '反侦察能力研判', '社会危害评级', '作案频率统计']
  },
  {
    icon: '🏗️',
    title: '系统核心架构',
    subtitle: '安全合规设计',
    features: ['数据不出域混合云架构', 'Docker容器化一键部署', '多源数据安全接入网关', '等保三级安全合规']
  },
  {
    icon: '📊',
    title: '数据质量评估',
    subtitle: '智能评分体系',
    features: ['数据完整性检测', '涉诈密度分析', '平台线索关联', '综合质量评分']
  },
  {
    icon: '⚡',
    title: '研判效能对比',
    subtitle: '效率提升验证',
    features: ['传统方式：2小时/案', '本系统：10秒/案', '效率提升：约8倍', '准确率：92%']
  }
]

const qualityData = [
  { label: '完整性', value: 95, color: '#00E5FF' },
  { label: '涉诈密度', value: 82, color: '#FFB800' },
  { label: '平台线索', value: 88, color: '#00D4AA' },
  { label: '综合评分', value: 88, color: '#00E5FF' }
]

// 客户证言数据
const testimonials = [
  {
    logo: '🏛️',
    text: '系统在试点中展现出优秀的线索挖掘能力，有效提升了研判效率。',
    source: '某市反诈中心'
  },
  {
    logo: '🛡️',
    text: 'AI辅助研判大幅缩短了案件分析周期，为快速响应提供了有力支撑。',
    source: '某单位'
  }
]

// 社会价值数据 - 修改为更合理的数据
const valueStats = [
  { icon: '�', value: '3 起', label: '辅助破案' },
  { icon: '�️', value: 'XX 万元', label: '避免损失' },
  { icon: '⏱️', value: '8 倍', label: '效率提升' },
  { icon: '📈', value: '92%', label: '准确率' }
]

const currentTime = new Date().toLocaleDateString('zh-CN')

// Refs
const radarChartRef = ref(null)

// 方法
const scrollToSection = (sectionId) => {
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const nextStep = () => {
  if (currentStep.value < 2) {
    currentStep.value++
  }
}

const getFeatureIcon = (index) => {
  const icons = ['🔒', '📦', '🚪', '🛡️', '⚙️', '🔑']
  return icons[index] || '📋'
}

const animateNumbers = () => {
  heroStats.forEach((stat, index) => {
    const duration = 2000
    const steps = 60
    const increment = stat.value / steps
    let current = 0
    const interval = setInterval(() => {
      current += increment
      if (current >= stat.value) {
        animatedStats.value[index] = stat.value
        clearInterval(interval)
      } else {
        animatedStats.value[index] = Math.floor(current)
      }
    }, duration / steps)
  })
}

const initCharts = () => {
  // 雷达图
  const radarEl = document.querySelector('.tech-chart')
  if (radarEl) {
    const chart = echarts.init(radarEl)
    chart.setOption({
      backgroundColor: 'transparent',
      radar: {
        indicator: [
          { name: '技术能力', max: 100 },
          { name: '组织严密性', max: 100 },
          { name: '反侦察能力', max: 100 },
          { name: '社会危害', max: 100 },
          { name: '作案频率', max: 100 }
        ],
        shape: 'polygon',
        splitNumber: 5,
        axisName: { color: '#94A3B8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        splitArea: {
          show: true,
          areaStyle: { color: ['rgba(0,229,255,0.05)', 'rgba(0,229,255,0.02)'] }
        },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
      },
      series: [{
        type: 'radar',
        data: [{
          value: [85, 75, 80, 90, 70],
          name: '团伙画像',
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { width: 2, color: '#00E5FF' },
          areaStyle: { color: 'rgba(0,229,255,0.3)' },
          itemStyle: { color: '#00E5FF' }
        }]
      }]
    })
    window.addEventListener('resize', () => chart.resize())
  }
}

onMounted(() => {
  animateNumbers()
  setTimeout(initCharts, 500)
})

onUnmounted(() => {
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped>
/* 页面基础样式 */
.showcase-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #020812 0%, #050D1A 50%, #0B1222 100%);
  color: #E8EDF5;
  font-family: 'Inter', 'JetBrains Mono', 'Roboto', sans-serif;
  overflow-x: hidden;
  position: relative;
}

/* 动态粒子背景 */
.particle-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(0, 229, 255, 0.6);
  border-radius: 50%;
  animation: particleFloat 8s ease-in-out infinite;
}

@keyframes particleFloat {
  0%, 100% {
    transform: translateY(0) translateX(0);
    opacity: 0.2;
  }
  25% {
    transform: translateY(-50px) translateX(20px);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-100px) translateX(-10px);
    opacity: 0.4;
  }
  75% {
    transform: translateY(-50px) translateX(-20px);
    opacity: 0.8;
  }
}

/* 导航栏 */
.showcase-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 76px;
  background: linear-gradient(135deg, rgba(8, 15, 30, 0.98) 0%, rgba(5, 10, 22, 0.98) 100%);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 198, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  z-index: 1000;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
}

.showcase-nav::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 198, 255, 0.5), rgba(0, 212, 170, 0.3), transparent);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  font-size: 32px;
  filter: drop-shadow(0 0 15px rgba(0, 198, 255, 0.6));
}

.brand-text {
  font-size: 22px;
  font-weight: 800;
  background: linear-gradient(135deg, #00C6FF 0%, #00E5FF 50%, #00D4AA 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
}

.nav-links {
  display: flex;
  gap: 36px;
}

.nav-links a {
  color: #8B9BB4;
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
  position: relative;
}

.nav-links a::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #00C6FF, #00D4AA);
  transition: width 0.3s ease;
}

.nav-links a:hover {
  color: #00C6FF;
}

.nav-links a:hover::after {
  width: 100%;
}

.nav-demo-btn {
  background: linear-gradient(135deg, #00C6FF 0%, #0099CC 50%, #0080AA 100%);
  border: 1px solid rgba(0, 198, 255, 0.5);
  color: #020812;
  padding: 12px 28px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.35s ease;
  box-shadow: 0 4px 20px rgba(0, 198, 255, 0.3);
}

.nav-demo-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 30px rgba(0, 198, 255, 0.45);
}

/* 英雄区 */
.hero-section {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 0 48px;
  background: linear-gradient(180deg, #020812 0%, #050D1A 50%, #0B1222 100%);
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(ellipse 60% 30% at 50% -10%, rgba(0, 198, 255, 0.15) 0%, transparent 60%),
    radial-gradient(ellipse 40% 20% at 50% 110%, rgba(0, 102, 204, 0.1) 0%, transparent 55%),
    radial-gradient(ellipse 30% 25% at 50% 50%, rgba(0, 198, 255, 0.04) 0%, transparent 50%),
    linear-gradient(rgba(0, 198, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 198, 255, 0.03) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 100% 100%, 50px 50px, 50px 50px;
}

.hero-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  max-width: 1400px;
  width: 100%;
  position: relative;
  z-index: 1;
  padding-top: 70px;
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-badge {
  display: inline-block;
  background: linear-gradient(135deg, rgba(0, 198, 255, 0.15) 0%, rgba(0, 198, 255, 0.05) 100%);
  border: 1px solid rgba(0, 198, 255, 0.3);
  color: #00C6FF;
  padding: 10px 24px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 500;
  width: fit-content;
  letter-spacing: 1px;
}

.hero-title {
  font-size: 64px;
  font-weight: 900;
  margin: 0;
  background: linear-gradient(135deg, #00C6FF 0%, #00E5FF 30%, #FFFFFF 50%, #00D4AA 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 3px;
  text-shadow: 0 0 60px rgba(0, 198, 255, 0.3);
}

.hero-subtitle {
  font-size: 24px;
  color: #8B9BB4;
  margin: 0;
  font-weight: 500;
  opacity: 0.9;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 30px;
}

.stat-item {
  background: linear-gradient(135deg, rgba(10, 20, 36, 0.9) 0%, rgba(5, 10, 22, 0.9) 100%);
  border: 1px solid rgba(0, 198, 255, 0.15);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  transition: all 0.35s ease;
  position: relative;
  overflow: hidden;
}

.stat-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 198, 255, 0.4), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.stat-item:hover {
  transform: translateY(-5px);
  border-color: rgba(0, 198, 255, 0.4);
  box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4);
}

.stat-item:hover::before {
  opacity: 1;
}

.stat-icon {
  font-size: 24px;
  margin-bottom: 10px;
  filter: drop-shadow(0 0 10px rgba(0, 198, 255, 0.4));
}

.stat-number {
  font-size: 36px;
  font-weight: 800;
  color: #00C6FF;
  font-family: 'JetBrains Mono', monospace;
}

.stat-label {
  font-size: 13px;
  color: #8B9BB4;
  margin-top: 10px;
  opacity: 0.85;
}

/* 技术标签 */
.hero-tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}

.tech-tag {
  padding: 6px 14px;
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 20px;
  font-size: 12px;
  color: #00E5FF;
}

.hero-actions {
  display: flex;
  gap: 16px;
  margin-top: 30px;
}

.btn-primary {
  background: linear-gradient(135deg, #00E5FF, #00B8CC);
  border: none;
  color: #0B0F19;
  padding: 14px 32px;
  border-radius: 8px;
  font-weight: bold;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 229, 255, 0.3);
}

.btn-secondary {
  background: transparent;
  border: 1px solid rgba(0, 229, 255, 0.4);
  color: #00E5FF;
  padding: 14px 32px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.btn-secondary:hover {
  background: rgba(0, 229, 255, 0.1);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hero-visual {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.hero-card {
  position: absolute;
  background: rgba(26, 31, 46, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 14px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(12px);
  animation: cardFloat 4s ease-in-out infinite;
  transition: transform 0.3s, box-shadow 0.3s;
}

.hero-card:hover {
  transform: scale(1.08);
  box-shadow: 0 8px 30px rgba(0, 229, 255, 0.2);
}

.card-1 {
  top: 5%;
  left: 5%;
}

.card-2 {
  top: 45%;
  right: 5%;
}

.card-3 {
  bottom: 10%;
  left: 25%;
}

.card-4 {
  top: 20%;
  left: 55%;
}

@keyframes cardFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.card-icon {
  font-size: 30px;
}

.card-text {
  font-size: 12px;
  color: #8B9BB4;
}

.card-trend {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 10px;
  margin-top: 4px;
}

.card-trend.positive {
  background: rgba(34, 197, 94, 0.15);
  color: #22C55E;
}

.card-trend.neutral {
  background: rgba(0, 229, 255, 0.15);
  color: #00E5FF;
}

/* 迷你网络图 */
.mini-network {
  position: absolute;
  width: 200px;
  height: 200px;
  bottom: 5%;
  right: 15%;
  opacity: 0.8;
}

.mini-node {
  animation: nodePulse 2s ease-in-out infinite;
}

@keyframes nodePulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.7;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
}

.hero-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: linear-gradient(180deg, transparent, #1A1F2E);
}

/* 通用区块样式 */
.section-header {
  text-align: center;
  margin-bottom: 50px;
}

.section-title {
  font-size: 32px;
  font-weight: bold;
  margin: 0 0 14px 0;
  color: #E8EDF5;
}

.section-desc {
  font-size: 15px;
  color: #8B9BB4;
  margin: 0;
}

/* 痛点洞察区块 */
.problem-section {
  padding: 80px 40px;
  background: #1A1F2E;
}

.problem-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.problem-card {
  background: rgba(11, 15, 25, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 14px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: transform 0.3s, border-color 0.3s;
}

.problem-card:hover {
  transform: translateY(-5px);
  border-color: rgba(0, 229, 255, 0.25);
}

.card-icon-large {
  font-size: 42px;
}

.card-title {
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  color: #E8EDF5;
}

.card-desc {
  font-size: 13px;
  color: #8B9BB4;
  margin: 0;
  flex: 1;
}

.card-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-label {
  font-size: 12px;
  color: #8B9BB4;
}

.progress-value {
  font-size: 14px;
  font-weight: bold;
  color: #FF6B35;
}

/* 核心流程区块 */
.solution-section {
  padding: 80px 40px;
  background: #0B0F19;
}

.flow-container {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto 40px;
}

.flow-step {
  flex: 1;
  background: rgba(26, 31, 46, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 14px;
  padding: 28px;
  text-align: center;
  transition: all 0.4s;
  position: relative;
}

.flow-step.active {
  border-color: #00E5FF;
  background: rgba(0, 229, 255, 0.04);
  box-shadow: 0 0 25px rgba(0, 229, 255, 0.15);
}

.step-number {
  position: absolute;
  top: -14px;
  left: 50%;
  transform: translateX(-50%);
  width: 28px;
  height: 28px;
  background: #0B0F19;
  border: 2px solid #00E5FF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #00E5FF;
  font-size: 13px;
}

.step-icon {
  font-size: 36px;
  margin: 18px 0;
}

.step-title {
  font-size: 17px;
  font-weight: bold;
  margin: 0 0 8px 0;
  color: #E8EDF5;
}

.step-desc {
  font-size: 12px;
  color: #8B9BB4;
  margin: 0;
}

.step-content {
  margin-top: 18px;
  min-height: 140px;
}

.step-data-flow {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.data-item {
  width: 56px;
  height: 56px;
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

/* 技术架构示意图 */
.step-architecture {
  padding: 10px;
}

.architecture-diagram {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.arch-node {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  color: #E8EDF5;
  text-align: center;
}

.input-layer {
  background: rgba(0, 229, 255, 0.2);
  border: 1px solid rgba(0, 229, 255, 0.4);
}

.nlp-layer {
  background: rgba(156, 136, 255, 0.2);
  border: 1px solid rgba(156, 136, 255, 0.4);
}

.graph-layer {
  background: rgba(251, 191, 36, 0.2);
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.kg-layer {
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.output-layer {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.arch-arrow {
  color: #00E5FF;
  font-size: 14px;
}

.arch-desc {
  font-size: 11px;
  color: #8B9BB4;
  text-align: center;
  margin-top: 12px;
  line-height: 1.5;
}

.step-report {
  display: flex;
  justify-content: center;
}

.report-preview {
  background: rgba(11, 15, 25, 0.8);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  padding: 14px;
  min-width: 240px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.report-title {
  font-weight: bold;
  color: #00E5FF;
  font-size: 13px;
}

.report-date {
  font-size: 11px;
  color: #8B9BB4;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-label {
  font-size: 11px;
  color: #8B9BB4;
}

.section-value {
  font-size: 12px;
  color: #E8EDF5;
}

.flow-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
}

.step-indicators {
  display: flex;
  gap: 8px;
}

.step-indicators span {
  width: 28px;
  height: 28px;
  background: rgba(11, 15, 25, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #8B9BB4;
  transition: all 0.3s;
}

.step-indicators span.active {
  background: #00E5FF;
  border-color: #00E5FF;
  color: #0B0F19;
}

/* 技术深度区块 */
.tech-section {
  padding: 80px 40px;
  background: #1A1F2E;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.tech-card {
  background: rgba(11, 15, 25, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 14px;
  padding: 26px;
  transition: transform 0.3s, border-color 0.3s;
}

.tech-card:hover {
  transform: translateY(-3px);
  border-color: rgba(0, 229, 255, 0.25);
}

.tech-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.tech-icon {
  font-size: 24px;
}

.tech-title {
  font-size: 17px;
  font-weight: bold;
  margin: 0;
  color: #E8EDF5;
}

.tech-content {
  min-height: 180px;
}

.tech-chart {
  width: 100%;
  height: 180px;
}

/* 架构面板 */
.architecture-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.arch-feature {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: rgba(0, 229, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(0, 229, 255, 0.1);
}

.feature-icon {
  font-size: 18px;
}

.feature-text {
  font-size: 13px;
  color: #E8EDF5;
}

.quality-panel-mini {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.quality-item-mini {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quality-label-mini {
  width: 56px;
  font-size: 12px;
  color: #8B9BB4;
}

.quality-value-mini {
  width: 36px;
  font-size: 12px;
  color: #00E5FF;
  text-align: right;
}

.comparison-chart {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comparison-header {
  font-size: 14px;
  font-weight: 500;
  color: #E8EDF5;
  margin-bottom: 4px;
}

.comparison-bars {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 72px;
  font-size: 12px;
  color: #8B9BB4;
}

.bar-container {
  flex: 1;
  height: 20px;
  background: rgba(11, 15, 25, 0.6);
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 4px;
}

.bar-traditional {
  background: linear-gradient(90deg, #FF6B35, #FF8C5A);
}

.bar-system {
  background: linear-gradient(90deg, #00E5FF, #00D4AA);
}

.bar-value {
  width: 54px;
  font-size: 12px;
  font-weight: 500;
  color: #E8EDF5;
  text-align: right;
}

.comparison-note {
  font-size: 11px;
  color: #FF6B35;
  text-align: center;
  padding-top: 4px;
}

.accuracy-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: rgba(0, 229, 255, 0.08);
  border-radius: 6px;
  border: 1px solid rgba(0, 229, 255, 0.1);
}

.accuracy-display span {
  font-size: 13px;
  color: #8B9BB4;
}

.accuracy-value {
  font-size: 22px;
  font-weight: bold;
  color: #00E5FF;
}

/* 价值总结区块 */
.value-section {
  padding: 80px 40px;
  background: #0B0F19;
}

.value-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  max-width: 1400px;
  margin: 0 auto 50px;
}

.testimonials {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.testimonial-card {
  background: rgba(26, 31, 46, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 14px;
  padding: 22px;
}

.client-logo {
  font-size: 28px;
  margin-bottom: 10px;
}

.testimonial-text {
  font-size: 13px;
  color: #E8EDF5;
  margin: 0 0 10px 0;
  line-height: 1.6;
}

.client-name {
  font-size: 11px;
  color: #8B9BB4;
  font-style: italic;
}

.social-value {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.social-title {
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  color: #E8EDF5;
}

.value-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.value-stat {
  background: rgba(26, 31, 46, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  transition: transform 0.3s;
}

.value-stat:hover {
  transform: translateY(-3px);
}

.value-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.value-number {
  font-size: 24px;
  font-weight: bold;
  color: #00E5FF;
}

.value-label {
  font-size: 11px;
  color: #8B9BB4;
  margin-top: 4px;
}

.final-cta {
  text-align: center;
  padding: 50px;
  background: rgba(0, 229, 255, 0.04);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 18px;
  max-width: 700px;
  margin: 0 auto;
}

.final-cta h3 {
  font-size: 24px;
  font-weight: bold;
  margin: 0 0 6px 0;
  color: #E8EDF5;
}

.final-cta p {
  font-size: 14px;
  color: #8B9BB4;
  margin: 0 0 24px 0;
}

.final-buttons {
  display: flex;
  justify-content: center;
  gap: 14px;
}

/* 页脚 */
.showcase-footer {
  background: #1A1F2E;
  padding: 36px;
  border-top: 1px solid rgba(0, 229, 255, 0.1);
}

.footer-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-brand .brand-icon {
  font-size: 22px;
}

.footer-brand .brand-text {
  font-size: 16px;
}

.brand-sub {
  font-size: 11px;
  color: #8B9BB4;
}

.footer-links {
  display: flex;
  gap: 20px;
}

.footer-links a {
  color: #8B9BB4;
  text-decoration: none;
  font-size: 12px;
  transition: color 0.3s;
}

.footer-links a:hover {
  color: #00E5FF;
}

.footer-copyright {
  font-size: 11px;
  color: #5A6A7E;
}

/* 响应式 */
@media (max-width: 1200px) {
  .hero-content {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .hero-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .problem-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .value-content {
    grid-template-columns: 1fr;
  }
  
  .flow-container {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 768px) {
  .showcase-nav {
    padding: 0 20px;
  }
  
  .nav-links {
    display: none;
  }
  
  .hero-title {
    font-size: 42px;
  }
  
  .hero-subtitle {
    font-size: 17px;
  }
  
  .hero-stats {
    grid-template-columns: 1fr;
  }
  
  .problem-cards {
    grid-template-columns: 1fr;
  }
  
  .tech-grid {
    grid-template-columns: 1fr;
  }
  
  .value-stats {
    grid-template-columns: 1fr;
  }
  
  .footer-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}
</style>