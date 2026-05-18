<template>
<div v-if="activeMenu === 'network'" class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title">
                <span class="title-icon">🕸️</span>
                关联网络
              </h2>
              <p class="section-desc">展示案件、团伙、资金等多维度关联关系</p>
            </div>
            <div class="header-right">
              <div class="network-controls">
                <el-button-group>
                  <el-button size="small" :type="networkView === 'all' ? 'primary' : ''" @click="networkView = 'all'">
                    全部
                  </el-button>
                  <el-button size="small" :type="networkView === 'gang' ? 'primary' : ''" @click="networkView = 'gang'">
                    团伙
                  </el-button>
                  <el-button size="small" :type="networkView === 'case' ? 'primary' : ''" @click="networkView = 'case'">
                    案件
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>

          <div class="network-container tech-card">
            <NetworkGraph :gangs="gangs" :selectedGang="selectedGang" @select="selectGang" />
          </div>
        </div>
</template>

<script setup>
import { inject } from "vue"
const state = inject("appState")
const {
  activeMenu, gangs, networkView, selectGang, selectedGang
} = state
</script>
