PATH = r'c:\Users\hd\Desktop\学习生涯\项目\FraudLens\frontend\src\App.vue'

with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. sidebar
sep = '</el-menu>\n\n      <div class="system-status">'
idx = content.find('<el-menu :default-active')
end = content.find(sep, idx) + 9  # len('</el-menu>')
sidebar = """      <el-menu :default-active="activeMenu" class="side-menu" @select="handleMenuSelect">
        <div class="menu-group">
          <div class="menu-group-title">案件办理</div>
          <el-menu-item index="input">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f4dd</span><span class="menu-text">录入分析</span></div></template>
          </el-menu-item>
          <el-menu-item index="overview">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f4cb</span><span class="menu-text">案件总览</span></div></template>
          </el-menu-item>
          <el-menu-item index="case-detail">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f50d</span><span class="menu-text">案件详情</span></div></template>
          </el-menu-item>
          <el-menu-item index="groups">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f465</span><span class="menu-text">团伙画像</span></div></template>
          </el-menu-item>
        </div>
        <div class="menu-group">
          <div class="menu-group-title">监测分析</div>
          <el-menu-item index="dashboard">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f4ca</span><span class="menu-text">数据看板</span></div></template>
          </el-menu-item>
          <el-menu-item index="network">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f578\ufe0f</span><span class="menu-text">关联网络</span></div></template>
          </el-menu-item>
        </div>
        <div class="menu-group">
          <div class="menu-group-title">输出报告</div>
          <el-menu-item index="report">
            <template #title><div class="menu-item-content"><span class="menu-icon">\U0001f4c4</span><span class="menu-text">报告生成</span></div></template>
          </el-menu-item>
        </div>
      </el-menu>"""

content = content[:idx] + sidebar + sep + content[end:]

# 2. placeholder
content = content.replace('请粘贴聊天记录、报警文本或涉案信息...', '粘贴聊天记录或案情描述，点击「开始研判」即可分析')
# Remove the extra format lines after placeholder
content = content.replace('&#10;&#10;支持格式：&#10;\u2022 聊天记录截图转文字&#10;\u2022 报警笔录&#10;\u2022 涉案资金流水描述&#10;\u2022 诈骗话术文本', '')

# 3. fake data
for old, new in [
    ("'王女士'", "'\u2014'"),
    ("'138****5678'", "'\u2014'"),
    ("'公司职员'", "'\u2014'"),
    ("'广东省深圳市'", "'\u2014'"),
    ("'0755-8888****'", "'\u2014'"),
    ("'广东深圳'", "'\u2014'"),
    ("'jd-security.com'", "'\u2014'"),
    ("'192.168.***.***'", "'\u2014'"),
    ("'23个'", "'\u2014'"),
    ("'3-5层'", "'\u2014'"),
    ("'85%'", "'\u2014'"),
    ("'***1234'", "'\u2014'"),
    ("'多层分散'", "'\u2014'"),
    ("'最终去向'", "'\u2014'"),
    ("'张警官'", "'\u2014'"),
    ("'李警官'", "'\u2014'"),
    ("'主办民警'", "'\u2014'"),
    ("'协办民警'", "'\u2014'"),
]:
    content = content.replace(old, new)

# '广东省' after '案发地区' context
content = content.replace("'广东省'", "'\u2014'")

# 4. long description
for desc in [
    "'2024年3月15日，受害人王女士接到自称\u201c京东客服\u201d的电话，对方准确报出其个人信息后，称其名下有一笔账户异常需要处理，否则将影响征信。在对方的诱导下，王女士通过手机银行转账至对方提供的\u201c安全账户\u201d，共计转账125,800元。转账后对方失联，王女士才发现被骗。'",
    "'2024年3月15日，受害人王女士接到自称京东客服的电话，对方准确报出其个人信息后，称其名下有一笔账户异常需要处理，否则将影响征信。在对方的诱导下，王女士通过手机银行转账至对方提供的安全账户，共计转账125,800元。转账后对方失联，王女士才发现被骗。'",
]:
    content = content.replace(desc, "'暂无详细案情描述'")

# 5. hasAnalysisResult computed
if 'hasAnalysisResult' not in content:
    content = content.replace("const generatingReport = ref(false)", "const generatingReport = ref(false)\nconst hasAnalysisResult = computed(() => cases.value.length > 0 || gangs.value.length > 0)")

# 6. action guide
content = content.replace(
    '</div>\n        </div>\n\n        <div v-if="activeMenu === \'upload\'" class="view-section">',
    '''          <div v-if="hasAnalysisResult" class="action-guide" style="margin-top:16px;text-align:center">
            <div class="guide-buttons" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
              <el-button type="primary" @click="activeMenu = 'overview'">\U0001f4cb 查看案件列表</el-button>
              <el-button @click="activeMenu = 'groups'">\U0001f465 查看团伙画像</el-button>
              <el-button @click="activeMenu = 'report'">\U0001f4c4 生成报告</el-button>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'upload'" class="view-section">'''
)

# 7. today_cases KPI
content = content.replace(
    '</div>\n          </div>\n\n          <div class="overview-charts">',
    '''            </div>
            <div class="stat-card tech-card">
              <div class="stat-icon-wrapper info">
                <span class="stat-icon">\U0001f4c5</span>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardData.today_cases ?? '-' }}</div>
                <div class="stat-label">今日新增</div>
                <div class="stat-trend up">
                  <span>本日录入</span>
                </div>
              </div>
            </div>
          </div>

          <div class="overview-charts">'''
)

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')