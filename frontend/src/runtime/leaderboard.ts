export type LeaderboardEntry = {
  rank?: number;
  user_name: string;
  final_score: number;
  final_salary?: number;
  grade?: string;
  created_at?: string;
};

export const LOCAL_LEADERBOARD_KEY = "salaryBattleLeaderboard";
const LOCAL_LEADERBOARD_VERSION_KEY = "salaryBattleLeaderboardVersion";
/**  bump to wipe stale browser test data once */
const LOCAL_LEADERBOARD_VERSION = "v2";

export function clearLocalLeaderboard() {
  localStorage.removeItem(LOCAL_LEADERBOARD_KEY);
}

/** 版本变更时自动清空一次 localStorage 测试榜 */
export function migrateLocalLeaderboardOnce() {
  if (localStorage.getItem(LOCAL_LEADERBOARD_VERSION_KEY) === LOCAL_LEADERBOARD_VERSION) return;
  clearLocalLeaderboard();
  localStorage.setItem(LOCAL_LEADERBOARD_VERSION_KEY, LOCAL_LEADERBOARD_VERSION);
}

export function loadLocalLeaderboard(): LeaderboardEntry[] {
  try {
    const raw = localStorage.getItem(LOCAL_LEADERBOARD_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LeaderboardEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveLocalLeaderboardEntry(entry: Omit<LeaderboardEntry, "rank">) {
  const list = loadLocalLeaderboard();
  list.push({
    ...entry,
    user_name: entry.user_name.trim() || "候选人",
    created_at: entry.created_at || new Date().toISOString(),
  });
  list.sort((a, b) => b.final_score - a.final_score || String(b.created_at).localeCompare(String(a.created_at)));
  localStorage.setItem(LOCAL_LEADERBOARD_KEY, JSON.stringify(list.slice(0, 100)));
}

export function rankLeaderboard(entries: LeaderboardEntry[]): LeaderboardEntry[] {
  const sorted = [...entries].sort(
    (a, b) => b.final_score - a.final_score || String(b.created_at).localeCompare(String(a.created_at)),
  );
  return sorted.map((row, idx) => ({ ...row, rank: idx + 1 }));
}
