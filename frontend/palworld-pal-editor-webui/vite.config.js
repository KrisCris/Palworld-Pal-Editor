import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
// import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    // VitePWA({
    //   registerType: 'autoUpdate', 
    //   workbox: {
    //     globPatterns: [],
    //     runtimeCaching: [
    //       {
    //         urlPattern: ({request}) => request.destination === 'image',
    //         handler: 'CacheFirst',
    //         options: {
    //           cacheName: 'images-cache',
    //           expiration: {
    //             maxEntries: 150,
    //             maxAgeSeconds: 24 * 60 * 60,
    //           },
    //           cacheableResponse: {
    //             statuses: [0, 200],
    //           },
    //         },
    //       },
    //       {
    //         urlPattern: ({request}) => request.destination !== 'image',
    //         handler: 'NetworkOnly',
    //       },
    //     ],
    //   },
    //   devOptions: {
    //     enabled: true
    //   }, 
    //   manifest: {
    //     name: 'Palworld Pal Editor',
    //     short_name: 'Pal Editor',
    //     description: 'Palworld Pal Editor, Authored by _connlost.',
    //     theme_color: '#ffffff',
    //     icons: [
    //       {
    //         src: '/icons/512.png',
    //         sizes: '512x512',
    //         type: 'image/png'
    //       }
    //     ]
    //   }
    // })
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
