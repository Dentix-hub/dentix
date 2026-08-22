import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
import { VitePWA } from 'vite-plugin-pwa'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: 'prompt',
            includeAssets: ['icons/icon-192.png', 'icons/icon-512.png'],
            manifest: {
                name: 'DENTIX — إدارة العيادة',
                short_name: 'DENTIX',
                description: 'نظام إدارة العيادات السنية',
                theme_color: '#0ea5e9',
                background_color: '#ffffff',
                display: 'standalone',
                // 'any' lets the OS rotate freely (portrait <-> landscape) based on
                // physical device orientation. The previous 'portrait' value locked
                // the installed PWA out of landscape on tablets.
                orientation: 'any',
                scope: '/',
                start_url: '/',
                lang: 'ar',
                dir: 'rtl',
                icons: [
                    {
                        src: 'icons/icon-192.png',
                        sizes: '192x192',
                        type: 'image/png',
                        purpose: 'any maskable'
                    },
                    {
                        src: 'icons/icon-512.png',
                        sizes: '512x512',
                        type: 'image/png',
                        purpose: 'any maskable'
                    }
                ]
            },
            workbox: {
                // Remove stale Workbox precache generations after each successful
                // deployment so mobile/PWA sessions cannot retain an obsolete app shell.
                cleanupOutdatedCaches: true,

                // Cache these for offline use
                globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
                
                // SPA navigation fallback
                navigateFallback: '/index.html',
                navigateFallbackDenylist: [/^\/api/],
                
                // Don't cache API calls — always fresh from server
                runtimeCaching: [
                    {
                        urlPattern: /^https?.*\/api\/.*/i,
                        handler: 'NetworkOnly',  // API = always live, never cached
                    }
                ],
                
                // Keep the active clinical session on its current version until the
                // user confirms the update prompt exposed by virtual:pwa-register.
                skipWaiting: false,
                clientsClaim: false,
            }
        })
    ],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        host: true
    },
    build: {
        rolldownOptions: {
            output: {
                minify: {
                    compress: {
                        dropConsole: true,
                        dropDebugger: true,
                    },
                },
                codeSplitting: {
                    groups: [
                        {
                            name: 'vendor-react',
                            test: /node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/,
                        },
                        {
                            name: 'vendor-query',
                            test: /node_modules[\\/]@tanstack[\\/](react-query|react-table)[\\/]/,
                        },
                        {
                            name: 'vendor-charts',
                            test: /node_modules[\\/]recharts[\\/]/,
                        },
                        {
                            name: 'vendor-calendar',
                            test: /node_modules[\\/]@fullcalendar[\\/]/,
                        },
                        {
                            name: 'vendor-ui',
                            test: /node_modules[\\/](lucide-react|@headlessui[\\/]react)[\\/]/,
                        },
                        {
                            name: 'vendor-i18n',
                            test: /node_modules[\\/](i18next|react-i18next)[\\/]/,
                        },
                        {
                            name: 'vendor-utils',
                            test: /node_modules[\\/](axios|date-fns|zustand)[\\/]/,
                        },
                    ],
                },
            }
        },
        chunkSizeWarningLimit: 600,
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/setupTests.js',
        include: ['src/**/*.test.{js,jsx,ts,tsx}'],
        pool: 'threads',
        fileParallelism: false,
        isolate: true,
    }
})
