import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })] }),
    Components({ resolvers: [ElementPlusResolver({ importStyle: false })] })
  ],
  build: {
    rollupOptions: {
      output: {
        // 手动分包：避免单个大 chunk 阻塞首屏，公共依赖独立缓存
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router'],
          'element-plus': ['element-plus'],
          // echarts 刻意不写在这里：源码只用 echarts/core 等子路径做动态 import，
          // 若保留 'echarts' 会把包入口（含全部图表类型）强行打成一个 chunk，
          // 按需引入就白做了。交给 Vite 按动态 import 自动分块，
          // 图表代码只在真正 init 图表的页面才下载。
          'vis-network': ['vis-network']
        }
      }
    }
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE || 'http://localhost:5003',
        changeOrigin: true
      },
      '/agent-analyze': {
        target: process.env.VITE_API_BASE || 'http://localhost:5003',
        changeOrigin: true
      },
      '/health': {
        target: process.env.VITE_API_BASE || 'http://localhost:5003',
        changeOrigin: true
      },
      '/ws': {
        target: process.env.VITE_WS_URL || 'ws://localhost:5003',
        ws: true
      }
    }
  }
})
