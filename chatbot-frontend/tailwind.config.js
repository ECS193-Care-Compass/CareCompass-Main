/** @type {import('tailwindcss').Config} */
export default {
content: [
  "./src/renderer/index.html",
  "./src/renderer/src/**/*.{js,ts,jsx,tsx}",
  ],
    theme: {
      extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
          care: {
            light: '#a1d7d6',
            dark: '#005f63',
          }
        },
        borderRadius: {
          lg: "var(--radius)",
          md: "calc(var(--radius) - 2px)",
          sm: "calc(var(--radius) - 4px)",
          '3xl': '1.5rem', 
        }
      },
    },
  plugins: [require('@tailwindcss/typography')],
}

