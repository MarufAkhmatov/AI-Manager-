import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        line: "var(--line)",
        text: "var(--text)",
        "text-dim": "var(--text-dim)",
        // Accent is monochrome — pure white in dark mode, pure black in
        // light mode — and resolved via CSS variables. No coloured hue.
        accent: {
          DEFAULT: "var(--accent)",
          dim: "var(--accent-dim)",
          soft: "var(--accent-soft)",
          ink: "var(--accent-ink)",
        },
      },
      boxShadow: {
        neo: "var(--shadow-neo)",
        "neo-in": "var(--shadow-neo-in)",
        glow: "var(--shadow-glow)",
      },
      backdropBlur: { glass: "18px" },
      borderRadius: { glass: "20px" },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "Helvetica"],
        mono: ["ui-monospace", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
