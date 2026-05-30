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
  hr_personality_id?: string;
  scene_id: string;
  role_id: string;
  status: "ongoing" | "settled" | "closed";
  round_index: number;
  max_round: number;
  hr_patience: number;
  info_exposure: number;
  trap_count: number;
  scene_context?: Record<string, unknown>;
};

export type TurnResult = {
  hr_reply: string;
  delta: { hr_patience: number; info_exposure: number; trap_count: number };
  is_trap_hit: boolean;
  is_game_over: boolean;
  next_round: number;
};

export type FlowDecision = {
  next_phase: "text" | "voice" | "end";
  reason: string;
  should_end: boolean;
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
  textTurn(sessionId: string, payload: { strategy?: string; player_text?: string }): Promise<{ result: TurnResult; session: SessionState; flow?: FlowDecision }>;
  voiceTurn(sessionId: string, payload: { audio_file?: File; audio_path?: string }): Promise<{
    asr: { transcript: string; confidence: number };
    result: TurnResult;
    session: SessionState;
    flow?: FlowDecision;
  }>;
  settle(sessionId: string): Promise<{ result: { final_score: number; final_salary: number; grade: string; review_tip: string } }>;
}
