import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: 'frontend',
  plugins: [react()],
  server: {
    allowedHosts: ['.manus.computer'],
  },
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true,
    sourcemap: false,
  },
});
