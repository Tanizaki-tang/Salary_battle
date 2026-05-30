import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("desktopBridge", {
  mode: "desktop",
  apiBaseUrl: "http://127.0.0.1:18080",
});
