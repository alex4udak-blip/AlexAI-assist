/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Backgrounds - Deep space
        bg: {
          primary: '#030712',
          secondary: '#0a0f1a',
          tertiary: '#111827',
          elevated: '#1a2332',
          hover: '#1f2937',
        },
        // Surfaces - Glass
        surface: {
          primary: 'rgba(6, 182, 212, 0.03)',
          hover: 'rgba(6, 182, 212, 0.06)',
          active: 'rgba(6, 182, 212, 0.1)',
        },
        // Borders - Subtle zinc
        border: {
          subtle: 'rgba(63, 63, 70, 0.5)',
          default: 'rgba(82, 82, 91, 0.6)',
          strong: 'rgba(113, 113, 122, 0.5)',
          glow: 'rgba(6, 182, 212, 0.3)',
        },
        // Text
        text: {
          primary: '#f0f9ff',
          secondary: 'rgba(224, 242, 254, 0.8)',
          tertiary: 'rgba(224, 242, 254, 0.6)',
          muted: 'rgba(224, 242, 254, 0.4)',
        },
        // HUD Accent - Cyan/Blue like Iron Man
        hud: {
          cyan: '#06b6d4',
          blue: '#3b82f6',
          teal: '#14b8a6',
          glow: 'rgba(6, 182, 212, 0.6)',
          muted: 'rgba(6, 182, 212, 0.15)',
        },
        // Rings colors
        ring: {
          outer: '#f97316', // Orange - productivity
          middle: '#8b5cf6', // Violet - focus
          inner: '#10b981', // Green - automation
        },
        // Status - Vibrant
        status: {
          success: '#22c55e',
          warning: '#f59e0b',
          error: '#ef4444',
          info: '#06b6d4',
          online: '#22c55e',
          offline: '#6b7280',
        },
        // Accent colors (alias for hud-cyan based theme)
        accent: {
          primary: '#06b6d4',
          muted: 'rgba(6, 182, 212, 0.15)',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.8125rem', { lineHeight: '1.25rem' }],
        'base': ['0.875rem', { lineHeight: '1.5rem' }],
        'lg': ['1rem', { lineHeight: '1.5rem' }],
        'xl': ['1.125rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['2rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.5rem', { lineHeight: '2.75rem' }],
        '5xl': ['3rem', { lineHeight: '3.25rem' }],
      },
      letterSpacing: {
        tighter: '-0.02em',
        tight: '-0.01em',
        wide: '0.05em',
        wider: '0.1em',
      },
      boxShadow: {
        'hud': '0 1px 3px rgba(0, 0, 0, 0.3)',
        'hud-sm': '0 1px 2px rgba(0, 0, 0, 0.2)',
        'hud-lg': '0 4px 12px rgba(0, 0, 0, 0.4)',
        'glow-cyan': '0 0 8px rgba(6, 182, 212, 0.2)',
        'glow-blue': '0 0 8px rgba(59, 130, 246, 0.2)',
        'glow-green': '0 0 8px rgba(34, 197, 94, 0.2)',
        'glow-orange': '0 0 8px rgba(249, 115, 22, 0.2)',
        'inner-glow': 'inset 0 1px 2px rgba(0, 0, 0, 0.1)',
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
        'hud-gradient': 'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%)',
        'hud-radial': 'radial-gradient(ellipse at center, rgba(6, 182, 212, 0.15) 0%, transparent 70%)',
        'card-gradient': 'linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(6, 182, 212, 0.02) 100%)',
        'glass': 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%)',
        'scanline': 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(6, 182, 212, 0.03) 2px, rgba(6, 182, 212, 0.03) 4px)',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'hud': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in': 'slide-in 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'scan': 'scan 3s linear infinite',
        'ring-fill': 'ring-fill 1.5s ease-out forwards',
        'data-stream': 'data-stream 20s linear infinite',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-in': {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'translateX(0)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'ring-fill': {
          from: { strokeDashoffset: '283' },
          to: { strokeDashoffset: 'var(--ring-offset)' },
        },
        'data-stream': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
