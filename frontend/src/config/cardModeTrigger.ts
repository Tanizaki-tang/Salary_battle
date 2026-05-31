/**
 * 文字阶段 hr_patience（0–100）低于阈值时，经预警过场后进入卡牌阶段。
 * 阈值须低于各性格开场满意度（scene 基准 80 + patience_bias），避免一进场就触发。
 * 阈值越高 → 越早进卡牌（需掉的耐心越少）。
 */
export const CARD_MODE_MIN_TEXT_ROUNDS = 1;

export const HR_PATIENCE_CARD_MODE_THRESHOLDS: Record<string, number> = {
  /** 开场约 62（80−18），再掉 ~4 即可进卡牌 */
  hr_aggressive: 58,
  /** 开场约 78，再掉 ~10 */
  hr_smiling_tiger: 68,
  /** 开场约 85 */
  hr_robot: 72,
  /** 开场约 86 */
  hr_honest: 70,
  /** 开场约 88 */
  hr_newbie: 72,
};

export const DEFAULT_CARD_MODE_THRESHOLD = 68;

/** 距离阈值多少以内显示「耐心告急」提示 */
export const CARD_MODE_WARNING_MARGIN = 10;

/** 切入卡牌前的系统预警（逐条展示，兼作过场） */
export const CARD_MODE_PRELUDE_MESSAGES = [
  "⚠️ 对方回复明显变短，谈薪气氛骤然紧张…",
  "⚠️ HR 明显失去了耐心，言语里开始带刺",
  "🔥 决战在所难免 —— 策略卡牌博弈即将开始",
] as const;

export const CARD_MODE_PRELUDE_LINE_MS = 1400;
export const CARD_MODE_PRELUDE_PAUSE_MS = 700;

export function getCardModeThreshold(personalityId: string | undefined): number {
  const id = (personalityId || "").trim();
  return HR_PATIENCE_CARD_MODE_THRESHOLDS[id] ?? DEFAULT_CARD_MODE_THRESHOLD;
}

export function shouldUnlockCardMode(
  hrPatience: number,
  personalityId: string | undefined,
  roundIndex = 1,
): boolean {
  if (roundIndex < CARD_MODE_MIN_TEXT_ROUNDS) return false;
  return hrPatience < getCardModeThreshold(personalityId);
}

export function isCardModeApproaching(
  hrPatience: number,
  personalityId: string | undefined,
  roundIndex = 1,
): boolean {
  if (roundIndex < CARD_MODE_MIN_TEXT_ROUNDS) return false;
  const threshold = getCardModeThreshold(personalityId);
  return hrPatience >= threshold && hrPatience < threshold + CARD_MODE_WARNING_MARGIN;
}

export function cardModeApproachingHint(hrPatience: number, threshold: number): string {
  return `⚠️ HR 耐心告急（${hrPatience} → 阈值 ${threshold}），决战逼近…`;
}

export function cardModeThresholdHint(threshold: number): string {
  return `卡牌决战阈值：HR 耐心 < ${threshold}（至少聊 ${CARD_MODE_MIN_TEXT_ROUNDS} 轮后生效）`;
}
