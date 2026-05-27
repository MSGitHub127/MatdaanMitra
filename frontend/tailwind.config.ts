import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // ── Color tokens (match CSS vars in globals.css) ─────────────────────
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        card: 'var(--card)',
        border: 'var(--border)',
        saffron: 'var(--saffron)',
        'saffron-warm': 'var(--saffron-warm)',
        emerald: 'var(--emerald)',
        sapphire: 'var(--sapphire)',
        amber: 'var(--amber)',
        rose: 'var(--rose)',
        violet: 'var(--violet)',
        ink: 'var(--ink)',
        'ink-dim': 'var(--ink-dim)',
        'ink-faint': 'var(--ink-faint)',
        'ink-ghost': 'var(--ink-ghost)',
      },
      // ── Typography ────────────────────────────────────────────────────────
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      // ── Animations ────────────────────────────────────────────────────────
      animation: {
        'spin-slow': 'spinSlow 8s linear infinite',
        'glow-ring': 'glowRing 3s ease infinite',
        'fade-up': 'fadeSlideUp 0.4s cubic-bezier(0.25,0.46,0.45,0.94) both',
        'breathe': 'breathe 4s ease infinite',
        'shimmer': 'shimmerFire 3s linear infinite',
        'pulse': 'pulse 1.8s ease infinite',
      },
      keyframes: {
        spinSlow: { to: { transform: 'rotate(360deg)' } },
      },
      // ── Border radius ─────────────────────────────────────────────────────
      borderRadius: {
        xl2: '14px',
        xl3: '18px',
      },
    },
  },
  plugins: [],
};

export default config;