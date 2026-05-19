<template>
<div class="view-section">
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
          <div v-if="!dispatchOrders.length && !dispatchStatusFilter" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">📋</div>
              <h3 class="empty-title">暂无派单记录</h3>
              <p class="empty-desc">预警生成后，系统将自动创建派单并分配到辖区</p>
            </div>
          </div>
        </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, dispatchOrders, dispatchStatusFilter, loadDispatchOrders, showCreateDispatch
} = state
</script>
