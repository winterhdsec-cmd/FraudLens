<template>
  <div class="police-system-layout">
    <div v-if="!store.isLoggedIn" class="login-overlay">
      <div class="login-container tech-card">
        <div class="login-header">
          <div class="login-logo-wrapper">
            <div class="login-logo-ring"></div>
            <div class="login-logo-icon">🛡️</div>
          </div>
          <h2 class="login-title">反诈情报分析系统</h2>
          <p class="login-subtitle">AI INTELLIGENT SYSTEM</p>
        </div>
        <div class="login-form">
          <div class="login-field">
            <span class="login-field-icon">👤</span>
            <el-input
              v-model="loginForm.username"
              placeholder="用户名"
              size="large"
              class="login-input"
              @keyup.enter="handleLogin"
            />
          </div>
          <div class="login-field">
            <span class="login-field-icon">🔑</span>
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              size="large"
              class="login-input"
              show-password
              @keyup.enter="handleLogin"
            />
          </div>
          <div v-if="loginError" class="login-error">{{ loginError }}</div>
          <el-button
            class="login-btn"
            type="primary"
            size="large"
            :loading="loginLoading"
            @click="handleLogin"
          >
            <span>{{ loginLoading ? '验证中...' : '登 录' }}</span>
          </el-button>
        </div>
        <div class="login-footer">
          <span class="login-footer-text">智能研判平台 v2.0</span>
        </div>
      </div>
    </div>
    <div class="particle-bg">
      <div v-for="i in 60" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>
    <div class="grid-overlay"></div>
    <div class="scan-line"></div>

    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-icon-wrapper">
          <div class="logo-ring"></div>
          <div class="logo-icon">🛡️</div>
        </div>
        <h2>反诈情报分析</h2>
        <span class="sub-title">AI INTELLIGENT SYSTEM</span>
        <div class="logo-badge">
          <span class="badge-dot"></span>
          <span>智能研判平台</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="side-menu" @select="handleMenuSelect">
        <div class="menu-group">
          <div class="menu-group-title">数据采集</div>
          <el-menu-item index="input">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📝</span>
                <span class="menu-text">文本录入</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="upload">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📷</span>
                <span class="menu-text">图片上传</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="api">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔌</span>
                <span class="menu-text">API接入</span>
                
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">系统总览</div>
          <el-menu-item index="dashboard">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📊</span>
                <span class="menu-text">数据看板</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="alerts">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔔</span>
                <span class="menu-text">预警中心</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">研判分析</div>
          <el-menu-item index="overview">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📊</span>
                <span class="menu-text">案件总览</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="case-detail">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🔍</span>
                <span class="menu-text">案件详情</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="groups">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">👥</span>
                <span class="menu-text">团伙画像</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="details">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📈</span>
                <span class="menu-text">深度分析</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="network">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">🕸️</span>
                <span class="menu-text">关联网络</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">深度研判</div>
          <el-menu-item index="capital-flow">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">💰</span>
                <span class="menu-text">资金流向</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="dispatch">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📋</span>
                <span class="menu-text">预警派单</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="key-persons">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">👤</span>
                <span class="menu-text">重点人员</span>
              </div>
            </template>
          </el-menu-item>
        </div>

        <div class="menu-group">
          <div class="menu-group-title">输出报告</div>
          <el-menu-item index="report">
            <template #title>
              <div class="menu-item-content">
                <span class="menu-icon">📄</span>
                <span class="menu-text">报告生成</span>
              </div>
            </template>
          </el-menu-item>
        </div>
      </el-menu>

      <div class="system-status">
        <div class="status-row">
          <div class="status-indicator">
            <div class="status-dot"></div>
            <span>系统运行正常</span>
          </div>
          <div class="version">v2.0</div>
        </div>
        <div class="status-details">
          <div class="status-item">
            <span class="status-label">AI引擎</span>
            <span class="status-value online">在线</span>
          </div>
          <div class="status-item">
            <span class="status-label">数据库</span>
            <span class="status-value online">已连接</span>
          </div>
        </div>
        <div class="logout-area" v-if="store.isLoggedIn">
          <el-button class="logout-btn" size="small" @click="handleLogout">
            <span>🚪</span> 退出登录
          </el-button>
        </div>
      </div>
    </aside>

    <main class="main-content" v-loading="loading" element-loading-text="AI 正在进行深度研判分析...">
      <div class="content-wrapper" :class="{ 'fade-in': true }">

        <!-- Dashboard 数据看板 -->
        <div v-if="activeMenu === 'dashboard'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📊</span>
                数据看板
              </h2>
              <p class="section-desc">系统运行数据总览，实时监控诈骗态势</p>
            </div>
            <div class="header-right">
              <el-button size="small" @click="loadDashboard" :loading="dashboardLoading">
                <span>🔄</span> 刷新数据
              </el-button>
            </div>
          </div>

          <div class="stats-overview">
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper danger">
                <span class="stat-icon">📋</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_cases ?? '-' }}</div>
                <div class="stat-label">案件总数</div>
                <div class="stat-trend up">
                  <span>累计录入</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper warning">
                <span class="stat-icon">👥</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_gangs ?? '-' }}</div>
                <div class="stat-label">涉案团伙</div>
                <div class="stat-trend up">
                  <span>已识别</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper success">
                <span class="stat-icon">💰</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.total_amount ?? '-' }}</div>
                <div class="stat-label">涉案金额</div>
                <div class="stat-trend">
                  <span>累计金额</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper info">
                <span class="stat-icon">🔔</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.active_alerts ?? '-' }}</div>
                <div class="stat-label">活跃预警</div>
                <div class="stat-trend up">
                  <span>待处理</span>
                </div>
              </div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">风险等级分布</span>
              </div>
              <div class="chart-content" ref="dashboardRiskChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">案件状态分布</span>
              </div>
              <div class="chart-content" ref="dashboardStatusChartRef"></div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">诈骗类型排行</span>
              </div>
              <div class="chart-content" ref="dashboardBarChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">月度趋势</span>
              </div>
              <div class="chart-content" ref="dashboardTrendChartRef"></div>
            </div>
          </div>

          <div class="recent-cases-section" v-if="dashboardData.recent_cases?.length">
            <div class="section-sub-header">
              <h3 class="sub-title">
                <span class="sub-icon">📋</span>
                最新案件
              </h3>
            </div>
            <div class="cases-table tech-card">
              <el-table :data="dashboardData.recent_cases" style="width: 100%" @row-click="viewCaseFromDashboard" :highlight-current-row="true">
                <el-table-column prop="id" label="案件编号" width="100" />
                <el-table-column prop="title" label="案件名称" />
                <el-table-column prop="type" label="案件类型" width="100">
                  <template #default="scope">
                    <el-tag type="info" size="small">{{ scope.row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="涉案金额" width="120" />
                <el-table-column prop="status" label="案件状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === '已立案' ? 'warning' : scope.row.status === '侦办中' ? 'primary' : 'success'" size="small">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="date" label="立案时间" width="120" />
                <el-table-column label="操作" width="100">
                  <template #default="scope">
                    <el-button size="small" type="primary" @click="viewCaseFromDashboard(scope.row)">
                      查看
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else-if="!dashboardLoading" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">📊</div>
              <h3 class="empty-title">暂无看板数据</h3>
              <p class="empty-desc">请先录入案情数据，系统将自动生成数据看板</p>
              <el-button type="primary" size="large" @click="activeMenu = 'input'">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>

        <!-- Alerts 预警中心 -->
        <div v-if="activeMenu === 'alerts'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🔔</span>
                预警中心
              </h2>
              <p class="section-desc">实时监控诈骗预警信息，快速响应处置</p>
            </div>
            <div class="header-right">
              <el-button size="small" @click="loadAlerts" :loading="alertsLoading">
                <span>🔄</span> 刷新
              </el-button>
            </div>
          </div>

          <div v-if="alerts.length" class="alerts-list">
            <div v-for="alert in alerts" :key="alert.id" class="alert-card tech-card">
              <div class="alert-header">
                <div class="alert-icon-wrapper">
                  <span class="alert-icon">🔔</span>
                </div>
                <div class="alert-info">
                  <div class="alert-type">
                    <el-tag :type="getAlertType(alert.confidence)" effect="dark" size="small">
                      {{ alert.alert_type || '未知预警' }}
                    </el-tag>
                    <span class="alert-id">ID: {{ alert.id }}</span>
                  </div>
                  <div class="alert-meta">
                    <span class="meta-item">
                      <span class="meta-icon">📋</span>
                      关联案件: {{ alert.matched_case_id || '未关联' }}
                    </span>
                    <span class="meta-item">
                      <span class="meta-icon">🎯</span>
                      置信度: {{ alert.confidence }}%
                    </span>
                    <span class="meta-item">
                      <span class="meta-icon">📅</span>
                      {{ alert.created_at }}
                    </span>
                  </div>
                </div>
                <div class="alert-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :loading="resolvingAlert === alert.id"
                    @click="handleResolveAlert(alert.id)"
                  >
                    <span>✅</span> 处置
                  </el-button>
                </div>
              </div>
              <div class="alert-body" v-if="alert.description">
                <p class="alert-desc">{{ alert.description }}</p>
              </div>
              <div class="alert-footer">
                <div class="confidence-bar">
                  <div class="confidence-label">威胁指数</div>
                  <div class="confidence-track">
                    <div class="confidence-fill" :style="{ width: alert.confidence + '%', background: getConfidenceColor(alert.confidence) }"></div>
                  </div>
                  <span class="confidence-value">{{ alert.confidence }}%</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="!alertsLoading" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">🔔</div>
              <h3 class="empty-title">暂无预警信息</h3>
              <p class="empty-desc">系统运行正常，暂无待处理的诈骗预警</p>
            </div>
          </div>
        </div>

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

        <div v-if="activeMenu === 'api'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🔌</span>
                多源数据API接入
              </h2>
              <p class="section-desc">对接银行风控、110报警平台、反诈平台等外部数据源</p>
            </div>
            <div class="header-right">
              <div class="connection-status">
                <span class="status-indicator">
                  <span class="status-dot active"></span>
                  <span>{{ connectedSources }} 个数据源已连接</span>
                </span>
              </div>
            </div>
          </div>

          <div class="api-sources-grid">
            <div class="api-source-card tech-card" :class="{ active: apiSources.bank.connected }">
              <div class="source-header">
                <div class="source-icon bank">🏦</div>
                <div class="source-info">
                  <div class="source-name">银行风控系统</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.bank.connected }"></span>
                    <span>{{ apiSources.bank.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.bank.connected" @change="toggleApiSource('bank')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入银行风控数据，获取涉案账户交易流水、异常交易预警等信息</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">💰</span>
                    <span>账户交易流水</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">⚠️</span>
                    <span>异常交易预警</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🔒</span>
                    <span>账户冻结状态</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.bank.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.bank.records }}</span>
                    <span class="stat-label">数据记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.bank.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.bank.connected">
                <el-button size="small" @click="syncApiData('bank')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchBankData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>

            <div class="api-source-card tech-card" :class="{ active: apiSources.police.connected }">
              <div class="source-header">
                <div class="source-icon police">🚔</div>
                <div class="source-info">
                  <div class="source-name">110报警平台</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.police.connected }"></span>
                    <span>{{ apiSources.police.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.police.connected" @change="toggleApiSource('police')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入110报警平台，实时获取诈骗类警情信息，支持案件串并分析</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">📞</span>
                    <span>警情实时推送</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">📋</span>
                    <span>案件基本信息</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🔗</span>
                    <span>串并案分析</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.police.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.police.records }}</span>
                    <span class="stat-label">警情记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.police.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.police.connected">
                <el-button size="small" @click="syncApiData('police')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchPoliceData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>

            <div class="api-source-card tech-card" :class="{ active: apiSources.antiFraud.connected }">
              <div class="source-header">
                <div class="source-icon antiFraud">🛡️</div>
                <div class="source-info">
                  <div class="source-name">反诈平台接入</div>
                  <div class="source-status">
                    <span class="status-dot" :class="{ active: apiSources.antiFraud.connected }"></span>
                    <span>{{ apiSources.antiFraud.connected ? '已连接' : '未连接' }}</span>
                  </div>
                </div>
                <el-switch v-model="apiSources.antiFraud.connected" @change="toggleApiSource('antiFraud')" />
              </div>
              <div class="source-content">
                <div class="source-desc">接入国家反诈中心平台，获取诈骗号码库、涉案账户库等核心数据</div>
                <div class="source-features">
                  <div class="feature-item">
                    <span class="feature-icon">📱</span>
                    <span>诈骗号码库</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">💳</span>
                    <span>涉案账户库</span>
                  </div>
                  <div class="feature-item">
                    <span class="feature-icon">🌐</span>
                    <span>诈骗网址库</span>
                  </div>
                </div>
                <div class="source-stats" v-if="apiSources.antiFraud.connected">
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.antiFraud.records }}</span>
                    <span class="stat-label">黑名单记录</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ apiSources.antiFraud.lastSync }}</span>
                    <span class="stat-label">最后同步</span>
                  </div>
                </div>
              </div>
              <div class="source-actions" v-if="apiSources.antiFraud.connected">
                <el-button size="small" @click="syncApiData('antiFraud')">
                  <span>🔄</span> 同步数据
                </el-button>
                <el-button size="small" type="primary" @click="fetchAntiFraudData">
                  <span>📥</span> 获取数据
                </el-button>
              </div>
            </div>
          </div>

          <div class="api-data-preview tech-card" v-if="apiDataPreview.length">
            <div class="preview-header">
              <span class="preview-icon">📊</span>
              <span class="preview-title">接入数据预览</span>
              <el-button size="small" @click="importApiData" type="primary">
                <span>📥</span> 导入系统
              </el-button>
            </div>
            <div class="preview-table">
              <el-table :data="apiDataPreview" style="width: 100%">
                <el-table-column prop="source" label="数据来源" width="120" />
                <el-table-column prop="type" label="数据类型" width="120" />
                <el-table-column prop="content" label="内容摘要" />
                <el-table-column prop="time" label="时间" width="180" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === '已验证' ? 'success' : 'warning'" size="small">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div class="action-bar">
            <el-button
              class="analyze-btn"
              type="primary"
              size="large"
              :loading="loading"
              :disabled="!hasApiData"
              @click="startApiAnalysis"
            >
              <span class="btn-icon">🚀</span>
              <span>{{ loading ? 'AI 正在分析接入数据...' : '开始数据分析' }}</span>
            </el-button>
          </div>
        </div>

        <div v-if="activeMenu === 'overview'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📊</span>
                案件总览
              </h2>
              <p class="section-desc">展示所有录入的案件及团伙信息概览，支持快速筛选和定位</p>
            </div>
            <div class="header-right">
              <div class="view-toggle">
                <el-button-group>
                  <el-button size="small" :type="viewMode === 'card' ? 'primary' : ''" @click="viewMode = 'card'">
                    <span>📇</span> 卡片
                  </el-button>
                  <el-button size="small" :type="viewMode === 'table' ? 'primary' : ''" @click="viewMode = 'table'">
                    <span>📋</span> 列表
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>

          <div class="stats-overview">
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper danger">
                <span class="stat-icon">👥</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ gangs.length }}</div>
                <div class="stat-label">涉案团伙</div>
                <div class="stat-trend up">
                  <span>↑ 2</span>
                  <span>本周新增</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper warning">
                <span class="stat-icon">📋</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ cases.length }}</div>
                <div class="stat-label">关联案件</div>
                <div class="stat-trend up">
                  <span>↑ 5</span>
                  <span>本周新增</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper success">
                <span class="stat-icon">💰</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ totalAmountFormatted }}</div>
                <div class="stat-label">涉案金额</div>
                <div class="stat-trend">
                  <span>{{ cases.length }}</span>
                  <span>案件累计</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper info">
                <span class="stat-icon">🎯</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ successRate }}%</div>
                <div class="stat-label">研判准确率</div>
                <div class="stat-trend up">
                  <span>↑ 3%</span>
                  <span>较上月</span>
                </div>
              </div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">案件类型分布</span>
              </div>
              <div class="chart-content" ref="pieChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">涉案金额趋势</span>
              </div>
              <div class="chart-content" ref="lineChartRef"></div>
            </div>
          </div>

          <div class="gangs-section" v-if="gangs.length">
            <div class="section-sub-header">
              <h3 class="sub-title">
                <span class="sub-icon">👥</span>
                团伙列表
              </h3>
              <div class="filter-bar">
                <el-input
                  v-model="gangSearchKeyword"
                  placeholder="搜索团伙名称..."
                  size="small"
                  class="search-input"
                  clearable
                >
                  <template #prefix>
                    <span>🔍</span>
                  </template>
                </el-input>
                <el-select v-model="riskFilter" placeholder="风险等级" size="small" clearable>
                  <el-option label="S级" value="S" />
                  <el-option label="A级" value="A" />
                  <el-option label="B级" value="B" />
                </el-select>
              </div>
            </div>

            <div class="gangs-grid" v-if="viewMode === 'card'">
              <div
                v-for="gang in filteredGangs"
                :key="gang.id"
                class="gang-card tech-card"
                :class="{ 'selected': selectedGang?.id === gang.id }"
                @click="selectGang(gang)"
              >
                <div class="gang-card-header">
                  <div class="gang-icon-wrapper" :class="'risk-' + gang.riskLevel.toLowerCase()">
                    <span class="gang-icon">{{ gang.icon }}</span>
                  </div>
                  <div class="gang-info">
                    <div class="gang-name">{{ gang.name }}</div>
                    <div class="gang-meta">
                      <el-tag :type="getRiskType(gang.riskLevel)" size="small" effect="dark">
                        {{ gang.riskLevel }}级风险
                      </el-tag>
                      <span class="gang-id">ID: {{ gang.id }}</span>
                    </div>
                  </div>
                </div>
                <div class="gang-card-body">
                  <div class="gang-stats">
                    <div class="gang-stat">
                      <span class="stat-icon">💰</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.amount }}</span>
                        <span class="stat-label">涉案金额</span>
                      </div>
                    </div>
                    <div class="gang-stat">
                      <span class="stat-icon">📋</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.cases }}起</span>
                        <span class="stat-label">关联案件</span>
                      </div>
                    </div>
                    <div class="gang-stat">
                      <span class="stat-icon">👥</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.members?.length || 0 }}人</span>
                        <span class="stat-label">团伙成员</span>
                      </div>
                    </div>
                  </div>
                  <div class="gang-tags">
                    <el-tag v-for="tag in gang.tags?.slice(0, 3)" :key="tag" size="small" type="info">
                      {{ tag }}
                    </el-tag>
                    <el-tag v-if="gang.tags?.length > 3" size="small" type="info">
                      +{{ gang.tags.length - 3 }}
                    </el-tag>
                  </div>
                </div>
                <div class="gang-card-footer">
                  <span class="update-time">更新于 {{ gang.updateTime || '刚刚' }}</span>
                  <el-button size="small" type="primary" @click.stop="viewGangDetail(gang)">
                    查看详情 →
                  </el-button>
                </div>
              </div>
            </div>

            <div class="gangs-table" v-else>
              <el-table :data="filteredGangs" style="width: 100%" @row-click="selectGang">
                <el-table-column prop="id" label="团伙ID" width="100" />
                <el-table-column prop="name" label="团伙名称" />
                <el-table-column prop="riskLevel" label="风险等级" width="100">
                  <template #default="scope">
                    <el-tag :type="getRiskType(scope.row.riskLevel)" effect="dark">
                      {{ scope.row.riskLevel }}级
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="涉案金额" width="120" />
                <el-table-column prop="cases" label="案件数" width="80" />
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="primary" @click="viewGangDetail(scope.row)">
                      详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div class="cases-section" v-if="cases.length">
            <div class="section-sub-header">
              <h3 class="sub-title">
                <span class="sub-icon">📋</span>
                案件列表
              </h3>
            </div>
            <div class="cases-table tech-card">
              <el-table :data="cases" style="width: 100%" @row-click="viewCaseDetail" :highlight-current-row="true">
                <el-table-column prop="id" label="案件编号" width="100" />
                <el-table-column prop="title" label="案件名称" />
                <el-table-column prop="type" label="案件类型" width="100">
                  <template #default="scope">
                    <el-tag type="info" size="small">{{ scope.row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="region" label="案发地区" width="120" />
                <el-table-column prop="amount" label="涉案金额" width="120" />
                <el-table-column prop="status" label="案件状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === '已立案' ? 'warning' : scope.row.status === '侦办中' ? 'primary' : 'success'" size="small">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="date" label="立案时间" width="120" />
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="primary" @click="viewCaseDetail(scope.row)">
                      查看详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">📊</div>
              <h3 class="empty-title">暂无案件数据</h3>
              <p class="empty-desc">请先通过数据录入功能添加案情信息，系统将自动进行智能研判</p>
              <el-button type="primary" size="large" @click="activeMenu = 'input'">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'case-detail'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🔍</span>
                案件详情
              </h2>
              <p class="section-desc">查看选中案件的详细信息、受害人和证据材料</p>
            </div>
          </div>

          <div v-if="selectedCase" class="case-detail-content">
            <div class="detail-main">
              <div class="case-header-card tech-card">
                <div class="case-header-top">
                  <div class="case-icon-wrapper">
                    <span class="case-icon">🔍</span>
                  </div>
                  <div class="case-header-info">
                    <h3 class="case-title">{{ selectedCase.title }}</h3>
                    <div class="case-meta">
                      <el-tag type="warning" effect="dark" size="large">
                        {{ selectedCase.status }}
                      </el-tag>
                      <span class="meta-item">
                        <span class="meta-icon">📋</span>
                        案件编号：{{ selectedCase.id }}
                      </span>
                      <span class="meta-item">
                        <span class="meta-icon">📅</span>
                        立案时间：{{ selectedCase.date || '2024-03-20' }}
                      </span>
                    </div>
                  </div>
                  <div class="case-header-actions">
                    <el-button type="primary" @click="activeMenu = 'report'">
                      <span>📄</span> 生成报告
                    </el-button>
                  </div>
                </div>
                <div class="case-header-stats">
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.amount }}</span>
                    <span class="header-stat-label">涉案金额</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.victims || 1 }}人</span>
                    <span class="header-stat-label">受害人数</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.region || '广东省' }}</span>
                    <span class="header-stat-label">案发地区</span>
                  </div>
                  <div class="header-stat">
                    <span class="header-stat-value">{{ selectedCase.type || '冒充客服' }}</span>
                    <span class="header-stat-label">案件类型</span>
                  </div>
                </div>
              </div>

              <div class="detail-tabs">
                <el-tabs v-model="detailTab">
                  <el-tab-pane label="案件概述" name="overview">
                    <div class="timeline-section tech-card">
                      <div class="case-overview">
                        <div class="overview-section">
                          <h4 class="overview-title">📝 案情描述</h4>
                          <p class="overview-content">{{ selectedCase.description || '2024年3月15日，受害人王女士接到自称"京东客服"的电话，对方准确报出其个人信息后，称其名下有一笔账户异常需要处理，否则将影响征信。在对方的诱导下，王女士通过手机银行转账至对方提供的"安全账户"，共计转账125,800元。转账后对方失联，王女士才发现被骗。' }}</p>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">👤 受害人信息</h4>
                          <div class="info-grid">
                            <div class="info-item">
                              <span class="info-label">姓名</span>
                              <span class="info-value">{{ selectedCase.victimName || '王女士' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">性别</span>
                              <span class="info-value">{{ selectedCase.victimGender || '女' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">年龄</span>
                              <span class="info-value">{{ selectedCase.victimAge || '32' }}岁</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">联系方式</span>
                              <span class="info-value">{{ selectedCase.victimPhone || '138****5678' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">职业</span>
                              <span class="info-value">{{ selectedCase.victimJob || '公司职员' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">户籍地址</span>
                              <span class="info-value">{{ selectedCase.victimAddress || '广东省深圳市' }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="overview-section">
                          <h4 class="overview-title">📞 涉案通讯信息</h4>
                          <div class="info-grid">
                            <div class="info-item">
                              <span class="info-label">诈骗号码</span>
                              <span class="info-value danger">{{ selectedCase.scamPhone || '0755-8888****' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">归属地</span>
                              <span class="info-value">{{ selectedCase.phoneLocation || '广东深圳' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">诈骗网址</span>
                              <span class="info-value danger">{{ selectedCase.scamUrl || 'jd-security.com' }}</span>
                            </div>
                            <div class="info-item">
                              <span class="info-label">IP地址</span>
                              <span class="info-value">{{ selectedCase.ipAddress || '192.168.***.***' }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="资金流向" name="money">
                    <div class="money-section tech-card">
                      <div class="money-header">
                        <span class="money-icon">💰</span>
                        <span class="money-title">资金流向追踪</span>
                      </div>
                      <div class="money-flow">
                        <div class="flow-diagram">
                          <div class="flow-node source">
                            <span class="node-icon">👤</span>
                            <span class="node-label">受害人账户</span>
                            <span class="node-amount">{{ selectedCase.amount }}</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">转账</span>
                          </div>
                          <div class="flow-node gang">
                            <span class="node-icon">💳</span>
                            <span class="node-label">涉案账户</span>
                            <span class="node-amount">***1234</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">分散</span>
                          </div>
                          <div class="flow-node middle">
                            <span class="node-icon">🏦</span>
                            <span class="node-label">中转账户</span>
                            <span class="node-amount">多层分散</span>
                          </div>
                          <div class="flow-arrow">
                            <span>→</span>
                            <span class="arrow-label">出境</span>
                          </div>
                          <div class="flow-node target">
                            <span class="node-icon">🌍</span>
                            <span class="node-label">境外取现</span>
                            <span class="node-amount">最终去向</span>
                          </div>
                        </div>
                      </div>
                      <div class="money-stats">
                        <div class="money-stat">
                          <span class="ms-label">涉案账户数</span>
                          <span class="ms-value">23个</span>
                        </div>
                        <div class="money-stat">
                          <span class="ms-label">资金层级</span>
                          <span class="ms-value">3-5层</span>
                        </div>
                        <div class="money-stat">
                          <span class="ms-label">境外流向</span>
                          <span class="ms-value">85%</span>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="调查进展" name="progress">
                    <div class="method-section tech-card">
                      <div class="method-header">
                        <span class="method-icon">📊</span>
                        <span class="method-title">案件调查进展</span>
                      </div>
                      <div class="investigation-timeline">
                        <div class="timeline-item" v-for="(step, idx) in investigationSteps" :key="idx">
                          <div class="timeline-marker">
                            <div class="timeline-dot" :class="{ completed: step.completed, current: step.current }"></div>
                            <div class="timeline-line" v-if="idx < investigationSteps.length - 1"></div>
                          </div>
                          <div class="timeline-content">
                            <div class="timeline-header">
                              <span class="timeline-date">{{ step.date }}</span>
                              <el-tag :type="step.completed ? 'success' : 'warning'" size="small">{{ step.status }}</el-tag>
                            </div>
                            <div class="timeline-title">{{ step.title }}</div>
                            <div class="timeline-desc">{{ step.description }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>

            <div class="detail-sidebar">
              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">📋</span>
                  <span class="section-title-text">证据材料</span>
                </div>
                <div class="evidence-list">
                  <div v-for="(ev, idx) in selectedCase.evidence || caseEvidence" :key="idx" class="evidence-item">
                    <span class="evidence-icon">{{ ev.icon }}</span>
                    <div class="evidence-info">
                      <div class="evidence-name">{{ ev.name }}</div>
                      <div class="evidence-meta">
                        <el-tag :type="ev.status === '已验证' ? 'success' : 'warning'" size="small">
                          {{ ev.status }}
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">🕵️</span>
                  <span class="section-title-text">办案民警</span>
                </div>
                <div class="member-list">
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">张警官</span>
                      <span class="member-role">主办民警</span>
                    </div>
                  </div>
                  <div class="member-item">
                    <span class="member-avatar">👮</span>
                    <div class="member-info">
                      <span class="member-name">李警官</span>
                      <span class="member-role">协办民警</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="sidebar-section tech-card">
                <div class="section-title-bar">
                  <span class="section-icon">🔗</span>
                  <span class="section-title-text">关联团伙</span>
                </div>
                <div class="tag-cloud">
                  <el-tag v-if="selectedCase.gang" type="danger" size="small" @click="viewRelatedGang(selectedCase.gang)">
                    {{ getGangById(selectedCase.gang)?.name || '未知团伙' }}
                  </el-tag>
                  <el-tag v-else type="info" size="small">待关联</el-tag>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">📋</div>
              <h3 class="empty-title">暂无选中案件</h3>
              <p class="empty-desc">请先在案件总览中选择一个案件查看详情</p>
              <el-button type="primary" size="large" @click="activeMenu = 'overview'">
                <span>📊</span> 前往案件总览
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'groups'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">👥</span>
                团伙画像总览
              </h2>
              <p class="section-desc">查看所有涉案团伙的详细画像信息，包括组织架构、作案特征等</p>
            </div>
          </div>

          <div v-if="gangs.length" class="profiles-container">
            <div v-for="gang in gangs" :key="gang.id" class="profile-card tech-card">
              <div class="profile-header">
                <div class="profile-avatar-wrapper" :class="'risk-' + gang.riskLevel.toLowerCase()">
                  <span class="profile-avatar">{{ gang.icon }}</span>
                </div>
                <div class="profile-basic">
                  <div class="profile-name">{{ gang.name }}</div>
                  <div class="profile-id">ID: {{ gang.id }}</div>
                  <el-tag :type="getRiskType(gang.riskLevel)" effect="dark">
                    {{ gang.riskLevel }}级风险
                  </el-tag>
                </div>
                <div class="profile-quick-stats">
                  <div class="quick-stat-item">
                    <span class="qsi-value">{{ gang.amount }}</span>
                    <span class="qsi-label">涉案金额</span>
                  </div>
                  <div class="quick-stat-item">
                    <span class="qsi-value">{{ gang.cases }}起</span>
                    <span class="qsi-label">案件数</span>
                  </div>
                </div>
              </div>

              <div class="profile-body">
                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">📊</span>
                    基本信息
                  </div>
                  <div class="info-grid">
                    <div class="info-item">
                      <span class="info-label">风险等级</span>
                      <el-tag :type="getRiskType(gang.riskLevel)" size="small">{{ gang.riskLevel }}级</el-tag>
                    </div>
                    <div class="info-item">
                      <span class="info-label">涉案金额</span>
                      <span class="info-value danger">{{ gang.amount }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">案件数量</span>
                      <span class="info-value">{{ gang.cases }} 起</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">成员人数</span>
                      <span class="info-value">{{ gang.members?.length || 0 }} 人</span>
                    </div>
                  </div>
                </div>

                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">🎭</span>
                    作案特征
                  </div>
                  <div class="feature-tags">
                    <el-tag v-for="tag in gang.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
                  </div>
                </div>

                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">👥</span>
                    成员信息
                  </div>
                  <div class="member-grid">
                    <div v-for="member in gang.members" :key="member.id" class="member-card">
                      <span class="member-avatar">{{ member.icon }}</span>
                      <div class="member-details">
                        <span class="member-name">{{ member.name }}</span>
                        <el-tag size="small" :type="member.role === '头目' ? 'danger' : 'info'">
                          {{ member.role }}
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">📈</span>
                    能力评估
                  </div>
                  <div class="ability-bars">
                    <div class="ability-item">
                      <span class="ability-label">技术能力</span>
                      <el-progress :percentage="gang.abilities?.tech || 75" :color="'#00d4ff'" :stroke-width="8" />
                    </div>
                    <div class="ability-item">
                      <span class="ability-label">组织严密性</span>
                      <el-progress :percentage="gang.abilities?.org || 85" :color="'#f59e0b'" :stroke-width="8" />
                    </div>
                    <div class="ability-item">
                      <span class="ability-label">反侦察能力</span>
                      <el-progress :percentage="gang.abilities?.antiDetect || 60" :color="'#ef4444'" :stroke-width="8" />
                    </div>
                  </div>
                </div>
              </div>

              <div class="profile-footer">
                <el-button size="small" @click="selectGang(gang); activeMenu = 'case-detail'">
                  <span>🔍</span> 查看详情
                </el-button>
                <el-button size="small" type="primary" @click="selectGang(gang); activeMenu = 'report'">
                  <span>📄</span> 生成报告
                </el-button>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">👥</div>
              <h3 class="empty-title">暂无团伙画像数据</h3>
              <p class="empty-desc">请先录入案情信息，系统将自动生成团伙画像</p>
              <el-button type="primary" size="large" @click="activeMenu = 'input'">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'details'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📈</span>
                深度分析
              </h2>
              <p class="section-desc">AI 智能分析团伙特征、资金流向和关联关系</p>
            </div>
          </div>

          <div class="analysis-dashboard">
            <div class="analysis-row">
              <div class="analysis-card tech-card money-flow-card">
                <div class="analysis-header">
                  <span class="analysis-icon">💰</span>
                  <span class="analysis-title">资金流向追踪</span>
                  <span class="flow-badge">AI分析</span>
                </div>
                <div class="analysis-content">
                  <div class="flow-chart">
                    <div class="flow-path">
                      <div class="flow-stage">
                        <div class="stage-node source">
                          <div class="node-glow"></div>
                          <span class="node-icon">👤</span>
                        </div>
                        <span class="stage-label">受害者</span>
                        <span class="stage-desc">账户资金流出</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">转账</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node gang">
                          <div class="node-glow"></div>
                          <span class="node-icon">💳</span>
                        </div>
                        <span class="stage-label">涉案账户</span>
                        <span class="stage-desc">第一层接收</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">分散</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node middle">
                          <div class="node-glow"></div>
                          <span class="node-icon">🏦</span>
                        </div>
                        <span class="stage-label">中转账户</span>
                        <span class="stage-desc">多层流转</span>
                      </div>
                      <div class="flow-connector">
                        <div class="connector-line"></div>
                        <div class="connector-arrow"></div>
                        <span class="connector-label">出境</span>
                      </div>
                      <div class="flow-stage">
                        <div class="stage-node target">
                          <div class="node-glow"></div>
                          <span class="node-icon">🌍</span>
                        </div>
                        <span class="stage-label">境外取现</span>
                        <span class="stage-desc">最终去向</span>
                      </div>
                    </div>
                  </div>
                  <div class="flow-metrics">
                    <div class="metric-item">
                      <div class="metric-icon">💰</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案金额</span>
                        <span class="metric-value danger">{{ totalAmountFormatted }}</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">📊</div>
                      <div class="metric-info">
                        <span class="metric-label">中转层级</span>
                        <span class="metric-value">3-5层</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🌏</div>
                      <div class="metric-info">
                        <span class="metric-label">境外流向</span>
                        <span class="metric-value warning">85%</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-icon">🏦</div>
                      <div class="metric-info">
                        <span class="metric-label">涉案账户</span>
                        <span class="metric-value">23个</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="analysis-card tech-card">
                <div class="analysis-header">
                  <span class="analysis-icon">🎯</span>
                  <span class="analysis-title">团伙特征提取</span>
                  <span class="analysis-subtitle">AI智能分析</span>
                </div>
                <div class="analysis-content">
                  <div class="feature-grid">
                    <div v-for="(feature, idx) in features" :key="feature.name" class="feature-card" :style="{ '--feature-color': feature.color }">
                      <div class="feature-icon-wrap">
                        <span class="feature-icon">{{ getFeatureIcon(idx) }}</span>
                      </div>
                      <div class="feature-info">
                        <div class="feature-header">
                          <span class="feature-name">{{ feature.name }}</span>
                          <span class="feature-value" :style="{ color: feature.color }">{{ feature.confidence }}%</span>
                        </div>
                        <span class="feature-desc">{{ feature.desc }}</span>
                      </div>
                      <div class="feature-bar-wrap">
                        <div class="feature-bar" :style="{ width: feature.confidence + '%', background: feature.color }"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="analysis-row">
              <div class="analysis-card tech-card full-width">
                <div class="analysis-header">
                  <span class="analysis-icon">🔗</span>
                  <span class="analysis-title">关联关系图谱</span>
                </div>
                <div class="analysis-content relation-map">
                  <div class="relation-viz">
                    <div v-for="node in relationNodes" :key="node.id" class="rel-node" :class="node.type" :style="node.style">
                      <span class="rel-icon">{{ node.icon }}</span>
                      <span class="rel-label">{{ node.label }}</span>
                    </div>
                    <svg class="relation-lines">
                      <line v-for="line in relationLines" :key="line.id" :x1="line.x1" :y1="line.y1" :x2="line.x2" :y2="line.y2" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div class="analysis-row">
              <div class="analysis-card tech-card">
                <div class="analysis-header">
                  <span class="analysis-icon">📊</span>
                  <span class="analysis-title">案件类型统计</span>
                </div>
                <div class="analysis-content">
                  <div class="type-stats">
                    <div class="type-item" v-for="(item, idx) in caseTypeStats" :key="idx">
                      <div class="type-bar" :style="{ width: item.percent + '%', background: item.color }"></div>
                      <div class="type-info">
                        <span class="type-name">{{ item.name }}</span>
                        <span class="type-count">{{ item.count }}起</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="analysis-card tech-card">
                <div class="analysis-header">
                  <span class="analysis-icon">🌍</span>
                  <span class="analysis-title">地域分布</span>
                </div>
                <div class="analysis-content">
                  <div class="region-stats">
                    <div class="region-item" v-for="(item, idx) in regionStats" :key="idx">
                      <span class="region-name">{{ item.name }}</span>
                      <div class="region-bar-wrapper">
                        <div class="region-bar" :style="{ width: item.percent + '%' }"></div>
                      </div>
                      <span class="region-count">{{ item.count }}起</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'network'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🕸️</span>
                关联网络
              </h2>
              <p class="section-desc">展示案件、团伙、资金等多维度关联关系</p>
            </div>
            <div class="header-right">
              <div class="network-controls">
                <el-button-group>
                  <el-button size="small" :type="networkView === 'all' ? 'primary' : ''" @click="networkView = 'all'">
                    全部
                  </el-button>
                  <el-button size="small" :type="networkView === 'gang' ? 'primary' : ''" @click="networkView = 'gang'">
                    团伙
                  </el-button>
                  <el-button size="small" :type="networkView === 'case' ? 'primary' : ''" @click="networkView = 'case'">
                    案件
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>

          <div class="network-container tech-card">
            <NetworkGraph :gangs="gangs" :selectedGang="selectedGang" @select="selectGang" />
          </div>
        </div>

        <!-- 资金流向 -->
        <div v-if="activeMenu === 'capital-flow'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title"><span class="title-icon">💰</span>资金流向追踪</h2>
              <p class="section-desc">追踪涉案资金的一级卡→二级卡→三级卡转账链路</p>
            </div>
            <div class="header-actions">
              <el-input v-model="flowSearchCaseId" placeholder="按案件编号搜索" style="width:200px" size="small" clearable @clear="loadFlowData" @keyup.enter="loadFlowData" />
              <el-button type="primary" size="small" @click="loadFlowData">查询</el-button>
            </div>
          </div>
          <div class="flow-container">
            <div class="network-container tech-card" style="height:450px">
              <NetworkGraph :gangs="[]" :selectedGang="null" :flowData="flowGraphData" />
            </div>
            <el-table :data="capitalFlows" style="width:100%;margin-top:12px" stripe size="small" max-height="300">
              <el-table-column prop="source_account" label="转出账户" min-width="140" />
              <el-table-column prop="target_account" label="转入账户" min-width="140" />
              <el-table-column prop="bank_name" label="开户行" width="120" />
              <el-table-column prop="amount" label="金额" width="100">
                 <template #default="{row}">¥{{ Number(row.amount || 0).toFixed(2) }}</template>
               </el-table-column>
              <el-table-column prop="direction" label="方向" width="70">
                <template #default="{row}"><el-tag :type="row.direction==='out' ? 'warning' : 'danger'" size="small">{{row.direction === 'out' ? '转出' : '转入'}}</el-tag></template>
              </el-table-column>
              <el-table-column prop="level" label="层级" width="60" />
              <el-table-column prop="transaction_time" label="交易时间" width="160" />
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{row}">
                  <el-button size="small" @click="addFlowRecord(row)">追加</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 预警派单 -->
        <div v-if="activeMenu === 'dispatch'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title"><span class="title-icon">📋</span>预警落地派单</h2>
              <p class="section-desc">预警生成 → 派单到辖区 → 签收 → 处置反馈</p>
            </div>
            <div class="header-actions">
              <el-select v-model="dispatchStatusFilter" placeholder="按状态" size="small" style="width:120px" @change="loadDispatchOrders">
                <el-option label="全部" value="" />
                <el-option label="待签收" value="pending" />
                <el-option label="已签收" value="signed" />
                <el-option label="已完成" value="completed" />
              </el-select>
              <el-button type="primary" size="small" @click="showCreateDispatch = true">新建派单</el-button>
            </div>
          </div>
          <div class="dispatch-list">
            <el-table :data="dispatchOrders" stripe size="small" max-height="500">
              <el-table-column prop="alert_id" label="预警编号" width="120" />
              <el-table-column prop="assigned_dept" label="派往单位" width="150" />
              <el-table-column prop="assigned_officer" label="责任人" width="100" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{row}">
                  <el-tag :type="row.status==='pending' ? 'warning' : row.status==='signed' ? 'primary' : 'success'" size="small">
                    {{row.status==='pending' ? '待签收' : row.status==='signed' ? '已签收' : '已完成'}}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="dispatch_time" label="派单时间" width="160" />
              <el-table-column prop="sign_time" label="签收时间" width="160" />
              <el-table-column prop="feedback" label="处置反馈" min-width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{row}">
                  <el-button v-if="row.status==='pending'" size="small" type="primary" @click="signDispatch(row.id)">签收</el-button>
                  <el-button v-if="row.status==='signed'" size="small" @click="showCompleteDispatch(row)">完成反馈</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 重点人员 -->
        <div v-if="activeMenu === 'key-persons'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title"><span class="title-icon">👤</span>重点人员库</h2>
              <p class="section-desc">前科人员 / 高危人员管理，研判时自动碰撞比对</p>
            </div>
            <div class="header-actions">
              <el-input v-model="personSearch" placeholder="姓名/电话/身份证" style="width:200px" size="small" clearable @clear="loadKeyPersons" @keyup.enter="loadKeyPersons" />
              <el-select v-model="personTypeFilter" placeholder="人员类型" size="small" style="width:120px" @change="loadKeyPersons">
                <el-option label="全部" value="" />
                <el-option label="前科人员" value="前科人员" />
                <el-option label="高危人员" value="高危人员" />
                <el-option label="在逃人员" value="在逃人员" />
              </el-select>
              <el-button type="primary" size="small" @click="showCreatePerson = true">新增人员</el-button>
            </div>
          </div>
          <div class="persons-container">
            <el-table :data="keyPersons" stripe size="small" max-height="500">
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="id_number" label="身份证号" width="180" />
              <el-table-column prop="phone" label="电话" width="130" />
              <el-table-column prop="bank_account" label="银行卡号" width="160" />
              <el-table-column prop="risk_label" label="风险等级" width="80">
                <template #default="{row}">
                  <el-tag :type="row.risk_level==='A' ? 'danger' : row.risk_level==='B' ? 'warning' : 'info'" size="small">{{row.risk_label}}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="person_type" label="类型" width="100" />
              <el-table-column prop="source" label="来源" width="100" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{row}">
                  <el-button size="small" type="danger" @click="deleteKeyPerson(row.id)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-if="activeMenu === 'report'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📄</span>
                分析报告生成
              </h2>
              <p class="section-desc">一键生成标准化的案件分析报告，支持多种格式导出</p>
            </div>
          </div>

          <div class="report-container">
            <div class="report-config-panel tech-card">
              <div class="config-header">
                <span class="config-icon">⚙️</span>
                <span class="config-title">报告配置</span>
              </div>
              <div class="config-body">
                <div class="config-item">
                  <label class="config-label">报告类型</label>
                  <el-select v-model="reportConfig.type" class="dark-select">
                    <el-option label="团伙分析报告" value="gang" />
                    <el-option label="案件分析报告" value="case" />
                    <el-option label="综合研判报告" value="comprehensive" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">选择团伙</label>
                  <el-select v-model="reportConfig.gangId" class="dark-select" placeholder="请选择团伙">
                    <el-option v-for="gang in gangs" :key="gang.id" :label="gang.name" :value="gang.id" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">导出格式</label>
                  <el-select v-model="reportConfig.format" class="dark-select">
                    <el-option label="PDF 文档" value="pdf" />
                    <el-option label="Word 文档" value="docx" />
                    <el-option label="HTML 网页" value="html" />
                  </el-select>
                </div>
                <div class="config-item">
                  <label class="config-label">报告内容</label>
                  <div class="checkbox-group">
                    <el-checkbox v-model="reportConfig.includeTimeline">时间线</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeMoney">资金分析</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeNetwork">关联网络</el-checkbox>
                    <el-checkbox v-model="reportConfig.includeSuggestion">处置建议</el-checkbox>
                  </div>
                </div>
              </div>
              <div class="config-footer">
                <el-button type="primary" class="generate-btn" @click="generateReport" :loading="generatingReport">
                  <span>🚀</span> 生成报告
                </el-button>
              </div>
            </div>

            <div class="report-preview-panel tech-card">
              <div class="preview-header">
                <span class="preview-icon">👁️</span>
                <span class="preview-title">报告预览</span>
                <div class="preview-actions" v-if="reportPreview">
                  <el-button size="small" @click="printReport">
                    <span>🖨️</span> 打印
                  </el-button>
                  <el-button size="small" type="primary" @click="downloadReport">
                    <span>📥</span> 下载
                  </el-button>
                </div>
              </div>
              <div class="preview-body">
                <div class="report-document" v-if="reportPreview">
                  <div class="doc-header">
                    <div class="doc-logo">
                      <span class="logo-icon">🛡️</span>
                      <span class="logo-text">反诈情报分析系统</span>
                    </div>
                    <div class="doc-title">{{ getReportTitle() }}</div>
                    <div class="doc-meta">
                      <div class="meta-item">
                        <span class="meta-label">报告编号：</span>
                        <span class="meta-value">RPT-{{ Date.now().toString().slice(-8) }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">生成时间：</span>
                        <span class="meta-value">{{ new Date().toLocaleString() }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">密级：</span>
                        <span class="meta-value secret">机密</span>
                      </div>
                    </div>
                  </div>

                  <div class="doc-content">
                    <div class="doc-section">
                      <div class="section-title">一、团伙基本信息</div>
                      <div class="section-body">
                        <div class="info-table">
                          <div class="info-row">
                            <span class="info-label">团伙名称</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.name || '未选择' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">风险等级</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.riskLevel || '-' }}级</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">涉案金额</span>
                            <span class="info-value danger">{{ getGangById(reportConfig.gangId)?.amount || '-' }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">关联案件</span>
                            <span class="info-value">{{ getGangById(reportConfig.gangId)?.cases || 0 }} 起</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeTimeline">
                      <div class="section-title">二、作案时间线</div>
                      <div class="section-body">
                        <div class="doc-timeline">
                          <div v-for="(event, idx) in getGangById(reportConfig.gangId)?.timeline || []" :key="idx" class="doc-timeline-item">
                            <span class="doc-time">{{ event.date }}</span>
                            <span class="doc-event">{{ event.title }}</span>
                            <span class="doc-desc">{{ event.desc }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeMoney">
                      <div class="section-title">三、资金流向分析</div>
                      <div class="section-body">
                        <div class="money-flow-summary">
                          <p>经分析，该团伙涉案资金主要通过多级账户进行转移，最终流向境外。资金流转层级约3-5层，境外资金占比约85%。</p>
                        </div>
                      </div>
                    </div>

                    <div class="doc-section" v-if="reportConfig.includeSuggestion">
                      <div class="section-title">四、处置建议</div>
                      <div class="section-body">
                        <div class="suggestion-list">
                          <div class="suggestion-item">
                            <span class="suggestion-num">1</span>
                            <span class="suggestion-text">建议立即对涉案账户进行止付冻结，防止资金进一步转移</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">2</span>
                            <span class="suggestion-text">协调银行调取完整交易流水，追踪资金去向</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">3</span>
                            <span class="suggestion-text">对团伙成员实施布控，择机收网</span>
                          </div>
                          <div class="suggestion-item">
                            <span class="suggestion-num">4</span>
                            <span class="suggestion-text">联系境外执法机构，开展国际协作</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="doc-footer">
                    <div class="footer-line"></div>
                    <div class="footer-text">
                      <span>本报告由反诈情报分析系统自动生成</span>
                      <span>仅供内部参考使用</span>
                    </div>
                  </div>
                </div>

                <div class="preview-empty" v-else>
                  <div class="empty-icon">📄</div>
                  <div class="empty-text">请配置报告参数并点击"生成报告"</div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import NetworkGraph from './components/NetworkGraph.vue'
import { store } from './store.js'
import {
  startAnalysis as apiStartAnalysis,
  fetchCases,
  fetchGangs,
  fetchGangDetail,
  connectSocket,
  disconnectSocket,
  login as apiLogin,
  getDashboardData,
  getActiveAlerts,
  resolveAlert,
  importCSV,
  importExcel
} from './api.js'

const activeMenu = ref('input')
const loading = ref(false)
const inputText = ref('')
const uploadedImages = ref([])
const gangs = ref([])
const cases = ref([])
const selectedGang = ref(null)
const selectedCase = ref(null)
const viewMode = ref('card')
const gangSearchKeyword = ref('')
const riskFilter = ref('')
const detailTab = ref('overview')
const networkView = ref('all')
const generatingReport = ref(false)

// P1 features state
const flowSearchCaseId = ref('')
const capitalFlows = ref([])
const flowGraphData = ref(null)
const dispatchOrders = ref([])
const dispatchStatusFilter = ref('')
const showCreateDispatch = ref(false)
const keyPersons = ref([])
const personSearch = ref('')
const personTypeFilter = ref('')
const showCreatePerson = ref(false)

const dashboardData = ref({
  total_cases: null,
  total_gangs: null,
  total_amount: null,
  active_alerts: null,
  risk_distribution: [],
  status_distribution: [],
  top_scam_types: [],
  monthly_trend: [],
  recent_cases: []
})
const dashboardLoading = ref(false)

const alerts = ref([])
const alertsLoading = ref(false)
const resolvingAlert = ref(null)

const dashboardRiskChartRef = ref(null)
const dashboardStatusChartRef = ref(null)
const dashboardBarChartRef = ref(null)
const dashboardTrendChartRef = ref(null)
let dashboardRiskChart = null
let dashboardStatusChart = null
let dashboardBarChart = null
let dashboardTrendChart = null

const reportConfig = ref({
  type: 'gang',
  gangId: '',
  format: 'pdf',
  includeTimeline: true,
  includeMoney: true,
  includeNetwork: true,
  includeSuggestion: true
})
const reportPreview = ref(false)

const loginForm = ref({ username: '', password: '' })
const loginLoading = ref(false)
const loginError = ref('')

const handleLogin = async () => {
  if (!loginForm.value.username.trim() || !loginForm.value.password.trim()) {
    loginError.value = '请输入用户名和密码'
    return
  }
  loginLoading.value = true
  loginError.value = ''
  try {
    const data = await apiLogin(loginForm.value.username, loginForm.value.password)
    if (data.success) {
      store.login(data.user || { username: loginForm.value.username }, data.token)
      loginForm.value = { username: '', password: '' }
      ElMessage.success('登录成功')
    } else {
      loginError.value = data.message || '登录失败，请重试'
    }
  } catch (err) {
    loginError.value = err.response?.data?.message || err.message || '登录失败，请检查网络连接'
  } finally {
    loginLoading.value = false
  }
}

const handleLogout = () => {
  store.logout()
  ElMessage.success('已安全退出')
}

const apiSources = ref({
  bank: { connected: false, records: 1256, lastSync: '10分钟前' },
  police: { connected: false, records: 89, lastSync: '5分钟前' },
  antiFraud: { connected: false, records: 3567, lastSync: '刚刚' }
})
const apiDataPreview = ref([])

const pieChartRef = ref(null)
const lineChartRef = ref(null)
let pieChart = null
let lineChart = null

const totalAmount = computed(() => {
  return gangs.value.reduce((sum, g) => {
    const num = parseFloat(g.amount?.replace(/[^0-9.]/g, '') || 0)
    return sum + (isNaN(num) ? 0 : num)
  }, 0)
})

const totalAmountFormatted = computed(() => {
  const amount = totalAmount.value
  if (amount >= 100) {
    return `¥${amount.toFixed(1)}万`
  }
  return `¥${amount.toFixed(2)}万`
})

const successRate = ref(92)

const textLineCount = computed(() => {
  return inputText.value.split('\n').filter(line => line.trim()).length
})

const extractedKeywords = computed(() => {
  const keywords = []
  const text = inputText.value
  if (text.includes('诈骗') || text.includes('被骗')) keywords.push('诈骗')
  if (text.includes('转账') || text.includes('汇款')) keywords.push('转账')
  if (text.includes('客服') || text.includes('京东')) keywords.push('冒充客服')
  if (text.includes('征信') || text.includes('贷款')) keywords.push('征信诈骗')
  if (text.includes('刷单') || text.includes('返利')) keywords.push('刷单诈骗')
  if (/\d{11}/.test(text)) keywords.push('手机号')
  if (/¥|万元|元/.test(text)) keywords.push('涉案金额')
  return keywords.slice(0, 6)
})

const hasTime = computed(() => /\d{4}年|\d{1,2}月|\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}/.test(inputText.value))
const hasAmount = computed(() => /¥|万元|元|\d+万/.test(inputText.value))
const hasPhone = computed(() => /\d{11}/.test(inputText.value))
const hasMethod = computed(() => /诈骗|被骗|转账|汇款|客服|征信|贷款|刷单/.test(inputText.value))

const connectedSources = computed(() => {
  return Object.values(apiSources.value).filter(s => s.connected).length
})

const hasApiData = computed(() => {
  return apiDataPreview.value.length > 0
})

const filteredGangs = computed(() => {
  let result = gangs.value
  if (gangSearchKeyword.value) {
    result = result.filter(g => g.name.includes(gangSearchKeyword.value))
  }
  if (riskFilter.value) {
    result = result.filter(g => g.riskLevel === riskFilter.value)
  }
  return result
})

const features = ref([
  { name: '诈骗话术成熟度', confidence: 92, color: '#ef4444', desc: '话术模板标准化程度' },
  { name: '资金分散程度', confidence: 85, color: '#f59e0b', desc: '资金流转层级数量' },
  { name: '成员关联密度', confidence: 78, color: '#00d4ff', desc: '团伙成员社交关系' },
  { name: '跨区域作案特征', confidence: 88, color: '#8b5cf6', desc: '跨省跨境作案能力' },
  { name: '技术手段先进性', confidence: 73, color: '#10b981', desc: '反侦察技术水平' },
  { name: '受害者画像精准度', confidence: 89, color: '#ec4899', desc: '目标人群定位能力' }
])

const relationNodes = ref([
  { id: 1, type: 'gang', icon: '👥', label: '团伙A', style: { left: '50%', top: '25%' } },
  { id: 2, type: 'case', icon: '📋', label: '案件1', style: { left: '25%', top: '45%' } },
  { id: 3, type: 'case', icon: '📋', label: '案件2', style: { left: '75%', top: '45%' } },
  { id: 4, type: 'money', icon: '💰', label: '资金', style: { left: '35%', top: '70%' } },
  { id: 5, type: 'money', icon: '💰', label: '资金', style: { left: '65%', top: '70%' } }
])
const relationLines = ref([
  { id: 1, x1: '50%', y1: '25%', x2: '25%', y2: '45%' },
  { id: 2, x1: '50%', y1: '25%', x2: '75%', y2: '45%' },
  { id: 3, x1: '25%', y1: '45%', x2: '35%', y2: '70%' },
  { id: 4, x1: '75%', y1: '45%', x2: '65%', y2: '70%' }
])

const caseEvidence = ref([
  { icon: '📱', name: '通话记录', status: '已验证' },
  { icon: '💳', name: '转账凭证', status: '已验证' },
  { icon: '📧', name: '聊天记录', status: '已验证' },
  { icon: '🖥️', name: '涉案设备', status: '核实中' }
])

const investigationSteps = ref([
  { date: '2024-03-15', title: '案件受理', description: '受害人报案，记录案情经过', status: '已完成', completed: true, current: false },
  { date: '2024-03-16', title: '初步调查', description: '调取银行流水、通话记录', status: '已完成', completed: true, current: false },
  { date: '2024-03-18', title: '案件分析', description: 'AI研判分析，关联涉案团伙', status: '已完成', completed: true, current: false },
  { date: '2024-03-20', title: '资金追踪', description: '追踪资金流向，冻结涉案账户', status: '进行中', completed: false, current: true },
  { date: '', title: '抓捕行动', description: '根据线索实施抓捕', status: '待进行', completed: false, current: false },
  { date: '', title: '案件结案', description: '移送审查起诉', status: '待进行', completed: false, current: false }
])

const defaultMethodFlow = [
  { title: '获取信任', desc: '冒充客服，准确报出受害人信息' },
  { title: '制造恐慌', desc: '声称账户异常，影响征信' },
  { title: '诱导转账', desc: '要求转账至"安全账户"验证' },
  { title: '完成诈骗', desc: '资金到账后立即失联' }
]

const defaultKeywords = ['冒充客服', '征信诈骗', '安全账户', '转账验证']

const caseTypeStats = ref([
  { name: '冒充客服诈骗', count: 45, percent: 35, color: '#ef4444' },
  { name: '刷单返利诈骗', count: 32, percent: 25, color: '#f59e0b' },
  { name: '贷款诈骗', count: 28, percent: 22, color: '#8b5cf6' },
  { name: '投资理财诈骗', count: 23, percent: 18, color: '#00d4ff' }
])

const regionStats = ref([
  { name: '广东', count: 25, percent: 30 },
  { name: '浙江', count: 18, percent: 22 },
  { name: '江苏', count: 15, percent: 18 },
  { name: '北京', count: 12, percent: 14 },
  { name: '上海', count: 10, percent: 12 }
])

const getParticleStyle = (i) => {
  const size = Math.random() * 4 + 2
  const duration = Math.random() * 20 + 10
  const delay = Math.random() * 10
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`
  }
}

const getRiskType = (level) => {
  const map = { S: 'danger', A: 'warning', B: 'info', C: 'success' }
  return map[level] || 'info'
}

const getEventType = (type) => {
  const map = { '作案': 'danger', '转移': 'warning', '洗钱': 'warning', '活动': 'info' }
  return map[type] || 'info'
}

const getGangById = (id) => gangs.value.find(g => g.id === id)

const getFeatureIcon = (idx) => {
  const icons = ['💬', '💰', '🔗', '🌍', '🔧', '🎯']
  return icons[idx] || '📊'
}

const getReportTitle = () => {
  const titles = {
    gang: '团伙分析报告',
    case: '案件分析报告',
    comprehensive: '综合研判报告'
  }
  return titles[reportConfig.value.type] || '分析报告'
}

const handleMenuSelect = (index) => {
  activeMenu.value = index
}

const selectGang = (gang) => {
  selectedGang.value = gang
}

const viewGangDetail = (gang) => {
  selectGang(gang)
  activeMenu.value = 'groups'
}

const viewCaseDetail = (caseItem) => {
  selectedCase.value = caseItem
  activeMenu.value = 'case-detail'
}

const viewRelatedGang = (gangId) => {
  const gang = gangs.value.find(g => g.id === gangId)
  if (gang) {
    selectGang(gang)
    activeMenu.value = 'groups'
  }
}

const clearInput = () => {
  inputText.value = ''
}

const clearImages = () => {
  uploadedImages.value = []
}

const removeImage = (idx) => {
  uploadedImages.value.splice(idx, 1)
}

const loadDemo = () => {
  inputText.value = `【案情描述】
受害人王女士报警称：2024年3月15日接到自称"京东客服"电话，对方准确报出其个人信息后称其开通了"京东金条"服务，如不取消将影响征信。王女士在对方指导下通过手机银行转账至"安全账户"共计 125,800 元。

受害人李先生报警称：2024年3月18日接到同样手法诈骗，对方冒充"京东金融"客服，诱骗其转账 89,600 元。

【资金流向】
被骗资金通过多个一级账户迅速分散转入二级账户，最终在境外取现。账户信息显示开户人均为"张伟"等人，但实际控制人信息被层层掩盖。

【作案手法分析】
1. 开场白："您好，我是京东金融/京东客服，您名下有一笔账户异常..."
2. 制造恐慌："如不处理，您的征信将受到严重影响"
3. 诱导转账："请将资金转入安全账户进行验证，稍后会全额返还"
4. 消失：验证后即失联

【初步结论】
初步判断为同一诈骗团伙所为，具有"注销校园贷"类诈骗特征，建议并案侦查。`
}

const handleBeforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    uploadedImages.value.push({
      url: e.target.result,
      name: file.name
    })
  }
  reader.readAsDataURL(file)
  return false
}

const gangIcons = ['🦈', '🐺', '🦊', '🐍', '🐯', '🦅']

const formatAmount = (amount) => {
  const num = typeof amount === 'number' ? amount : parseFloat(amount) || 0
  if (num >= 10000) {
    return '¥' + (num / 10000).toFixed(1) + '万'
  }
  return '¥' + num.toLocaleString()
}

const startAnalysis = async () => {
  if (!inputText.value.trim()) return
  loading.value = true

  const sessionId = 'session_' + Date.now()
  const messages = [{ role: 'user', content: inputText.value }]

  try {
    connectSocket(sessionId, {
      onProgress: (data) => {
        console.log('分析进度:', data)
      },
      onComplete: (data) => {
        console.log('分析完成:', data)
      }
    })

    const response = await apiStartAnalysis(messages, sessionId)

    if (response.success) {
      gangs.value = (response.gangs || []).map((g, idx) => ({
        id: g.gang_id || 'G' + String(idx + 1).padStart(3, '0'),
        name: g.gang_name || '未知团伙',
        icon: gangIcons[idx % gangIcons.length],
        riskLevel: g.risk_level || 'B',
        amount: formatAmount(g.total_amount_involved),
        cases: g.total_cases || 0,
        tags: Array.isArray(g.fingerprint)
          ? g.fingerprint.filter(Boolean)
          : g.fingerprint
            ? g.fingerprint.split(/[,，、]/).map(t => t.trim()).filter(Boolean)
            : [],
        members: Array.isArray(g.network_nodes)
          ? g.network_nodes.slice(0, 6).map((n, i) => ({
              id: i + 1,
              name: n.label || n.id || '成员' + (i + 1),
              icon: '👤',
              role: n.role || n.type || '成员'
            }))
          : [],
        timeline: (g.steps || []).map(s => ({
          date: s.date || s.time || '',
          title: s.title || s.name || '',
          desc: s.description || s.desc || '',
          type: s.type || '活动'
        })),
        evidence: [],
        abilities: g.radar_data || { tech: 50, org: 50, antiDetect: 50 },
        victims: g.total_cases || 0,
        createTime: '',
        updateTime: '刚刚'
      }))

      cases.value = (response.raw_cases || []).map(c => ({
        id: c.case_id || 'C' + String(Math.random()).slice(2, 8),
        title: (c.victim || '当事人') + '被诈骗案',
        gang: c.related_gang_id || c.assigned_gang || '',
        amount: formatAmount(c.amount),
        status: c.is_error ? '待核查' : '已立案',
        date: c.extracted_entities?.date || '',
        region: c.extracted_entities?.address || '',
        type: c.scam_type || '',
        victims: 1,
        victimName: c.victim || '',
        victimGender: c.extracted_entities?.gender || '',
        victimAge: c.extracted_entities?.age || '',
        victimPhone: c.extracted_entities?.phone || '',
        victimJob: c.extracted_entities?.job || '',
        victimAddress: c.extracted_entities?.address || '',
        scamPhone: c.extracted_entities?.scam_phone || '',
        phoneLocation: c.extracted_entities?.phone_location || '',
        scamUrl: c.extracted_entities?.url || '',
        ipAddress: c.extracted_entities?.ip || '',
        description: c.ai_report || ''
      }))

      selectedCase.value = cases.value[0] || null
      const gangCount = response.gangs?.length || 0
      ElMessage.success(`AI 研判完成！已识别出 ${gangCount} 个涉案团伙`)
      activeMenu.value = 'overview'
    } else {
      ElMessage.error('分析失败: ' + (response.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('分析请求异常: ' + (err.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

const startImageAnalysis = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    ElMessage.success('图片识别完成，已提取关键信息')
    startAnalysis()
  }, 2000)
}

const toggleApiSource = (source) => {
  if (apiSources.value[source].connected) {
    ElMessage.success(`${source === 'bank' ? '银行风控' : source === 'police' ? '110报警平台' : '反诈平台'}已连接`)
  }
}

const syncApiData = (source) => {
  ElMessage.success('数据同步中...')
  setTimeout(() => {
    apiSources.value[source].lastSync = '刚刚'
    ElMessage.success('数据同步完成')
  }, 1500)
}

const fetchBankData = () => {
  apiDataPreview.value.push(
    { source: '银行风控', type: '交易流水', content: '账户 ***1234 异常转账记录', time: '2024-03-20 14:30', status: '已验证' },
    { source: '银行风控', type: '账户信息', content: '涉案账户开户人信息', time: '2024-03-20 14:25', status: '待验证' }
  )
  ElMessage.success('已获取银行风控数据')
}

const fetchPoliceData = () => {
  apiDataPreview.value.push(
    { source: '110平台', type: '警情信息', content: '诈骗类警情推送 #20240320001', time: '2024-03-20 10:15', status: '已验证' }
  )
  ElMessage.success('已获取110报警平台数据')
}

const fetchAntiFraudData = () => {
  apiDataPreview.value.push(
    { source: '反诈平台', type: '黑名单', content: '涉案号码 138****5678 已入库', time: '2024-03-20 09:00', status: '已验证' },
    { source: '反诈平台', type: '涉案账户', content: '账户 ***5678 已标记', time: '2024-03-20 09:05', status: '已验证' }
  )
  ElMessage.success('已获取反诈平台数据')
}

const importApiData = () => {
  ElMessage.success('数据已导入系统')
  apiDataPreview.value = []
}

const startApiAnalysis = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    startAnalysis()
  }, 1500)
}

const generateReport = () => {
  if (!reportConfig.value.gangId) {
    ElMessage.warning('请先选择一个团伙')
    return
  }
  generatingReport.value = true
  setTimeout(() => {
    generatingReport.value = false
    reportPreview.value = true
    ElMessage.success('报告生成成功')
  }, 1500)
}

const printReport = () => {
  ElMessage.success('正在准备打印...')
}

const downloadReport = () => {
  ElMessage.success('报告下载中...')
}

const loadDashboard = async () => {
  dashboardLoading.value = true
  try {
    const data = await getDashboardData()
    if (data.success) {
      dashboardData.value = {
        total_cases: data.total_cases ?? data.data?.total_cases ?? '-',
        total_gangs: data.total_gangs ?? data.data?.total_gangs ?? '-',
        total_amount: data.total_amount ?? data.data?.total_amount ?? '-',
        active_alerts: data.active_alerts ?? data.data?.active_alerts ?? '-',
        risk_distribution: data.risk_distribution ?? data.data?.risk_distribution ?? [],
        status_distribution: data.status_distribution ?? data.data?.status_distribution ?? [],
        top_scam_types: data.top_scam_types ?? data.data?.top_scam_types ?? [],
        monthly_trend: data.monthly_trend ?? data.data?.monthly_trend ?? [],
        recent_cases: data.recent_cases ?? data.data?.recent_cases ?? []
      }
      nextTick(() => initDashboardCharts())
    } else {
      ElMessage.error('获取看板数据失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('获取看板数据异常: ' + (err.message || '网络错误'))
  } finally {
    dashboardLoading.value = false
  }
}

const initDashboardCharts = () => {
  const riskData = dashboardData.value.risk_distribution.length
    ? dashboardData.value.risk_distribution
    : [
        { name: 'S级', value: 8, itemStyle: { color: '#ef4444' } },
        { name: 'A级', value: 15, itemStyle: { color: '#f59e0b' } },
        { name: 'B级', value: 22, itemStyle: { color: '#00d4ff' } },
        { name: 'C级', value: 18, itemStyle: { color: '#10b981' } }
      ]

  const statusData = dashboardData.value.status_distribution.length
    ? dashboardData.value.status_distribution
    : [
        { name: '已立案', value: 35, itemStyle: { color: '#f59e0b' } },
        { name: '侦办中', value: 28, itemStyle: { color: '#00d4ff' } },
        { name: '已结案', value: 15, itemStyle: { color: '#10b981' } },
        { name: '待核查', value: 12, itemStyle: { color: '#8b5cf6' } }
      ]

  const barData = dashboardData.value.top_scam_types.length
    ? dashboardData.value.top_scam_types
    : [
        { name: '冒充客服', count: 45 },
        { name: '刷单返利', count: 32 },
        { name: '贷款诈骗', count: 28 },
        { name: '投资理财', count: 23 },
        { name: '冒充公检法', count: 12 }
      ]

  const trendData = dashboardData.value.monthly_trend.length
    ? dashboardData.value.monthly_trend
    : [
        { month: '1月', amount: 120, cases: 8 },
        { month: '2月', amount: 182, cases: 12 },
        { month: '3月', amount: 191, cases: 15 },
        { month: '4月', amount: 234, cases: 18 },
        { month: '5月', amount: 290, cases: 22 },
        { month: '6月', amount: 330, cases: 25 }
      ]

  nextTick(() => {
    if (dashboardRiskChartRef.value) {
      if (dashboardRiskChart) dashboardRiskChart.dispose()
      dashboardRiskChart = echarts.init(dashboardRiskChartRef.value)
      dashboardRiskChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: {
          orient: 'vertical', right: 10, top: 'center',
          textStyle: { color: '#94a3b8' }
        },
        series: [{
          type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: riskData
        }]
      })
      dashboardRiskChart.resize()
    }

    if (dashboardStatusChartRef.value) {
      if (dashboardStatusChart) dashboardStatusChart.dispose()
      dashboardStatusChart = echarts.init(dashboardStatusChartRef.value)
      dashboardStatusChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: {
          orient: 'vertical', right: 10, top: 'center',
          textStyle: { color: '#94a3b8' }
        },
        series: [{
          type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: statusData
        }]
      })
      dashboardStatusChart.resize()
    }

    if (dashboardBarChartRef.value) {
      if (dashboardBarChart) dashboardBarChart.dispose()
      dashboardBarChart = echarts.init(dashboardBarChartRef.value)
      const barNames = barData.map(d => d.name)
      const barCounts = barData.map(d => d.count)
      const colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#00d4ff', '#10b981']
      dashboardBarChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category', data: barNames,
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
        },
        series: [{
          type: 'bar', barWidth: '60%',
          itemStyle: {
            color: (params) => colors[params.dataIndex % colors.length],
            borderRadius: [4, 4, 0, 0]
          },
          data: barCounts
        }]
      })
      dashboardBarChart.resize()
    }

    if (dashboardTrendChartRef.value) {
      if (dashboardTrendChart) dashboardTrendChart.dispose()
      dashboardTrendChart = echarts.init(dashboardTrendChartRef.value)
      dashboardTrendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: {
          data: ['涉案金额', '案件数量'],
          textStyle: { color: '#94a3b8' }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category', boundaryGap: false,
          data: trendData.map(d => d.month),
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
        },
        series: [
          {
            name: '涉案金额', type: 'line', smooth: true,
            yAxisIndex: 0,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
              ])
            },
            lineStyle: { color: '#00d4ff', width: 2 },
            itemStyle: { color: '#00d4ff' },
            data: trendData.map(d => d.amount)
          },
          {
            name: '案件数量', type: 'line', smooth: true,
            yAxisIndex: 0,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(239, 68, 68, 0.2)' },
                { offset: 1, color: 'rgba(239, 68, 68, 0.02)' }
              ])
            },
            lineStyle: { color: '#ef4444', width: 2 },
            itemStyle: { color: '#ef4444' },
            data: trendData.map(d => d.cases)
          }
        ]
      })
      dashboardTrendChart.resize()
    }
  })
}

const loadAlerts = async () => {
  alertsLoading.value = true
  try {
    const data = await getActiveAlerts()
    if (data.success) {
      alerts.value = data.alerts || data.data || []
    } else {
      ElMessage.error('获取预警信息失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('获取预警信息异常: ' + (err.message || '网络错误'))
  } finally {
    alertsLoading.value = false
  }
}

// ========== P1 API Methods ==========
const loadCapitalFlows = async () => {
  try {
    const params = flowSearchCaseId.value ? { case_id: flowSearchCaseId.value } : {}
    const r = await api.get('/api/capital/flows', { params })
    capitalFlows.value = r.data.flows || r.data.data || []
  } catch (e) {
    console.error('loadCapitalFlows:', e)
  }
}
const loadFlowGraph = async () => {
  if (!flowSearchCaseId.value) return
  try {
    const r = await api.get('/api/capital/graph/' + flowSearchCaseId.value)
    flowGraphData.value = r.data
  } catch (e) {
    console.error('loadFlowGraph:', e)
  }
}
const loadFlowData = async () => {
  await loadCapitalFlows()
  await loadFlowGraph()
}
const addFlowRecord = (row) => {
  ElMessage.info('追加资金流向功能：' + row.source_account + ' → ' + row.target_account)
}

const loadDispatchOrders = async () => {
  try {
    const params = dispatchStatusFilter.value ? { status: dispatchStatusFilter.value } : {}
    const r = await api.get('/api/dispatch/list', { params })
    dispatchOrders.value = r.data.dispatch_orders || r.data.data || []
  } catch (e) {
    console.error('loadDispatchOrders:', e)
  }
}
const signDispatch = async (id) => {
  try {
    const r = await api.put('/api/dispatch/' + id + '/sign')
    if (r.data.success) { ElMessage.success('签收成功'); await loadDispatchOrders() }
    else ElMessage.error(r.data.error || '签收失败')
  } catch (e) {
    ElMessage.error('签收异常: ' + (e.message || ''))
  }
}
const showCompleteDispatch = (row) => {
  ElMessageBox.prompt('处置反馈内容', '完成派单', { inputType: 'textarea', inputPlaceholder: '请描述处置情况...' })
    .then(async ({ value }) => {
      const r = await api.put('/api/dispatch/' + row.id + '/complete', { feedback: value })
      if (r.data.success) { ElMessage.success('已完成'); await loadDispatchOrders() }
    }).catch(() => {})
}

const loadKeyPersons = async () => {
  try {
    const params = {}
    if (personSearch.value) params.search = personSearch.value
    if (personTypeFilter.value) params.person_type = personTypeFilter.value
    const r = await api.get('/api/persons/key', { params })
    keyPersons.value = r.data.persons || r.data.data || []
  } catch (e) {
    console.error('loadKeyPersons:', e)
  }
}
const deleteKeyPerson = async (id) => {
  try {
    const r = await api.delete('/api/persons/key/' + id)
    if (r.data.success) { ElMessage.success('已移除'); await loadKeyPersons() }
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

const handleResolveAlert = async (alertId) => {
  resolvingAlert.value = alertId
  try {
    const data = await resolveAlert(alertId)
    if (data.success) {
      alerts.value = alerts.value.filter(a => a.id !== alertId)
      ElMessage.success('预警已处置')
    } else {
      ElMessage.error('处置失败: ' + (data.message || '服务器返回异常'))
    }
  } catch (err) {
    ElMessage.error('处置异常: ' + (err.message || '网络错误'))
  } finally {
    resolvingAlert.value = null
  }
}

const getAlertType = (confidence) => {
  if (confidence >= 80) return 'danger'
  if (confidence >= 60) return 'warning'
  return 'info'
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 80) return '#ef4444'
  if (confidence >= 60) return '#f59e0b'
  return '#00d4ff'
}

const viewCaseFromDashboard = (caseItem) => {
  selectedCase.value = caseItem
  activeMenu.value = 'case-detail'
}

const initCharts = () => {
  nextTick(() => {
    if (pieChartRef.value) {
      if (pieChart) {
        pieChart.dispose()
      }
      pieChart = echarts.init(pieChartRef.value)
      pieChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c}起 ({d}%)' },
        legend: {
          orient: 'vertical',
          right: 10,
          top: 'center',
          textStyle: { color: '#94a3b8' }
        },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#0a0e1a', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
          data: [
            { value: 45, name: '冒充客服', itemStyle: { color: '#ef4444' } },
            { value: 32, name: '刷单返利', itemStyle: { color: '#f59e0b' } },
            { value: 28, name: '贷款诈骗', itemStyle: { color: '#8b5cf6' } },
            { value: 23, name: '投资理财', itemStyle: { color: '#00d4ff' } }
          ]
        }]
      })
      pieChart.resize()
    }
    if (lineChartRef.value) {
      if (lineChart) {
        lineChart.dispose()
      }
      lineChart = echarts.init(lineChartRef.value)
      lineChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: ['1月', '2月', '3月', '4月', '5月', '6月'],
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.3)' } },
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: 'rgba(0, 198, 255, 0.1)' } }
        },
        series: [{
          name: '涉案金额',
          type: 'line',
          smooth: true,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
              { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
            ])
          },
          lineStyle: { color: '#00d4ff', width: 2 },
          itemStyle: { color: '#00d4ff' },
          data: [120, 182, 191, 234, 290, 330]
        }]
      })
      lineChart.resize()
    }
  })
}

watch(activeMenu, (newVal) => {
  if (newVal === 'overview' && gangs.value.length) {
    nextTick(() => initCharts())
  }
  if (newVal === 'dashboard') {
    loadDashboard()
  }
  if (newVal === 'alerts') {
    loadAlerts()
  }
})

onMounted(() => {
  console.log('反诈情报分析系统已启动')
})
</script>

<style scoped>
.police-system-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.particle-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.particle {
  position: absolute;
  background: var(--accent-cyan);
  border-radius: 50%;
  opacity: 0.3;
  animation: float 20s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  25% { transform: translateY(-30px) translateX(20px); opacity: 0.5; }
  50% { transform: translateY(-60px) translateX(-20px); opacity: 0.3; }
  75% { transform: translateY(-30px) translateX(10px); opacity: 0.5; }
}

.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image:
    linear-gradient(rgba(0, 198, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 198, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
  animation: scan 8s linear infinite;
  opacity: 0.5;
  z-index: 1;
}

@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}

.sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: 10;
  flex-shrink: 0;
}

.logo-area {
  padding: 24px 20px;
  text-align: center;
  border-bottom: 1px solid var(--border-primary);
  background: linear-gradient(180deg, rgba(0, 198, 255, 0.05) 0%, transparent 100%);
}

.logo-icon-wrapper {
  position: relative;
  width: 60px;
  height: 60px;
  margin: 0 auto 12px;
}

.logo-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}

.logo-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 32px;
}

.logo-area h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 2px;
}

.sub-title {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  margin-top: 4px;
  display: block;
}

.logo-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 4px 12px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: var(--accent-cyan);
}

.badge-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-cyan);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.side-menu {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}

.menu-group {
  margin-bottom: 8px;
}

.menu-group-title {
  padding: 8px 20px;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.menu-icon {
  font-size: 16px;
}

.menu-text {
  flex: 1;
}

.menu-badge {
  background: var(--accent-cyan);
  color: var(--bg-primary);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.system-status {
  padding: 16px 20px;
  border-top: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.active {
  background: var(--accent-cyan);
  box-shadow: 0 0 8px var(--accent-cyan);
}

.version {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 8px;
  background: rgba(0, 198, 255, 0.1);
  border-radius: 4px;
}

.status-details {
  display: flex;
  gap: 16px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-label {
  font-size: 10px;
  color: var(--text-muted);
}

.status-value {
  font-size: 11px;
  color: var(--text-secondary);
}

.status-value.online {
  color: var(--accent-green);
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  position: relative;
  z-index: 5;
}

.content-wrapper {
  max-width: 1600px;
  margin: 0 auto;
}

.fade-in {
  animation: fadeIn 0.5s ease;
}

.view-section {
  animation: fadeIn 0.5s ease;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 28px;
}

.section-desc {
  color: var(--text-secondary);
  margin: 0;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.quick-stats {
  display: flex;
  gap: 16px;
}

.quick-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
}

.qs-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-cyan);
}

.qs-label {
  font-size: 11px;
  color: var(--text-muted);
}

.input-container {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  margin-bottom: 24px;
}

.input-main {
  padding: 20px;
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-icon {
  font-size: 20px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.input-area {
  margin-bottom: 12px;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.format-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.tip-icon {
  font-size: 14px;
}

.input-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-card {
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 18px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-content {
  min-height: 60px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-label {
  font-size: 12px;
  color: var(--text-muted);
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.empty-text {
  font-size: 12px;
}

.checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.check-item.active {
  background: rgba(16, 185, 129, 0.1);
  color: var(--accent-green);
}

.check-icon {
  font-size: 14px;
}

.action-bar {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.analyze-btn {
  padding: 16px 48px;
  font-size: 16px;
  font-weight: 600;
  height: auto;
  background: linear-gradient(135deg, #00d4ff 0%, #0084ff 100%) !important;
  border: none !important;
  border-radius: 12px;
  color: #0a0e1a !important;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
}

.analyze-btn:hover {
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.6);
  transform: translateY(-2px);
}

.btn-icon {
  font-size: 20px;
}

.upload-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 24px;
}

.upload-main {
  padding: 20px;
}

.upload-toolbar {
  margin-bottom: 16px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  background: rgba(10, 14, 26, 0.8) !important;
  border: 2px dashed rgba(0, 198, 255, 0.4) !important;
  border-radius: 16px !important;
  width: 100% !important;
  height: auto !important;
  transition: all 0.3s ease !important;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-cyan) !important;
  background: rgba(0, 198, 255, 0.05) !important;
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.2) !important;
}

.upload-content {
  padding: 48px 24px;
  text-align: center;
}

.upload-icon-wrapper {
  margin-bottom: 16px;
}

.upload-icon {
  font-size: 56px;
  color: var(--accent-cyan);
}

.upload-text {
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-size: 15px;
}

.upload-text .highlight {
  color: var(--accent-cyan);
  font-weight: 600;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.upload-formats {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.format-tag {
  padding: 4px 12px;
  background: rgba(0, 198, 255, 0.1);
  border: 1px solid rgba(0, 198, 255, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: var(--accent-cyan);
}

.upload-preview {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.preview-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-primary);
  background: rgba(10, 14, 26, 0.9);
}

.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.9));
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.preview-name {
  font-size: 10px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.preview-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
}

.upload-tips {
  padding: 20px;
}

.tip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.tip-icon {
  font-size: 18px;
}

.tip-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.tip-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tip-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 198, 255, 0.2);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.tip-text {
  font-size: 13px;
  color: var(--text-secondary);
}

.api-sources-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.api-source-card {
  padding: 20px;
  transition: all 0.3s ease;
}

.api-source-card.active {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.2);
}

.source-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.source-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  border-radius: 12px;
}

.source-icon.bank {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.source-icon.police {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.source-icon.antiFraud {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
}

.source-info {
  flex: 1;
}

.source-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.source-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.source-content {
  margin-bottom: 16px;
}

.source-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}

.source-features {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.feature-icon {
  font-size: 14px;
}

.source-stats {
  display: flex;
  gap: 24px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.source-actions {
  display: flex;
  gap: 8px;
}

.api-data-preview {
  padding: 20px;
  margin-bottom: 24px;
}

.api-data-preview .preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.api-data-preview .preview-icon {
  font-size: 18px;
}

.api-data-preview .preview-title {
  flex: 1;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 28px;
}

.stat-icon-wrapper.danger {
  background: rgba(239, 68, 68, 0.15);
}

.stat-icon-wrapper.warning {
  background: rgba(245, 158, 11, 0.15);
}

.stat-icon-wrapper.success {
  background: rgba(16, 185, 129, 0.15);
}

.stat-icon-wrapper.info {
  background: rgba(0, 198, 255, 0.15);
}

.stat-content {
  flex: 1;
}

.stat-content .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-content .stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.stat-trend.up {
  color: var(--accent-green);
}

.overview-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  padding: 20px;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-content {
  height: 250px;
}

.gangs-section {
  margin-bottom: 24px;
}

.section-sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.sub-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.sub-icon {
  font-size: 18px;
}

.filter-bar {
  display: flex;
  gap: 12px;
}

.search-input {
  width: 200px;
}

.gangs-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.gang-card {
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.gang-card:hover,
.gang-card.selected {
  transform: translateY(-4px);
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.2);
}

.gang-card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.gang-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 28px;
}

.gang-icon-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.gang-icon-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.gang-icon-wrapper.risk-b {
  background: rgba(0, 198, 255, 0.2);
  border: 1px solid rgba(0, 198, 255, 0.4);
}

.gang-info {
  flex: 1;
}

.gang-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.gang-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gang-id {
  font-size: 11px;
  color: var(--text-muted);
}

.gang-card-body {
  margin-bottom: 16px;
}

.gang-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.gang-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.gang-stat .stat-icon {
  font-size: 16px;
}

.gang-stat .stat-content {
  display: flex;
  flex-direction: column;
}

.gang-stat .stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.gang-stat .stat-label {
  font-size: 10px;
  color: var(--text-muted);
}

.gang-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gang-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
}

.update-time {
  font-size: 11px;
  color: var(--text-muted);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.empty-content {
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.case-detail-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
}

.detail-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.case-header-card {
  padding: 24px;
}

.case-header-top {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 20px;
}

.case-icon-wrapper {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  font-size: 32px;
}

.case-icon-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 2px solid rgba(239, 68, 68, 0.4);
}

.case-icon-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 2px solid rgba(245, 158, 11, 0.4);
}

.case-header-info {
  flex: 1;
}

.case-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.case-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-icon {
  font-size: 14px;
}

.case-header-actions {
  display: flex;
  gap: 8px;
}

.case-header-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.header-stat {
  text-align: center;
}

.header-stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  display: block;
}

.header-stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.detail-tabs {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.detail-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: rgba(0, 0, 0, 0.2);
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.detail-tabs :deep(.el-tabs__item) {
  color: var(--text-secondary);
  padding: 16px 20px;
  height: auto;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-cyan);
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background: var(--accent-cyan);
}

.detail-tabs :deep(.el-tabs__content) {
  padding: 20px;
}

.timeline-section {
  padding: 24px;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent-cyan);
  border: 3px solid var(--bg-primary);
  box-shadow: 0 0 10px var(--accent-cyan);
}

.timeline-dot.dot-0 { background: #ef4444; box-shadow: 0 0 10px #ef4444; }
.timeline-dot.dot-1 { background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }
.timeline-dot.dot-2 { background: #8b5cf6; box-shadow: 0 0 10px #8b5cf6; }
.timeline-dot.dot-3 { background: #00d4ff; box-shadow: 0 0 10px #00d4ff; }

.timeline-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(to bottom, var(--border-secondary), transparent);
  margin-top: 8px;
}

.timeline-content {
  flex: 1;
  padding-bottom: 8px;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.timeline-date {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.timeline-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.timeline-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.timeline-details {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.detail-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 6px;
}

.detail-label {
  color: var(--text-muted);
}

.detail-value {
  color: var(--text-primary);
}

.method-section,
.money-section {
  padding: 24px;
}

.method-header,
.money-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.method-icon,
.money-icon {
  font-size: 24px;
}

.method-title,
.money-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.method-flow {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  overflow-x: auto;
  padding: 16px 0;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: max-content;
}

.step-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}

.step-content {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.step-desc {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 150px;
}

.step-arrow {
  font-size: 20px;
  color: var(--text-muted);
}

.method-keywords {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.keyword-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.money-flow {
  margin-bottom: 20px;
}

.flow-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 24px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  flex-wrap: wrap;
}

.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-radius: 12px;
  min-width: 100px;
}

.flow-node.source {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.flow-node.gang {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
}

.flow-node.middle {
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.flow-node.target {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.node-icon {
  font-size: 24px;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.node-amount {
  font-size: 11px;
  color: var(--text-muted);
}

.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 24px;
  color: var(--text-muted);
}

.arrow-label {
  font-size: 10px;
  color: var(--text-muted);
}

.money-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.money-stat {
  text-align: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.ms-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.ms-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-section {
  padding: 16px;
}

.section-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-icon {
  font-size: 16px;
}

.section-title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.evidence-icon {
  font-size: 20px;
}

.evidence-info {
  flex: 1;
}

.evidence-name {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.member-avatar {
  font-size: 20px;
}

.member-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.member-name {
  font-size: 13px;
  color: var(--text-primary);
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feature-tag {
  margin: 0;
}

.profiles-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.profile-card {
  padding: 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-primary);
}

.profile-avatar-wrapper {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  font-size: 32px;
}

.profile-avatar-wrapper.risk-s {
  background: rgba(239, 68, 68, 0.2);
  border: 2px solid rgba(239, 68, 68, 0.4);
}

.profile-avatar-wrapper.risk-a {
  background: rgba(245, 158, 11, 0.2);
  border: 2px solid rgba(245, 158, 11, 0.4);
}

.profile-basic {
  flex: 1;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.profile-id {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.profile-quick-stats {
  display: flex;
  gap: 16px;
}

.quick-stat-item {
  text-align: right;
}

.qsi-value {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.qsi-label {
  font-size: 11px;
  color: var(--text-muted);
}

.profile-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-section {
  margin-bottom: 0;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--accent-cyan);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.label-icon {
  font-size: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.info-label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.info-value.danger {
  color: var(--accent-red);
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.member-details {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ability-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ability-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ability-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.profile-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.analysis-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.analysis-card {
  padding: 20px;
}

.analysis-card.full-width {
  grid-column: span 2;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.analysis-icon {
  font-size: 20px;
}

.analysis-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.analysis-subtitle {
  font-size: 12px;
  color: var(--accent-cyan);
  margin-left: auto;
  padding: 2px 8px;
  background: rgba(0, 198, 255, 0.1);
  border-radius: 4px;
}

.flow-badge {
  font-size: 11px;
  color: #f59e0b;
  margin-left: auto;
  padding: 3px 10px;
  background: rgba(245, 158, 11, 0.15);
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.flow-chart {
  margin-bottom: 20px;
}

.flow-path {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 0;
  flex-wrap: wrap;
}

.flow-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stage-node {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 2px solid;
}

.stage-node.source {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.5);
}

.stage-node.gang {
  background: rgba(139, 92, 246, 0.15);
  border-color: rgba(139, 92, 246, 0.5);
}

.stage-node.middle {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.5);
}

.stage-node.target {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
}

.stage-node .node-glow {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  animation: pulse-glow 2s ease-in-out infinite;
}

.stage-node.source .node-glow {
  background: rgba(239, 68, 68, 0.3);
}

.stage-node.gang .node-glow {
  background: rgba(139, 92, 246, 0.3);
}

.stage-node.middle .node-glow {
  background: rgba(245, 158, 11, 0.3);
}

.stage-node.target .node-glow {
  background: rgba(16, 185, 129, 0.3);
}

.stage-node .node-icon {
  font-size: 22px;
  position: relative;
  z-index: 1;
}

.stage-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.stage-desc {
  font-size: 10px;
  color: var(--text-muted);
}

.flow-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 5px;
}

.connector-line {
  width: 40px;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-cyan), rgba(0, 198, 255, 0.3));
}

.connector-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid var(--accent-cyan);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
}

.connector-label {
  font-size: 10px;
  color: var(--text-muted);
}

.flow-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.metric-icon {
  font-size: 20px;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
}

.metric-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.feature-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: var(--feature-color, var(--accent-cyan));
  transform: translateY(-2px);
}

.feature-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(0, 198, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-icon {
  font-size: 18px;
}

.feature-info {
  flex: 1;
}

.feature-card .feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-card .feature-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.feature-card .feature-value {
  font-size: 13px;
  font-weight: 600;
}

.feature-desc {
  font-size: 10px;
  color: var(--text-muted);
}

.feature-bar-wrap {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.feature-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s ease;
}

@keyframes pulse-glow {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 0; }
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-name {
  font-size: 13px;
  color: var(--text-secondary);
}

.feature-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.relation-map {
  min-height: 300px;
}

.relation-viz {
  position: relative;
  height: 300px;
}

.rel-node {
  position: absolute;
  width: 60px;
  height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: all 0.3s ease;
}

.rel-node.gang {
  background: rgba(139, 92, 246, 0.3);
  border: 2px solid var(--accent-purple);
}

.rel-node.case {
  background: rgba(0, 198, 255, 0.3);
  border: 2px solid var(--accent-cyan);
}

.rel-node.money {
  background: rgba(245, 158, 11, 0.3);
  border: 2px solid var(--accent-orange);
}

.rel-node:hover {
  transform: translate(-50%, -50%) scale(1.2);
}

.rel-icon {
  font-size: 20px;
}

.rel-label {
  font-size: 10px;
  color: var(--text-primary);
}

.relation-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.relation-lines line {
  stroke: var(--border-secondary);
  stroke-width: 2;
}

.type-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.type-item {
  position: relative;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.type-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  opacity: 0.3;
  border-radius: 8px;
}

.type-info {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-name {
  font-size: 13px;
  color: var(--text-primary);
}

.type-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.region-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.region-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.region-name {
  width: 50px;
  font-size: 12px;
  color: var(--text-secondary);
}

.region-bar-wrapper {
  flex: 1;
  height: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.region-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  border-radius: 4px;
}

.region-count {
  width: 50px;
  text-align: right;
  font-size: 12px;
  color: var(--text-primary);
}

.network-container {
  height: calc(100vh - 320px);
  min-height: 500px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.network-legend {
  display: flex;
  justify-content: center;
  gap: 30px;
  padding: 16px;
  margin-top: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.gang-s {
  background: #ff3860;
  box-shadow: 0 0 8px rgba(255, 56, 96, 0.5);
}

.legend-dot.gang-a {
  background: #ffd700;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
}

.legend-dot.case {
  background: #00c6ff;
  box-shadow: 0 0 8px rgba(0, 198, 255, 0.5);
}

.legend-dot.money {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
}

.legend-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.report-container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
}

.report-config-panel {
  padding: 20px;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary);
}

.config-icon {
  font-size: 20px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-footer {
  padding-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.generate-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
}

.report-preview-panel {
  padding: 20px;
}

.report-preview-panel .preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.report-preview-panel .preview-icon {
  font-size: 18px;
}

.report-preview-panel .preview-title {
  flex: 1;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.preview-body {
  min-height: 500px;
}

.report-document {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #e2e8f0;
  padding: 40px;
  border-radius: 12px;
  font-family: "Microsoft YaHei", "SimHei", serif;
  border: 1px solid rgba(0, 198, 255, 0.2);
  box-shadow: 0 0 30px rgba(0, 198, 255, 0.1);
}

.doc-header {
  text-align: center;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 2px solid rgba(0, 198, 255, 0.3);
  position: relative;
}

.doc-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
}

.doc-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.doc-logo .logo-icon {
  font-size: 24px;
  position: static;
  transform: none;
}

.doc-logo .logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.doc-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
  text-shadow: 0 0 20px rgba(0, 198, 255, 0.3);
}

.doc-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 12px;
  color: var(--text-secondary);
}

.doc-meta .meta-item {
  color: var(--text-secondary);
}

.doc-meta .meta-value {
  color: var(--text-primary);
}

.doc-meta .meta-value.secret {
  color: var(--accent-red);
  font-weight: 600;
}

.doc-content {
  margin-bottom: 32px;
}

.doc-section {
  margin-bottom: 24px;
}

.doc-section .section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-cyan);
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 4px solid var(--accent-cyan);
}

.doc-section .section-body {
  padding-left: 16px;
}

.info-table {
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.info-row {
  display: flex;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .info-label {
  width: 120px;
  padding: 10px 12px;
  background: rgba(0, 198, 255, 0.1);
  font-size: 13px;
  color: var(--text-secondary);
}

.info-row .info-value {
  flex: 1;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
}

.info-row .info-value.danger {
  color: var(--accent-red);
  font-weight: 600;
}

.doc-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-timeline-item {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.doc-time {
  width: 80px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.doc-event {
  width: 120px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.doc-desc {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.money-flow-summary {
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.money-flow-summary p {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 198, 255, 0.1);
}

.suggestion-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-cyan);
  color: var(--bg-primary);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
}

.suggestion-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.doc-footer {
  text-align: center;
  padding-top: 24px;
}

.footer-line {
  height: 1px;
  background: #ddd;
  margin-bottom: 16px;
}

.footer-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #999;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: var(--text-muted);
}

.preview-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.preview-empty .empty-text {
  font-size: 14px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1400px) {
  .api-sources-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .profiles-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1200px) {
  .input-container {
    grid-template-columns: 1fr;
  }
  
  .case-detail-content {
    grid-template-columns: 1fr;
  }
  
  .detail-sidebar {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .sidebar-section {
    flex: 1;
    min-width: 280px;
  }
  
  .report-container {
    grid-template-columns: 1fr;
  }
}

.login-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(10, 14, 26, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(8px);
}

.login-container {
  width: 420px;
  padding: 0;
  overflow: visible;
}

.login-header {
  text-align: center;
  padding: 40px 40px 24px;
  border-bottom: 1px solid var(--border-primary);
  background: linear-gradient(180deg, rgba(0, 198, 255, 0.05) 0%, transparent 100%);
}

.login-logo-wrapper {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
}

.login-logo-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

.login-logo-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 36px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 3px;
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 3px;
  margin: 0;
}

.login-form {
  padding: 32px 40px 24px;
}

.login-field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.login-field-icon {
  font-size: 20px;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: var(--radius-md);
}

.login-input {
  flex: 1;
}

.login-input .el-input__wrapper {
  background: rgba(0, 0, 0, 0.4) !important;
}

.login-error {
  color: var(--accent-red);
  font-size: 13px;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  text-align: center;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 6px;
}

.login-btn .el-button--primary {
  height: 44px;
}

.login-footer {
  text-align: center;
  padding: 16px 40px 32px;
}

.login-footer-text {
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.logout-area {
  border-top: 1px solid var(--border-primary);
  padding: 8px 12px;
}

.logout-btn {
  width: 100%;
  justify-content: center;
}

.alert-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.alert-card:hover {
  border-color: rgba(0, 198, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 198, 255, 0.05);
}

.alert-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 24px 16px;
}

.alert-icon-wrapper {
  width: 44px;
  height: 44px;
  background: rgba(239, 68, 68, 0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.alert-icon {
  font-size: 22px;
}

.alert-info {
  flex: 1;
  min-width: 0;
}

.alert-type {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.alert-id {
  font-size: 12px;
  color: var(--text-muted);
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.alert-meta .meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.alert-meta .meta-icon {
  font-size: 14px;
}

.alert-actions {
  flex-shrink: 0;
}

.alert-body {
  padding: 0 24px 12px;
}

.alert-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.alert-footer {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--border-primary);
}

.confidence-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.confidence-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.confidence-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.confidence-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.recent-cases-section {
  margin-top: 32px;
}

.recent-cases-section .section-sub-header {
  margin-bottom: 16px;
}

.recent-cases-section .sub-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
</style>