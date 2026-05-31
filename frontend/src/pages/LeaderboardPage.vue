<template>
  <section class="lb-stage" :class="{ 'is-entered': entered, 'is-loading': loading }">
    <div class="lb-flash" aria-hidden="true" />
    <div class="lb-scan" aria-hidden="true" />
    <div class="lb-grid" aria-hidden="true" />

    <header class="lb-top">
      <button type="button" class="lb-back" @click="goBack">‹ 返回</button>
      <div class="lb-title-wrap">
        <p class="lb-kicker">Salary Battle</p>
        <h1 class="lb-title">🏆 全球谈判榜</h1>
      </div>
      <div class="lb-top-spacer" />
    </header>

    <div v-if="loading" class="lb-loading">榜单载入中…</div>
    <p v-else-if="error" class="lb-error">{{ error }}</p>

    <div v-else class="lb-board">
      <div class="lb-board-head">
        <span>排名</span>
        <span>玩家</span>
        <span>分数</span>
        <span>薪资</span>
        <span>评级</span>
      </div>
      <ul class="lb-list">
        <li
          v-for="(row, idx) in entries"
          :key="`${row.user_name}-${row.created_at}-${idx}`"
          class="lb-row"
          :class="{
            'is-top1': row.rank === 1,
            'is-top2': row.rank === 2,
            'is-top3': row.rank === 3,
          }"
          :style="{ '--row-delay': `${120 + idx * 55}ms` }"
        >
          <span class="lb-rank">{{ medalFor(row.rank) }}</span>
          <span class="lb-name">{{ row.user_name }}</span>
          <span class="lb-score">{{ row.final_score }}</span>
          <span class="lb-salary">{{ salaryText(row.final_salary) }}</span>
          <span class="lb-grade">{{ row.grade || "-" }}</span>
        </li>
      </ul>
      <p v-if="!entries.length" class="lb-empty">暂无记录，完成一局谈判即可上榜</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchLeaderboard } from "../runtime/leaderboard_adapter";
import type { LeaderboardEntry } from "../runtime/leaderboard";

const router = useRouter();
const loading = ref(true);
const error = ref("");
const entered = ref(false);
const entries = ref<LeaderboardEntry[]>([]);

function medalFor(rank?: number) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return rank ?? "-";
}

function salaryText(value?: number) {
  if (!value) return "-";
  return `${Math.round(value / 1000)}K`;
}

function goBack() {
  router.push("/");
}

onMounted(async () => {
  document.body.classList.add("leaderboard-fullscreen-active");
  window.setTimeout(() => {
    entered.value = true;
  }, 40);
  try {
    entries.value = await fetchLeaderboard(50);
  } catch (e) {
    error.value = `加载排行榜失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  document.body.classList.remove("leaderboard-fullscreen-active");
});
</script>

<style scoped>
.lb-stage {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  flex-direction: column;
  padding: 16px 20px 20px;
  background: radial-gradient(ellipse 120% 80% at 50% 0%, #122a4a 0%, #060d18 55%, #03060c 100%);
  color: #fff;
  overflow: hidden;
}

.lb-flash {
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 40%, rgba(123, 237, 159, 0.35) 50%, transparent 60%);
  transform: translateX(-120%);
  opacity: 0;
  pointer-events: none;
}

.lb-scan {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(255, 255, 255, 0.03) 0,
    rgba(255, 255, 255, 0.03) 1px,
    transparent 1px,
    transparent 4px
  );
  opacity: 0;
  pointer-events: none;
}

.lb-grid {
  position: absolute;
  inset: -20%;
  background-image:
    linear-gradient(rgba(0, 194, 162, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 194, 162, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  transform: perspective(600px) rotateX(58deg) scale(1.2);
  opacity: 0;
  pointer-events: none;
}

.lb-stage.is-entered .lb-flash {
  animation: lb-flash 0.85s ease-out forwards;
}

.lb-stage.is-entered .lb-scan {
  animation: lb-scan 1.1s ease-out 0.1s forwards;
}

.lb-stage.is-entered .lb-grid {
  animation: lb-grid-in 1.2s ease-out 0.05s forwards;
}

.lb-top {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.lb-back {
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.lb-title-wrap {
  text-align: center;
}

.lb-kicker {
  margin: 0;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(123, 237, 159, 0.85);
}

.lb-title {
  margin: 2px 0 0;
  font-size: clamp(18px, 3.2vw, 26px);
  font-weight: 800;
}

.lb-top-spacer {
  width: 72px;
}

.lb-board {
  position: relative;
  z-index: 2;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(123, 237, 159, 0.22);
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(8px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.lb-board-head,
.lb-row {
  display: grid;
  grid-template-columns: 56px minmax(100px, 1.4fr) 72px 72px 56px;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
}

.lb-board-head {
  height: 40px;
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.55);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.lb-list {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  overflow: auto;
  flex: 1;
}

.lb-row {
  min-height: 48px;
  margin: 4px 8px;
  border-radius: 12px;
  font-size: 14px;
  opacity: 0;
  transform: translateX(28px);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.lb-stage.is-entered:not(.is-loading) .lb-row {
  animation: lb-row-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--row-delay);
}

.lb-row.is-top1 {
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.18), rgba(255, 255, 255, 0.05));
  border-color: rgba(255, 215, 0, 0.35);
}

.lb-row.is-top2 {
  background: linear-gradient(90deg, rgba(192, 192, 192, 0.16), rgba(255, 255, 255, 0.04));
}

.lb-row.is-top3 {
  background: linear-gradient(90deg, rgba(205, 127, 50, 0.16), rgba(255, 255, 255, 0.04));
}

.lb-name {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lb-score {
  font-weight: 800;
  color: #7bed9f;
  font-variant-numeric: tabular-nums;
}

.lb-salary,
.lb-grade {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-variant-numeric: tabular-nums;
}

.lb-loading,
.lb-error,
.lb-empty {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 40px 16px;
  color: rgba(255, 255, 255, 0.7);
}

.lb-error {
  color: #ff6b81;
}

@keyframes lb-flash {
  0% {
    opacity: 0;
    transform: translateX(-120%);
  }
  20% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translateX(120%);
  }
}

@keyframes lb-scan {
  from {
    opacity: 0.55;
  }
  to {
    opacity: 0.12;
  }
}

@keyframes lb-grid-in {
  from {
    opacity: 0;
    transform: perspective(600px) rotateX(68deg) scale(1.05) translateY(20px);
  }
  to {
    opacity: 0.35;
    transform: perspective(600px) rotateX(58deg) scale(1.2) translateY(0);
  }
}

@keyframes lb-row-in {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (orientation: portrait) and (max-width: 768px) {
  .lb-stage {
    padding: 12px 10px 14px;
  }

  .lb-board-head,
  .lb-row {
    grid-template-columns: 44px minmax(80px, 1.2fr) 56px 56px 44px;
    padding: 0 10px;
    font-size: 12px;
  }
}
</style>

<style>
body.leaderboard-fullscreen-active {
  overflow: hidden;
}

body.leaderboard-fullscreen-active .app-root {
  align-items: stretch;
  justify-content: stretch;
  padding: 0;
}
</style>
