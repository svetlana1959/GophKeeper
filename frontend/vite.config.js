import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only: proxy API paths to the backend so the browser talks same-origin and
// avoids CORS. In production nginx serves the SPA and proxies the same paths.
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/accounts': apiTarget,
      '/auth': apiTarget,
      '/enroll': apiTarget,
      '/sync': apiTarget,
      '/devices': apiTarget,
    },
  },
})
