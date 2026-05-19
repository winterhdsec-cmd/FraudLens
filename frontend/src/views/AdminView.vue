<template>
  <div class="view-section">
    <div class="section-header">
      <div class="header-left">
        <h2 class="section-title">
          <span class="title-icon">⚙️</span>
          系统管理
        </h2>
        <p class="section-desc">用户管理、操作审计与系统配置</p>
      </div>
    </div>

    <el-tabs v-model="adminTab" class="admin-tabs">
      <el-tab-pane label="用户管理" name="users">
        <div class="admin-toolbar">
          <el-button type="primary" size="small" @click="showAddUser = true">
            <span>➕</span> 添加用户
          </el-button>
        </div>
        <el-table :data="userList" style="width:100%" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="display_name" label="姓名" width="120" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="s">
              <el-tag :type="s.row.role === 'admin' ? 'danger' : 'info'" size="small">{{ s.row.role === 'admin' ? '管理员' : '民警' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="department" label="部门" />
          <el-table-column prop="phone" label="手机号" width="130" />
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="s">
              <el-tag :type="s.row.is_active ? 'success' : 'danger'" size="small">{{ s.row.is_active ? '正常' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="s">
              <el-button size="small" @click="editUser(s.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDeleteUser(s.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="操作日志" name="logs">
        <el-table :data="logList" style="width:100%" stripe>
          <el-table-column prop="id" label="#" width="50" />
          <el-table-column prop="username" label="用户" width="100" />
          <el-table-column prop="action" label="操作" width="120" />
          <el-table-column prop="target" label="目标" width="150" />
          <el-table-column prop="detail" label="详情" min-width="200">
            <template #default="s">
              <span class="log-detail">{{ typeof s.row.detail === 'object' ? JSON.stringify(s.row.detail) : s.row.detail }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP" width="140" />
          <el-table-column prop="created_at" label="时间" width="160" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="系统信息" name="info">
        <div class="admin-info-grid">
          <div class="info-card tech-card">
            <div class="info-card-title">系统状态</div>
            <div class="info-row"><span>运行模式</span><span>{{ useCelery ? 'Celery 异步' : '同步' }}</span></div>
            <div class="info-row"><span>数据库</span><span class="status-online">已连接</span></div>
            <div class="info-row"><span>AI引擎</span><span class="status-online">在线</span></div>
            <div class="info-row"><span>JWT过期</span><span>24小时</span></div>
          </div>
          <div class="info-card tech-card">
            <div class="info-card-title">修改密码</div>
            <el-form label-width="100px" class="admin-form">
              <el-form-item label="当前密码">
                <el-input v-model="pwForm.old" type="password" size="small" />
              </el-form-item>
              <el-form-item label="新密码">
                <el-input v-model="pwForm.new" type="password" size="small" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="small" @click="handleChangePw" :loading="pwLoading">确认修改</el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { changePassword, updateUser, deleteUser, getOperationLogs } from '../api.js'
import { useAppState } from '../composables/useAppState.js'

const state = useAppState()
const { activeMenu } = state

const adminTab = ref('users')
const userList = ref([])
const logList = ref([])
const showAddUser = ref(false)
const pwForm = ref({ old: '', new: '' })
const pwLoading = ref(false)
const useCelery = ref(false)

async function loadUsers() {
  try {
    const { default: api } = await import('../api.js')
    const r = await api.get('/api/auth/users')
    userList.value = r.data.users || []
  } catch (e) {
    console.error(e)
  }
}

async function loadLogs() {
  try {
    const data = await getOperationLogs()
    logList.value = data.logs || []
  } catch (e) {
    console.error(e)
  }
}

function editUser(user) {
  ElMessageBox.prompt('角色 (admin/police)', '编辑用户', {
    inputValue: user.role,
    inputPlaceholder: 'admin 或 police'
  }).then(async ({ value }) => {
    await updateUser(user.id, { role: value })
    ElMessage.success('已更新')
    loadUsers()
  }).catch(() => {})
}

async function handleDeleteUser(user) {
  try {
    await ElMessageBox.confirm('确认删除用户 ' + user.username + '？', '警告', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('已删除')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleChangePw() {
  if (!pwForm.value.old || !pwForm.value.new) {
    ElMessage.warning('请填写完整')
    return
  }
  pwLoading.value = true
  try {
    const data = await changePassword(pwForm.value.old, pwForm.value.new)
    if (data.success) {
      ElMessage.success('密码已修改')
      pwForm.value = { old: '', new: '' }
    } else {
      ElMessage.error(data.error || '修改失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '修改失败')
  } finally {
    pwLoading.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadLogs()
})
</script>

<style scoped>
.admin-tabs .el-table,
.admin-tabs .el-table__body,
.admin-tabs .el-table__header,
.admin-tabs .el-table__body-wrapper,
.admin-tabs .el-table__inner-wrapper,
.admin-tabs .el-table__footer {
  background: transparent !important;
  color: #e2e8f0;
}
.admin-tabs .el-table th.el-table__cell {
  background: rgba(0, 0, 0, 0.3) !important;
  color: #94a3b8;
  border-bottom: 1px solid rgba(0, 198, 255, 0.1);
}
.admin-tabs .el-table tr.el-table__row {
  background: transparent !important;
}
.admin-tabs .el-table tr.el-table__row--striped td {
  background: rgba(0, 0, 0, 0.15) !important;
}
.admin-tabs .el-table td.el-table__cell {
  border-bottom: 1px solid rgba(0, 198, 255, 0.05);
  color: #e2e8f0;
}
.admin-tabs .el-table--enable-row-hover .el-table__body tr:hover > td {
  background: rgba(0, 198, 255, 0.05) !important;
}
</style>