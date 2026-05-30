export type WsServerEvent =
  | "server.conn_ready"
  | "server.asr_partial"
  | "server.asr_final"
  | "server.hr_delta"
  | "server.hr_audio_chunk"
  | "server.turn_done"
  | "server.error";

export type WsMessage<T = Record<string, unknown>> = {
  type: WsServerEvent | string;
  payload: T;
  ts?: number;
  seq?: number;
};

type EventHandler = (message: WsMessage) => void;

function resolveWsBaseUrl(): string {
  const direct = (import.meta.env.VITE_WS_BASE_URL || "").trim();
  if (direct) return direct.replace(/\/$/, "");
  const apiBase = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").trim();
  if (apiBase.startsWith("https://")) return apiBase.replace("https://", "wss://").replace(/\/$/, "");
  if (apiBase.startsWith("http://")) return apiBase.replace("http://", "ws://").replace(/\/$/, "");
  return "ws://127.0.0.1:8000";
}

function uint8ToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  return uint8ToBase64(new Uint8Array(buffer));
}

export class RealtimeWsClient {
  private ws: WebSocket | null = null;
  private readonly handlers = new Set<EventHandler>();
  private readonly baseUrl = resolveWsBaseUrl();

  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${this.baseUrl}/api/v1/ws/sessions/${sessionId}`);
      ws.onopen = () => {
        this.ws = ws;
        this.send("client.session_init", { session_id: sessionId });
        resolve();
      };
      ws.onerror = () => reject(new Error("WebSocket connect failed"));
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(String(event.data)) as WsMessage;
          this.handlers.forEach((h) => h(data));
        } catch {
          // ignore malformed events
        }
      };
      ws.onclose = () => {
        this.ws = null;
      };
    });
  }

  onEvent(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  close(): void {
    if (this.ws) {
      this.send("client.hangup", {});
      this.ws.close();
      this.ws = null;
    }
  }

  sendText(text: string): void {
    this.send("client.user_text", { text });
  }

  async sendVoiceChunk(blob: Blob, mimeType: string): Promise<void> {
    const chunkB64 = await blobToBase64(blob);
    this.send("client.voice_chunk", { chunk_b64: chunkB64, mime_type: mimeType });
  }

  commitUtterance(mimeType: string): void {
    this.send("client.commit_utterance", { mime_type: mimeType });
  }

  private send(type: string, payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ type, payload, ts: Date.now() }));
  }
}

