import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production: the SPA is served by Django/WhiteNoise under /static/, so the build
// must emit asset URLs with that prefix. Dev: base stays '/' (so localhost:5173
// works normally) and /api is proxied to the Django backend, letting the app use
// same-origin relative URLs (no CORS, cookies just work). VITE_PROXY_TARGET lets
// docker-compose point the proxy at the "web" service.
// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/' : '/',
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
    },
  },
}))
