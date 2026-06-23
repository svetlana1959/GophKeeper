module.exports = {
  root: true,
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  env: {
    browser: true,
    es2024: true,
  },
  extends: ['eslint:recommended', 'plugin:react-hooks/recommended'],
  plugins: ['react-hooks'],
  rules: {
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'no-console': 'warn',
  },
  overrides: [
    {
      files: ['**/*.jsx'],
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
  ],
};
