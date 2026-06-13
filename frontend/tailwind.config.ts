import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // ── Color tokens (mirror CSS vars in globals.css) ───────────────────
      colors: {
        bg: 'var(--bg)',
        'bg-warm': 'var(--bg-warm)',
        surface: 'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        card: 'var(--card)',
        'card-warm': 'var(--card-warm)',
        border: 'var(--border)',
        'border-fine': 'var(--border-fine)',
        'border-hair': 'var(--border-hair)',

        // Cinnamon / espresso brand scale
        saffron: 'var(--saffron)',
        'saffron-deep': 'var(--saffron-deep)',
        'saffron-warm': 'var(--saffron-warm)',
        'saffron-light': 'var(--saffron-light)',
        'saffron-pale': 'var(--saffron-pale)',
        'saffron-dim': 'var(--saffron-dim)',

        // Semantic
        emerald: 'var(--emerald)',
        'emerald-light': 'var(--emerald-light)',
        sapphire: 'var(--sapphire)',
        'sapphire-light': 'var(--sapphire-light)',
        amber: 'var(--amber)',
        rose: 'var(--rose)',
        violet: 'var(--violet)',

        // Ink scale
        ink: 'var(--ink)',
        'ink-rich': 'var(--ink-rich)',
        'ink-dim': 'var(--ink-dim)',
        'ink-faint': 'var(--ink-faint)',
        'ink-ghost': 'var(--ink-ghost)',
        'ink-mist': 'var(--ink-mist)',
      },

      // ── Typography ────────────────────────────────────────────────────────
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1.4', letterSpacing: '0.02em' }],
        'sm': ['0.8125rem', { lineHeight: '1.5', letterSpacing: '0.005em' }],
        'base': ['0.9375rem', { lineHeight: '1.65', letterSpacing: '-0.01em' }],
        'md': ['1rem', { lineHeight: '1.55', letterSpacing: '-0.012em' }],
        'lg': ['1.0625rem', { lineHeight: '1.45', letterSpacing: '-0.015em' }],
        'xl': ['1.25rem', { lineHeight: '1.35', letterSpacing: '-0.02em' }],
        '2xl': ['1.5rem', { lineHeight: '1.25', letterSpacing: '-0.025em' }],
        '3xl': ['2rem', { lineHeight: '1.15', letterSpacing: '-0.03em' }],
        '4xl': ['2.5rem', { lineHeight: '1.08', letterSpacing: '-0.035em' }],
      },

      // ── Shadows ───────────────────────────────────────────────────────────
      boxShadow: {
        'xs': 'var(--shadow-xs)',
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
        'brand': 'var(--shadow-brand)',
        'inset': 'var(--shadow-inset)',
      },

      // ── Border radius ─────────────────────────────────────────────────────
      borderRadius: {
        xs: 'var(--radius-xs)',
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        pill: 'var(--radius-pill)',
        // Legacy aliases kept for backwards compat
        xl2: '14px',
        xl3: '18px',
      },

      // ── Spacing extras ─────────────────────────────────────────────────────
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
      },

      // ── Animations ────────────────────────────────────────────────────────
      animation: {
        'spin-slow': 'spinSlow 8s linear infinite',
        'glow-ring': 'glowRing 3s ease infinite',
        'fade-up': 'fadeSlideUp 0.4s cubic-bezier(0.25,0.46,0.45,0.94) both',
        'breathe': 'breathe 4s ease infinite',
        'shimmer': 'shimmerFire 3s linear infinite',
        'pulse': 'pulse 1.8s ease infinite',
        'float-up': 'floatUp 0.4s cubic-bezier(0.34,1.56,0.64,1) both',
        'pop-in': 'popIn 0.3s cubic-bezier(0.34,1.56,0.64,1) both',
        'skeleton': 'skeleton-shimmer 1.6s ease infinite',
        'slide-dn': 'slideDown 0.2s ease both',
        'tick-pop': 'tickPop 0.35s cubic-bezier(0.34,1.56,0.64,1) both',
      },
      keyframes: {
        spinSlow: { to: { transform: 'rotate(360deg)' } },
        floatUp: {
          '0%': { opacity: '0', transform: 'translateY(20px) scale(0.96)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        popIn: {
          '0%': { opacity: '0', transform: 'scale(0.88)' },
          '60%': { opacity: '1', transform: 'scale(1.04)' },
          '100%': { transform: 'scale(1)' },
        },
        'skeleton-shimmer': {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },

      // ── Transitions ───────────────────────────────────────────────────────
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'ease-out': 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      },
      transitionDuration: {
        fast: '150ms',
        base: '240ms',
        slow: '400ms',
      },

      // ── Backdrop blur ─────────────────────────────────────────────────────
      backdropBlur: {
        xs: '4px',
        sm: '8px',
        md: '10px',
        DEFAULT: '16px',
        lg: '24px',
        xl: '36px',
      },
    },
  },
  plugins: [],
};

export default config;
