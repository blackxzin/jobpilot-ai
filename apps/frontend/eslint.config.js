import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default [
  {
    // Build output: .next for the server build, out for the static export.
    ignores: [".next/**", "out/**", "node_modules/**", "test-results/**", "next-env.d.ts"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // Build tooling runs in Node.
  {
    files: ["*.js", "*.mjs", "*.ts"],
    languageOptions: { globals: globals.node },
  },

  // The service worker has its own global scope (self, caches, clients) that
  // neither the browser nor the Node preset covers.
  {
    files: ["public/sw.js"],
    languageOptions: {
      globals: { ...globals.serviceworker, ...globals.browser },
      ecmaVersion: 2022,
    },
  },

  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Application code is fully typed; `any` here means a shape was never
      // modelled, which is what the types in src/lib/types.ts exist to prevent.
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];
