/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        podium: ['"FSP DEMO - PODIUM Sharp 4.11"', 'Inter', 'sans-serif'],
        inter: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Brand palette lifted from the existing landing page.
        ink: '#0c0c0c',
        abyss: '#091020',
        deep: '#0B2551',
        cyan: '#00d2ff',
        frost: '#A4F4FD',
        brand: '#3D81E3',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(30px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.9)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        drift: {
          '0%,100%': { transform: 'translate3d(0,0,0) scale(1)' },
          '33%': { transform: 'translate3d(6%,-4%,0) scale(1.12)' },
          '66%': { transform: 'translate3d(-5%,5%,0) scale(0.94)' },
        },
        sheen: {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '200% 50%' },
        },
      },
      animation: {
        drift: 'drift 26s ease-in-out infinite',
        'drift-slow': 'drift 38s ease-in-out infinite reverse',
        sheen: 'sheen 9s linear infinite',
      },
    },
  },
  plugins: [],
};
