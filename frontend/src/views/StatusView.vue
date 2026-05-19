<template>
<div class="view-section">
  <div class="section-header">
    <div class="header-left">
      <h2 class="section-title">
        <span class="title-icon">📊</span>
        系统数据监控
      </h2>
      <p class="section-desc">实时监控各功能模块数据接入状态</p>
    </div>
    <div class="header-right">
      <el-button size="small" @click="refreshAll" :loading="refreshing">
        <span>🔄</span> 刷新
      </el-button>
    </div>
  </div>

  <div class="monitor-grid">
    <div v-for="module in modules" :key="module.key" class="monitor-card tech-card" :class="{ warning: module.status === 'warning', error: module.status === 'error' }">
      <div class="monitor-header">
        <span class="monitor-icon">{{ module.icon }}</span>
        <span class="monitor-name">{{ module.name }}</span>
        <el-tag :type="module.status === 'ok' ? 'success' : module.status === 'warning' ? 'warning' : 'danger'" size="small" effect="dark">
          {{ module.status === 'ok' ? '正常' : module.status === 'warning' ? '数据不足' : '异常' }}
        </el-tag>
      </div>
      <div class="monitor-body">
        <div class="monitor-stat">
          <span class="stat-value">{{ module.count }}</span>
          <span class="stat-label">{{ module.unit }}</span>
        </div>
        <div class="monitor-time">
          <span class="time-label">更新时间</span>
          <span class="time-value">{{ module.updatedAt }}</span>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const modules = ref([])
const refreshing = ref(false)

const refreshAll = async () => {
  refreshing.value = true
  try {
    const { fetchCases, fetchGangs, getDashboardData, getActiveAlerts } = await import('../api.js')
    const [cr, gr, dr, ar] = await Promise.all([
      fetchCases(), fetchGangs(), getDashboardData(), getActiveAlerts()
    ])

    const now = new Date().toLocaleString('zh-CN')
    const toStatus = (count, min=1) => count >= min ? 'ok' : count > 0 ? 'warning' : 'error'

    modules.value = [
      { key: 'cases', icon: '📋', name: '案件数据', count: cr.total || 0, unit: '条', status: toStatus(cr.total||0, 5), updatedAt: now },
      { key: 'gangs', icon: '👥', name: '团伙数据', count: gr.total || 0, unit: '个', status: toStatus(gr.total||0, 1), updatedAt: now },
      { key: 'dashboard', icon: '📊', name: '数据看板', count: dr.data?.total_cases || 0, unit: '案', status: toStatus(dr.data?.total_cases||0, 1), updatedAt: now },
      { key: 'alerts', icon: '🔔', name: '预警中心', count: ar.alerts?.length || 0, unit: '条', status: toStatus(ar.alerts?.length||0, 1), updatedAt: now },
      { key: 'search', icon: '🔍', name: '全文搜索', count: 0, unit: '功能', status: 'ok', updatedAt: now },
    ]
  } catch (e) {
    ElMessage.error('获取状态失败: ' + e.message)
  } finally {
    refreshing.value = false
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.monitor-card {
  padding: 20px;
  border-radius: 8px;
  background: rgba(0, 198, 255, 0.03);
  border: 1px solid rgba(0, 198, 255, 0.1);
  transition: all 0.3s;
}
.monitor-card:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,198,255,0.1); }
.monitor-card.warning { border-color: rgba(245,158,11,0.5); }
.monitor-card.error { border-color: rgba(239,68,68,0.5); }
.monitor-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.monitor-icon { font-size: 24px; }
.monitor-name { font-size: 15px; font-weight: 600; color: #e2e8f0; flex: 1; }
.monitor-body { display: flex; justify-content: space-between; align-items: flex-end; }
.monitor-stat { display: flex; flex-direction: column; }
.stat-value { font-size: 28px; font-weight: 700; color: #00d4ff; }
.stat-label { font-size: 12px; color: #94a3b8; }
.monitor-time { text-align: right; }
.time-label { display: block; font-size: 11px; color: #64748b; }
.time-value { font-size: 12px; color: #94a3b8; }
</style>