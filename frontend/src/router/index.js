import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'showcase', component: () => import('../components/ShowcaseView.vue'), meta: { title: '系统首页', fullPage: true, public: true } },
  { path: '/input', name: 'input', component: () => import('../views/InputView.vue'), meta: { title: '文本录入', public: true } },
  { path: '/dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '数据看板' } },
  { path: '/alerts', name: 'alerts', component: () => import('../views/AlertsView.vue'), meta: { title: '预警中心' } },
  { path: '/upload', name: 'upload', component: () => import('../views/UploadView.vue'), meta: { title: '文件上传' } },
  { path: '/api', name: 'api', component: () => import('../views/ApiView.vue'), meta: { title: '接口管理' } },
  { path: '/overview', name: 'overview', component: () => import('../views/OverviewView.vue'), meta: { title: '案件管理' } },
  { path: '/case-detail', name: 'case-detail', component: () => import('../views/CaseDetailView.vue'), meta: { title: '案件详情' } },
  { path: '/workbench', name: 'workbench', component: () => import('../views/WorkbenchView.vue'), meta: { title: '办案工作台' } },
  { path: '/groups', name: 'groups', component: () => import('../views/GroupsView.vue'), meta: { title: '团伙画像' } },
  { path: '/details', name: 'details', component: () => import('../views/DetailsView.vue'), meta: { title: '深度分析' } },
  { path: '/network', name: 'network', component: () => import('../views/NetworkView.vue'), meta: { title: '关系图谱' } },
  { path: '/capital-flow', name: 'capital-flow', component: () => import('../views/CapitalFlowView.vue'), meta: { title: '资金流向' } },
  { path: '/dispatch', name: 'dispatch', component: () => import('../views/DispatchView.vue'), meta: { title: '预警派单' } },
  { path: '/key-persons', name: 'key-persons', component: () => import('../views/KeyPersonsView.vue'), meta: { title: '重点人员' } },
  { path: '/report', name: 'report', component: () => import('../views/ReportView.vue'), meta: { title: '报告生成' } },
  { path: '/status', name: 'status', component: () => import('../views/StatusView.vue'), meta: { title: '系统监控' } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { title: '系统管理' } },
  { path: '/chat', name: 'chat', component: () => import('../views/ChatView.vue'), meta: { title: 'AI对话助手' } },
  { path: '/:pathMatch(.*)*', name: 'not-found', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const PUBLIC_ROUTES = new Set(['showcase'])

router.beforeEach((to, from, next) => {
  if (to.meta?.public || PUBLIC_ROUTES.has(to.name)) {
    next()
    return
  }
  // 不再强制重定向到 showcase —— App.vue 的 login-overlay 会在非 fullPage
  // 路由上自动展示登录界面，登录成功后用户即可访问目标页面，避免循环重定向。
  next()
})

export default router
