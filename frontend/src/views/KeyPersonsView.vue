<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title"><span class="title-icon">👤</span>重点人员库</h2>
              <p class="section-desc">前科人员 / 高危人员管理，研判时自动碰撞比对</p>
            </div>
            <div class="header-actions">
              <el-input v-model="personSearch" placeholder="姓名/电话/身份证" style="width:200px" size="small" clearable @clear="loadKeyPersons" @keyup.enter="loadKeyPersons" />
              <el-select v-model="personTypeFilter" placeholder="人员类型" size="small" style="width:120px" @change="loadKeyPersons">
                <el-option label="全部" value="" />
                <el-option label="前科人员" value="前科人员" />
                <el-option label="高危人员" value="高危人员" />
                <el-option label="在逃人员" value="在逃人员" />
              </el-select>
              <el-button type="primary" size="small" @click="showCreatePerson = true">新增人员</el-button>
            </div>
          </div>
          <div class="persons-container">
            <el-table :data="keyPersons" stripe size="small" max-height="500">
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="id_number" label="身份证号" width="180" />
              <el-table-column prop="phone" label="电话" width="130" />
              <el-table-column prop="bank_account" label="银行卡号" width="160" />
              <el-table-column prop="risk_label" label="风险等级" width="80">
                <template #default="{row}">
                  <el-tag :type="row.risk_level==='A' ? 'danger' : row.risk_level==='B' ? 'warning' : 'info'" size="small">{{row.risk_label}}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="person_type" label="类型" width="100" />
              <el-table-column prop="source" label="来源" width="100" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{row}">
                  <el-button size="small" type="danger" @click="deleteKeyPerson(row.id)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
</template>

<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
const {
  activeMenu, keyPersons, loadKeyPersons, personSearch, personTypeFilter, showCreatePerson
} = state
</script>
