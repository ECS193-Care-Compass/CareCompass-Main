/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./App.tsx",
    "./Chat.tsx",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./figma_components/**/*.{js,ts,jsx,tsx}",
  ],
    theme: {
      extend: {
        colors: {
          primary: {
            DEFAULT: "var(--primary)",
            foreground: "var(--primary-foreground)",
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

