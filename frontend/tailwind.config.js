/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        'space-grotesk': ['var(--font-space-grotesk)', 'sans-serif'],
      },
      screens: {
        short: { raw: '(max-height: 769px)' },
      },
      colors: {
        blue: {
          200: '#7599d1',
          300: '#5883c8',
          400: '#3e6eba',
          500: '#345D9D',
          600: '#2e528a',
          700: '#274677',
          800: '#213b64',
          900: '#122036',
        },
      },
    },
  },
  plugins: [
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@tailwindcss/typography'),
  ],
}
