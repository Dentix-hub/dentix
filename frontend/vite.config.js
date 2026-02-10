import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
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
        rollupOptions: {
            output: {
                manualChunks: {
                    // React core - loaded first, cached long
                    'vendor-react': ['react', 'react-dom', 'react-router-dom'],
                    // Charts - only loaded when Dashboard opens
                    'vendor-charts': ['recharts'],
                    // UI libraries - shared across app
                    'vendor-ui': ['framer-motion', 'lucide-react'],
                    // Data fetching - small but critical
                    'vendor-query': ['@tanstack/react-query'],
                }
            }
        },
        // Increase warning limit since we're chunking properly
        chunkSizeWarningLimit: 500,
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/setupTests.js',
    }
})
