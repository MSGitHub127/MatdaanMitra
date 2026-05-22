import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#04070E",
        surface: "#080D18",
        card: "#0F1A2E",
        border: "#162338",
        saffron: "#FF9500",
        "saffron-warm": "#FFB347",
        emerald: "#10B981",
        sapphire: "#3B82F6",
        amber: "#F59E0B",
        rose: "#F43F5E",
        ink: "#E8EDF8",
        "ink-dim": "#8AA0C0",
        "ink-faint": "#3A5070",
      },
      fontFamily: {
        display: ["Cormorant Garamond", "serif"],
        sans: ["Outfit", "sans-serif"],
      },
      animation: {
        "fade-slide-up": "fadeSlideUp 0.4s ease-out",
        "tick-pop": "tickPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        "grain": "grain 8s steps(10) infinite",
      },
      keyframes: {
        fadeSlideUp: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        tickPop: {
          "0%": { transform: "scale(0) rotate(-45deg)" },
          "60%": { transform: "scale(1.3)" },
          "100%": { transform: "scale(1)" },
        },
        glowPulse: {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(255,149,0,0.2)" },
          "50%": { boxShadow: "0 0 0 8px rgba(255,149,0,0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% center" },
          "100%": { backgroundPosition: "-200% center" },
        },
        grain: {
          "0%,100%": { transform: "translate(0,0)" },
          "50%": { transform: "translate(-1%,2%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
