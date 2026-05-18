"""Fix all view files: properly destructure injected appState"""
import os, re

VIEWS = r'c:\Users\hd\Desktop\学习生涯\项目\FraudLens\frontend\src\views'

# Complete list of all exposed state properties
ALL_PROPS = [
    'activeMenu', 'loading', 'inputText', 'uploadedImages',
    'gangs', 'cases', 'selectedGang', 'selectedCase', 'viewMode',
    'gangSearchKeyword', 'riskFilter', 'detailTab', 'networkView',
    'generatingReport', 'parsedReport',
    'flowSearchCaseId', 'capitalFlows', 'flowGraphData',
    'dispatchOrders', 'dispatchStatusFilter', 'showCreateDispatch',
    'keyPersons', 'personSearch', 'personTypeFilter', 'showCreatePerson',
    'dashboardData', 'dashboardLoading',
    'alerts', 'alertsLoading', 'resolvingAlert',
    'reportConfig', 'reportPreview',
    'loginForm', 'loginLoading', 'loginError',
    'apiSources', 'apiDataPreview',
    'pieChartRef', 'lineChartRef',
    'dashboardRiskChartRef', 'dashboardStatusChartRef',
    'dashboardBarChartRef', 'dashboardTrendChartRef',
    'totalAmount', 'totalAmountFormatted', 'successRate',
    'textLineCount', 'extractedKeywords',
    'hasTime', 'hasAmount', 'hasPhone', 'hasMethod',
    'connectedSources', 'hasApiData', 'filteredGangs',
    'features', 'relationNodes', 'relationLines',
    'caseEvidence', 'investigationSteps',
    'defaultMethodFlow', 'defaultKeywords',
    'caseTypeStats', 'regionStats',
    'getParticleStyle', 'getRiskType', 'getEventType',
    'getGangById', 'getFeatureIcon', 'getReportTitle',
    'handleMenuSelect', 'handleLogin', 'handleLogout',
    'clearInput', 'clearImages', 'removeImage', 'loadDemo',
    'handleBeforeUpload', 'startAnalysis',
    'startImageAnalysis', 'toggleApiSource', 'syncApiData',
    'fetchBankData', 'fetchPoliceData', 'fetchAntiFraudData',
    'importApiData', 'startApiAnalysis',
    'generateReport', 'printReport', 'downloadReport',
    'loadDashboard', 'loadAlerts',
    'loadCapitalFlows', 'loadFlowGraph', 'loadFlowData',
    'addFlowRecord',
    'loadDispatchOrders', 'signDispatch', 'showCompleteDispatch',
    'loadKeyPersons', 'deleteKeyPerson',
    'handleResolveAlert', 'getAlertType', 'getConfidenceColor',
    'viewCaseFromDashboard',
    'selectGang', 'viewGangDetail', 'viewCaseDetail',
    'viewRelatedGang',
    'features', 'relationNodes', 'relationLines',
    'caseEvidence', 'investigationSteps',
    'defaultMethodFlow', 'defaultKeywords',
    'caseTypeStats', 'regionStats',
    'gangIcons', 'formatAmount', 'navigateTo'
]

for fname in sorted(os.listdir(VIEWS)):
    if not fname.endswith('.vue'):
        continue
    fp = os.path.join(VIEWS, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find what props this file actually uses in template
    template = content[:content.index('</template>')] if '</template>' in content else ''
    used_props = set()
    for prop in ALL_PROPS:
        # Check if referenced in template
        if prop in template:
            used_props.add(prop)

    # Replace the inject line with destructured version
    old_script = 'const state = inject("appState")'
    if old_script not in content:
        # already fixed or different pattern
        print(f'{fname}: already fixed or different pattern')
        continue

    if used_props:
        sorted_props = sorted(used_props)
        # Break into lines of 6 for readability
        lines = []
        for i in range(0, len(sorted_props), 6):
            chunk = sorted_props[i:i+6]
            lines.append('  ' + ', '.join(chunk))
        joined = ',\n'.join(lines)
        new_script = f'const state = inject("appState")\nconst {{\n{joined}\n}} = state'
    else:
        new_script = old_script  # keep as-is if nothing needed

    content = content.replace(old_script, new_script)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'{fname}: {len(used_props)} props destructured')

print('ALL DONE')