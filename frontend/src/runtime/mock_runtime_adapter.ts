import dialogTree from "../mock/dialog_tree.json";
import resultRules from "../mock/result_rules.json";
import scenario from "../mock/scenario.json";
import type { BattleRuntimeAdapter, SessionState } from "./battle_runtime_adapter";

const sessions = new Map<string, SessionState>();
const roleToScene: Record<string, string> = {
  role_backend: "scene_001",
  role_product: "scene_002",
  role_sales: "scene_003",
};
const sceneOpening: Record<string, string> = {
  scene_001: scenario.hr_opening,
  scene_002: "我们先给到 13K*14，绩效另算，你怎么看？",
  scene_003: "底薪 8K，提成另计，欢迎你提问。",
};
const sceneInitial: Record<string, { max_round: number; hr_patience: number; info_exposure: number; trap_count: number }> = {
  scene_001: {
    max_round: scenario.max_round,
    hr_patience: scenario.initial_state.hr_patience,
    info_exposure: scenario.initial_state.info_exposure,
    trap_count: scenario.initial_state.trap_count,
  },
  scene_002: { max_round: 5, hr_patience: 75, info_exposure: 25, trap_count: 0 },
  scene_003: { max_round: 5, hr_patience: 85, info_exposure: 15, trap_count: 0 },
};

export const mockRuntimeAdapter: BattleRuntimeAdapter = {
  async createSession(userId, sceneId, roleId, userName) {
    const resolvedScene = sceneId || roleToScene[roleId || "role_backend"] || "scene_001";
    const initial = sceneInitial[resolvedScene] || sceneInitial.scene_001;
    const resolvedName = (userName || "").trim() || "候选人";
    const session: SessionState = {
      session_id: `sess_mock_${Date.now()}`,
      user_id: userId,
      user_name: resolvedName,
      scene_id: resolvedScene,
      role_id: roleId || "role_backend",
      status: "ongoing",
      round_index: 1,
      max_round: initial.max_round,
      hr_patience: initial.hr_patience,
      info_exposure: initial.info_exposure,
      trap_count: initial.trap_count,
    };
    sessions.set(session.session_id, session);
    return {
      session,
      hr_opening: sceneOpening[resolvedScene] || sceneOpening.scene_001,
      scene_meta: { scene_id: resolvedScene, role_hint: session.role_id },
    };
  },
  async textTurn(sessionId, payload) {
    const session = sessions.get(sessionId)!;
    const key = payload.strategy || "probe";
    const node = (dialogTree as any)[key];
    session.round_index = Math.min(session.round_index + 1, session.max_round);
    session.hr_patience += node.delta.hr_patience;
    session.info_exposure += node.delta.info_exposure;
    session.trap_count += node.delta.trap_count;
    return {
      result: {
        hr_reply: `${session.user_name}，${node.hr_reply}`,
        delta: node.delta,
        is_trap_hit: node.delta.trap_count > 0,
        is_game_over: session.round_index >= session.max_round,
        next_round: session.round_index,
      },
      session,
    };
  },
  async voiceTurn(sessionId) {
    const base = await this.textTurn(sessionId, { strategy: "probe" });
    return {
      asr: { transcript: "我想确认薪资区间", confidence: 0.88 },
      flow: { next_phase: "text", reason: "mock_voice_done", should_end: false },
      ...base,
    };
  },
  async settle(sessionId) {
    const session = sessions.get(sessionId)!;
    const final_score = Math.max(0, Math.min(100, Math.round(session.hr_patience * 0.5 + (100 - session.info_exposure) * 0.3 + session.trap_count * 10)));
    return {
      result: {
        final_score,
        final_salary: resultRules.base_salary + final_score * 20,
        grade: final_score >= 80 ? "A" : final_score >= 65 ? "B" : "C",
        review_tip: resultRules.review_tip,
      },
    };
  },
};
