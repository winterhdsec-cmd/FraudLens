import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
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
