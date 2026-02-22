import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  envDir: '../',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/config.js': 'http://localhost:8000',
    },
  },
})
