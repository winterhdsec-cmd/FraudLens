<template>
<div class="view-section">
          <div class="section-header">
            <div class="header-left">
              <h2 class="section-title"><span class="title-icon"><el-icon><User /></el-icon></span>重点人员库</h2>
              <p class="section-desc">前科人员 / 高危人员管理，研判时自动碰撞比对</p>
            </div>
            <div class="header-actions">
              <el-input v-model="personSearch" placeholder="姓名/电话/身份证" style="width:200px" size="small" clearable @clear="reloadPersons" @keyup.enter="reloadPersons" />
              <el-select v-model="personTypeFilter" placeholder="人员类型" size="small" style="width:120px" @change="reloadPersons">
                <el-option label="全部" value="" />
                <el-option label="前科人员" value="前科人员" />
                <el-option label="高危人员" value="高危人员" />
                <el-option label="在逃人员" value="在逃人员" />
              </el-select>
              <el-button type="primary" size="small" @click="showCreatePerson = true">新增人员</el-button>
            </div>
          </div>
          <div class="persons-container" v-loading="personsLoading" element-loading-text="正在加载人员数据…">
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
                  <el-button size="small" type="danger" @click="onRemovePerson(row)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-if="!keyPersons.length && !personSearch && !personsLoading" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon"><el-icon><User /></el-icon></div>
              <h3 class="empty-title">暂无重点人员</h3>
              <p class="empty-desc">研判分析中碰撞到的人员会自动添加到重点人员库</p>
              <!-- 空态给一个可以立刻做的动作，而不是只告诉用户"为什么是空的" -->
              <div style="margin-top: 14px">
                <el-button type="primary" @click="showCreatePerson = true">手动新增人员</el-button>
              </div>
            </div>
          </div>
        </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAppState } from '../composables/useAppState.js'
import { confirmDanger } from '../utils/confirm.js'
const state = useAppState()
const {
  activeMenu, keyPersons, loadKeyPersons, personSearch, personTypeFilter, showCreatePerson,
  deleteKeyPerson
} = state

// 人员列表加载态：数据未回来时给遮罩，避免空白页让人以为界面坏了
const personsLoading = ref(false)
async function reloadPersons() {
  personsLoading.value = true
  try {
    await loadKeyPersons()
  } finally {
    personsLoading.value = false
  }
}

/**
 * 移除重点人员。
 *
 * 原先按钮直接绑 deleteKeyPerson —— 点了就删、没有任何确认，而这是不可逆的数据删除。
 * 统一走 confirmDanger（确认文案固定为「做什么 + 什么后果」）。
 */
async function onRemovePerson(row) {
  const ok = await confirmDanger({
    title: '移除重点人员',
    action: `将「${row?.name || '该人员'}」移出重点人员库`,
    detail: '该记录会从重点人员列表删除，后续人员碰撞比对不再纳入此人。此操作不可撤销。',
    confirmText: '确认移除'
  })
  if (!ok) return
  await deleteKeyPerson(row.id)
}

onMounted(() => reloadPersons())
</script>
