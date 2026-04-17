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
                    DEFAULT: '#0891B2',
                    50: '#F0FDFA',
                    100: '#E0F2FE',
                    500: '#0891B2',
                    600: '#0E7490',
                    700: '#155E75',
                },
                medical: {
                    light: '#E0F2FE',
                    DEFAULT: '#0891B2',
                    dark: '#155E75',
                },
                health: {
                    light: '#DCFCE7',
                    DEFAULT: '#22C55E',
                    dark: '#166534',
                },
                'mint-tint': '#F0FDFA',
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
