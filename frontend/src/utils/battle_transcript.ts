export type TranscriptMessage = {
  role: "hr" | "player" | "system";
  content: string;
  round_index?: number;
};

function transcriptKey(sessionId: string) {
  return `battleTranscript:${sessionId}`;
}

export function saveBattleTranscript(sessionId: string, messages: TranscriptMessage[]) {
  if (!sessionId || !messages.length) return;
  try {
    sessionStorage.setItem(transcriptKey(sessionId), JSON.stringify(messages));
  } catch {
    /* ignore quota */
  }
}

export function loadBattleTranscript(sessionId: string): TranscriptMessage[] {
  try {
    const raw = sessionStorage.getItem(transcriptKey(sessionId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as TranscriptMessage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function clearBattleTranscript(sessionId: string) {
  sessionStorage.removeItem(transcriptKey(sessionId));
}

export function normalizeConversationHistory(
  rows: Array<{ role?: string; content?: string; round_index?: number }> | undefined,
): TranscriptMessage[] {
  if (!rows?.length) return [];
  return rows
    .filter((row) => row.content?.trim())
    .map((row) => ({
      role: row.role === "hr" || row.role === "player" || row.role === "system" ? row.role : "system",
      content: String(row.content).trim(),
      round_index: typeof row.round_index === "number" ? row.round_index : undefined,
    }));
}
