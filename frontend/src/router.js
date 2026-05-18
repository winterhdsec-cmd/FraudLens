import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('./pages/DashboardPage.vue') },
  { path: '/input', name: 'input', component: () => import('./pages/InputPage.vue') },
  { path: '/overview', name: 'overview', component: () => import('./pages/OverviewPage.vue') },
  { path: '/case-detail', name: 'case-detail', component: () => import('./pages/CaseDetailPage.vue') },
  { path: '/groups', name: 'groups', component: () => import('./pages/GroupsPage.vue') },
  { path: '/network', name: 'network', component: () => import('./pages/NetworkPage.vue') },
  { path: '/report', name: 'report', component: () => import('./pages/ReportPage.vue') },
  { path: '/alerts', name: 'alerts', component: () => import('./pages/AlertsPage.vue') },
  { path: '/upload', name: 'upload', component: () => import('./pages/UploadPage.vue') },
  { path: '/details', name: 'details', component: () => import('./pages/DetailsPage.vue') },
  { path: '/capital-flow', name: 'capital-flow', component: () => import('./pages/CapitalFlowPage.vue') },
  { path: '/dispatch', name: 'dispatch', component: () => import('./pages/DispatchPage.vue') },
  { path: '/key-persons', name: 'key-persons', component: () => import('./pages/KeyPersonsPage.vue') },
  { path: '/api', name: 'api', component: () => import('./pages/ApiPage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router