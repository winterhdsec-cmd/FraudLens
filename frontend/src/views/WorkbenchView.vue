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
                  <el-button v-if="row.status === 'failed' || row.status === 'partial'" link size="small" type="warning" @click="onExecuteFreeze(row)">执行重试</el-button>
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

          <!-- 串并案建议 -->
          <el-tab-pane label="并案建议" name="merge">
            <div class="tab-toolbar">
              <el-button type="primary" :loading="mergeLoading" @click="onGenerateMerges">
                <el-icon><MagicStick /></el-icon> AI 重新发现
              </el-button>
              <el-button @click="loadMerges">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
              <el-radio-group v-model="mergeStatusFilter" size="small" @change="loadMerges">
                <el-radio-button label="pending">待研判 {{ mergeSummary.pending || 0 }}</el-radio-button>
                <el-radio-button label="approved">已采纳 {{ mergeSummary.approved || 0 }}</el-radio-button>
                <el-radio-button label="rejected">已驳回 {{ mergeSummary.rejected || 0 }}</el-radio-button>
                <el-radio-button label="all">全部 {{ mergeSummary.total || 0 }}</el-radio-button>
              </el-radio-group>
            </div>

            <div v-if="mergeError" class="merge-error">
              <el-icon><WarningFilled /></el-icon> 并案建议加载失败：{{ mergeError }}
            </div>

            <el-table v-loading="mergeLoading" :data="merges" stripe size="small" style="margin-top: 12px">
              <el-table-column label="相似度" width="96" align="center">
                <template #default="{ row }">
                  <span class="sim-badge" :class="simClass(row.similarity)">{{ (row.similarity * 100).toFixed(1) }}%</span>
                </template>
              </el-table-column>
              <el-table-column label="案件 A" min-width="200">
                <template #default="{ row }">
                  <div class="merge-case">
                    <el-button link type="primary" size="small" @click="openCase(row.case_id_a)">{{ row.case_id_a }}</el-button>
                    <span class="mc-title">{{ row.case_a_title || '—' }}</span>
                    <span class="mc-sub">受害人：{{ row.case_a_victim || '—' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="案件 B" min-width="200">
                <template #default="{ row }">
                  <div class="merge-case">
                    <el-button link type="primary" size="small" @click="openCase(row.case_id_b)">{{ row.case_id_b }}</el-button>
                    <span class="mc-title">{{ row.case_b_title || '—' }}</span>
                    <span class="mc-sub">受害人：{{ row.case_b_victim || '—' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="并案依据" min-width="220" show-overflow-tooltip />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="mergeStatusType(row.status)" size="small">{{ mergeStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核" width="150">
                <template #default="{ row }">
                  <span v-if="row.status === 'pending'" class="muted">待人工复核</span>
                  <span v-else class="mc-sub">{{ formatTime(row.reviewed_at) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <template v-if="row.status === 'pending'">
                    <el-button link size="small" type="success" @click="onAdoptMerge(row)">采纳</el-button>
                    <el-button link size="small" type="danger" @click="onRejectMerge(row)">驳回</el-button>
                  </template>
                  <el-button link size="small" @click="openCase(row.case_id_a)">查看</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty :description="mergeStatusFilter === 'pending' ? '暂无待研判的并案建议' : '暂无数据'" :image-size="80" />
              </template>
            </el-table>
            <p class="merge-hint">
              采纳后两起案件将建立同一团伙关联（不覆盖原案情）；驳回仅登记研判结论，可在「全部」中回溯。
            </p>
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

    <!-- 冻结工单详情：基本信息 + 审批链 + 执行回执 -->
    <el-dialog v-model="showFreezeDetail" :title="`冻结工单详情 · ${freezeDetail.order?.order_id || ''}`" width="860px" top="6vh">
      <div v-loading="freezeDetailLoading">
        <template v-if="freezeDetail.order">
          <!-- 状态条 -->
          <div class="fd-status-bar">
            <el-tag :type="freezeStatusType(freezeDetail.order.status)" size="large">
              {{ freezeStatusLabel(freezeDetail.order.status) }}
            </el-tag>
            <span class="fd-amount" v-if="freezeDetail.order.freeze_amount">
              涉案金额 ¥{{ Number(freezeDetail.order.freeze_amount).toLocaleString() }}
            </span>
            <span class="fd-dept" v-if="freezeDetail.order.department">{{ freezeDetail.order.department }}</span>
          </div>

          <!-- 基本信息 -->
          <h4 class="fd-title">基本信息</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="案件编号">{{ freezeDetail.order.case_id || '—' }}</el-descriptions-item>
            <el-descriptions-item label="动作类型">{{ freezeDetail.order.action_type || '—' }}</el-descriptions-item>
            <el-descriptions-item label="申请人">{{ freezeDetail.order.applicant_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(freezeDetail.order.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="批准时间">{{ formatTime(freezeDetail.order.approved_at) }}</el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ formatTime(freezeDetail.order.executed_at) }}</el-descriptions-item>
            <el-descriptions-item label="法律依据" :span="2">{{ freezeDetail.order.legal_basis || '—' }}</el-descriptions-item>
            <el-descriptions-item label="事由" :span="2">{{ freezeDetail.order.reason || '—' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 目标账户：字段名以接口为准（account_number/account_name/bank_name） -->
          <h4 class="fd-title">
            目标账户
            <span class="fd-count">{{ (freezeDetail.order.target_accounts || []).length }} 个</span>
          </h4>
          <el-table :data="freezeDetail.order.target_accounts || []" size="small" border>
            <el-table-column type="index" label="#" width="46" />
            <el-table-column prop="account_name" label="户名" width="110">
              <template #default="{ row }">{{ row.account_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="account_number" label="账号" min-width="190" show-overflow-tooltip>
              <template #default="{ row }">{{ row.account_number || '—' }}</template>
            </el-table-column>
            <el-table-column prop="bank_name" label="开户行" width="150">
              <template #default="{ row }">{{ row.bank_name || '—' }}</template>
            </el-table-column>
          </el-table>

          <!-- 审批链 -->
          <h4 class="fd-title">
            审批链
            <span class="fd-count">{{ (freezeDetail.approval_flows || []).length }} 条流程</span>
          </h4>
          <template v-if="(freezeDetail.approval_flows || []).length">
            <div v-for="f in freezeDetail.approval_flows" :key="f.flow_id" class="fd-flow">
              <div class="fd-flow-head">
                <b>{{ f.flow_id }}</b>
                <el-tag :type="approvalStatusType(f.status)" size="small">{{ f.status }}</el-tag>
                <span class="fd-flow-summary">{{ f.summary }}</span>
              </div>
              <div class="fd-chain">
                <div v-for="n in (f.approval_chain || [])" :key="n.level"
                     class="fd-node" :class="{ done: f.status === 'approved' }">
                  <span class="fd-node-lv">{{ n.level }}</span>
                  <span class="fd-node-role">{{ n.role }}</span>
                  <span class="fd-node-user">{{ n.user_name }}</span>
                </div>
              </div>
            </div>
            <!-- 已表决记录（含批语） -->
            <el-table v-if="(freezeDetail.approvals || []).length" :data="freezeDetail.approvals"
                      size="small" border style="margin-top:8px">
              <el-table-column prop="approval_level" label="层级" width="60" align="center" />
              <el-table-column prop="approver_role" label="角色" width="120" />
              <el-table-column prop="approver_name" label="审批人" width="120" />
              <el-table-column prop="decision" label="结论" width="94">
                <template #default="{ row }">
                  <el-tag :type="row.decision === 'approved' ? 'success' : 'warning'" size="small">
                    {{ row.decision === 'approved' ? '同意' : row.decision }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="comment" label="批语" min-width="200" show-overflow-tooltip />
              <el-table-column label="时间" width="140">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </template>
          <el-empty v-else description="尚未提交审批" :image-size="60" />

          <!-- 执行回执 -->
          <h4 class="fd-title">
            执行回执
            <span class="fd-count">{{ (freezeDetail.receipts || []).length }} 条</span>
          </h4>
          <el-table v-if="(freezeDetail.receipts || []).length" :data="freezeDetail.receipts" size="small" border>
            <el-table-column prop="target_account" label="冻结账号" min-width="160" show-overflow-tooltip />
            <el-table-column prop="bank_name" label="开户行" width="140">
              <template #default="{ row }">{{ row.bank_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="execution_status" label="执行状态" width="100">
              <template #default="{ row }">
                <el-tag :type="receiptStatusType(row.execution_status)" size="small">
                  {{ row.execution_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="external_ref" label="外部单号" width="150" show-overflow-tooltip />
            <el-table-column label="冻结至" width="140">
              <template #default="{ row }">{{ formatTime(row.freeze_until) }}</template>
            </el-table-column>
            <el-table-column prop="execution_message" label="回执说明" min-width="200" show-overflow-tooltip />
          </el-table>
          <el-empty v-else
                    :description="freezeDetail.order.status === 'draft' ? '尚未提交审批，暂无回执'
                                  : '审批通过后自动执行；若无回执请点击「提交审批」重试'"
                    :image-size="60" />
        </template>
      </div>
      <template #footer>
        <el-button @click="showFreezeDetail = false">关闭</el-button>
        <el-button type="primary" @click="onDownloadFreezeDoc(freezeDetail.order)">
          <el-icon><Download /></el-icon> 下载文书
        </el-button>
      </template>
    </el-dialog>

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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Plus, Delete, Refresh, WarningFilled, Download } from '@element-plus/icons-vue'
import {
  getCaseLifecycle, transitionCaseStatus, getCaseTimeline,
  listInvestigations, createInvestigation, downloadInvestigationReport,
  listFreezeOrders, createFreezeOrder, submitFreezeOrder, cancelFreezeOrder,
  downloadFreezeDoc,
  listReviews, resolveReview,
  listPendingApprovals, listApprovals, approveFlow, rejectFlow,
  fetchMergeSuggestions, generateMergeSuggestions, rejectMergeSuggestion, confirmMergeSuggestion,
  fetchFreezeOrderDetail, executeFreezeOrder,
} from '../api.js'
import { useAppState } from '../composables/useAppState.js'

const appState = useAppState()
const route = useRoute()
const router = useRouter()

// ── 案件选择 ──
const selectedCaseId = ref('')
/**
 * 从 appState 安全取出数组型状态。
 *
 * ⚠️ 这里曾是一个**渲染期崩溃**的根因：`useFraudLens()` 返回的是**普通对象**
 * （内部字段是 ref），未经 `reactive()` 包裹，因此 `appState.cases` 拿到的是
 * **Ref 本身而不是数组**。原代码写 `computed(() => appState.cases || [])`
 * 漏了 `.value`，于是 `caseList.value.find(...)` 抛
 * "caseList.value.find is not a function"。
 *
 * 该异常发生在 `caseInfo` 求值时，而 `caseInfo` 只在「已选中案件」的 v-else
 * 分支里被渲染 —— 所以**只有带 `?case_id=` 进入工作台才会崩**（例如从案件详情页
 * 点「进入工作台」），不带参数进入则完全正常，极难复现。
 *
 * 其他视图的既定写法是 `cases.value`（如 CapitalFlowView）。此处兼容两种形态，
 * 既修掉当前缺陷，也不会在将来 appState 改为 reactive 后再次踩坑。
 */
function asArray(maybeRef) {
  const v = (maybeRef && typeof maybeRef === 'object' && 'value' in maybeRef)
    ? maybeRef.value
    : maybeRef
  return Array.isArray(v) ? v : []
}

const caseList = computed(() => asArray(appState.cases))
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
// 工单详情（含审批链与执行回执）
const showFreezeDetail = ref(false)
const freezeDetailLoading = ref(false)
const freezeDetail = reactive({ order: null, approvals: [], receipts: [], approval_flows: [] })
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

// ── 并案建议 ──
const merges = ref([])
const mergeLoading = ref(false)
const mergeError = ref('')
const mergeStatusFilter = ref('pending')
const mergeSummary = reactive({ pending: 0, approved: 0, rejected: 0, total: 0 })

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

function simClass(sim) {
  if (sim >= 0.9) return 'sim-high'
  if (sim >= 0.8) return 'sim-mid'
  return 'sim-low'
}

function mergeStatusType(status) {
  return { pending: 'warning', approved: 'success', rejected: 'info' }[status] || 'info'
}

function mergeStatusLabel(status) {
  return { pending: '待研判', approved: '已采纳', rejected: '已驳回' }[status] || status
}

async function loadMerges() {
  mergeLoading.value = true
  mergeError.value = ''
  try {
    const res = await fetchMergeSuggestions(mergeStatusFilter.value)
    if (res.success) {
      merges.value = res.suggestions || []
      if (res.summary) Object.assign(mergeSummary, res.summary)
    } else {
      mergeError.value = res.error || '未知错误'
    }
  } catch (e) {
    mergeError.value = e.message || String(e)
  } finally {
    mergeLoading.value = false
  }
}

async function onGenerateMerges() {
  mergeLoading.value = true
  try {
    const res = await generateMergeSuggestions()
    if (res.success) {
      ElMessage.success(res.total ? `发现 ${res.total} 条新的并案线索` : '未发现新的并案线索')
      await loadMerges()
    } else {
      ElMessage.error(res.error || '并案发现失败')
    }
  } catch (e) {
    ElMessage.error('并案发现失败：' + (e.message || e))
  } finally {
    mergeLoading.value = false
  }
}

async function onAdoptMerge(row) {
  let gangId
  try {
    const { value } = await ElMessageBox.prompt(
      `确认将 ${row.case_id_a} 与 ${row.case_id_b} 并入同一团伙？\n请输入目标团伙编号，可在「团伙画像」页查看现有编号。`,
      '采纳并案建议',
      { inputPlaceholder: '如 G0001', inputPattern: /\S+/, inputErrorMessage: '团伙编号不能为空' }
    )
    gangId = (value || '').trim()
  } catch (e) {
    return // 用户取消
  }
  try {
    const res = await confirmMergeSuggestion(row.case_id_a, row.case_id_b, gangId)
    if (res.success) {
      ElMessage.success('已并入团伙 ' + gangId)
      await loadMerges()
      await loadTimeline(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '并案失败')
    }
  } catch (e) {
    const msg = e?.response?.data?.error || e.message || e
    ElMessage.error('并案失败：' + msg)
  }
}

async function onRejectMerge(row) {
  let reason
  try {
    const { value } = await ElMessageBox.prompt(
      `驳回 ${row.case_id_a} 与 ${row.case_id_b} 的并案建议？`,
      '驳回并案建议',
      { inputPlaceholder: '驳回理由（可选，如：两名受害人无资金往来）', inputType: 'textarea' }
    )
    reason = value || ''
  } catch (e) {
    return
  }
  try {
    const res = await rejectMergeSuggestion(row.id, reason)
    if (res.success) {
      ElMessage.success('已驳回该并案建议')
      await loadMerges()
    } else {
      ElMessage.error(res.error || '驳回失败')
    }
  } catch (e) {
    const msg = e?.response?.data?.error || e.message || e
    ElMessage.error('驳回失败：' + msg)
  }
}

function openCase(caseId) {
  router.push({ name: 'case-detail', query: { case_id: caseId } })
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
  else if (tab === 'merge' && !merges.value.length) loadMerges()
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
      // 详情对话框开着时同步刷新，让审批链立即出现
      if (showFreezeDetail.value && freezeDetail.order?.order_id === row.order_id) {
        await loadFreezeDetail(row.order_id)
      }
      await loadTimeline(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '提交失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('提交失败：' + (e.message || e))
  }
}

async function onExecuteFreeze(row) {
  // 执行重试：仅 approved / failed / partial 可执行（后端状态门控）
  try {
    await ElMessageBox.confirm(
      `对工单 ${row.order_id} 重新执行止付冻结？\n（仅"已批准/执行失败/部分执行"状态可执行，未审批工单会被拒绝）`,
      '执行冻结', { type: 'warning' }
    )
  } catch (e) {
    return // 用户取消
  }
  try {
    const res = await executeFreezeOrder(row.order_id)
    if (res.success) {
      ElMessage.success(`执行完成，工单状态：${res.status}（回执 ${(res.receipts || []).length} 条）`)
      await loadFreezeOrders()
      if (showFreezeDetail.value && freezeDetail.order?.order_id === row.order_id) {
        await loadFreezeDetail(row.order_id)
      }
      await loadTimeline(selectedCaseId.value)
    } else {
      ElMessage.error(res.error || '执行失败')
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.response?.data?.error || e.message || e
    ElMessage.error('执行失败：' + msg)
  }
}

async function onCancelFreeze(row) {
  try {
    const { value: reason } = await ElMessageBox.prompt('撤销原因', '撤销工单', { inputPlaceholder: '撤销原因' })
    const res = await cancelFreezeOrder(row.order_id, reason || '')
    if (res.success) {
      ElMessage.success('已撤销')
      await loadFreezeOrders()
      if (showFreezeDetail.value && freezeDetail.order?.order_id === row.order_id) {
        await loadFreezeDetail(row.order_id)
      }
      await loadTimeline(selectedCaseId.value)
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('撤销失败：' + (e.message || e))
  }
}

function viewFreezeOrder(row) {
  // 拉取完整详情（含审批链与执行回执）渲染，而非把原始 JSON 直接弹窗
  freezeDetail.order = row
  freezeDetail.approvals = []
  freezeDetail.receipts = []
  freezeDetail.approval_flows = []
  showFreezeDetail.value = true
  loadFreezeDetail(row.order_id)
}

const freezeStatusLabel = (s) => ({
  draft: '草稿', pending_approval: '待审批', approved: '已批准',
  rejected: '已驳回', executed: '已执行', partial: '部分执行',
  failed: '执行失败', cancelled: '已撤销',
}[s] || s || '—')

const receiptStatusType = (s) => ({
  success: 'success', pending: 'warning', processing: 'warning', failed: 'danger',
}[s] || 'info')

async function loadFreezeDetail(orderId) {
  freezeDetailLoading.value = true
  try {
    const res = await fetchFreezeOrderDetail(orderId)
    if (res.success) {
      freezeDetail.order = res.order || freezeDetail.order
      freezeDetail.approvals = res.approvals || []
      freezeDetail.receipts = res.receipts || []
      freezeDetail.approval_flows = res.approval_flows || []
    } else {
      ElMessage.error(res.error || '工单详情加载失败')
    }
  } catch (e) {
    ElMessage.error('工单详情加载失败：' + (e.message || e))
  } finally {
    freezeDetailLoading.value = false
  }
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

/* ── 并案建议面板 ── */
.sim-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sim-high {
  background: rgba(255, 77, 79, 0.15);
  color: #ff7875;
  border: 1px solid rgba(255, 77, 79, 0.35);
}

.sim-mid {
  background: rgba(250, 173, 20, 0.15);
  color: #ffc53d;
  border: 1px solid rgba(250, 173, 20, 0.35);
}

.sim-low {
  background: rgba(0, 212, 255, 0.12);
  color: var(--accent-cyan);
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.merge-case {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.4;
}

.merge-case .mc-title {
  color: var(--text-primary);
  font-size: 13px;
}

.merge-case .mc-sub {
  color: var(--text-muted);
  font-size: 12px;
}

.merge-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md, 8px);
  background: rgba(255, 77, 79, 0.08);
  border: 1px solid rgba(255, 77, 79, 0.25);
  color: #ff7875;
  font-size: 13px;
}

.merge-hint {
  margin: 12px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

/* ── 冻结工单详情 ── */
.fd-status-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: var(--radius-md, 8px);
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
}

.fd-amount {
  font-size: 15px;
  font-weight: 600;
  color: #ffc53d;
  font-variant-numeric: tabular-nums;
}

.fd-dept {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}

.fd-title {
  margin: 20px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.fd-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  padding: 1px 8px;
  border-radius: 9px;
  background: rgba(0, 212, 255, 0.09);
}

.fd-flow {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(0, 212, 255, 0.1);
  margin-bottom: 8px;
}

.fd-flow-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-primary);
}

.fd-flow-summary {
  color: var(--text-muted);
  font-size: 12px;
}

.fd-chain {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.fd-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 14px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-muted);
}

.fd-node.done {
  background: rgba(82, 196, 26, 0.12);
  border-color: rgba(82, 196, 26, 0.35);
  color: #95de64;
}

.fd-node-lv {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 10px;
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}

.fd-node-role {
  font-weight: 600;
}

.fd-node-user {
  color: inherit;
  opacity: 0.75;
}
</style>
