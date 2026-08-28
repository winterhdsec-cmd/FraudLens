<template>
  <div class="advisory-wrap" v-if="shouldShow">
    <!-- 异常卡 / 失败边界提示（REQ-S7） -->
    <div v-if="abnormal && abnormal.abnormal && abnormal.abnormal !== 'none'"
         class="advisory-banner"
         :class="abnormal.abnormal === 'missing_data' ? 'is-error' : 'is-warning'">
      <div class="adv-icon">
        <el-icon v-if="abnormal.abnormal === 'missing_data'" :size="18"><CircleCloseFilled /></el-icon>
        <el-icon v-else :size="18"><WarningFilled /></el-icon>
      </div>
      <div class="adv-body">
        <div class="adv-title">
          研判失败边界提示：{{ abnormalLabel(abnormal.abnormal) }}
          <span class="adv-stage" v-if="abnormal.detail && abnormal.detail.stage">（阶段：{{ abnormal.detail.stage }}）</span>
        </div>
        <div class="adv-reason">{{ (abnormal.detail && abnormal.detail.reason) || '系统检测到异常，请人工介入复核' }}</div>
        <div class="adv-action" v-if="abnormal.detail && abnormal.detail.action">
          <el-icon><Right /></el-icon> {{ abnormal.detail.action }}
        </div>
      </div>
    </div>

    <!-- 低可信度 / 其他告警 -->
    <div v-for="(w, i) in warnings" :key="'w' + i"
         class="advisory-banner"
         :class="w.level === 'error' ? 'is-error' : 'is-warning'">
      <div class="adv-icon">{{ w.level === 'error' ? '⛔' : '⚠️' }}</div>
      <div class="adv-body">
        <div class="adv-title">{{ warningLabel(w.type) }}</div>
        <div class="adv-reason">{{ w.message }}</div>
        <div class="adv-action" v-if="w.action"><el-icon><Right /></el-icon> {{ w.action }}</div>
      </div>
    </div>

    <!-- 四单流转（B-L7）可折叠摘要 -->
    <div v-if="slips" class="slips-card tech-card">
      <div class="slips-header" @click="expanded = !expanded">
        <span class="slips-title"><span class="title-icon"><el-icon><Folder /></el-icon></span> 研判过程文档（四单流转）</span>
        <span class="slips-toggle">{{ expanded ? '收起 ▲' : '展开 ▼' }}</span>
      </div>
      <div v-if="expanded" class="slips-body">
        <!-- 警情单 -->
        <div class="slip-block">
          <div class="slip-name">① 警情单</div>
          <div class="slip-line">案件数：{{ slips.alarm?.n_cases ?? 0 }} ｜ 涉案金额：¥{{ fmtAmount(slips.alarm?.total_amount) }}</div>
          <div class="slip-line" v-if="(slips.alarm?.scam_types || []).length">诈骗类型：{{ slips.alarm.scam_types.join('、') }}</div>
          <div class="slip-line" v-if="keyEntitiesText">关键实体：{{ keyEntitiesText }}</div>
        </div>
        <!-- 研判单 -->
        <div class="slip-block">
          <div class="slip-name">② 研判单</div>
          <div class="slip-line" v-if="(slips.analysis?.fund_flow_notes || []).length">资金流：{{ slips.analysis.fund_flow_notes.slice(0, 3).join('；') }}</div>
          <div class="slip-line slip-warn" v-if="(slips.analysis?.contradiction_notes || []).length">矛盾识别：{{ slips.analysis.contradiction_notes.slice(0, 3).join('；') }}</div>
          <div class="slip-line" v-if="!(slips.analysis?.fund_flow_notes || []).length && !(slips.analysis?.contradiction_notes || []).length">暂无显著资金流/矛盾要点</div>
        </div>
        <!-- 指令单 -->
        <div class="slip-block">
          <div class="slip-name">③ 指令单</div>
          <div class="slip-line" v-for="(d, i) in (slips.dispatch?.dispatch_notes || []).slice(0, 5)" :key="'d' + i">{{ d }}</div>
          <div class="slip-line" v-if="!(slips.dispatch?.dispatch_notes || []).length">暂无处置建议</div>
        </div>
        <!-- 反馈单 -->
        <div class="slip-block">
          <div class="slip-name">④ 反馈单</div>
          <div class="slip-line">质量分：{{ (slips.feedback?.quality_score ?? 0).toFixed?.(2) ?? slips.feedback?.quality_score ?? 0 }}</div>
          <div class="slip-line" v-if="(slips.feedback?.evidence_summary || []).length">证据链：{{ slips.feedback.evidence_summary.slice(0, 3).join('；') }}</div>
          <div class="slip-line" v-if="slips.feedback?.review_chain">已生成复盘六动作记录（{{ reviewChainText }}）</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  abnormal: { type: Object, default: () => ({ abnormal: 'none', detail: null }) },
  warnings: { type: Array, default: () => [] },
  slips: { type: Object, default: null }
})

const expanded = ref(false)

const shouldShow = computed(() => {
  const abn = props.abnormal && props.abnormal.abnormal && props.abnormal.abnormal !== 'none'
  return !!(abn || (props.warnings && props.warnings.length) || props.slips)
})

const keyEntitiesText = computed(() => {
  const ke = (props.slips?.alarm?.key_entities) || {}
  const parts = []
  const labelMap = { bank_accounts: '账户', phone_numbers: '手机号', wechat_ids: '微信', qq_numbers: 'QQ' }
  for (const [k, v] of Object.entries(ke)) {
    if (Array.isArray(v) && v.length) parts.push(`${labelMap[k] || k} ${v.length} 个`)
  }
  return parts.join('、')
})

const reviewChainText = computed(() => {
  const rc = props.slips?.feedback?.review_chain
  if (!rc) return ''
  const keys = Object.keys(rc).filter(k => !k.startsWith('_'))
  return keys.join(' / ')
})

const abnormalLabel = (t) => ({
  missing_data: '数据缺失（退回人工补材料）',
  model_conflict: '模型冲突（建议人工裁决）',
  timeout: '处理超时降级（标记交人工）'
}[t] || t)

const warningLabel = (t) => ({
  missing_data: '数据缺失',
  model_conflict: '模型冲突',
  timeout: '处理超时',
  low_confidence: '低可信度提示'
}[t] || (t || '提示'))

const fmtAmount = (v) => {
  if (v == null) return '0'
  const n = Number(v) || 0
  return n >= 10000 ? (n / 10000).toFixed(2) + '万' : n.toFixed(2)
}
</script>

<style scoped>
.advisory-wrap { margin-bottom: 20px; display: flex; flex-direction: column; gap: 12px; }

.advisory-banner {
  display: flex;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 12px;
  align-items: flex-start;
  border: 1px solid;
  animation: fadeIn .35s ease both;
}
.advisory-banner.is-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.35);
}
.advisory-banner.is-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.35);
}
.adv-icon { font-size: 22px; line-height: 1.4; flex-shrink: 0; }
.adv-body { flex: 1; }
.adv-title { font-size: 14px; font-weight: 700; color: var(--text-primary, #e2e8f0); }
.is-error .adv-title { color: #fca5a5; }
.is-warning .adv-title { color: #fcd34d; }
.adv-stage { font-size: 12px; font-weight: 400; color: var(--text-muted, #94a3b8); }
.adv-reason { font-size: 13px; color: #cbd5e1; margin-top: 4px; line-height: 1.6; }
.adv-action { font-size: 12px; color: #fbbf24; margin-top: 6px; }

.slips-card {
  padding: 14px 18px;
  border: 1px solid rgba(0, 198, 255, 0.12);
  background: var(--bg-card, rgba(15, 23, 42, 0.4));
}
.slips-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.slips-title { font-size: 14px; font-weight: 600; color: var(--text-primary, #e2e8f0); display: flex; align-items: center; gap: 6px; }
.title-icon { font-size: 16px; }
.slips-toggle { font-size: 12px; color: var(--accent-cyan, #00d4ff); }
.slips-body { margin-top: 12px; display: flex; flex-direction: column; gap: 14px; }
.slip-block {
  padding: 10px 14px;
  border-left: 3px solid var(--accent-cyan, #00d4ff);
  background: rgba(0, 0, 0, 0.18);
  border-radius: 6px;
}
.slip-name { font-size: 13px; font-weight: 700; color: var(--accent-cyan, #00d4ff); margin-bottom: 6px; }
.slip-line { font-size: 12px; color: #cbd5e1; line-height: 1.7; }
.slip-warn { color: #fcd34d; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
</style>
