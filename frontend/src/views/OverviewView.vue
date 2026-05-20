<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title">
        <span class="title-icon">📊</span>
        案件总览
      </h2>
      <p class="section-desc">查看所有录入案件信息，点击可进入案件详情页</p>
    </div>
    <div class="header-right">
      <div class="view-toggle">
        <el-button-group>
          <el-button size="small" :type="viewMode === 'card' ? 'primary' : ''" @click="viewMode = 'card'">📇 卡片</el-button>
          <el-button size="small" :type="viewMode === 'table' ? 'primary' : ''" @click="viewMode = 'table'">📋 列表</el-button>
        </el-button-group>
      </div>
    </div>
  </div>

  <div class="stats-overview">
    <div class="stat-card tech-card">
      <div class="stat-icon-wrapper danger"><span class="stat-icon">📋</span></div>
      <div class="stat-content"><div class="stat-value">{{ cases.length }}</div><div class="stat-label">案件总数</div></div>
    </div>
    <div class="stat-card tech-card">
      <div class="stat-icon-wrapper warning"><span class="stat-icon">👥</span></div>
      <div class="stat-content"><div class="stat-value">{{ gangs.length }}</div><div class="stat-label">涉案团伙</div></div>
    </div>
    <div class="stat-card tech-card">
      <div class="stat-icon-wrapper success"><span class="stat-icon">💰</span></div>
      <div class="stat-content"><div class="stat-value">{{ totalAmountFormatted }}</div><div class="stat-label">涉案金额</div></div>
    </div>
    <div class="stat-card tech-card">
      <div class="stat-icon-wrapper info"><span class="stat-icon">🎯</span></div>
      <div class="stat-content"><div class="stat-value">{{ successRate }}%</div><div class="stat-label">研判准确率</div></div>
    </div>
  </div>

  <div class="overview-charts">
    <div class="chart-card tech-card">
      <div class="chart-header"><span class="chart-title">案件类型分布</span></div>
      <div class="chart-content" ref="pieChartRef"></div>
    </div>
    <div class="chart-card tech-card">
      <div class="chart-header"><span class="chart-title">涉案金额趋势</span></div>
      <div class="chart-content" ref="lineChartRef"></div>
    </div>
  </div>

  <div class="cases-section" v-if="cases.length">
    <div class="section-sub-header">
      <h3 class="sub-title"><span class="sub-icon">📋</span>案件列表</h3>
    </div>
    <div v-if="viewMode === 'card'" class="cases-card-grid">
      <div v-for="c in cases" :key="c.id" class="case-card tech-card" @click="viewCaseDetail(c)">
        <div class="case-card-top">
          <span class="case-badge">{{ c.scam_type || c.type || '其他' }}</span>
          <span class="case-amount">{{ c.amount }}</span>
        </div>
        <div class="case-card-title">{{ c.title }}</div>
        <div class="case-card-meta">
          <span>👤 {{ c.victimName || '未知' }}</span>
          <span>📅 {{ c.date || c.created_at ? (c.date||c.created_at).slice(0,10) : '-' }}</span>
        </div>
        <div class="case-card-footer">
          <el-tag :type="c.status === '已立案' ? 'warning' : c.status === '侦办中' ? 'primary' : 'success'" size="small">{{ c.status }}</el-tag>
          <span class="case-card-gang" v-if="getCaseGang(c.id)">👥 {{ getCaseGang(c.id).name }}</span>
        </div>
      </div>
    </div>
    <div v-else class="cases-table">
      <el-table :data="cases" style="width:100%" @row-click="viewCaseDetail" highlight-current-row stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="title" label="案件名称" min-width="160" />
        <el-table-column prop="type" label="类型" width="100"><template #default="s"><el-tag type="info" size="small">{{ s.row.type }}</el-tag></template></el-table-column>
        <el-table-column prop="amount" label="金额" width="120" />
        <el-table-column prop="status" label="状态" width="90"><template #default="s"><el-tag :type="s.row.status==='已立案'?'warning':'primary'" size="small">{{ s.row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="date" label="时间" width="110" />
        <el-table-column label="操作" width="80"><template #default="s"><el-button size="small" type="primary" @click="viewCaseDetail(s.row)">详情</el-button></template></el-table-column>
      </el-table>
    </div>
  </div>

  <div v-if="gangs.length" class="gangs-section">
    <div class="section-sub-header">
      <h3 class="sub-title"><span class="sub-icon">👥</span>关联团伙</h3>
      <div class="filter-bar">
        <el-input v-model="gangSearchKeyword" placeholder="搜索团伙..." size="small" style="width:160px" clearable />
        <el-select v-model="riskFilter" placeholder="风险等级" size="small" clearable style="width:120px">
          <el-option label="S级" value="S" /><el-option label="A级" value="A" /><el-option label="B级" value="B" />
        </el-select>
      </div>
    </div>
    <div class="gangs-list">
      <el-table :data="filteredGangs" style="width:100%" @row-click="viewGangDetail" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="团伙名称" min-width="140" />
        <el-table-column prop="riskLevel" label="风险" width="70"><template #default="s"><el-tag :type="s.row.riskLevel==='S'?'danger':s.row.riskLevel==='A'?'warning':'info'" size="small">{{ s.row.riskLevel }}</el-tag></template></el-table-column>
        <el-table-column prop="amount" label="金额" width="120" />
        <el-table-column prop="cases" label="案件数" width="70" />
        <el-table-column label="操作" width="80"><template #default="s"><el-button size="small" type="primary" @click.stop="viewGangDetail(s.row)">分析</el-button></template></el-table-column>
      </el-table>
    </div>
  </div>

  <div v-if="!cases.length && !gangs.length" class="empty-state">
    <div class="empty-content">
      <div class="empty-icon">📊</div>
      <h3 class="empty-title">暂无数据</h3>
      <p class="empty-desc">请先通过录入功能添加案情信息</p>
      <el-button type="primary" size="large" @click="router.push({ name: 'input' })">📝 前往录入</el-button>
    </div>
  </div>
</div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const state = useAppState()
const {
  activeMenu, cases, gangSearchKeyword, gangs, lineChartRef, pieChartRef, successRate,
  totalAmount, totalAmountFormatted, viewMode,
  riskFilter, filteredGangs, getCaseGang, selectGang, viewGangDetail, viewCaseDetail, getRiskType
} = state
</script>

<style scoped>
.cases-card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; margin-bottom: 20px; }
.case-card { padding: 16px; cursor: pointer; transition: all 0.25s ease; }
.case-card:hover { border-color: var(--accent-cyan); box-shadow: 0 0 20px rgba(0,198,255,0.15); transform: translateY(-2px); }
.case-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.case-badge { font-size: 11px; padding: 2px 8px; background: rgba(0,198,255,0.1); border-radius: 4px; color: var(--accent-cyan); font-weight: 500; }
.case-amount { font-size: 16px; font-weight: 700; color: var(--accent-red); }
.case-card-title { font-size: 14px; color: var(--text-primary); font-weight: 600; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-card-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.case-card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--border-primary); }
.case-card-gang { font-size: 11px; color: var(--accent-cyan); }
.gangs-list { margin-bottom: 16px; }
</style>