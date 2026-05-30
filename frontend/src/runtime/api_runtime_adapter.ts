import axios from "axios";
import type { BattleRuntimeAdapter } from "./battle_runtime_adapter";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const client = axios.create({ baseURL });

export const apiRuntimeAdapter: BattleRuntimeAdapter = {
  async createSession(userId, sceneId, roleId, userName) {
    const res = await client.post("/api/v1/sessions", {
      user_id: userId,
      user_name: userName,
      scene_id: sceneId,
      role_id: roleId,
    });
    return res.data.data;
  },
  async textTurn(sessionId, payload) {
    const res = await client.post(`/api/v1/sessions/${sessionId}/text-turn`, payload);
    return res.data.data;
  },
  async voiceTurn(sessionId, payload) {
    const form = new FormData();
    if (payload.audio_file) form.append("audio_file", payload.audio_file);
    else form.append("audio_file", new File([new Blob(["RIFF....WAVE"])], "voice.wav", { type: "audio/wav" }));
    const res = await client.post(`/api/v1/sessions/${sessionId}/voice-turn`, form);
    return res.data.data;
  },
  async settle(sessionId) {
    const res = await client.post(`/api/v1/sessions/${sessionId}/settle`, {});
    return res.data.data;
  },
};
