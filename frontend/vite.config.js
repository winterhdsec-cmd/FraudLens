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
          echarts: ['echarts'],
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
