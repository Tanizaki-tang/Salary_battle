export type SessionState = {
  session_id: string;
  user_id: string;
  status: "ongoing" | "settled" | "closed";
  round_index: number;
  max_round: number;
  hr_patience: number;
  info_exposure: number;
  trap_count: number;
};

export type TurnResult = {
  hr_reply: string;
  delta: { hr_patience: number; info_exposure: number; trap_count: number };
  is_trap_hit: boolean;
  is_game_over: boolean;
  next_round: number;
};

export interface BattleRuntimeAdapter {
  createSession(userId: string): Promise<{ session: SessionState; hr_opening: string }>;
  textTurn(sessionId: string, payload: { strategy?: string; player_text?: string }): Promise<{ result: TurnResult; session: SessionState }>;
  voiceTurn(sessionId: string, payload: { audio_file?: File; audio_path?: string }): Promise<{
    asr: { transcript: string; confidence: number };
    result: TurnResult;
    session: SessionState;
  }>;
  settle(sessionId: string): Promise<{ result: { final_score: number; final_salary: number; grade: string; review_tip: string } }>;
}
