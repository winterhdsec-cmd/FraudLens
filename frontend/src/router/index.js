import { createRouter, createWebHistory } from 'vue-router'
import InputView from '../views/InputView.vue'
import UploadView from '../views/UploadView.vue'
import ApiView from '../views/ApiView.vue'
import DashboardView from '../views/DashboardView.vue'
import AlertsView from '../views/AlertsView.vue'
import OverviewView from '../views/OverviewView.vue'
import CaseDetailView from '../views/CaseDetailView.vue'
import GroupsView from '../views/GroupsView.vue'
import DetailsView from '../views/DetailsView.vue'
import NetworkView from '../views/NetworkView.vue'
import CapitalFlowView from '../views/CapitalFlowView.vue'
import DispatchView from '../views/DispatchView.vue'
import KeyPersonsView from '../views/KeyPersonsView.vue'
import ReportView from '../views/ReportView.vue'
import AdminView from '../views/AdminView.vue'
import StatusView from '../views/StatusView.vue'

const routes = [
  { path: '/', redirect: '/input' },
  { path: '/input', name: 'input', component: InputView },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/alerts', name: 'alerts', component: AlertsView },
  { path: '/upload', name: 'upload', component: UploadView },
  { path: '/api', name: 'api', component: ApiView },
  { path: '/overview', name: 'overview', component: OverviewView },
  { path: '/case-detail', name: 'case-detail', component: CaseDetailView },
  { path: '/groups', name: 'groups', component: GroupsView },
  { path: '/details', name: 'details', component: DetailsView },
  { path: '/network', name: 'network', component: NetworkView },
  { path: '/capital-flow', name: 'capital-flow', component: CapitalFlowView },
  { path: '/dispatch', name: 'dispatch', component: DispatchView },
  { path: '/key-persons', name: 'key-persons', component: KeyPersonsView },
  { path: '/report', name: 'report', component: ReportView },
  { path: '/status', name: 'status', component: StatusView },
  { path: '/admin', name: 'admin', component: AdminView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router