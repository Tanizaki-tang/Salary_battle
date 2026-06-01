import type { FlowDecision, SessionState, TurnResult } from "./battle_runtime_adapter";
import { buildRuntimeAuthHeaders } from "../utils/app_settings";
import { resolveApiBaseUrl } from "../utils/api_base_url";

export type TextTurnPayload = {
  strategy?: string;
  player_text?: string;
};

export type TextTurnStreamDone = {
  result: TurnResult;
  session: SessionState;
  flow?: FlowDecision;
};

export type TextTurnStreamHandlers = {
  onToken: (text: string) => void;
};

export async function streamTextTurn(
  sessionId: string,
  payload: TextTurnPayload,
  handlers: TextTurnStreamHandlers,
): Promise<TextTurnStreamDone> {
  const baseURL = resolveApiBaseUrl();
  const res = await fetch(`${baseURL}/api/v1/sessions/${sessionId}/text-turn/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildRuntimeAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `stream request failed (${res.status})`);
  }
  if (!res.body) {
    throw new Error("stream body missing");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload: TextTurnStreamDone | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .map((row) => row.trim())
        .find((row) => row.startsWith("data:"));
      if (!line) continue;
      const raw = line.slice(5).trim();
      if (!raw) continue;
      const event = JSON.parse(raw) as {
        event: string;
        text?: string;
        message?: string;
        result?: TurnResult;
        session?: SessionState;
        flow?: FlowDecision;
      };
      if (event.event === "token" && event.text) {
        handlers.onToken(event.text);
      } else if (event.event === "done" && event.result && event.session) {
        donePayload = {
          result: event.result,
          session: event.session,
          flow: event.flow,
        };
      } else if (event.event === "error") {
        throw new Error(event.message || "stream error");
      }
    }
  }

  if (!donePayload) {
    throw new Error("stream ended without done event");
  }
  return donePayload;
}

async function sleep(ms: number) {
  await new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function mockStreamText(
  fullText: string,
  handlers: TextTurnStreamHandlers,
  chunkSize = 2,
  delayMs = 28,
) {
  for (let i = 0; i < fullText.length; i += chunkSize) {
    handlers.onToken(fullText.slice(i, i + chunkSize));
    await sleep(delayMs);
  }
}
