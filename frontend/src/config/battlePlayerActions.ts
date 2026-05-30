export type PlayerActionId =
  | "strong_push"
  | "probe"
  | "concede"
  | "counter_pressure"
  | "expose_rhetoric"
  | "off_topic";

export type BackendStrategy = "strong_push" | "probe" | "concede" | "counter_pressure";

export type PlayerActionCard = {
  id: PlayerActionId;
  label: string;
  emoji: string;
  desc: string;
  strategy?: BackendStrategy;
  prompt: string;
};

export const PLAYER_ACTION_CARDS: PlayerActionCard[] = [
  {
    id: "strong_push",
    label: "强硬要求",
    emoji: "💪",
    desc: "明确底线，直接要价",
    strategy: "strong_push",
    prompt: "我的底线很明确，请把薪资包拆开说明，并给出可接受的上调空间。",
  },
  {
    id: "probe",
    label: "信息搜集",
    emoji: "🔍",
    desc: "旁敲侧击，摸清底牌",
    strategy: "probe",
    prompt: "我想先了解这份 offer 的完整结构，包括底薪、绩效、补贴和期权各自怎么算。",
  },
  {
    id: "concede",
    label: "温和协商",
    emoji: "🤝",
    desc: "留有余地，换取信息",
    strategy: "concede",
    prompt: "整体方向我可以接受，但在关键条款上还需要再对齐，我们看看有没有双赢的调整方案。",
  },
  {
    id: "counter_pressure",
    label: "反客为主",
    emoji: "♟️",
    desc: "转移焦点，掌握节奏",
    strategy: "counter_pressure",
    prompt: "在聊具体数字前，我想先确认岗位权责和长期成长空间，再反推合理的薪酬区间。",
  },
  {
    id: "expose_rhetoric",
    label: "拆穿话术",
    emoji: "🪤",
    desc: "点破陷阱，争取主动",
    strategy: "counter_pressure",
    prompt: "您刚才提到的总包和弹性福利，听起来有些模糊，能否逐项落到书面条款，避免口头承诺？",
  },
  {
    id: "off_topic",
    label: "非谈判内容",
    emoji: "💬",
    desc: "闲聊缓冲，观察反应",
    prompt: "顺便问一下团队日常协作和加班节奏，我想先感受一下真实的工作状态。",
  },
];

export function getPlayerActionCard(id: PlayerActionId): PlayerActionCard | undefined {
  return PLAYER_ACTION_CARDS.find((card) => card.id === id);
}
