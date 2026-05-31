const PROD_FALLBACK_API_BASE_URL = "https://salary-battlesalary-battle-apisalary.onrender.com";

function isLocalHost(hostname: string) {
  return hostname === "127.0.0.1" || hostname === "localhost";
}

export function resolveApiBaseUrl() {
  const envBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
  const currentHost = window.location.hostname;
  const currentIsLocal = isLocalHost(currentHost);

  if (envBase) {
    try {
      const url = new URL(envBase);
      if (isLocalHost(url.hostname) && !currentIsLocal) return "";
    } catch {}
    return envBase;
  }

  if (!currentIsLocal && currentHost.endsWith("netlify.app")) {
    return PROD_FALLBACK_API_BASE_URL;
  }

  return "";
}
