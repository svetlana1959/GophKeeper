/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev-only: proxy API paths to the backend so the browser talks same-origin and
// avoids CORS. In production nginx serves the SPA and proxies the same paths.
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8080'
const proxied = ['/accounts', '/auth', '/enroll', '/sync', '/devices', '/stats', '/health']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: Object.fromEntries(proxied.map((path) => [path, apiTarget])),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
})
