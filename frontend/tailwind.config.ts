import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Palette mirrors the AI-Workflow Figma export so the AI Manager
        // dashboard reads as the same product family.
        bg: "#050505",
        surface: "rgba(255, 255, 255, 0.04)",
        "surface-2": "rgba(255, 255, 255, 0.05)",
        line: "rgba(255, 255, 255, 0.10)",
        text: "#ffffff",
        "text-dim": "rgba(255, 255, 255, 0.6)",
        // Neon green primary — for active states, running glow, accent
        // buttons. Yellow secondary — for KB-related running paths.
        neon: {
          DEFAULT: "#22ff88",
          dim: "rgba(34, 255, 136, 0.5)",
          soft: "rgba(34, 255, 136, 0.10)",
        },
        amber: {
          DEFAULT: "#ffcc00",
          soft: "rgba(255, 204, 0, 0.10)",
        },
        danger: "#ff4f5e",
        // Backwards-compat alias so the KB and per-agent pages keep
        // resolving the old "accent" colour without a rewrite.
        accent: "#22ff88",
      },
      boxShadow: {
        "neon-sm": "0 0 10px rgba(34, 255, 136, 0.35)",
        "neon-md": "0 0 22px rgba(34, 255, 136, 0.25)",
        "neon-lg": "0 0 40px rgba(34, 255, 136, 0.25)",
        "amber-md": "0 0 22px rgba(255, 204, 0, 0.25)",
      },
      backdropBlur: { glass: "18px" },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Helvetica"],
        mono: ["ui-monospace", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
