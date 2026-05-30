import { ref } from "vue";
import {
  cardModeApproachingHint,
  cardModeThresholdHint,
  getCardModeThreshold,
  isCardModeApproaching,
  shouldUnlockCardMode,
} from "../config/cardModeTrigger";
import type { SessionState } from "../runtime/battle_runtime_adapter";

function storageKey(battleSessionId: string) {
  return `cardPhaseUnlocked:${battleSessionId}`;
}

export function useCardModeTrigger(battleSessionId: () => string) {
  const cardPhaseUnlocked = ref(
    typeof sessionStorage !== "undefined" &&
      sessionStorage.getItem(storageKey(battleSessionId())) === "1",
  );

  function markUnlocked() {
    cardPhaseUnlocked.value = true;
    sessionStorage.setItem(storageKey(battleSessionId()), "1");
  }

  function evaluate(session: SessionState | null) {
    const patience = session?.hr_patience ?? 100;
    const personalityId = session?.hr_personality_id;
    const roundIndex = session?.round_index ?? 1;
    const threshold = getCardModeThreshold(personalityId);

    if (cardPhaseUnlocked.value) {
      return {
        shouldTrigger: false,
        alreadyUnlocked: true,
        approaching: false,
        patience,
        threshold,
        hint: "",
      };
    }

    if (!session) {
      return {
        shouldTrigger: false,
        alreadyUnlocked: false,
        approaching: false,
        patience,
        threshold,
        hint: "",
      };
    }

    if (shouldUnlockCardMode(patience, personalityId, roundIndex)) {
      return {
        shouldTrigger: true,
        alreadyUnlocked: false,
        approaching: false,
        patience,
        threshold,
        hint: "",
      };
    }

    const approaching = isCardModeApproaching(patience, personalityId, roundIndex);
    return {
      shouldTrigger: false,
      alreadyUnlocked: false,
      approaching,
      patience,
      threshold,
      hint: approaching
        ? cardModeApproachingHint(patience, threshold)
        : cardModeThresholdHint(threshold),
    };
  }

  return {
    cardPhaseUnlocked,
    markUnlocked,
    evaluate,
    getCardModeThreshold: (personalityId?: string) => getCardModeThreshold(personalityId),
  };
}
