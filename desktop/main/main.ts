import { app, BrowserWindow } from "electron";
import path from "node:path";
import { startBackend, stopBackend } from "./backend_process";

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 420,
    height: 860,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.loadURL("http://127.0.0.1:5173");
  return win;
}

app.whenReady().then(() => {
  startBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});
