<template>
  <section class="cg-result">
    <div class="cg-result-card" v-if="result">
      <div class="cg-verdict" :class="hireVerdict === 'hired' ? 'is-hired' : 'is-rejected'">
        {{ hireVerdictLabel(hireVerdict) }}
      </div>
      <div class="cg-medal">{{ result.medal }}</div>
      <h1>{{ result.title }}</h1>
      <p class="cg-score">{{ result.final_score }} <span>分</span></p>
      <p class="cg-outcome">{{ outcomeLabel }}</p>

      <div class="cg-stats-grid">
        <div v-for="row in statRows" :key="row.label" class="cg-stat-row">
          <span>{{ row.icon }} {{ row.label }}</span>
          <strong>{{ row.value }}</strong>
        </div>
      </div>

      <div class="cg-breakdown">
        <div v-for="bar in bars" :key="bar.key" class="cg-bar-row">
          <div class="cg-bar-head"><span>{{ bar.label }}</span><strong>{{ bar.value }}</strong></div>
          <div class="cg-bar-track"><div class="cg-bar-fill" :style="{ width: `${bar.value}%` }" /></div>
        </div>
      </div>

      <p class="cg-tip">{{ result.review_tip }}</p>

      <div class="cg-actions">
        <button type="button" class="cg-btn ghost" @click="$router.push('/card-game')">再来一局</button>
        <button type="button" class="cg-btn primary" @click="$router.push('/')">返回首页</button>
      </div>
    </div>
    <p v-else class="cg-empty">暂无结算数据</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { CardGameSettleResult } from "../card-game/types";
import {
  hireVerdictLabel,
  resolveCardHireVerdict,
  type HireVerdict,
} from "../utils/hire_verdict";

const result = ref<CardGameSettleResult | null>(null);
const hireVerdict = ref<HireVerdict>("hired");

const outcomeLabel = computed(() => {
  const o = result.value?.outcome;
  if (o === "collapsed") return "💀 谈崩";
  if (o === "high_deal") return "🏆 高位成交";
  if (o === "low_deal") return "⚠️ 低满成交";
  if (o === "forced_deal") return "📋 强制结算";
  return "🤝 成交";
});

const statRows = computed(() => {
  const s = result.value?.stats;
  if (!s) return [];
  return [
    { icon: "😊", label: "满意度", value: s.satisfaction.toFixed(1) },
    { icon: "💰", label: "薪资", value: `${s.salary_k.toFixed(1)}K` },
    { icon: "⏰", label: "工时", value: s.work_hours.toFixed(1) },
    { icon: "🛡️", label: "保障", value: s.security.toFixed(1) },
  ];
});

const bars = computed(() => {
  const b = result.value?.breakdown;
  if (!b) return [];
  return [
    { key: "salary", label: "薪资得分", value: b.salary },
    { key: "wh", label: "工时得分", value: b.work_hours },
    { key: "sec", label: "保障得分", value: b.security },
    { key: "sat", label: "满意度得分", value: b.satisfaction },
  ];
});

onMounted(() => {
  const raw = sessionStorage.getItem("cardGameResult");
  if (!raw) return;
  const parsed = JSON.parse(raw) as CardGameSettleResult;
  result.value = parsed;
  hireVerdict.value = resolveCardHireVerdict(parsed);
});
</script>

<style scoped>
.cg-result {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(160deg, #0a1628, #091018);
  color: #fff;
}

.cg-result-card {
  width: min(520px, 100%);
  padding: 28px 22px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  text-align: center;
}

.cg-verdict {
  font-size: 56px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: 0.14em;
  margin-bottom: 12px;
}
.cg-verdict.is-hired {
  color: #7bed9f;
  text-shadow: 0 8px 24px rgba(123, 237, 159, 0.25);
}
.cg-verdict.is-rejected {
  color: #ff6b81;
  text-shadow: 0 8px 24px rgba(255, 107, 129, 0.22);
}

.cg-medal { font-size: 48px; }
h1 { margin: 8px 0; font-size: 24px; }
.cg-score { margin: 0; font-size: 42px; font-weight: 800; color: #7bed9f; }
.cg-score span { font-size: 18px; }
.cg-outcome { color: rgba(255, 255, 255, 0.7); }

.cg-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin: 18px 0;
  text-align: left;
}

.cg-stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.2);
  font-size: 13px;
}

.cg-breakdown { text-align: left; margin-bottom: 14px; }
.cg-bar-row { margin-bottom: 8px; }
.cg-bar-head { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
.cg-bar-track { height: 6px; border-radius: 999px; background: rgba(255, 255, 255, 0.12); overflow: hidden; }
.cg-bar-fill { height: 100%; background: linear-gradient(90deg, #00c2a2, #7bed9f); }

.cg-tip {
  font-size: 13px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.72);
  text-align: left;
}

.cg-actions { display: flex; gap: 10px; margin-top: 18px; }
.cg-btn {
  flex: 1;
  height: 40px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}
.cg-btn.primary { background: #00c2a2; color: #fff; }
.cg-btn.ghost { background: rgba(255, 255, 255, 0.08); color: #fff; }
.cg-empty { color: rgba(255, 255, 255, 0.6); }
</style>
