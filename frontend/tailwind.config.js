/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: { panel: "0 16px 48px rgba(7, 19, 42, 0.12)" },
    },
  },
  plugins: [],
};

