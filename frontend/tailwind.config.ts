import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Cosmic color palette
        void: {
          950: '#030014',
          900: '#0a0520',
          800: '#0f0a2a',
          700: '#1a1040',
          600: '#251560',
        },
        nebula: {
          purple: '#7c3aed',
          violet: '#a855f7',
          pink: '#ec4899',
          blue: '#3b82f6',
        },
        star: {
          white: '#f8fafc',
          gold: '#fbbf24',
          cyan: '#06b6d4',
        },
        aurora: {
          green: '#22c55e',
          teal: '#14b8a6',
        }
      },
      fontFamily: {
        display: ['var(--font-space-grotesk)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'monospace'],
      },
      backgroundImage: {
        'cosmic-gradient': 'radial-gradient(ellipse at top, #1a1040 0%, #030014 50%, #0a0520 100%)',
        'nebula-glow': 'radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.3) 0%, transparent 50%)',
        'star-field': 'radial-gradient(2px 2px at 20px 30px, #f8fafc, transparent), radial-gradient(2px 2px at 40px 70px, rgba(248, 250, 252, 0.8), transparent), radial-gradient(1px 1px at 90px 40px, #f8fafc, transparent), radial-gradient(2px 2px at 130px 80px, rgba(248, 250, 252, 0.6), transparent)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'orbit': 'orbit 20s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(124, 58, 237, 0.4)' },
          '100%': { boxShadow: '0 0 40px rgba(168, 85, 247, 0.6)' },
        },
        orbit: {
          '0%': { transform: 'rotate(0deg) translateX(100px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(100px) rotate(-360deg)' },
        },
      },
      boxShadow: {
        'neon-purple': '0 0 20px rgba(124, 58, 237, 0.5), 0 0 40px rgba(124, 58, 237, 0.3)',
        'neon-cyan': '0 0 20px rgba(6, 182, 212, 0.5), 0 0 40px rgba(6, 182, 212, 0.3)',
      },
    },
  },
  plugins: [],
}
export default config






