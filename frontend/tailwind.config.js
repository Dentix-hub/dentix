/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Cairo', 'sans-serif'],
                cairo: ['Cairo', 'sans-serif'],
            },
            colors: {
                primary: {
                    DEFAULT: '#0ea5e9',
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                },
                // Semantic Colors
                background: "var(--background)",
                surface: "var(--surface)",
                "surface-hover": "var(--surface-hover)",
                "text-primary": "var(--text-primary)",
                "text-secondary": "var(--text-secondary)",
                border: "var(--border)",
                input: "var(--input)",
                "input-focus": "var(--input-focus)",
            }
        },
    },
    plugins: [],
}
