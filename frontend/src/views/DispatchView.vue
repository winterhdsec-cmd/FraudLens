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
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{row}">
                  <div style="display:flex;gap:8px">
                    <el-button v-if="row.status==='pending'" size="small" type="primary" @click="signDispatch(row.id)">签收</el-button>
                    <el-button v-if="row.status==='signed'" size="small" type="success" @click="showCompleteDispatch(row)">完成反馈</el-button>
                  </div>
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

          <el-dialog v-model="showFeedbackDialog" title="完成派单" width="480px" class="feedback-dialog">
            <div class="feedback-form">
              <label class="feedback-label">处置反馈内容</label>
              <textarea
                v-model="feedbackForm.text"
                rows="5"
                placeholder="请描述处置情况..."
                class="native-feedback-textarea"
              ></textarea>
            </div>
            <template #footer>
              <el-button @click="showFeedbackDialog = false">取消</el-button>
              <el-button type="primary" @click="submitFeedback">提交反馈</el-button>
            </template>
          </el-dialog>
        </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, dispatchOrders, dispatchStatusFilter, loadDispatchOrders, showCreateDispatch,
  signDispatch, showCompleteDispatch, showFeedbackDialog, feedbackForm, submitFeedback
} = state

onMounted(() => loadDispatchOrders())
</script>

<style scoped>
.dispatch-list .el-table .cell {
  position: relative;
}

.dispatch-list .el-table tr td:first-child .cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 3px;
  border-radius: 2px;
}

.native-feedback-textarea {
  width: 100%;
  padding: 12px 14px;
  background: rgba(10, 14, 26, 0.6);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
}
.native-feedback-textarea::placeholder {
  color: #475569;
}
.native-feedback-textarea:focus {
  border-color: rgba(0, 198, 255, 0.5);
  box-shadow: 0 0 10px rgba(0, 198, 255, 0.15);
}
.feedback-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.feedback-form {
  position: relative;
}

.char-count {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 11px;
  color: var(--text-muted);
}
</style>
