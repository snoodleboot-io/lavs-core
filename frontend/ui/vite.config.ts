import { resolve } from 'node:path';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Backend (uvicorn/DuckDB) for dev + E2E; overridable via VITE_LAVS_API_URL.
const BACKEND_URL = process.env.VITE_LAVS_API_URL ?? 'http://127.0.0.1:8001';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Same-origin in dev so the HttpOnly session cookie flows without CORS.
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.{test,spec}.{ts,tsx}',
        'src/**/index.ts',
        'src/main.tsx',
        'src/test/**',
        'src/mocks/**',
        'src/**/*.d.ts',
      ],
      thresholds: {
        lines: 80,
        branches: 70,
        functions: 90,
        statements: 85,
      },
    },
  },
});
