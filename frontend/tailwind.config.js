/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "oklch(55% 0.2 250)",
          foreground: "oklch(95% 0.01 250)",
        },
        secondary: {
          DEFAULT: "oklch(80% 0.1 200)",
          foreground: "oklch(25% 0.01 200)",
        },
        accent: {
          DEFAULT: "oklch(70% 0.25 50)",
          foreground: "oklch(20% 0.01 50)",
        },
        muted: {
          DEFAULT: "oklch(95% 0.01 0)",
          foreground: "oklch(64% 0.01 0)",
        },
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "oklch(85% 0.01 0 / 0.15)",
        input: "oklch(85% 0.01 0 / 0.15)",
        destructive: {
          DEFAULT: "oklch(65% 0.25 25)",
          foreground: "oklch(95% 0.01 0)",
        },
        success: {
          DEFAULT: "oklch(65% 0.2 150)",
          foreground: "oklch(95% 0.01 0)",
        },
        warning: {
          DEFAULT: "oklch(70% 0.15 85)",
          foreground: "oklch(15% 0.01 0)",
        },
        info: {
          DEFAULT: "oklch(65% 0.2 220)",
          foreground: "oklch(95% 0.01 0)",
        },
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      container: {
        center: true,
        padding: "2rem",
        screens: {
          "2xl": "1400px",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)"],
        mono: ["var(--font-geist-mono)"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
  ],
}