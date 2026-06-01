export type HrPersonalityMeta = {
  personality_id: string;
  name: string;
  tagline: string;
  emoji: string;
  patience_bias?: number;
};

export type SessionState = {
  session_id: string;
  user_id: string;
  user_name: string;
  interaction_mode?: "text" | "voice";
  hr_personality_id?: string;
  scene_id: string;
  role_id: string;
  status: "ongoing" | "settled" | "closed";
  round_index: number;
  max_round: number;
  hr_patience: number;
  info_exposure: number;
  trap_count: number;
  current_salary_offer?: number;
  active_game_point_id?: string | null;
  resolved_game_points?: string[];
  scene_context?: Record<string, unknown>;
};

export type GamePointHint = {
  point_id: string;
  trap_type: string;
  explanation: string;
  status: "active" | "resolved";
};

export type TurnResult = {
  hr_reply: string;
  delta: { hr_patience: number; info_exposure: number; trap_count: number };
  is_trap_hit: boolean;
  is_game_over: boolean;
  next_round: number;
  game_point_hint?: GamePointHint | null;
  /** 横屏 HR 气泡出场：fade | slam | slide */
  hr_bubble_entrance?: string;
  /** 横屏玩家气泡出场：fade | slam | slide */
  player_bubble_entrance?: string;
};

export type FlowDecision = {
  next_phase: "text" | "end";
  reason: string;
  should_end: boolean;
};

export type ScoreBreakdown = {
  dq: number;
  td: number;
  wh: number;
  si: number;
};

export type OfferPackage = {
  equity_ratio: number;
  social_security_base: string;
  housing_fund_ratio: string;
  overtime_policy: string;
  working_hours_agreement: string;
  base_salary?: number | null;
  performance_salary?: number | null;
  annual_bonus_months?: number | null;
  performance_protection_months?: number | null;
  quarterly_bonus_clause?: string | null;
  signing_bonus?: number | null;
  non_compete_months?: number | null;
  housing_subsidy_months?: number | null;
  package_note?: string | null;
};

export type SettleStats = {
  traps_identified: number;
  traps_total: number;
  trap_labels: string[];
  law_citation_count: number;
  strategy_count: number;
  final_patience: number;
};

export type SettleResultView = {
  final_score: number;
  final_salary: number;
  grade: string;
  review_tip: string;
  verdict?: "hired" | "rejected";
  outcome_reason?: string;
  title?: string;
  medal?: string;
  scene_name?: string;
  summary?: string;
  risk_notes?: string[];
  missed_clauses?: string[];
  breakdown?: ScoreBreakdown;
  offer?: OfferPackage;
  stats?: SettleStats;
};

export type TextTurnResponse = {
  result: TurnResult;
  session: SessionState;
  flow?: FlowDecision;
};

export type TextTurnStreamHandlers = {
  onToken: (text: string) => void;
};

export interface BattleRuntimeAdapter {
  listHrPersonalities?(): Promise<HrPersonalityMeta[]>;
  createSession(
    userId: string,
    sceneId?: string,
    roleId?: string,
    userName?: string,
    hrPersonalityId?: string
  ): Promise<{
    session: SessionState;
    hr_opening: string;
    scene_meta?: Record<string, unknown>;
    hr_personality_meta?: HrPersonalityMeta;
  }>;
  textTurn(
    sessionId: string,
    payload: { strategy?: string; player_text?: string },
  ): Promise<TextTurnResponse>;
  textTurnStream(
    sessionId: string,
    payload: { strategy?: string; player_text?: string },
    handlers: TextTurnStreamHandlers,
  ): Promise<TextTurnResponse>;
  settle(sessionId: string): Promise<{
    result: SettleResultView;
    conversation_history?: Array<{ role?: string; content?: string; round_index?: number }>;
  }>;
}
