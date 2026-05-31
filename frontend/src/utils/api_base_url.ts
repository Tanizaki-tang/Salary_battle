export function resolveApiBaseUrl() {
  const envBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
  if (!envBase) return "";
  try {
    const url = new URL(envBase);
    const isLocal = url.hostname === "127.0.0.1" || url.hostname === "localhost";
    const currentHost = window.location.hostname;
    const currentIsLocal = currentHost === "127.0.0.1" || currentHost === "localhost";
    if (isLocal && !currentIsLocal) return "";
  } catch {}
  return envBase;
}

