import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

/**
 * Vitest configuration (separate from vite.config.js which uses the
 * function form). Uses jsdom so component tests can mount DOM nodes.
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // ESM-safe path resolution ("type":"module" → no __dirname).
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.{js,ts}'],
    css: false,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,vue}'],
      exclude: [
        'src/**/*.spec.js',
        'src/**/*.test.js',
        'src/test/**', // test harness/infra
        'src/main.js', // app bootstrap; exercised by E2E, not unit tests
        'src/components/editor/UEditor.vue', // thin wrapper over global UEditor lib (iframe), covered by E2E
        'src/components/viewer/PdfViewer.vue' // thin wrapper over pdfjs-dist, covered by E2E
      ],
      reporter: ['text', 'text-summary', 'html', 'json-summary'],
      reportsDirectory: './coverage',
      // Lock in the coverage gains; CI fails if coverage regresses below these.
      thresholds: {
        statements: 90,
        branches: 85,
        functions: 60,
        lines: 90
      }
    }
  }
})
