/** 横屏气泡出场方式，供后端 text-turn 响应指定 */
export type BubbleEntrance = "fade" | "slam" | "slide";

const ENTRANCE_ALIASES: Record<string, BubbleEntrance> = {
  fade: "fade",
  slam: "slam",
  slide: "slide",
  float: "fade",
  emerge: "fade",
  drop: "slam",
  smash: "slam",
  rush: "slide",
  swipe: "slide",
  浮现: "fade",
  砸下: "slam",
  重重砸下: "slam",
  滑出: "slide",
  快速滑出: "slide",
};

export function normalizeBubbleEntrance(
  value: unknown,
  fallback: BubbleEntrance = "fade",
): BubbleEntrance {
  if (typeof value !== "string") return fallback;
  const key = value.trim().toLowerCase();
  return ENTRANCE_ALIASES[key] ?? ENTRANCE_ALIASES[value.trim()] ?? fallback;
}
