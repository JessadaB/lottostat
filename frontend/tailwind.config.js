/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#121416",
        panel: "#f8faf8",
        line: "#d9ded8",
        mint: "#1f9d78",
        coral: "#d96459",
        amber: "#d99b31"
      }
    }
  },
  plugins: []
};
