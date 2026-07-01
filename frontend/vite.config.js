import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: 'autoUpdate',
            includeAssets: ['icon-192x192.png', 'icon-512x512.png'],
            manifest: {
                name: 'Legate — Digital Legacy Vault',
                short_name: 'Legate',
                description: 'Securely store and deliver your digital legacy',
                theme_color: '#3D4F6B',
                background_color: '#F0F2F5',
                display: 'standalone',
                start_url: '/',
                icons: [
                    { src: 'icon-192x192.png', sizes: '192x192', type: 'image/png' },
                    { src: 'icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
                ],
            },
            workbox: {
                // NetworkFirst for API calls: try network, fall back to cache
                runtimeCaching: [
                    {
                        // Only cache GET requests — POST/PATCH/DELETE must never be
                        // intercepted by the SW. Without the method filter, Workbox's
                        // NetworkFirst handler tries to use the request as a Cache API
                        // key (Cache API only accepts GET), converting POST to GET and
                        // causing 405 from the backend.
                        urlPattern: /\/api\/.*/i,
                        handler: 'NetworkFirst',
                        method: 'GET',
                        options: {
                            cacheName: 'api-cache',
                            networkTimeoutSeconds: 10,
                            expiration: { maxEntries: 50, maxAgeSeconds: 300 },
                            cacheableResponse: { statuses: [0, 200] },
                        },
                    },
                ],
            },
        }),
    ],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        open: true,
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./src/test/setup.ts'],
        include: ['src/test/**/*.{test,spec}.{ts,tsx}'],
    },
});
