export type CardStrategyId =
  | "strong_push"
  | "probe"
  | "concede"
  | "counter_pressure"
  | "expose_rhetoric"
  | "off_topic";

export type CardGameStatus = "ongoing" | "collapsed" | "accepted" | "forced_settle" | "settled";
export type CardGameOutcome = "collapsed" | "high_deal" | "deal" | "low_deal" | "forced_deal";

export type CardGameStats = {
  satisfaction: number;
  salary_k: number;
  work_hours: number;
  security: number;
};

export type CardGameState = {
  session_id: string;
  user_id: string;
  user_name: string;
  hr_personality_id: string;
  status: CardGameStatus;
  round_index: number;
  max_round: number;
  stats: CardGameStats;
  current_question: string;
  available_strategies?: CardStrategyId[];
  option_replies?: Partial<Record<CardStrategyId, string>>;
  recommended_strategy?: CardStrategyId | null;
  last_hr_reply: string;
  last_player_text?: string;
  last_strategy: CardStrategyId | null;
  strategy_history: CardStrategyId[];
  outcome: CardGameOutcome | null;
};

export type CardDeltaView = {
  satisfaction: number;
  salary_k: number;
  work_hours: number;
  security: number;
};

export type CardTurnResult = {
  hr_reply: string;
  player_text_used?: string;
  next_question: string;
  available_strategies?: CardStrategyId[];
  delta: CardDeltaView;
  stats: CardGameStats;
  round_index: number;
  is_game_over: boolean;
  recommended_strategy?: CardStrategyId | null;
  outcome: CardGameOutcome | null;
  outcome_reason: string;
  option_replies?: Partial<Record<CardStrategyId, string>>;
};

export type CardGameScoreBreakdown = {
  salary: number;
  work_hours: number;
  security: number;
  satisfaction: number;
};

export type CardGameSettleResult = {
  final_score: number;
  grade: string;
  medal: string;
  title: string;
  outcome: CardGameOutcome;
  review_tip: string;
  conditions_met: number;
  breakdown: CardGameScoreBreakdown;
  stats: CardGameStats;
  strategy_count: number;
  bonus_diversity: number;
  penalty_low_satisfaction: number;
};

export type HrPersonalityMeta = {
  personality_id: string;
  name: string;
  tagline: string;
  emoji: string;
};

export const DEAL_THRESHOLDS = {
  salary_k: 18,
  work_hours: 7,
  security: 3,
  satisfaction: 0,
} as const;

export const STAT_LIMITS = {
  satisfaction: { min: 0, max: 10 },
  salary_k: { min: 8, max: 22 },
  work_hours: { min: 0, max: 10 },
  security: { min: 0, max: 5 },
} as const;
