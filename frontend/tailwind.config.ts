import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Surfaces resolve to CSS variables so the same class works in
        // light + dark themes. See app/globals.css for the palettes.
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        line: "var(--line)",
        text: "var(--text)",
        "text-dim": "var(--text-dim)",
        // Brand: a single green used for active / focus / accent states.
        accent: {
          DEFAULT: "#22D58F",
          dim: "#16A36B",
          soft: "rgba(34,213,143,0.18)",
        },
      },
      boxShadow: {
        neo: "var(--shadow-neo)",
        "neo-in": "var(--shadow-neo-in)",
        glow: "0 0 0 1px rgba(34,213,143,0.45), 0 0 24px rgba(34,213,143,0.28)",
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
