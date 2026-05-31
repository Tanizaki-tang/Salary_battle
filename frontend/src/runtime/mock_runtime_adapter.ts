import dialogTree from "../mock/dialog_tree.json";
import resultRules from "../mock/result_rules.json";
import scenario from "../mock/scenario.json";
import type { BattleRuntimeAdapter, HrPersonalityMeta, SessionState, TextTurnStreamHandlers } from "./battle_runtime_adapter";
import { mockStreamText } from "./text_turn_stream";

const MOCK_PERSONALITIES: HrPersonalityMeta[] = [
  { personality_id: "hr_newbie", name: "菜鸟新人", tagline: "紧张没底气，容易说漏信息", emoji: "🐣" },
  { personality_id: "hr_robot", name: "冷漠流程型", tagline: "按系统流程办事，几乎无情绪波动", emoji: "🤖" },
  { personality_id: "hr_aggressive", name: "强势压价型", tagline: "开门见山压价，耐心极低", emoji: "💪" },
  { personality_id: "hr_honest", name: "老实人型", tagline: "真诚坦率，容易被说服", emoji: "😇" },
  { personality_id: "hr_smiling_tiger", name: "笑面虎型", tagline: "表面热情，话术圆滑", emoji: "😊" },
];

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
  async listHrPersonalities() {
    return MOCK_PERSONALITIES;
  },
  async createSession(userId, sceneId, roleId, userName, hrPersonalityId) {
    const resolvedScene = sceneId || roleToScene[roleId || "role_backend"] || "scene_001";
    const initial = sceneInitial[resolvedScene] || sceneInitial.scene_001;
    const resolvedName = (userName || "").trim() || "候选人";
    const personalityId =
      hrPersonalityId ||
      MOCK_PERSONALITIES[Math.floor(Math.random() * MOCK_PERSONALITIES.length)]!.personality_id;
    const personalityMeta = MOCK_PERSONALITIES.find((p) => p.personality_id === personalityId) || MOCK_PERSONALITIES[4];
    const session: SessionState = {
      session_id: `sess_mock_${Date.now()}`,
      user_id: userId,
      user_name: resolvedName,
      hr_personality_id: personalityId,
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
      hr_personality_meta: personalityMeta,
    };
  },
  async textTurn(sessionId, payload) {
    return this.textTurnStream(sessionId, payload, { onToken: () => {} });
  },
  async textTurnStream(sessionId, payload, handlers: TextTurnStreamHandlers) {
    const session = sessions.get(sessionId)!;
    const key = payload.strategy || "probe";
    const node = (dialogTree as any)[key];
    session.round_index = Math.min(session.round_index + 1, session.max_round);
    session.hr_patience += node.delta.hr_patience;
    session.info_exposure += node.delta.info_exposure;
    session.trap_count += node.delta.trap_count;
    const bubbleByStrategy: Record<string, { hr: string; player: string }> = {
      strong_push: { hr: "slam", player: "slide" },
      probe: { hr: "fade", player: "slide" },
      concede: { hr: "fade", player: "fade" },
      counter_pressure: { hr: "slam", player: "slide" },
    };
    const bubbles = bubbleByStrategy[key] || { hr: "fade", player: "slide" };
    const hrReply = `${session.user_name}，${node.hr_reply}`;
    await mockStreamText(hrReply, handlers);
    return {
      result: {
        hr_reply: hrReply,
        delta: node.delta,
        is_trap_hit: node.delta.trap_count > 0,
        is_game_over: session.round_index >= session.max_round,
        next_round: session.round_index,
        hr_bubble_entrance: bubbles.hr,
        player_bubble_entrance: bubbles.player,
      },
      session,
    };
  },
  async settle(sessionId) {
    const session = sessions.get(sessionId)!;
    const final_score = Math.max(0, Math.min(100, Math.round(session.hr_patience * 0.5 + (100 - session.info_exposure) * 0.3 + session.trap_count * 10)));
    const dq = Math.min(100, Math.round((final_score * 0.9)));
    const td = Math.min(100, session.trap_count * 25 + 10);
    const wh = Math.max(0, 100 - session.info_exposure);
    const si = Math.min(100, 50 + session.trap_count * 12);
    const title = final_score >= 85 ? "老练求职者" : final_score >= 70 ? "稳健求职者" : "入门求职者";
    const medal = final_score >= 95 ? "🥇" : final_score >= 85 ? "🥈" : final_score >= 70 ? "🥉" : "📋";
    const salaryK = Math.round((resultRules.base_salary + final_score * 20) / 1000);
    return {
      result: {
        final_score,
        final_salary: resultRules.base_salary + final_score * 20,
        grade: final_score >= 80 ? "A" : final_score >= 65 ? "B" : "C",
        review_tip: resultRules.review_tip,
        title,
        medal,
        scene_name: "初创公司后端岗",
        summary: `你接受了 ${salaryK}K 的 offer。在初创公司后端岗，这是一个相当不错的结果。`,
        breakdown: { dq, td, wh, si },
        offer: {
          equity_ratio: 0,
          social_security_base: session.trap_count >= 2 ? "全额工资基数" : "按标准缴纳",
          housing_fund_ratio: session.trap_count >= 2 ? "7%" : "未约定",
          overtime_policy: session.trap_count >= 1 ? "单独计算" : "含在总包",
          working_hours_agreement: wh >= 80 ? "明确约定" : "未约定",
        },
        stats: {
          traps_identified: session.trap_count,
          traps_total: 5,
          trap_labels: ["期权画饼", "加班费打包"].slice(0, session.trap_count),
          law_citation_count: 0,
          strategy_count: 2,
          final_patience: session.hr_patience,
        },
      },
    };
  },
};
