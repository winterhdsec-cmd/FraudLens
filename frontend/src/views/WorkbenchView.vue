<template>
  <div class="workbench-view">
    <!-- 顶部：案件选择 + 状态横幅 -->
    <div class="wb-header">
      <div class="wb-title">
        <h2>办案工作台</h2>
        <span class="wb-subtitle">立案 → 研判 → 复核 → 止付 → 审批 → 结案 全流程</span>
      </div>
      <div class="wb-case-picker">
        <el-select
          v-model="selectedCaseId"
          placeholder="选择案件"
          filterable
          clearable
          style="width: 320px"
          @change="onCaseChange"
        >
          <el-option
            v-for="c in caseList"
            :key="c.case_id"
            :label="`${c.case_id} · ${c.title || c.scam_type || '未命名'}`"
            :value="c.case_id"
          />
        </el-select>
      </div>
    </div>

    <div v-if="!selectedCaseId" class="wb-empty">
      <el-empty description="请选择一个案件以开始办案流程" />
    </div>

    <div v-else class="wb-body">
      <!-- 案件台卡 + 状态机 -->
      <el-card class="wb-card case-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="card-title">案件台卡</span>
            <el-tag :type="statusTagType(lifecycle.current_status)" size="large">
              {{ lifecycle.current_status || '待立案' }}
            </el-tag>
          </div>
        </template>
        <div v-if="caseInfo" class="case-meta">
          <div class="meta-row"><span class="meta-label">案件编号</span><span>{{ caseInfo.case_id }}</span></div>
          <div class="meta-row"><span class="meta-label">案件名称</span><span>{{ caseInfo.title || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">诈骗类型</span><span>{{ caseInfo.scam_type || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">受害人</span><span>{{ caseInfo.victim_name || '—' }} {{ caseInfo.victim_phone || '' }}</span></div>
          <div class="meta-row"><span class="meta-label">涉案金额</span><span class="amount">{{ caseInfo.amount || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">风险等级</span>
            <el-tag :type="riskTagType(caseInfo.risk_level)" size="small">{{ caseInfo.risk_label || caseInfo.risk_level }}</el-tag>
          </div>
        </div>
        <!-- 状态流转按钮 -->
        <div class="transition-bar">
          <span class="bar-label">流转到：</span>
          <el-button
            v-for="s in lifecycle.available_transitions || []"
            :key="s"
            size="small"
            :type="statusBtnType(s)"
            @click="onTransition(s)"
          >{{ s }}</el-button>
          <span v-if="!lifecycle.available_transitions?.length" class="muted">已终态（归档）</span>
        </div>
      </el-card>

      <!-- Tab 区：研判 / 止付冻结 / 复核 / 审批 / 时间线 -->
      <el-card class="wb-card" shadow="never">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <!-- 研判任务 -->
          <el-tab-pane label="研判任务" name="investigation">
            <div class="tab-toolbar">
              <el-button type="primary" :loading="invLoading" @click="onRunInvestigation">
                <el-icon><MagicStick /></el-icon> 发起研判
              </el-button>
              <el-button @click="loadInvestigations">刷新列表</el-button>
            </div>
            <el-table :data="investigations" stripe size="small" style="margin-top: 12px">
              <el-table-column prop="task_id" label="任务ID" width="220" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="invStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度" width="100">
                <template #default="{ row }">{{ row.confidence != null ? (row.confidence * 100).toFixed(1) + '%' : '—' }}</template>
              </el-table-column>
              <el-table-column prop="gate_decision" label="门控决策" width="140" />
              <el-table-column prop="operator_name" label="研判人" width="120" />
              <el-table-column prop="created_at" label="时间" width="160">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="{ row }">
                  <el-button link size="small" @click="viewInvestigation(row)">详情</el-button>
                  <el-button link size="small" @click="downloadReport(row.task_id)">报告</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 止付冻结工单 -->
          <el-tab-pane label="止付冻结" name="freeze">
            <div class="tab-toolbar">
              <el-button type="primary" @click="showFreezeDialog = true">
                <el-icon><Plus /></el-icon> 新建工单
              </el-button>
              <el-button @click="loadFreezeOrders">刷新</el-button>
            </div>
            <el-table :data="freezeOrders" stripe size="small" style="margin-top: 12px">
              <el-table-column prop="order_id" label="工单ID" width="220" />
              <el-table-column prop="action_type" label="类型" width="80" />
              <el-table-column prop="status" label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="freezeStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="freeze_amount" label="金额" width="120">
                <template #default="{ row }">{{ row.freeze_amount ? '¥' + Number(row.freeze_amount).toLocaleString() : '—' }}</template>
              </el-table-column>
              <el-table-column label="账户数" width="80">
                <template #default="{ row }">{{ (row.target_accounts || []).length }}</template>
              </el-table-column>
              <el-table-column prop="applicant_name" label="申请人" width="100" />
              <el-table-column prop="created_at" label="创建时间" width="160">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="240">
                <template #default="{ row }">
                  <el-button link size="small" @click="viewFreezeOrder(row)">详情</el-button>
                  <el-button v-if="row.status === 'draft' || row.status === 'rejected'" link size="small" type="primary" @click="onSubmitFreeze(row)">提交审批</el-button>
                  <el-button link size="small" @click="onDownloadFreezeDoc(row)">文书</el-button>
                  <el-button v-if="row.status === 'draft' || row.status === 'pending_approval'" link size="small" type="danger" @click="onCancelFreeze(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 复核任务 -->
          <el-tab-pane label="HITL 复核" name="review">
            <div class="tab-toolbar">
              <el-button @click="loadReviews">刷新</el-button>
              <el-radio-group v-model="reviewStatusFilter" size="small" @change="loadReviews">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="pending">待分派</el-radio-button>
                <el-radio-button label="assigned">已分派</el-radio-button>
                <el-radio-button label="resolved">已完成</el-radio-button>
              </el-radio-group>
            </div>
            <el-table :data="reviews" stripe size="small" style="margin-top: 12px">
              <el-table-column prop="review_id" label="复核ID" width="220" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="reviewStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="original_gate_decision" label="原决策" width="120" />
              <el-table-column prop="confidence" label="置信度" width="100">
                <template #default="{ row }">{{ row.confidence != null ? (row.confidence * 100).toFixed(1) + '%' : '—' }}</template>
              </el-table-column>
              <el-table-column prop="assigned_to_name" label="复核人" width="120" />
              <el-table-column prop="review_result" label="结论" width="160" />
              <el-table-column label="操作" width="160">
                <template #default="{ row }">
                  <el-button link size="small" @click="viewReview(row)">详情</el-button>
                  <el-button v-if="row.status !== 'resolved'" link size="small" type="primary" @click="onResolveReview(row)">处理</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 审批流 -->
          <el-tab-pane label="审批中心" name="approval">
            <div class="tab-toolbar">
              <el-button @click="loadPendingApprovals">刷新待我审批</el-button>
              <el-button @click="showAllApprovals = !showAllApprovals; showAllApprovals && loadAllApprovals()">
                {{ showAllApprovals ? '查看待我审批' : '查看全部审批' }}
              </el-button>
            </div>
            <el-table :data="approvals" stripe size="small" style="margin-top: 12px">
              <el-table-column prop="flow_id" label="审批流ID" width="220" />
              <el-table-column prop="business_type" label="业务类型" width="120" />
              <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip />
              <el-table-column prop="current_level" label="当前层级" width="100" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="approvalStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="applicant_name" label="申请人" width="100" />
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'pending'" link size="small" type="success" @click="onApprove(row)">通过</el-button>
                  <el-button v-if="row.status === 'pending'" link size="small" type="danger" @click="onReject(row)">驳回</el-button>
                  <el-button link size="small" @click="viewApproval(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 时间线 -->
          <el-tab-pane label="办案时间线" name="timeline">
            <el-timeline v-if="timeline.length">
              <el-timeline-item
                v-for="(e, idx) in timeline"
                :key="idx"
                :timestamp="formatTime(e.time)"
                :type="timelineType(e.type)"
                placement="top"
              >
                <h4>{{ e.title || e.type }}</h4>
                <p v-if="e.operator" class="muted">操作人：{{ e.operator }}</p>
                <p v-if="e.reason" class="muted">事由：{{ e.reason }}</p>
                <p v-if="e.status" class="muted">状态：{{ e.status }}</p>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无时间线数据" />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 新建止付工单对话框 -->
    <el-dialog v-model="showFreezeDialog" title="新建止付/冻结工单" width="640px">
      <el-form :model="freezeForm" label-width="100px">
        <el-form-item label="动作类型">
          <el-radio-group v-model="freezeForm.action_type">
            <el-radio label="止付">止付</el-radio>
            <el-radio label="冻结">冻结</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="冻结金额">
          <el-input-number v-model="freezeForm.freeze_amount" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="法律依据">
          <el-input v-model="freezeForm.legal_basis" type="textarea" :rows="2"
            placeholder="《中华人民共和国反电信网络诈骗法》第十一条、第十二条" />
        </el-form-item>
        <el-form-item label="事由">
          <el-input v-model="freezeForm.reason" type="textarea" :rows="3"
            placeholder="涉案资金需要紧急止付/冻结，防止资金转移" />
        </el-form-item>
        <el-form-item label="目标账户">
          <div v-for="(acc, i) in freezeForm.target_accounts" :key="i" class="acc-row">
            <el-input v-model="acc.account_number" placeholder="账号" style="width: 200px" />
            <el-input v-model="acc.account_name" placeholder="户名" style="width: 120px; margin-left: 8px" />
            <el-input v-model="acc.bank_name" placeholder="开户行" style="width: 160px; margin-left: 8px" />
            <el-button link type="danger" @click="freezeForm.target_accounts.splice(i, 1)" style="margin-left: 8px">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button link type="primary" @click="freezeForm.target_accounts.push({ account_number: '', account_name: '', bank_name: '' })">
            <el-icon><Plus /></el-icon> 添加账户
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFreezeDialog = false">取消</el-button>
        <el-button type="primary" :loading="freezeSubmitting" @click="onSubmitNewFreeze">创建工单</el-button>
      </template>
    </el-dialog>

    <!-- 审批对话框 -->
    <el-dialog v-model="showApprovalDialog" :title="approvalAction === 'approve' ? '审批通过' : '驳回审批'" width="480px">
      <el-form>
        <el-form-item label="审批意见">
          <el-input v-model="approvalComment" type="textarea" :rows="4" placeholder="请输入审批意见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApprovalDialog = false">取消</el-button>
        <el-button :type="approvalAction === 'approve' ? 'success' : 'danger'" @click="onConfirmApproval">确认</el-button>
      </template>
    </el-dialog>

    <!-- 复核处理对话框 -->
    <el-dialog v-model="showReviewDialog" title="处理复核任务" width="560px">
      <el-form :model="reviewForm" label-width="100px">
        <el-form-item label="结论">
          <el-select v-model="reviewForm.review_result" placeholder="选择复核结论" style="width: 100%">
            <el-option label="确认合并（维持原研判）" value="confirmed_merge" />
            <el-option label="拆分团伙" value="split_gang" />
            <el-option label="修正诈骗类型" value="corrected_type" />
            <el-option label="补充实体" value="supplemented_entity" />
            <el-option label="标记误报" value="false_positive" />
          </el-select>
        </el-form-item>
        <el-form-item label="意见">
          <el-input v-model="reviewForm.comment" type="textarea" :rows="3" placeholder="复核意见" />
        </el-form-item>
        <el-form-item label="触发再分析">
          <el-switch v-model="reviewForm.trigger_reanalysis" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="primary" @click="onConfirmReview">完成复核</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Plus, Delete } from '@element-plus/icons-vue'
import {
  getCaseLifecycle, transitionCaseStatus, getCaseTimeline,
  listInvestigations, createInvestigation, downloadInvestigationReport,
  listFreezeOrders, createFreezeOrder, submitFreezeOrder, cancelFreezeOrder,
  downloadFreezeDoc,
  listReviews, resolveReview,
  listPendingApprovals, listApprovals, approveFlow, rejectFlow,
} from '../api.js'
import { useAppState } from '../composables/useAppState.js'

const appState = useAppState()
const route = useRoute()

// ── 案件选择 ──
const selectedCaseId = ref('')
const caseList = computed(() => appState.cases || [])
const caseInfo = computed(() => caseList.value.find(c => c.case_id === selectedCaseId.value) || null)

// ── 生命周期 ──
const lifecycle = reactive({
  current_status: '',
  available_transitions: [],
  all_statuses: [],
  timeline: [],
})

// ── Tab 状态 ──
const activeTab = ref('investigation')

// ── 研判 ──
const investigations = ref([])
const invLoading = ref(false)

// ── 止付冻结 ──
const freezeOrders = ref([])
const showFreezeDialog = ref(false)
const freezeSubmitting = ref(false)
const freezeForm = reactive({
  action_type: '冻结',
  freeze_amount: 0,
  legal_basis: '《中华人民共和国反电信网络诈骗法》第十一条、第十二条',
  reason: '涉案资金需要紧急止付/冻结，防止资金转移',
  target_accounts: [{ account_number: '', account_name: '', bank_name: '' }],
})

// ── 复核 ──
const reviews = ref([])
const reviewStatusFilter = ref('')
const showReviewDialog = ref(false)
const reviewForm = reactive({ review_result: '', comment: '', trigger_reanalysis: false })
const currentReviewId = ref('')

// ── 审批 ──
const approvals = ref([])
const showAllApprovals = ref(false)
const showApprovalDialog = ref(false)
const approvalAction = ref('approve')
const approvalComment = ref('')
const currentFlowId = ref('')

// ── 时间线 ──
const timeline = ref([])

// ── 方法 ──
function onCaseChange(caseId) {
  if (!caseId) return
  loadLifecycle(caseId)
  loadTimeline(caseId)
  // 重置各 tab 数据
  investigations.value = []
  freezeOrders.value = []
  reviews.value = []
  approvals.value = []
}

async function loadLifecycle(caseId) {
  try {
    const res = await getCaseLifecycle(caseId)
    if (res.success) {
      lifecycle.current_status = res.current_status
      lifecycle.available_transitions = res.available_transitions || []
      lifecycle.all_statuses = res.all_statuses || []
    }
  } catch (e) {
    console.error('加载生命周期失败', e)
  }
}

async function loadTimeline(caseId) {
  try {
    const res = await getCaseTimeline(caseId)
    if (res.success) {
      timeline.value = res.timeline || []
    }
  } catch (e) {
    console.error('加载时间线失败', e)
  }
}

async function onTransition(toStatus) {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      `确认将案件流转到「${toStatus}」状态？`, '状态流转',
      { inputPlaceholder: '流转事由（可选）', inputType: 'textarea' }
    )
    const res = await transitionCaseStatus(selectedCaseId.value, toStatus, reason || '')
    if (res.success) {
      ElMessage.success(`已流转到：${toStatus}`)
      await loadLifecycle(selectedCaseId.value)
      await loadTimeline(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '流转失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('流转失败：' + (e.message || e))
    }
  }
}

function onTabChange(tab) {
  if (!selectedCaseId.value) return
  if (tab === 'investigation' && !investigations.value.length) loadInvestigations()
  else if (tab === 'freeze' && !freezeOrders.value.length) loadFreezeOrders()
  else if (tab === 'review' && !reviews.value.length) loadReviews()
  else if (tab === 'approval' && !approvals.value.length) loadPendingApprovals()
}

async function loadInvestigations() {
  if (!selectedCaseId.value) return
  try {
    const res = await listInvestigations(selectedCaseId.value)
    if (res.success) investigations.value = res.tasks || []
  } catch (e) {
    console.error('加载研判任务失败', e)
  }
}

async function onRunInvestigation() {
  if (!selectedCaseId.value) return
  invLoading.value = true
  try {
    ElMessage.info('正在调用研判引擎，请稍候...')
    const res = await createInvestigation(selectedCaseId.value, { use_gnn: true })
    if (res.success) {
      ElMessage.success(`研判完成：置信度 ${(res.confidence * 100).toFixed(1)}%，决策：${res.gate_decision}`)
      await loadInvestigations()
      await loadTimeline(selectedCaseId.value)
      await loadLifecycle(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '研判失败')
    }
  } catch (e) {
    ElMessage.error('研判失败：' + (e.message || e))
  } finally {
    invLoading.value = false
  }
}

function viewInvestigation(row) {
  ElMessageBox.alert(JSON.stringify(row, null, 2), `研判任务 ${row.task_id}`, { customClass: 'json-dialog' })
}

async function downloadReport(taskId) {
  try {
    const res = await downloadInvestigationReport(taskId, 'pdf')
    const blob = new Blob([res.data], { type: res.headers['content-type'] })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `研判报告_${taskId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载报告失败：' + (e.message || e))
  }
}

async function loadFreezeOrders() {
  if (!selectedCaseId.value) return
  try {
    const res = await listFreezeOrders(selectedCaseId.value)
    if (res.success) freezeOrders.value = res.orders || []
  } catch (e) {
    console.error('加载止付工单失败', e)
  }
}

async function onSubmitNewFreeze() {
  if (!freezeForm.target_accounts.filter(a => a.account_number).length) {
    ElMessage.warning('请至少添加一个目标账户')
    return
  }
  freezeSubmitting.value = true
  try {
    const payload = {
      case_id: selectedCaseId.value,
      action_type: freezeForm.action_type,
      freeze_amount: freezeForm.freeze_amount,
      legal_basis: freezeForm.legal_basis,
      reason: freezeForm.reason,
      target_accounts: freezeForm.target_accounts.filter(a => a.account_number),
    }
    const res = await createFreezeOrder(payload)
    if (res.success) {
      ElMessage.success(`工单已创建：${res.order.order_id}`)
      showFreezeDialog.value = false
      await loadFreezeOrders()
      await loadTimeline(selectedCaseId.value)
      // 重置表单
      freezeForm.freeze_amount = 0
      freezeForm.target_accounts = [{ account_number: '', account_name: '', bank_name: '' }]
    } else {
      ElMessage.error(res.error || '创建失败')
    }
  } catch (e) {
    ElMessage.error('创建失败：' + (e.message || e))
  } finally {
    freezeSubmitting.value = false
  }
}

async function onSubmitFreeze(row) {
  try {
    await ElMessageBox.confirm(`提交工单 ${row.order_id} 进入审批流程？`, '提交审批', { type: 'info' })
    const res = await submitFreezeOrder(row.order_id, null)
    if (res.success) {
      ElMessage.success(`已提交审批，审批流：${res.flow_id}`)
      await loadFreezeOrders()
      await loadTimeline(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '提交失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('提交失败：' + (e.message || e))
  }
}

async function onCancelFreeze(row) {
  try {
    const { value: reason } = await ElMessageBox.prompt('撤销原因', '撤销工单', { inputPlaceholder: '撤销原因' })
    const res = await cancelFreezeOrder(row.order_id, reason || '')
    if (res.success) {
      ElMessage.success('已撤销')
      await loadFreezeOrders()
      await loadTimeline(selectedCaseId.value)
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('撤销失败：' + (e.message || e))
  }
}

function viewFreezeOrder(row) {
  ElMessageBox.alert(JSON.stringify(row, null, 2), `工单 ${row.order_id}`, { customClass: 'json-dialog' })
}

async function onDownloadFreezeDoc(row) {
  try {
    const res = await downloadFreezeDoc(row.order_id, 'pdf')
    const blob = new Blob([res.data], { type: res.headers['content-type'] })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `止付冻结文书_${row.order_id}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载文书失败：' + (e.message || e))
  }
}

async function loadReviews() {
  if (!selectedCaseId.value) return
  try {
    const res = await listReviews(selectedCaseId.value, reviewStatusFilter.value)
    if (res.success) reviews.value = res.reviews || []
  } catch (e) {
    console.error('加载复核任务失败', e)
  }
}

function onResolveReview(row) {
  currentReviewId.value = row.review_id
  reviewForm.review_result = ''
  reviewForm.comment = ''
  reviewForm.trigger_reanalysis = false
  showReviewDialog.value = true
}

async function onConfirmReview() {
  if (!reviewForm.review_result) {
    ElMessage.warning('请选择复核结论')
    return
  }
  try {
    const res = await resolveReview(currentReviewId.value, {
      review_result: reviewForm.review_result,
      comment: reviewForm.comment,
      trigger_reanalysis: reviewForm.trigger_reanalysis,
    })
    if (res.success) {
      ElMessage.success('复核已完成')
      showReviewDialog.value = false
      await loadReviews()
      await loadTimeline(selectedCaseId.value)
    }
  } catch (e) {
    ElMessage.error('复核失败：' + (e.message || e))
  }
}

function viewReview(row) {
  ElMessageBox.alert(JSON.stringify(row, null, 2), `复核 ${row.review_id}`, { customClass: 'json-dialog' })
}

async function loadPendingApprovals() {
  try {
    const res = await listPendingApprovals()
    if (res.success) approvals.value = res.flows || []
  } catch (e) {
    console.error('加载待审批失败', e)
  }
}

async function loadAllApprovals() {
  try {
    const res = await listApprovals('', '', 100)
    if (res.success) approvals.value = res.flows || []
  } catch (e) {
    console.error('加载审批列表失败', e)
  }
}

function onApprove(row) {
  currentFlowId.value = row.flow_id
  approvalAction.value = 'approve'
  approvalComment.value = ''
  showApprovalDialog.value = true
}

function onReject(row) {
  currentFlowId.value = row.flow_id
  approvalAction.value = 'reject'
  approvalComment.value = ''
  showApprovalDialog.value = true
}

async function onConfirmApproval() {
  try {
    const fn = approvalAction.value === 'approve' ? approveFlow : rejectFlow
    const res = await fn(currentFlowId.value, approvalComment.value)
    if (res.success) {
      ElMessage.success(approvalAction.value === 'approve' ? '已通过' : '已驳回')
      showApprovalDialog.value = false
      if (showAllApprovals.value) await loadAllApprovals()
      else await loadPendingApprovals()
      await loadTimeline(selectedCaseId.value)
    }
  } catch (e) {
    ElMessage.error('审批失败：' + (e.message || e))
  }
}

function viewApproval(row) {
  ElMessageBox.alert(JSON.stringify(row, null, 2), `审批流 ${row.flow_id}`, { customClass: 'json-dialog' })
}

// ── 工具函数 ──
function formatTime(s) {
  if (!s) return '—'
  try {
    const d = new Date(s)
    if (isNaN(d.getTime())) return s
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch { return s }
}

function statusTagType(s) {
  const map = { '待立案': 'info', '已立案': '', '侦查中': 'warning', '待研判': 'info', '研判中': 'warning', '研判完成': 'success', '待结案': 'warning', '已归档': 'info' }
  return map[s] || 'info'
}

function statusBtnType(s) {
  const map = { '已立案': 'primary', '侦查中': 'warning', '研判中': 'warning', '研判完成': 'success', '待结案': 'warning', '已归档': 'info' }
  return map[s] || 'default'
}

function riskTagType(r) {
  const map = { 'HIGH': 'danger', 'S': 'danger', 'CRITICAL': 'danger', 'MEDIUM': 'warning', 'LOW': 'info' }
  return map[(r || '').toUpperCase()] || 'info'
}

function invStatusType(s) {
  return { running: 'warning', completed: 'success', failed: 'danger' }[s] || 'info'
}

function freezeStatusType(s) {
  return { draft: 'info', pending_approval: 'warning', approved: 'success', rejected: 'danger', executed: 'success', partial: 'warning', failed: 'danger', cancelled: 'info' }[s] || 'info'
}

function reviewStatusType(s) {
  return { pending: 'info', assigned: 'warning', in_review: 'warning', resolved: 'success' }[s] || 'info'
}

function approvalStatusType(s) {
  return { pending: 'warning', approved: 'success', rejected: 'danger', cancelled: 'info' }[s] || 'info'
}

function timelineType(t) {
  return { status_transition: 'primary', investigation: 'warning', freeze_order: 'danger', review: 'success' }[t] || 'info'
}

onMounted(() => {
  // 读取路由 query 参数 case_id，自动选中案件（来自案件详情页"进入工作台"入口）
  const qCaseId = route.query.case_id
  if (qCaseId) {
    trySelectCase(String(qCaseId))
  }
})

// 案件列表异步加载完成后，若仍未选中但 query 携带了 case_id，则补选一次
watch(caseList, (list) => {
  if (!selectedCaseId.value && route.query.case_id && list.length) {
    trySelectCase(String(route.query.case_id))
  }
}, { immediate: true })

function trySelectCase(cid) {
  // 等待案件列表就绪后再选；若列表暂无此 id，保留 selectedCaseId 以便列表加载后匹配
  selectedCaseId.value = cid
  if (caseList.value.length && caseList.value.find(c => c.case_id === cid)) {
    onCaseChange(cid)
  } else {
    // 列表未就绪：先加载生命周期/时间线，待 watch 触发后再补 onCaseChange
    loadLifecycle(cid)
    loadTimeline(cid)
  }
}
</script>

<style scoped>
.workbench-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── 顶部标题区 ── */
.wb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.08), rgba(139, 92, 246, 0.05));
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.wb-title h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.wb-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 6px;
  display: block;
  letter-spacing: 0.5px;
}

.wb-empty {
  padding: 100px 0;
}

/* ── 卡片 ── */
.wb-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.wb-card {
  background: var(--bg-card);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: var(--radius-lg);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.wb-card:hover {
  border-color: rgba(0, 212, 255, 0.25);
  box-shadow: 0 4px 24px rgba(0, 212, 255, 0.08);
}

/* 案件台卡特殊样式 */
.case-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(20, 30, 55, 0.85));
  border-left: 3px solid var(--accent-cyan);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  background: var(--accent-cyan);
  border-radius: 2px;
}

/* ── 案件元信息 ── */
.case-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 32px;
}

.meta-row {
  display: flex;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.meta-label {
  width: 80px;
  color: var(--text-muted);
  flex-shrink: 0;
  font-size: 12px;
}

.meta-row .amount {
  color: var(--accent-red);
  font-weight: 700;
  font-size: 14px;
}

/* ── 状态流转按钮区 ── */
.transition-bar {
  margin-top: 20px;
  padding: 16px 20px;
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.bar-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.transition-bar :deep(.el-button) {
  transition: all 0.25s ease;
}

.transition-bar :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 12px rgba(0, 212, 255, 0.2);
}

/* ── Tab 工具栏 ── */
.tab-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: rgba(0, 212, 255, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 212, 255, 0.06);
}

/* ── 账户输入行 ── */
.acc-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-sm);
}

/* ── 辅助文本 ── */
.muted {
  color: var(--text-muted);
  font-size: 12px;
  margin: 3px 0;
}

/* ── Tab 样式 ── */
:deep(.el-tabs__header) {
  margin-bottom: 16px;
}

:deep(.el-tabs__item) {
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s ease;
}

:deep(.el-tabs__item.is-active) {
  color: var(--accent-cyan);
  font-weight: 600;
}

:deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  height: 3px;
  border-radius: 2px;
}

:deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(0, 212, 255, 0.08);
}

/* ── 表格 ── */
:deep(.el-table) {
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: rgba(0, 212, 255, 0.06);
  color: var(--text-primary);
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
}

:deep(.el-table tr) {
  background: transparent;
  transition: background 0.2s ease;
}

:deep(.el-table tr:hover > td) {
  background: rgba(0, 212, 255, 0.04) !important;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 13px;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.015);
}

/* ── 卡片头部 ── */
:deep(.el-card__header) {
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  padding: 16px 20px;
}

:deep(.el-card__body) {
  padding: 20px;
}

/* ── 时间线美化 ── */
:deep(.el-timeline-item__timestamp) {
  color: var(--text-muted);
  font-size: 12px;
}

:deep(.el-timeline-item__node) {
  box-shadow: 0 0 8px currentColor;
}

:deep(.el-timeline-item__tail) {
  border-left-style: dashed;
  border-left-color: rgba(0, 212, 255, 0.15);
}

:deep(.el-timeline-item h4) {
  color: var(--text-primary);
  font-size: 14px;
  margin: 0 0 4px 0;
}

/* ── 空状态 ── */
:deep(.el-empty__description) {
  color: var(--text-muted);
}

/* ── 对话框 ── */
:deep(.el-dialog) {
  background: var(--bg-card);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: var(--radius-lg);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

:deep(.el-dialog__title) {
  color: var(--text-primary);
  font-weight: 600;
}

/* ── 选择器 ── */
:deep(.el-select .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.04);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.15) inset;
}

:deep(.el-select .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--accent-cyan) inset;
}

:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--accent-cyan) inset, 0 0 12px rgba(0, 212, 255, 0.15);
}
</style>
