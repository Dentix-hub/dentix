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
                sans: ['Inter', 'Cairo', 'sans-serif'],
                cairo: ['Cairo', 'sans-serif'],
                inter: ['Inter', 'sans-serif'],
            },
            spacing: {
                'card': '1.5rem',      // 24px
                'card-sm': '1rem',     // 16px
                'section': '2rem',     // 32px
                'page': '2rem',        // 32px
                'page-sm': '1rem',     // 16px
                'inline': '0.75rem',   // 12px
                'stack': '0.5rem',     // 8px
            },
            colors: {
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                    950: '#082f49',
                    DEFAULT: '#0ea5e9',
                },
                secondary: {
                    50: '#f0fdfa',
                    100: '#ccfbf1',
                    200: '#99f6e4',
                    300: '#5eead4',
                    400: '#2dd4bf',
                    500: '#14b8a6',
                    600: '#0d9488',
                    700: '#0f766e',
                    800: '#115e59',
                    900: '#134e4a',
                    950: '#042f2e',
                    DEFAULT: '#14b8a6',
                },
                accent: {
                    50: '#fffbeb',
                    100: '#fef3c7',
                    200: '#fde68a',
                    300: '#fcd34d',
                    400: '#fbbf24',
                    500: '#f59e0b',
                    600: '#d97706',
                    700: '#b45309',
                    800: '#92400e',
                    900: '#78350f',
                    950: '#451a03',
                    DEFAULT: '#f59e0b',
                },
                success: {
                    DEFAULT: '#10b981',
                    light: '#d1fae5',
                    dark: '#065f46',
                },
                warning: {
                    DEFAULT: '#f59e0b',
                    light: '#fef3c7',
                    dark: '#92400e',
                },
                danger: {
                    DEFAULT: '#ef4444',
                    light: '#fee2e2',
                    dark: '#991b1b',
                },
                info: {
                    DEFAULT: '#3b82f6',
                    light: '#dbeafe',
                    dark: '#1e40af',
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
                // Compatibility aliases used by Finance V2 shared primitives.
                // Keep cards on the glass surface token, while popovers that must
                // fully obscure underlying content should use explicit solid
                // light/dark backgrounds.
                card: "var(--surface)",
                muted: "var(--surface-hover)",
                "text-primary": "var(--text-primary)",
                "text-secondary": "var(--text-secondary)",
                border: "var(--border)",
                input: "var(--input)",
                "input-focus": "var(--input-focus)",
            }
        },
    },
    plugins: [],
    safelist: [
        'bg-indigo-50', 'dark:bg-indigo-900/20', 'text-indigo-600', 'dark:text-indigo-400',
        'bg-emerald-50', 'dark:bg-emerald-900/20', 'text-emerald-600', 'dark:text-emerald-400',
        'bg-amber-50', 'dark:bg-amber-900/20', 'text-amber-600', 'dark:text-amber-400',
        'bg-red-50', 'dark:bg-red-900/20', 'text-red-600', 'dark:text-red-400',
        'bg-blue-50', 'dark:bg-blue-900/20', 'text-blue-600', 'dark:text-blue-400',
        'bg-teal-50', 'dark:bg-teal-900/20', 'text-teal-600', 'dark:text-teal-400',
        'bg-violet-50', 'dark:bg-violet-900/20', 'text-violet-600', 'dark:text-violet-400',
        'bg-sky-50', 'dark:bg-sky-900/20', 'text-sky-600', 'dark:text-sky-400',
    ],
}
