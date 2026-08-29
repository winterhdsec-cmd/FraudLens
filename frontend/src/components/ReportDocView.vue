<template>
  <!-- 纸面红头公文版式：预览与打印/下载 HTML 共用同一数据模型与类名（rd-*） -->
  <div class="report-doc">
    <div class="rd-org">FraudLens 反诈智能研判系统</div>
    <div class="rd-title">{{ doc.title }}</div>
    <div class="rd-meta">
      <span>{{ doc.no }}</span>
      <span>密级：<b class="rd-secret">{{ doc.secret }}</b></span>
      <span>生成时间：{{ doc.time }}</span>
    </div>
    <div class="rd-redline"></div>

    <div class="rd-body">
      <div v-for="(sec, si) in doc.sections" :key="si" class="rd-section">
        <div class="rd-sec-title">{{ sec.title }}</div>
        <table v-if="sec.rows && sec.rows.length" class="doc-table">
          <tbody>
            <tr v-for="(row, ri) in sec.rows" :key="ri">
              <td class="dt-label">{{ row[0] }}</td>
              <td class="dt-value" :class="{ danger: row[2] === 'danger' }">{{ row[1] }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="sec.text" class="doc-para">{{ sec.text }}</p>
        <ol v-if="sec.items && sec.items.length" class="doc-ol">
          <li v-for="(it, ii) in sec.items" :key="ii">{{ it }}</li>
        </ol>
      </div>
    </div>

    <div class="rd-sign">
      <div>研判民警（承办）：＿＿＿＿＿＿＿＿　复核：＿＿＿＿＿＿＿＿</div>
      <div class="rd-sign-date">{{ doc.date }}</div>
    </div>
    <div class="rd-footer">
      本报告由 FraudLens 反诈智能研判系统自动生成，数据来源于本单位授权系统，仅供内部研判参考，严禁外传。
    </div>
  </div>
</template>

<script setup>
defineProps({
  // buildReportDoc() 产出的文档模型：
  // { title, no, secret, time, date, sections: [{ title, rows?, text?, items? }] }
  doc: { type: Object, required: true }
})
</script>

<style scoped>
/* 与 useFraudLens.js 中 REPORT_DOC_CSS（打印窗口用）保持一致的纸面版式 */
.report-doc {
  background: #fff;
  color: #1a1a1a;
  font-family: 'SimSun', 'Songti SC', 'Microsoft YaHei', serif;
  line-height: 1.9;
  font-size: 15px;
}
.rd-org {
  text-align: center;
  color: #c00000;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 2px;
  font-family: 'SimHei', 'Microsoft YaHei', sans-serif;
}
.rd-title { text-align: center; font-size: 21px; font-weight: 700; margin: 14px 0 8px; letter-spacing: 3px; }
.rd-meta { text-align: center; font-size: 13px; color: #333; margin-bottom: 6px; }
.rd-meta span { margin: 0 10px; }
.rd-secret { color: #c00000; }
.rd-redline { height: 2.5px; background: #c00000; margin: 6px 0 22px; }
.rd-section { margin-bottom: 18px; }
.rd-sec-title {
  font-size: 16.5px;
  font-weight: 700;
  font-family: 'SimHei', 'Microsoft YaHei', sans-serif;
  margin-bottom: 8px;
}
.doc-table { width: 100%; border-collapse: collapse; }
.doc-table td { border: 1px solid #8a8a8a; padding: 6px 10px; font-size: 14px; vertical-align: middle; }
.dt-label { width: 120px; background: #f4f4f4; font-weight: 700; text-align: center; }
.dt-value.danger { color: #c00000; font-weight: 700; }
.doc-para { text-indent: 2em; margin: 6px 0; }
.doc-ol { margin: 6px 0; padding-left: 26px; }
.doc-ol li { margin-bottom: 4px; }
.rd-sign { margin-top: 34px; text-align: right; font-size: 15px; }
.rd-sign-date { margin-top: 6px; padding-right: 40px; }
.rd-footer {
  margin-top: 26px;
  border-top: 1px solid #999;
  padding-top: 8px;
  font-size: 11px;
  color: #888;
  text-align: center;
}
</style>
