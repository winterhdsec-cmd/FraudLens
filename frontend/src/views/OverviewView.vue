<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">📊</span>
                案件总览
              </h2>
              <p class="section-desc">展示所有录入的案件及团伙信息概览，支持快速筛选和定位</p>
            </div>
            <div class="header-right">
              <div class="view-toggle">
                <el-button-group>
                  <el-button size="small" :type="viewMode === 'card' ? 'primary' : ''" @click="viewMode = 'card'">
                    <span>📇</span> 卡片
                  </el-button>
                  <el-button size="small" :type="viewMode === 'table' ? 'primary' : ''" @click="viewMode = 'table'">
                    <span>📋</span> 列表
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>

          <div class="stats-overview">
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper danger">
                <span class="stat-icon">👥</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ gangs.length }}</div>
                <div class="stat-label">涉案团伙</div>
                <div class="stat-trend up">
                  <span>↑ 2</span>
                  <span>本周新增</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper warning">
                <span class="stat-icon">📋</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ cases.length }}</div>
                <div class="stat-label">关联案件</div>
                <div class="stat-trend up">
                  <span>↑ 5</span>
                  <span>本周新增</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper success">
                <span class="stat-icon">💰</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ totalAmountFormatted }}</div>
                <div class="stat-label">涉案金额</div>
                <div class="stat-trend">
                  <span>{{ cases.length }}</span>
                  <span>案件累计</span>
                </div>
              </div>
            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper info">
                <span class="stat-icon">🎯</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ successRate }}%</div>
                <div class="stat-label">研判准确率</div>
                <div class="stat-trend up">
                  <span>↑ 3%</span>
                  <span>较上月</span>
                </div>
              </div>
            </div>
          </div>

          <div class="overview-charts">
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">案件类型分布</span>
              </div>
              <div class="chart-content" ref="pieChartRef"></div>
            </div>
            <div class="chart-card tech-card">
              <div class="chart-header">
                <span class="chart-title">涉案金额趋势</span>
              </div>
              <div class="chart-content" ref="lineChartRef"></div>
            </div>
          </div>

          <div class="gangs-section" v-if="gangs.length">
            <div class="section-sub-header">
              <h3 class="sub-title">
                <span class="sub-icon">👥</span>
                团伙列表
              </h3>
              <div class="filter-bar">
                <el-input
                  v-model="gangSearchKeyword"
                  placeholder="搜索团伙名称..."
                  size="small"
                  class="search-input"
                  clearable
                >
                  <template #prefix>
                    <span>🔍</span>
                  </template>
                </el-input>
                <el-select v-model="riskFilter" placeholder="风险等级" size="small" clearable>
                  <el-option label="S级" value="S" />
                  <el-option label="A级" value="A" />
                  <el-option label="B级" value="B" />
                </el-select>
              </div>
            </div>

            <div class="gangs-grid" v-if="viewMode === 'card'">
              <div
                v-for="gang in filteredGangs"
                :key="gang.id"
                class="gang-card tech-card"
                :class="{ 'selected': selectedGang?.id === gang.id }"
                @click="selectGang(gang)"
              >
                <div class="gang-card-header">
                  <div class="gang-icon-wrapper" :class="'risk-' + gang.riskLevel.toLowerCase()">
                    <span class="gang-icon">{{ gang.icon }}</span>
                  </div>
                  <div class="gang-info">
                    <div class="gang-name">{{ gang.name }}</div>
                    <div class="gang-meta">
                      <el-tag :type="getRiskType(gang.riskLevel)" size="small" effect="dark">
                        {{ gang.riskLevel }}级风险
                      </el-tag>
                      <span class="gang-id">ID: {{ gang.id }}</span>
                    </div>
                  </div>
                </div>
                <div class="gang-card-body">
                  <div class="gang-stats">
                    <div class="gang-stat">
                      <span class="stat-icon">💰</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.amount }}</span>
                        <span class="stat-label">涉案金额</span>
                      </div>
                    </div>
                    <div class="gang-stat">
                      <span class="stat-icon">📋</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.cases }}起</span>
                        <span class="stat-label">关联案件</span>
                      </div>
                    </div>
                    <div class="gang-stat">
                      <span class="stat-icon">👥</span>
                      <div class="stat-content">
                        <span class="stat-value">{{ gang.members?.length || 0 }}人</span>
                        <span class="stat-label">团伙成员</span>
                      </div>
                    </div>
                  </div>
                  <div class="gang-tags">
                    <el-tag v-for="tag in gang.tags?.slice(0, 3)" :key="tag" size="small" type="info">
                      {{ tag }}
                    </el-tag>
                    <el-tag v-if="gang.tags?.length > 3" size="small" type="info">
                      +{{ gang.tags.length - 3 }}
                    </el-tag>
                  </div>
                </div>
                <div class="gang-card-footer">
                  <span class="update-time">更新于 {{ gang.updateTime || '刚刚' }}</span>
                  <el-button size="small" type="primary" @click.stop="viewGangDetail(gang)">
                    查看详情 →
                  </el-button>
                </div>
              </div>
            </div>

            <div class="gangs-table" v-else>
              <el-table :data="filteredGangs" style="width: 100%" @row-click="selectGang">
                <el-table-column prop="id" label="团伙ID" width="100" />
                <el-table-column prop="name" label="团伙名称" />
                <el-table-column prop="riskLevel" label="风险等级" width="100">
                  <template #default="scope">
                    <el-tag :type="getRiskType(scope.row.riskLevel)" effect="dark">
                      {{ scope.row.riskLevel }}级
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="涉案金额" width="120" />
                <el-table-column prop="cases" label="案件数" width="80" />
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="primary" @click="viewGangDetail(scope.row)">
                      详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div class="cases-section" v-if="cases.length">
            <div class="section-sub-header">
              <h3 class="sub-title">
                <span class="sub-icon">📋</span>
                案件列表
              </h3>
            </div>
            <div class="cases-table tech-card">
              <el-table :data="cases" style="width: 100%" @row-click="viewCaseDetail" :highlight-current-row="true">
                <el-table-column prop="id" label="案件编号" width="100" />
                <el-table-column prop="title" label="案件名称" />
                <el-table-column prop="type" label="案件类型" width="100">
                  <template #default="scope">
                    <el-tag type="info" size="small">{{ scope.row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="region" label="案发地区" width="120" />
                <el-table-column prop="amount" label="涉案金额" width="120" />
                <el-table-column prop="status" label="案件状态" width="100">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === '已立案' ? 'warning' : scope.row.status === '侦办中' ? 'primary' : 'success'" size="small">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="date" label="立案时间" width="120" />
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="primary" @click="viewCaseDetail(scope.row)">
                      查看详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">📊</div>
              <h3 class="empty-title">暂无案件数据</h3>
              <p class="empty-desc">请先通过数据录入功能添加案情信息，系统将自动进行智能研判</p>
              <el-button type="primary" size="large" @click="activeMenu = 'input'">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, cases, gangSearchKeyword, gangs, lineChartRef, pieChartRef,
  successRate, totalAmount, totalAmountFormatted, viewMode
} = state
</script>
