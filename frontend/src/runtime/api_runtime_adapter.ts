import type { BattleRuntimeAdapter, TextTurnStreamHandlers } from "./battle_runtime_adapter";
import { streamTextTurn } from "./text_turn_stream";
import { buildRuntimeAuthHeaders } from "../utils/app_settings";
import { resolveApiBaseUrl } from "../utils/api_base_url";

const baseURL = resolveApiBaseUrl();

export const apiRuntimeAdapter: BattleRuntimeAdapter = {
  async listHrPersonalities() {
    const res = await fetch(`${baseURL}/api/v1/hr-personalities`);
    const json = await res.json();
    return json.data.personalities;
  },
  async createSession(userId, sceneId, roleId, userName, hrPersonalityId) {
    const body: Record<string, string> = {
      user_id: userId,
      user_name: userName || "",
      scene_id: sceneId || "",
      role_id: roleId || "",
    };
    if (hrPersonalityId) {
      body.hr_personality_id = hrPersonalityId;
    }
    const res = await fetch(`${baseURL}/api/v1/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildRuntimeAuthHeaders(),
      },
      body: JSON.stringify(body),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(json));
    return json.data;
  },
  async textTurnStream(sessionId, payload, handlers: TextTurnStreamHandlers) {
    return streamTextTurn(sessionId, payload, handlers);
  },
  async textTurn(sessionId, payload) {
    return streamTextTurn(sessionId, payload, { onToken: () => {} });
  },
  async settle(sessionId) {
    const res = await fetch(`${baseURL}/api/v1/sessions/${sessionId}/settle`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildRuntimeAuthHeaders(),
      },
      body: JSON.stringify({}),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(json));
    return json.data;
  },
};
