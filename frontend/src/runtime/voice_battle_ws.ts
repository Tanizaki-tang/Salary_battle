import type { FlowDecision, SessionState, TurnResult } from "./battle_runtime_adapter";
import { resolveApiBaseUrl } from "../utils/api_base_url";

export type VoiceBattleEvent =
  | { type: "ready"; asr?: { sample_rate?: number } }
  | { type: "asr.partial"; text: string }
  | { type: "asr.final"; text: string }
  | { type: "hr.text.start" }
  | { type: "hr.text.delta"; text: string }
  | { type: "hr.text.done"; text: string }
  | { type: "hr.audio.delta"; audio_b64: string; format: string; sample_rate: number }
  | { type: "turn.done"; result: TurnResult; session: SessionState; flow?: FlowDecision; hr_text?: string }
  | { type: "error"; message: string };

export type VoiceBattleHandlers = {
  onEvent: (evt: VoiceBattleEvent) => void;
};

export function connectVoiceBattle(sessionId: string, handlers: VoiceBattleHandlers) {
  const baseURL = resolveApiBaseUrl();
  const wsURL = baseURL
    ? toWsUrl(`${baseURL}/api/v1/voice-battle/ws/${sessionId}`)
    : toWsUrl(`${window.location.origin}/api/v1/voice-battle/ws/${sessionId}`);
  const ws = new WebSocket(wsURL);
  ws.binaryType = "arraybuffer";

  ws.onmessage = (ev) => {
    if (typeof ev.data === "string") {
      try {
        handlers.onEvent(JSON.parse(ev.data) as VoiceBattleEvent);
      } catch {
        handlers.onEvent({ type: "error", message: "invalid ws payload" });
      }
    }
  };

  const sendAudio = (pcm16: Int16Array) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    ws.send(pcm16.buffer.slice(0));
  };

  const close = () => {
    try {
      ws.close();
    } catch {
      /* ignore */
    }
  };

  return { ws, sendAudio, close };
}

function toWsUrl(httpUrl: string) {
  if (httpUrl.startsWith("https://")) return "wss://" + httpUrl.slice("https://".length);
  if (httpUrl.startsWith("http://")) return "ws://" + httpUrl.slice("http://".length);
  return httpUrl;
}
