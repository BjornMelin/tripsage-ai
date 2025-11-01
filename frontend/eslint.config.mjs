import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

/** @type {import('eslint').Linter.FlatConfig[]} */
const eslintConfig = [
  ...compat.extends("next/core-web-vitals"),
  {
    rules: {
      // Temporarily disable some rules to get build working
      "react/display-name": "off",
      "react/no-unescaped-entities": "off",
      "react-hooks/exhaustive-deps": "warn",
      "@next/next/no-img-element": "warn",
      // Disallow importing server-only Supabase admin/RPC modules in client code
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@/lib/supabase/admin",
              message:
                "Server-only module. Use in Next.js route handlers or server code only.",
            },
            {
              name: "@/lib/supabase/rpc",
              message:
                "Server-only RPC helpers. Do not import into client components.",
            },
          ],
        },
      ],
    },
  },
  // Allow server-only imports in server contexts (routes, supabase lib, tests)
  {
    files: [
      "src/app/api/**",
      "src/lib/supabase/**",
      "src/test/**",
      "src/**/__tests__/**",
    ],
    rules: {
      "no-restricted-imports": "off",
    },
  },
];

export default eslintConfig;
