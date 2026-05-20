<template>
<div class="view-section">
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
    <div v-if="!capitalFlows.length && !flowSearchCaseId" class="empty-state" style="margin-bottom:16px">
      <div class="empty-content">
        <div class="empty-icon">💰</div>
        <h3 class="empty-title">暂无资金流向数据</h3>
        <p class="empty-desc">输入案件编号查询资金流转链路，系统将自动分析资金去向</p>
      </div>
    </div>
    <template v-else>
      <div class="network-container tech-card" style="height:400px;min-height:400px">
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
    </template>
  </div>
</div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import NetworkGraph from '../components/NetworkGraph.vue'
const state = useAppState()
const {
  activeMenu, capitalFlows, flowGraphData, flowSearchCaseId, loadFlowData, addFlowRecord
} = state

onMounted(() => {
  loadFlowData()
})
</script>