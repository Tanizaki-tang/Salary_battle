<template>
  <div
    class="battle-card-landscape"
    :class="{ 'is-impact': showDelta }"
    :style="{ '--battle-scale': uiScale }"
  >
    <div class="battle-card-main">
      <aside v-if="cardSession" class="battle-card-info">
        <div class="battle-card-info-title">信息面板</div>
        <div class="battle-card-info-item" :class="statFlash?.sat === 'bad' ? 'flash-bad' : statFlash?.sat === 'good' ? 'flash-good' : ''">
          <div class="battle-card-info-row">
            <span class="battle-card-info-label">满意度</span>
            <span class="battle-card-info-val">{{ cardSession.stats.satisfaction.toFixed(1) }}</span>
          </div>
          <div class="battle-card-info-track">
            <div class="battle-card-info-fill" :style="{ width: `${(cardSession.stats.satisfaction / 10) * 100}%` }" />
          </div>
        </div>
        <div class="battle-card-info-item" :class="statFlash?.salary === 'bad' ? 'flash-bad' : statFlash?.salary === 'good' ? 'flash-good' : ''">
          <div class="battle-card-info-row">
            <span class="battle-card-info-label">薪资</span>
            <span class="battle-card-info-val">{{ cardSession.stats.salary_k.toFixed(1) }}K</span>
          </div>
          <div class="battle-card-info-track">
            <div class="battle-card-info-fill" :style="{ width: `${((cardSession.stats.salary_k - 8) / 14) * 100}%` }" />
          </div>
        </div>
        <div class="battle-card-info-item" :class="statFlash?.hours === 'bad' ? 'flash-bad' : statFlash?.hours === 'good' ? 'flash-good' : ''">
          <div class="battle-card-info-row">
            <span class="battle-card-info-label">工作时长</span>
            <span class="battle-card-info-val">{{ cardSession.stats.work_hours.toFixed(1) }}</span>
          </div>
          <div class="battle-card-info-track">
            <div class="battle-card-info-fill" :style="{ width: `${(cardSession.stats.work_hours / 10) * 100}%` }" />
          </div>
        </div>
        <div class="battle-card-info-item" :class="statFlash?.sec === 'bad' ? 'flash-bad' : statFlash?.sec === 'good' ? 'flash-good' : ''">
          <div class="battle-card-info-row">
            <span class="battle-card-info-label">社保情况</span>
            <span class="battle-card-info-val">{{ cardSession.stats.security.toFixed(1) }}</span>
          </div>
          <div class="battle-card-info-track">
            <div class="battle-card-info-fill" :style="{ width: `${(cardSession.stats.security / 5) * 100}%` }" />
          </div>
        </div>
      </aside>

      <section class="battle-card-center">
        <div class="battle-card-hr-emoji">
          <div class="battle-card-hr-emoji-inner" :title="hrMoodMeta.label">{{ hrMoodMeta.emoji }}</div>
        </div>

        <div class="battle-card-hr-line">
          <div v-if="cardDialogLoading" class="battle-card-dialogue-loading">正在生成对话…</div>
          <div class="battle-card-line-text">{{ cardWaiting ? "对方正在输入中…" : displayHrText }}</div>
        </div>

        <div class="battle-card-strategy-line">
          <div v-if="cardBusy && !lastPlayerCardText" class="battle-card-line-text">正在出牌…</div>
          <div v-else-if="lastPlayerCardText" class="battle-card-line-text">{{ lastPlayerCardText }}</div>
          <div v-else class="battle-card-countdown">
            <div class="battle-card-countdown-track">
              <div class="battle-card-countdown-fill" :style="{ width: `${turnProgressPercent}%` }" />
            </div>
            <div class="battle-card-countdown-label">{{ countdownRunning ? `${turnRemainingSeconds}s` : "暂停" }}</div>
          </div>
        </div>

        <div class="battle-card-played">
          <div v-if="playedCard" class="battle-card-played-card" :class="`tone-${playedCard.tone}`">
            <div class="battle-card-played-corner top">{{ playedCard.emoji }}</div>
            <div class="battle-card-played-center">
              <div class="battle-card-played-emoji">{{ playedCard.emoji }}</div>
              <div class="battle-card-played-label">{{ playedCard.label }}</div>
            </div>
            <div class="battle-card-played-corner bottom">{{ playedCard.emoji }}</div>
          </div>
        </div>

        <div class="battle-card-deck-zone">
          <div class="battle-card-deck-title">策略牌存放区</div>
          <CardGameDeck
            :disabled="cardBusy || cardDialogLoading || !countdownRunning"
            :selected-id="selectedCard"
            :available-strategies="cardSession?.available_strategies"
            :option-replies="cardSession?.option_replies"
            @select="$emit('select-card', $event)"
          />
          <div class="battle-card-note">
            <p v-if="lastDeltaHint" class="battle-card-hint">{{ lastDeltaHint }}</p>
            <p v-if="cardError" class="battle-card-error">{{ cardError }}</p>
          </div>
        </div>

        <div class="battle-card-player-avatar">
          <img class="battle-card-player-img" :src="playerAvatarUrl" alt="玩家" />
        </div>
      </section>
    </div>

    <CardGameDeltaFlash :delta="flashDelta" :visible="showDelta" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { playerAvatarUrl } from "../../assets/avatars";
import { CARD_GAME_CARDS } from "../../card-game/cards";
import CardGameDeck from "../card-game/CardGameDeck.vue";
import CardGameDeltaFlash from "../card-game/CardGameDeltaFlash.vue";
import type { CardDeltaView, CardGameState, CardStrategyId } from "../../card-game/types";
import type { MoodMeta } from "../../composables/useBattleMood";

const props = defineProps<{
  cardSession: CardGameState | null;
  displayHrText: string;
  lastPlayerCardText: string;
  cardWaiting: boolean;
  cardBusy: boolean;
  cardDialogLoading: boolean;
  cardError: string;
  lastDeltaHint: string;
  selectedCard: CardStrategyId | null;
  flashDelta: CardDeltaView | null;
  showDelta: boolean;
  cardHrMeter: number;
  cardPlayerMeter: number;
  hrMood: string;
  playerMood: string;
  hrMoodMeta: MoodMeta;
  playerMoodMeta: MoodMeta;
  hrRoleLabel: string;
  playerRoleLabel: string;
  uiScale: number;
  countdownRunning: boolean;
  turnProgressPercent: number;
  turnRemainingSeconds: number;
}>();

defineEmits<{ "select-card": [id: CardStrategyId] }>();

type StatFlashTone = "good" | "bad";

const statFlash = computed(() => {
  if (!props.showDelta || !props.flashDelta) return {} as Partial<Record<string, StatFlashTone>>;
  const d = props.flashDelta;
  const out: Partial<Record<string, StatFlashTone>> = {};
  if (d.satisfaction !== 0) out.sat = d.satisfaction < 0 ? "bad" : "good";
  if (d.salary_k !== 0) out.salary = d.salary_k > 0 ? "good" : "bad";
  if (d.work_hours !== 0) out.hours = d.work_hours > 0 ? "good" : "bad";
  if (d.security !== 0) out.sec = d.security > 0 ? "good" : "bad";
  return out;
});

const playedCard = computed(() => {
  const id = (props.selectedCard || props.cardSession?.last_strategy || null) as CardStrategyId | null;
  if (!id) return null;
  return CARD_GAME_CARDS.find((c) => c.id === id) || null;
});
</script>

<style scoped>
.battle-card-landscape {
  --battle-scale: 1;
  display: flex;
  min-height: 0;
  height: 100%;
  width: 100%;
  max-width: 100%;
  max-height: 100%;
  overflow: hidden;
  padding: 0 calc(12px * var(--battle-scale)) calc(10px * var(--battle-scale));
  box-sizing: border-box;
}

.battle-card-main {
  display: grid;
  grid-template-columns: minmax(calc(150px * var(--battle-scale)), calc(220px * var(--battle-scale))) minmax(0, 1fr);
  gap: calc(14px * var(--battle-scale));
  min-height: 0;
  width: 100%;
}

.battle-card-dialogue-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(9, 16, 24, 0.45);
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.battle-card-info {
  min-height: 0;
  border-radius: calc(14px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  padding: calc(12px * var(--battle-scale));
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--battle-scale));
}

.battle-card-info-title {
  font-size: calc(12px * var(--battle-scale));
  font-weight: 800;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: 0.08em;
}

.battle-card-info-item {
  border-radius: calc(12px * var(--battle-scale));
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: calc(10px * var(--battle-scale)) calc(10px * var(--battle-scale));
}

.battle-card-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: rgba(255, 255, 255, 0.86);
  font-size: calc(12px * var(--battle-scale));
  margin-bottom: calc(8px * var(--battle-scale));
}

.battle-card-info-val {
  font-variant-numeric: tabular-nums;
  font-weight: 800;
}

.battle-card-info-track {
  height: calc(7px * var(--battle-scale));
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.battle-card-info-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffa502, #00c2a2);
  transition: width 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.battle-card-info-item.flash-good {
  box-shadow: 0 0 28px rgba(123, 237, 159, 0.26);
  border-color: rgba(123, 237, 159, 0.5);
}

.battle-card-info-item.flash-bad {
  box-shadow: 0 0 28px rgba(255, 107, 129, 0.22);
  border-color: rgba(255, 107, 129, 0.5);
}

.battle-card-center {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
  gap: calc(12px * var(--battle-scale));
  align-items: start;
}

.battle-card-hr-emoji {
  display: flex;
  justify-content: center;
}

.battle-card-hr-emoji-inner {
  width: calc(64px * var(--battle-scale));
  height: calc(64px * var(--battle-scale));
  border-radius: calc(16px * var(--battle-scale));
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: calc(34px * var(--battle-scale));
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.25);
}

.battle-card-hr-line,
.battle-card-strategy-line {
  position: relative;
  border-radius: calc(14px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  padding: calc(12px * var(--battle-scale)) calc(14px * var(--battle-scale));
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(54px * var(--battle-scale));
}

.battle-card-line-text {
  font-size: calc(14px * var(--battle-scale));
  font-weight: 650;
  color: rgba(255, 255, 255, 0.92);
  line-height: 1.35;
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.battle-card-countdown {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: calc(12px * var(--battle-scale));
}

.battle-card-countdown-track {
  height: calc(10px * var(--battle-scale));
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.22);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.battle-card-countdown-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 194, 162, 0.9), rgba(255, 165, 2, 0.9));
  transition: width 0.25s linear;
}

.battle-card-countdown-label {
  font-size: calc(12px * var(--battle-scale));
  color: rgba(255, 255, 255, 0.78);
  font-variant-numeric: tabular-nums;
  font-weight: 800;
}

.battle-card-played {
  display: flex;
  justify-content: center;
  min-height: calc(128px * var(--battle-scale));
}

.battle-card-played-card {
  width: calc(96px * var(--battle-scale));
  aspect-ratio: 2.6 / 3.6;
  border-radius: calc(14px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(120% 110% at 30% 10%, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0) 52%),
    linear-gradient(155deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.06));
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.3);
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto;
  padding: calc(10px * var(--battle-scale)) calc(10px * var(--battle-scale));
  transform: translateZ(0);
}

.battle-card-played-card::after {
  content: "";
  position: absolute;
  inset: calc(6px * var(--battle-scale));
  border-radius: calc(10px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.16);
  pointer-events: none;
}

.battle-card-played-corner {
  font-size: calc(13px * var(--battle-scale));
  opacity: 0.9;
}

.battle-card-played-corner.bottom {
  justify-self: end;
  align-self: end;
  transform: rotate(180deg);
}

.battle-card-played-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: calc(6px * var(--battle-scale));
}

.battle-card-played-emoji {
  font-size: calc(30px * var(--battle-scale));
}

.battle-card-played-label {
  font-size: calc(12px * var(--battle-scale));
  font-weight: 800;
  color: rgba(255, 255, 255, 0.92);
  text-align: center;
}

.battle-card-deck-zone {
  min-height: 0;
  overflow: hidden;
  border-radius: calc(16px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.04);
  padding: calc(12px * var(--battle-scale));
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: calc(10px * var(--battle-scale));
}

.battle-card-deck-title {
  font-size: calc(12px * var(--battle-scale));
  font-weight: 800;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.08em;
  text-align: center;
}

.battle-card-note {
  text-align: center;
}

.battle-card-hint {
  margin: 0;
  font-size: calc(12px * var(--battle-scale));
  color: rgba(255, 255, 255, 0.65);
}

.battle-card-error {
  margin: calc(6px * var(--battle-scale)) 0 0;
  color: #ff6b81;
  font-size: calc(12px * var(--battle-scale));
}

:deep(.cg-deck) {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 4px;
  gap: calc(8px * var(--battle-scale));
}

:deep(.cg-card) {
  padding: calc(10px * var(--battle-scale)) calc(8px * var(--battle-scale));
}

:deep(.cg-card-emoji) {
  font-size: calc(28px * var(--battle-scale));
}

:deep(.cg-card-label) {
  font-size: calc(12px * var(--battle-scale));
}

:deep(.cg-card-desc) {
  font-size: calc(10px * var(--battle-scale));
}

.battle-card-player-avatar {
  display: flex;
  justify-content: center;
  padding-top: calc(2px * var(--battle-scale));
}

.battle-card-player-img {
  width: calc(54px * var(--battle-scale));
  height: calc(54px * var(--battle-scale));
  border-radius: calc(16px * var(--battle-scale));
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.24);
  object-fit: cover;
}

.battle-card-landscape.is-impact {
  animation: screenShake 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

.battle-card-landscape.is-impact .battle-card-deck-zone {
  animation: deckRecoil 0.45s ease-out both;
}

@keyframes screenShake {
  0%, 100% { transform: translate(0, 0); }
  12% { transform: translate(-5px, 3px); }
  24% { transform: translate(4px, -2px); }
  36% { transform: translate(-3px, -3px); }
  48% { transform: translate(3px, 2px); }
  60% { transform: translate(-2px, 1px); }
  72% { transform: translate(1px, -1px); }
}

@keyframes deckRecoil {
  0% { transform: translateY(0); }
  30% { transform: translateY(6px); }
  100% { transform: translateY(0); }
}
</style>
