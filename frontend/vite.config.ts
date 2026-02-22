import { defineConfig, type Plugin } from 'vite'

function injectConfigScript(): Plugin {
  return {
    name: 'inject-config-script',
    enforce: 'post',
    transformIndexHtml() {
      return [{ tag: 'script', attrs: { src: '/config.js' }, injectTo: 'head' }]
    },
  }
}

export default defineConfig({
  plugins: [injectConfigScript()],
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
