export type AppSettings = {
  volume: number;
  userApiKey: string;
  internalDebugEnabled: boolean;
  debugPassword: string;
  asrSensitivity: number;
};

const STORAGE_KEY = "salaryBattleAppSettings";
const LEGACY_BGM_VOLUME_KEY = "bgmVolume";

const DEFAULT_SETTINGS: AppSettings = {
  volume: 0.6,
  userApiKey: "",
  internalDebugEnabled: false,
  debugPassword: "",
  asrSensitivity: 0.5,
};

function clampVolume(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return DEFAULT_SETTINGS.volume;
  return Math.max(0, Math.min(1, numeric));
}

function clampUnitFloat(value: unknown, fallback: number) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(0, Math.min(1, numeric));
}

export function loadAppSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<AppSettings>;
      return {
        volume: clampVolume(parsed.volume),
        userApiKey: typeof parsed.userApiKey === "string" ? parsed.userApiKey.trim() : "",
        internalDebugEnabled: Boolean(parsed.internalDebugEnabled),
        debugPassword: typeof parsed.debugPassword === "string" ? parsed.debugPassword : "",
        asrSensitivity: clampUnitFloat((parsed as Partial<Record<string, unknown>>).asrSensitivity, DEFAULT_SETTINGS.asrSensitivity),
      };
    }

    const legacyVolume = localStorage.getItem(LEGACY_BGM_VOLUME_KEY);
    return {
      ...DEFAULT_SETTINGS,
      volume: clampVolume(legacyVolume),
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveAppSettings(next: AppSettings) {
  const normalized: AppSettings = {
    volume: clampVolume(next.volume),
    userApiKey: next.userApiKey.trim(),
    internalDebugEnabled: Boolean(next.internalDebugEnabled),
    debugPassword: next.debugPassword,
    asrSensitivity: clampUnitFloat(next.asrSensitivity, DEFAULT_SETTINGS.asrSensitivity),
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    localStorage.setItem(LEGACY_BGM_VOLUME_KEY, String(normalized.volume));
  } catch {
    /* ignore storage failures */
  }
  return normalized;
}

export function buildRuntimeAuthHeaders(settings: AppSettings = loadAppSettings()): Record<string, string> {
  const headers: Record<string, string> = {};
  if (settings.userApiKey.trim()) {
    headers["X-User-Api-Key"] = settings.userApiKey.trim();
  }
  if (settings.internalDebugEnabled && settings.debugPassword.trim()) {
    headers["X-Debug-Unlock-Password"] = settings.debugPassword.trim();
  }
  return headers;
}

export function buildVoiceAuthQuery(settings: AppSettings = loadAppSettings()): string {
  const params = new URLSearchParams();
  if (settings.userApiKey.trim()) {
    params.set("api_key", settings.userApiKey.trim());
  }
  if (settings.internalDebugEnabled && settings.debugPassword.trim()) {
    params.set("debug_password", settings.debugPassword.trim());
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function hasRuntimeCredential(settings: AppSettings = loadAppSettings()): boolean {
  return Boolean(
    settings.userApiKey.trim() || (settings.internalDebugEnabled && settings.debugPassword.trim()),
  );
}

export function hasDeveloperModeCredential(settings: AppSettings = loadAppSettings()): boolean {
  return Boolean(settings.internalDebugEnabled && settings.debugPassword.trim());
}
