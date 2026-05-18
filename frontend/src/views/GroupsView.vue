<template>
<div v-if="activeMenu === 'groups'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">👥</span>
                团伙画像总览
              </h2>
              <p class="section-desc">查看所有涉案团伙的详细画像信息，包括组织架构、作案特征等</p>
            </div>
          </div>

          <div v-if="gangs.length" class="profiles-container">
            <div v-for="gang in gangs" :key="gang.id" class="profile-card tech-card">
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
                    <span class="label-icon">📊</span>
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
                    <span class="label-icon">🎭</span>
                    作案特征
                  </div>
                  <div class="feature-tags">
                    <el-tag v-for="tag in gang.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
                  </div>
                </div>

                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">👥</span>
                    成员信息
                  </div>
                  <div class="member-grid">
                    <div v-for="member in gang.members" :key="member.id" class="member-card">
                      <span class="member-avatar">{{ member.icon }}</span>
                      <div class="member-details">
                        <span class="member-name">{{ member.name }}</span>
                        <el-tag size="small" :type="member.role === '头目' ? 'danger' : 'info'">
                          {{ member.role }}
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="profile-section">
                  <div class="section-label">
                    <span class="label-icon">📈</span>
                    能力评估
                  </div>
                  <div class="ability-bars">
                    <div class="ability-item">
                      <span class="ability-label">技术能力</span>
                      <el-progress :percentage="gang.abilities?.tech || 75" :color="'#00d4ff'" :stroke-width="8" />
                    </div>
                    <div class="ability-item">
                      <span class="ability-label">组织严密性</span>
                      <el-progress :percentage="gang.abilities?.org || 85" :color="'#f59e0b'" :stroke-width="8" />
                    </div>
                    <div class="ability-item">
                      <span class="ability-label">反侦察能力</span>
                      <el-progress :percentage="gang.abilities?.antiDetect || 60" :color="'#ef4444'" :stroke-width="8" />
                    </div>
                  </div>
                </div>
              </div>

              <div class="profile-footer">
                <el-button size="small" @click="selectGang(gang); activeMenu = 'case-detail'">
                  <span>🔍</span> 查看详情
                </el-button>
                <el-button size="small" type="primary" @click="selectGang(gang); activeMenu = 'report'">
                  <span>📄</span> 生成报告
                </el-button>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">👥</div>
              <h3 class="empty-title">暂无团伙画像数据</h3>
              <p class="empty-desc">请先录入案情信息，系统将自动生成团伙画像</p>
              <el-button type="primary" size="large" @click="activeMenu = 'input'">
                <span>📝</span> 前往录入
              </el-button>
            </div>
          </div>
        </div>
</template>

<script setup>
import { inject } from "vue"
const state = inject("appState")
const {
  activeMenu, cases, gangs, getRiskType, selectGang
} = state
</script>
