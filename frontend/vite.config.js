import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { VitePWA } from 'vite-plugin-pwa'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Build identity is generated at build time so every deployed bundle can be
// traced back to the exact source revision. Never hard-code a build ID again.
function resolveBuildInfo(mode) {
    let sha = 'unknown';
    try {
        sha = execSync('git rev-parse HEAD', { cwd: __dirname, encoding: 'utf8' }).trim();
    } catch {
        sha = 'unknown';
    }
    const environment = process.env.VITE_ENVIRONMENT || mode || 'development';
    return {
        sha,
        shaShort: sha === 'unknown' ? 'unknown' : sha.slice(0, 7),
        builtAt: new Date().toISOString(),
        environment,
    };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
    define: {
        __BUILD_INFO__: JSON.stringify(resolveBuildInfo(mode)),
    },
    plugins: [
        react(),
        VitePWA({
            registerType: 'prompt',
            // Custom worker (plan §11): injectManifest gives us push handlers,
            // allowlisted notification clicks and full cache-policy control
            // while keeping the same public sw.js URL for existing installs.
            strategies: 'injectManifest',
            srcDir: 'src/pwa',
            filename: 'sw.js',
            includeAssets: [
                'icons/icon-192.png',
                'icons/icon-512.png',
                'icons/icon-192-maskable.png',
                'icons/icon-512-maskable.png',
                'icons/apple-touch-icon-180.png',
            ],
            manifest: {
                // Stable application identity bound to the canonical origin.
                // Installed PWAs, cookie stores, push subscriptions and future
                // WebAuthn RP configuration are all origin-bound: never change
                // this without the canonical-origin review (docs/pwa/canonical-origin.md).
                id: '/',
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
                        purpose: 'any'
                    },
                    {
                        src: 'icons/icon-512.png',
                        sizes: '512x512',
                        type: 'image/png',
                        purpose: 'any'
                    },
                    {
                        src: 'icons/icon-192-maskable.png',
                        sizes: '192x192',
                        type: 'image/png',
                        purpose: 'maskable'
                    },
                    {
                        src: 'icons/icon-512-maskable.png',
                        sizes: '512x512',
                        type: 'image/png',
                        purpose: 'maskable'
                    }
                ]
            },
            injectManifest: {
                // Measured precache (plan §11.3 / Phase 8): the app shell and
                // core chunks are precached; heavy lazy-route vendor chunks
                // (charts, calendar + their locale bundle) load on demand and
                // are cached at runtime by the service worker. Baseline was
                // 121 entries / 2.90 MiB. Note: workbox-build ignores inline
                // negation patterns, so exclusions use globIgnores.
                globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
                globIgnores: [
                    'assets/vendor-charts-*.js',
                    'assets/vendor-calendar-*.js',
                    'assets/es-*.js',
                ],
            },
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
}))
