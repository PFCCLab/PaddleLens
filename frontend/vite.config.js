import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue()],
    server: {
        host: '0.0.0.0', // 这样公网也能访问到
        port: 5173,
        allowedHosts: ['paddle-lens.osslab-pku.org'],
    },
})
