/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3D4F6B',
        danger: '#C0392B',
        success: '#22C55E',
        'bg-primary': '#F0F2F5',
        'text-primary': '#0D1117',
        'text-secondary': '#6B7280',
        'border': '#E5E7EB',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
