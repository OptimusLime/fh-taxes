import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Phase 2 Astro config (D-59).
// - Preact integration for any client-island components (charts, future widgets).
// - Vite watcher explicitly includes src/data/** so atomic .tmp+rename writes
//   from Python modeling scripts trigger HMR (D-63 hot-reload contract).
//   Default Vite already watches src/**, but we name it for documentation.
export default defineConfig({
  integrations: [preact()],
  // 4322 because port 4321 is taken by the Sophon dashboard on this machine.
  server: { host: '0.0.0.0', port: 4322 },
  vite: {
    server: {
      // Allow Tailscale / LAN hostnames through Vite's host check. Add more as needed.
      allowedHosts: ['pauls-macbook-pro', '.local', '.ts.net'],
      watch: {
        ignored: ['!**/src/data/**'],
      },
    },
  },
});
