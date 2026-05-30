export type HrPersonalityMeta = {
  personality_id: string;
  name: string;
  tagline: string;
  emoji: string;
};

export const HR_PERSONALITY_CATALOG: HrPersonalityMeta[] = [
  { personality_id: "hr_newbie", name: "菜鸟新人", tagline: "紧张没底气，容易说漏信息", emoji: "🐣" },
  { personality_id: "hr_robot", name: "冷漠流程型", tagline: "按系统流程办事，几乎无情绪波动", emoji: "🤖" },
  { personality_id: "hr_aggressive", name: "强势压价型", tagline: "开门见山压价，耐心极低", emoji: "💪" },
  { personality_id: "hr_honest", name: "老实人型", tagline: "真诚坦率，容易被说服", emoji: "😇" },
  { personality_id: "hr_smiling_tiger", name: "笑面虎型", tagline: "表面热情，话术圆滑", emoji: "😊" },
];

export function findHrPersonalityMeta(personalityId?: string | null): HrPersonalityMeta | null {
  if (!personalityId) return null;
  return HR_PERSONALITY_CATALOG.find((item) => item.personality_id === personalityId) ?? null;
}

export function loadHrPersonalityMetaFromStorage(): HrPersonalityMeta | null {
  const raw = sessionStorage.getItem("hrPersonalityMeta");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as HrPersonalityMeta;
  } catch {
    return null;
  }
}

export function syncHrPersonalityMeta(session?: { hr_personality_id?: string } | null): HrPersonalityMeta | null {
  const stored = loadHrPersonalityMetaFromStorage();
  if (stored?.name) return stored;

  const resolved = findHrPersonalityMeta(session?.hr_personality_id);
  if (resolved) {
    sessionStorage.setItem("hrPersonalityMeta", JSON.stringify(resolved));
  }
  return resolved;
}
