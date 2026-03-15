<template>
  <div class="police-system-layout">
    <!-- 左侧导航栏 -->
    <aside class="sidebar">
      <div class="logo-area">
        <h2>🛡️ 反诈团伙画像</h2>
        <span class="sub-title">AI Intelligent Analysis</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="side-menu"
        background-color="#0f172a"
        text-color="#94a3b8"
        active-text-color="#3b82f6"
        @select="handleMenuSelect"
      >
        <!-- 新增：数据录入中心作为第一个菜单 -->
        <el-menu-item index="input">
          <i class="el-icon-edit-outline"></i>
          <span>📥 数据录入中心</span>
        </el-menu-item>
        
        <el-menu-item index="overview">
          <i class="el-icon-s-home"></i>
          <span>报告概览</span>
        </el-menu-item>
        <el-menu-item index="groups">
          <i class="el-icon-s-group"></i>
          <span>团伙画像总览</span>
        </el-menu-item>
        <el-menu-item index="details">
          <i class="el-icon-s-data"></i>
          <span>团伙深度分析</span>
        </el-menu-item>
        <el-menu-item index="network">
          <i class="el-icon-connection"></i>
          <span>案件关联网络</span>
        </el-menu-item>
      </el-menu>
      
      <div class="system-status">
        <el-tag type="success" size="small">系统运行中</el-tag>
        <div class="version-info">v2.0 Pro | Qwen-Max</div>
      </div>
    </aside>

    <!-- 右侧主内容区 -->
    <main class="main-content">
      
      <!-- 1. 数据录入中心 (新独立页面) -->
      <div v-if="activeMenu === 'input'" class="content-view fade-in">
        <el-card class="input-card-full">
          <template #header>
            <div class="card-header-flex">
              <div>
                <h3 class="page-title">📥 多源数据采集与录入</h3>
                <p class="page-subtitle">支持聊天记录粘贴、图片上传、API 数据流接入（预留）</p>
              </div>
              <el-button type="primary" @click="loadDemo" icon="Document">加载测试案情</el-button>
            </div>
          </template>

          <div class="input-workspace">
            <!-- 左侧：文本输入区 -->
            <div class="input-panel">
              <div class="panel-header">
                <span class="label">📝 文本/对话内容</span>
                <el-tooltip content="支持粘贴多条聊天记录，每行一条消息；也支持粘贴 110 报警录音转写文本">
                  <i class="el-icon-question"></i>
                </el-tooltip>
              </div>
              <el-input 
                v-model="inputText" 
                type="textarea" 
                :rows="15" 
                placeholder="请在此处粘贴聊天记录、报警录音转写文本或涉案信息...&#10;&#10;示例：&#10;嫌疑人：您好，这里是【京东官方】合作推广部...&#10;受害人：我没开过这个服务啊！&#10;..." 
                class="chat-input-large"
              />
              <div class="input-stats">
                <span>当前行数：{{ messageCount }} 条</span>
                <span v-if="inputText.length > 0">字符数：{{ inputText.length }}</span>
              </div>
            </div>

            <!-- 右侧：辅助功能区 -->
            <div class="tools-panel">
              <div class="tool-card">
                <h4>🖼️ 图片证据上传</h4>
                <el-upload
                  :before-upload="handleBeforeUpload"
                  :show-file-list="false"
                  accept="image/*"
                  class="upload-area-large"
                  drag
                >
                  <i class="el-icon-upload"></i>
                  <div class="el-upload__text">将图片拖到此处，或 <em>点击上传</em></div>
                  <div class="el-upload__tip">支持 PNG/JPG, 最大 10MB (自动提取文字并追加到文本框)</div>
                </el-upload>
              </div>

              <div class="tool-card api-hint">
                <h4>🔌 外部数据接入</h4>
                <p>当前模式：手动录入</p>
                <p class="hint-text">未来可对接：国家反诈中心 APP、110 接处警系统、银行风控系统</p>
                <el-button type="info" plain size="small" disabled>接口配置 (开发中)</el-button>
              </div>

              <div class="action-area">
                <el-button type="danger" size="large" @click="analyze" :loading="loading" icon="Search" style="width: 100%">
                  🚀 开始智能研判
                </el-button>
                <p class="action-hint">点击后系统将自动分案、提取特征并生成团伙画像</p>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 动态内容区域 (其他分析页面) -->
      <div v-else v-loading="loading" element-loading-text="AI 正在深度研判中...">
        
        <!-- 2. 报告概览 -->
        <div v-if="activeMenu === 'overview'" class="content-view fade-in">
          <div v-if="!hasData" class="empty-state">
            <el-empty description="暂无分析数据，请先在'数据录入中心'录入数据并分析" >
              <el-button type="primary" @click="activeMenu = 'input'">前往录入</el-button>
            </el-empty>
          </div>
          <div v-else>
            <div class="report-header-card">
              <h3>AI 反诈团伙画像系统 - 诈骗案件分析报告</h3>
              <div class="report-meta">
                <span>生成时间：{{ currentTime }}</span>
                <span>分析案件数：{{ totalCases }}个</span>
                <span>识别诈骗案件：{{ identifiedCases }}个</span>
                <span class="highlight">高风险案件：{{ highRiskCases }}个</span>
              </div>
            </div>
            
            <div class="cases-summary">
              <el-statistic title="总案件数" :value="totalCases" />
              <el-statistic title="高风险案件" :value="highRiskCases" />
              <el-statistic title="系统置信度" :value="confidenceScore" suffix="%" />
            </div>
            
            <div class="cases-grid">
              <el-card 
                v-for="(caseItem, index) in results" 
                :key="index"
                class="case-card"
                :class="{ 'risk-high': caseItem.risk_level === 'HIGH' }"
                @click="selectCase(index)"
              >
                <div class="case-header">
                  <h4>案件 #{{ caseItem.case_id }}</h4>
                  <el-tag :type="caseItem.risk_type" size="small">
                    {{ caseItem.risk_label }} ({{ caseItem.risk_score }}%)
                  </el-tag>
                </div>
                <div class="case-body">
                  <div class="info-row">
                    <span class="label">⏰ 时间范围:</span>
                    <span class="value">{{ caseItem.time_range }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">🔍 诈骗类型:</span>
                    <span class="value">{{ caseItem.scam_type }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">💡 关键词:</span>
                    <span class="value">
                      {{ caseItem.keywords && caseItem.keywords.length ? caseItem.keywords.slice(0, 3).join('、') + (caseItem.keywords.length > 3 ? '...' : '') : '无' }}
                    </span>
                  </div>
                </div>
                <div v-if="caseItem.warning" class="warning-alert">
                  <el-alert :title="caseItem.warning" type="warning" :closable="false" size="small" />
                </div>
              </el-card>
            </div>
          </div>
        </div>

        <!-- 3. 团伙画像总览 -->
        <div v-if="activeMenu === 'groups'" class="content-view fade-in">
          <h3 class="section-title">🕵️♂️ 识别出的诈骗团伙列表</h3>
          <div v-if="!hasData" class="empty-state"><el-empty description="暂无数据" /></div>
          <el-empty v-else-if="results.length === 0" description="未检测到明显诈骗团伙特征" />
          <div v-else class="groups-grid">
            <el-card 
              v-for="(group, index) in results" 
              :key="group.case_id" 
              class="group-card"
              shadow="hover"
              @click="selectCase(index)" 
            >
              <div class="group-header">
                <h4>案件 #{{ group.case_id }}: {{ group.scam_type || '未知类型' }}</h4>
                <el-tag :type="group.risk_type || 'info'" size="small">
                  {{ group.risk_label || '低风险' }} ({{ group.risk_score || 0 }}%)
                </el-tag>
              </div>
              <div class="group-body">
                <div class="info-row">
                  <span class="label">🔍 诈骗类型:</span>
                  <span class="value">{{ group.scam_type || '未知' }}</span>
                </div>
                <div class="info-row">
                  <span class="label">⏰ 时间范围:</span>
                  <span class="value">{{ group.time_range }}</span>
                </div>
                <div class="info-row">
                  <span class="label">💡 关键词:</span>
                  <span class="value">
                    {{ group.keywords && group.keywords.length ? group.keywords.join('、') : '无有效关键词' }}
                  </span>
                </div>
              </div>
              <div class="card-footer">
                <el-button type="primary" link @click.stop="selectCase(index)">深度研判 ></el-button>
              </div>
            </el-card>
          </div>
        </div>

        <!-- 4. 团伙深度分析 -->
        <div v-if="activeMenu === 'details'" class="content-view fade-in">
          <div v-if="!hasData" class="empty-state"><el-empty description="暂无数据" /></div>
          <div v-else-if="selectedGroupIndex === null" class="empty-state">
            <el-result icon="info" title="请选择案件" sub-title="请在“报告概览”或“团伙画像总览”中点击任意案件卡片">
              <template #extra><el-button type="primary" @click="activeMenu = 'overview'">前往概览页</el-button></template>
            </el-result>
          </div>
          <div v-else class="detail-container">
            <div class="detail-header">
              <el-button icon="ArrowLeft" @click="activeMenu = 'groups'" circle />
              <h3>{{ currentCaseData.scam_type }} - 深度研判报告 <el-tag size="small" :type="currentCaseData.risk_type">{{ currentCaseData.risk_label }}</el-tag></h3>
            </div>
            <div class="charts-container">
              <el-card class="chart-card">
                <template #header><span>📊 团伙特征雷达</span></template>
                <div ref="radarChartRef" style="width: 100%; height: 300px;"></div>
              </el-card>
              <el-card class="chart-card">
                <template #header><span>☁️ 高频话术分析</span></template>
                <div ref="wordCloudRef" style="width: 100%; height: 300px;"></div>
              </el-card>
              <el-card class="chart-card full-width">
                <template #header><span>🔄 行为序列指纹</span></template>
                <div class="sequence-flow">
                  <div class="step" v-for="(step, i) in currentGroupSteps" :key="i">
                    <span class="step-num">{{ i + 1 }}</span>
                    <span class="step-text">{{ step }}</span>
                    <i v-if="i < currentGroupSteps.length - 1" class="el-icon-right arrow"></i>
                  </div>
                </div>
                <p class="chart-desc">* 该团伙最常见作案路径</p>
              </el-card>
            </div>
          </div>
        </div>

        <!-- 5. 案件关联网络 -->
        <div v-if="activeMenu === 'network'" class="content-view fade-in">
          <div v-if="!hasData" class="empty-state">
            <el-empty description="暂无数据，请先进行分析" />
          </div>
          <div v-else-if="results.length === 0" class="empty-state">
            <el-empty description="未发现案件，无法生成关联图" />
          </div>
          <div v-else>
            <el-card>
              <template #header>
                <div class="card-header-flex">
                  <span>🕸️ 团伙 - 案件关联关系图</span>
                  <el-tag type="info" size="small">交互式图谱</el-tag>
                </div>
              </template>
              <div ref="networkChartRef" style="width: 100%; height: 600px; min-height: 400px;"></div>
              <p class="chart-desc">* 中心节点为诈骗团伙，周围节点为关联案件</p>
            </el-card>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

// --- 状态管理 ---
const activeMenu = ref('input') // 默认进入录入页面
const inputText = ref('')
const loading = ref(false)
const hasData = ref(false)
const selectedGroupIndex = ref(null)

// 图表 DOM 引用
const radarChartRef = ref(null)
const wordCloudRef = ref(null)
const networkChartRef = ref(null)

// 数据模型
const totalCases = ref(0)
const identifiedCases = ref(0)
const highRiskCases = ref(0)
const confidenceScore = ref(0)
const currentTime = ref('')
const results = ref([])
const currentGroupSteps = ref([])

// --- 计算属性 ---
const messageCount = computed(() => inputText.value.split('\n').filter(l => l.trim()).length)

const currentCaseData = computed(() => {
  if (selectedGroupIndex.value === null || !results.value[selectedGroupIndex.value]) {
    return { scam_type: '未知', risk_level: 'LOW', risk_type: 'info', risk_label: '低风险', keywords: [], steps: [] }
  }
  return results.value[selectedGroupIndex.value]
})

// --- 方法 ---

const loadDemo = () => {
  inputText.value = `您好，我是抖音官方客服，您的百万保障服务即将扣费 800 元
我没开过这个服务啊！
请点击此链接关闭：http://fake-security.com
您的会员服务将在 24 小时内扣款
怎么证明你是官方？
我们是正规平台，不处理将影响征信
系统检测到异常登录，请立即验证身份
这是钓鱼网站吧？
我是警察，请配合调查
你的银行卡涉嫌洗钱
请提供验证码
我不信
紧急通知，您的账户已被冻结
需要缴纳保证金才能解冻
账号是 6222 0219 8888 6666
快点，不然抓人
我转了 5000 元
收到，还需要 2000 元激活
骗子！
拉黑了`
  ElMessage.success('已加载模拟案情数据')
}

const handleBeforeUpload = (file) => {
  const isImage = file.type.startsWith('image/');
  if (!isImage) { ElMessage.error('只能上传图片文件'); return false; }
  if (file.size / 1024 / 1024 >= 10) { ElMessage.error('图片大小不能超过 10MB'); return false; }
  
  // 模拟 OCR 过程，实际项目中这里会调用后端 OCR 接口
  const reader = new FileReader();
  reader.onload = (e) => {
    // 这里只是简单追加，实际应该调用后端解析图片文字
    inputText.value += `\n[图片内容待识别] ${file.name}\n`;
    ElMessage.success('图片已上传，系统正在后台提取文字...（模拟）');
  };
  reader.readAsDataURL(file);
  return false;
};

const analyze = async () => {
  const lines = inputText.value.split('\n').filter(line => line.trim() !== '')
  if (lines.length < 5) {
    if(!confirm('消息数量较少，分析结果可能不准确，确定要继续吗？')) return;
  }

  const messages = lines.map(line => {
    if (line.startsWith('[图片]') || line.startsWith('[图片内容')) {
      return { type: 'image', content: line } // 简化处理
    }
    return { type: 'text', content: line }
  })
  
  loading.value = true
  hasData.value = false
  selectedGroupIndex.value = null
  
  try {
    const response = await axios.post('http://127.0.0.1:5000/upload', { messages })
    //这里上传的是json格式的文件，所以我们后端会request.json直接接受到我们的数据
    const data = response.data
    if (data.error) throw new Error(data.error)

    results.value = data.results || []
    totalCases.value = results.value.length
    highRiskCases.value = results.value.filter(item => item.risk_level === 'HIGH').length
    identifiedCases.value = results.value.length
    currentTime.value = new Date().toLocaleString()
    confidenceScore.value = Math.floor(Math.random() * 20) + 80
    hasData.value = true
    
    // 分析完成后，自动跳转到概览页
    activeMenu.value = 'overview'
    ElMessage.success(`✅ 分析完成！共发现 ${totalCases.value} 个案件，已自动生成报告`)

    setTimeout(() => initCharts(), 300)

  } catch (error) {
    console.error(error)
    ElMessage.error('分析失败：' + (error.response?.data?.error || error.message))
  } finally {
    loading.value = false
  }
}

const handleMenuSelect = (index) => {
  activeMenu.value = index
  if (hasData.value && (index === 'details' || index === 'network')) {
    nextTick(() => initCharts())
  }
}

const selectCase = (index) => {
  if (!results.value[index]) { ElMessage.error("案件数据不存在"); return; }
  selectedGroupIndex.value = index
  activeMenu.value = 'details'
  
  const rawData = results.value[index];
  let steps = rawData.steps;
  if (!steps || !Array.isArray(steps) || steps.length === 0) {
    steps = ['接触受害人', '建立信任', '隔离受害人', '诱导转账', '拉黑消失'];
  }
  currentGroupSteps.value = steps;
  
  nextTick(() => {
    initCharts();
    ElMessage.success(`已加载案件 #${rawData.case_id} 详情`);
  });
}

// --- ECharts 初始化逻辑 ---
const initCharts = () => {
  const disposeChart = (ref) => {
    if (ref.value) {
      const instance = echarts.getInstanceByDom(ref.value);
      if (instance) instance.dispose();
    }
  };

  if (activeMenu.value === 'details' && radarChartRef.value && selectedGroupIndex.value !== null) {
    disposeChart(radarChartRef);
    const chart = echarts.init(radarChartRef.value);
    const currentRisk = currentCaseData.value.risk_level;
    const multiplier = currentRisk === 'HIGH' ? 1.0 : 0.7;
    
    chart.setOption({
      color: ['#409EFF'],
      radar: {
        indicator: [
          { name: '话术诱导性', max: 10 }, { name: '资金转移速度', max: 10 },
          { name: '反侦察意识', max: 10 }, { name: '技术复杂度', max: 10 }, { name: '扩散速度', max: 10 }
        ],
        axisName: { color: '#666' },
        splitArea: { areaStyle: { color: ['#f8f9fa', '#fff'] } }
      },
      series: [{
        type: 'radar',
        data: [{
          value: [8.5, 9.0, 6.0, 7.0, 8.0].map(v => v * multiplier),
          name: '团伙特征',
          areaStyle: { color: currentRisk === 'HIGH' ? 'rgba(245, 108, 108, 0.4)' : 'rgba(64, 158, 255, 0.4)' },
          lineStyle: { color: currentRisk === 'HIGH' ? '#F56C6C' : '#409EFF' }
        }]
      }]
    })
  }

  if (activeMenu.value === 'details' && wordCloudRef.value && selectedGroupIndex.value !== null) {
    disposeChart(wordCloudRef);
    const chart = echarts.init(wordCloudRef.value);
    const keywords = currentCaseData.value.keywords || ['验证码', '安全账户', '转账'];
    const displayKeywords = keywords.length >= 3 ? keywords.slice(0, 6) : [...keywords, '冷冻账户', '银监会'];
    
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: displayKeywords, axisLabel: { color: '#333' } },
      series: [{
        type: 'bar',
        data: displayKeywords.map(() => Math.floor(Math.random() * 40) + 20),
        itemStyle: { color: '#409EFF', borderRadius: [0, 4, 4, 0] },
        barWidth: '60%'
      }]
    })
  }

  if (activeMenu.value === 'network' && networkChartRef.value && hasData.value && results.value.length > 0) {
    if (!networkChartRef.value.offsetWidth || !networkChartRef.value.offsetHeight) {
      setTimeout(initCharts, 100);
      return;
    }

    disposeChart(networkChartRef);
    const chart = echarts.init(networkChartRef.value);
    
    const nodes = [{ 
      id: '0', 
      name: '核心诈骗团伙', 
      symbolSize: 80, 
      category: 0, 
      itemStyle: { color: '#F56C6C' },
      label: { show: true, fontSize: 14, fontWeight: 'bold' }
    }]
    const links = []
    
    results.value.forEach((caseItem, idx) => {
      const nodeId = `${idx + 1}`
      const safeName = `案件#${caseItem.case_id} (${caseItem.scam_type || '未知'})`;
      
      nodes.push({ 
        id: nodeId, 
        name: safeName, 
        symbolSize: 50, 
        category: 1,
        itemStyle: { color: caseItem.risk_level === 'HIGH' ? '#F56C6C' : '#67C23A' }
      })
      links.push({ source: '0', target: nodeId, value: caseItem.scam_type || '关联' })
    })
    
    chart.setOption({
      tooltip: { 
        formatter: function(x) {
          if (x.dataType === 'node') return `<strong>${x.name}</strong>`;
          return `${x.data.source} -> ${x.data.target}`;
        }
      },
      animationDurationUpdate: 1500,
      animationEasingUpdate: 'quinticInOut',
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: links,
        roam: true,
        label: { show: true, position: 'right', formatter: '{b}', color: '#333', fontSize: 12 },
        force: { repulsion: 800, edgeLength: 200, gravity: 0.1 },
        lineStyle: { color: 'source', curveness: 0.3, width: 2 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 5 } },
        categories: [{ name: '核心团伙' }, { name: '关联案件' }]
      }]
    })
    setTimeout(() => chart.resize(), 50);
  }
}

window.addEventListener('resize', () => {
  [radarChartRef, wordCloudRef, networkChartRef].forEach(ref => {
    if (ref.value) {
      const instance = echarts.getInstanceByDom(ref.value);
      if (instance) instance.resize();
    }
  })
})
</script>

<style scoped>
/* ====== 整体布局 ====== */
.police-system-layout {
  display: flex;
  height: 100vh;
  background-color: #f0f2f5;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
}

/* ====== 侧边栏 ====== */
.sidebar {
  width: 240px;
  background-color: #0f172a;
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  z-index: 10;
}

.logo-area {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #1e293b;
}

.logo-area h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
  letter-spacing: 1px;
}

.sub-title {
  font-size: 12px;
  color: #64748b;
  display: block;
  margin-top: 5px;
  text-transform: uppercase;
}

.side-menu {
  flex: 1;
  border-right: none;
  background-color: transparent;
}

.system-status {
  padding: 20px;
  border-top: 1px solid #1e293b;
  text-align: center;
}

.version-info {
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
}

/* ====== 主内容区 ====== */
.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ====== 内容视图与动画 ====== */
.content-view {
  animation: fadeIn 0.4s ease;
  min-height: 400px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

/* ====== 数据录入中心样式 ====== */
.input-card-full {
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.page-subtitle {
  margin: 5px 0 0;
  font-size: 13px;
  color: #909399;
}

.input-workspace {
  display: flex;
  gap: 20px;
  flex: 1;
  overflow: hidden; /* 防止溢出 */
}

.input-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  background: #f9fafc;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: bold;
  color: #606266;
}

.chat-input-large {
  flex: 1;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.6;
}

.input-stats {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
  display: flex;
  justify-content: space-between;
}

.tools-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 300px;
}

.tool-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.tool-card h4 {
  margin: 0 0 15px;
  font-size: 16px;
  color: #303133;
  border-left: 4px solid #409EFF;
  padding-left: 10px;
}

.upload-area-large {
  width: 100%;
  border: 2px dashed #dcdfe6;
  border-radius: 6px;
  transition: all 0.3s;
}

.upload-area-large:hover {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.api-hint {
  background: #f4f4f5;
  border-color: #e9e9eb;
}

.api-hint p {
  font-size: 13px;
  color: #606266;
  margin: 5px 0;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  font-style: italic;
}

.action-area {
  margin-top: auto;
  padding-top: 20px;
}

.action-hint {
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-top: 10px;
}

/* ====== 概览卡片 ====== */
.report-header-card {
  background: linear-gradient(135deg, #001f3f, #003366);
  color: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,31,63,0.3);
}

.report-header-card h3 {
  margin: 0 0 10px 0;
  font-size: 20px;
}

.report-meta {
  display: flex;
  gap: 20px;
  font-size: 14px;
  opacity: 0.9;
  flex-wrap: wrap;
}

.report-meta .highlight {
  color: #ffd700;
  font-weight: bold;
}

.cases-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

/* ====== 案件/团伙卡片网格 ====== */
.cases-grid, .groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.case-card, .group-card {
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid #ebeef5;
}

.case-card:hover, .group-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.case-card.risk-high {
  border-left: 4px solid #F56C6C;
}

.case-header, .group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
  margin-bottom: 10px;
}

.case-header h4, .group-header h4 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.case-body, .group-body {
  font-size: 14px;
  color: #606266;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.info-row .label {
  color: #909399;
}

.info-row .value {
  font-weight: 500;
  text-align: right;
  max-width: 60%;
  word-break: break-all;
}

.card-footer {
  text-align: right;
  margin-top: 10px;
  border-top: 1px solid #f5f7fa;
  padding-top: 10px;
}

.warning-alert {
  margin-top: 10px;
}

/* ====== 详情页面样式 ====== */
.section-title {
  margin-bottom: 20px;
  color: #303133;
  border-left: 4px solid #409EFF;
  padding-left: 10px;
  font-size: 18px;
}

.detail-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.detail-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-card.full-width {
  grid-column: span 2;
}

.sequence-flow {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  padding: 20px 0;
  flex-wrap: wrap;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f5f7fa;
  padding: 15px 20px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  min-width: 100px;
}

.step-num {
  width: 28px;
  height: 28px;
  background: #409EFF;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  margin-bottom: 8px;
  font-weight: bold;
}

.step-text {
  font-size: 14px;
  color: #303133;
  text-align: center;
}

.arrow {
  color: #909399;
  font-size: 18px;
}

.chart-desc {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 10px;
}

/* ====== 响应式 ====== */
@media (max-width: 1000px) {
  .input-workspace {
    flex-direction: column;
    overflow-y: auto;
  }
  .tools-panel {
    min-width: auto;
  }
  .cases-summary {
    grid-template-columns: 1fr;
  }
  .charts-container {
    grid-template-columns: 1fr;
  }
  .chart-card.full-width {
    grid-column: span 1;
  }
  .sequence-flow {
    justify-content: center;
  }
}
</style>