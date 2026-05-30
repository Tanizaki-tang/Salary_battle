import type { CardStrategyId } from "./types";

export type CardGameCard = {
  id: CardStrategyId;
  label: string;
  emoji: string;
  desc: string;
  tone: "red" | "blue" | "green" | "yellow" | "purple" | "gray";
};

export const CARD_GAME_CARDS: CardGameCard[] = [
  { id: "strong_push", label: "强硬要求", emoji: "💪", desc: "直接要价，最强涨薪", tone: "red" },
  { id: "probe", label: "信息搜集", emoji: "🔍", desc: "摸清底牌，推工时保障", tone: "blue" },
  { id: "concede", label: "温和协商", emoji: "🤝", desc: "恢复满意度", tone: "green" },
  { id: "counter_pressure", label: "反客为主", emoji: "♟️", desc: "打乱节奏，逼出预算", tone: "yellow" },
  { id: "expose_rhetoric", label: "拆穿话术", emoji: "🪤", desc: "点破模糊，推保障", tone: "purple" },
  { id: "off_topic", label: "非谈判内容", emoji: "💬", desc: "闲聊救场，不推条件", tone: "gray" },
];

export function getCardGameCard(id: CardStrategyId): CardGameCard | undefined {
  return CARD_GAME_CARDS.find((c) => c.id === id);
}
