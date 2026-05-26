import { createRouter, createWebHistory } from 'vue-router'
import ShowcaseView from '../components/ShowcaseView.vue'
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
  { path: '/', name: 'showcase', component: ShowcaseView, meta: { fullPage: true, public: true } },
  { path: '/input', name: 'input', component: InputView, meta: { public: true } },
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
  const token = sessionStorage.getItem('fraudlens_token')
  if (!token) {
    next({ name: 'showcase' })
    return
  }
  next()
})

export default router