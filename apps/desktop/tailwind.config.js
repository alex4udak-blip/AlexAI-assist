/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#09090b',
          secondary: '#0f0f12',
          tertiary: '#18181b',
          elevated: '#1f1f23',
          hover: '#27272a',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.05)',
          default: 'rgba(255, 255, 255, 0.08)',
          strong: 'rgba(255, 255, 255, 0.12)',
        },
        text: {
          primary: '#fafafa',
          secondary: '#a1a1aa',
          tertiary: '#71717a',
          muted: '#52525b',
        },
        accent: {
          primary: '#6366f1',
          hover: '#818cf8',
          muted: 'rgba(99, 102, 241, 0.1)',
        },
        status: {
          success: '#22c55e',
          warning: '#eab308',
          error: '#ef4444',
          info: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
};
