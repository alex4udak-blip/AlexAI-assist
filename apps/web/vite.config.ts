import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  // Load from .env files
  const fileEnv = loadEnv(mode, process.cwd(), '');

  // Merge with process.env (Railway sets env vars here)
  // process.env takes priority over .env files
  const env = {
    ...fileEnv,
    ...process.env,
  };

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    define: {
      // Inject env vars at build time
      'import.meta.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL || ''),
      'import.meta.env.VITE_WS_URL': JSON.stringify(env.VITE_WS_URL || ''),
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_WS_URL || 'ws://localhost:8000',
          ws: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
    },
  };
});
