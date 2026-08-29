/**
 * echarts 懒加载。
 *
 * 为什么要懒加载：App.vue 在根组件注入 useFraudLens，如果那里静态 import echarts，
 * 首屏（Showcase 首页，一个图表都没有）也得先下载约 1MB 的 echarts chunk。
 * 改成动态 import 后，echarts 只在真正要 init 图表的页面才拉取。
 *
 * 为什么统一在这里注册：useFraudLens（看板/总览）与 CaseDetailView、DetailsView
 * （雷达图）都要用，集中注册一份，避免三处各写一套 use() 导致漏注册。
 * 只注册实际用到的图表与组件，没用到的（地图、3D、散点等）不进包。
 */
let _echartsPromise = null

export function getEcharts() {
  if (!_echartsPromise) {
    _echartsPromise = Promise.all([
      import('echarts/core'),
      import('echarts/charts'),
      import('echarts/components'),
      import('echarts/renderers')
    ]).then(([core, charts, components, renderers]) => {
      core.use([
        charts.BarChart,
        charts.LineChart,
        charts.PieChart,
        charts.RadarChart,
        components.GridComponent,
        components.LegendComponent,
        components.TooltipComponent,
        components.TitleComponent,
        renderers.CanvasRenderer
      ])
      return core
    })
  }
  return _echartsPromise
}
