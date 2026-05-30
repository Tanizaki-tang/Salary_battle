import type {
  CardDeltaView,
  CardGameOutcome,
  CardGameScoreBreakdown,
  CardGameSettleResult,
  CardGameState,
  CardGameStats,
  CardStrategyId,
  CardTurnResult,
} from "./types";
import { DEAL_THRESHOLDS } from "./types";

const SALARY_MIN = 8;
const SALARY_MAX = 22;

type BaseDelta = { satisfaction: number; salary_k: number; work_hours: number; security: number };

const BASE_DELTAS: Record<CardStrategyId, BaseDelta> = {
  strong_push: { satisfaction: -2.5, salary_k: 2.75, work_hours: 0.5, security: 0 },
  probe: { satisfaction: -1, salary_k: 1, work_hours: 2, security: 1 },
  concede: { satisfaction: 1.5, salary_k: 1, work_hours: -0.5, security: 0.5 },
  counter_pressure: { satisfaction: -1.5, salary_k: 2.25, work_hours: 1.5, security: 0.5 },
  expose_rhetoric: { satisfaction: -1.5, salary_k: 1.5, work_hours: 1.5, security: 1.5 },
  off_topic: { satisfaction: 2, salary_k: 0, work_hours: 0, security: 0 },
};

const PERSONALITY_MODS: Record<string, Partial<Record<CardStrategyId, [number, number, number, number]>>> = {
  hr_smiling_tiger: {
    strong_push: [1.1, 0.9, 1, 1],
    probe: [1.2, 1, 1, 1],
    concede: [1, 0.8, 1, 1],
    counter_pressure: [1.2, 1, 1, 1],
    expose_rhetoric: [1.5, 1.2, 1, 1.3],
    off_topic: [0.8, 1, 1, 1],
  },
  hr_honest: {
    strong_push: [0.8, 1.3, 1, 1],
    probe: [1, 1, 1.3, 1.5],
    concede: [1.3, 1.2, 1, 1],
    counter_pressure: [0.8, 1.2, 1, 1],
    expose_rhetoric: [0.7, 1, 1.3, 1.3],
    off_topic: [1.3, 1, 1, 1],
  },
  hr_aggressive: {
    strong_push: [1.5, 0.7, 1, 1],
    probe: [1.3, 1, 0.7, 1],
    counter_pressure: [1.5, 1, 1, 1],
    expose_rhetoric: [1.3, 1, 1, 1],
    off_topic: [0.5, 1, 1, 1],
  },
  hr_robot: { off_topic: [0.3, 1, 1, 1] },
  hr_newbie: {
    strong_push: [1.3, 1.5, 1, 1],
    probe: [1, 1, 1.5, 1.5],
    concede: [1.5, 1.2, 1, 1],
    counter_pressure: [1.3, 1.4, 1, 1],
    expose_rhetoric: [1, 1, 1.5, 1.5],
    off_topic: [1.5, 1, 1, 1],
  },
};

const ROUND_QUESTIONS = [
  "我们这边 base 15K 是统一标准，你怎么看？",
  "你更在意薪资数字，还是成长空间和团队氛围？",
  "如果绩效浮动比较大，你能接受怎样的区间？",
  "关于加班和弹性，你这边有什么底线吗？",
  "五险一金我们是按合规最低基数，这个你了解吗？",
  "你手上有其他 offer 吗？方便说一下区间吗？",
  "最后几个点我们对齐一下，你最想先谈哪一块？",
  "这是最后一轮了，你现在的整体感受如何？",
];

const OPTION_FALLBACK: Record<CardStrategyId, string> = {
  strong_push: "我希望薪资能再往上谈一档，15K 和我的预期还有差距。",
  probe: "方便把 base、绩效和加班规则拆开说明一下吗？",
  concede: "整体方向我能接受，我们看看还有哪些细节可以微调。",
  counter_pressure: "如果预算有限，你们最灵活的是薪资还是工时这块？",
  expose_rhetoric: "「弹性工作制」具体怎么算？我希望关键条款写进 offer。",
  off_topic: "听说团队氛围不错，你们平时协作节奏大概是怎样的？",
};

const ALL_STRATEGIES: CardStrategyId[] = [
  "strong_push",
  "probe",
  "concede",
  "counter_pressure",
  "expose_rhetoric",
  "off_topic",
];

const HR_REPLIES: Record<CardStrategyId, string[]> = {
  strong_push: ["你这个态度……我先记下了，但预算真的有限。", "别这么硬，咱们还是看能不能各退一步。"],
  probe: ["你问得挺细，我把结构给你拆开说明。", "这些细节我可以补充，但也要看整体 package。"],
  concede: ["你这个说法我比较能接受，我们再看怎么微调。", "嗯，有合作意愿就好办，我帮你争取一下。"],
  counter_pressure: ["你这个问题把我问住了……让我想想怎么回答。", "行，你先说说你的优先级，我再对应调整。"],
  expose_rhetoric: ["……好吧，这部分确实需要写清楚。", "被你看出来了，我们把它落到纸面上。"],
  off_topic: ["哈哈行，团队氛围确实不错，不过咱们还得聊正事。", "闲聊可以，但时间有限，待会还得回到 offer。"],
};

function roundMultiplier(roundIndex: number): number {
  if (roundIndex <= 2) return 1;
  if (roundIndex <= 4) return 1.3;
  if (roundIndex <= 6) return 1.6;
  return 2;
}

function personalityMod(pid: string, strategy: CardStrategyId): [number, number, number, number] {
  return PERSONALITY_MODS[pid]?.[strategy] ?? [1, 1, 1, 1];
}

function repeatPenalty(history: CardStrategyId[], strategy: CardStrategyId): number {
  let streak = 0;
  for (let i = history.length - 1; i >= 0; i -= 1) {
    if (history[i] === strategy) streak += 1;
    else break;
  }
  if (streak >= 2) return 0.5;
  if (streak >= 1) return 0.7;
  return 1;
}

function roundFavorPlayer(value: number, positiveGood: boolean): number {
  if (value === 0) return 0;
  if (positiveGood) return value > 0 ? Math.ceil(value - 1e-9) : Math.floor(value + 1e-9);
  return value < 0 ? Math.floor(value + 1e-9) : Math.ceil(value - 1e-9);
}

export function computeDelta(
  strategy: CardStrategyId,
  personalityId: string,
  roundIndex: number,
  history: CardStrategyId[],
): CardDeltaView {
  const base = BASE_DELTAS[strategy];
  const [satM, salM, whM, secM] = personalityMod(personalityId, strategy);
  const rm = roundMultiplier(roundIndex);
  const repeat = repeatPenalty(history, strategy);
  const rawSat = base.satisfaction * rm * satM * repeat;
  const rawSal = base.salary_k * rm * salM * repeat;
  const rawWh = base.work_hours * rm * whM * repeat;
  const rawSec = base.security * rm * secM * repeat;
  return {
    satisfaction: roundFavorPlayer(rawSat, false),
    salary_k: rawSal ? Math.round(rawSal * 10) / 10 : 0,
    work_hours: roundFavorPlayer(rawWh, true),
    security: roundFavorPlayer(rawSec, true),
  };
}

export function applyDelta(stats: CardGameStats, delta: CardDeltaView): CardGameStats {
  return {
    satisfaction: clamp(stats.satisfaction + delta.satisfaction, 0, 10),
    salary_k: clamp(stats.salary_k + delta.salary_k, SALARY_MIN, SALARY_MAX),
    work_hours: clamp(stats.work_hours + delta.work_hours, 0, 10),
    security: clamp(stats.security + delta.security, 0, 5),
  };
}

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

export function countConditions(stats: CardGameStats): number {
  let met = 0;
  if (stats.salary_k >= DEAL_THRESHOLDS.salary_k) met += 1;
  if (stats.work_hours >= DEAL_THRESHOLDS.work_hours) met += 1;
  if (stats.security >= DEAL_THRESHOLDS.security) met += 1;
  if (stats.satisfaction > DEAL_THRESHOLDS.satisfaction) met += 1;
  return met;
}

function pickQuestion(roundIndex: number, userName: string) {
  const idx = Math.min(Math.max(roundIndex - 1, 0), ROUND_QUESTIONS.length - 1);
  return `${userName}，${ROUND_QUESTIONS[idx]}`;
}

function pickHrReply(strategy: CardStrategyId) {
  const options = HR_REPLIES[strategy];
  return options[Math.floor(Math.random() * options.length)]!;
}

function pickPack(): { available: CardStrategyId[]; recommended: CardStrategyId } {
  const pool = [...ALL_STRATEGIES];
  for (let i = pool.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = pool[i]!;
    pool[i] = pool[j]!;
    pool[j] = tmp;
  }
  const available = pool.slice(0, 3);
  return { available, recommended: available[0]! };
}

export function createInitialState(
  sessionId: string,
  userId: string,
  userName: string,
  hrPersonalityId: string,
): CardGameState {
  const pack = pickPack();
  return {
    session_id: sessionId,
    user_id: userId,
    user_name: userName,
    hr_personality_id: hrPersonalityId,
    status: "ongoing",
    round_index: 1,
    max_round: 8,
    stats: { satisfaction: 6, salary_k: 15, work_hours: 2, security: 1 },
    current_question: pickQuestion(1, userName),
    available_strategies: pack.available,
    option_replies: Object.fromEntries(pack.available.map((k) => [k, OPTION_FALLBACK[k]])),
    recommended_strategy: pack.recommended,
    last_hr_reply: "",
    last_player_text: "",
    last_strategy: null,
    strategy_history: [],
    outcome: null,
  };
}

export function playTurn(
  state: CardGameState,
  strategy: CardStrategyId,
  playerText?: string,
): { state: CardGameState; result: CardTurnResult } {
  if (state.status !== "ongoing") throw new Error("game already ended");
  if (state.available_strategies?.length && !state.available_strategies.includes(strategy)) {
    throw new Error("只能从本回合发放的三张牌中选择");
  }
  const resolvedPlayerText =
    (playerText || "").trim() || state.option_replies?.[strategy]?.trim() || OPTION_FALLBACK[strategy];
  const delta = computeDelta(strategy, state.hr_personality_id, state.round_index, state.strategy_history);
  const newStats = applyDelta(state.stats, delta);
  const hrReply = pickHrReply(strategy);
  const nextRound = state.round_index + 1;
  const history = [...state.strategy_history, strategy];
  let outcome: CardGameOutcome | null = null;
  let reason = "";
  let status = state.status;
  if (newStats.satisfaction <= 0) {
    outcome = "collapsed";
    reason = "满意度归零，HR 撤回 offer";
    status = "collapsed";
  } else if (nextRound > state.max_round) {
    outcome = "forced_deal";
    reason = "第 8 轮结束，强制进入结算";
    status = "forced_settle";
  }
  const nextQuestion = status === "ongoing" ? pickQuestion(nextRound, state.user_name) : "";
  const nextPack = status === "ongoing" ? pickPack() : null;
  const nextOptions =
    status === "ongoing"
      ? Object.fromEntries(nextPack!.available.map((k) => [k, OPTION_FALLBACK[k]]))
      : {};
  const nextState: CardGameState = {
    ...state,
    status,
    round_index: status === "ongoing" ? nextRound : state.round_index,
    stats: newStats,
    current_question: nextQuestion || state.current_question,
    available_strategies: status === "ongoing" ? nextPack!.available : [],
    option_replies: nextOptions,
    recommended_strategy: status === "ongoing" ? nextPack!.recommended : null,
    last_hr_reply: hrReply,
    last_player_text: resolvedPlayerText,
    last_strategy: strategy,
    strategy_history: history,
    outcome,
  };
  return {
    state: nextState,
    result: {
      hr_reply: hrReply,
      player_text_used: resolvedPlayerText,
      next_question: nextQuestion,
      available_strategies: status === "ongoing" ? nextPack!.available : [],
      delta,
      stats: newStats,
      round_index: nextState.round_index,
      is_game_over: status !== "ongoing",
      recommended_strategy: status === "ongoing" ? nextPack!.recommended : null,
      outcome,
      outcome_reason: reason,
      option_replies: nextOptions,
    },
  };
}

export function acceptOffer(state: CardGameState): { state: CardGameState; outcome: CardGameOutcome; reason: string } {
  if (state.status !== "ongoing") throw new Error("game already ended");
  if (state.round_index < 3) throw new Error("第 3 轮后才可接受 offer");
  const met = countConditions(state.stats);
  const sat = state.stats.satisfaction;
  let outcome: CardGameOutcome;
  let reason: string;
  if (sat <= 0) {
    outcome = "collapsed";
    reason = "满意度已崩盘，无法接受 offer";
  } else if (sat <= 1) {
    outcome = "low_deal";
    reason = "勉强接受，HR 脸色很难看";
  } else if (met >= 3) {
    outcome = "high_deal";
    reason = "高位成交，多数条件已达成";
  } else if (met >= 2) {
    outcome = "deal";
    reason = "成功成交，部分条件达成";
  } else {
    outcome = "deal";
    reason = "条件达成偏少，但仍选择接受";
  }
  return { state: { ...state, status: "accepted", outcome }, outcome, reason };
}

function gradeForScore(score: number, outcome: CardGameOutcome): [string, string, string] {
  if (outcome === "collapsed") return ["谈崩了", "💀", "谈判破裂"];
  if (score >= 95) return ["谈判大师", "🥇", "谈判大师"];
  if (score >= 80) return ["老练求职者", "🥈", "老练求职者"];
  if (score >= 60) return ["可造之材", "🥉", "可造之材"];
  if (score >= 40) return ["职场小白", "📋", "职场小白"];
  return ["谈崩了", "💀", "谈崩了"];
}

export function settleGame(state: CardGameState): CardGameSettleResult {
  const stats = state.stats;
  const outcome = state.outcome ?? "forced_deal";
  const salaryScore = clamp(Math.round(((stats.salary_k - SALARY_MIN) / (SALARY_MAX - SALARY_MIN)) * 100), 0, 100);
  const whScore = clamp(Math.round(stats.work_hours * 10), 0, 100);
  const secScore = clamp(Math.round(stats.security * 20), 0, 100);
  const satScore = clamp(Math.round(stats.satisfaction * 10), 0, 100);
  const base = salaryScore * 0.35 + whScore * 0.25 + secScore * 0.25 + satScore * 0.15;
  const strategyCount = new Set(state.strategy_history).size;
  const bonus = strategyCount >= 3 ? 5 : 0;
  const penalty = outcome === "low_deal" ? 10 : 0;
  const final = outcome === "collapsed" ? Math.max(0, Math.round(base * 0.3)) : clamp(Math.round(base + bonus - penalty), 0, 110);
  const [grade, medal, title] = gradeForScore(final, outcome);
  const conditions = countConditions(stats);
  return {
    final_score: final,
    grade,
    medal,
    title,
    outcome,
    review_tip:
      outcome === "collapsed"
        ? "满意度管理失败：进攻牌用太猛，记得穿插温和协商或闲聊救场。"
        : outcome === "high_deal"
          ? `高位成交！达成 ${conditions}/4 项条件，策略多样性 ${strategyCount} 种。`
          : outcome === "low_deal"
            ? "低满成交：HR 勉强点头，下次可多留满意度缓冲。"
            : outcome === "forced_deal"
              ? `拖满 8 轮强制结算，达成 ${conditions}/4 项，可考虑更早接受 offer。`
              : `成交达成 ${conditions}/4 项条件，继续尝试不同策略组合。`,
    conditions_met: conditions,
    breakdown: { salary: salaryScore, work_hours: whScore, security: secScore, satisfaction: satScore },
    stats,
    strategy_count: strategyCount,
    bonus_diversity: bonus,
    penalty_low_satisfaction: penalty,
  };
}
