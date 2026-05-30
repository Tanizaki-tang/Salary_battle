<template>
  <Transition name="impact-root">
    <div
      v-if="visible && delta"
      class="impact-root"
      :class="[`tone-${impactTone}`, { critical: isCritical }]"
      aria-live="polite"
    >
      <div class="impact-flash" aria-hidden="true" />
      <div class="impact-vignette" aria-hidden="true" />
      <div class="impact-shockwave" aria-hidden="true" />
      <div class="impact-shockwave impact-shockwave-2" aria-hidden="true" />

      <div class="impact-burst" aria-hidden="true">
        <span v-for="n in 12" :key="n" class="impact-ray" :style="{ '--ray-i': n }" />
      </div>

      <div class="impact-particles" aria-hidden="true">
        <span v-for="n in 18" :key="n" class="impact-particle" :style="particleStyle(n)" />
      </div>

      <p v-if="impactLabel" class="impact-label">{{ impactLabel }}</p>

      <div class="delta-row">
        <div
          v-for="(item, idx) in rows"
          :key="item.key"
          class="delta-chip"
          :class="[item.tone, { zero: item.isZero }]"
          :style="{ '--chip-i': idx }"
        >
          <span class="delta-chip-glow" aria-hidden="true" />
          <span class="delta-chip-text">{{ item.text }}</span>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { CardDeltaView } from "../../card-game/types";

const props = defineProps<{ delta: CardDeltaView | null; visible: boolean }>();

const rows = computed(() => {
  if (!props.delta) return [];
  const d = props.delta;
  const fmt = (n: number, suffix = "") => `${n > 0 ? "+" : ""}${n}${suffix}`;
  return [
    { key: "sat", tone: d.satisfaction < 0 ? "bad" : d.satisfaction > 0 ? "good" : "neutral", text: `😊 ${fmt(d.satisfaction)}`, isZero: d.satisfaction === 0 },
    { key: "sal", tone: d.salary_k > 0 ? "good" : d.salary_k < 0 ? "bad" : "neutral", text: `💰 ${fmt(d.salary_k, "K")}`, isZero: d.salary_k === 0 },
    { key: "wh", tone: d.work_hours > 0 ? "good" : d.work_hours < 0 ? "bad" : "neutral", text: `⏰ ${fmt(d.work_hours)}`, isZero: d.work_hours === 0 },
    { key: "sec", tone: d.security > 0 ? "good" : d.security < 0 ? "bad" : "neutral", text: `🛡️ ${fmt(d.security)}`, isZero: d.security === 0 },
  ].filter((r) => !r.isZero);
});

const impactTone = computed(() => {
  const d = props.delta;
  if (!d) return "mixed";
  if (d.satisfaction <= -2) return "negative";
  const gain = (d.salary_k > 0 ? 1 : 0) + (d.work_hours > 0 ? 1 : 0) + (d.security > 0 ? 1 : 0);
  const pain = (d.satisfaction < 0 ? 1 : 0) + (d.salary_k < 0 ? 1 : 0);
  if (gain >= 2 && pain === 0) return "positive";
  if (pain >= 1 && gain === 0) return "negative";
  return "mixed";
});

const isCritical = computed(() => {
  const d = props.delta;
  if (!d) return false;
  return d.satisfaction <= -2 || d.salary_k >= 2 || d.work_hours >= 2;
});

const impactLabel = computed(() => {
  const d = props.delta;
  if (!d) return "";
  if (d.satisfaction <= -2) return "💥 暴击失分";
  if (d.salary_k >= 2.5) return "⚡ 薪资猛攻";
  if (d.work_hours >= 2 && d.security >= 2) return "🔥 双线突破";
  if (impactTone.value === "positive") return "✨ 有效出牌";
  if (impactTone.value === "negative") return "⚠️ 硬碰硬";
  return "💫 局势变化";
});

function particleStyle(n: number) {
  const angle = (n / 18) * 360;
  const dist = 80 + (n % 5) * 28;
  return {
    "--p-angle": `${angle}deg`,
    "--p-dist": `${dist}px`,
    "--p-delay": `${(n % 6) * 0.04}s`,
  };
}
</script>

<style scoped>
.impact-root {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding-top: 12vh;
  pointer-events: none;
  z-index: 4000;
  overflow: hidden;
}

.impact-flash {
  position: absolute;
  inset: 0;
  opacity: 0;
  animation: impactFlash 0.55s ease-out both;
}

.tone-positive .impact-flash {
  background: radial-gradient(circle at 50% 42%, rgba(0, 194, 162, 0.45), transparent 58%);
}

.tone-negative .impact-flash {
  background: radial-gradient(circle at 50% 42%, rgba(255, 71, 87, 0.5), transparent 55%);
}

.tone-mixed .impact-flash {
  background: radial-gradient(circle at 50% 42%, rgba(255, 165, 2, 0.35), transparent 58%);
}

.impact-vignette {
  position: absolute;
  inset: 0;
  box-shadow: inset 0 0 120px rgba(0, 0, 0, 0.55);
  opacity: 0;
  animation: vignettePulse 0.7s ease-out both;
}

.impact-shockwave {
  position: absolute;
  top: 38%;
  left: 50%;
  width: 40px;
  height: 40px;
  margin: -20px 0 0 -20px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.65);
  opacity: 0;
  animation: shockwave 0.75s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.impact-shockwave-2 {
  animation-delay: 0.08s;
  border-color: rgba(0, 194, 162, 0.5);
}

.tone-negative .impact-shockwave {
  border-color: rgba(255, 107, 129, 0.75);
}

.tone-negative .impact-shockwave-2 {
  border-color: rgba(255, 71, 87, 0.45);
}

.impact-burst {
  position: absolute;
  top: 38%;
  left: 50%;
  width: 0;
  height: 0;
}

.impact-ray {
  position: absolute;
  top: 0;
  left: -2px;
  width: 4px;
  height: 56px;
  transform-origin: center top;
  transform: rotate(calc(var(--ray-i) * 30deg)) translateY(-8px);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), transparent);
  opacity: 0;
  animation: rayBurst 0.5s ease-out both;
  animation-delay: calc(var(--ray-i) * 0.015s);
}

.tone-positive .impact-ray {
  background: linear-gradient(180deg, rgba(123, 237, 159, 0.95), transparent);
}

.tone-negative .impact-ray {
  background: linear-gradient(180deg, rgba(255, 107, 129, 0.95), transparent);
}

.impact-particles {
  position: absolute;
  top: 38%;
  left: 50%;
  width: 0;
  height: 0;
}

.impact-particle {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  opacity: 0;
  animation: particleFly 0.65s ease-out both;
  animation-delay: var(--p-delay);
  transform: rotate(var(--p-angle)) translateX(var(--p-dist));
}

.tone-positive .impact-particle {
  background: #7bed9f;
  box-shadow: 0 0 8px #7bed9f;
}

.tone-negative .impact-particle {
  background: #ff6b81;
  box-shadow: 0 0 8px #ff6b81;
}

.impact-label {
  position: relative;
  z-index: 2;
  margin: 0 0 14px;
  font-size: clamp(22px, 3.2vw, 34px);
  font-weight: 900;
  letter-spacing: 0.08em;
  text-shadow:
    0 0 20px rgba(255, 255, 255, 0.35),
    0 4px 16px rgba(0, 0, 0, 0.45);
  animation: labelSlam 0.45s cubic-bezier(0.22, 1.12, 0.36, 1) both;
}

.tone-positive .impact-label { color: #7bed9f; }
.tone-negative .impact-label { color: #ff6b81; }
.tone-mixed .impact-label { color: #ffd166; }

.critical .impact-label {
  animation: labelSlamCritical 0.55s cubic-bezier(0.22, 1.2, 0.36, 1) both;
}

.delta-row {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  max-width: 92vw;
}

.delta-chip {
  position: relative;
  padding: 14px 20px;
  border-radius: 16px;
  font-size: clamp(20px, 2.4vw, 28px);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  background: rgba(10, 22, 40, 0.88);
  border: 2px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.45);
  animation: chipSlam 0.55s cubic-bezier(0.22, 1.15, 0.36, 1) both;
  animation-delay: calc(0.08s + var(--chip-i) * 0.07s);
  overflow: hidden;
}

.delta-chip-glow {
  position: absolute;
  inset: -20%;
  opacity: 0.6;
  animation: chipGlow 0.8s ease-out both;
}

.delta-chip.good {
  color: #7bed9f;
  border-color: rgba(123, 237, 159, 0.55);
  text-shadow: 0 0 16px rgba(123, 237, 159, 0.45);
}

.delta-chip.good .delta-chip-glow {
  background: radial-gradient(circle, rgba(123, 237, 159, 0.35), transparent 70%);
}

.delta-chip.bad {
  color: #ff6b81;
  border-color: rgba(255, 107, 129, 0.55);
  text-shadow: 0 0 16px rgba(255, 107, 129, 0.45);
}

.delta-chip.bad .delta-chip-glow {
  background: radial-gradient(circle, rgba(255, 107, 129, 0.35), transparent 70%);
}

.delta-chip.neutral {
  color: #dfe6e9;
}

.delta-chip-text {
  position: relative;
  z-index: 1;
}

@keyframes impactFlash {
  0% { opacity: 0; }
  12% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes vignettePulse {
  0%, 100% { opacity: 0; }
  20% { opacity: 1; }
}

@keyframes shockwave {
  0% { opacity: 0.85; transform: scale(0.2); }
  100% { opacity: 0; transform: scale(14); }
}

@keyframes rayBurst {
  0% { opacity: 0; transform: rotate(calc(var(--ray-i) * 30deg)) translateY(-8px) scaleY(0.2); }
  30% { opacity: 0.9; }
  100% { opacity: 0; transform: rotate(calc(var(--ray-i) * 30deg)) translateY(-8px) scaleY(1.2); }
}

@keyframes particleFly {
  0% { opacity: 1; transform: rotate(var(--p-angle)) translateX(0) scale(1); }
  100% { opacity: 0; transform: rotate(var(--p-angle)) translateX(calc(var(--p-dist) * 1.2)) scale(0.2); }
}

@keyframes labelSlam {
  0% { opacity: 0; transform: translateY(-36px) scale(1.35); filter: blur(4px); }
  55% { opacity: 1; transform: translateY(4px) scale(0.96); filter: blur(0); }
  100% { transform: translateY(0) scale(1); }
}

@keyframes labelSlamCritical {
  0% { opacity: 0; transform: translateY(-48px) scale(1.5) rotate(-3deg); }
  40% { opacity: 1; transform: translateY(6px) scale(0.92) rotate(2deg); }
  60% { transform: translateY(-3px) scale(1.04) rotate(-1deg); }
  100% { transform: translateY(0) scale(1) rotate(0); }
}

@keyframes chipSlam {
  0% { opacity: 0; transform: translateY(40px) scale(0.6) rotate(-6deg); }
  60% { opacity: 1; transform: translateY(-6px) scale(1.08) rotate(2deg); }
  100% { transform: translateY(0) scale(1) rotate(0); }
}

@keyframes chipGlow {
  0% { opacity: 0.9; transform: scale(0.5); }
  100% { opacity: 0; transform: scale(1.4); }
}

.impact-root-enter-active,
.impact-root-leave-active {
  transition: opacity 0.35s ease;
}

.impact-root-enter-from,
.impact-root-leave-to {
  opacity: 0;
}
</style>
