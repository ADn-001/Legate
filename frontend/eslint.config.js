import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      // TS's own type-checker covers undefined identifiers; no-undef
      // produces false positives on TS-specific syntax and ambient/DOM
      // globals. This is the official typescript-eslint guidance.
      'no-undef': 'off',
      // NFR-09 / S6 (Phase 5 T6): prevent accidental logging of CEK, passwords,
      // or decrypted content.  console.error is allowed for error reporting;
      // all other console methods are errors so regressions fail lint.
      'no-console': ['error', { allow: ['error', 'warn'] }],
    },
  },
]
