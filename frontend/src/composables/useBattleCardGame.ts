import { computed, ref } from "vue";
import { CARD_GAME_CARDS } from "../card-game/cards";
import { countConditions } from "../card-game/engine";
import type { CardDeltaView, CardGameState, CardStrategyId, HrPersonalityMeta } from "../card-game/types";
import { cardGameAdapter } from "../runtime/card_game_adapter";
import type { SessionState } from "../runtime/battle_runtime_adapter";

function storageKey(battleSessionId: string) {
  return `cardGameForBattle:${battleSessionId}`;
}

export function useBattleCardGame(
  battleSessionId: () => string,
  getTextSession: () => SessionState | null,
  countdown: { reset: (seconds?: number) => void; pause: () => void },
  goResult: (cardSessionId: string) => void,
) {
  const cardSession = ref<CardGameState | null>(null);
  const cardSessionId = ref("");
  const hrMeta = ref<HrPersonalityMeta | null>(null);
  const cardBusy = ref(false);
  const cardDialogLoading = ref(false);
  const cardWaiting = ref(false);
  const cardError = ref("");
  const selectedCard = ref<CardStrategyId | null>(null);
  const flashDelta = ref<CardDeltaView | null>(null);
  const showDelta = ref(false);
  const lastDeltaHint = ref("");
  const displayHrText = ref("");
  const lastPlayerCardText = ref("");

  const canAccept = computed(
    () => (cardSession.value?.round_index ?? 0) >= 3 && cardSession.value?.status === "ongoing",
  );

  const acceptHint = computed(() => {
    if (!cardSession.value) return "";
    const met = countConditions(cardSession.value.stats);
    if ((cardSession.value.round_index ?? 0) < 3) return "第 3 轮后可接受 offer";
    if (met < 2) return `当前仅达成 ${met}/4 条件，接受可能不是最优`;
    return `已达成 ${met}/4 条件`;
  });

  const cardHrMeter = computed(() => Math.round((cardSession.value?.stats.satisfaction ?? 6) * 10));
  const cardPlayerMeter = computed(() => {
    const salary = cardSession.value?.stats.salary_k ?? 15;
    return Math.round(((salary - 8) / 14) * 100);
  });

  function persistCard(state: CardGameState) {
    cardSession.value = state;
    sessionStorage.setItem(
      storageKey(battleSessionId()),
      JSON.stringify({ cardSessionId: cardSessionId.value, session: state }),
    );
    sessionStorage.setItem("cardGameSession", JSON.stringify(state));
  }

  function loadCached() {
    const raw = sessionStorage.getItem(storageKey(battleSessionId()));
    if (!raw) return false;
    const parsed = JSON.parse(raw) as { cardSessionId: string; session: CardGameState };
    cardSessionId.value = parsed.cardSessionId;
    cardSession.value = parsed.session;
    displayHrText.value = parsed.session.current_question;
    const metaRaw = sessionStorage.getItem("hrPersonalityMeta");
    if (metaRaw) hrMeta.value = JSON.parse(metaRaw) as HrPersonalityMeta;
    return true;
  }

  async function ensureCardSession() {
    if (cardSession.value && cardSessionId.value) return;
    if (loadCached()) return;

    cardDialogLoading.value = true;
    try {
      const textSession = getTextSession();
      const metaRaw = sessionStorage.getItem("hrPersonalityMeta");
      if (metaRaw) hrMeta.value = JSON.parse(metaRaw) as HrPersonalityMeta;

      const data = await cardGameAdapter.createSession(
        textSession?.user_id || `user_${Date.now()}`,
        textSession?.user_name || "候选人",
        textSession?.hr_personality_id,
      );
      cardSessionId.value = data.session.session_id;
      cardSession.value = data.session;
      if (data.hr_personality_meta) hrMeta.value = data.hr_personality_meta;
      displayHrText.value = data.session.current_question;
      persistCard(data.session);
    } finally {
      cardDialogLoading.value = false;
    }
  }

  async function showDeltaFlash(delta: CardDeltaView, hint: string) {
    flashDelta.value = delta;
    showDelta.value = true;
    lastDeltaHint.value = hint;
    await new Promise((r) => window.setTimeout(r, 2200));
    showDelta.value = false;
  }

  async function onSelectCard(strategy: CardStrategyId) {
    if (cardBusy.value || cardDialogLoading.value || !cardSession.value || cardSession.value.status !== "ongoing") {
      return;
    }
    selectedCard.value = strategy;
    cardBusy.value = true;
    countdown.pause();
    cardError.value = "";

    const playerText =
      cardSession.value.option_replies?.[strategy]?.trim() ||
      CARD_GAME_CARDS.find((c) => c.id === strategy)?.desc ||
      "";
    lastPlayerCardText.value = playerText;

    try {
      const { session: next, result } = await cardGameAdapter.playTurn(
        cardSessionId.value,
        strategy,
        playerText,
      );
      cardWaiting.value = true;
      displayHrText.value = result.hr_reply;
      await new Promise((r) => window.setTimeout(r, 700));
      cardWaiting.value = false;
      await showDeltaFlash(result.delta, result.outcome_reason || "数值已更新");
      persistCard(next);
      if (result.is_game_over) {
        await finishCardGame();
        return;
      }
      displayHrText.value = result.next_question || next.current_question;
      selectedCard.value = null;
      countdown.reset(15);
    } catch (e) {
      cardError.value = String(e);
      countdown.reset(15);
    } finally {
      cardBusy.value = false;
      cardWaiting.value = false;
      cardDialogLoading.value = false;
    }
  }

  async function onAcceptOffer() {
    if (!canAccept.value || cardBusy.value) return;
    cardBusy.value = true;
    countdown.pause();
    try {
      const { session: next, reason } = await cardGameAdapter.acceptOffer(cardSessionId.value);
      persistCard(next);
      lastDeltaHint.value = reason;
      await finishCardGame();
    } catch (e) {
      cardError.value = String(e);
    } finally {
      cardBusy.value = false;
    }
  }

  async function finishCardGame() {
    countdown.pause();
    const { result } = await cardGameAdapter.settle(cardSessionId.value);
    sessionStorage.setItem("cardGameResult", JSON.stringify(result));
    goResult(cardSessionId.value);
  }

  async function enterCardPhase() {
    cardError.value = "";
    try {
      await ensureCardSession();
      countdown.reset(15);
    } catch (e) {
      cardError.value = `卡牌模式启动失败：${String(e)}`;
    }
  }

  function leaveCardPhase() {
    countdown.pause();
  }

  function onCardCountdownExpire() {
    if (cardSession.value?.status === "ongoing" && !cardBusy.value) {
      lastDeltaHint.value = "倒计时结束，请尽快选牌";
      countdown.reset(15);
    }
  }

  return {
    cardSession,
    hrMeta,
    cardBusy,
    cardDialogLoading,
    cardWaiting,
    cardError,
    selectedCard,
    flashDelta,
    showDelta,
    lastDeltaHint,
    displayHrText,
    lastPlayerCardText,
    canAccept,
    acceptHint,
    cardHrMeter,
    cardPlayerMeter,
    enterCardPhase,
    leaveCardPhase,
    onSelectCard,
    onAcceptOffer,
    onCardCountdownExpire,
  };
}
