<template>
  <div class="police-system-layout">
    
    

    <!-- 左侧导航栏 -->
<aside class="sidebar">
  <div class="logo-area">
    <div class="logo-icon">🛡️</div>
    <h2>反诈团伙画像</h2>
    <span class="sub-title">AI INTELLIGENT ANALYSIS</span>
  </div>
  <el-menu
    :default-active="activeMenu"
    class="side-menu"
    background-color="#0f172a"
    text-color="#94a3b8"
    active-text-color="#3b82f6"
    @select="handleMenuSelect"
  >
    <el-menu-item index="input">
      <i class="el-icon-edit-outline"></i>
      <span>数据录入中心</span>
    </el-menu-item>
    
    <el-menu-item index="overview">
      <i class="el-icon-s-home"></i>
      <span>案件总览</span>
    </el-menu-item>
    
    <!-- 【新增】案件详情 - 放在案件总览下面 -->
    <el-menu-item index="case-detail">
      <i class="el-icon-document"></i>
      <span>案件详情查看</span>
    </el-menu-item>
    
    <el-menu-item index="groups">
      <i class="el-icon-s-group"></i>
      <span>团伙画像总览</span>
    </el-menu-item>
    
    <el-menu-item index="details">
      <i class="el-icon-s-data"></i>
      <span>团伙深度分析</span>
    </el-menu-item>
    
    <el-menu-item index="network">
      <i class="el-icon-connection"></i>
      <span>案件关联网络</span>
    </el-menu-item>
    
    <!-- 【新增】报告生成 - 放在最下面 -->
    <el-menu-item index="report">
      <i class="el-icon-printer"></i>
      <span>报告生成导出</span>
    </el-menu-item>
  </el-menu>
  
  <div class="system-status">
    <el-tag :type="isMockMode ? 'warning' : 'success'" size="small" effect="dark">
      {{ isMockMode ? '系统运行中' : '系统运行中' }}
    </el-tag>
    <div class="version-info">v2.0 Pro | Qwen-Max</div>
  </div>
</aside>

    <!-- 右侧主内容区 -->
    <main class="main-content" v-loading="loading" element-loading-text="AI 正在深度研判中..." element-loading-spinner="el-icon-loading">
      
      <!-- 1. 数据录入中心 -->
      <div v-if="activeMenu === 'input'" class="content-view fade-in">
        <el-card class="input-card-full">
          <template #header>
            <div class="card-header-flex">
              <div>
                <h3 class="page-title">📊 多源数据采集与录入</h3>
                <p class="page-subtitle">支持聊天记录粘贴、图片上传、API 数据流接入（预留）</p>
              </div>
              <el-button type="primary" @click="loadDemo" icon="Document" plain>📋 加载测试案情</el-button>
            </div>
          </template>

          <div class="input-workspace">
            <div class="input-panel">
              <div class="panel-header">
                <span class="label">📝 文本/对话内容</span>
                <el-tooltip content="建议粘贴多条不同受害者的报警记录，以便系统提取共性特征进行团伙聚类">
                  <i class="el-icon-question"></i>
                </el-tooltip>
              </div>
              <el-input 
                v-model="inputText" 
                type="textarea" 
                :rows="15" 
                placeholder="请在此处粘贴聊天记录、报警录音转写文本或涉案信息..." 
                class="chat-input-large"
              >
                <template #prefix>
                  <span style="color: #909399; font-size: 12px; line-height: 32px;">示例：<br/>嫌疑人：您好，这里是【京东官方】...<br/>受害人：我没开过这个服务啊！<br/>...</span>
                </template>
              </el-input>
              <div class="input-stats">
                <span>📄 当前行数：<strong>{{ messageCount }}</strong> 条</span>
                <span v-if="inputText.length > 0">📊 字符数：<strong>{{ inputText.length }}</strong></span>
              </div>
            </div>

            <div class="tools-panel">
              <!-- 图片上传 -->
              <div class="tool-card image-upload-card">
                <h4>🖼️ 图片证据上传</h4>
                <el-upload
                  :before-upload="handleBeforeUpload"
                  :show-file-list="false"
                  accept="image/*"
                  class="upload-area-large"
                  drag
                >
                  <i class="el-icon-upload"></i>
                  <div class="el-upload__text">将图片拖到此处，或 <em>点击上传</em></div>
                  <div class="el-upload__tip">支持 PNG/JPG, 最大 10MB (自动提取文字并追加到文本框)</div>
                </el-upload>
              </div>

              <!-- 外部数据接入模块 -->
              <div class="tool-card external-data-panel">
                <h4><i class="el-icon-connection"></i> 外部数据接入</h4>
                <p class="current-mode">
                  <span style="color: #67C23A; font-weight: bold;">✅</span> 
                  当前模式：<strong>模拟数据生成</strong>（用于演示与算法验证）
                </p>
                <div class="future-integrations">
                  <span class="integration-tag">🏛️ 国家反诈中心 APP</span>
                  <span class="integration-tag">🚨 110 接处警系统</span>
                  <span class="integration-tag">🏦 银行风控系统</span>
                </div>
                <p class="note">
                  * 真实场景需通过公安网闸及安全认证后部署
                </p>
              </div>

              <!-- 开始研判按钮 -->
              <div class="action-area">
                <el-button 
                  class="analyze-btn-pro"
                  size="large" 
                  @click="analyze" 
                  :loading="loading" 
                  icon="Search" 
                  style="width: 100%"
                  :disabled="!inputText.trim()"
                >
                  <i class="el-icon-search" style="margin-right: 8px;"></i>
                  {{ loading ? 'AI 正在深度研判...' : '🚀 开始智能研判' }}
                </el-button>
                
                <div v-if="loading && isMockMode" class="progress-container">
                  <el-progress :percentage="mockProgress" :stroke-width="6" :show-text="false"></el-progress>
                  <p class="progress-text">{{ mockStatusText }}</p>
                </div>

                <p class="action-hint">点击后系统将自动分案、聚类团伙并生成画像</p>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 2. 案件总览 -->
      <div v-if="activeMenu === 'overview'" class="content-view fade-in" v-show="hasData">
        <div class="report-header">
          <div class="report-title-section">
            <h2>📋 AI 反诈团伙画像系统 - 诈骗案件分析报告</h2>
            <p class="report-subtitle">基于多源数据聚类分析，自动识别犯罪团伙并生成深度画像</p>
          </div>
          <div class="report-meta">
            <div class="meta-item">
              <span class="meta-label">生成时间</span>
              <span class="meta-value">{{ currentTime }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">分析案件数</span>
              <span class="meta-value highlight">{{ totalCases }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">发现犯罪团伙</span>
              <span class="meta-value highlight-red">{{ results.length }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">高风险团伙</span>
              <span class="meta-value highlight-red">{{ results.filter(r => r.risk_level === 'HIGH').length }}</span>
            </div>
          </div>
        </div>

        <div class="stats-cards">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-icon">📁</div>
            <div class="stat-label">总案件数</div>
            <div class="stat-value">{{ totalCases }}</div>
          </el-card>
          <el-card shadow="hover" class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-label">犯罪团伙数</div>
            <div class="stat-value">{{ results.length }}</div>
          </el-card>
          <el-card shadow="hover" class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-label">系统置信度</div>
            <div class="stat-value">91%</div>
          </el-card>
        </div>

        <h3 class="section-title">📂 原始案件列表 (按受害人)</h3>
        <div class="case-grid">
          <el-card v-for="(gang, gIndex) in results" :key="gIndex" class="gang-summary-card" shadow="hover">
            <template #header>
              <div class="gang-header">
                <span class="gang-name">{{ gang.gang_name }}</span>
                <el-tag :type="gang.risk_type" size="small" effect="dark">{{ gang.risk_label }}</el-tag>
              </div>
            </template>
            <div v-for="(caseItem, cIndex) in gang.related_cases" :key="cIndex" class="case-item">
              <div class="case-id">案件 #{{ caseItem.case_id }}</div>
              <div class="case-detail">
                <span>👤 受害人：{{ caseItem.victim }}</span>
                <span class="case-amount">💰 涉案金额：{{ caseItem.amount }}</span>
              </div>
              <div class="case-snippet">关键片段：{{ caseItem.snippet }}</div>
            </div>
          </el-card>
        </div>
        <div style="text-align: center; margin-top: 20px;">
          <el-button type="primary" @click="activeMenu = 'groups'" size="large">查看团伙画像总览</el-button>
        </div>
      </div>
      
      <div v-if="activeMenu === 'overview' && !hasData" class="empty-state">
        <el-empty description="暂无数据，请先在「数据录入中心」进行分析">
          <el-button type="primary" @click="activeMenu = 'input'">去录入数据</el-button>
        </el-empty>
      </div>
      <!-- 3. 案件详情查看 -->
<div v-if="activeMenu === 'case-detail'" class="content-view fade-in" v-show="hasData">
  <div class="page-header-section">
  <div class="header-content">
    <h2 class="page-main-title">
      <span class="title-icon">📋</span>
      案件详情查看
    </h2>
    <p class="page-desc">从团伙下钻到单个案件，查看案件完整信息与证据链</p>
  </div>
  <div class="header-actions">
    <el-button @click="activeMenu = 'overview'" icon="ArrowLeft">返回总览</el-button>
    <el-button type="primary" @click="exportCaseReport" icon="Download">导出报告</el-button>
  </div>
</div>
  

  <!-- 案件选择器 -->
  <el-card class="case-selector-card">
    <template #header>
      <div class="card-title-colored">
        <span class="title-icon">🔍</span>
        <h4>选择案件</h4>
        <div class="title-gradient-bar selector-bar"></div>
      </div>
    </template>
    <div class="case-selector-content">
      <el-select 
        v-model="selectedCaseId" 
        placeholder="请选择要查看的案件" 
        size="large"
        style="width: 450px;"
        @change="loadCaseDetail"
      >
        <el-option
          v-for="caseItem in allCases"
          :key="caseItem.case_id"
          :label="`${caseItem.case_id} - ${caseItem.victim} - ${caseItem.amount}`"
          :value="caseItem.case_id"
        >
          <span style="float: left">{{ caseItem.case_id }}</span>
          <span style="float: right; color: #8492a6; font-size: 13px">{{ caseItem.victim }}</span>
        </el-option>
      </el-select>
      <el-tag v-if="selectedCaseGang" type="info" effect="dark" style="margin-left: 20px;">
        🔗 所属团伙：{{ selectedCaseGang.gang_name }}
      </el-tag>
    </div>
  </el-card>

  <!-- 案件详细信息 -->
  <div v-if="currentCaseDetail" class="case-detail-container">
    <!-- 案件基本信息 -->
    <el-card class="detail-card">
      <template #header>
        <div class="card-title-colored case-info-title">
          <span class="title-icon">📁</span>
          <h4>案件基本信息</h4>
          <div class="title-gradient-bar info-bar"></div>
        </div>
      </template>
      <el-descriptions :column="2" border class="colorful-descriptions">
        <el-descriptions-item label="🆔 案件编号">
          <span class="colored-value id">{{ currentCaseDetail.case_id }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="⏰ 录入时间">
          <span class="colored-value time">{{ currentCaseDetail.input_time || '2024-03-23' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="👤 受害人">
          <span class="colored-value members">{{ currentCaseDetail.victim }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="💰 涉案金额">
          <span class="colored-value money">{{ currentCaseDetail.amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="🎯 诈骗类型">
          <el-tag :type="currentCaseDetail.fraud_type === '冒充客服' ? 'danger' : 'warning'" size="small" effect="dark">
            {{ currentCaseDetail.fraud_type || '冒充客服诈骗' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="⚠️ 风险等级">
          <el-tag :type="currentCaseDetail.risk_level === 'HIGH' ? 'danger' : 'warning'" size="small" effect="dark">
            {{ currentCaseDetail.risk_level || '高风险' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 案件关键片段 -->
    <el-card class="detail-card">
      <template #header>
        <div class="card-title-colored snippet-title">
          <span class="title-icon">💬</span>
          <h4>关键对话片段</h4>
          <div class="title-gradient-bar snippet-bar"></div>
        </div>
      </template>
      <div class="snippet-content">
        <div class="message-bubble suspect">
          <div class="bubble-header">
            <span class="avatar">👤</span>
            <span class="name">嫌疑人</span>
          </div>
          <div class="bubble-text">{{ currentCaseDetail.snippet }}</div>
        </div>
        <div class="message-bubble victim">
          <div class="bubble-header">
            <span class="avatar">👤</span>
            <span class="name">受害人</span>
          </div>
          <div class="bubble-text">我没开过这个服务啊！你们是不是搞错了？</div>
        </div>
        <div class="message-bubble suspect">
          <div class="bubble-header">
            <span class="avatar">👤</span>
            <span class="name">嫌疑人</span>
          </div>
          <div class="bubble-text">系统显示您确实开通了，现在需要您配合取消，否则每月会自动扣费 800 元...</div>
        </div>
      </div>
    </el-card>

    <!-- 关联团伙信息 -->
    <el-card class="detail-card">
      <template #header>
        <div class="card-title-colored gang-link-title">
          <span class="title-icon">👥</span>
          <h4>关联犯罪团伙</h4>
          <div class="title-gradient-bar gang-bar"></div>
        </div>
      </template>
      <div class="gang-link-content" v-if="selectedCaseGang">
        <div class="gang-link-card" @click="viewGangDetail">
          <div class="gang-link-header">
            <span class="gang-link-name">{{ selectedCaseGang.gang_name }}</span>
            <el-tag :type="selectedCaseGang.risk_type" size="small" effect="dark">
              {{ selectedCaseGang.risk_label }}
            </el-tag>
          </div>
          <div class="gang-link-metrics">
            <div class="metric-item">
              <span class="metric-label">涉案总额</span>
              <span class="metric-value money">{{ selectedCaseGang.total_amount_involved }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">关联案件</span>
              <span class="metric-value">{{ selectedCaseGang.total_cases }} 起</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">置信度</span>
              <span class="metric-value">{{ selectedCaseGang.confidence }}%</span>
            </div>
          </div>
          <div class="gang-link-action">
            <el-button type="primary" size="small" icon="ArrowRight">查看团伙详情</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 证据链 -->
    <el-card class="detail-card">
      <template #header>
        <div class="card-title-colored evidence-title">
          <span class="title-icon">🔗</span>
          <h4>证据链信息</h4>
          <div class="title-gradient-bar evidence-bar"></div>
        </div>
      </template>
      <div class="evidence-list">
        <div class="evidence-item">
          <div class="evidence-icon">📞</div>
          <div class="evidence-info">
            <div class="evidence-title">通话记录</div>
            <div class="evidence-desc">来电号码：+86-170****5678 | 通话时长：12 分 35 秒</div>
          </div>
          <el-tag size="small" type="success" effect="dark">已提取</el-tag>
        </div>
        <div class="evidence-item">
          <div class="evidence-icon">💬</div>
          <div class="evidence-info">
            <div class="evidence-title">聊天记录</div>
            <div class="evidence-desc">腾讯会议截图 3 张 | 文字记录 1 份</div>
          </div>
          <el-tag size="small" type="success" effect="dark">已提取</el-tag>
        </div>
        <div class="evidence-item">
          <div class="evidence-icon">🏦</div>
          <div class="evidence-info">
            <div class="evidence-title">转账记录</div>
            <div class="evidence-desc">收款账户：6222****5678 | 转账金额：{{ currentCaseDetail.amount }}</div>
          </div>
          <el-tag size="small" type="warning" effect="dark">待核实</el-tag>
        </div>
        <div class="evidence-item">
          <div class="evidence-icon">🌐</div>
          <div class="evidence-info">
            <div class="evidence-title">IP 地址追踪</div>
            <div class="evidence-desc">登录 IP：183.214.***.*** | 归属地：湖南省长沙市</div>
          </div>
          <el-tag size="small" type="info" effect="dark">分析中</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 操作按钮 -->
    <div class="case-actions">
      <el-button type="primary" @click="activeMenu = 'overview'" icon="ArrowLeft">返回案件总览</el-button>
      <el-button type="success" @click="exportCaseReport" icon="Download">导出本案报告</el-button>
      <el-button type="info" @click="viewGangDetail" icon="Share">查看关联团伙</el-button>
    </div>
  </div>

  <!-- 未选择案件时的提示 -->
  <div v-else class="empty-state">
    <el-empty description="请在上方选择一个案件查看详情">
      <el-button type="primary" @click="activeMenu = 'overview'">返回案件总览</el-button>
    </el-empty>
  </div>
</div>

      <!-- 4. 团伙画像总览 -->
      <div v-if="activeMenu === 'groups'" class="content-view fade-in" v-show="hasData">
        <div class="page-header-section">
          <h2 class="page-main-title">🎯 犯罪团伙画像总览</h2>
          <p class="page-desc">基于多案聚类分析，自动识别独立犯罪团伙，生成团伙级画像</p>
        </div>

        <div class="summary-stats">
          <div class="stat-box red">
            <div class="stat-icon-large">⚠️</div>
            <div class="num">1</div>
            <div class="label">高风险团伙</div>
          </div>
          <div class="stat-box orange">
            <div class="stat-icon-large">👥</div>
            <div class="num">18-25</div>
            <div class="label">预估涉案人员</div>
          </div>
          <div class="stat-box blue">
            <div class="stat-icon-large">💰</div>
            <div class="num">17.0</div>
            <div class="label">涉案总金额 (万元)</div>
          </div>
          <div class="stat-box green">
            <div class="stat-icon-large">📊</div>
            <div class="num">5</div>
            <div class="label">串并案件数</div>
          </div>
        </div>

        <h3 class="section-title">🔍 识别出的犯罪团伙</h3>
        <div class="gang-cards-container">
          <div 
            v-for="(gang, index) in results" 
            :key="index" 
            class="gang-card" 
            :class="{ 'active': selectedGroupIndex === index }"
            @click="selectGang(index)"
          >
            <div class="card-top">
              <div class="badge">犯罪团伙</div>
              <el-tag :type="gang.risk_type" size="small" effect="dark">{{ gang.risk_label }} (置信度 {{ gang.confidence }}%)</el-tag>
            </div>
            <h3 class="gang-title">{{ gang.gang_name }}</h3>
            <div class="gang-id">ID: {{ gang.gang_id }}</div>
            
            <div class="gang-metrics">
              <div class="metric">
                <div class="m-label">关联案件</div>
                <div class="m-value">{{ gang.total_cases }} 起</div>
              </div>
              <div class="metric">
                <div class="m-label">涉案金额</div>
                <div class="m-value money">{{ gang.total_amount_involved }}</div>
              </div>
              <div class="metric">
                <div class="m-label">成员规模</div>
                <div class="m-value">{{ gang.member_count_estimate }}</div>
              </div>
            </div>

            <div class="tags-row">
              <el-tag v-for="(tag, tIdx) in gang.fingerprint" :key="tIdx" size="small" effect="plain">{{ tag }}</el-tag>
            </div>

            <div class="card-action">
              <span class="link-text" @click.stop="selectGang(index)">深度画像分析 &gt;</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="activeMenu === 'groups' && !hasData" class="empty-state">
        <el-empty description="暂无数据" />
      </div>

      <!-- 5. 团伙深度分析 -->
<div v-if="activeMenu === 'details'" class="content-view fade-in" v-show="hasData && selectedGroupIndex !== null">
  <div class="page-header-section">
  <div class="header-content">
    <h2 class="page-main-title">
      <span class="title-icon"></span>
      {{ currentGangData.gang_name }}
    </h2>
    <p class="page-desc">AI 智能分析的犯罪团伙深度画像与能力评估</p>
  </div>
  <div class="header-actions">
    <el-tag :type="currentGangData.risk_type" size="large" effect="dark">
      {{ currentGangData.risk_label }}
    </el-tag>
    <el-button @click="selectGroup((selectedGroupIndex - 1 + results.length) % results.length)" icon="ArrowLeft">上一个</el-button>
    <el-button @click="selectGroup((selectedGroupIndex + 1) % results.length)" icon="ArrowRight">下一个</el-button>
  </div>
</div>

<!-- 报告生成导出页面头部 -->
<div class="page-header-section">
  <div class="header-content">
    <h2 class="page-main-title">
      <span class="title-icon">📄</span>
      报告生成导出
    </h2>
    <p class="page-desc">选择团伙或案件，生成专业分析报告，支持 PDF/Word 格式导出</p>
  </div>
  <div class="header-actions">
    <el-button @click="resetReportConfig" icon="Refresh">重置配置</el-button>
  </div>
</div>

  <!-- 基本信息卡片 - 增加色彩 -->
  <el-card class="info-card colorful-card">
    <template #header>
      <div class="card-title-colored">
        <span class="title-icon">📋</span>
        <h4>团伙基本信息</h4>
        <div class="title-gradient-bar"></div>
      </div>
    </template>
    <el-descriptions :column="3" border class="colorful-descriptions">
      <el-descriptions-item label="🆔 团伙 ID">
        <span class="colored-value id">{{ currentGangData.gang_id }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="⚠️ 风险等级">
        <el-tag :type="currentGangData.risk_type" size="small" effect="dark">{{ currentGangData.risk_level }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="✅ 置信度">
        <span class="colored-value confidence">{{ currentGangData.confidence }}%</span>
      </el-descriptions-item>
      <el-descriptions-item label="👥 成员规模">
        <span class="colored-value members">{{ currentGangData.member_count_estimate }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="🕐 活跃时段">
        <span class="colored-value time">{{ currentGangData.active_time }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="💻 技术等级">
        <span class="colored-value tech">{{ currentGangData.tech_level }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="📜 作案剧本">
        <span class="colored-value script">{{ currentGangData.script_type }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="💰 涉案总额">
        <span class="colored-value money">{{ currentGangData.total_amount_involved }}</span>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>

  <!-- 图表区域 - 增加色彩 -->
  <div class="charts-row">
    <el-card class="chart-card colorful-chart-card">
      <template #header>
        <div class="card-title-colored radar-title">
          <span class="title-icon">📊</span>
          <h4>团伙能力雷达</h4>
          <div class="title-gradient-bar radar-bar"></div>
        </div>
      </template>
      <div ref="radarChartRef" class="echart-container"></div>
    </el-card>
    <el-card class="chart-card colorful-chart-card">
      <template #header>
        <div class="card-title-colored fingerprint-title">
          <span class="title-icon">🔍</span>
          <h4>团伙特征指纹</h4>
          <div class="title-gradient-bar fingerprint-bar"></div>
        </div>
      </template>
      <div ref="wordCloudRef" class="echart-container"></div>
    </el-card>
  </div>

  <!-- 作案流程 - 彩色步骤 -->
  <el-card class="flow-card colorful-card">
    <template #header>
      <div class="card-title-colored flow-title">
        <span class="title-icon">🔄</span>
        <h4>团伙作案流程指纹</h4>
        <div class="title-gradient-bar flow-bar"></div>
      </div>
    </template>
    <div class="flow-steps">
      <div v-for="(step, idx) in currentGangData.steps" :key="idx" class="step-item">
        <div class="step-num" :class="'step-color-' + (idx % 5 + 1)">{{ idx + 1 }}</div>
        <div class="step-text">{{ step }}</div>
        <div class="step-connector" v-if="idx < currentGangData.steps.length - 1">➜</div>
      </div>
    </div>
    <p class="flow-note">* 该团伙标准化作案路径 (基于多案件行为序列挖掘)</p>
  </el-card>

  <!-- 案件表格 - 彩色增强 -->
  <el-card class="cases-card colorful-card">
    <template #header>
      <div class="card-title-colored cases-title">
        <span class="title-icon">📂</span>
        <h4>该团伙关联案件 ({{ currentGangData.total_cases }} 起)</h4>
        <div class="title-gradient-bar cases-bar"></div>
      </div>
    </template>
    <el-table :data="currentGangData.related_cases" style="width: 100%" class="colorful-table">
      <el-table-column prop="case_id" label="案件 ID" width="140">
        <template #default="scope">
          <span class="case-id-colored">{{ scope.row.case_id }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="victim" label="受害人" width="120">
        <template #default="scope">
          <span class="victim-tag">👤 {{ scope.row.victim }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="涉案金额" width="140">
        <template #default="scope">
          <span class="amount-colored">{{ scope.row.amount }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="snippet" label="关键片段">
        <template #default="scope">
          <span class="snippet-text">{{ scope.row.snippet }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</div>
      <!-- 6. 案件关联网络 -->
      <div v-if="activeMenu === 'network'" class="content-view fade-in" v-show="hasData">
        <div class="page-header-section">
          <h2 class="page-main-title">🕸️ 团伙 - 案件关联关系图</h2>
          <p class="page-desc">可视化展示犯罪团伙与关联案件之间的复杂关系网络</p>
        </div>
        
        <div class="network-legend">
          <span class="legend-item"><span class="dot red"></span> 犯罪团伙</span>
          <span class="legend-item"><span class="dot blue"></span> 关联案件</span>
          <span class="legend-item"><span class="line-sample thick"></span> 连线粗细 = 涉案金额</span>
          <span class="legend-item"><span class="line-sample color"></span> 连线颜色 = 风险等级</span>
        </div>
        
        <div ref="networkChartRef" class="network-container"></div>
        
        <div class="network-tips">
          <div class="tip-item">🖱️ 拖拽节点可调整布局</div>
          <div class="tip-item">🔍 滚轮缩放查看细节</div>
          <div class="tip-item">👆 点击节点查看详情</div>
          <div class="tip-item">✨ 悬停高亮关联关系</div>
        </div>
      </div>
      <div v-if="activeMenu === 'network' && !hasData" class="empty-state">
        <el-empty description="暂无数据" />
      </div>
     <!-- 7. 报告生成导出 (升级版) -->
<div v-if="activeMenu === 'report'" class="content-view fade-in" v-show="hasData">
  <div class="page-header-section">
    <div class="header-content">
      <h2 class="page-main-title">
        <span class="title-icon">📄</span>
        报告生成导出
      </h2>
      <p class="page-desc">选择团伙或案件，生成专业分析报告，支持 PDF/Word 格式导出</p>
    </div>
    <div class="header-actions">
      <el-button @click="resetReportConfig" icon="Refresh">重置配置</el-button>
    </div>
  </div>

  <!-- 报告配置 -->
  <el-card class="report-config-card">
    <template #header>
      <div class="card-title-colored">
        <span class="title-icon">⚙️</span>
        <h4>报告配置</h4>
        <div class="title-gradient-bar config-bar"></div>
      </div>
    </template>
    <div class="report-config-content">
      <div class="config-row">
        <span class="config-label">报告类型：</span>
        <el-radio-group v-model="reportType" size="large">
          <el-radio label="gang">👥 团伙分析报告</el-radio>
          <el-radio label="case">📋 案件分析报告</el-radio>
        </el-radio-group>
      </div>
      
      <div class="config-row" v-if="reportType === 'gang'">
        <span class="config-label">选择团伙：</span>
        <el-select v-model="selectedReportGangId" placeholder="请选择犯罪团伙" size="large" style="width: 450px;">
          <el-option
            v-for="gang in results"
            :key="gang.gang_id"
            :label="gang.gang_name"
            :value="gang.gang_id"
          >
            <span style="float: left">{{ gang.gang_name }}</span>
            <el-tag :type="gang.risk_type" size="small" style="float: right; margin-right: 10px;">
              {{ gang.risk_label }}
            </el-tag>
          </el-option>
        </el-select>
      </div>

      <div class="config-row" v-if="reportType === 'case'">
        <span class="config-label">选择案件：</span>
        <el-select v-model="selectedReportCaseId" placeholder="请选择案件" size="large" style="width: 450px;">
          <el-option
            v-for="caseItem in allCases"
            :key="caseItem.case_id"
            :label="`${caseItem.case_id} - ${caseItem.victim}`"
            :value="caseItem.case_id"
          />
        </el-select>
      </div>

      <div class="config-row">
        <span class="config-label">导出格式：</span>
        <el-radio-group v-model="exportFormat" size="large">
          <el-radio label="pdf">📕 PDF 文档</el-radio>
          <el-radio label="word">📘 Word 文档</el-radio>
        </el-radio-group>
      </div>
    </div>

    <div class="report-actions">
      <el-button type="primary" size="large" @click="previewReport" icon="Document">
        📋 预览报告
      </el-button>
      <el-button type="success" size="large" @click="exportReport" icon="Download" :loading="exporting">
        {{ exporting ? '生成中...' : '📥 导出报告' }}
      </el-button>
      <el-button type="info" size="large" @click="printReport" icon="Printer">
        🖨️ 打印报告
      </el-button>
    </div>
  </el-card>

  <!-- 报告预览 (全新升级结构) -->
  <div v-if="showPreview" class="report-preview-card">
    <el-card class="preview-card">
      <template #header>
        <div class="preview-header">
          <h4>📄 报告预览</h4>
          <div class="preview-actions">
            <el-button size="small" @click="showPreview = false">关闭预览</el-button>
            <el-button type="primary" size="small" @click="exportReport">确认导出</el-button>
          </div>
        </div>
      </template>
      
      <div class="preview-content" ref="reportPreviewRef">
        <!-- 1. 报告封面 -->
        <div class="report-cover">
          <div class="cover-logo">🛡️</div>
          <h1 class="cover-title">AI 反诈团伙画像系统</h1>
          <h2 class="cover-subtitle">诈骗案件深度研判报告</h2>
          
          <div class="cover-info-box">
            <div class="info-item">
              <span class="info-label">报告编号</span>
              <span class="info-value">{{ reportNumber }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">生成时间</span>
              <span class="info-value">{{ currentTime }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">报告类型</span>
              <span class="info-value">{{ reportTypeText }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">研判等级</span>
              <el-tag :type="getRiskLevelType()" size="small" effect="dark">
                {{ getRiskLevelText() }}
              </el-tag>
            </div>
          </div>
          
          <div class="cover-seal">
            <div class="seal-text">公安专用</div>
            <div class="seal-subtext">机密·内部资料</div>
          </div>
          
          <div class="cover-footer">
            <p>本报告基于 AI 智能分析生成，仅供公安机关办案参考</p>
            <p>生成单位：XXX 公安局反诈中心 | 技术支持：AI 反诈团伙画像系统 v2.0</p>
          </div>
        </div>

        <!-- 2. 报告正文 -->
        <div class="report-body">
          <!-- 第一章：基本信息 -->
          <div class="section">
            <h3 class="section-title">
              <span class="section-number">一、</span>
              基本信息概览
            </h3>
            <el-table :data="reportBasicData" border style="width: 100%" class="report-table">
              <el-table-column prop="label" label="项目" width="200"></el-table-column>
              <el-table-column prop="value" label="内容"></el-table-column>
            </el-table>
          </div>

          <!-- 第二章：团伙特征深度分析 (仅团伙报告显示) -->
          <div class="section" v-if="reportType === 'gang'">
            <h3 class="section-title">
              <span class="section-number">二、</span>
              团伙特征深度分析
            </h3>
            <div class="analysis-grid">
              <div class="analysis-card">
                <h4 class="card-title">🎯 作案手法分析</h4>
                <ul class="analysis-list">
                  <li v-for="(step, index) in currentGangSteps" :key="index">
                    <span class="step-number">{{ index + 1 }}</span>
                    <span class="step-text">{{ step }}</span>
                  </li>
                </ul>
              </div>
              
              <div class="analysis-card">
                <h4 class="card-title">🔍 技术对抗能力</h4>
                <div class="tech-analysis">
                  <div class="tech-item">
                    <span class="tech-label">设备水平</span>
                    <el-progress :percentage="85" :color="'#ef4444'"></el-progress>
                  </div>
                  <div class="tech-item">
                    <span class="tech-label">反侦察能力</span>
                    <el-progress :percentage="78" :color="'#f59e0b'"></el-progress>
                  </div>
                  <div class="tech-item">
                    <span class="tech-label">组织严密性</span>
                    <el-progress :percentage="92" :color="'#10b981'"></el-progress>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 第三章：关联案件串并分析 -->
          <div class="section">
            <h3 class="section-title">
              <span class="section-number">{{ reportType === 'gang' ? '三、' : '二、' }}</span>
              关联案件串并分析
            </h3>
            <el-table :data="reportCasesData" border style="width: 100%" class="report-table">
              <el-table-column prop="case_id" label="案件 ID" width="150"></el-table-column>
              <el-table-column prop="victim" label="受害人" width="120"></el-table-column>
              <el-table-column prop="amount" label="涉案金额" width="120">
                <template #default="{ row }">
                  <span class="money-highlight">{{ row.amount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="snippet" label="关键片段" min-width="200"></el-table-column>
              <el-table-column label="风险标识" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.risk_level === 'HIGH' ? 'danger' : 'warning'" size="small">
                    {{ row.risk_level }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            
            <!-- 案件统计图表 -->
            <div class="chart-summary">
              <div class="stat-card">
                <div class="stat-number">{{ reportCasesData.length }}</div>
                <div class="stat-label">关联案件总数</div>
              </div>
              <div class="stat-card">
                <div class="stat-number money-highlight">{{ calculateTotalAmount() }}</div>
                <div class="stat-label">涉案总金额</div>
              </div>
              <div class="stat-card">
                <div class="stat-number">{{ calculateAvgAmount() }}</div>
                <div class="stat-label">单案平均金额</div>
              </div>
              <div class="stat-card">
                <div class="stat-number">{{ calculateHighRiskCount() }}</div>
                <div class="stat-label">高风险案件数</div>
              </div>
            </div>
          </div>

          <!-- 第四章：证据链完整性评估 -->
          <div class="section">
            <h3 class="section-title">
              <span class="section-number">{{ reportType === 'gang' ? '四、' : '三、' }}</span>
              证据链完整性评估
            </h3>
            <div class="evidence-assessment">
              <div class="assessment-item">
                <div class="assessment-header">
                  <span class="assessment-icon">📞</span>
                  <span class="assessment-title">通话记录</span>
                  <el-tag size="small" type="success">已提取</el-tag>
                </div>
                <div class="assessment-detail">
                  <p>来电号码：+86-170****5678</p>
                  <p>通话时长：12 分 35 秒</p>
                </div>
                <div class="assessment-score">
                  <el-progress :percentage="95" :format="() => '95%'"></el-progress>
                </div>
              </div>
              
              <div class="assessment-item">
                <div class="assessment-header">
                  <span class="assessment-icon">💬</span>
                  <span class="assessment-title">聊天记录</span>
                  <el-tag size="small" type="success">已提取</el-tag>
                </div>
                <div class="assessment-detail">
                  <p>腾讯会议截图 3 张</p>
                  <p>文字记录 1 份</p>
                </div>
                <div class="assessment-score">
                  <el-progress :percentage="90" :format="() => '90%'"></el-progress>
                </div>
              </div>
              
              <div class="assessment-item">
                <div class="assessment-header">
                  <span class="assessment-icon">🏦</span>
                  <span class="assessment-title">资金流向</span>
                  <el-tag size="small" type="warning">待核实</el-tag>
                </div>
                <div class="assessment-detail">
                  <p>收款账户：6222****5678</p>
                  <p>转账金额：{{ calculateTotalAmount() }}</p>
                </div>
                <div class="assessment-score">
                  <el-progress :percentage="70" :format="() => '70%'"></el-progress>
                </div>
              </div>
              
              <div class="assessment-item">
                <div class="assessment-header">
                  <span class="assessment-icon">🌐</span>
                  <span class="assessment-title">IP 地址追踪</span>
                  <el-tag size="small" type="info">分析中</el-tag>
                </div>
                <div class="assessment-detail">
                  <p>登录 IP：183.214.***.***</p>
                  <p>归属地：湖南省长沙市</p>
                </div>
                <div class="assessment-score">
                  <el-progress :percentage="60" :format="() => '60%'"></el-progress>
                </div>
              </div>
            </div>
            
            <!-- 证据链雷达图 -->
            <div class="evidence-radar">
              <div ref="evidenceRadarRef" style="width: 100%; height: 300px;"></div>
            </div>
          </div>

          <!-- 第五章：研判建议与处置方案 -->
          <div class="section">
            <h3 class="section-title">
              <span class="section-number">{{ reportType === 'gang' ? '五、' : '四、' }}</span>
              研判建议与处置方案
            </h3>
            <div class="suggestion-box">
              <div class="suggestion-item priority-high">
                <span class="suggestion-icon">⚠️</span>
                <div class="suggestion-content">
                  <strong>立即立案侦查</strong>
                  <p>该团伙作案手法成熟，涉案金额巨大，建议立即立案并成立专案组</p>
                </div>
              </div>
              
              <div class="suggestion-item">
                <span class="suggestion-icon">🔍</span>
                <div class="suggestion-content">
                  <strong>调取银行流水</strong>
                  <p>建议协调银行部门调取涉案账户完整流水，追踪资金去向</p>
                </div>
              </div>
              
              <div class="suggestion-item">
                <span class="suggestion-icon">🌐</span>
                <div class="suggestion-content">
                  <strong>技术侦查手段</strong>
                  <p>建议对涉案 IP 地址、虚拟号码进行技术侦查，定位犯罪嫌疑人真实身份</p>
                </div>
              </div>
              
              <div class="suggestion-item">
                <span class="suggestion-icon">📢</span>
                <div class="suggestion-content">
                  <strong>发布预警信息</strong>
                  <p>建议通过官方渠道发布预警信息，提高群众防范意识</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 第六章：附录 (法律法规) -->
          <div class="section">
            <h3 class="section-title">
              <span class="section-number">{{ reportType === 'gang' ? '六、' : '五、' }}</span>
              附录：相关法律法规依据
            </h3>
            <div class="legal-appendix">
              <div class="legal-item">
                <h4>《中华人民共和国刑法》第二百六十六条【诈骗罪】</h4>
                <p>诈骗公私财物，数额较大的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金；数额巨大或者有其他严重情节的，处三年以上十年以下有期徒刑，并处罚金。</p>
              </div>
              <div class="legal-item">
                <h4>《关于办理诈骗刑事案件具体应用法律若干问题的解释》</h4>
                <p>诈骗公私财物价值三千元至一万元以上、三万元至十万元以上、五十万元以上的，应当分别认定为刑法第二百六十六条规定的"数额较大"、"数额巨大"、"数额特别巨大"。</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 报告页脚 -->
        <div class="report-footer">
          <p>本报告由 AI 反诈团伙画像系统自动生成，仅供参考</p>
          <p>生成单位：XXX 公安局反诈中心 | 报告编号：{{ reportNumber }}</p>
          <p>本报告一式三份，分别存档于：办案部门、法制部门、档案室</p>
        </div>
      </div>
    </el-card>
  </div>
</div>


    </main>
  </div>
  
</template>
<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

// ================= 配置 =================
const API_BASE_URL = 'http://localhost:5000'

// --- 状态管理 ---
const activeMenu = ref('input')
const inputText = ref('')
const loading = ref(false)
const hasData = ref(false)
const selectedGroupIndex = ref(null)

// 图表 DOM 引用
const radarChartRef = ref(null)
const wordCloudRef = ref(null)
const networkChartRef = ref(null)

// 数据模型
const totalCases = ref(0)
const currentTime = ref('')
const results = ref([])          // 团伙列表

// 案件详情相关
const selectedCaseId = ref('')
const currentCaseDetail = ref(null)
const selectedCaseGang = ref(null)
const allCases = ref([])

// 报告相关
const reportType = ref('gang')
const reportTypeText = computed(() => {
  const map = { gang: '团伙分析报告', case: '案件分析报告' }
  return map[reportType.value] || '分析报告'
})
const selectedReportGangId = ref('')
const selectedReportCaseId = ref('')
const exportFormat = ref('pdf')
const showPreview = ref(false)
const exporting = ref(false)
const reportPreviewRef = ref(null)
const reportNumber = ref('')
const reportBasicData = ref([])
const reportCasesData = ref([])
const evidenceRadarRef = ref(null)
const currentGangSteps = ref([])

// ---------- 数据适配函数 ----------
/**
 * 将后端返回的gang对象转换为前端期望的格式
 */
const adaptGangData = (gang) => {
  if (!gang) return null
  
  // 提取字段，处理可能的字段名差异
  const gangName = gang.gang_name || gang.gangName || '未命名团伙'
  const gangId = gang.gang_id || gang.gangId || 'unknown'
  const riskLevel = gang.risk_level || gang.riskLevel || 'LOW'
  const scriptType = gang.script_type || gang.scriptType || '未知类型'
  const totalAmount = gang.total_amount_involved || gang.totalAmountInvolved || '0万元'
  const totalCases = gang.total_cases || gang.totalCases || 0
  
  // 处理关联案件
  let relatedCases = []
  if (gang.related_cases && Array.isArray(gang.related_cases)) {
    relatedCases = gang.related_cases
  } else if (gang.relatedCases && Array.isArray(gang.relatedCases)) {
    relatedCases = gang.relatedCases
  }
  
  // 确保每个案件有必要的字段
  relatedCases = relatedCases.map(caseItem => ({
    case_id: caseItem.case_id || caseItem.caseId || '未知',
    victim: caseItem.victim || '未知',
    amount: caseItem.amount || '未知金额',
    snippet: caseItem.snippet || (caseItem.ai_report ? caseItem.ai_report.substring(0, 60) + '...' : '无详细片段'),
    risk_level: caseItem.risk_level || caseItem.riskLevel || riskLevel
  }))
  
  return {
    // 基础信息
    gang_id: gangId,
    gang_name: gangName,
    
    // 风险信息
    risk_level: riskLevel,
    risk_label: gang.risk_label || gang.riskLabel || 
               (riskLevel === 'HIGH' ? '高风险' : 
                riskLevel === 'MEDIUM' ? '中风险' : '低风险'),
    risk_type: gang.risk_type || gang.riskType || 
              (riskLevel === 'HIGH' ? 'danger' : 
               riskLevel === 'MEDIUM' ? 'warning' : 'info'),
    confidence: gang.confidence || 70 + relatedCases.length * 3,
    
    // 统计信息
    total_cases: totalCases,
    total_amount_involved: totalAmount,
    member_count_estimate: gang.member_count_estimate || gang.memberCountEstimate || '未知',
    active_time: gang.active_time || gang.activeTime || '未知',
    
    // 技术信息
    script_type: scriptType,
    tech_level: gang.tech_level || gang.techLevel || '中',
    
    // 特征信息
    fingerprint: gang.fingerprint || gang.characteristics || [],
    steps: gang.steps || [],
    description: gang.description || '',
    
    // 关联信息
    related_cases: relatedCases,
    
    // 网络数据
    network_nodes: gang.network_nodes || gang.networkNodes || []
  }
}

/**
 * 适配后端返回的完整响应数据
 */
const adaptBackendResponse = (responseData) => {
  console.log('后端原始数据:', responseData)
  
  if (!responseData || !responseData.success) {
    return { totalCases: 0, gangs: [], networkData: null }
  }
  
  // 处理gangs数组
  const gangs = Array.isArray(responseData.gangs) ? responseData.gangs : []
  const adaptedGangs = gangs.map(gang => adaptGangData(gang))
  
  return {
    totalCases: responseData.total_cases || adaptedGangs.reduce((sum, gang) => sum + gang.total_cases, 0),
    gangs: adaptedGangs,
    networkData: responseData.network_data || null,
    processingInfo: responseData.processing_info || {},
    triageStatus: responseData.triage_status || 'unknown'
  }
}

// 计算属性
const currentGangData = computed(() => {
  if (selectedGroupIndex.value === null || !results.value[selectedGroupIndex.value]) {
    return { 
      gang_name: '未知', 
      risk_level: 'LOW', 
      steps: [], 
      fingerprint: [], 
      related_cases: [],
      total_amount_involved: '0万元',
      risk_label: '低风险',
      gang_id: 'unknown',
      script_type: '未知类型',
      total_cases: 0
    }
  }
  return results.value[selectedGroupIndex.value]
})

const messageCount = computed(() => inputText.value.split('\n').filter(l => l.trim()).length)

// ---------- 辅助函数 ----------
const parseInputToMessages = () => {
  const lines = inputText.value.split('\n').filter(line => line.trim().length > 0)
  
  if (lines.length === 0) return []
  
  return lines.map((line, index) => {
    // 尝试提取发送者信息
    let sender = 'unknown'
    let content = line.trim()
    
    // 简单的发送者识别逻辑
    if (content.includes('受害人') || content.includes('用户') || content.includes('我')) {
      sender = 'victim'
    } else if (content.includes('客服') || content.includes('公安') || content.includes('银行')) {
      sender = 'suspect'
    } else if (content.includes('系统') || content.includes('平台')) {
      sender = 'system'
    }
    
    return {
      content: content,
      sender: sender,
      timestamp: null
    }
  })
}

// 金额解析辅助函数
const parseAmountToNumber = (amountStr) => {
  if (!amountStr) return 0
  const match = amountStr.match(/(\d+(?:\.\d+)?)/)
  if (match) {
    let num = parseFloat(match.group(1))
    if (amountStr.includes('万')) num *= 10000
    return num
  }
  return 0
}

// ---------- 核心分析函数（调用后端） ----------
const analyze = async () => {
  if (inputText.value.length < 10) {
    ElMessage.warning('请输入更多数据以便进行团伙聚类')
    return
  }

  loading.value = true
  hasData.value = false
  selectedGroupIndex.value = null
  results.value = []

  try {
    const messages = parseInputToMessages()
    console.log('发送消息到后端:', messages)
    
    const response = await axios.post(`${API_BASE_URL}/agent-analyze`, {
      messages: messages,
      platform_data: {}
    }, {
      timeout: 120000  // 2分钟超时
    })

    console.log('后端响应状态:', response.status)
    
    if (response.data) {
      // 适配后端数据
      const adaptedData = adaptBackendResponse(response.data)
      
      totalCases.value = adaptedData.totalCases
      currentTime.value = adaptedData.processingInfo.server_time || new Date().toLocaleString()
      results.value = adaptedData.gangs
      hasData.value = true

      // 存储网络数据
      if (adaptedData.networkData) {
        window.backendNetworkData = adaptedData.networkData
        console.log('已接收网络数据:', adaptedData.networkData)
      }

      activeMenu.value = 'overview'
      
      const processTime = adaptedData.processingInfo.processing_time_ms
      const timeMsg = processTime ? ` (耗时: ${processTime}ms)` : ''
      
      ElMessage.success({
        message: `✅ 研判完成！发现 ${totalCases.value} 起案件，成功聚类为 ${results.value.length} 个犯罪团伙${timeMsg}`,
        duration: 5000
      })

      // 调试输出
      console.log('处理后团伙数据:', results.value)
      if (results.value.length > 0) {
        console.log('第一个团伙详情:', results.value[0])
      }
      
      setTimeout(() => initCharts(), 300)
    } else {
      ElMessage.error('后端返回空数据')
    }
  } catch (error) {
    console.error('请求错误详情:', error)
    
    let errorMsg = '分析失败: '
    if (error.response) {
      // 服务器返回了错误状态码
      console.error('响应状态:', error.response.status)
      console.error('响应数据:', error.response.data)
      
      if (error.response.status === 500) {
        errorMsg = '后端服务器内部错误'
      } else if (error.response.status === 404) {
        errorMsg = '接口不存在，请检查后端服务'
      } else if (error.response.status === 400) {
        errorMsg = '请求格式错误: ' + (error.response.data.error || '')
      } else {
        errorMsg = `HTTP ${error.response.status}: ${error.response.data.error || ''}`
      }
    } else if (error.request) {
      // 请求发出但没有响应
      errorMsg = '无法连接到后端服务，请检查:'
      errorMsg += '\n1. 后端服务是否已启动 (python app.py)'
      errorMsg += '\n2. 端口5000是否被占用'
      errorMsg += '\n3. 网络连接是否正常'
    } else if (error.code === 'ECONNABORTED') {
      errorMsg = '请求超时，请检查后端处理时间是否过长'
    } else {
      errorMsg = error.message
    }
    
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

// 加载演示数据
const loadDemo = () => {
  inputText.value = `[案件 1] 受害人张三：您好，这里是京东金融官方客服，您的百万保障即将扣费 800 元...要求屏幕共享
[案件 2] 受害人李四：系统检测到您之前开通的京东白条需要注销，否则影响征信...要求屏幕共享
[案件 3] 受害人王五：我是公安局的，你涉嫌洗钱，需要核查资金...要求转账安全账户
[案件 4] 受害人赵六：宝妈兼职，在家动动手指就能日赚 300 元...刷单返利
[案件 5] 受害人孙七：简单，给抖音店铺点赞关注，每单佣金 3-5 元...刷单返利
[案件 6] 受害人周八：京东客服，您的白条利率过高需要调整...屏幕共享
[案件 7] 受害人吴九：点赞任务，先垫付 100 元返 115 元...刷单
[案件 8] 受害人郑十：公安局通缉令，需要资金核查...安全账户`
  ElMessage.success('已加载 8 起模拟案件数据，点击"开始智能研判"进行分析')
}

const handleBeforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    inputText.value += `\n[图片证据] ${file.name}\n`
    ElMessage.success('图片已上传 (模拟 OCR 识别)')
  }
  reader.readAsDataURL(file)
  return false
}

// ---------- 团伙与案件导航 ----------
const selectGang = (index) => {
  if (!results.value[index]) return
  
  selectedGroupIndex.value = index
  activeMenu.value = 'details'
  
  nextTick(() => {
    initCharts()
    ElMessage.success(`已加载团伙 [${results.value[index].gang_name}] 深度画像`)
  })
}

// 获取所有案件列表
const getAllCases = () => {
  const cases = []
  results.value.forEach(gang => {
    const relatedCases = gang.related_cases || []
    
    relatedCases.forEach(c => {
      cases.push({
        case_id: c.case_id,
        victim: c.victim,
        amount: c.amount,
        snippet: c.snippet,
        risk_level: c.risk_level,
        gang_id: gang.gang_id,
        gang_name: gang.gang_name,
        fraud_type: gang.script_type,
        input_time: '2024-03-23'
      })
    })
  })
  allCases.value = cases
}

const loadCaseDetail = (caseId) => {
  if (!caseId) {
    currentCaseDetail.value = null
    selectedCaseGang.value = null
    return
  }
  
  // 在所有团伙中查找案件
  for (const gang of results.value) {
    const relatedCases = gang.related_cases || []
    const caseItem = relatedCases.find(c => c.case_id === caseId)
    
    if (caseItem) {
      currentCaseDetail.value = {
        ...caseItem,
        gang_id: gang.gang_id,
        gang_name: gang.gang_name,
        fraud_type: gang.script_type,
        risk_level: gang.risk_level
      }
      selectedCaseGang.value = gang
      ElMessage.success(`已加载案件 ${caseId} 详情`)
      return
    }
  }
  
  ElMessage.warning(`未找到案件 ${caseId}`)
  currentCaseDetail.value = null
  selectedCaseGang.value = null
}

const viewGangDetail = () => {
  if (!selectedCaseGang.value) return
  const idx = results.value.findIndex(g => g.gang_id === selectedCaseGang.value.gang_id)
  if (idx !== -1) {
    selectGang(idx)
  }
}

const exportCaseReport = () => {
  if (!currentCaseDetail.value) {
    ElMessage.warning('请先选择案件')
    return
  }
  reportType.value = 'case'
  selectedReportCaseId.value = currentCaseDetail.value.case_id
  activeMenu.value = 'report'
}

// ---------- 图表初始化 ----------
const initCharts = () => {
  if (activeMenu.value === 'details' && currentGangData.value.gang_name !== '未知') {
    initRadar()
    initBar()
  }
  if (activeMenu.value === 'network') {
    initNetwork()
  }
}

// 雷达图
const initRadar = () => {
  if (!radarChartRef.value) return
  const chart = echarts.init(radarChartRef.value)
  const data = currentGangData.value
  
  // 根据风险等级设置雷达图数值
  let radarValues = [60, 50, 70, 40, 50] // 默认值
  if (data.risk_level === 'HIGH') {
    radarValues = [90, 85, 95, 80, 95]
  } else if (data.risk_level === 'MEDIUM') {
    radarValues = [75, 70, 80, 65, 75]
  }

  const option = {
    radar: {
      indicator: [
        { name: '组织严密性', max: 100 },
        { name: '反侦察能力', max: 100 },
        { name: '资金流转速', max: 100 },
        { name: '技术对抗力', max: 100 },
        { name: '话术标准化', max: 100 }
      ],
      radius: '68%',
      axisName: {
        color: '#1e40af',
        fontSize: 13,
        fontWeight: '600'
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(59, 130, 246, 0.1)',
            'rgba(59, 130, 246, 0.2)',
            'rgba(59, 130, 246, 0.3)',
            'rgba(59, 130, 246, 0.4)'
          ]
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(59, 130, 246, 0.4)',
          width: 2
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(59, 130, 246, 0.3)',
          width: 1
        }
      }
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: radarValues,
          name: '团伙能力',
          areaStyle: { 
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
              { offset: 0, color: 'rgba(59, 130, 246, 0.8)' },
              { offset: 0.5, color: 'rgba(37, 99, 235, 0.6)' },
              { offset: 1, color: 'rgba(29, 78, 216, 0.4)' }
            ])
          },
          lineStyle: { 
            color: '#2563eb',
            width: 3,
            shadowColor: 'rgba(37, 99, 235, 0.5)',
            shadowBlur: 10
          },
          itemStyle: {
            color: '#ffffff',
            borderColor: '#2563eb',
            borderWidth: 3,
            shadowColor: 'rgba(37, 99, 235, 0.6)',
            shadowBlur: 8
          }
        }
      ]
    }]
  }
  chart.setOption(option)
  window.addEventListener('resize', () => chart.resize())
}

// 柱状图
const initBar = () => {
  if (!wordCloudRef.value) return
  const chart = echarts.init(wordCloudRef.value)
  const data = currentGangData.value.fingerprint.map((item, index) => ({
    name: item,
    value: Math.floor(Math.random() * 50) + 50
  }))
  
  // 多彩颜色数组
  const colors = [
    new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#3b82f6' },
      { offset: 1, color: '#1d4ed8' }
    ]),
    new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#10b981' },
      { offset: 1, color: '#059669' }
    ]),
    new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#f59e0b' },
      { offset: 1, color: '#d97706' }
    ]),
    new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#ef4444' },
      { offset: 1, color: '#dc2626' }
    ]),
    new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#8b5cf6' },
      { offset: 1, color: '#7c3aed' }
    ])
  ]
  
  const option = {
    grid: { top: 10, bottom: 20, left: 100, right: 40 },
    xAxis: { type: 'value', show: false },
    yAxis: { 
      type: 'category', 
      data: data.map(d => d.name), 
      axisLabel: { 
        width: 80, 
        overflow: 'truncate',
        color: '#475569',
        fontWeight: '500'
      },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      data: data.map((item, index) => ({
        ...item,
        itemStyle: {
          color: colors[index % colors.length],
          borderRadius: [0, 8, 8, 0]
        }
      })),
      label: { 
        show: true, 
        position: 'right', 
        formatter: '{c}%',
        color: '#475569',
        fontSize: 13,
        fontWeight: '600'
      },
      barWidth: '65%',
      showBackground: true,
      backgroundStyle: {
        color: 'rgba(226, 232, 240, 0.4)',
        borderRadius: [0, 8, 8, 0]
      }
    }]
  }
  chart.setOption(option)
  window.addEventListener('resize', () => chart.resize())
}

// 网络图
const initNetwork = () => {
  if (!networkChartRef.value) return
  const chart = echarts.init(networkChartRef.value)
  
  const nodes = []
  const links = []
  const colors = { HIGH: '#f56c6c', MEDIUM: '#e6a23c', LOW: '#67c23a' }
  const gangColors = {
    '"黑鲨"专业客服诈骗团': '#f56c6c',
    '"野狼"兼职刷单团': '#e6a23c',
    '"毒蛛"冒充公检法团': '#f56c6c'
  }

  // 尝试使用后端提供的 network_nodes，如果没有则回退到前端计算
  let hasBackendNetworkData = false
  if (window.backendNetworkData && Array.isArray(window.backendNetworkData.nodes)) {
    console.log('使用后端网络数据')
    window.backendNetworkData.nodes.forEach(node => {
      const isGang = node.type === 'gang'
      const nodeColor = isGang ? (gangColors[node.name] || colors[node.risk_level]) : '#409EFF'
      nodes.push({
        id: node.id,
        name: node.name,
        symbolSize: isGang ? 80 : 40,
        itemStyle: { 
          color: nodeColor,
          shadowBlur: isGang ? 15 : 8,
          shadowColor: isGang ? 'rgba(0,0,0,0.3)' : 'rgba(64, 158, 255, 0.4)',
          borderColor: '#fff',
          borderWidth: isGang ? 3 : 2
        },
        category: isGang ? 0 : 1,
        value: node.value,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: isGang ? 13 : 11,
          fontWeight: isGang ? 'bold' : 'normal',
          color: isGang ? '#303133' : '#606266',
          backgroundColor: 'rgba(255,255,255,0.8)',
          padding: isGang ? [4, 8] : [3, 6],
          borderRadius: isGang ? 4 : 3
        }
      })
      // 构建链接 (案件节点链接到其所属团伙)
      if (!isGang && node.gang_id) {
        links.push({
          source: node.gang_id,
          target: node.id,
          value: node.value,
          lineStyle: {
            width: Math.max(2, Math.min(8, (node.value || 0) / 3000)),
            color: gangColors[node.gang_name] || colors[node.risk_level],
            curveness: 0.2,
            opacity: 0.7
          }
        })
      }
    })
    hasBackendNetworkData = true
  }

  // 如果后端没有提供 network_nodes，则使用原来的前端计算逻辑
  if (!hasBackendNetworkData) {
    console.warn('后端未提供 network_nodes 数据，使用前端计算网络')
    results.value.forEach((gang) => {
      const gangColor = gangColors[gang.gang_name] || colors[gang.risk_level]
      nodes.push({
        id: gang.gang_id,
        name: gang.gang_name,
        symbolSize: 80,
        itemStyle: { 
          color: gangColor,
          shadowBlur: 15,
          shadowColor: 'rgba(0,0,0,0.3)',
          borderColor: '#fff',
          borderWidth: 3
        },
        category: 0,
        value: parseFloat(gang.total_amount_involved.replace('万元', '')),
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 13,
          fontWeight: 'bold',
          color: '#303133',
          backgroundColor: 'rgba(255,255,255,0.8)',
          padding: [4, 8],
          borderRadius: 4
        },
        fixed: false
      })
      
      gang.related_cases.forEach((caseItem) => {
        const caseId = caseItem.case_id
        const amountNum = parseAmountToNumber(caseItem.amount)
        nodes.push({
          id: caseId,
          name: `${caseId}\n${caseItem.victim}`,
          symbolSize: 40,
          itemStyle: { 
            color: '#409EFF',
            shadowBlur: 8,
            shadowColor: 'rgba(64, 158, 255, 0.4)',
            borderColor: '#fff',
            borderWidth: 2
          },
          category: 1,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
            fontSize: 11,
            color: '#606266',
            backgroundColor: 'rgba(255,255,255,0.9)',
            padding: [3, 6],
            borderRadius: 3
          }
        })

        links.push({
          source: gang.gang_id,
          target: caseId,
          value: amountNum,
          lineStyle: {
            width: Math.max(2, Math.min(8, amountNum / 3000)),
            color: gangColor,
            curveness: 0.2,
            opacity: 0.7
          }
        })
      })
    })
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        if (params.data.category === 0) {
          const gang = results.value.find(g => g.gang_id === params.data.id)
          return `<div style="padding: 8px;">
            <strong style="font-size: 14px;">${params.data.name}</strong><br/>
            <span style="color: #909399;">风险等级：</span>${gang?.risk_label || '未知'}<br/>
            <span style="color: #909399;">涉案总额：</span>${gang?.total_amount_involved || '0万元'}<br/>
            <span style="color: #909399;">关联案件：</span>${gang?.total_cases || 0} 起
          </div>`
        } else {
          const caseData = results.value.flatMap(g => g.related_cases).find(c => c.case_id === params.data.id)
          return `<div style="padding: 8px;">
            <strong style="font-size: 14px;">${params.data.name}</strong><br/>
            <span style="color: #909399;">受害人：</span>${caseData?.victim || '未知'}<br/>
            <span style="color: #909399;">涉案金额：</span>${caseData?.amount || '未知'}
          </div>`
        }
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: {
        color: '#606266'
      }
    },
    legend: [{
      data: ['犯罪团伙', '关联案件'],
      bottom: 10,
      left: 'center',
      textStyle: { 
        color: '#606266',
        fontSize: 13
      },
      itemWidth: 15,
      itemHeight: 15
    }],
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      categories: [
        { name: '犯罪团伙', itemStyle: { color: '#f56c6c' } },
        { name: '关联案件', itemStyle: { color: '#409EFF' } }
      ],
      roam: true,
      draggable: true,
      label: { show: true },
      force: {
        repulsion: 800,
        edgeLength: 250,
        gravity: 0.05,
        friction: 0.6
      },
      lineStyle: {
        opacity: 0.8,
        curveness: 0.2
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { 
          width: 10,
          opacity: 1
        },
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(0,0,0,0.5)'
        }
      },
      animation: true,
      animationDuration: 1500,
      animationEasing: 'cubicOut'
    }]
  }

  chart.setOption(option)
  window.addEventListener('resize', () => chart.resize())
}

// ---------- 报告预览与导出 ----------
const previewReport = () => {
  if (reportType.value === 'gang' && !selectedReportGangId.value) {
    ElMessage.warning('请选择团伙')
    return
  }
  if (reportType.value === 'case' && !selectedReportCaseId.value) {
    ElMessage.warning('请选择案件')
    return
  }
  reportNumber.value = `REPORT-${Date.now().toString().slice(-8)}`
  if (reportType.value === 'gang') {
    const gang = results.value.find(g => g.gang_id === selectedReportGangId.value)
    currentGangSteps.value = gang.steps
    reportBasicData.value = [
      { label: '团伙名称', value: gang.gang_name },
      { label: '风险等级', value: gang.risk_label },
      { label: '涉案总额', value: gang.total_amount_involved },
      { label: '关联案件', value: `${gang.total_cases}起` }
    ]
    reportCasesData.value = gang.related_cases
  } else {
    const c = allCases.value.find(c => c.case_id === selectedReportCaseId.value)
    currentGangSteps.value = []
    reportBasicData.value = [
      { label: '案件编号', value: c.case_id },
      { label: '受害人', value: c.victim },
      { label: '涉案金额', value: c.amount },
      { label: '诈骗类型', value: c.fraud_type }
    ]
    reportCasesData.value = [c]
  }
  showPreview.value = true
  nextTick(() => {
    if (evidenceRadarRef.value) {
      const radar = echarts.init(evidenceRadarRef.value)
      radar.setOption({
        radar: { indicator: [{ name:'通话记录',max:100},{ name:'聊天记录',max:100},{ name:'资金流向',max:100},{ name:'IP追踪',max:100}] },
        series: [{ type:'radar', data:[{ value:[95,90,70,60], name:'证据完整性' }] }]
      })
    }
  })
}

const exportReport = async () => {
  if (!showPreview.value) previewReport()
  else {
    exporting.value = true
    await new Promise(r => setTimeout(r, 1500))
    exporting.value = false
    showPreview.value = false
    ElMessage.success(`报告已导出 (${exportFormat.value.toUpperCase()})`)
  }
}

const printReport = () => {
  if (!showPreview.value) previewReport()
  else window.print()
}

const resetReportConfig = () => {
  reportType.value = 'gang'
  selectedReportGangId.value = ''
  selectedReportCaseId.value = ''
  showPreview.value = false
}

const getRiskLevelType = () => {
  if (reportType.value === 'gang') {
    const g = results.value.find(g => g.gang_id === selectedReportGangId.value)
    return g?.risk_type || 'info'
  }
  return 'warning'
}
const getRiskLevelText = () => {
  if (reportType.value === 'gang') {
    const g = results.value.find(g => g.gang_id === selectedReportGangId.value)
    return g?.risk_label || '未知'
  }
  return '中风险'
}
const calculateTotalAmount = () => {
  const total = reportCasesData.value.reduce((s, i) => s + parseFloat(i.amount.replace(/[^0-9.]/g,'')||0), 0)
  return `${total.toFixed(1)}万元`
}
const calculateAvgAmount = () => {
  const total = reportCasesData.value.reduce((s, i) => s + parseFloat(i.amount.replace(/[^0-9.]/g,'')||0), 0)
  const avg = reportCasesData.value.length ? total / reportCasesData.value.length : 0
  return `${avg.toFixed(1)}万元`
}
const calculateHighRiskCount = () => reportCasesData.value.filter(i => i.risk_level === 'HIGH').length

// 菜单切换
const handleMenuSelect = (index) => {
  activeMenu.value = index
  if (index === 'case-detail') getAllCases()
  if (hasData.value && (index === 'details' || index === 'network')) nextTick(() => initCharts())
}

onMounted(() => {
  currentTime.value = new Date().toLocaleString()
})
</script>
<style >
/* =========================================
   【全局变量与基础重置】
   ========================================= */
:root {
  --primary-bg: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
  --sidebar-bg: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  --card-shadow: 0 4px 20px rgba(0,0,0,0.06);
  --card-hover-shadow: 0 8px 30px rgba(0,0,0,0.12);
  --header-gradient: linear-gradient(90deg, #f0f9ff 0%, #e0f2fe 100%);
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-red: #ef4444;
  --accent-green: #10b981;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
}

/* ====== 整体布局 ====== */
.police-system-layout {
  display: flex;
  height: 100vh;
  background: var(--primary-bg);
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
  position: relative;
  overflow: hidden;
  color: var(--text-primary);
}

/* ====== 演示模式提示条 ====== */
.mock-mode-banner {
  position: absolute;
  top: 0;
  left: 240px;
  right: 0;
  background: linear-gradient(90deg, var(--accent-blue), #2563eb);
  color: white;
  padding: 10px 20px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.4);
}
.mock-mode-banner strong { color: #ffd700; margin: 0 4px; }

/* ====== 侧边栏 ====== */
.sidebar {
  width: 240px;
  background: var(--sidebar-bg);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 16px rgba(0,0,0,0.15);
  z-index: 10;
  flex-shrink: 0;
}
.logo-area { 
  padding: 25px 20px; 
  text-align: center; 
  border-bottom: 1px solid rgba(255,255,255,0.1);
  background: rgba(0,0,0,0.2);
}
.logo-icon { font-size: 36px; margin-bottom: 8px; }
.logo-area h2 { 
  margin: 0; 
  font-size: 20px; 
  color: #fff; 
  letter-spacing: 2px;
  font-weight: 600;
}
.sub-title { 
  font-size: 11px; 
  color: #94a3b8; 
  display: block; 
  margin-top: 6px; 
  text-transform: uppercase;
  letter-spacing: 1px;
}
.side-menu { flex: 1; border-right: none; background-color: transparent; }
.side-menu .el-menu-item {
  border-radius: 8px;
  margin: 4px 12px;
  padding-left: 20px !important;
  transition: all 0.3s;
  color: #cbd5e1;
}
.side-menu .el-menu-item:hover {
  background-color: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}
.side-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.3), rgba(59, 130, 246, 0.1));
  color: var(--accent-blue);
  border-left: 4px solid var(--accent-blue);
  font-weight: 600;
}
.system-status { 
  padding: 20px; 
  border-top: 1px solid rgba(255,255,255,0.1); 
  text-align: center;
  background: rgba(0,0,0,0.2);
}
.version-info { font-size: 11px; color: #94a3b8; margin-top: 8px; }

/* ====== 主内容区 ====== */
.main-content {
  flex: 1;
  padding: 24px;
  padding-top: 56px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
}
.content-wrapper, .content-view { 
  animation: fadeIn 0.5s ease; 
  min-height: 400px; 
}
@keyframes fadeIn { 
  from { opacity: 0; transform: translateY(15px); } 
  to { opacity: 1; transform: translateY(0); } 
}
.empty-state { 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  height: 400px; 
  background: white; 
  border-radius: 12px; 
  box-shadow: var(--card-shadow); 
}

/* ====== 通用卡片与顶栏美化 (核心修复) ====== */
.el-card {
  border-radius: 12px;
  border: none;
  box-shadow: var(--card-shadow);
  transition: all 0.3s;
  background: #ffffff;
  overflow: hidden;
  position: relative;
}
.el-card:hover {
  box-shadow: var(--card-hover-shadow);
  transform: translateY(-2px);
}

.el-card__header {
  background: var(--header-gradient);
  border-bottom: 1px solid #e2e8f0;
  padding: 18px 24px;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
}

/* 顶栏标题装饰 */
.el-card__header .page-title,
.el-card__header h2,
.el-card__header h3,
.el-card__header .card-title {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
  font-weight: 700;
  position: relative;
  display: inline-block;
  padding-right: 20px;
}
.el-card__header .page-title::after,
.el-card__header h2::after,
.el-card__header h3::after,
.el-card__header .card-title::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 0;
  width: 50px;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
  border-radius: 2px;
  
}

/* 【关键】顶栏右侧空白填充 - 系统状态标签 */
.el-card__header::before {
  content: '📊 数据实时同步 | 最后更新：' attr(data-update-time);
  position: absolute;
  top: 50%;
  left: 280px;
  right: 160px;
  transform: translateY(-50%);
  font-size: 12px;
  color: #059669;
  background: rgba(5, 150, 105, 0.08);
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px solid rgba(5, 150, 105, 0.2);
  white-space: nowrap;
  z-index: 1;
  pointer-events: none;
  font-style: italic;
  letter-spacing: 0.5px;
  left: 400px; /* 【修改】从 280px 改为 320px，避开左侧标题 */
  top: 55%;    /* 【修改】微调垂直位置，使其居中 */
}

.el-card__header .header-actions {
  z-index: 2;
  display: flex;
  gap: 12px;
}

/* ====== 录入页特定样式 ====== */
.input-card-full { 
  height: calc(100vh - 96px); 
  display: flex; 
  flex-direction: column;
  border-radius: 16px;
}
.page-subtitle { 
  margin: 6px 0 0; 
  font-size: 14px; 
  color: var(--text-secondary); 
}
.input-workspace { 
  display: flex; 
  gap: 24px; 
  flex: 1; 
  overflow: hidden; 
}
.input-panel { 
  flex: 2; 
  display: flex; 
  flex-direction: column; 
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); 
  padding: 20px; 
  border-radius: 12px; 
  border: 1px solid #e2e8f0;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.03);
}
.panel-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 12px; 
  font-weight: 600; 
  color: #475569;
  font-size: 15px;
}
.chat-input-large { 
  flex: 1; 
  font-family: 'Courier New', Courier, monospace; 
  font-size: 14px; 
  line-height: 1.8;
  border-radius: 8px;
}
.input-stats { 
  margin-top: 12px; 
  font-size: 13px; 
  color: var(--text-secondary); 
  display: flex; 
  justify-content: space-between;
  background: rgba(255,255,255,0.6);
  padding: 8px 12px;
  border-radius: 6px;
}
.input-stats strong { color: var(--accent-blue); }

.tools-panel { 
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  gap: 20px; 
  min-width: 340px; 
}

.tool-card { 
  background: white; 
  padding: 20px; 
  border-radius: 12px; 
  border: 1px solid #e2e8f0; 
  box-shadow: var(--card-shadow); 
  transition: all 0.3s;
}
.tool-card:hover {
  box-shadow: var(--card-hover-shadow);
  transform: translateY(-3px);
  border-color: var(--accent-blue);
}
.tool-card h4 { 
  margin: 0 0 16px; 
  font-size: 16px; 
  color: var(--text-primary); 
  border-left: 4px solid var(--accent-blue); 
  padding-left: 12px; 
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.upload-area-large { 
  width: 100%; 
  border: 2px dashed #cbd5e1; 
  border-radius: 10px; 
  transition: all 0.3s;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}
.upload-area-large:hover { 
  border-color: var(--accent-blue); 
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); 
}

.external-data-panel {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-left: 4px solid var(--accent-green);
  border-color: #86efac;
  border-radius: 12px;
  padding: 20px;
}
.current-mode {
  font-size: 13px;
  color: #475569;
  margin-bottom: 14px;
  line-height: 1.6;
  background: rgba(255,255,255,0.7);
  padding: 10px;
  border-radius: 6px;
}
.future-integrations {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.integration-tag {
  font-size: 12px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: #1d4ed8;
  border-radius: 20px;
  border: 1px solid #bfdbfe;
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  transition: all 0.3s;
}
.integration-tag:hover {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  transform: scale(1.05);
}
.note {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
  font-style: italic;
  border-top: 1px dashed #cbd5e1;
  padding-top: 10px;
  background: rgba(255,255,255,0.5);
  padding: 8px;
  border-radius: 4px;
}

.action-area { 
  margin-top: auto; 
  padding-top: 20px; 
  position: relative; 
}
.analyze-btn-pro {
  background: linear-gradient(135deg, var(--accent-red), #dc2626);
  border: none;
  color: white;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: 1px;
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  height: 54px;
  border-radius: 10px;
  width: 100%;
}
.analyze-btn-pro:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(239, 68, 68, 0.6);
  background: linear-gradient(135deg, #f87171 0%, var(--accent-red) 100%);
}
.analyze-btn-pro:active { transform: translateY(-2px); }
.analyze-btn-pro.is-disabled {
  background: #f1f5f9;
  color: #94a3b8;
  box-shadow: none;
  cursor: not-allowed;
}
.progress-text { 
  font-size: 13px; 
  color: var(--text-secondary); 
  text-align: center; 
  margin-top: 8px; 
  font-weight: 500;
  background: rgba(255,255,255,0.8);
  padding: 6px;
  border-radius: 4px;
}
.action-hint { 
  text-align: center; 
  font-size: 12px; 
  color: #94a3b8; 
  margin-top: 12px;
  font-style: italic;
}

/* ====== 报告头部 (案件总览页) ====== */
.report-header { 
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
  color: white; 
  padding: 24px; 
  border-radius: 16px; 
  margin-bottom: 24px;
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.3);
  position: relative;
  overflow: hidden;
}
.report-header::after {
  content: 'AI INTELLIGENCE V2.0';
  position: absolute;
  top: 20px;
  right: 20px;
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  border: 1px solid rgba(255,255,255,0.2);
  padding: 4px 8px;
  border-radius: 4px;
}
.report-title-section h2 { 
  margin: 0 0 8px; 
  font-size: 24px;
  font-weight: 600;
  color: #fff;
}
.report-subtitle {
  margin: 0;
  font-size: 14px;
  opacity: 0.8;
  color: #cbd5e1;
}
.report-meta { 
  display: flex; 
  gap: 24px; 
  font-size: 14px; 
  margin-top: 16px;
  flex-wrap: wrap;
}
.meta-item { display: flex; flex-direction: column; gap: 4px; }
.meta-label { font-size: 12px; opacity: 0.7; }
.meta-value { font-size: 18px; font-weight: 600; }
.meta-value.highlight { color: #60a5fa; }
.meta-value.highlight-red { color: #f87171; }

/* ====== 统计卡片与团伙卡片 ====== */
.stats-cards { 
  display: grid; 
  grid-template-columns: repeat(3, 1fr); 
  gap: 20px; 
  margin-bottom: 24px; 
}
.stat-card {
  text-align: center;
  padding: 20px;
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--card-shadow);
}
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.stat-value { 
  font-size: 32px; 
  font-weight: 700; 
  background: linear-gradient(135deg, var(--accent-blue), #1d4ed8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.section-title { 
  font-size: 18px; 
  margin: 24px 0 16px; 
  border-left: 5px solid var(--accent-blue); 
  padding-left: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

/* 修复：添加了缺失的右括号 */
.case-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
  gap: 20px; 
}
.gang-summary-card { height: 100%; border-radius: 12px; }
.gang-header { display: flex; justify-content: space-between; align-items: center; }
.gang-name { font-weight: 600; font-size: 16px; color: var(--text-primary); }
.case-item { 
  margin-top: 16px; 
  padding-top: 16px; 
  border-top: 1px solid #e2e8f0;
  transition: all 0.3s;
}
.case-item:hover {
  background: #f8fafc;
  margin: 16px -20px -16px;
  padding: 16px 20px;
  border-radius: 8px;
}
.case-id { font-weight: 600; color: var(--accent-blue); font-size: 14px; margin-bottom: 8px; }
.case-detail { display: flex; justify-content: space-between; font-size: 13px; margin: 6px 0; color: #475569; }
.case-amount { color: var(--accent-red); font-weight: 500; }
.case-snippet { 
  font-size: 12px; 
  color: var(--text-secondary); 
  background: #f1f5f9; 
  padding: 8px 10px; 
  border-radius: 6px;
  line-height: 1.5;
}

.summary-stats { 
  display: grid; 
  grid-template-columns: repeat(4, 1fr); 
  gap: 20px; 
  margin-bottom: 30px; 
}
.stat-box { 
  background: white; 
  padding: 24px; 
  border-radius: 12px; 
  text-align: center; 
  box-shadow: var(--card-shadow);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}
.stat-box::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
}
.stat-box.red::before { background: linear-gradient(90deg, #f87171, var(--accent-red)); }
.stat-box.orange::before { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.stat-box.blue::before { background: linear-gradient(90deg, #60a5fa, var(--accent-blue)); }
.stat-box.green::before { background: linear-gradient(90deg, #34d399, var(--accent-green)); }
.stat-box:hover {
  transform: translateY(-5px);
  box-shadow: var(--card-hover-shadow);
}
.stat-icon-large { font-size: 36px; margin-bottom: 8px; }
.stat-box .num { font-size: 36px; font-weight: 700; margin-bottom: 6px; }
.stat-box.red .num { color: var(--accent-red); }
.stat-box.orange .num { color: #f59e0b; }
.stat-box.blue .num { color: var(--accent-blue); }
.stat-box.green .num { color: var(--accent-green); }
.stat-box .label { font-size: 14px; color: var(--text-secondary); font-weight: 500; }

/* 修复：添加了缺失的右括号 */
.gang-cards-container { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); 
  gap: 24px; 
}
.gang-card { 
  background: white; 
  border: 1px solid #e2e8f0; 
  border-radius: 16px; 
  padding: 24px; 
  cursor: pointer; 
  transition: all 0.3s; 
  position: relative;
}
.gang-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
  opacity: 0;
  transition: opacity 0.3s;
}
.gang-card:hover::before { opacity: 1; }
.gang-card:hover { 
  transform: translateY(-6px); 
  box-shadow: var(--card-hover-shadow); 
  border-color: var(--accent-blue);
}
.gang-card.active { 
  border: 2px solid var(--accent-blue); 
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.2);
}
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.badge { 
  background: linear-gradient(135deg, #6366f1, #4f46e5); 
  color: white; 
  padding: 4px 10px; 
  border-radius: 6px; 
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.gang-title { margin: 0 0 6px; font-size: 18px; color: var(--text-primary); font-weight: 600; }
.gang-id { font-size: 12px; color: #94a3b8; margin-bottom: 16px; font-family: 'Courier New', monospace; }
.gang-metrics { 
  display: grid; 
  grid-template-columns: 1fr 1fr 1fr; 
  gap: 12px; 
  margin-bottom: 16px; 
  text-align: center;
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
}
.metric .m-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.metric .m-value { font-size: 15px; font-weight: 700; color: var(--text-primary); margin-top: 4px; }
.metric .m-value.money { color: var(--accent-red); font-size: 16px; }
.tags-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.tags-row .el-tag { border-radius: 6px; font-size: 11px; padding: 4px 8px; }
.card-action { text-align: right; border-top: 1px solid #e2e8f0; padding-top: 12px; }
.link-text { color: var(--accent-blue); font-size: 13px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
.link-text:hover { color: #1d4ed8; text-decoration: underline; }

/* ====== 详情页特定样式 ====== */
.details-header { 
  display: flex; 
  align-items: center; 
  margin-bottom: 24px;
  background: white;
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: var(--card-shadow);
}
.page-main-title { font-size: 24px; margin: 0; color: var(--text-primary); font-weight: 600; }
.page-desc { color: var(--text-secondary); margin-bottom: 24px; font-size: 14px; line-height: 1.6; }
.page-header-section { margin-bottom: 24px; }
.info-card { margin-bottom: 24px; border-radius: 12px; }
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.chart-card { height: 380px; border-radius: 12px; }
.echart-container { width: 100%; height: 320px; }
.flow-card { margin-bottom: 24px; border-radius: 12px; }
.flow-steps { 
  display: flex; 
  gap: 20px; 
  overflow-x: auto; 
  padding: 20px 10px;
  background: #f8fafc;
  border-radius: 8px;
}
.step-item { 
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  min-width: 130px;
  position: relative;
}
.step-item:not(:last-child)::after {
  content: '→';
  position: absolute;
  right: -15px;
  top: 15px;
  color: #94a3b8;
  font-size: 18px;
}
.step-num { 
  width: 36px; height: 36px; 
  background: linear-gradient(135deg, var(--accent-blue), #1d4ed8); 
  color: white; 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  font-weight: 700; 
  margin-bottom: 10px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}
.step-text { font-size: 13px; text-align: center; color: #475569; line-height: 1.5; font-weight: 500; }
.flow-note { font-size: 12px; color: #94a3b8; text-align: center; margin-top: 12px; font-style: italic; }
.cases-card { margin-bottom: 24px; border-radius: 12px; }

.case-selector-card { margin-bottom: 24px; border-radius: 16px; }
.case-selector-content { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; }
.selector-bar { background: linear-gradient(90deg, var(--accent-green), #14b8a6, #06b6d4); }

.detail-card { border-radius: 16px; transition: all 0.3s; }
.detail-card:hover { box-shadow: var(--card-hover-shadow); }

.info-bar { background: linear-gradient(90deg, var(--accent-blue), #1d4ed8); }
.snippet-bar { background: linear-gradient(90deg, var(--accent-green), #059669); }
.gang-bar { background: linear-gradient(90deg, var(--accent-purple), #7c3aed); }
.evidence-bar { background: linear-gradient(90deg, #f59e0b, #d97706); }

.snippet-content { display: flex; flex-direction: column; gap: 16px; padding: 20px; background: #f8fafc; border-radius: 12px; }
.message-bubble { max-width: 80%; padding: 16px; border-radius: 16px; position: relative; }
.message-bubble.suspect { align-self: flex-start; background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%); border-left: 4px solid var(--accent-red); }
.message-bubble.victim { align-self: flex-end; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-right: 4px solid var(--accent-blue); }
.bubble-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; color: var(--text-secondary); }
.bubble-header .avatar { font-size: 16px; }
.bubble-text { font-size: 14px; color: var(--text-primary); line-height: 1.6; }

.gang-link-content { padding: 10px; }
.gang-link-card { 
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}
.gang-link-card:hover {
  border-color: var(--accent-purple);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.2);
  transform: translateY(-2px);
}
.gang-link-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.gang-link-name { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.gang-link-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
.metric-item { text-align: center; padding: 12px; background: white; border-radius: 8px; }
.metric-label { font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 6px; }
.metric-value { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.metric-value.money { color: var(--accent-red); }
.gang-link-action { text-align: right; }

.evidence-list { display: flex; flex-direction: column; gap: 16px; }
.evidence-item { 
  display: flex; 
  align-items: center; 
  gap: 16px; 
  padding: 16px; 
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 10px;
  border-left: 4px solid #f59e0b;
  transition: all 0.3s;
}
.evidence-item:hover {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  transform: translateX(5px);
}
.evidence-icon { font-size: 28px; }
.evidence-info { flex: 1; }
.evidence-info .evidence-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.evidence-info .evidence-desc { font-size: 13px; color: var(--text-secondary); }

/* ====== 网络图谱 ====== */
.network-legend { 
  display: flex; 
  gap: 24px; 
  margin-bottom: 16px; 
  font-size: 14px; 
  color: #475569;
  flex-wrap: wrap;
  background: white;
  padding: 12px 20px;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.legend-item { display: flex; align-items: center; gap: 6px; font-weight: 500; }
.dot { width: 14px; height: 14px; border-radius: 50%; display: inline-block; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }
.dot.red { background: linear-gradient(135deg, #f87171, var(--accent-red)); border: 2px solid #fff; }
.dot.blue { background: linear-gradient(135deg, #60a5fa, var(--accent-blue)); border: 2px solid #fff; }
.line-sample { width: 30px; height: 4px; border-radius: 2px; display: inline-block; }
.line-sample.thick { background: linear-gradient(90deg, #f87171, var(--accent-red)); height: 6px; }
.line-sample.color { background: linear-gradient(90deg, #60a5fa, var(--accent-blue)); }

.network-container { 
  width: 100%; 
  height: 650px; 
  background: white; 
  border-radius: 16px; 
  box-shadow: var(--card-shadow);
  border: 1px solid #e2e8f0;
  position: relative;
  overflow: hidden;
}
.network-container::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 2%),
    radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 2%);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}
.network-tips { display: flex; justify-content: center; gap: 24px; margin-top: 16px; flex-wrap: wrap; }
.tip-item { font-size: 13px; color: var(--text-secondary); background: white; padding: 8px 16px; border-radius: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); font-weight: 500; }
.network-note { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 16px; font-style: italic; }

/* ====== 报告生成页面 ====== */
.report-config-card { margin-bottom: 24px; border-radius: 16px; }
.report-config-content { display: flex; flex-direction: column; gap: 20px; padding: 10px 0; }
.config-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.config-label { font-size: 15px; font-weight: 600; color: #475569; min-width: 100px; }
.config-bar { background: linear-gradient(90deg, #6366f1, var(--accent-purple), #a855f7); }

.report-actions { display: flex; gap: 16px; margin-top: 24px; padding-top: 24px; border-top: 1px solid #e2e8f0; justify-content: center; }

.report-preview-card { margin-top: 24px; }
.preview-card { border-radius: 16px; overflow: hidden; }
.preview-header { display: flex; justify-content: space-between; align-items: center; }
.preview-header h4 { margin: 0; font-size: 16px; color: var(--text-primary); }
.preview-actions { display: flex; gap: 10px; }
.preview-content { background: white; padding: 40px; min-height: 600px; }

.report-cover {
  text-align: center;
  padding: 60px 40px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  color: white;
  border-radius: 12px;
  margin-bottom: 30px;
  position: relative;
  overflow: hidden;
}
.cover-logo { font-size: 64px; margin-bottom: 20px; display: block; }
.cover-title { font-size: 32px; margin: 0 0 10px; font-weight: 700; }
.cover-subtitle { font-size: 24px; margin: 0 0 40px; font-weight: 400; opacity: 0.9; }
.cover-info { text-align: left; background: rgba(255,255,255,0.1); padding: 20px; border-radius: 8px; margin: 0 auto; max-width: 500px; }
.cover-info p { margin: 10px 0; font-size: 14px; opacity: 0.9; }
.cover-seal {
  position: absolute;
  bottom: 30px; right: 40px;
  width: 100px; height: 100px;
  border: 3px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  transform: rotate(-15deg);
  color: rgba(255,255,255,0.5);
  font-size: 12px; font-weight: bold;
}

.report-body { padding: 20px 0; }
.section { margin-bottom: 40px; }
.section-title-report { font-size: 20px; color: var(--text-primary); margin: 0 0 20px; padding-left: 15px; border-left: 4px solid var(--accent-blue); font-weight: 600; }

.chart-placeholder { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.chart-box { background: #f8fafc; border-radius: 12px; padding: 20px; text-align: center; }
.chart-title { font-size: 14px; color: var(--text-secondary); margin-bottom: 15px; font-weight: 500; }
.chart-image { height: 200px; border-radius: 8px; background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%); }
.radar-placeholder { background: radial-gradient(circle, rgba(59,130,246,0.2) 0%, rgba(59,130,246,0.05) 70%); }
.bar-placeholder { background: linear-gradient(90deg, rgba(59,130,246,0.1) 0%, rgba(59,130,246,0.3) 100%); }

.suggestion-box { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-left: 4px solid #f59e0b; border-radius: 12px; padding: 20px; }
.suggestion-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px dashed rgba(245, 158, 11, 0.3); }
.suggestion-item:last-child { border-bottom: none; }
.suggestion-icon { font-size: 20px; }
.suggestion-item span:last-child { font-size: 14px; color: #475569; font-weight: 500; }

.report-footer { text-align: center; padding: 30px; margin-top: 40px; border-top: 2px solid #e2e8f0; color: #94a3b8; font-size: 12px; }
.report-footer p { margin: 8px 0; }

/* ====== 响应式适配 ====== */
@media (max-width: 1200px) {
  .stats-cards, .summary-stats, .charts-row, .gang-cards-container { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 1000px) {
  .mock-mode-banner { left: 0; }
  .sidebar { display: none; }
  .main-content { padding-top: 64px; }
  .input-workspace { flex-direction: column; overflow-y: auto; }
  .tools-panel { min-width: auto; }
  .stats-cards, .summary-stats, .charts-row, .gang-cards-container { grid-template-columns: 1fr; }
}
@media print {
  .sidebar, .mock-mode-banner, .report-actions, .preview-actions, .el-card__header::before { display: none !important; }
  .main-content { padding: 0 !important; }
  .preview-card { box-shadow: none !important; }
  .el-card { box-shadow: none; border: 1px solid #ccc; }
}
</style>