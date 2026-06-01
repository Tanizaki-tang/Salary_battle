import axios from "axios";
import { resolveApiBaseUrl } from "../utils/api_base_url";
import { buildRuntimeAuthHeaders } from "../utils/app_settings";

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
});

apiClient.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  const authHeaders = buildRuntimeAuthHeaders();
  Object.entries(authHeaders).forEach(([key, value]) => {
    config.headers.set?.(key, value);
    if (!config.headers.set) {
      (config.headers as Record<string, string>)[key] = value;
    }
  });
  return config;
});
