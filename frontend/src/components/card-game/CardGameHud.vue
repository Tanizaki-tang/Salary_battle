<template>
  <header class="cg-hud">
    <div
      v-for="item in items"
      :key="item.key"
      class="cg-stat"
      :class="{
        danger: item.danger,
        ok: item.ok,
        'flash-good': statFlash?.[item.key] === 'good',
        'flash-bad': statFlash?.[item.key] === 'bad',
      }"
    >
      <div class="cg-stat-head">
        <span class="cg-stat-icon">{{ item.icon }}</span>
        <span class="cg-stat-label">{{ item.label }}</span>
        <span class="cg-stat-val">{{ item.display }}</span>
      </div>
      <div class="cg-stat-track">
        <div class="cg-stat-fill" :style="{ width: `${item.percent}%` }" />
      </div>
      <div v-if="item.hint" class="cg-stat-hint">{{ item.hint }}</div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { CardGameStats } from "../../card-game/types";
import { DEAL_THRESHOLDS, STAT_LIMITS } from "../../card-game/types";

const props = defineProps<{
  stats: CardGameStats;
  roundIndex: number;
  maxRound: number;
  statFlash?: Partial<Record<string, "good" | "bad">>;
}>();

const items = computed(() => {
  const s = props.stats;
  return [
    {
      key: "sat",
      icon: "😊",
      label: "满意度",
      display: `${s.satisfaction.toFixed(1)}`,
      percent: (s.satisfaction / STAT_LIMITS.satisfaction.max) * 100,
      danger: s.satisfaction <= 2,
      ok: s.satisfaction > DEAL_THRESHOLDS.satisfaction,
      hint: s.satisfaction <= 0 ? "谈崩风险" : "",
    },
    {
      key: "salary",
      icon: "💰",
      label: "薪资",
      display: `${s.salary_k.toFixed(1)}K`,
      percent: ((s.salary_k - STAT_LIMITS.salary_k.min) / (STAT_LIMITS.salary_k.max - STAT_LIMITS.salary_k.min)) * 100,
      danger: false,
      ok: s.salary_k >= DEAL_THRESHOLDS.salary_k,
      hint: `目标 ≥ ${DEAL_THRESHOLDS.salary_k}K`,
    },
    {
      key: "hours",
      icon: "⏰",
      label: "工时约定",
      display: `${s.work_hours.toFixed(1)}`,
      percent: (s.work_hours / STAT_LIMITS.work_hours.max) * 100,
      danger: false,
      ok: s.work_hours >= DEAL_THRESHOLDS.work_hours,
      hint: `目标 ≥ ${DEAL_THRESHOLDS.work_hours}`,
    },
    {
      key: "sec",
      icon: "🛡️",
      label: "保障情况",
      display: `${s.security.toFixed(1)}`,
      percent: (s.security / STAT_LIMITS.security.max) * 100,
      danger: false,
      ok: s.security >= DEAL_THRESHOLDS.security,
      hint: `目标 ≥ ${DEAL_THRESHOLDS.security}`,
    },
  ];
});
</script>

<style scoped>
.cg-hud {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.cg-stat {
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.cg-stat.danger {
  border-color: rgba(255, 71, 87, 0.55);
  box-shadow: 0 0 16px rgba(255, 71, 87, 0.15);
}

.cg-stat.ok .cg-stat-fill {
  background: linear-gradient(90deg, #00c2a2, #7bed9f);
}

.cg-stat-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 6px;
}

.cg-stat-val {
  margin-left: auto;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.cg-stat-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.cg-stat-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ffa502, #00c2a2);
  transition: width 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.cg-stat-hint {
  margin-top: 4px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.55);
}

.cg-stat.flash-good {
  animation: statPulseGood 0.65s cubic-bezier(0.22, 1.15, 0.36, 1) both;
}

.cg-stat.flash-bad {
  animation: statPulseBad 0.65s cubic-bezier(0.22, 1.15, 0.36, 1) both;
}

.cg-stat.flash-good .cg-stat-val {
  animation: statValPop 0.55s cubic-bezier(0.22, 1.2, 0.36, 1) both;
}

.cg-stat.flash-bad .cg-stat-val {
  animation: statValPop 0.55s cubic-bezier(0.22, 1.2, 0.36, 1) both;
}

@keyframes statPulseGood {
  0% { box-shadow: 0 0 0 rgba(123, 237, 159, 0); border-color: rgba(123, 237, 159, 0.2); }
  35% { box-shadow: 0 0 28px rgba(123, 237, 159, 0.45); border-color: rgba(123, 237, 159, 0.75); transform: scale(1.04); }
  100% { box-shadow: 0 0 0 rgba(123, 237, 159, 0); transform: scale(1); }
}

@keyframes statPulseBad {
  0% { box-shadow: 0 0 0 rgba(255, 107, 129, 0); border-color: rgba(255, 107, 129, 0.2); }
  35% { box-shadow: 0 0 28px rgba(255, 107, 129, 0.45); border-color: rgba(255, 107, 129, 0.75); transform: scale(1.04); }
  100% { box-shadow: 0 0 0 rgba(255, 107, 129, 0); transform: scale(1); }
}

@keyframes statValPop {
  0% { transform: scale(1); }
  40% { transform: scale(1.28); color: #fff; }
  100% { transform: scale(1); }
}
</style>
