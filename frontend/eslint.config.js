// ESLint flat config for the Vue 3 frontend.
// Intentionally lenient: catches real bugs (unused vars, undefined refs) while
// leaving stylistic choices to the team. Runs as a quality signal, not a gate.
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'

export default [
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'public/**',
      'src/components/editor/ueditor/**',
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        console: 'readonly',
        navigator: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        FormData: 'readonly',
        URL: 'readonly',
        Blob: 'readonly',
        fetch: 'readonly',
      },
    },
    rules: {
      // Keep noise low: warn on unused vars, allow intentional _-prefixed ones.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
    },
  },
]
