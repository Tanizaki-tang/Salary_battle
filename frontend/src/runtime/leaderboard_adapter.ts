import axios from "axios";
import {
  loadLocalLeaderboard,
  migrateLocalLeaderboardOnce,
  rankLeaderboard,
  type LeaderboardEntry,
} from "./leaderboard";
import { resolveApiBaseUrl } from "../utils/api_base_url";

const baseURL = resolveApiBaseUrl();
const client = axios.create({ baseURL });
const mode = (import.meta.env.VITE_RUNTIME_MODE || "api").toLowerCase();

export async function fetchLeaderboard(limit = 50): Promise<LeaderboardEntry[]> {
  migrateLocalLeaderboardOnce();
  if (mode === "mock") {
    return rankLeaderboard(loadLocalLeaderboard()).slice(0, limit);
  }
  try {
    const res = await client.get("/api/v1/leaderboard", { params: { limit } });
    const entries = (res.data?.data?.entries ?? []) as LeaderboardEntry[];
    return rankLeaderboard(entries).slice(0, limit);
  } catch {
    return rankLeaderboard(loadLocalLeaderboard()).slice(0, limit);
  }
}
