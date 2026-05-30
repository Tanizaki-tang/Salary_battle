<template>
  <aside
    class="mood-panel"
    :class="[`mood-${side}`, `tone-${moodKey}`]"
    :style="{ '--mood-scale': scale ?? 1 }"
  >
    <div class="mood-card">
      <div class="mood-role">{{ roleLabel }}</div>
      <img v-if="avatarUrl" class="mood-avatar" :src="avatarUrl" :alt="roleLabel" />
      <Transition name="mood-pop" mode="out-in">
        <div :key="moodKey" class="mood-emoji-wrap">
          <span class="mood-emoji">{{ meta.emoji }}</span>
          <span class="mood-glow" aria-hidden="true" />
        </div>
      </Transition>
      <Transition name="mood-fade" mode="out-in">
        <div :key="moodKey" class="mood-copy">
          <div class="mood-label">{{ meta.label }}</div>
          <div class="mood-hint">{{ meta.hint }}</div>
        </div>
      </Transition>
      <div class="mood-meter">
        <span class="mood-meter-label">{{ meterLabel }}</span>
        <div class="mood-meter-track">
          <div class="mood-meter-fill" :style="{ width: `${meterValue}%` }" />
        </div>
        <span class="mood-meter-val">{{ meterValue }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { MoodMeta } from "../../composables/useBattleMood";

defineProps<{
  side: "hr" | "player";
  moodKey: string;
  meta: MoodMeta;
  roleLabel: string;
  avatarUrl?: string;
  meterLabel: string;
  meterValue: number;
  scale?: number;
}>();
</script>

<style scoped>
.mood-panel {
  --mood-scale: 1;
  flex: 0 0 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: calc(24px * var(--mood-scale)) calc(16px * var(--mood-scale));
  animation: panelIn 0.68s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.mood-hr {
  animation-name: panelInLeft;
}

.mood-player {
  animation-name: panelInRight;
}

@keyframes panelInLeft {
  from { opacity: 0; transform: translateX(-28px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes panelInRight {
  from { opacity: 0; transform: translateX(28px); }
  to { opacity: 1; transform: translateX(0); }
}

.mood-card {
  width: min(100%, calc(280px * var(--mood-scale)));
  padding: calc(28px * var(--mood-scale)) calc(22px * var(--mood-scale)) calc(24px * var(--mood-scale));
  border-radius: calc(24px * var(--mood-scale));
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  text-align: center;
  color: #fff;
}

.mood-role {
  font-size: calc(13px * var(--mood-scale));
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.72);
  margin-bottom: calc(14px * var(--mood-scale));
}

.mood-avatar {
  width: calc(56px * var(--mood-scale));
  height: calc(56px * var(--mood-scale));
  border-radius: calc(14px * var(--mood-scale));
  object-fit: cover;
  margin: 0 auto calc(16px * var(--mood-scale));
  display: block;
  border: 2px solid rgba(255, 255, 255, 0.18);
}

.mood-emoji-wrap {
  position: relative;
  width: calc(120px * var(--mood-scale));
  height: calc(120px * var(--mood-scale));
  margin: 0 auto calc(18px * var(--mood-scale));
  display: flex;
  align-items: center;
  justify-content: center;
}

.mood-emoji {
  font-size: calc(72px * var(--mood-scale));
  line-height: 1;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 calc(8px * var(--mood-scale)) calc(18px * var(--mood-scale)) rgba(0, 0, 0, 0.25));
}

.mood-label {
  font-size: calc(24px * var(--mood-scale));
  font-weight: 700;
  margin-bottom: calc(8px * var(--mood-scale));
}

.mood-hint {
  font-size: calc(13px * var(--mood-scale));
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.72);
  min-height: calc(40px * var(--mood-scale));
}

.mood-meter {
  margin-top: calc(18px * var(--mood-scale));
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: calc(8px * var(--mood-scale));
  align-items: center;
  font-size: calc(11px * var(--mood-scale));
  color: rgba(255, 255, 255, 0.65);
}

.mood-meter-track {
  height: calc(6px * var(--mood-scale));
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.mood-glow {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  opacity: 0.55;
  filter: blur(18px);
}

.tone-calm .mood-glow,
.tone-confident .mood-glow {
  background: radial-gradient(circle, rgba(0, 194, 162, 0.55), transparent 70%);
}

.tone-angry .mood-glow {
  background: radial-gradient(circle, rgba(255, 71, 87, 0.65), transparent 70%);
}

.tone-aggrieved .mood-glow,
.tone-pleading .mood-glow {
  background: radial-gradient(circle, rgba(255, 165, 2, 0.55), transparent 70%);
}

.tone-panicked .mood-glow {
  background: radial-gradient(circle, rgba(116, 185, 255, 0.55), transparent 70%);
}

.mood-meter-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #00c2a2, #7bed9f);
  transition: width 0.45s ease;
}

.tone-angry .mood-meter-fill {
  background: linear-gradient(90deg, #ff4757, #ffa502);
}

.tone-panicked .mood-meter-fill,
.tone-pleading .mood-meter-fill {
  background: linear-gradient(90deg, #ffa502, #ff6348);
}

.mood-pop-enter-active,
.mood-pop-leave-active {
  transition: transform 0.32s ease, opacity 0.32s ease;
}

.mood-pop-enter-from {
  opacity: 0;
  transform: scale(0.55) rotate(-8deg);
}

.mood-pop-leave-to {
  opacity: 0;
  transform: scale(0.85) rotate(8deg);
}

.mood-fade-enter-active,
.mood-fade-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.mood-fade-enter-from,
.mood-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
