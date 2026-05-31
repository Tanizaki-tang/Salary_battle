<template>

  <div class="cg-deck" role="toolbar" aria-label="策略卡牌">

    <button

      v-for="(card, idx) in cardsToShow"
      :key="card.id"

      type="button"

      class="cg-card"

      :class="[`tone-${card.tone}`, { disabled, active: selectedId === card.id }]"

      :style="{ '--cg-tilt': `${(idx - (cardsToShow.length - 1) / 2) * 2}deg` }"
      :disabled="disabled"

      :title="previewText(card.id)"

      @click="$emit('select', card.id)"

    >

      <span class="cg-card-corner top">{{ card.emoji }}</span>
      <span class="cg-card-corner bottom">{{ card.emoji }}</span>

      <span class="cg-card-center">
        <span class="cg-card-emoji">{{ card.emoji }}</span>
        <span class="cg-card-label">{{ card.label }}</span>
      </span>

      <span class="cg-card-desc">{{ previewText(card.id) }}</span>

    </button>

  </div>

</template>



<script setup lang="ts">

import { computed } from "vue";
import { CARD_GAME_CARDS } from "../../card-game/cards";

import type { CardStrategyId } from "../../card-game/types";



const props = defineProps<{

  disabled?: boolean;

  selectedId?: CardStrategyId | null;

  availableStrategies?: CardStrategyId[];

  optionReplies?: Partial<Record<CardStrategyId, string>>;

}>();



defineEmits<{ select: [id: CardStrategyId] }>();


const cardsToShow = computed(() => {
  const ids = props.availableStrategies;
  if (!ids || ids.length === 0) return CARD_GAME_CARDS;
  return CARD_GAME_CARDS.filter((c) => ids.includes(c.id));
});


function previewText(id: CardStrategyId) {

  const llm = props.optionReplies?.[id]?.trim();

  if (llm) return llm;

  return CARD_GAME_CARDS.find((c) => c.id === id)?.desc ?? "";

}

</script>



<style scoped>

.cg-deck {

  perspective: 1000px;
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 14px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 4px 8px;
  -webkit-overflow-scrolling: touch;
}



.cg-card {

  appearance: none;

  border: 1px solid rgba(255, 255, 255, 0.14);

  background:
    radial-gradient(140% 120% at 20% 0%, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0) 60%),
    linear-gradient(160deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04));
  border-radius: 18px;

  padding: 14px 12px 12px;

  color: #fff;

  cursor: pointer;

  display: flex;

  flex-direction: column;

  align-items: center;

  gap: 6px;

  width: clamp(120px, 16vw, 168px);
  min-height: 0;
  aspect-ratio: 2.6 / 3.6;
  flex: 0 0 auto;

  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
  transform: rotate(var(--cg-tilt, 0deg)) translateZ(0);
  transform-style: preserve-3d;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, filter 0.18s ease, overflow 0s;
}



.cg-card::before {
  content: "";
  position: absolute;
  inset: -40%;
  background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.18) 50%, transparent 70%);
  transform: translateX(-40%) rotate(12deg);
  opacity: 0;
  transition: opacity 0.18s ease, transform 0.35s ease;
  pointer-events: none;
}

.cg-card-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
  flex: 1 1 auto;
  min-height: 0;
}

.cg-card-corner {
  position: absolute;
  font-size: 14px;
  opacity: 0.88;
}

.cg-card-corner.top {
  top: 14px;
  left: 14px;
}

.cg-card-corner.bottom {
  bottom: 14px;
  right: 14px;
  transform: rotate(180deg);
}

.cg-card:not(:disabled):hover,
.cg-card:not(:disabled):focus-visible {
  z-index: 30;
  overflow: visible;
  transform: translateY(-6px) rotate(var(--cg-tilt, 0deg)) scale(1.02);
  filter: saturate(1.05);
}

.cg-card:not(:disabled):hover::before {
  opacity: 1;
  transform: translateX(30%) rotate(12deg);
}



.cg-card.active {
  box-shadow:
    0 0 0 2px rgba(0, 194, 162, 0.85),
    0 0 32px rgba(0, 194, 162, 0.45),
    0 16px 40px rgba(0, 0, 0, 0.35);
  z-index: 10;
  animation: cgThrow 0.62s cubic-bezier(0.16, 0.85, 0.22, 1) both;
}

.cg-card.active::after {
  content: "";
  position: absolute;
  inset: -8px;
  border-radius: 18px;
  border: 2px solid rgba(0, 194, 162, 0.55);
  opacity: 0;
  pointer-events: none;
  animation: cgThrowRing 0.62s ease-out both;
}



.cg-card.disabled,

.cg-card:disabled {

  opacity: 0.45;

  cursor: not-allowed;

  transform: none;

}



.tone-red { border-color: rgba(255, 71, 87, 0.45); }

.tone-blue { border-color: rgba(116, 185, 255, 0.45); }

.tone-green { border-color: rgba(0, 194, 162, 0.45); }

.tone-yellow { border-color: rgba(255, 165, 2, 0.45); }

.tone-purple { border-color: rgba(162, 155, 254, 0.45); }

.tone-gray { border-color: rgba(255, 255, 255, 0.2); }



.cg-card-emoji { font-size: 40px; line-height: 1; }

.cg-card-label { font-size: 15px; font-weight: 700; }

.cg-card-desc {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 6px;
  z-index: 4;
  padding: 6px 8px;
  border-radius: 10px;
  background: rgba(8, 14, 24, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
  font-size: 11px;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.92);
  text-align: center;
  opacity: 0;
  visibility: hidden;
  transform: translateY(6px);
  transition: opacity 0.16s ease, transform 0.16s ease, visibility 0.16s ease;
  pointer-events: none;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cg-card:not(:disabled):hover .cg-card-desc,
.cg-card:not(:disabled):focus-visible .cg-card-desc {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.cg-card.active .cg-card-desc {
  opacity: 0;
  visibility: hidden;
}


@keyframes cgThrow {
  0% {
    transform: translateY(0) rotate(var(--cg-tilt, 0deg)) scale(1);
    filter: brightness(1) saturate(1);
  }
  18% {
    transform: translateY(-8px) rotate(calc(var(--cg-tilt, 0deg) * 0.85)) scale(1.12);
    filter: brightness(1.25) saturate(1.2);
  }
  55% {
    transform: translateY(-52px) rotate(calc(var(--cg-tilt, 0deg) * 0.15)) scale(1.08);
    filter: brightness(1.15);
  }
  100% {
    transform: translateY(-96px) rotate(calc(var(--cg-tilt, 0deg) * 0.05)) scale(0.92);
    opacity: 0;
    filter: blur(2px) brightness(1.4);
  }
}

@keyframes cgThrowRing {
  0% { opacity: 0.85; transform: scale(0.85); }
  100% { opacity: 0; transform: scale(1.45); }
}
</style>
