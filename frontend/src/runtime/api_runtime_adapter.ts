import type { BattleRuntimeAdapter, TextTurnOptions } from "./battle_runtime_adapter";
import { readNdjsonStream } from "./stream_ndjson";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const apiRuntimeAdapter: BattleRuntimeAdapter = {
  async listHrPersonalities() {
    const res = await fetch(`${baseURL}/api/v1/hr-personalities`);
    if (!res.ok) throw new Error(await res.text());
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    return json.data;
  },
  async textTurn(sessionId, payload, options?: TextTurnOptions) {
    const res = await fetch(`${baseURL}/api/v1/sessions/${sessionId}/text-turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let donePayload: { result: unknown; session: unknown; flow?: unknown } | null = null;
    let streamError = "";

    await readNdjsonStream(res, (event) => {
      if (event.type === "token") {
        options?.onToken?.(event.text);
        return;
      }
      if (event.type === "done") {
        donePayload = event.data as { result: unknown; session: unknown; flow?: unknown };
        return;
      }
      if (event.type === "error") {
        streamError = event.message;
      }
    });

    if (streamError) throw new Error(streamError);
    if (!donePayload) throw new Error("流式响应未完成");
    return donePayload as Awaited<ReturnType<BattleRuntimeAdapter["textTurn"]>>;
  },
  async settle(sessionId) {
    const res = await fetch(`${baseURL}/api/v1/sessions/${sessionId}/settle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    return json.data;
  },
};
