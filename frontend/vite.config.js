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
            registerType: 'autoUpdate',
            includeAssets: ['favicon.ico', 'icons/icon-192.png', 'icons/icon-512.png'],
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
                    },
                    {
                        urlPattern: /^https?.*\.(png|jpg|jpeg|svg|gif|webp)$/i,
                        handler: 'CacheFirst',
                        options: {
                            cacheName: 'images-cache',
                            expiration: {
                                maxEntries: 50,
                                maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
                            }
                        }
                    }
                ],
                
                // Skip waiting — update immediately when new version deployed
                skipWaiting: true,
                clientsClaim: true,
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
    esbuild: {
        drop: ['console', 'debugger'],
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    'vendor-react': ['react', 'react-dom', 'react-router-dom'],
                    'vendor-query': ['@tanstack/react-query', '@tanstack/react-table'],
                    'vendor-charts': ['recharts'],
                    'vendor-calendar': [
                        '@fullcalendar/core',
                        '@fullcalendar/react',
                        '@fullcalendar/daygrid',
                        '@fullcalendar/timegrid',
                        '@fullcalendar/interaction'
                    ],
                    'vendor-ui': ['lucide-react', '@headlessui/react'],
                    'vendor-i18n': ['i18next', 'react-i18next'],
                    'vendor-utils': ['axios', 'date-fns', 'zustand'],
                }
            }
        },
        chunkSizeWarningLimit: 600,
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/setupTests.js',
        include: ['src/**/*.test.{js,jsx,ts,tsx}'],
        pool: 'forks',
        maxWorkers: 1,
    }
})
