import axios from "axios";
import { resolveApiBaseUrl } from "../utils/api_base_url";

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
});
