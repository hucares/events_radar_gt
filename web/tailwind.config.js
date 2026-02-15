/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        nyc: {
          navy: "#1a1a2e",
          steel: "#2d3748",
          yellow: "#f7c948",
          orange: "#e8590c",
          sky: "#4299e1",
        },
      },
    },
  },
  plugins: [],
};
