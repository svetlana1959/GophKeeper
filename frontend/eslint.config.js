import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

export default tseslint.config(
  globalIgnores(['dist', 'src/api/schema.d.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // shadcn/ui primitives export a component plus its cva variants (a const).
      'react-refresh/only-export-components': ['error', { allowConstantExport: true }],
    },
  },
  {
    // Build/config files run in Node, not the browser.
    files: ['**/*.config.{js,ts}'],
    languageOptions: { globals: globals.node },
  },
)
