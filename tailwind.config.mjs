/**
 * Minimal Tailwind CSS configuration (ESM).
 * Tailwind v4 supports zero-config via the PostCSS plugin; this exists to
 * satisfy tooling (e.g., shadcn/ui CLI) that references a Tailwind config path.
 */
export default {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  plugins: [],
  theme: {
    extend: {},
  },
};
