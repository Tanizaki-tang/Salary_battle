export type NdjsonStreamEvent =
  | { type: "token"; text: string }
  | { type: "done"; data: unknown }
  | { type: "error"; message: string };

export async function readNdjsonStream(
  response: Response,
  onEvent: (event: NdjsonStreamEvent) => void,
): Promise<void> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("响应体为空");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let lineBreak = buffer.indexOf("\n");
    while (lineBreak >= 0) {
      const line = buffer.slice(0, lineBreak).trim();
      buffer = buffer.slice(lineBreak + 1);
      if (line) {
        onEvent(JSON.parse(line) as NdjsonStreamEvent);
      }
      lineBreak = buffer.indexOf("\n");
    }
  }

  const tail = buffer.trim();
  if (tail) {
    onEvent(JSON.parse(tail) as NdjsonStreamEvent);
  }
}
