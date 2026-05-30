import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(frontendRoot, "..");

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@resources": path.resolve(projectRoot, "resources"),
    },
  },
  server: {
    fs: {
      allow: [projectRoot],
    },
  },
});
