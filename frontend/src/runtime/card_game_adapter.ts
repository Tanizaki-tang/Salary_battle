import { apiClient } from "../api/client";
import {
  acceptOffer,
  createInitialState,
  playTurn,
  settleGame,
} from "../card-game/engine";
import type {
  CardGameSettleResult,
  CardGameState,
  CardStrategyId,
  CardTurnResult,
  HrPersonalityMeta,
} from "../card-game/types";

export interface CardGameAdapter {
  createSession(userId: string, userName: string, hrPersonalityId?: string): Promise<{
    session: CardGameState;
    hr_personality_meta: HrPersonalityMeta;
  }>;
  getSession(sessionId: string): Promise<CardGameState>;
  playTurn(sessionId: string, strategy: CardStrategyId, playerText?: string): Promise<{ session: CardGameState; result: CardTurnResult }>;
  acceptOffer(sessionId: string): Promise<{ session: CardGameState; outcome: string; reason: string }>;
  settle(sessionId: string): Promise<{ session: CardGameState; result: CardGameSettleResult }>;
}

const MOCK_PERSONALITIES: HrPersonalityMeta[] = [
  { personality_id: "hr_newbie", name: "菜鸟新人", tagline: "紧张没底气", emoji: "🐣" },
  { personality_id: "hr_robot", name: "冷漠流程型", tagline: "按流程办事", emoji: "🤖" },
  { personality_id: "hr_aggressive", name: "强势压价型", tagline: "耐心极低", emoji: "💪" },
  { personality_id: "hr_honest", name: "老实人型", tagline: "容易被说服", emoji: "😇" },
  { personality_id: "hr_smiling_tiger", name: "笑面虎型", tagline: "话术圆滑", emoji: "😊" },
];

const mockSessions = new Map<string, CardGameState>();

export const cardGameMockAdapter: CardGameAdapter = {
  async createSession(userId, userName, hrPersonalityId) {
    const pid =
      hrPersonalityId && hrPersonalityId !== "random"
        ? hrPersonalityId
        : MOCK_PERSONALITIES[Math.floor(Math.random() * MOCK_PERSONALITIES.length)]!.personality_id;
    const meta = MOCK_PERSONALITIES.find((p) => p.personality_id === pid) ?? MOCK_PERSONALITIES[4]!;
    const sessionId = `card_mock_${Date.now()}`;
    const session = createInitialState(sessionId, userId, userName.trim() || "候选人", pid);
    mockSessions.set(sessionId, session);
    return { session, hr_personality_meta: meta };
  },
  async getSession(sessionId) {
    const s = mockSessions.get(sessionId);
    if (!s) throw new Error("session not found");
    return s;
  },
  async playTurn(sessionId, strategy, playerText) {
    const state = mockSessions.get(sessionId);
    if (!state) throw new Error("session not found");
    const { state: next, result } = playTurn(state, strategy, playerText);
    mockSessions.set(sessionId, next);
    return { session: next, result };
  },
  async acceptOffer(sessionId) {
    const state = mockSessions.get(sessionId);
    if (!state) throw new Error("session not found");
    const { state: next, outcome, reason } = acceptOffer(state);
    mockSessions.set(sessionId, next);
    return { session: next, outcome, reason };
  },
  async settle(sessionId) {
    let state = mockSessions.get(sessionId);
    if (!state) throw new Error("session not found");
    if (state.status === "ongoing") {
      state = { ...state, status: "forced_settle", outcome: "forced_deal" };
    }
    const result = settleGame(state);
    mockSessions.set(sessionId, { ...state, status: "settled" });
    return { session: { ...state, status: "settled" }, result };
  },
};

export const cardGameApiAdapter: CardGameAdapter = {
  async createSession(userId, userName, hrPersonalityId) {
    const res = await apiClient.post("/api/v1/card-game/sessions", {
      user_id: userId,
      user_name: userName,
      hr_personality_id: hrPersonalityId,
    });
    return res.data.data;
  },
  async getSession(sessionId) {
    const res = await apiClient.get(`/api/v1/card-game/sessions/${sessionId}`);
    return res.data.data.session;
  },
  async playTurn(sessionId, strategy, playerText) {
    const res = await apiClient.post(`/api/v1/card-game/sessions/${sessionId}/turn`, {
      strategy,
      player_text: playerText,
    });
    return res.data.data;
  },
  async acceptOffer(sessionId) {
    const res = await apiClient.post(`/api/v1/card-game/sessions/${sessionId}/accept`);
    return res.data.data;
  },
  async settle(sessionId) {
    const res = await apiClient.post(`/api/v1/card-game/sessions/${sessionId}/settle`);
    return res.data.data;
  },
};

const mode = (import.meta.env.VITE_RUNTIME_MODE || "api").toLowerCase();
export const cardGameAdapter: CardGameAdapter = mode === "mock" ? cardGameMockAdapter : cardGameApiAdapter;

export { MOCK_PERSONALITIES };
