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
      <div class="cases-toolbar" v-if="viewMode === 'table'">
        <div class="toolbar-left">
          <span class="selected-count" v-if="selectedCaseIds.length">已选 {{ selectedCaseIds.length }} 条</span>
        </div>
        <div class="toolbar-right">
          <el-button size="small" type="danger" :disabled="!selectedCaseIds.length" @click="handleBatchDelete">
            <span>🗑️</span> 批量删除
          </el-button>
          <el-select v-model="batchStatus" size="small" placeholder="批量修改状态" :disabled="!selectedCaseIds.length" style="width:140px" @change="handleBatchStatus">
            <el-option label="已立案" value="已立案" />
            <el-option label="侦办中" value="侦办中" />
            <el-option label="已结案" value="已结案" />
          </el-select>
        </div>
      </div>
      <el-table :data="cases" style="width:100%" @row-click="viewCaseDetail" highlight-current-row stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="title" label="案件名称" min-width="160" />
        <el-table-column prop="type" label="类型" width="100"><template #default="s"><el-tag type="info" size="small">{{ s.row.type }}</el-tag></template></el-table-column>
        <el-table-column prop="amount" label="金额" width="120" />
        <el-table-column prop="status" label="状态" width="90"><template #default="s"><el-tag :type="s.row.status==='已立案'?'warning':s.row.status==='侦办中'?'primary':'success'" size="small">{{ s.row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="date" label="时间" width="110" />
        <el-table-column label="操作" width="80"><template #default="s"><el-button size="small" type="primary" @click="viewCaseDetail(s.row)">详情</el-button></template></el-table-column>
      </el-table>
    </div>
  </div>

  <div v-if="gangs.length" class="gangs-section">
    <div class="gangs-card">
      <div class="section-sub-header">
        <h3 class="sub-title"><span class="sub-icon">👥</span>关联团伙</h3>
        <div class="filter-bar">
          <el-input v-model="gangSearchKeyword" placeholder="搜索团伙..." size="small" style="width:160px" clearable />
          <el-select v-model="riskFilter" placeholder="风险等级" size="small" clearable style="width:120px">
            <el-option label="S级" value="S" /><el-option label="A级" value="A" /><el-option label="B级" value="B" />
          </el-select>
        </div>
      </div>
      <div class="gangs-grid">
        <div v-for="g in filteredGangs" :key="g.id" class="gang-item" @click="viewGangDetail(g)">
          <div class="gang-header">
            <span class="gang-name">{{ g.name }}</span>
            <el-tag v-if="g.riskLevel==='S'" type="danger" size="small">S级</el-tag>
            <el-tag v-else-if="g.riskLevel==='A'" type="warning" size="small">A级</el-tag>
            <el-tag v-else type="info" size="small">B级</el-tag>
          </div>
          <div class="gang-metrics">
            <div class="gang-metric">
              <span class="gang-metric-value">¥{{ g.amount }}</span>
              <span class="gang-metric-label">涉案金额</span>
            </div>
            <div class="gang-metric">
              <span class="gang-metric-value">{{ g.cases }}</span>
              <span class="gang-metric-label">关联案件</span>
            </div>
          </div>
          <div class="gang-footer">
            <el-button size="small" type="primary" @click.stop="viewGangDetail(g)">深度分析</el-button>
          </div>
        </div>
      </div>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteCase, updateCaseStatus } from '../api.js'

const router = useRouter()
const state = useAppState()
const {
  activeMenu, cases, gangSearchKeyword, gangs, lineChartRef, pieChartRef, successRate,
  totalAmount, totalAmountFormatted, viewMode,
  riskFilter, filteredGangs, getCaseGang, selectGang, viewGangDetail, viewCaseDetail, getRiskType
} = state

const selectedCaseIds = ref([])
const batchStatus = ref('')

const onSelectionChange = (selection) => {
  selectedCaseIds.value = selection.map(s => s.id || s.case_id).filter(Boolean)
}

const handleBatchDelete = async () => {
  if (!selectedCaseIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedCaseIds.value.length} 条案件？此操作不可恢复。`,
      '批量删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    for (const id of selectedCaseIds.value) {
      try { await deleteCase(id) } catch (e) { console.warn('delete failed:', id, e) }
    }
    ElMessage.success(`已删除 ${selectedCaseIds.value.length} 条案件`)
    selectedCaseIds.value = []
    batchStatus.value = ''
    window.location.reload()
  } catch (e) { /* cancelled */ }
}

const handleBatchStatus = async (status) => {
  if (!selectedCaseIds.value.length || !status) return
  for (const id of selectedCaseIds.value) {
    try { await updateCaseStatus(id, status) } catch (e) { console.warn('status update failed:', id, e) }
  }
  ElMessage.success(`已将 ${selectedCaseIds.value.length} 条案件状态改为「${status}」`)
  selectedCaseIds.value = []
  batchStatus.value = ''
  window.location.reload()
}
</script>

<style scoped>
.section-header { margin-bottom: 12px; }

.section-title { font-size: 20px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin: 0; }

.section-title .title-icon { font-size: 22px; }

.section-desc { font-size: 13px; color: var(--text-muted); margin: 4px 0 0; }

.stats-overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }

.stat-card { padding: 18px 20px; display: flex; align-items: center; gap: 16px; transition: all 0.3s ease; cursor: pointer; border: 1px solid rgba(0,198,255,0.08); position: relative; overflow: hidden; }

.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; opacity: 0.5; transition: opacity 0.3s ease; }

.stat-card:nth-child(1)::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.stat-card:nth-child(2)::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.stat-card:nth-child(3)::before { background: linear-gradient(90deg, #10b981, #34d399); }
.stat-card:nth-child(4)::before { background: linear-gradient(90deg, #00d4ff, #38bdf8); }

.stat-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,198,255,0.12); border-color: rgba(0,198,255,0.2); }

.stat-card:hover::before { opacity: 1; }

.stat-icon-wrapper { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

.stat-icon-wrapper.danger { background: rgba(239,68,68,0.15); }
.stat-icon-wrapper.warning { background: rgba(245,158,11,0.15); }
.stat-icon-wrapper.success { background: rgba(16,185,129,0.15); }
.stat-icon-wrapper.info { background: rgba(0,212,255,0.15); }

.stat-icon { font-size: 20px; transition: transform 0.5s ease; display: inline-block; }

.stat-card:hover .stat-icon { transform: rotate(360deg); }

.stat-content { flex: 1; }

.stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', 'Consolas', monospace; line-height: 1.2; }

.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.overview-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }

.chart-card { padding: 16px; border: 1px solid rgba(0,198,255,0.08); }

.chart-header { border-left: 3px solid var(--accent-cyan); padding-left: 12px; margin-bottom: 12px; }

.chart-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }

.chart-content { width: 100%; height: 260px; }

.section-sub-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-top: 8px; }

.sub-title { font-size: 16px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px; margin: 0; }

.sub-icon { font-size: 18px; }

.filter-bar { display: flex; gap: 8px; align-items: center; }

.cases-card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; margin-bottom: 20px; }

.case-card { padding: 16px; cursor: pointer; transition: all 0.25s ease; animation: fadeInUp 0.5s ease both; border: 1px solid rgba(0,198,255,0.08); position: relative; overflow: hidden; }

.case-card::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent); opacity: 0; transition: opacity 0.3s ease; }

.case-card:hover::after { opacity: 0.6; }

.case-card:nth-child(1) { animation-delay: 0.05s; }
.case-card:nth-child(2) { animation-delay: 0.1s; }
.case-card:nth-child(3) { animation-delay: 0.15s; }
.case-card:nth-child(4) { animation-delay: 0.2s; }
.case-card:nth-child(5) { animation-delay: 0.25s; }
.case-card:nth-child(6) { animation-delay: 0.3s; }
.case-card:nth-child(7) { animation-delay: 0.35s; }
.case-card:nth-child(8) { animation-delay: 0.4s; }
.case-card:nth-child(9) { animation-delay: 0.45s; }
.case-card:nth-child(10) { animation-delay: 0.5s; }

.case-card:hover { border-color: var(--accent-cyan); box-shadow: 0 0 20px rgba(0,198,255,0.15); transform: translateY(-2px); }

.case-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.case-badge { font-size: 11px; padding: 3px 10px; background: rgba(0,198,255,0.1); border-radius: 4px; color: var(--accent-cyan); font-weight: 500; border: 1px solid rgba(0,198,255,0.2); }

.case-amount { font-size: 16px; font-weight: 700; color: #f87171; text-shadow: 0 0 10px rgba(239,68,68,0.3); }

.case-card-title { font-size: 14px; color: var(--text-primary); font-weight: 600; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.case-card-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }

.case-card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid rgba(0,198,255,0.08); }

.case-card-gang { font-size: 11px; color: var(--accent-cyan); }

.gangs-list { margin-bottom: 16px; }

.cases-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 8px 16px; background: rgba(0,0,0,0.2); border: 1px solid rgba(0,198,255,0.1); border-radius: 8px; }

.selected-count { font-size: 12px; color: var(--accent-cyan); }

.cases-section, .gangs-section { margin-bottom: 20px; }

.gangs-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 16px;
}

.gangs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.gang-item {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(0, 212, 255, 0.08);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.gang-item:hover {
  border-color: rgba(0, 212, 255, 0.3);
  background: rgba(15, 23, 42, 0.7);
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 212, 255, 0.08);
}

.gang-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gang-name {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.gang-metrics {
  display: flex;
  gap: 20px;
}

.gang-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gang-metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
}

.gang-metric-label {
  font-size: 11px;
  color: #64748b;
}

.gang-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
  border-top: 1px solid rgba(255,255,255,0.04);
}

.gangs-section .el-table { margin-top: 0; }

.empty-state { text-align: center; padding: 60px 20px; }

.empty-content { display: flex; flex-direction: column; align-items: center; gap: 16px; }

.empty-icon { font-size: 64px; opacity: 0.5; }

.empty-title { font-size: 20px; color: var(--text-primary); font-weight: 600; margin: 0; }

.empty-desc { font-size: 14px; color: var(--text-muted); max-width: 400px; }

@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>