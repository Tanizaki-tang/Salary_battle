import path from "path";
import { fileURLToPath } from "url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(frontendRoot, "..");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, "");
  const target = env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
  return {
    envDir: projectRoot,
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
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          ws: true,
        },
        "/resources": {
          target,
          changeOrigin: true,
        },
      },
    },
  };
});
