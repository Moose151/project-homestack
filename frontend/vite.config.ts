import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// usePolling keeps file-watching reliable inside Docker bind mounts.
// Behind the Nginx Proxy Manager reverse proxy (Security §14), the browser's Host header is the
// public hostname (e.g. homestack.moosesoftwares.com) even though the request never leaves the
// LAN — Vite blocks unknown Host headers by default, so it must be explicitly allowed.
const publicHostname = process.env.HOMESTACK_PUBLIC_HOSTNAME
const allowedHosts = ['homestack.home.arpa', '.home.arpa', ...(publicHostname ? [publicHostname] : [])]

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: { usePolling: true },
    allowedHosts,
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
