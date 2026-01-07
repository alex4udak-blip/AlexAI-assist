/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        bg: {
          primary: '#000000',
          secondary: '#0a0a0a',
          tertiary: '#111111',
          elevated: '#161616',
          hover: '#1a1a1a',
        },
        // Surfaces
        surface: {
          primary: 'rgba(255, 255, 255, 0.03)',
          hover: 'rgba(255, 255, 255, 0.05)',
          active: 'rgba(255, 255, 255, 0.08)',
        },
        // Borders
        border: {
          subtle: 'rgba(255, 255, 255, 0.06)',
          default: 'rgba(255, 255, 255, 0.1)',
          strong: 'rgba(255, 255, 255, 0.15)',
        },
        // Text
        text: {
          primary: '#ffffff',
          secondary: 'rgba(255, 255, 255, 0.7)',
          tertiary: 'rgba(255, 255, 255, 0.5)',
          muted: 'rgba(255, 255, 255, 0.3)',
        },
        // Accent - violet gradient like Linear
        accent: {
          primary: '#8B5CF6',
          secondary: '#6366F1',
          tertiary: '#3B82F6',
          glow: 'rgba(139, 92, 246, 0.4)',
          muted: 'rgba(139, 92, 246, 0.1)',
        },
        // Status
        status: {
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],      // 12px
        'sm': ['0.8125rem', { lineHeight: '1.25rem' }], // 13px
        'base': ['0.875rem', { lineHeight: '1.5rem' }], // 14px
        'lg': ['1rem', { lineHeight: '1.5rem' }],       // 16px
        'xl': ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],      // 24px
        '3xl': ['2rem', { lineHeight: '2.25rem' }],     // 32px
        '4xl': ['2.5rem', { lineHeight: '2.75rem' }],   // 40px
      },
      letterSpacing: {
        tighter: '-0.02em',
        tight: '-0.01em',
      },
      boxShadow: {
        glow: '0 0 20px rgba(139, 92, 246, 0.4)',
        'glow-sm': '0 0 10px rgba(139, 92, 246, 0.3)',
        sm: '0 1px 2px rgba(0, 0, 0, 0.5)',
        md: '0 4px 12px rgba(0, 0, 0, 0.5)',
        lg: '0 8px 24px rgba(0, 0, 0, 0.5)',
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(135deg, #8B5CF6 0%, #6366F1 50%, #3B82F6 100%)',
        'card-gradient': 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.03), transparent)',
        'glow-gradient': 'linear-gradient(to bottom right, rgba(139, 92, 246, 0.1), transparent)',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-in': 'slide-in 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
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
      },
    },
  },
  plugins: [],
};
