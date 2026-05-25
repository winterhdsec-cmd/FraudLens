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
            <div class="info-card-title"><span class="title-accent"></span>系统状态</div>
            <div class="info-row"><span>运行模式</span><span>{{ useCelery ? 'Celery 异步' : '同步' }}</span></div>
            <div class="info-row"><span>数据库</span><span class="status-online">已连接</span></div>
            <div class="info-row"><span>AI引擎</span><span class="status-online">在线</span></div>
            <div class="info-row"><span>JWT过期</span><span>24小时</span></div>
          </div>
          <div class="info-card tech-card">
            <div class="info-card-title"><span class="title-accent"></span>修改密码</div>
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

      <el-tab-pane label="AI 配置" name="ai-config">
        <div class="admin-info-grid">
          <div class="info-card tech-card">
            <div class="info-card-title"><span class="title-accent"></span>AI 模型配置</div>
            <el-form label-width="100px" class="admin-form">
              <el-form-item label="API Key">
                <el-input v-model="aiConfig.api_key" type="password" show-password placeholder="请输入 API Key" size="small" />
              </el-form-item>
              <el-form-item label="Base URL">
                <el-input v-model="aiConfig.base_url" placeholder="https://api.deepseek.com/v1" size="small" />
              </el-form-item>
              <el-form-item label="Model">
                <el-input v-model="aiConfig.model" placeholder="deepseek-chat" size="small" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="small" @click="handleSaveAiConfig" :loading="aiConfigLoading">保存配置</el-button>
              </el-form-item>
            </el-form>
          </div>
          <div class="info-card tech-card">
            <div class="info-card-title"><span class="title-accent"></span>当前配置状态</div>
            <div class="info-row"><span>配置状态</span><span :class="aiConfigured ? 'status-online' : 'status-offline'">{{ aiConfigured ? '已配置' : '未配置' }}</span></div>
            <div class="info-row"><span>Key 预览</span><span>{{ keyPreview || '—' }}</span></div>
            <div class="info-row"><span>Base URL</span><span>{{ aiConfig.base_url || '—' }}</span></div>
            <div class="info-row"><span>Model</span><span>{{ aiConfig.model || '—' }}</span></div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { changePassword, updateUser, deleteUser, getOperationLogs, getAiConfig, saveAiConfig } from '../api.js'
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
const aiConfig = ref({ api_key: '', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' })
const aiConfigured = ref(false)
const keyPreview = ref('')
const aiConfigLoading = ref(false)

async function loadUsers() {
  try {
    const { default: api } = await import('../api.js')
    const r = await api.get('/api/auth/users')
    userList.value = r.data.users || []
  } catch (e) {
    console.warn('用户列表API不可用')
  }
}

async function loadLogs() {
  try {
    const data = await getOperationLogs()
    logList.value = data.logs || []
  } catch (e) {
    console.warn('操作日志API不可用')
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
  if (user.username === 'admin' || user.role === 'admin') {
    ElMessage.warning('管理员账户不能删除')
    return
  }
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

async function loadAiConfig() {
  try {
    const r = await getAiConfig()
    const d = r.data
    if (d && d.success) {
      aiConfigured.value = d.configured || false
      keyPreview.value = d.key_preview || ''
      if (d.base_url) aiConfig.value.base_url = d.base_url
      if (d.model) aiConfig.value.model = d.model
    } else {
      aiConfigured.value = false
      keyPreview.value = ''
    }
  } catch (e) {
    aiConfigured.value = false
    keyPreview.value = ''
  }
}

async function handleSaveAiConfig() {
  if (!aiConfig.value.api_key) {
    ElMessage.warning('请填写 API Key')
    return
  }
  aiConfigLoading.value = true
  try {
    await saveAiConfig(aiConfig.value)
    ElMessage.success('AI 配置已保存')
    loadAiConfig()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '保存失败')
  } finally {
    aiConfigLoading.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadLogs()
  loadAiConfig()
})
</script>

<style scoped>
.section-header {
  background: linear-gradient(135deg, rgba(15,23,42,0.6), rgba(10,18,36,0.3));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}
.section-header::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0,198,255,0.4), transparent);
}
.section-header::after {
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 100px; height: 100px;
  background: radial-gradient(circle, rgba(0,198,255,0.04) 0%, transparent 70%);
  pointer-events: none;
}
.section-title { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
.section-title .title-icon { margin-right: 6px; }
.section-desc { font-size: 13px; color: #64748b; margin-top: 4px; }

.admin-tabs {
  position: relative;
}
.admin-tabs :deep(.el-tabs__header) {
  margin: 0 0 20px;
  border-bottom: 1px solid rgba(0,198,255,0.08);
  background: rgba(10,14,26,0.3);
  border-radius: 12px 12px 0 0;
  padding: 4px 4px 0;
}
.admin-tabs :deep(.el-tabs__nav-wrap) {
  padding-left: 4px;
}
.admin-tabs :deep(.el-tabs__item) {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  height: 42px;
  line-height: 42px;
  padding: 0 22px;
  transition: all 0.3s ease;
  border-radius: 10px 10px 0 0;
}
.admin-tabs :deep(.el-tabs__item:hover) {
  color: #94a3b8;
  background: rgba(0,198,255,0.03);
}
.admin-tabs :deep(.el-tabs__item.is-active) {
  color: #00E5FF;
  background: rgba(0,198,255,0.08);
  font-weight: 600;
}
.admin-tabs :deep(.el-tabs__active-bar) {
  display: none;
}
.admin-tabs :deep(.el-tabs__content) {
  background: rgba(15,23,42,0.4);
  border: 1px solid rgba(0,198,255,0.06);
  border-radius: 0 0 12px 12px;
  padding: 20px;
  min-height: 400px;
}

/* Admin toolbar */
.admin-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(0,198,255,0.06);
  border-radius: 10px;
}
.admin-toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.admin-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* System Info cards */
.admin-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.admin-info-grid .info-card {
  background: linear-gradient(135deg, rgba(10,20,40,0.6), rgba(15,25,45,0.4));
  border: 1px solid rgba(0,198,255,0.08);
  border-radius: 14px;
  padding: 24px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.admin-info-grid .info-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0,198,255,0.25), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}
.admin-info-grid .info-card:hover {
  border-color: rgba(0,198,255,0.18);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.admin-info-grid .info-card:hover::before {
  opacity: 1;
}
.admin-info-grid .info-card-title {
  font-size: 15px;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.3px;
}
.admin-info-grid .info-card-title .title-accent {
  width: 3px;
  height: 16px;
  border-radius: 2px;
  background: #00E5FF;
}
.admin-info-grid .info-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  font-size: 13px;
  color: #94a3b8;
  border-bottom: 1px solid rgba(0,198,255,0.04);
  transition: all 0.2s;
}
.admin-info-grid .info-row:last-child {
  border-bottom: none;
}
.admin-info-grid .info-row:hover {
  padding-left: 4px;
  color: #e2e8f0;
}
.admin-info-grid .info-row span:last-child {
  font-weight: 500;
  color: #e2e8f0;
}
.admin-info-grid .status-online {
  color: #10b981 !important;
  text-shadow: 0 0 8px rgba(16,185,129,0.3);
}
.admin-info-grid .status-offline {
  color: #ef4444 !important;
}

/* Password form */
.admin-form {
  margin-top: 4px;
}
.admin-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.admin-form :deep(.el-form-item__label) {
  color: #94a3b8;
  font-size: 13px;
}
.admin-form :deep(.el-input__wrapper) {
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(0,198,255,0.1);
  border-radius: 8px;
  box-shadow: none;
  transition: all 0.3s;
}
.admin-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(0,198,255,0.25);
}
.admin-form :deep(.el-input__wrapper.is-focus) {
  border-color: #00E5FF;
  box-shadow: 0 0 10px rgba(0,229,255,0.15);
}
.admin-form :deep(.el-input__inner) {
  color: #e2e8f0;
}
.admin-form :deep(.el-input__inner::placeholder) {
  color: #64748b;
}
.admin-form .el-button--primary {
  width: 100%;
  height: 38px;
  font-weight: 600;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #00E5FF, #0099CC);
  border: none;
  color: #020812;
  transition: all 0.3s ease;
  border-radius: 8px;
}
.admin-form .el-button--primary:hover {
  box-shadow: 0 4px 16px rgba(0,229,255,0.35);
  transform: translateY(-1px);
}

/* Log detail */
.log-detail {
  font-size: 12px;
  color: #94a3b8;
  word-break: break-all;
  display: block;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.2s;
}
.log-detail:hover {
  max-height: none;
  color: #e2e8f0;
}

/* Table enhancements */
.admin-tabs :deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}
.admin-tabs :deep(.el-table th.el-table__cell) {
  background: rgba(0,0,0,0.3) !important;
  color: #94a3b8;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid rgba(0,198,255,0.1);
}
.admin-tabs :deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid rgba(0,198,255,0.04);
  color: #e2e8f0;
  font-size: 13px;
}
.admin-tabs :deep(.el-table__body tr:hover > td) {
  background: rgba(0,198,255,0.04) !important;
}
.admin-tabs :deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(0,198,255,0.015);
}
.admin-tabs :deep(.el-table__body .el-button) {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 6px;
}
.admin-tabs :deep(.el-table__body .el-button--default) {
  background: rgba(0,198,255,0.1);
  border-color: rgba(0,198,255,0.2);
  color: #e2e8f0;
  transition: all 0.3s;
}
.admin-tabs :deep(.el-table__body .el-button--default:hover) {
  background: rgba(0,198,255,0.2);
  border-color: rgba(0,198,255,0.35);
  color: #00E5FF;
}
.admin-tabs :deep(.el-table__body .el-button--danger) {
  background: rgba(239,68,68,0.1);
  border-color: rgba(239,68,68,0.2);
  color: #ef4444;
  transition: all 0.3s;
}
.admin-tabs :deep(.el-table__body .el-button--danger:hover) {
  background: rgba(239,68,68,0.2);
  border-color: rgba(239,68,68,0.4);
  box-shadow: 0 0 12px rgba(239,68,68,0.15);
}
</style>