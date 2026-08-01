import { fileURLToPath } from "node:url";

import { renderToString } from "@vue/server-renderer";
import { createSSRApp, h } from "vue";
import { createServer } from "vite";

const server = await createServer({
  root: fileURLToPath(new URL("../", import.meta.url)),
  appType: "custom",
  logLevel: "silent",
  server: { middlewareMode: true },
});

export const loadVueModule = path => server.ssrLoadModule(path);

export async function renderVue(component, { pinia, props = {}, slots = {} } = {}) {
  const app = createSSRApp({ render: () => h(component, props, slots) });
  if (pinia) app.use(pinia);
  const context = {};
  const html = await renderToString(app, context);
  return html + Object.values(context.teleports ?? {}).join("");
}

export const closeVueServer = () => server.close();
