/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        void: '#030303',
        surface: {
          DEFAULT: '#121212',
          light: '#1a1a1a',
          elevation: {
            1: '#1a1a1a',
            2: '#222222',
            3: '#2a2a2a',
          },
        },
        signal: '#10b981',
        accent: '#3b82f6',
        text: {
          primary: '#f3f4f6',
          secondary: '#9ca3af',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrainsMono', 'monospace'],
      },
    },
  },
  plugins: [],
};
