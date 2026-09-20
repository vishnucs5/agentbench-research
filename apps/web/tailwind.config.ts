import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#080D16",
        panel: "#101A26",
        "panel-light": "#142331",
        border: "#1E293B",
        accent: "#CFFF4B",
        "accent-dim": "#8FBF2A",
        cyan: "#22D3EE",
        coral: "#FF6B6B",
        amber: "#F59E0B",
        muted: "#64748B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config
