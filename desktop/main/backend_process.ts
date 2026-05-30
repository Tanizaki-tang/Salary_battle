import { ChildProcess, spawn } from "node:child_process";

let backendProcess: ChildProcess | null = null;

export function startBackend(): ChildProcess {
  /**
   * 输入: 无
   * 输出: ChildProcess (FastAPI 子进程句柄)
   */
  backendProcess = spawn("python", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18080"], {
    cwd: "../backend",
    stdio: "inherit",
    shell: true,
  });
  return backendProcess;
}

export function stopBackend(): void {
  /**
   * 输入: 无
   * 输出: 无 (终止子进程)
   */
  backendProcess?.kill();
  backendProcess = null;
}
