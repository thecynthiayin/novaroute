import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import ts from 'typescript-eslint';
import next from '@next/eslint-plugin-next';
export default defineConfig([
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    plugins: { '@next/next': next },
    rules: { ...next.configs.recommended.rules, ...next.configs['core-web-vitals'].rules },
  },
  globalIgnores(['.next/**', 'next-env.d.ts', 'playwright-report/**', 'test-results/**']),
]);
