import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// usePolling keeps file-watching reliable inside Docker bind mounts.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: { usePolling: true },
    // Proxy API calls to the backend container so the browser stays host-port-agnostic
    // and avoids CORS. The target uses the compose service name on the docker network.
    proxy: {
      '/api': {
        target: 'http://homestack-backend:8000',
        changeOrigin: true,
      },
    },
  },
})
