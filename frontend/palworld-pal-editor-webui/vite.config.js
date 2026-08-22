import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      injectRegister: 'script',
      includeAssets: ['favicon.ico', 'icons/192.png', 'icons/512.png'],
      workbox: {
        // The app shell must always be served fresh from the network so a rebuild
        // is picked up immediately. We intentionally do NOT set navigateFallback
        // (which would serve a precached index.html for every navigation), and we
        // exclude index.html from the precache. Only versioned game images (keyed by
        // their commit hash via ?v=) are cached long-term; everything else updates.
        navigateFallback: null,
        globIgnores: ['**/index.html'],
        // Activate and take control immediately when a new service worker is
        // detected, so a shipped update is picked up without a manual reload.
        skipWaiting: true,
        clientsClaim: true,
        runtimeCaching: [
          {
            urlPattern: ({ request, url }) => request.destination === 'image'
              && url.pathname.startsWith('/image/')
              && /^[0-9a-f]{6}$/i.test(url.searchParams.get('v') || ''),
            handler: 'CacheFirst',
            options: {
              cacheName: 'backend-images',
              cacheableResponse: {
                statuses: [0, 200]
              },
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 30 * 24 * 60 * 60,
                purgeOnQuotaError: true
              }
            }
          }
        ]
      },
      manifest: {
        name: 'Palworld Pal Editor',
        short_name: 'Pal Editor',
        description: 'Palworld Pal Editor, made by _connlost.',
        theme_color: '#181818',
        background_color: '#181818',
        display: 'standalone',
        start_url: './',
        scope: './',
        icons: [
          {
            src: 'icons/192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: 'icons/512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:58080/',
        changeOrigin: true
      },
      '/image': {
        target: 'http://127.0.0.1:58080/',
        changeOrigin: true
      }
    }
  }
})
