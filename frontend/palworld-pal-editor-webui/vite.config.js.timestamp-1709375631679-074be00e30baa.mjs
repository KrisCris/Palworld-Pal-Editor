// vite.config.js
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "file:///Users/connlost/Coding/Palworld-Pal-Editor/frontend/palworld-pal-editor-webui/node_modules/vite/dist/node/index.js";
import vue from "file:///Users/connlost/Coding/Palworld-Pal-Editor/frontend/palworld-pal-editor-webui/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import vueJsx from "file:///Users/connlost/Coding/Palworld-Pal-Editor/frontend/palworld-pal-editor-webui/node_modules/@vitejs/plugin-vue-jsx/dist/index.mjs";
import { VitePWA } from "file:///Users/connlost/Coding/Palworld-Pal-Editor/frontend/palworld-pal-editor-webui/node_modules/vite-plugin-pwa/dist/index.js";
var __vite_injected_original_import_meta_url = "file:///Users/connlost/Coding/Palworld-Pal-Editor/frontend/palworld-pal-editor-webui/vite.config.js";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    vueJsx()
    // VitePWA({
    //   registerType: 'autoUpdate', 
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
    //         src: '@/assets/logo.ico',
    //         sizes: '192x192',
    //         type: 'image/ico'
    //       },
    //       {
    //         src: '@/assets/logo.ico',
    //         sizes: '512x512',
    //         type: 'image/ico'
    //       }
    //     ]
    //   }
    // })
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url))
    }
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:58080/",
        changeOrigin: true
      },
      "/image": {
        target: "http://127.0.0.1:58080/",
        changeOrigin: true
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvVXNlcnMvY29ubmxvc3QvQ29kaW5nL1BhbHdvcmxkLVBhbC1FZGl0b3IvZnJvbnRlbmQvcGFsd29ybGQtcGFsLWVkaXRvci13ZWJ1aVwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiL1VzZXJzL2Nvbm5sb3N0L0NvZGluZy9QYWx3b3JsZC1QYWwtRWRpdG9yL2Zyb250ZW5kL3BhbHdvcmxkLXBhbC1lZGl0b3Itd2VidWkvdml0ZS5jb25maWcuanNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL1VzZXJzL2Nvbm5sb3N0L0NvZGluZy9QYWx3b3JsZC1QYWwtRWRpdG9yL2Zyb250ZW5kL3BhbHdvcmxkLXBhbC1lZGl0b3Itd2VidWkvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBmaWxlVVJMVG9QYXRoLCBVUkwgfSBmcm9tICdub2RlOnVybCdcblxuaW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcbmltcG9ydCB2dWUgZnJvbSAnQHZpdGVqcy9wbHVnaW4tdnVlJ1xuaW1wb3J0IHZ1ZUpzeCBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUtanN4J1xuaW1wb3J0IHsgVml0ZVBXQSB9IGZyb20gJ3ZpdGUtcGx1Z2luLXB3YSdcblxuLy8gaHR0cHM6Ly92aXRlanMuZGV2L2NvbmZpZy9cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFtcbiAgICB2dWUoKSxcbiAgICB2dWVKc3goKSxcbiAgICAvLyBWaXRlUFdBKHtcbiAgICAvLyAgIHJlZ2lzdGVyVHlwZTogJ2F1dG9VcGRhdGUnLCBcbiAgICAvLyAgIGRldk9wdGlvbnM6IHtcbiAgICAvLyAgICAgZW5hYmxlZDogdHJ1ZVxuICAgIC8vICAgfSwgXG4gICAgLy8gICBtYW5pZmVzdDoge1xuICAgIC8vICAgICBuYW1lOiAnUGFsd29ybGQgUGFsIEVkaXRvcicsXG4gICAgLy8gICAgIHNob3J0X25hbWU6ICdQYWwgRWRpdG9yJyxcbiAgICAvLyAgICAgZGVzY3JpcHRpb246ICdQYWx3b3JsZCBQYWwgRWRpdG9yLCBBdXRob3JlZCBieSBfY29ubmxvc3QuJyxcbiAgICAvLyAgICAgdGhlbWVfY29sb3I6ICcjZmZmZmZmJyxcbiAgICAvLyAgICAgaWNvbnM6IFtcbiAgICAvLyAgICAgICB7XG4gICAgLy8gICAgICAgICBzcmM6ICdAL2Fzc2V0cy9sb2dvLmljbycsXG4gICAgLy8gICAgICAgICBzaXplczogJzE5MngxOTInLFxuICAgIC8vICAgICAgICAgdHlwZTogJ2ltYWdlL2ljbydcbiAgICAvLyAgICAgICB9LFxuICAgIC8vICAgICAgIHtcbiAgICAvLyAgICAgICAgIHNyYzogJ0AvYXNzZXRzL2xvZ28uaWNvJyxcbiAgICAvLyAgICAgICAgIHNpemVzOiAnNTEyeDUxMicsXG4gICAgLy8gICAgICAgICB0eXBlOiAnaW1hZ2UvaWNvJ1xuICAgIC8vICAgICAgIH1cbiAgICAvLyAgICAgXVxuICAgIC8vICAgfVxuICAgIC8vIH0pXG4gIF0sXG4gIHJlc29sdmU6IHtcbiAgICBhbGlhczoge1xuICAgICAgJ0AnOiBmaWxlVVJMVG9QYXRoKG5ldyBVUkwoJy4vc3JjJywgaW1wb3J0Lm1ldGEudXJsKSlcbiAgICB9XG4gIH0sXG4gIHNlcnZlcjoge1xuICAgIHByb3h5OiB7XG4gICAgICAnL2FwaSc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMTo1ODA4MC8nLFxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWVcbiAgICAgIH0sXG4gICAgICAnL2ltYWdlJzoge1xuICAgICAgICB0YXJnZXQ6ICdodHRwOi8vMTI3LjAuMC4xOjU4MDgwLycsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZVxuICAgICAgfVxuICAgIH1cbiAgfVxufSlcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBeVosU0FBUyxlQUFlLFdBQVc7QUFFNWIsU0FBUyxvQkFBb0I7QUFDN0IsT0FBTyxTQUFTO0FBQ2hCLE9BQU8sWUFBWTtBQUNuQixTQUFTLGVBQWU7QUFMME8sSUFBTSwyQ0FBMkM7QUFRblQsSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsU0FBUztBQUFBLElBQ1AsSUFBSTtBQUFBLElBQ0osT0FBTztBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLEVBeUJUO0FBQUEsRUFDQSxTQUFTO0FBQUEsSUFDUCxPQUFPO0FBQUEsTUFDTCxLQUFLLGNBQWMsSUFBSSxJQUFJLFNBQVMsd0NBQWUsQ0FBQztBQUFBLElBQ3REO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sT0FBTztBQUFBLE1BQ0wsUUFBUTtBQUFBLFFBQ04sUUFBUTtBQUFBLFFBQ1IsY0FBYztBQUFBLE1BQ2hCO0FBQUEsTUFDQSxVQUFVO0FBQUEsUUFDUixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsTUFDaEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
