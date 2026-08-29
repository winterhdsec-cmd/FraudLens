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

    <div class="admin-error" v-if="adminError">{{ adminError }}</div>
    <el-tabs v-model="adminTab" class="admin-tabs">
      <el-tab-pane label="用户管理" name="users">
        <div class="admin-toolbar">
          <div class="admin-toolbar-left">
            <el-button type="primary" size="small" @click="openAddUser">
              <span>➕</span> 添加用户
            </el-button>
          </div>
          <div class="admin-toolbar-right">
            <el-input
              v-model="userSearch"
              size="small"
              placeholder="搜索用户名/姓名/部门"
              clearable
              style="width: 220px"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <span class="user-count">共 {{ filteredUsers.length }} 人</span>
          </div>
        </div>
        <el-table :data="pagedUsers" style="width:100%" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="username" label="用户名" width="140" show-overflow-tooltip />
          <el-table-column prop="display_name" label="姓名" width="120" show-overflow-tooltip />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="s">
              <el-tag :type="roleTagType(s.row.role)" size="small">{{ roleLabel(s.row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="department" label="部门" show-overflow-tooltip />
          <el-table-column prop="phone" label="手机号" width="130" />
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="s">
              <el-tag :type="s.row.is_active ? 'success' : 'danger'" size="small">{{ s.row.is_active ? '正常' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="s">{{ formatTime(s.row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="s">
              <el-button size="small" @click="openEditUser(s.row)">编辑</el-button>
              <el-button
                size="small"
                :type="s.row.is_active ? 'warning' : 'success'"
                @click="handleToggleActive(s.row)"
                :disabled="s.row.username === 'admin'"
              >{{ s.row.is_active ? '禁用' : '启用' }}</el-button>
              <el-button size="small" type="danger" @click="handleDeleteUser(s.row)" :disabled="s.row.username === 'admin'">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="users-pagination" v-if="filteredUsers.length > userPageSize">
          <el-pagination
            v-model:current-page="userPage"
            :page-size="userPageSize"
            :total="filteredUsers.length"
            layout="total, prev, pager, next, jumper"
            background
            small
          />
        </div>
      </el-tab-pane>

      <!-- 添加用户对话框（此前按钮只有 showAddUser=true 但没有对话框，点击无反应） -->
      <el-dialog v-model="showAddUser" title="添加用户" width="420px" append-to-body>
        <el-form label-width="80px">
          <el-form-item label="用户名">
            <el-input v-model="addForm.username" placeholder="登录账号" />
          </el-form-item>
          <el-form-item label="初始密码">
            <el-input v-model="addForm.password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="addForm.display_name" placeholder="真实姓名" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="addForm.department" placeholder="如：刑侦大队" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="addForm.role" style="width:100%">
              <el-option label="民警/分析师" value="analyst" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAddUser = false">取消</el-button>
          <el-button type="primary" :loading="addLoading" @click="handleAddUser">创建</el-button>
        </template>
      </el-dialog>

      <!-- 编辑用户对话框（此前是 prompt 只改角色，且接口路径错误必然 404） -->
      <el-dialog v-model="showEditUser" title="编辑用户" width="420px" append-to-body>
        <el-form label-width="80px">
          <el-form-item label="用户名">
            <el-input :model-value="editForm.username" disabled />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="editForm.display_name" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="editForm.department" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="editForm.phone" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="editForm.role" style="width:100%" :disabled="editForm.username === 'admin'">
              <el-option label="民警/分析师" value="analyst" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEditUser = false">取消</el-button>
          <el-button type="primary" :loading="editLoading" @click="handleSaveUser">保存</el-button>
        </template>
      </el-dialog>

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
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { changePassword, updateUser, deleteUser, createUser, getOperationLogs, getAiConfig, saveAiConfig } from '../api.js'
import { useAppState } from '../composables/useAppState.js'

const state = useAppState()
const { activeMenu } = state

const adminTab = ref('users')
const userList = ref([])
const logList = ref([])
const adminError = ref('')
const pwForm = ref({ old: '', new: '' })
const pwLoading = ref(false)
const useCelery = ref(false)
const aiConfig = ref({ api_key: '', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' })
const aiConfigured = ref(false)
const keyPreview = ref('')
const aiConfigLoading = ref(false)

// ===== 用户管理：搜索 + 分页 =====
const userSearch = ref('')
const userPage = ref(1)
const userPageSize = 20
const filteredUsers = computed(() => {
  const kw = userSearch.value.trim().toLowerCase()
  if (!kw) return userList.value
  return userList.value.filter(u =>
    (u.username || '').toLowerCase().includes(kw) ||
    (u.display_name || '').toLowerCase().includes(kw) ||
    (u.department || '').toLowerCase().includes(kw)
  )
})
const pagedUsers = computed(() => {
  const start = (userPage.value - 1) * userPageSize
  return filteredUsers.value.slice(start, start + userPageSize)
})
// 搜索词变化时回到第一页，避免停在越界空白页
watch(userSearch, () => { userPage.value = 1 })

const roleLabel = (r) => ({ admin: '管理员', analyst: '民警/分析师', police: '民警' }[r] || r)
const roleTagType = (r) => (r === 'admin' ? 'danger' : 'info')
const formatTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '')

async function loadUsers() {
  try {
    const { default: api } = await import('../api.js')
    const r = await api.get('/api/auth/users')
    userList.value = r.data.users || []
    adminError.value = ''
    if (!userList.value.length) {
      adminError.value = '暂未获取到用户数据，请确认登录状态'
    }
  } catch (e) {
    console.warn('用户列表API不可用:', e)
    adminError.value = '获取用户列表失败: ' + (e.response?.data?.error || e.message || '网络错误')
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

// ===== 添加用户 =====
const showAddUser = ref(false)
const addLoading = ref(false)
const addForm = ref({ username: '', password: '', display_name: '', department: '', role: 'analyst' })

function openAddUser() {
  addForm.value = { username: '', password: '', display_name: '', department: '', role: 'analyst' }
  showAddUser.value = true
}

async function handleAddUser() {
  const f = addForm.value
  if (!f.username || !f.password) { ElMessage.warning('用户名和密码不能为空'); return }
  if (f.password.length < 6) { ElMessage.warning('密码长度至少 6 位'); return }
  addLoading.value = true
  try {
    const res = await createUser(f)
    if (res.success) {
      // 后端 register 固定 role=analyst；需要管理员时创建后再 PUT 改角色
      if (f.role === 'admin' && res.user?.id) {
        await updateUser(res.user.id, { role: 'admin' })
      }
      ElMessage.success('用户已创建')
      showAddUser.value = false
      loadUsers()
    } else {
      ElMessage.error(res.error || '创建失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.response?.data?.detail || '创建失败')
  } finally {
    addLoading.value = false
  }
}

// ===== 编辑用户 =====
const showEditUser = ref(false)
const editLoading = ref(false)
const editForm = ref({ id: null, username: '', display_name: '', department: '', phone: '', role: 'analyst' })

function openEditUser(user) {
  editForm.value = {
    id: user.id,
    username: user.username,
    display_name: user.display_name || '',
    department: user.department || '',
    phone: user.phone || '',
    role: user.role || 'analyst'
  }
  showEditUser.value = true
}

async function handleSaveUser() {
  editLoading.value = true
  try {
    const { id, username, ...data } = editForm.value
    const res = await updateUser(id, data)
    if (res.success) {
      ElMessage.success('已保存')
      showEditUser.value = false
      loadUsers()
    } else {
      ElMessage.error(res.error || '保存失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '保存失败')
  } finally {
    editLoading.value = false
  }
}

async function handleToggleActive(user) {
  try {
    const res = await updateUser(user.id, { is_active: !user.is_active })
    if (res.success) {
      ElMessage.success(user.is_active ? '已禁用' : '已启用')
      loadUsers()
    } else {
      ElMessage.error(res.error || '操作失败')
    }
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleDeleteUser(user) {
  if (user.username === 'admin' || user.role === 'admin') {
    ElMessage.warning('管理员账户不能删除')
    return
  }
  try {
    await ElMessageBox.confirm('确认删除用户 ' + user.username + '？', '警告', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    const res = await deleteUser(user.id)
    if (res.success) {
      ElMessage.success('已删除')
      loadUsers()
    } else {
      ElMessage.error(res.error || '删除失败')
    }
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

.admin-error {
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.25);
  color: #f87171;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

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
  gap: 12px;
}
.user-count {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}
.users-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
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