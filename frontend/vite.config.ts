import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import tailwindcss from "@tailwindcss/vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: ['homelab', 'localhost', '.homelab'],
    strictPort: false,
    hmr: {
      clientPort: 5173,
    },
    watch: {
      usePolling: true,
    },
  },
})
