import type { CardGameSettleResult } from "../card-game/types";
import type { SettleResultView } from "../runtime/battle_runtime_adapter";

export type HireVerdict = "hired" | "rejected";

export function resolveTextHireVerdict(
  result: SettleResultView,
  sessionPatience?: number | null,
): HireVerdict {
  const patience = result.stats?.final_patience ?? sessionPatience;
  if (typeof patience === "number" && patience <= 10) return "rejected";
  if (result.grade === "C" && result.final_score < 50) return "rejected";
  return "hired";
}

export function resolveCardHireVerdict(result: CardGameSettleResult): HireVerdict {
  return result.outcome === "collapsed" ? "rejected" : "hired";
}

export function hireVerdictLabel(verdict: HireVerdict): string {
  return verdict === "hired" ? "录用" : "未录用";
}
