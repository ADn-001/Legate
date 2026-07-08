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
                        // Only cache GET requests made BY THE APP (fetch/XHR) — never a
                        // top-level browser navigation. Without the request.mode check,
                        // this rule also matched navigations, which is exactly what
                        // happens when a user clicks a one-time check-in confirm/snooze/
                        // emergency-pause link from an email: the service worker
                        // intercepted that navigation instead of letting it hit the
                        // network directly, so the token was never actually redeemed
                        // server-side and the user landed on a cached/fallback page
                        // instead of the backend's confirmation page. Those links are
                        // single-use and must never be served from cache.
                        //
                        // Also: without the method filter, Workbox's NetworkFirst
                        // handler tries to use the request as a Cache API key (Cache API
                        // only accepts GET), converting POST to GET and causing 405 from
                        // the backend.
                        urlPattern: function (_a) {
                            var url = _a.url, request = _a.request;
                            return request.mode !== 'navigate' && /\/api\//.test(url.pathname);
                        },
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
                // Belt-and-suspenders: even if a navigate-fallback route exists
                // (app-shell pattern), never redirect an /api/* navigation to the
                // SPA shell. Covers the same one-time-token-link scenario above.
                navigateFallbackDenylist: [/^\/api\//],
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
