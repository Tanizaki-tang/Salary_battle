import {
  CARD_MODE_PRELUDE_LINE_MS,
  CARD_MODE_PRELUDE_MESSAGES,
  CARD_MODE_PRELUDE_PAUSE_MS,
} from "../config/cardModeTrigger";

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export async function playCardModePrelude(
  pushSystemMessage: (text: string) => void,
  onLine?: () => void,
) {
  for (const line of CARD_MODE_PRELUDE_MESSAGES) {
    pushSystemMessage(line);
    onLine?.();
    await sleep(CARD_MODE_PRELUDE_LINE_MS);
  }
  await sleep(CARD_MODE_PRELUDE_PAUSE_MS);
}
