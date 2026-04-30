import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Phase 2 Astro config (D-59).
// - Preact integration for any client-island components (charts, future widgets).
// - Vite watcher explicitly includes src/data/** so atomic .tmp+rename writes
//   from Python modeling scripts trigger HMR (D-63 hot-reload contract).
//   Default Vite already watches src/**, but we name it for documentation.
export default defineConfig({
  integrations: [preact()],
  vite: {
    server: {
      watch: {
        ignored: ['!**/src/data/**'],
      },
    },
  },
});
