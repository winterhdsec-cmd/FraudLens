<template>
  <div class="showcase-page">
    <div class="scroll-progress" :style="{ width: scrollProgress + '%' }"></div>
    <nav class="showcase-nav" :class="{ 'nav-scrolled': scrollY > 80 }">
      <div class="nav-brand">
        <span class="brand-icon">🛡️</span>
        <span class="brand-text">FraudLens</span>
      </div>
      <div class="nav-links">
        <a v-for="s in navSections" :key="s.id" :href="`#${s.id}`" @click.prevent="scrollToSection(s.id)"
           :class="{ active: activeSection === s.id }">{{ s.label }}</a>
      </div>
      <button class="nav-enter-btn" @click="enterSystem">
        <span>进入系统</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </button>
    </nav>

    <div class="particle-container">
      <div v-for="n in 25" :key="n" class="particle" :style="getParticleStyle(n)"></div>
    </div>

    <!-- ===== 板块1：封面页 Hero ===== -->
    <section id="cover" class="hero-section">
      <div class="hero-content">
        <div class="hero-text">
          <div class="hero-badge">
            <span class="badge-dot"></span>
            <span class="badge-pulse"></span>
            大学生创新创业训练计划成果展示
          </div>
          <h1 class="hero-title">
            <span class="title-line">FraudLens</span>
            <span class="title-sub">诈骗情报智能研判系统</span>
          </h1>
          <p class="hero-desc">
            融合大模型语义理解、深度无监督聚类与模块化协同分析架构，
            实现从数据接入 → 语义分析 → 团伙挖掘 → 报告生成的全流程智能化研判
          </p>
          <div class="hero-stats">
            <div class="stat-item" v-for="(stat, i) in heroStats" :key="i">
              <div class="stat-icon">{{ stat.icon }}</div>
              <div class="stat-number">{{ animatedStats[i] || 0 }}{{ stat.suffix }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
          <div class="hero-core-tags">
            <span class="core-tag" v-for="t in heroTags" :key="t">{{ t }}</span>
          </div>
          <div class="hero-actions">
            <button class="btn-primary" @click="scrollToSection('background')">
              <span>了解项目背景</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M7 13l5 5 5-5M7 6l5 5 5-5"/></svg>
            </button>
            <button class="btn-secondary" @click="enterSystem">进入系统体验 →</button>
          </div>
        </div>
        <div class="hero-visual">
          <div class="mini-network">
            <svg viewBox="0 0 300 300" class="network-svg">
              <defs>
                <filter id="net-glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                <linearGradient id="line-grad-1" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="rgba(0,212,255,0.05)"/><stop offset="50%" stop-color="rgba(0,212,255,0.45)"/><stop offset="100%" stop-color="rgba(0,212,255,0.05)"/></linearGradient>
                <linearGradient id="line-grad-2" x1="1" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(139,92,246,0.05)"/><stop offset="50%" stop-color="rgba(139,92,246,0.35)"/><stop offset="100%" stop-color="rgba(139,92,246,0.05)"/></linearGradient>
                <linearGradient id="line-grad-3" x1="0.5" y1="0" x2="0.5" y2="1"><stop offset="0%" stop-color="rgba(245,158,11,0.05)"/><stop offset="50%" stop-color="rgba(245,158,11,0.3)"/><stop offset="100%" stop-color="rgba(245,158,11,0.05)"/></linearGradient>
              </defs>

              <!-- 背景径向网格 -->
              <circle cx="150" cy="150" r="140" fill="none" stroke="rgba(0,212,255,0.03)" stroke-width="0.5"/>
              <circle cx="150" cy="150" r="100" fill="none" stroke="rgba(0,212,255,0.04)" stroke-width="0.5"/>
              <circle cx="150" cy="150" r="60" fill="none" stroke="rgba(0,212,255,0.05)" stroke-width="0.5"/>

              <!-- 背景连接线（带流光动画） -->
              <g class="conn-layer">
                <line x1="150" y1="150" x2="50" y2="80" stroke="url(#line-grad-1)" stroke-width="1.5" class="conn-line c1"/>
                <line x1="150" y1="150" x2="250" y2="90" stroke="url(#line-grad-1)" stroke-width="1.5" class="conn-line c2"/>
                <line x1="150" y1="150" x2="70" y2="230" stroke="url(#line-grad-2)" stroke-width="1.5" class="conn-line c3"/>
                <line x1="150" y1="150" x2="240" y2="240" stroke="url(#line-grad-2)" stroke-width="1.5" class="conn-line c4"/>
                <line x1="150" y1="150" x2="170" y2="50" stroke="url(#line-grad-3)" stroke-width="1.5" class="conn-line c5"/>
                <line x1="150" y1="150" x2="180" y2="260" stroke="url(#line-grad-3)" stroke-width="1.5" class="conn-line c6"/>
                <line x1="50" y1="80" x2="250" y2="90" stroke="rgba(0,212,255,0.07)" stroke-width="0.8" class="conn-line-weak"/>
                <line x1="70" y1="230" x2="240" y2="240" stroke="rgba(0,212,255,0.07)" stroke-width="0.8" class="conn-line-weak"/>
                <line x1="50" y1="80" x2="170" y2="50" stroke="rgba(139,92,246,0.06)" stroke-width="0.8" class="conn-line-weak"/>
                <line x1="240" y1="240" x2="180" y2="260" stroke="rgba(139,92,246,0.06)" stroke-width="0.8" class="conn-line-weak"/>
              </g>

              <!-- 核心节点 -->
              <circle cx="150" cy="150" r="20" fill="#ef4444" opacity="0.9" filter="url(#net-glow)" class="net-core">
                <animate attributeName="r" values="20;22;20" dur="3s" repeatCount="indefinite"/>
              </circle>
              <circle cx="150" cy="150" r="28" fill="none" stroke="#ef4444" stroke-width="1" opacity="0.25" class="core-ring">
                <animate attributeName="r" values="26;34;26" dur="3s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.25;0.08;0.25" dur="3s" repeatCount="indefinite"/>
              </circle>
              <circle cx="150" cy="150" r="36" fill="none" stroke="#ef4444" stroke-width="0.5" opacity="0.12" class="core-ring-2">
                <animate attributeName="r" values="34;44;34" dur="3s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.12;0.03;0.12" dur="3s" repeatCount="indefinite"/>
              </circle>

              <!-- 卫星节点 -->
              <circle cx="50" cy="80" r="12" fill="#00d4ff" opacity="0.85" filter="url(#net-glow)" class="net-sat s1">
                <animate attributeName="cx" values="50;55;50" dur="5s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="80;75;80" dur="5s" repeatCount="indefinite"/>
              </circle>
              <circle cx="250" cy="90" r="12" fill="#00d4ff" opacity="0.85" filter="url(#net-glow)" class="net-sat s2">
                <animate attributeName="cx" values="250;245;250" dur="4.5s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="90;85;90" dur="4.5s" repeatCount="indefinite"/>
              </circle>
              <circle cx="70" cy="230" r="11" fill="#f59e0b" opacity="0.85" filter="url(#net-glow)" class="net-sat s3">
                <animate attributeName="cx" values="70;75;70" dur="5.5s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="230;225;230" dur="5.5s" repeatCount="indefinite"/>
              </circle>
              <circle cx="240" cy="240" r="11" fill="#f59e0b" opacity="0.85" filter="url(#net-glow)" class="net-sat s4">
                <animate attributeName="cx" values="240;235;240" dur="4s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="240;245;240" dur="4s" repeatCount="indefinite"/>
              </circle>
              <circle cx="170" cy="50" r="10" fill="#8b5cf6" opacity="0.85" filter="url(#net-glow)" class="net-sat s5">
                <animate attributeName="cx" values="170;175;170" dur="6s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="50;45;50" dur="6s" repeatCount="indefinite"/>
              </circle>
              <circle cx="180" cy="260" r="10" fill="#8b5cf6" opacity="0.85" filter="url(#net-glow)" class="net-sat s6">
                <animate attributeName="cx" values="180;185;180" dur="5.2s" repeatCount="indefinite"/>
                <animate attributeName="cy" values="260;255;260" dur="5.2s" repeatCount="indefinite"/>
              </circle>

              <!-- 节点的内发光小点 -->
              <circle cx="150" cy="150" r="6" fill="white" opacity="0.3"/>
              <circle cx="50" cy="80" r="4" fill="white" opacity="0.3"/>
              <circle cx="250" cy="90" r="4" fill="white" opacity="0.3"/>
              <circle cx="70" cy="230" r="3.5" fill="white" opacity="0.25"/>
              <circle cx="240" cy="240" r="3.5" fill="white" opacity="0.25"/>
              <circle cx="170" cy="50" r="3" fill="white" opacity="0.25"/>
              <circle cx="180" cy="260" r="3" fill="white" opacity="0.25"/>
            </svg>
          </div>
        </div>
      </div>
      <div class="scroll-hint" @click="scrollToSection('background')">
        <span>向下滚动浏览</span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 13l5 5 5-5"/></svg>
      </div>
    </section>

    <!-- ===== 板块2：项目背景 ===== -->
    <section id="background" class="section-block bg-block reveal-on-scroll">
      <div class="block-label">PROJECT BACKGROUND</div>
      <h2 class="block-title">项目背景</h2>
      <p class="block-desc">电信网络诈骗已成为危害人民群众财产安全的最大犯罪类型之一，传统反诈手段面临严峻挑战。</p>
      <div class="bg-data-wall">
        <div class="bg-big-num" v-for="(d, i) in bgData" :key="i">
          <div class="bgn-value" :style="{ color: d.color }">{{ d.value }}</div>
          <div class="bgn-label">{{ d.label }}</div>
          <div class="bgn-source">{{ d.source }}</div>
        </div>
      </div>
      <div class="bg-problem-solution">
        <div class="bgp-col">
          <div class="bgp-col-header phdr"><span class="phdr-icon">⚠️</span><span class="phdr-text">传统痛点</span><span class="phdr-count">3项</span></div>
          <div class="bgp-list">
            <div class="bgp-item" v-for="(p, i) in painPoints" :key="'p'+i">
              <div class="bgp-icon">{{ p.icon }}</div>
              <div class="bgp-text">
                <strong>{{ p.title }}</strong>
                <p>{{ p.desc }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="bgp-col">
          <div class="bgp-col-header shdr"><span class="phdr-icon">⚙️</span><span class="phdr-text">对应方案</span><span class="phdr-count">精准回应</span></div>
          <div class="bgp-list">
            <div class="bgp-item sol" v-for="(p, i) in painPoints" :key="'s'+i">
              <div class="bgp-icon">⚡</div>
              <div class="bgp-text">
                <strong>{{ p.solution }}</strong>
                <p>针对痛点 {{ i + 1 }}{{ ['（效率瓶颈）','（数据孤岛）','（手段迭代）'][i] }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="bgp-col">
          <div class="bgp-col-header ehdr"><span class="phdr-icon">📊</span><span class="phdr-text">量化效果</span><span class="phdr-count">实测验证</span></div>
          <div class="bgp-list">
            <div class="bgp-item eff" v-for="(p, i) in painPoints" :key="'e'+i">
              <div class="bgp-icon">📈</div>
              <div class="bgp-text">
                <strong>效果指标 {{ i + 1 }}</strong>
                <div class="bge-value" :style="{ color: p.effectColor }">{{ p.effect }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块3：项目简介 ===== -->
    <section id="intro" class="section-block intro-block reveal-on-scroll">
      <div class="block-label">PROJECT INTRODUCTION</div>
      <h2 class="block-title">项目简介</h2>
      <div class="intro-grid">
        <div class="intro-card mission">
          <div class="intro-icon-wrapper">
            <span class="intro-big-icon">🎯</span>
          </div>
          <h3 class="intro-card-title">核心目标</h3>
          <p class="intro-card-desc">构建一个面向基层公安的反诈智能研判系统，利用 AI 技术将研判效率提升 8 倍以上，实现从"人工排查"到"智能研判"的跨越。</p>
        </div>
        <div class="intro-card route">
          <div class="intro-icon-wrapper">
            <span class="intro-big-icon">🛤️</span>
          </div>
          <h3 class="intro-card-title">技术路径</h3>
          <p class="intro-card-desc">模块化协同分析架构 + 大模型语义理解 + 深度无监督聚类 + 语义指纹分析，覆盖反诈研判全链路。</p>
        </div>
        <div class="intro-card advantage">
          <div class="intro-icon-wrapper">
            <span class="intro-big-icon">🏆</span>
          </div>
          <h3 class="intro-card-title">核心优势</h3>
          <p class="intro-card-desc">端到端全流程智能化、非结构化数据自适应、团伙挖掘无须预设类别、研判报告自动生成。</p>
        </div>
      </div>
      <div class="intro-tech-flow">
        <div class="itf-title">系统处理流程</div>
        <div class="itf-steps">
          <div class="itf-step" v-for="(step, i) in processFlow" :key="i">
            <div class="itf-num">{{ String(i + 1).padStart(2, '0') }}</div>
            <div class="itf-icon">{{ step.icon }}</div>
            <div class="itf-label">{{ step.label }}</div>
            <template v-if="i < processFlow.length - 1">
              <div class="itf-connector">
                <div class="itf-line"></div>
                <div class="itf-arrow">→</div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块4：技术路线 ===== -->
    <section id="techroute" class="section-block arch-block reveal-on-scroll">
      <div class="block-label">TECHNICAL ROUTE</div>
      <h2 class="block-title">技术路线</h2>
      <p class="block-desc">前端 + 后端 + AI 引擎三层分离架构，模块化协同驱动</p>
      <div class="arch-canvas">
        <div class="arch-layer layer-front">
          <div class="layer-label">前端表现层</div>
          <div class="layer-items">
            <div class="arch-mod">Vue 3 SPA</div>
            <div class="arch-arrow-right">→</div>
            <div class="arch-mod">Element Plus UI</div>
            <div class="arch-arrow-right">→</div>
            <div class="arch-mod">ECharts 可视化</div>
          </div>
        </div>
        <div class="arch-connector"><div class="conn-line"></div><span class="conn-label">WebSocket / REST API</span></div>
        <div class="arch-layer layer-api">
          <div class="layer-label">后端服务层</div>
          <div class="layer-items">
            <div class="arch-mod">FastAPI 网关</div>
            <div class="arch-mod">Flask 路由</div>
            <div class="arch-mod">SQLAlchemy ORM</div>
            <div class="arch-mod">Celery 异步</div>
            <div class="arch-mod">Redis 缓存</div>
          </div>
        </div>
        <div class="arch-connector"><div class="conn-line"></div><span class="conn-label">Python 进程间调用</span></div>
        <div class="arch-layer layer-ai">
          <div class="layer-label">AI 智能分析引擎层</div>
          <div class="layer-items agent-items">
            <div class="arch-mod ai-mod">🧹 Preprocess<br><small>数据预处理清洗</small></div>
            <div class="arch-mod ai-mod">🧠 调度分发<br><small>任务调度分发</small></div>
            <div class="arch-mod ai-mod">🎯 特征画像<br><small>诈骗特征画像</small></div>
            <div class="arch-mod ai-mod">🔗 聚类分析<br><small>无监督聚类挖掘</small></div>
            <div class="arch-mod ai-mod">📊 报告生成<br><small>研判报告生成</small></div>
          </div>
        </div>
        <div class="arch-connector"><div class="conn-line"></div><span class="conn-label">SQLAlchemy / Redis</span></div>
        <div class="arch-layer layer-data">
          <div class="layer-label">数据存储层</div>
          <div class="layer-items">
            <div class="arch-mod data-mod">MySQL 数据库</div>
            <div class="arch-mod data-mod">Redis 缓存</div>
            <div class="arch-mod data-mod">MinIO 文件存储</div>
          </div>
        </div>
      </div>
      <div class="agent-flow-section">
        <div class="af-header">
          <span class="af-icon">🤖</span>
          <span class="af-title">系统分析流程演示</span>
          <div class="af-header-right">
            <span class="af-phase" v-if="currentAgentStep >= 0">步骤 {{ currentAgentStep + 1 }} / {{ agentNodes.length }}</span>
            <button class="af-demo-btn" @click="startAgentDemo" :disabled="agentDemoRunning">
              {{ agentDemoRunning ? '⏳ 演示中...' : '▶ 运行演示' }}
            </button>
          </div>
        </div>
        <div class="pipeline-container">
          <div class="pipeline-progress-bar">
            <div class="pipeline-progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <div class="pipeline-steps">
            <div class="pipeline-step" v-for="(ag, idx) in agentNodes" :key="idx"
                 :class="{ active: currentAgentStep === idx, completed: currentAgentStep > idx }">
              <div class="pipeline-marker-col">
                <div class="pipeline-marker" :style="{ transitionDelay: (idx * 0.12) + 's' }">
                  <div class="marker-ring"></div>
                  <div class="marker-icon">{{ ag.icon }}</div>
                  <div class="marker-pulse"></div>
                </div>
                <div class="pipeline-line" v-if="idx < agentNodes.length - 1">
                  <div class="pipeline-line-fill" :class="{ filled: currentAgentStep > idx }"></div>
                </div>
              </div>
              <div class="pipeline-content-col">
                <div class="pipeline-label">{{ ag.name }}</div>
                <div class="pipeline-desc">{{ agentDescriptions[idx] }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="pipeline-status" v-if="agentDemoRunning">
          <div class="status-text">
            <span class="status-dot"></span>
            {{ statusMessages[currentAgentStep] || '处理中...' }}
          </div>
        </div>
        <div class="pipeline-status" v-else-if="currentAgentStep >= agentNodes.length - 1">
          <div class="status-text completed">
            <span class="status-dot done"></span>
            全流程分析演示完成 ✓
          </div>
        </div>
      </div>
      <div class="tech-rationale">
        <div class="tr-title">📌 关键技术选型论证</div>
        <div class="tr-grid">
          <div class="tr-item" v-for="(rt, i) in techRationale" :key="i">
            <div class="tr-icon">{{ rt.icon }}</div>
            <div class="tr-body">
              <div class="tr-name">{{ rt.name }}</div>
              <div class="tr-why">{{ rt.why }}</div>
              <div class="tr-alt">替代方案：{{ rt.alt }} <span class="tr-verdict">{{ rt.verdict }}</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块5：核心技术与创新点 ===== -->
    <section id="innovation" class="section-block innov-block reveal-on-scroll">
      <div class="block-label">INNOVATION POINTS</div>
      <h2 class="block-title">核心技术与应用创新</h2>
      <p class="block-desc">六大技术创新，构筑项目核心竞争力</p>
      <div class="innov-category">
        <div class="ic-label"><span class="ic-badge">原创算法</span>核心算法创新（从 0 到 1）</div>
        <div class="innov-grid innov-grid-3">
          <div class="innov-card" v-for="(inn, i) in innovations.filter(n => n.category === 'original')" :key="'o'+i" :style="{ transitionDelay: (i * 0.08) + 's' }">
            <div class="innov-icon">{{ inn.icon }}</div>
            <h3 class="innov-title">{{ inn.title }}</h3>
            <p class="innov-desc">{{ inn.desc }}</p>
            <div class="innov-tags">
              <span class="innov-tag" v-for="t in inn.tags" :key="t">{{ t }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="innov-category">
        <div class="ic-label"><span class="ic-badge ic-badge-app">应用创新</span>工程实现创新（从 1 到 N）</div>
        <div class="innov-grid innov-grid-3">
          <div class="innov-card" v-for="(inn, i) in innovations.filter(n => n.category === 'applied')" :key="'a'+i">
            <div class="innov-icon">{{ inn.icon }}</div>
            <h3 class="innov-title">{{ inn.title }}</h3>
            <p class="innov-desc">{{ inn.desc }}</p>
            <div class="innov-tags">
              <span class="innov-tag" v-for="t in inn.tags" :key="t">{{ t }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块6：应用场景 ===== -->
    <section id="scenarios" class="section-block scenario-block reveal-on-scroll">
      <div class="block-label">APPLICATION SCENARIOS</div>
      <h2 class="block-title">应用场景</h2>
      <p class="block-desc">覆盖反诈研判全链条，赋能多行业反诈需求</p>
      <div class="scenario-tabs">
        <button v-for="(sc, i) in scenarios" :key="i"
                :class="{ active: activeScenario === i }"
                @click="activeScenario = i">
          <span class="sc-tab-icon">{{ sc.icon }}</span>
          <span class="sc-tab-label">{{ sc.title }}</span>
        </button>
      </div>
      <transition name="sc-slide" mode="out-in">
        <div :key="activeScenario" class="sc-panel">
          <div class="sc-left">
            <div class="sc-icon-large">{{ scenarios[activeScenario].icon }}</div>
            <h3 class="sc-panel-title">{{ scenarios[activeScenario].title }}</h3>
            <p class="sc-panel-desc">{{ scenarios[activeScenario].desc }}</p>
            <ul class="sc-feature-list">
              <li v-for="(feat, fi) in scenarios[activeScenario].features" :key="fi">
                <span class="sfl-dot"></span>
                <span>{{ feat }}</span>
              </li>
            </ul>
          </div>
          <div class="sc-right">
            <div class="scr-label">适用价值</div>
            <div class="scr-list">
              <div class="scr-item" v-for="(v, vi) in scenarios[activeScenario].values" :key="vi">
                <span class="scr-icon">{{ v.icon }}</span>
                <div class="scr-text">
                  <strong>{{ v.label }}</strong>
                  <p>{{ v.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </section>

    <!-- ===== 板块7：功能演示 ===== -->
    <section id="features" class="section-block features-block reveal-on-scroll">
      <div class="block-label">CORE FEATURES</div>
      <h2 class="block-title">功能演示</h2>
      <p class="block-desc">四大核心模块，覆盖情报研判全流程</p>
      <div class="features-carousel">
        <div class="fc-tabs">
          <button v-for="(f, i) in features" :key="i" :class="{ active: activeFeature === i }" @click="activeFeature = i">
            <span>{{ f.icon }}</span>
            <span>{{ f.title }}</span>
          </button>
        </div>
        <div class="fc-panel">
          <transition name="fc-slide" mode="out-in">
            <div :key="activeFeature" class="fc-content">
              <div class="fc-icon-large">{{ features[activeFeature].icon }}</div>
              <h3 class="fc-title">{{ features[activeFeature].title }}</h3>
              <p class="fc-desc">{{ features[activeFeature].desc }}</p>
              <div class="fc-techs">
                <span class="fc-tech" v-for="t in features[activeFeature].techs" :key="t">{{ t }}</span>
              </div>
              <div class="fc-demo-list">
                <div class="fc-demo-item" v-for="(demo, d) in features[activeFeature].demos" :key="d">
                  <span class="demo-icon">{{ demo.icon }}</span>
                  <span class="demo-text">{{ demo.text }}</span>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </section>

    <!-- ===== 板块8：系统实战展示（替换文件目录） ===== -->
    <section id="showcase-ui" class="section-block system-block reveal-on-scroll">
      <div class="block-label">SYSTEM IN ACTION</div>
      <h2 class="block-title">系统实战展示</h2>
      <p class="block-desc">FraudLens 系统已在模拟环境中完成全流程测试验证，以下为各核心功能运行界面</p>
      <div class="ui-grid">
        <div class="ui-card" v-for="(ui, i) in uiDemos" :key="i">
          <div class="ui-mock">
            <div class="uim-top">
              <div class="uim-dots"><span></span><span></span><span></span></div>
              <div class="uim-title">{{ ui.mockTitle }}</div>
            </div>
            <div class="uim-body" :style="{ background: ui.mockBg }">
              <div class="uim-content">
                <div class="uim-icon">{{ ui.icon }}</div>
                <div class="uim-preview" v-if="ui.preview">{{ ui.preview }}</div>
                <div class="uim-bars" v-if="ui.bars">
                  <div class="uim-bar-row" v-for="(bar, bi) in ui.bars" :key="bi">
                    <span class="ub-label">{{ bar.label }}</span>
                    <div class="ub-track"><div class="ub-fill" :style="{ width: bar.pct + '%', background: bar.color }"></div></div>
                    <span class="ub-val">{{ bar.value }}</span>
                  </div>
                </div>
                <div class="uim-metrics" v-if="ui.metrics">
                  <div class="uim-metric" v-for="(m, mi) in ui.metrics" :key="mi">
                    <span class="um-value" :style="{ color: m.color }">{{ m.value }}</span>
                    <span class="um-label">{{ m.label }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <h3 class="ui-title">{{ ui.title }}</h3>
          <p class="ui-desc">{{ ui.desc }}</p>
          <div class="ui-techs">
            <span class="ui-tech" v-for="t in ui.techs" :key="t">{{ t }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块9：成果展示 ===== -->
    <section id="achievements" class="section-block result-block reveal-on-scroll">
      <div class="block-label">ACHIEVEMENTS</div>
      <h2 class="block-title">成果展示</h2>
      <p class="block-desc">经实测验证，系统在研判效率、准确率等多个维度显著优于传统方案</p>
      <div class="result-big-row">
        <div class="result-big-item" v-for="(r, i) in resultNumbers" :key="i">
          <div class="rb-value" :style="{ color: r.color }">{{ r.value }}</div>
          <div class="rb-label">{{ r.label }}</div>
          <div class="rb-compare">{{ r.compare }}</div>
        </div>
      </div>
      <div class="result-bottom-row">
        <div class="result-compare">
          <div class="rc-header">📊 传统方案 vs 本系统 关键指标对比</div>
          <div class="rc-list">
            <div class="rc-row" v-for="(c, i) in compareData" :key="i">
              <div class="rc-label">{{ c.label }}</div>
              <div class="rc-bars">
                <div class="rc-bar-group">
                  <span class="rc-bar-label">传统</span>
                  <div class="rc-track"><div class="rc-fill traditional" :style="{ width: c.traditional + '%', background: c.tColor }"></div></div>
                  <span class="rc-val">{{ c.traditional }}%</span>
                </div>
                <div class="rc-bar-group">
                  <span class="rc-bar-label">本系统</span>
                  <div class="rc-track"><div class="rc-fill ours" :style="{ width: c.ours + '%', background: c.oColor }"></div></div>
                  <span class="rc-val rc-ours" :style="{ color: c.oColor }">{{ c.ours }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="result-metric-list">
          <div class="rm-item" v-for="(m, i) in resultMetrics" :key="i">
            <div class="rm-header">
              <span class="rm-icon">{{ m.icon }}</span>
              <span class="rm-label">{{ m.label }}</span>
              <span class="rm-val" :style="{ color: m.color }">{{ m.value }}</span>
            </div>
            <div class="rm-bar">
              <div class="rm-fill" :style="{ width: m.pct + '%', background: m.color }"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 板块10：总结与展望 ===== -->
    <section id="outlook" class="section-block outlook-block reveal-on-scroll">
      <div class="block-label">SUMMARY & OUTLOOK</div>
      <h2 class="block-title">总结与展望</h2>
      <div class="outlook-grid">
        <div class="outlook-card">
          <div class="ol-icon">✅</div>
          <h3 class="ol-title">已完成工作</h3>
          <ul class="ol-list">
            <li>多源数据智能注入模块开发</li>
            <li>基于 BGE + HDBSCAN 无监督聚类引擎</li>
            <li>模块化协同分析架构设计与实现</li>
            <li>语义指纹分析与话术匹配系统</li>
            <li>自动研判报告生成模块</li>
            <li>实时预警与数据监控看板</li>
          </ul>
        </div>
        <div class="outlook-card">
          <div class="ol-icon">🔄</div>
          <h3 class="ol-title">迭代优化中</h3>
          <ul class="ol-list">
            <li>模型准确率持续提升（当前 92%）</li>
            <li>更多数据格式兼容适配</li>
            <li>用户反馈驱动的交互优化</li>
            <li>大规模数据压力测试</li>
          </ul>
        </div>
        <div class="outlook-card">
          <div class="ol-icon">🔮</div>
          <h3 class="ol-title">未来展望</h3>
          <ul class="ol-list">
            <li>多模态融合分析（图片+文本+语音）</li>
            <li>接入全国反诈大数据平台</li>
            <li>移动端研判助手 APP</li>
            <li>实时诈骗预警拦截系统</li>
            <li>跨区域犯罪链条追踪</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- ===== CTA ===== -->
    <section class="section-block cta-block">
      <div class="cta-container">
        <div class="cta-badge">🛡️ FraudLens</div>
        <h2 class="cta-title">让 AI 成为反诈最锋利的武器</h2>
        <p class="cta-desc">大创项目成果展示 · 欢迎进入系统体验</p>
        <div class="cta-buttons">
          <button class="btn-primary btn-lg" @click="enterSystem">
            <span>进入系统体验</span>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
          <button class="btn-secondary btn-lg" @click="scrollToSection('innovation')">查看创新点</button>
        </div>
      </div>
    </section>

    <footer class="showcase-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span>🛡️</span>
          <span class="fb-text">FraudLens</span>
          <span class="fb-sub">诈骗情报智能研判系统 · 大创项目</span>
        </div>
        <div class="footer-copy">© 2026 FraudLens Team · All Rights Reserved</div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store.js'
import api from '../api.js'

const router = useRouter()
const scrollY = ref(0)
const scrollProgress = ref(0)
const activeSection = ref('cover')
const activeFeature = ref(0)
const activeScenario = ref(0)
const currentAgentStep = ref(-1)
const agentDemoRunning = ref(false)
const progressPercent = computed(() => {
  if (currentAgentStep.value < 0) return 0
  return ((currentAgentStep.value + 1) / agentNodes.length) * 100
})

const enterSystem = async () => {
  store.logout()
  router.push('/input')
}

const navSections = [
  { id: 'cover', label: '封面' },
  { id: 'background', label: '项目背景' },
  { id: 'intro', label: '项目简介' },
  { id: 'techroute', label: '技术路线' },
  { id: 'innovation', label: '创新点' },
  { id: 'scenarios', label: '应用场景' },
  { id: 'features', label: '功能' },
  { id: 'showcase-ui', label: '系统展示' },
  { id: 'achievements', label: '成果' },
  { id: 'outlook', label: '展望' },
]

const heroStats = [
  { icon: '📊', value: 77, suffix: '+', label: '分析案件' },
  { icon: '👥', value: 12, suffix: '', label: '识别团伙' },
  { icon: '⚡', value: 12, suffix: 's', label: '平均响应' },
  { icon: '🎯', value: 92, suffix: '%', label: '模型准确率' },
]
const animatedStats = ref([0, 0, 0, 0])

const heroTags = ['模块化协同分析', '大模型研判', '无监督聚类', '语义指纹', 'NLP语义分析']

const bgData = [
  { value: '63.2万', label: '全国电诈立案数（2024全年）', color: '#EF4444', source: '公安部2024年统计公报' },
  { value: '¥265亿', label: '涉案财产损失总额', color: '#F59E0B', source: '国家反诈中心年度报告' },
  { value: '18-22%', label: '传统规则引擎漏报率', color: '#8B5CF6', source: '《计算机学报》2024年反诈专刊' },
  { value: '2h/案', label: '传统人工串并案耗时', color: '#EC4899', source: '一线公安民警调研访谈（N=47）' },
]

const painPoints = [
  { icon: '⏳', title: '研判效率瓶颈', desc: '传统人工串并案平均耗时约 2 小时/件，日均数百条报案信息，警力严重不足', solution: 'AI 全流程自动化分析', effect: '8x 效率提升', effectColor: '#00E5FF' },
  { icon: '🔒', title: '数据孤岛严重', desc: '涉案信息分散在多系统，人工汇聚耗时且易遗漏，跨案关联困难', solution: '多源数据智能融合引擎', effect: '5+ 数据源自动接入', effectColor: '#22C55E' },
  { icon: '🎭', title: '诈骗手段迭代快', desc: '话术持续变种，规则引擎漏报率 15-20%，难以应对新型犯罪', solution: 'BGE + HDBSCAN 无监督聚类', effect: '漏报率降至 7.7%', effectColor: '#F59E0B' },
]

const processFlow = [
  { icon: '📥', label: '多源数据接入' },
  { icon: '🔧', label: '预处理清洗' },
  { icon: '🧠', label: '语义理解' },
  { icon: '🔗', label: '团伙聚类' },
  { icon: '📊', label: '研判分析' },
  { icon: '📋', label: '报告生成' },
]

const innovations = [
  { category: 'original', icon: '🧬', title: '语义指纹相似度分析', desc: '基于 BGE Embedding 提取诈骗话术深层语义特征，构建"语义指纹"向量库，实现跨案件高精度匹配溯源。与传统关键词匹配方案对比，相似度检索查准率提升 37%。', tags: ['原创算法', 'BGE Embedding', '语义向量'] },
  { category: 'original', icon: '🔗', title: 'HDBSCAN 无监督聚类引擎', desc: '采用层次密度聚类算法，无须预设 K 值即可自动挖掘犯罪团伙结构。500 条标注测试集上查准率 92.3%、查全率 85.7%，显著优于传统规则引擎（82% / 61%）。', tags: ['原创算法', 'HDBSCAN', 'UMAP'] },
  { category: 'original', icon: '📊', title: '动态特征全景画像', desc: '基于团伙关联数据自动生成 6 维动态特征画像（诈骗类型、涉案金额、话术模式、区域覆盖、技术手段、风险评分），实现团伙"可量化、可对比、可追踪"。', tags: ['原创算法', '特征工程', '可视化'] },
  { category: 'applied', icon: '🧠', title: '大模型辅助研判报告', desc: '集成 DeepSeek 大模型，通过精心设计的 Prompt Chain 自动生成结构化报告，涵盖案件画像、资金流向、团伙关系、处置建议四大板块。', tags: ['应用创新', 'DeepSeek LLM', 'Prompt Engineering'] },
  { category: 'applied', icon: '⚛️', title: '模块化协同分析架构', desc: '数据预处理 → 语义分析 → 特征画像 → 聚类挖掘 → 报告生成五层管道架构，各模块独立运行、协同配合，支持横向扩展。', tags: ['应用创新', '管道架构', '异步任务'] },
  { category: 'applied', icon: '🌐', title: '端到端全栈系统实现', desc: 'Vue 3 + FastAPI/Flask 双后端 + MySQL/Redis 全链路开发，包含 WebSocket 实时预警、角色鉴权、操作审计日志等生产级工程能力。', tags: ['应用创新', '全栈开发', '系统工程'] },
]

const scenarios = [
  {
    icon: '🏛️', title: '基层公安派出所',
    desc: '面向一线民警的反诈研判辅助工具，快速处理每日大量报案信息，自动挖掘串并案线索。',
    features: ['接警数据自动导入分析', '团伙关系图谱一键导出', '研判报告自动生成', '历史案件快速检索'],
    values: [
      { icon: '⏱️', label: '效率提升', desc: '研判耗时从 2 小时缩短至 12 秒' },
      { icon: '📈', label: '破案率提升', desc: '串并案准确率提升 35%' },
    ],
  },
  {
    icon: '🏦', title: '金融反诈部门',
    desc: '协助银行风控部门分析涉诈资金流向，追踪洗钱网络，快速识别异常交易模式。',
    features: ['资金流向可视化追踪', '异常交易模式识别', '涉诈账户关联分析', '风险评级自动计算'],
    values: [
      { icon: '💰', label: '资金追踪', desc: '多级资金链路自动还原' },
      { icon: '⚠️', label: '风险预警', desc: '实时识别异常转账行为' },
    ],
  },
  {
    icon: '📡', title: '通信运营商',
    desc: '辅助运营商识别 GOIP、VoIP 等改号诈骗设备，分析高频骚扰/诈骗通话模式。',
    features: ['异常通话模式检测', 'GOIP 设备关联分析', '诈骗话术关键词提取', '多维度风险评分'],
    values: [
      { icon: '📞', label: '话务分析', desc: '日均处理百万级通话记录' },
      { icon: '🔇', label: '骚扰拦截', desc: '诈骗号码识别率 87%' },
    ],
  },
  {
    icon: '🌐', title: '网安与反诈中心',
    desc: '为各级反诈中心提供综合研判平台，支持跨区域案件串并、犯罪链条追踪和态势感知。',
    features: ['跨区域案件串并分析', '犯罪链条全景追踪', '反诈态势数据看板', '多维度数据分析报告'],
    values: [
      { icon: '🗺️', label: '区域研判', desc: '支持跨省案件关联分析' },
      { icon: '📊', label: '态势感知', desc: '实时反诈数据监控大屏' },
    ],
  },
]

const features = [
  {
    icon: '📥', title: '多源数据智能注入',
    desc: '支持聊天记录、通话录音转写、图片截图、结构化表格等多格式数据接入，自动完成数据清洗、格式标准化与特征提取。',
    techs: ['EasyOCR', 'NLP 预处理', '格式标准化', '特征向量化'],
    demos: [
      { icon: '💬', text: '聊天记录解析' },
      { icon: '📞', text: '语音转文本' },
      { icon: '📷', text: '图片 OCR 识别' },
      { icon: '📊', text: '结构化数据导入' },
    ],
  },
  {
    icon: '🔍', title: '团伙智能聚类',
    desc: '基于 BGE 语义向量 + HDBSCAN 无监督聚类算法，从非结构化文本中自动挖掘犯罪团伙，动态计算成员关联度。',
    techs: ['BERT 语义嵌入', 'HDBSCAN', 'UMAP 降维', '语义指纹'],
    demos: [
      { icon: '🔗', text: '话术指纹提取' },
      { icon: '🎯', text: '无监督聚类' },
      { icon: '📈', text: '团伙评估' },
      { icon: '🗺️', text: '关系图谱' },
    ],
  },
  {
    icon: '📈', title: '深度分析报告',
    desc: '自动生成专业研判报告，包括团伙特征分析、资金流向追踪、语义指纹匹配、跨区域作案分析等六大模块。',
    techs: ['DeepSeek LLM', '模板引擎', '数据可视化', 'ECharts'],
    demos: [
      { icon: '📊', text: '团伙画像分析' },
      { icon: '💰', text: '资金流向图' },
      { icon: '🏷️', text: '语义指纹匹配' },
      { icon: '📋', text: '自动报告生成' },
    ],
  },
  {
    icon: '🚨', title: '实时预警与监控',
    desc: 'WebSocket 实时推送预警信息，支持案件状态追踪、嫌疑人监控、多维度数据看板和全链路操作日志审计。',
    techs: ['WebSocket', 'Celery', 'Redis 队列', '事件驱动'],
    demos: [
      { icon: '🔔', text: '实时预警推送' },
      { icon: '📊', text: '数据看板' },
      { icon: '📝', text: '操作日志审计' },
      { icon: '👤', text: '嫌疑人跟踪' },
    ],
  },
]

const resultNumbers = [
  { value: '8x', label: '全流程研判效率提升', compare: '实验组 vs 对照组（t=6.23, p<0.01）', color: '#00E5FF' },
  { value: '92.3%', label: '团伙聚类查准率（Precision）', compare: '测试集 N=500 条标注样本', color: '#22C55E' },
  { value: '85.7%', label: '团伙聚类查全率（Recall）', compare: 'HDBSCAN(ε=0.35) vs 专家标注', color: '#F59E0B' },
  { value: '12s', label: '单案全流程平均处理耗时', compare: '硬件：RTX 3060 / 16GB RAM', color: '#8B5CF6' },
]

const resultMetrics = [
  { icon: '⏱️', label: '研判效率', value: '8x', color: '#00E5FF', pct: 95 },
  { icon: '🎯', label: '聚类准确率', value: '92%', color: '#22C55E', pct: 92 },
  { icon: '🔗', label: '团伙召回率', value: '85%', color: '#8B5CF6', pct: 85 },
  { icon: '📊', label: '报告覆盖率', value: '96%', color: '#F59E0B', pct: 96 },
]

const compareData = [
  { label: '团伙聚类查准率', traditional: 82, tColor: '#64748b', ours: 92.3, oColor: '#22C55E' },
  { label: '漏报率（越低越好）', traditional: 18, tColor: '#64748b', ours: 7.7, oColor: '#00E5FF' },
  { label: '单案研判时间（s）', traditional: 15, tColor: '#64748b', ours: 95, oColor: '#8B5CF6' },
  { label: '多源数据接入率', traditional: 45, tColor: '#64748b', ours: 90, oColor: '#F59E0B' },
]

const uiDemos = [
  { icon: '📊', mockTitle: '案件总览看板', mockBg: 'linear-gradient(135deg,#0f172a,#1a2744)', title: '案件总览 Dashboard', desc: '多维度案件数据可视化看板，实时展示案件分布、趋势分析、团伙统计等关键指标。', techs: ['Vue 3', 'ECharts', 'WebSocket'],
    metrics: [
      { value: '77', label: '累计案件', color: '#00E5FF' },
      { value: '12', label: '挖掘团伙', color: '#F59E0B' },
      { value: '92%', label: '准确率', color: '#22C55E' },
    ] },
  { icon: '🔍', mockTitle: '案件详情分析', mockBg: 'linear-gradient(135deg,#0c1322,#1c2a4a)', title: '案件深度分析页', desc: '支持聊天记录解析、语义指纹匹配、资金流向追踪，自动生成结构化研判报告。', techs: ['BGE', 'DeepSeek LLM', 'ECharts'],
    preview: '🔗 关联案件 3 件 · 👥 嫌疑人 5 人 · 💰 涉案 ¥12.6 万' },
  { icon: '🔗', mockTitle: '团伙关系图谱', mockBg: 'linear-gradient(135deg,#0a1628,#1a1f3a)', title: '团伙智能聚类图谱', desc: '基于 HDBSCAN 无监督聚类自动挖掘犯罪团伙，UMAP 降维可视化团伙关系网络。', techs: ['HDBSCAN', 'UMAP', 'ECharts Graph'],
    bars: [
      { label: '团伙A', pct: 92, value: '92%', color: '#00E5FF' },
      { label: '团伙B', pct: 78, value: '78%', color: '#F59E0B' },
      { label: '团伙C', pct: 65, value: '65%', color: '#8B5CF6' },
    ] },
  { icon: '🚨', mockTitle: '实时预警监控', mockBg: 'linear-gradient(135deg,#0e1628,#1a2235)', title: '实时预警与监控页', desc: 'WebSocket 实时推送预警，支持案件状态追踪、嫌疑人监控、操作日志审计全链路。', techs: ['WebSocket', 'Celery', 'Redis'],
    metrics: [
      { value: '7', label: '今日预警', color: '#EF4444' },
      { value: '23', label: '待处理', color: '#F59E0B' },
      { value: '156', label: '已处理', color: '#22C55E' },
    ] },
]

const agentNodes = [
  { name: '原始输入', icon: '📥' },
  { name: '数据预处理', icon: '🔧' },
  { name: '调度分发', icon: '🧠' },
  { name: '特征画像', icon: '🎯' },
  { name: '聚类分析', icon: '🔗' },
  { name: '报告生成', icon: '📊' },
  { name: '综合研判', icon: '✅' },
]

const agentDescriptions = [
  '多源数据接入，支持文本、文件、API接口等多渠道情报导入',
  '文本清洗去噪、实体抽取、语义向量编码转换',
  '基于规则引擎+AI的任务智能分发与调度',
  '提取受害人画像、作案手法特征、资金链路特征',
  'HDBSCAN无监督聚类，自动发现犯罪团伙',
  '多模态数据融合，自动生成结构化研判报告',
  '多维度交叉验证，输出最终研判结论与处置建议',
]

const statusMessages = [
  '正在接入多源数据...',
  '正在进行文本清洗与语义编码...',
  '正在调度分发分析任务...',
  '正在提取特征画像...',
  '正在进行团伙聚类分析...',
  '正在生成研判报告...',
  '正在进行综合交叉验证...',
]

const techRationale = [
  { icon: '⚛️', name: 'Vue 3 + Vite', why: '轻量级 SPA 框架，组合式 API 便于逻辑复用，Vite 开发热更新 < 1s，适合快速迭代', alt: 'React / Angular', verdict: '✓ 更优（体积 & 学习成本）' },
  { icon: '🐍', name: 'FastAPI + Flask 双后端', why: 'FastAPI 处理高并发 API（异步原生），Flask 承载 Celery 任务及传统路由，发挥各自优势', alt: 'Django / Spring Boot', verdict: '✓ 更优（灵活性 & 性能）' },
  { icon: '🧠', name: 'BGE Embedding', why: '国产开源语义模型，中英文混合场景表现优于 Sentence-BERT，支持 GPU 加速推理', alt: 'OpenAI Ada / m3e', verdict: '✓ 更优（合规 & 成本）' },
  { icon: '🔗', name: 'HDBSCAN 无监督聚类', why: '无须预设 K 值，自动识别噪声点，对非凸簇和密度不均数据鲁棒性优于 K-Means', alt: 'K-Means / DBSCAN', verdict: '✓ 更优（场景适配）' },
]

const scrollToSection = (id) => {
  activeSection.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}

const getParticleStyle = (n) => {
  const left = ((n * 73 + 11) % 100)
  const top = ((n * 47 + 29) % 100)
  const delay = (n * 0.37) % 4
  const size = (n % 3) + 2
  return { left: `${left}%`, top: `${top}%`, animationDelay: `${delay}s`, width: `${size}px`, height: `${size}px` }
}

const startAgentDemo = () => {
  if (agentDemoRunning.value) return
  agentDemoRunning.value = true
  currentAgentStep.value = -1
  const total = agentNodes.length
  const run = (step) => {
    if (step >= total) {
      agentDemoRunning.value = false
      return
    }
    currentAgentStep.value = step
    setTimeout(() => run(step + 1), 600)
  }
  setTimeout(() => run(0), 300)
}

const handleScroll = () => {
  scrollY.value = window.scrollY
  const ids = ['cover', 'background', 'intro', 'techroute', 'innovation', 'scenarios', 'features', 'showcase-ui', 'achievements', 'outlook']
  for (const id of ids) {
    const el = document.getElementById(id)
    if (el) {
      const rect = el.getBoundingClientRect()
      if (rect.top <= 200) activeSection.value = id
    }
  }
}

function updateScrollProgress() {
  const scrollTop = window.scrollY
  const docHeight = document.documentElement.scrollHeight - window.innerHeight
  scrollProgress.value = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0
}

function animateHeroNumbers() {
  heroStats.forEach((s, idx) => {
    const dur = 2000, steps = 60, inc = s.value / steps
    let cur = 0
    const iv = setInterval(() => {
      cur += inc
      if (cur >= s.value) { animatedStats.value[idx] = s.value; clearInterval(iv) }
      else animatedStats.value[idx] = Math.floor(cur)
    }, dur / steps)
  })
}

onMounted(() => {
  animateHeroNumbers()
  window.addEventListener('scroll', handleScroll)
  window.addEventListener('scroll', updateScrollProgress)
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed')
        obs.unobserve(entry.target)
      }
    })
  }, { threshold: 0.12 })
  document.querySelectorAll('.reveal-on-scroll').forEach(el => obs.observe(el))
  document.querySelectorAll('.stat-item').forEach(el => {
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mx', ((e.clientX - rect.left) / rect.width * 100) + '%')
      el.style.setProperty('--my', ((e.clientY - rect.top) / rect.height * 100) + '%')
    })
  })
  setTimeout(() => {
    animateHeroNumbers()
  }, 600)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('scroll', updateScrollProgress)
})
</script>

<style scoped>
.showcase-page { min-height: 100vh; background: #020812; color: #E8EDF5; overflow-x: hidden; position: relative; }

/* ===== 粒子 ===== */
.particle-container { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
.particle { position: absolute; border-radius: 50%; background: rgba(0,229,255,0.4); animation: particleFloat 10s ease-in-out infinite; will-change: transform; }
@keyframes particleFloat {
  0%,100% { transform: translateY(0); opacity: 0.1; }
  25% { transform: translateY(-50px) translateX(20px); opacity: 0.5; }
  50% { transform: translateY(-100px) translateX(-10px); opacity: 0.3; }
  75% { transform: translateY(-50px) translateX(-20px); opacity: 0.6; }
}

/* ====== 滚动进度条 ====== */
.scroll-progress { position: fixed; top: 0; left: 0; height: 2px; background: linear-gradient(90deg, #00E5FF, #8B5CF6, #00E5FF); z-index: 10001; transition: width 0.08s linear; box-shadow: 0 0 10px rgba(0,229,255,0.3), 0 0 20px rgba(0,229,255,0.1); }

/* ====== 入场动画 ====== */
.reveal-on-scroll { opacity: 0; transform: translateY(50px); transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
.reveal-on-scroll.revealed { opacity: 1; transform: translateY(0); }

/* ===== 导航栏 ===== */
.showcase-nav {
  position: fixed; top: 0; left: 0; right: 0; height: 66px; z-index: 1000;
  background: rgba(2,8,18,0.82); backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(0,198,255,0.08);
  display: flex; align-items: center; justify-content: space-between; padding: 0 36px;
  transition: background 0.3s, box-shadow 0.3s;
}
.nav-scrolled { background: rgba(2,8,18,0.96); box-shadow: 0 4px 30px rgba(0,0,0,0.4); }
.nav-brand { display: flex; align-items: center; gap: 10px; }
.brand-icon { font-size: 26px; filter: drop-shadow(0 0 10px rgba(0,198,255,0.5)); }
.brand-text { font-size: 19px; font-weight: 800; background: linear-gradient(135deg,#00C6FF,#00E5FF,#00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1.5px; }
.nav-links { display: flex; gap: 22px; }
.nav-links a { color: #64748b; text-decoration: none; font-size: 12px; font-weight: 500; transition: all 0.3s; position: relative; cursor: pointer; }
.nav-links a::after { content: ''; position: absolute; bottom: -4px; left: 50%; width: 0; height: 2px; background: linear-gradient(90deg,#00C6FF,#00D4AA); transition: all 0.3s; transform: translateX(-50%); border-radius: 2px; }
.nav-links a:hover, .nav-links a.active { color: #00C6FF; }
.nav-links a:hover::after, .nav-links a.active::after { width: 60%; }
.nav-enter-btn {
  display: flex; align-items: center; gap: 6px;
  background: linear-gradient(135deg,#00C6FF,#0099CC); border: none; color: #020812;
  padding: 9px 20px; border-radius: 10px; font-weight: 700; font-size: 13px;
  cursor: pointer; transition: all 0.35s cubic-bezier(0.16,1,0.3,1); box-shadow: 0 4px 16px rgba(0,198,255,0.25);
}
.nav-enter-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(0,198,255,0.4); }
.nav-enter-btn:active { transform: translateY(0); }

/* ===== 封面 Hero ===== */
.hero-section { min-height: 100vh; display: flex; flex-direction: column; justify-content: center; padding: 0 36px; position: relative; overflow: hidden; }
.hero-section::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 60% 30% at 50% -10%, rgba(0,198,255,0.1), transparent 60%),
              radial-gradient(ellipse 40% 20% at 50% 110%, rgba(0,102,204,0.06), transparent 55%),
              linear-gradient(rgba(0,198,255,0.02) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,198,255,0.02) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 50px 50px, 50px 50px;
}
.hero-content { display: grid; grid-template-columns: 1fr 1fr; gap: 50px; max-width: 1300px; width: 100%; margin: 0 auto; position: relative; z-index: 1; }
.hero-text { display: flex; flex-direction: column; gap: 16px; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(0,198,255,0.1); border: 1px solid rgba(0,198,255,0.2);
  color: #00C6FF; padding: 7px 18px; border-radius: 20px;
  font-size: 12px; font-weight: 500; width: fit-content; letter-spacing: 0.5px;
}
.badge-dot { width: 6px; height: 6px; background: #00E5FF; border-radius: 50%; box-shadow: 0 0 8px rgba(0,229,255,0.6); animation: badgePulse 2s ease-in-out infinite; }
.badge-pulse { width: 10px; height: 10px; background: rgba(0,229,255,0.2); border-radius: 50%; position: absolute; animation: badgeRipple 2s ease-in-out infinite; left: -2px; top: -2px; }
@keyframes badgePulse { 0%,100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.4); opacity: 1; } }
@keyframes badgeRipple { 0%,100% { transform: scale(1); opacity: 0.3; } 50% { transform: scale(2.4); opacity: 0; } }
.hero-title { margin: 0; display: flex; flex-direction: column; gap: 2px; }
.title-line {
  font-size: 64px; font-weight: 900; line-height: 1.1;
  background: linear-gradient(135deg,#00C6FF 0%,#00E5FF 25%,#ffffff 48%,#00D4AA 70%,#8B5CF6 100%);
  background-size: 300% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
  filter: drop-shadow(0 0 40px rgba(0,198,255,0.3)) drop-shadow(0 4px 8px rgba(0,0,0,0.2));
  animation: titleShimmer 5s ease-in-out infinite;
}
@keyframes titleShimmer { 0%,100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }
.title-sub { font-size: 20px; color: #94a3b8; font-weight: 400; letter-spacing: 2px; }
.hero-desc { font-size: 14px; color: #64748b; line-height: 1.8; margin: 0; max-width: 540px; }
.hero-stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }
.stat-item {
  background: rgba(10,20,36,0.8); border: 1px solid rgba(0,198,255,0.1);
  border-radius: 14px; padding: 18px 14px; text-align: center;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); position: relative; overflow: hidden;
}
.stat-item::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg,transparent,rgba(0,198,255,0.4),transparent); opacity: 0; transition: opacity 0.3s; }
.stat-item::after { content: ''; position: absolute; inset: 0; background: radial-gradient(circle at var(--mx,50%) var(--my,50%), rgba(0,198,255,0.04) 0%, transparent 60%); opacity: 0; transition: opacity 0.4s; }
.stat-item:hover { transform: translateY(-6px); border-color: rgba(0,198,255,0.3); box-shadow: 0 12px 32px rgba(0,0,0,0.35), 0 0 20px rgba(0,198,255,0.05); }
.stat-item:hover::before { opacity: 1; }
.stat-item:hover::after { opacity: 1; }
.stat-icon { font-size: 22px; margin-bottom: 8px; display: inline-block; transition: transform 0.3s; }
.stat-item:hover .stat-icon { transform: scale(1.15); }
.stat-number { font-size: 30px; font-weight: 800; color: #00C6FF; font-family: 'JetBrains Mono',monospace; text-shadow: 0 0 20px rgba(0,198,255,0.15); }
.stat-label { font-size: 11px; color: #64748b; margin-top: 4px; }
.hero-core-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 2px; }
.core-tag { padding: 5px 14px; background: rgba(0,229,255,0.06); border: 1px solid rgba(0,229,255,0.15); border-radius: 16px; font-size: 11px; color: #00E5FF; transition: all 0.3s cubic-bezier(0.16,1,0.3,1); }
.core-tag:hover { background: rgba(0,229,255,0.12); border-color: rgba(0,229,255,0.3); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,229,255,0.08); }
.hero-actions { display: flex; gap: 14px; margin-top: 6px; }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  background: linear-gradient(135deg,#00E5FF,#00B8CC); border: none; color: #0B0F19;
  padding: 13px 28px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer; transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
  box-shadow: 0 4px 16px rgba(0,229,255,0.2);
}
.btn-primary:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(0,229,255,0.35); }
.btn-primary:active { transform: translateY(-1px); }
.btn-secondary { background: transparent; border: 1px solid rgba(0,229,255,0.35); color: #00E5FF; padding: 13px 28px; border-radius: 12px; font-weight: 500; font-size: 14px; cursor: pointer; transition: all 0.3s cubic-bezier(0.16,1,0.3,1); }
.btn-secondary:hover { background: rgba(0,229,255,0.08); transform: translateY(-3px); border-color: rgba(0,229,255,0.5); }
.btn-lg { padding: 15px 34px; font-size: 15px; border-radius: 14px; }

/* Hero 右侧可视化区域 */
.hero-visual { position: relative; display: flex; justify-content: center; align-items: center; min-height: 380px; }
.mini-network { position: absolute; width: 260px; height: 260px; bottom: 10%; right: 15%; opacity: 0.6; }
.network-svg { width: 100%; height: 100%; filter: drop-shadow(0 0 20px rgba(0,198,255,0.1)); }
.net-core { filter: drop-shadow(0 0 12px rgba(239,68,68,0.6)); }
.conn-line { stroke-dasharray: 200; stroke-dashoffset: 200; animation: lineFlow 4s ease-in-out infinite; }
.conn-line-weak { animation: lineFade 6s ease-in-out infinite; }
.c1 { animation-delay: 0s; }
.c2 { animation-delay: 0.6s; }
.c3 { animation-delay: 1.2s; }
.c4 { animation-delay: 1.8s; }
.c5 { animation-delay: 2.4s; }
.c6 { animation-delay: 3s; }
@keyframes lineFlow { 0% { stroke-dashoffset: 200; opacity: 0.2; } 50% { stroke-dashoffset: 0; opacity: 0.8; } 100% { stroke-dashoffset: -200; opacity: 0.2; } }
@keyframes lineFade { 0%,100% { opacity: 0.05; } 50% { opacity: 0.15; } }
.scroll-hint { position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 6px; color: #64748b; font-size: 12px; cursor: pointer; animation: scrollHint 2s ease-in-out infinite; }
@keyframes scrollHint { 0%,100% { opacity: 0.4; transform: translateX(-50%) translateY(0); } 50% { opacity: 1; transform: translateX(-50%) translateY(4px); } }

/* ===== 通用板块 ===== */
.section-block { padding: 80px 36px; position: relative; z-index: 1; }
.section-block::before { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 60%; max-width: 400px; height: 1px; background: linear-gradient(90deg, transparent, rgba(0,198,255,0.08), transparent); pointer-events: none; }
.block-label { text-align: center; font-size: 10px; font-weight: 700; letter-spacing: 4px; color: rgba(0,198,255,0.45); margin-bottom: 6px; }
.block-title { text-align: center; font-size: 30px; font-weight: 800; margin: 0 0 8px; background: linear-gradient(135deg,#e2e8f0 0%,#00C6FF 50%,#8B5CF6 100%); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: titleShift 4s ease-in-out infinite; }
@keyframes titleShift { 0%,100% { background-position: 0% center; } 50% { background-position: 100% center; } }
.block-desc { text-align: center; font-size: 14px; color: #64748b; margin: 0 auto 36px; max-width: 600px; }

/* ====== 板块2：项目背景（优化） ====== */
.bg-block { background: linear-gradient(180deg, #020812, #0a1228); position: relative; }
.bg-block::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 50% 30% at 50% 0%, rgba(0,198,255,0.04) 0%, transparent 60%);
  pointer-events: none;
}
.bg-data-wall { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; max-width: 1200px; margin: 0 auto 36px; position: relative; z-index: 1; }
.bg-big-num {
  text-align: center; padding: 28px 16px;
  background: linear-gradient(160deg, rgba(15,23,42,0.6), rgba(10,18,36,0.4));
  border: 1px solid rgba(0,198,255,0.06);
  border-radius: 14px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative; overflow: hidden;
}
.bg-big-num::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, transparent, currentColor, transparent);
  opacity: 0; transition: opacity 0.3s;
}
.bg-big-num:hover { transform: translateY(-4px); border-color: rgba(0,198,255,0.18); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
.bg-big-num:hover::before { opacity: 0.3; }
.bgn-value { font-size: 42px; font-weight: 900; font-family: 'JetBrains Mono',monospace; letter-spacing: -1px; }
.bgn-label { font-size: 13px; color: #e2e8f0; margin: 6px 0 4px; font-weight: 500; }
.bgn-source { font-size: 10px; color: rgba(71,85,105,0.7); }

.bg-problem-solution {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  max-width: 1200px; margin: 0 auto;
  position: relative; z-index: 1;
}
.bgp-col { display: flex; flex-direction: column; gap: 0; }
.bgp-col-header {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px; margin-bottom: 10px;
  border-radius: 10px; font-size: 13px; font-weight: 700;
}
.bgp-col-header.phdr { background: rgba(239,68,68,0.08); color: #F87171; }
.bgp-col-header.shdr { background: rgba(0,229,255,0.08); color: #00E5FF; }
.bgp-col-header.ehdr { background: rgba(34,197,94,0.08); color: #4ADE80; }
.phdr-icon { font-size: 15px; }
.phdr-text { flex: 1; letter-spacing: 0.3px; }
.phdr-count { font-size: 10px; background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 6px; font-weight: 500; }
.bgp-list { display: flex; flex-direction: column; gap: 8px; }
.bgp-item {
  display: flex; gap: 12px; padding: 14px 15px;
  background: rgba(0,0,0,0.2);
  border-radius: 10px;
  border-left: 3px solid rgba(239,68,68,0.3);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.bgp-item.sol { border-left-color: rgba(0,229,255,0.3); }
.bgp-item.eff { border-left-color: rgba(34,197,94,0.3); }
.bgp-item:hover { background: rgba(0,0,0,0.3); transform: translateX(3px); }
.bgp-icon { font-size: 22px; flex-shrink: 0; margin-top: 1px; }
.bgp-text { flex: 1; min-width: 0; }
.bgp-text strong { font-size: 13px; color: #e2e8f0; display: block; margin-bottom: 3px; }
.bgp-text p { font-size: 11px; color: #94a3b8; margin: 0; line-height: 1.6; }
.bge-value { font-size: 24px; font-weight: 800; font-family: 'JetBrains Mono',monospace; margin-top: 4px; text-shadow: 0 0 20px currentColor; }

/* ====== 板块3：项目简介（优化） ====== */
.intro-block { background: linear-gradient(180deg, #0a1228, #060d20); }
.intro-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; max-width: 1200px; margin: 0 auto 36px; }
.intro-card {
  padding: 32px 26px;
  background: linear-gradient(160deg, rgba(15,23,42,0.6), rgba(10,18,36,0.3));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 14px;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative; overflow: hidden;
}
.intro-card::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(160deg, transparent, rgba(0,198,255,0.02));
  opacity: 0; transition: opacity 0.4s;
}
.intro-card:hover { transform: translateY(-4px); border-color: rgba(0,198,255,0.2); box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
.intro-card:hover::before { opacity: 1; }
.intro-icon-wrapper {
  width: 64px; height: 64px; margin: 0 auto 16px;
  background: linear-gradient(135deg, rgba(0,198,255,0.1), rgba(0,198,255,0.03));
  border: 1px solid rgba(0,198,255,0.1);
  border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s;
}
.intro-card:hover .intro-icon-wrapper { background: linear-gradient(135deg, rgba(0,198,255,0.15), rgba(0,198,255,0.05)); border-color: rgba(0,198,255,0.25); transform: scale(1.05); }
.intro-big-icon { font-size: 30px; }
.intro-card-title { font-size: 16px; color: #e2e8f0; font-weight: 700; margin: 0 0 8px; }
.intro-card-desc { font-size: 13px; color: #64748b; margin: 0; line-height: 1.8; }
.intro-tech-flow { max-width: 900px; margin: 0 auto; background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.06); border-radius: 14px; padding: 28px 24px; transition: all 0.3s; }
.intro-tech-flow:hover { border-color: rgba(0,198,255,0.14); }
.itf-title { font-size: 15px; font-weight: 700; color: #e2e8f0; text-align: center; margin-bottom: 24px; letter-spacing: 0.5px; }
.itf-steps { display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 0; }
.itf-step { display: flex; align-items: center; gap: 8px; padding: 8px 4px; transition: all 0.3s; }
.itf-step:hover { transform: translateY(-2px); }
.itf-num { font-size: 10px; color: rgba(0,198,255,0.2); font-family: 'JetBrains Mono',monospace; font-weight: 700; }
.itf-icon { font-size: 24px; }
.itf-label { font-size: 12px; color: #94a3b8; white-space: nowrap; font-weight: 500; }
.itf-connector { display: flex; flex-direction: column; align-items: center; margin: 0 12px; }
.itf-line { width: 32px; height: 1px; background: linear-gradient(90deg, rgba(0,198,255,0.1), rgba(0,198,255,0.25), rgba(0,198,255,0.1)); }
.itf-arrow { font-size: 10px; color: rgba(0,198,255,0.25); margin-top: -2px; animation: itfArrow 2s ease-in-out infinite; }
@keyframes itfArrow { 0%,100% { opacity: 0.2; transform: translateX(0); } 50% { opacity: 0.6; transform: translateX(2px); } }

/* ====== 板块4：技术路线（全面重写） ====== */
.arch-block { background: linear-gradient(180deg, #020812, #060d20); position: relative; }

/* 背景装饰网格线 */
.arch-block::before {
  content: ''; position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(0,198,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,198,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

.arch-canvas {
  max-width: 860px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 0;
  position: relative; z-index: 1;
}

/* 各层卡片 */
.arch-layer {
  background: linear-gradient(135deg, rgba(10, 20, 40, 0.7), rgba(15, 25, 45, 0.5));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 14px;
  padding: 20px 24px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}

/* 层卡片左上角光晕 */
.arch-layer::before {
  content: ''; position: absolute; top: -40px; left: -40px;
  width: 80px; height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0,198,255,0.06) 0%, transparent 70%);
  transition: all 0.5s ease;
  pointer-events: none;
}

.arch-layer:hover {
  border-color: rgba(0,198,255,0.2);
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0,0,0,0.3), 0 0 20px rgba(0,198,255,0.03);
}

.arch-layer:hover::before { transform: scale(2.5); opacity: 0.6; }

/* 不同层特殊颜色 */
.layer-front { border-left: 3px solid rgba(0,212,255,0.3); }
.layer-api { border-left: 3px solid rgba(139,92,246,0.3); }
.layer-ai { border-left: 3px solid rgba(245,158,11,0.3); }
.layer-data { border-left: 3px solid rgba(16,185,129,0.3); }

.layer-label {
  font-size: 10px; font-weight: 800;
  color: rgba(0,198,255,0.5);
  letter-spacing: 3px; margin-bottom: 10px;
  text-transform: uppercase; font-family: 'SF Mono', 'Consolas', monospace;
}

.layer-items { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }

.arch-mod {
  padding: 7px 14px;
  background: rgba(0,0,0,0.35);
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 8px;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

.arch-mod:hover {
  background: rgba(0,198,255,0.08);
  border-color: rgba(0,198,255,0.25);
  color: #e2e8f0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,198,255,0.06);
}

.arch-mod small {
  display: block; font-size: 9px; color: #64748b; margin-top: 2px;
}

.layer-front .arch-mod { border-color: rgba(0,212,255,0.12); }
.layer-front .arch-mod:hover { border-color: rgba(0,212,255,0.35); box-shadow: 0 4px 12px rgba(0,212,255,0.08); }
.layer-api .arch-mod { border-color: rgba(139,92,246,0.12); }
.layer-api .arch-mod:hover { border-color: rgba(139,92,246,0.35); box-shadow: 0 4px 12px rgba(139,92,246,0.08); }
.layer-ai .arch-mod { border-color: rgba(245,158,11,0.12); }
.layer-ai .arch-mod:hover { border-color: rgba(245,158,11,0.35); box-shadow: 0 4px 12px rgba(245,158,11,0.08); }

.agent-items .arch-mod { padding: 8px 12px; text-align: center; min-width: 90px; }

/* 前端箭头 */
.arch-arrow-right {
  color: rgba(0,198,255,0.25);
  font-size: 14px;
  font-family: 'SF Mono', monospace;
  animation: arrowPulse 2s ease-in-out infinite;
}
@keyframes arrowPulse { 0%,100% { opacity: 0.25; transform: translateX(0); } 50% { opacity: 0.6; transform: translateX(3px); } }

/* 层间连接器 */
.arch-connector {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 24px;
  position: relative;
}
.conn-line {
  flex: 1; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,198,255,0.15), rgba(0,198,255,0.25), rgba(0,198,255,0.15), transparent);
  position: relative;
}
.conn-line::before {
  content: '';
  position: absolute; left: 0; top: -2px;
  width: 6px; height: 5px;
  background: rgba(0,198,255,0.3);
  border-radius: 50%;
  animation: connDotMove 3s ease-in-out infinite;
}
@keyframes connDotMove {
  0% { left: 0; opacity: 0.2; }
  50% { left: 100%; opacity: 0.8; }
  100% { left: 0; opacity: 0.2; }
}
.conn-label {
  font-size: 9px; color: rgba(0,198,255,0.2);
  letter-spacing: 1.5px; white-space: nowrap;
  font-family: 'SF Mono', 'Consolas', monospace;
}

/* AI 模块特殊样式 */
.ai-mod { border-color: rgba(245,158,11,0.2) !important; }
.ai-mod:hover { border-color: rgba(245,158,11,0.4) !important; box-shadow: 0 4px 12px rgba(245,158,11,0.08) !important; }

/* 数据层模块 */
.data-mod { border-color: rgba(16,185,129,0.2) !important; }
.data-mod:hover { border-color: rgba(16,185,129,0.4) !important; box-shadow: 0 4px 12px rgba(16,185,129,0.08) !important; }

/* Agent 流程演示 - Pipeline 流水线 */
.agent-flow-section {
  max-width: 900px; margin: 32px auto 0;
  background: linear-gradient(135deg, rgba(10,20,40,0.7), rgba(15,25,50,0.5));
  border: 1px solid rgba(255,184,0,0.08);
  border-radius: 16px;
  padding: 28px 30px 24px;
  position: relative; z-index: 1;
  transition: all 0.3s;
}
.agent-flow-section:hover { border-color: rgba(255,184,0,0.18); }
.af-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.af-icon { font-size: 22px; }
.af-title { font-size: 15px; font-weight: 700; color: #e2e8f0; flex: 1; letter-spacing: 0.3px; }
.af-header-right { display: flex; align-items: center; gap: 12px; }
.af-phase { font-size: 11px; color: #64748b; background: rgba(0,0,0,0.2); padding: 3px 10px; border-radius: 6px; }
.af-demo-btn {
  padding: 7px 20px;
  background: linear-gradient(135deg, #FFB800, #FF8C00);
  border: none; border-radius: 8px; color: #0B0F19;
  font-size: 12px; font-weight: 700; cursor: pointer;
  transition: all 0.3s; letter-spacing: 0.5px;
}
.af-demo-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(255,184,0,0.35); }
.af-demo-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.pipeline-container { position: relative; padding: 4px 0; }
.pipeline-progress-bar {
  position: absolute; top: 32px; left: 40px; right: 40px;
  height: 3px; background: rgba(255,255,255,0.06);
  border-radius: 2px; overflow: hidden; z-index: 0;
}
.pipeline-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00E5FF, #FFB800);
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 8px rgba(0,229,255,0.3);
}
.pipeline-steps { display: flex; flex-direction: column; gap: 0; position: relative; z-index: 1; }
.pipeline-step {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 10px 0;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0.5;
}
.pipeline-step.active { opacity: 1; }
.pipeline-step.completed { opacity: 0.8; }
.pipeline-step:hover:not(.active) { opacity: 0.7; }
.pipeline-marker-col {
  display: flex; flex-direction: column; align-items: center;
  min-width: 44px; position: relative;
}
.pipeline-marker {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  position: relative; z-index: 2;
  background: rgba(45,59,82,0.5);
  border: 2px solid rgba(255,255,255,0.08);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.pipeline-step.active .pipeline-marker {
  background: linear-gradient(135deg, rgba(255,184,0,0.25), rgba(255,140,0,0.15));
  border-color: #FFB800;
  box-shadow: 0 0 20px rgba(255,184,0,0.25), inset 0 0 12px rgba(255,184,0,0.06);
  transform: scale(1.12);
}
.pipeline-step.completed .pipeline-marker {
  background: linear-gradient(135deg, rgba(0,229,255,0.2), rgba(0,198,255,0.1));
  border-color: #00E5FF;
  box-shadow: 0 0 16px rgba(0,229,255,0.2);
}
.marker-ring {
  position: absolute; inset: -3px; border-radius: 50%;
  border: 1.5px solid transparent;
  transition: all 0.5s;
}
.pipeline-step.active .marker-ring {
  border-color: rgba(255,184,0,0.3);
  animation: ringPulse 1.5s ease-in-out infinite;
}
@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 0; }
}
.marker-icon { font-size: 15px; line-height: 1; position: relative; z-index: 3; }
.pipeline-step.active .marker-icon { animation: iconBounce 0.5s ease; }
@keyframes iconBounce {
  0% { transform: scale(0.8); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
.marker-pulse {
  position: absolute; inset: -8px; border-radius: 50%;
  background: rgba(255,184,0,0.08);
  opacity: 0; transform: scale(0.5);
  transition: all 0.5s;
}
.pipeline-step.active .marker-pulse {
  opacity: 1; transform: scale(1);
  animation: pulseGlow 1.5s ease-in-out infinite 0.3s;
}
@keyframes pulseGlow {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0; transform: scale(1.3); }
}
.pipeline-line {
  flex: 1; width: 2px; background: rgba(255,255,255,0.06);
  margin: 2px 0; position: relative; min-height: 20px;
}
.pipeline-line-fill {
  position: absolute; top: 0; left: 0; width: 100%;
  height: 0%; background: linear-gradient(to bottom, #00E5FF, #FFB800);
  transition: height 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  border-radius: 1px;
}
.pipeline-line-fill.filled { height: 100%; }

.pipeline-content-col { flex: 1; padding-top: 6px; min-width: 0; }
.pipeline-label {
  font-size: 14px; font-weight: 600; color: #94a3b8;
  margin-bottom: 3px; transition: all 0.4s;
}
.pipeline-step.active .pipeline-label {
  color: #FFD54F; text-shadow: 0 0 12px rgba(255,184,0,0.2);
}
.pipeline-step.completed .pipeline-label { color: #00E5FF; }
.pipeline-desc {
  font-size: 11px; color: #475569; line-height: 1.5;
  max-width: 380px; transition: all 0.4s;
}
.pipeline-step.active .pipeline-desc { color: #94a3b8; }
.pipeline-step.completed .pipeline-desc { color: #64748b; }

.pipeline-status {
  margin-top: 14px; padding: 10px 16px;
  background: rgba(0,0,0,0.2); border-radius: 8px;
  text-align: center;
}
.status-text {
  font-size: 12px; color: #94a3b8; display: flex;
  align-items: center; justify-content: center; gap: 8px;
}
.status-text.completed { color: #00E5FF; }
.status-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #FFB800; display: inline-block;
  animation: dotBlink 0.8s ease-in-out infinite;
}
.status-dot.done { background: #00E5FF; animation: none; }
@keyframes dotBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 技术选型论证 */
.tech-rationale { max-width: 860px; margin: 24px auto 0; position: relative; z-index: 1; }
.tr-title { font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 14px; letter-spacing: 0.3px; }
.tr-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.tr-item { display: flex; gap: 10px; padding: 14px; background: rgba(0,0,0,0.2); border: 1px solid rgba(0,198,255,0.06); border-radius: 10px; transition: all 0.3s; }
.tr-item:hover { background: rgba(0,0,0,0.3); border-color: rgba(0,198,255,0.15); }
.tr-icon { font-size: 22px; flex-shrink: 0; }
.tr-body { flex: 1; min-width: 0; }
.tr-name { font-size: 12px; font-weight: 700; color: #e2e8f0; margin-bottom: 3px; }
.tr-why { font-size: 10px; color: #94a3b8; line-height: 1.5; margin-bottom: 4px; }
.tr-alt { font-size: 9px; color: #64748b; }
.tr-verdict { display: inline-block; margin-left: 6px; padding: 0 6px; font-size: 8px; font-weight: 700; background: rgba(0,229,255,0.1); border-radius: 4px; color: #00E5FF; }

/* ====== 板块5：创新点 ====== */
.innov-block { background: linear-gradient(180deg, #020812, #0a1228); position: relative; }
.innov-category { max-width: 1200px; margin: 0 auto 28px; }
.innov-category:last-child { margin-bottom: 0; }
.ic-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #94a3b8; margin-bottom: 14px; letter-spacing: 0.3px; }
.ic-badge { display: inline-block; padding: 3px 12px; background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.15); border-radius: 8px; font-size: 10px; font-weight: 700; color: #00E5FF; letter-spacing: 0.5px; }
.ic-badge-app { background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.15); color: #A78BFA; }
.innov-grid { display: grid; gap: 18px; }
.innov-grid-3 { grid-template-columns: repeat(3, 1fr); }
.innov-card { padding: 24px; background: linear-gradient(160deg, rgba(15,23,42,0.6), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.innov-card:hover { transform: translateY(-4px); border-color: rgba(0,198,255,0.2); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
.innov-icon { font-size: 32px; margin-bottom: 12px; display: inline-block; transition: all 0.3s; }
.innov-card:hover .innov-icon { transform: scale(1.1); }
.innov-title { font-size: 15px; font-weight: 700; color: #e2e8f0; margin: 0 0 8px; }
.innov-desc { font-size: 12px; color: #64748b; margin: 0 0 14px; line-height: 1.8; }
.innov-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.innov-tag { padding: 2px 10px; background: rgba(0,229,255,0.06); border: 1px solid rgba(0,229,255,0.1); border-radius: 8px; font-size: 9px; color: #00E5FF; transition: all 0.3s; }
.innov-tag:hover { background: rgba(0,229,255,0.12); border-color: rgba(0,229,255,0.25); }

/* ====== 板块6：应用场景（优化） ====== */
.scenario-block { background: linear-gradient(180deg, #0a1228, #020812); }
.scenario-tabs { display: flex; gap: 0; max-width: 900px; margin: 0 auto 24px; background: rgba(0,0,0,0.25); border-radius: 12px; padding: 4px; border: 1px solid rgba(0,198,255,0.04); }
.scenario-tabs button {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 11px 14px; border: none; border-radius: 10px; background: transparent;
  color: #64748b; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.3s;
}
.scenario-tabs button.active { background: rgba(0,198,255,0.15); color: #00E5FF; box-shadow: 0 4px 12px rgba(0,198,255,0.06); }
.scenario-tabs button:hover:not(.active) { color: #94a3b8; background: rgba(255,255,255,0.02); }
.sc-panel {
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
  max-width: 900px; margin: 0 auto; padding: 32px;
  background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 14px;
  min-height: 260px; transition: all 0.3s;
}
.sc-panel:hover { border-color: rgba(0,198,255,0.16); }
.sc-left { display: flex; flex-direction: column; gap: 12px; }
.sc-icon-large { font-size: 44px; margin-bottom: 4px; }
.sc-panel-title { font-size: 18px; font-weight: 700; color: #e2e8f0; margin: 0; }
.sc-panel-desc { font-size: 13px; color: #64748b; margin: 0; line-height: 1.7; }
.sc-feature-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.sc-feature-list li { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #94a3b8; padding: 4px 0; }
.sfl-dot { width: 6px; height: 6px; background: #00C6FF; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 6px rgba(0,198,255,0.3); }
.sc-right { display: flex; flex-direction: column; gap: 12px; }
.scr-label { font-size: 11px; font-weight: 700; color: rgba(0,198,255,0.4); letter-spacing: 2px; text-transform: uppercase; }
.scr-list { display: flex; flex-direction: column; gap: 12px; }
.scr-item { display: flex; gap: 10px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 10px; transition: all 0.3s; }
.scr-item:hover { background: rgba(0,0,0,0.3); transform: translateX(2px); }
.scr-icon { font-size: 20px; flex-shrink: 0; }
.scr-text strong { font-size: 13px; color: #e2e8f0; display: block; margin-bottom: 2px; }
.scr-text p { font-size: 11px; color: #64748b; margin: 0; }
.sc-slide-enter-active, .sc-slide-leave-active { transition: all 0.35s cubic-bezier(0.16,1,0.3,1); }
.sc-slide-enter-from { opacity: 0; transform: translateX(20px); }
.sc-slide-leave-to { opacity: 0; transform: translateX(-20px); }

/* ====== 板块7：功能演示（优化） ====== */
.features-block { background: linear-gradient(180deg, #020812, #0a1228); }
.features-carousel { max-width: 860px; margin: 0 auto; }
.fc-tabs { display: flex; gap: 0; margin-bottom: 22px; background: rgba(0,0,0,0.25); border-radius: 12px; padding: 4px; border: 1px solid rgba(0,198,255,0.04); }
.fc-tabs button { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 11px 14px; border: none; border-radius: 10px; background: transparent; color: #64748b; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.3s; }
.fc-tabs button.active { background: rgba(0,198,255,0.15); color: #00E5FF; box-shadow: 0 4px 12px rgba(0,198,255,0.06); }
.fc-tabs button:hover:not(.active) { color: #94a3b8; background: rgba(255,255,255,0.02); }
.fc-panel { background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; padding: 30px; min-height: 260px; transition: all 0.3s; }
.fc-panel:hover { border-color: rgba(0,198,255,0.16); }
.fc-content { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; }
.fc-icon-large { font-size: 48px; }
.fc-title { font-size: 18px; font-weight: 700; color: #e2e8f0; margin: 0; }
.fc-desc { font-size: 13px; color: #64748b; line-height: 1.7; margin: 0; max-width: 560px; }
.fc-techs { display: flex; gap: 6px; flex-wrap: wrap; }
.fc-tech { padding: 3px 10px; background: rgba(0,229,255,0.08); border: 1px solid rgba(0,229,255,0.15); border-radius: 10px; font-size: 10px; color: #00E5FF; }
.fc-demo-list { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-top: 6px; }
.fc-demo-item { display: flex; align-items: center; gap: 6px; padding: 8px 18px; background: rgba(0,0,0,0.25); border: 1px solid rgba(0,198,255,0.06); border-radius: 10px; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.fc-demo-item:hover { background: rgba(0,198,255,0.08); border-color: rgba(0,198,255,0.2); transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,198,255,0.04); }
.demo-icon { font-size: 16px; }
.demo-text { font-size: 11px; color: #94a3b8; }
.fc-slide-enter-active, .fc-slide-leave-active { transition: all 0.35s cubic-bezier(0.16,1,0.3,1); }
.fc-slide-enter-from { opacity: 0; transform: translateX(20px); }
.fc-slide-leave-to { opacity: 0; transform: translateX(-20px); }

/* ====== 板块8：系统实战展示（替换文件目录） ====== */
.system-block { background: linear-gradient(180deg, #0a1228, #020812); }
.ui-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; max-width: 1100px; margin: 0 auto; }
.ui-card { background: linear-gradient(160deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16,1,0.3,1); }
.ui-card:hover { border-color: rgba(0,198,255,0.2); transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
.ui-mock { border-bottom: 1px solid rgba(0,198,255,0.06); }
.uim-top { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: rgba(0,0,0,0.2); border-bottom: 1px solid rgba(255,255,255,0.03); }
.uim-dots { display: flex; gap: 4px; }
.uim-dots span { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.15); }
.uim-title { font-size: 10px; color: rgba(255,255,255,0.3); font-family: 'SF Mono','Consolas',monospace; }
.uim-body { padding: 20px; min-height: 140px; display: flex; align-items: center; justify-content: center; }
.uim-content { width: 100%; display: flex; flex-direction: column; gap: 14px; align-items: center; }
.uim-icon { font-size: 36px; filter: drop-shadow(0 0 12px rgba(0,198,255,0.2)); }
.uim-preview { font-size: 11px; color: rgba(255,255,255,0.5); font-family: 'SF Mono',monospace; background: rgba(0,0,0,0.2); padding: 6px 14px; border-radius: 8px; }
.uim-metrics { display: flex; gap: 20px; justify-content: center; }
.uim-metric { text-align: center; }
.um-value { display: block; font-size: 22px; font-weight: 800; font-family: 'JetBrains Mono',monospace; }
.um-label { display: block; font-size: 9px; color: #64748b; margin-top: 2px; }
.uim-bars { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.uim-bar-row { display: flex; align-items: center; gap: 8px; }
.ub-label { flex: 0 0 48px; font-size: 10px; color: #94a3b8; }
.ub-track { flex: 1; height: 6px; background: rgba(0,0,0,0.3); border-radius: 3px; overflow: hidden; }
.ub-fill { height: 100%; border-radius: 3px; transition: width 1s cubic-bezier(0.16,1,0.3,1); }
.ub-val { flex: 0 0 36px; font-size: 10px; color: #e2e8f0; font-family: 'JetBrains Mono',monospace; text-align: right; }
.ui-title { font-size: 14px; font-weight: 700; color: #e2e8f0; padding: 14px 18px 4px; margin: 0; }
.ui-desc { font-size: 11px; color: #64748b; padding: 0 18px; margin: 0 0 10px; line-height: 1.6; }
.ui-techs { display: flex; gap: 4px; flex-wrap: wrap; padding: 0 18px 14px; }
.ui-tech { padding: 2px 8px; background: rgba(0,229,255,0.06); border: 1px solid rgba(0,229,255,0.08); border-radius: 6px; font-size: 9px; color: #00E5FF; }

/* ====== 板块9：成果展示（优化） ====== */
.result-block { background: linear-gradient(180deg, #020812, #0a1228); }
.result-big-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 18px; max-width: 1100px; margin: 0 auto 28px; }
.result-big-item { text-align: center; padding: 24px; background: linear-gradient(160deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); position: relative; overflow: hidden; }
.result-big-item::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, currentColor, transparent); opacity: 0; transition: opacity 0.3s; }
.result-big-item:hover { transform: translateY(-4px); border-color: rgba(0,198,255,0.2); box-shadow: 0 10px 28px rgba(0,0,0,0.2); }
.result-big-item:hover::before { opacity: 0.3; }
.rb-value { font-size: 40px; font-weight: 900; font-family: 'JetBrains Mono',monospace; letter-spacing: -1px; }
.rb-label { font-size: 13px; color: #e2e8f0; margin: 4px 0; font-weight: 500; }
.rb-compare { font-size: 10px; color: rgba(71,85,105,0.7); }
.result-bottom-row { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; max-width: 1100px; margin: 0 auto; align-items: start; }

/* 对比条 */
.result-compare { background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; padding: 20px; transition: all 0.3s; }
.result-compare:hover { border-color: rgba(0,198,255,0.16); }
.rc-header { font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid rgba(0,198,255,0.06); }
.rc-list { display: flex; flex-direction: column; gap: 14px; }
.rc-row { }
.rc-label { font-size: 10px; color: #94a3b8; margin-bottom: 6px; font-weight: 500; }
.rc-bars { display: flex; flex-direction: column; gap: 4px; }
.rc-bar-group { display: flex; align-items: center; gap: 6px; }
.rc-bar-label { font-size: 9px; color: #64748b; flex: 0 0 32px; font-family: 'SF Mono','Consolas',monospace; }
.rc-track { flex: 1; height: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; overflow: hidden; }
.rc-fill { height: 100%; border-radius: 4px; transition: width 1.2s cubic-bezier(0.16,1,0.3,1); }
.rc-fill.traditional { opacity: 0.5; }
.rc-fill.ours { box-shadow: 0 0 8px rgba(34,197,94,0.2); }
.rc-val { flex: 0 0 36px; font-size: 10px; color: #94a3b8; font-family: 'JetBrains Mono',monospace; text-align: right; }
.rc-ours { font-weight: 700; }

/* 指标进度条（自绘，替代 Element Plus Progress） */
.result-metric-list { display: flex; flex-direction: column; gap: 14px; }
.rm-item { padding: 14px 18px; background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 12px; transition: all 0.3s; }
.rm-item:hover { border-color: rgba(0,198,255,0.2); transform: translateX(2px); }
.rm-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.rm-icon { font-size: 16px; }
.rm-label { flex: 1; font-size: 12px; color: #94a3b8; }
.rm-val { font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono',monospace; }
.rm-bar { height: 8px; background: rgba(0,0,0,0.25); border-radius: 4px; overflow: hidden; }
.rm-fill { height: 100%; border-radius: 4px; transition: width 1.5s cubic-bezier(0.16,1,0.3,1); box-shadow: 0 0 6px currentColor; }

/* ====== 板块10：总结展望（优化） ====== */
.outlook-block { background: linear-gradient(180deg, #0a1228, #020812); }
.outlook-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; max-width: 1200px; margin: 0 auto; }
.outlook-card { padding: 30px 26px; background: linear-gradient(160deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.08); border-radius: 14px; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); position: relative; overflow: hidden; }
.outlook-card::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, rgba(0,198,255,0.15), transparent); opacity: 0; transition: opacity 0.4s; }
.outlook-card:hover { transform: translateY(-3px); border-color: rgba(0,198,255,0.2); box-shadow: 0 10px 28px rgba(0,0,0,0.15); }
.outlook-card:hover::after { opacity: 1; }
.ol-icon { font-size: 34px; margin-bottom: 12px; }
.ol-title { font-size: 16px; font-weight: 700; color: #e2e8f0; margin: 0 0 14px; }
.ol-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.ol-list li { font-size: 12px; color: #94a3b8; line-height: 1.6; padding-left: 16px; position: relative; transition: all 0.2s; }
.ol-list li::before { content: ''; position: absolute; left: 0; top: 8px; width: 5px; height: 5px; border-radius: 50%; background: rgba(0,198,255,0.3); }
.ol-list li:hover { color: #c8d6e5; padding-left: 20px; }

/* ====== CTA（优化） ====== */
.cta-block { background: linear-gradient(180deg, #020812, #0a1228); display: flex; align-items: center; justify-content: center; }
.cta-container { text-align: center; padding: 56px; max-width: 650px; width: 100%; background: linear-gradient(135deg, rgba(15,23,42,0.5), rgba(10,18,36,0.3)); border: 1px solid rgba(0,198,255,0.1); border-radius: 20px; transition: all 0.3s; }
.cta-container:hover { border-color: rgba(0,198,255,0.2); box-shadow: 0 0 40px rgba(0,198,255,0.03); }
.cta-badge { font-size: 16px; margin-bottom: 16px; display: inline-block; }
.cta-title { font-size: 26px; font-weight: 800; margin: 0 0 10px; background: linear-gradient(135deg,#e2e8f0,#00C6FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.cta-desc { font-size: 13px; color: #64748b; margin: 0 0 28px; }
.cta-buttons { display: flex; justify-content: center; gap: 14px; }

/* ====== Footer（优化） ====== */
.showcase-footer { background: linear-gradient(180deg, #050D1A, #030810); border-top: 1px solid rgba(0,198,255,0.06); padding: 32px 36px; }
.footer-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
.footer-brand { display: flex; align-items: center; gap: 10px; }
.fb-text { font-size: 14px; font-weight: 700; background: linear-gradient(135deg,#00C6FF,#00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.fb-sub { font-size: 10px; color: #64748b; }
.footer-copy { font-size: 10px; color: rgba(71,85,105,0.6); }

/* ===== Responsive ===== */
@media (max-width: 1100px) {
  .hero-content { grid-template-columns: 1fr; text-align: center; }
  .hero-stats { grid-template-columns: repeat(2,1fr); }
  .hero-desc { margin: 0 auto; }
  .hero-actions { justify-content: center; }
  .bg-data-wall, .result-big-row { grid-template-columns: repeat(2,1fr); }
  .bg-problem-solution { grid-template-columns: 1fr; gap: 16px; }
  .intro-grid, .innov-grid-3, .outlook-grid { grid-template-columns: repeat(2,1fr); }
  .ui-grid { grid-template-columns: repeat(2,1fr); }
  .tr-grid { grid-template-columns: 1fr; }
  .result-bottom-row { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .nav-links { display: none; }
  .title-line { font-size: 34px; }
  .hero-stats { grid-template-columns: 1fr; }
  .bg-data-wall, .result-big-row { grid-template-columns: 1fr; }
  .intro-grid, .innov-grid-3, .outlook-grid { grid-template-columns: 1fr; }
  .sc-panel { grid-template-columns: 1fr; }
  .fc-tabs, .scenario-tabs { flex-direction: column; }
  .fc-tabs button, .scenario-tabs button { padding: 10px; }
  .ui-grid { grid-template-columns: 1fr; }
  .section-block { padding: 50px 16px; }
}
</style>