/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0B0D12',
        bone: '#F4F1EC',
        crimson: {
          DEFAULT: '#B3151B',
          bright: '#E0231C',
          light: '#FF5A4F',
        },
        ice: '#AEB8C6',
        mist: '#AEB8C6',
        steel: '#4A525E',
        dawn: '#D6C9B0',
      },
      fontFamily: {
        sans: ['Onest', 'sans-serif'],
        serif: ['"Cormorant Garamond"', 'serif'],
      },
      animation: {
        'fade-in': 'fadeIn 1.2s ease-out forwards',
        'fade-in-up': 'fadeInUp 0.7s ease-out forwards',
        'slide-up': 'slideUp 0.6s ease-out forwards',
        'appear': 'appear 0.4s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '10%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        appear: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}
