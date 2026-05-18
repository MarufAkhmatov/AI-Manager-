import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#000000",
          900: "#0a0a0a",
          800: "#111111",
          700: "#1a1a1a",
          600: "#222222",
        },
        bone: {
          50: "#ffffff",
          100: "#f5f5f5",
          200: "#cccccc",
          300: "#999999",
          400: "#666666",
        },
        accent: {
          DEFAULT: "#7CE7FF",
          dim: "#4FB8D4",
        },
      },
      boxShadow: {
        // Neomorphic raised: highlight top-left, shadow bottom-right.
        neo: "8px 8px 24px rgba(0,0,0,0.6), -2px -2px 8px rgba(255,255,255,0.04)",
        "neo-in":
          "inset 4px 4px 12px rgba(0,0,0,0.7), inset -2px -2px 8px rgba(255,255,255,0.03)",
        glow: "0 0 0 1px rgba(124,231,255,0.4), 0 0 24px rgba(124,231,255,0.25)",
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
