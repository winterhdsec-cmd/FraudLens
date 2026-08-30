<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon"><el-icon><User /></el-icon></span>
                团伙画像总览
              </h2>
              <p class="section-desc">查看所有涉案团伙的详细画像信息，包括组织架构、作案特征等</p>
            </div>
            <div class="header-right review-controls">
              <span class="review-status-text" v-if="gangReview.checkedGangs">
                复核层已检查 {{ gangReview.checkedGangs }} 个团伙
                <template v-if="gangReview.llmEnabled">· LLM 增强</template>
                <template v-else>· 规则引擎</template>
              </span>
              <el-button size="small" :loading="gangReviewLoading" @click="loadGangReview(true)">
                <el-icon v-if="!gangReviewLoading"><Refresh /></el-icon> 刷新复核
              </el-button>
              <el-tooltip content="开启后由大模型对全部团伙做一次深度复核，耗时较长" placement="bottom">
                <el-switch
                  v-model="gangReviewUseLlm"
                  inline-prompt
                  active-text="LLM"
                  inactive-text="规则"
                  :disabled="gangReviewLoading"
                  @change="toggleGangReviewLlm"
                />
              </el-tooltip>
            </div>
          </div>

          <!-- 误并案探测器（Skill B）告警横幅 -->
          <div v-if="suspiciousMerges.length" class="review-alert-banner">
            <div class="rab-header">
              <span class="rab-icon"><el-icon><WarningFilled /></el-icon></span>
              <span class="rab-title">误并案探测告警</span>
              <el-tag size="small" type="warning" effect="dark">{{ gangReview.review?.source === 'llm' ? 'LLM 复核' : '规则复核' }}</el-tag>
              <span class="rab-count">发现 {{ suspiciousMerges.length }} 个可疑合并团伙，建议人工拆解复核</span>
            </div>
            <div class="rab-list">
              <div v-for="(s, si) in suspiciousMerges" :key="si" class="rab-item">
                <b>{{ s.gang_id }}</b>
                <span class="rab-reason">{{ s.reason }}</span>
                <span class="rab-cases">涉及案件: {{ (s.case_ids || []).slice(0, 6).join('、') }}{{ (s.case_ids || []).length > 6 ? ' 等' + s.case_ids.length + ' 起' : '' }}</span>
              </div>
            </div>
          </div>
          <div v-else-if="gangReview.checkedGangs && !gangReview.error" class="review-ok-banner">
            <span class="rob-icon"><el-icon><CircleCheckFilled /></el-icon></span>
            误并案探测器已复核全部团伙，未发现可疑合并（无共享实体/资金闭环且话术互异的组合）
          </div>
          <div v-if="gangReview.error" class="review-error-banner">
            <span class="rob-icon"><el-icon><WarningFilled /></el-icon></span>
            复核层暂时不可用：{{ gangReview.error }}
          </div>

          <div v-if="!casesReady" class="profiles-loading">
            <div class="sk-grid">
              <div v-for="n in 6" :key="n" class="sk-card tech-card">
                <el-skeleton animated>
                  <template #template>
                    <div class="sk-head">
                      <el-skeleton-item variant="circle" style="width:44px;height:44px" />
                      <div class="sk-head-body">
                        <el-skeleton-item variant="h3" style="width:60%;height:16px" />
                        <el-skeleton-item variant="text" style="width:38%;height:12px;margin-top:8px" />
                      </div>
                    </div>
                    <el-skeleton-item variant="text" style="width:92%;height:12px;margin-top:16px" />
                    <el-skeleton-item variant="text" style="width:78%;height:12px;margin-top:8px" />
                    <div class="sk-row" style="margin-top:16px">
                      <el-skeleton-item variant="button" style="width:72px;height:22px" />
                      <el-skeleton-item variant="button" style="width:88px;height:22px;margin-left:auto" />
                    </div>
                  </template>
                </el-skeleton>
              </div>
            </div>
          </div>

          <div v-else-if="gangs.length" class="profiles-container">
            <div v-for="gang in pagedGangs" :key="gang.id" class="profile-card tech-card">
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
                    <span class="label-icon"><el-icon><DataAnalysis /></el-icon></span>
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
                    <span class="label-icon"><el-icon><UserFilled /></el-icon></span>
                    作案特征
                  </div>
                  <div class="feature-tags">
                    <el-tag v-if="gang.script_type" size="small" type="warning" effect="dark">{{ gang.script_type }}</el-tag>
                    <el-tag v-for="tag in gang.tags.slice(0, 6)" :key="tag" size="small" type="info">{{ tag }}</el-tag>
                  </div>
                  <!-- 作案流程：引流 / 实施 / 洗钱（公安一线话术），后端 steps 真实填充 -->
                  <div v-if="gang.steps && gang.steps.length" class="gang-steps">
                    <span class="steps-label">作案流程</span>
                    <div class="steps-chain">
                      <template v-for="(s, si) in gang.steps" :key="si">
                        <span class="step-node">{{ typeof s === 'string' ? s : (s.title || s.name || s.step || '环节') }}</span>
                        <span v-if="si < gang.steps.length - 1" class="step-arrow">→</span>
                      </template>
                    </div>
                  </div>
                </div>

                <!-- 能力评估改用 radar_data 真实六维评分（原 abilities.* 字段不存在，三根条永远显示假值） -->
                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon"><el-icon><TrendCharts /></el-icon></span>
                    能力评估
                  </div>
                  <div class="ability-bars" v-if="radarPairs(gang).length">
                    <div class="ability-item" v-for="(p, pi) in radarPairs(gang)" :key="p.k">
                      <span class="ability-label">{{ p.k }}</span>
                      <el-progress :percentage="p.v" :color="abilityColor(pi)" :stroke-width="8" />
                    </div>
                  </div>
                  <div v-else class="ability-empty">暂无能力评估数据</div>
                </div>

                <!-- 关联案件摘要：团伙画像最有价值的信息（此前完全不显示） -->
                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon"><el-icon><Files /></el-icon></span>
                    关联案件
                    <span class="section-count" v-if="gang.related_cases?.length">前 {{ Math.min(3, gang.related_cases.length) }} / 共 {{ gang.related_cases.length }} 起</span>
                  </div>
                  <div class="related-case-list" v-if="gang.related_cases?.length">
                    <div v-for="rc in gang.related_cases.slice(0, 3)" :key="rc.case_id" class="related-case-row" @click="jumpToCase(rc.case_id)">
                      <span class="rc-id">{{ rc.case_id }}</span>
                      <span class="rc-victim">{{ rc.victim || '受害人' }}</span>
                      <span class="rc-amount">{{ rc.amount || '-' }}</span>
                      <el-tag size="small" :type="getRiskType(rc.risk_level)" effect="plain" v-if="rc.risk_level">{{ rc.risk_level }}</el-tag>
                    </div>
                  </div>
                  <div v-else class="ability-empty">暂无关联案件明细</div>
                </div>

                <!-- 并案依据解释器（Skill A）：反思闭环可视化 -->
                <div class="profile-section review-section">
                  <div class="section-label">
                    <span class="label-icon"><el-icon><ChatLineSquare /></el-icon></span>
                    并案依据（AI 复核）
                    <el-tag
                      v-if="gangReviewMap[gang.id]"
                      size="small"
                      :type="gangReviewMap[gang.id].source === 'llm' ? 'success' : 'info'"
                      effect="plain"
                      class="review-src-tag"
                    >{{ gangReviewMap[gang.id].source === 'llm' ? 'LLM 生成' : '规则引擎' }}</el-tag>
                    <el-tag v-if="suspiciousMergeMap[gang.id]" size="small" type="danger" effect="dark" class="review-src-tag">可疑合并</el-tag>
                  </div>

                  <div v-if="suspiciousMergeMap[gang.id]" class="review-suspicious">
                    <el-icon><WarningFilled /></el-icon>
                    <span>{{ suspiciousMergeMap[gang.id].reason }}</span>
                  </div>

                  <div v-if="gangReviewMap[gang.id]" class="review-explanation">
                    {{ gangReviewMap[gang.id].explanation }}
                  </div>
                  <div v-else-if="gangReviewLoading" class="review-loading">
                    <el-icon class="is-loading"><Loading /></el-icon> 复核层分析中…
                  </div>
                  <div v-else-if="gangReview.error" class="review-muted">复核不可用</div>
                  <div v-else class="review-muted">该团伙暂无复核结论</div>

                  <!-- 规则模式下 explanation 已含全部依据；仅 LLM 模式补充结构化证据行 -->
                  <div v-if="gangReviewMap[gang.id]?.rule_lines?.length && gangReviewMap[gang.id].source === 'llm'" class="review-rules">
                    <div v-for="(line, li) in gangReviewMap[gang.id].rule_lines" :key="li" class="review-rule-line">
                      <span class="rrl-dot"></span>{{ line }}
                    </div>
                  </div>

                  <div v-if="gangReviewMap[gang.id]?.evidence" class="review-evidence">
                    <span
                      v-for="(v, k) in gangReviewMap[gang.id].evidence.shared_entities || {}"
                      :key="'se' + k"
                      class="ev-badge ev-shared"
                    >共享{{ entityLabel(k) }}×{{ (v && v.length !== undefined) ? v.length : 1 }}</span>
                    <span v-if="(gangReviewMap[gang.id].evidence.reflux_cycles || []).length" class="ev-badge ev-reflux">
                      资金回流闭环×{{ gangReviewMap[gang.id].evidence.reflux_cycles.length }}
                    </span>
                    <span v-if="(gangReviewMap[gang.id].evidence.evidence_chain || []).length" class="ev-badge ev-chain">
                      证据链×{{ gangReviewMap[gang.id].evidence.evidence_chain.length }}
                    </span>
                    <span v-if="(gangReviewMap[gang.id].evidence.freeze_candidates || []).length" class="ev-badge ev-freeze">
                      可冻结账户×{{ gangReviewMap[gang.id].evidence.freeze_candidates.length }}
                    </span>
                    <span v-for="(fp, fi) in (gangReviewMap[gang.id].evidence.fingerprint || []).slice(0, 3)" :key="'fp' + fi" class="ev-badge ev-fp">
                      #{{ fp }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="profile-footer">
                <el-button size="small" @click="selectGang(gang); router.push({ name: 'details' })">
                  <span><el-icon><Search /></el-icon></span> 深度分析
                </el-button>
                <el-button size="small" type="primary" @click="selectGang(gang); router.push({ name: 'report', query: { gangId: gang.id } })">
                  <span><el-icon><Document /></el-icon></span> 生成报告
                </el-button>
              </div>
            </div>

            <div class="profiles-pagination" v-if="gangs.length > pageSize">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[6, 12, 24, 50]"
                :total="gangs.length"
                layout="total, sizes, prev, pager, next, jumper"
                background
              />
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon empty-icon-gang"><el-icon :size="64"><UserFilled /></el-icon></div>
              <h3 class="empty-title">暂未识别诈骗团伙</h3>
              <p class="empty-desc">系统需要通过案件间的资金链关联和话术语义相似度来聚类发现团伙。请先录入足够的案件数据（建议 10 条以上），系统将自动运行 GNN 图神经网络进行团伙发现。</p>
              <el-button type="primary" size="large" @click="router.push({ name: 'input' })">
                <span><el-icon><EditPen /></el-icon></span> 前往录入案件
              </el-button>
            </div>
          </div>
        </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
const router = useRouter()
const state = useAppState()
const {
  activeMenu, cases, gangs, casesReady, getRiskType, selectGang,
  gangReview, gangReviewLoading, gangReviewUseLlm,
  gangReviewMap, suspiciousMergeMap, suspiciousMerges,
  loadGangReview, toggleGangReviewLlm
} = state

// 团伙画像卡片内含成员列表与并案依据，单卡 DOM 成本很高（实测整页 5690 节点），
// 因此每页只渲染少量卡片，默认 12 个
const currentPage = ref(1)
const pageSize = ref(12)
const pagedGangs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return gangs.value.slice(start, start + pageSize.value)
})
// 团伙数变化或改页大小后回到第一页，避免停在越界的空白页
watch([() => gangs.value.length, pageSize], () => { currentPage.value = 1 })

// 共享实体类型 -> 中文标签（key 与后端 gang_reviewer.ENTITY_TYPES 对齐）
const ENTITY_LABELS = {
  bank_accounts: '银行账户', phone_numbers: '手机号',
  wechat_ids: '微信号', qq_numbers: 'QQ号', id_cards: '身份证',
  bank_account: '银行账户', phone: '手机号', wechat: '微信号',
  qq: 'QQ号', id_card: '身份证', account: '账户', accounts: '账户',
  ip: 'IP', ips: 'IP', wallet: '钱包地址'
}
const entityLabel = (k) => ENTITY_LABELS[k] || String(k).replace(/_/g, '')

// radar_data 是中文键的六维评分字典（后端真实字段，0~100），取前 3 维做进度条
const RADAR_COLORS = ['#00d4ff', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#ec4899']
const radarPairs = (gang) => {
  const rd = gang.radar_data || gang.radarData || {}
  return Object.entries(rd)
    .filter(([, v]) => typeof v === 'number' && v > 0)
    .map(([k, v]) => ({ k, v: Math.round(v) }))
    .slice(0, 4)
}
const abilityColor = (i) => RADAR_COLORS[i % RADAR_COLORS.length]

const jumpToCase = (caseId) => {
  const c = cases.value?.find(x => x.case_id === caseId || x.id === caseId)
  if (c) { state.viewCaseDetail?.(c) } else { router.push({ name: 'overview' }) }
}
</script>

<style scoped>
.profiles-pagination {
  display: flex;
  justify-content: center;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 198, 255, 0.08);
}

/* 数据加载骨架：网格与 .profiles-container 近似，数据到位后跳版最小化 */
.profiles-loading { margin-bottom: 20px; }
.sk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}
.sk-card {
  padding: 16px;
  border: 1px solid rgba(0, 198, 255, 0.08);
}
.sk-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sk-head-body { flex: 1; min-width: 0; }
.sk-row {
  display: flex;
  align-items: center;
}

/* ===== 团伙画像卡片增强 ===== */
/* 团伙卡片：紫色左侧竖条（区别于案件卡片的青色） */
.profile-card {
  position: relative;
  padding-left: 22px;
}
.profile-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #8b5cf6, rgba(139, 92, 246, 0.3));
  opacity: 0.7;
  transition: opacity 0.3s ease, width 0.2s ease;
  border-radius: 0 2px 2px 0;
}
.profile-card:hover::before {
  opacity: 1;
  width: 4px;
}

.gang-steps { margin-top: 10px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.steps-label { font-size: 11.5px; color: var(--text-secondary, #64748b); flex-shrink: 0; }
.steps-chain { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.step-node {
  font-size: 11.5px;
  color: #7dd3fc;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.25);
  border-radius: 999px;
  padding: 2px 9px;
  white-space: nowrap;
}
.step-arrow { color: rgba(125, 211, 252, 0.5); font-size: 11px; }
.ability-empty { font-size: 12px; color: var(--text-secondary, #64748b); }
.section-count { font-size: 11px; color: var(--text-muted, #475569); margin-left: auto; font-weight: 400; }
.related-case-list { display: flex; flex-direction: column; gap: 4px; }
.related-case-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.18);
  cursor: pointer;
  transition: background 0.2s;
  min-width: 0;
}
.related-case-row:hover { background: rgba(0, 212, 255, 0.08); }
.rc-id {
  font-family: 'JetBrains Mono', Consolas, monospace;
  color: #93c5fd;
  flex-shrink: 0;
  font-size: 11.5px;
}
.rc-victim {
  color: var(--text-primary, #cbd5e1);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rc-amount { color: #f87171; flex-shrink: 0; font-weight: 600; }

/* ===== 复核解释层（并案依据 / 误并案探测）===== */
.review-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.review-status-text {
  font-size: 12px;
  color: var(--text-secondary, #8b9dc3);
}
.review-alert-banner {
  margin: 0 0 16px;
  padding: 14px 18px;
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.45);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(239, 68, 68, 0.08));
}
.rab-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.rab-icon { color: #f59e0b; display: inline-flex; font-size: 16px; }
.rab-title { font-weight: 700; color: #fbbf24; font-size: 14px; }
.rab-count { font-size: 12px; color: var(--text-secondary, #8b9dc3); }
.rab-list { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.rab-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12.5px;
  color: var(--text-primary, #e2e8f0);
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(245, 158, 11, 0.08);
}
.rab-item b { color: #fbbf24; }
.rab-reason { color: var(--text-secondary, #8b9dc3); }
.rab-cases { color: #93c5fd; }
.review-ok-banner {
  margin: 0 0 16px;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.08);
  font-size: 12.5px;
  color: #86efac;
  display: flex;
  align-items: center;
  gap: 8px;
}
.rob-icon { display: inline-flex; font-size: 15px; color: #22c55e; }
.review-error-banner {
  margin: 0 0 16px;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(148, 163, 184, 0.08);
  font-size: 12.5px;
  color: var(--text-secondary, #8b9dc3);
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-error-banner .rob-icon { color: #94a3b8; }

.review-section { border-top: 1px dashed rgba(0, 212, 255, 0.2); }
.review-src-tag { margin-left: 4px; }
.review-suspicious {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12.5px;
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 8px;
}
.review-explanation {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-primary, #cbd5e1);
  background: rgba(0, 212, 255, 0.05);
  border-left: 3px solid rgba(0, 212, 255, 0.5);
  border-radius: 0 6px 6px 0;
  padding: 8px 12px;
  word-break: break-word;
}
.review-loading, .review-muted {
  font-size: 12px;
  color: var(--text-secondary, #64748b);
  display: flex;
  align-items: center;
  gap: 6px;
}
.review-rules { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.review-rule-line {
  font-size: 12px;
  color: #7dd3fc;
  display: flex;
  align-items: baseline;
  gap: 6px;
  word-break: break-word;
}
.rrl-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #00d4ff; flex-shrink: 0;
  position: relative; top: -1px;
}
.review-evidence {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ev-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid;
  white-space: nowrap;
}
.ev-shared { color: #f472b6; border-color: rgba(244, 114, 182, 0.45); background: rgba(244, 114, 182, 0.08); }
.ev-reflux { color: #4ade80; border-color: rgba(74, 222, 128, 0.45); background: rgba(74, 222, 128, 0.08); }
.ev-chain { color: #c084fc; border-color: rgba(192, 132, 252, 0.45); background: rgba(192, 132, 252, 0.08); }
.ev-freeze { color: #fbbf24; border-color: rgba(251, 191, 36, 0.45); background: rgba(251, 191, 36, 0.08); }
.ev-fp { color: #94a3b8; border-color: rgba(148, 163, 184, 0.4); background: rgba(148, 163, 184, 0.06); }

/* ===== 空状态差异化 ===== */
.empty-state { text-align: center; padding: 60px 20px; }
.empty-content { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.empty-icon {
  font-size: 64px;
  opacity: 0.6;
  width: 100px; height: 100px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 20px;
}
.empty-icon-gang {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(139, 92, 246, 0.03));
  color: #8b5cf6;
}
.empty-title { font-size: 20px; color: var(--text-primary); font-weight: 600; margin: 0; }
.empty-desc { font-size: 14px; color: var(--text-muted); max-width: 480px; line-height: 1.7; }
</style>
