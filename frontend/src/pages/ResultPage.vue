<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar blue">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>

      <div class="result-page">
        <div class="result-header">
          <div class="result-back" @click="$router.push('/')">‹</div>
          <div class="result-header-title">谈判结算</div>
          <div class="result-header-spacer"></div>
        </div>

        <div class="result-scroll">
          <div v-if="loading && !result" class="result-loading">正在结算...</div>

          <template v-else-if="result">
            <div class="result-hero">
              <div class="result-verdict" :class="hireVerdict === 'hired' ? 'is-hired' : 'is-rejected'">
                {{ hireVerdictLabel(hireVerdict) }}
              </div>
              <div class="result-medal">{{ result.medal || "🏁" }}</div>
              <div class="result-title">{{ result.title || gradeTitle }}</div>
              <div class="result-score">{{ result.final_score }} <span>分</span></div>
            </div>

            <div v-if="result.outcome_reason" class="result-card outcome-card">
              <div class="section-title no-gap">结果说明</div>
              <p class="outcome-text">{{ result.outcome_reason }}</p>
            </div>

            <div class="result-card">
              <div v-for="row in offerRows" :key="row.label" class="offer-row">
                <span class="offer-icon">{{ row.icon }}</span>
                <span class="offer-label">{{ row.label }}</span>
                <span class="offer-value">{{ row.value }}</span>
              </div>
            </div>

            <div class="section-title">得分明细</div>
            <div class="result-card score-card">
              <div v-for="bar in scoreBars" :key="bar.key" class="score-row">
                <div class="score-row-head">
                  <span>{{ bar.label }}</span>
                  <strong>{{ bar.value }}</strong>
                </div>
                <div class="score-track">
                  <div class="score-fill" :class="bar.tone" :style="{ width: `${bar.value}%` }"></div>
                </div>
              </div>

              <div class="stats-grid">
                <div class="stat-item">
                  <span class="stat-label">🪤 识破陷阱</span>
                  <span class="stat-value">
                    {{ stats?.traps_identified ?? 0 }}/{{ stats?.traps_total ?? 5 }}
                    <template v-if="trapLabelText">（{{ trapLabelText }}）</template>
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">📖 法条引用</span>
                  <span class="stat-value">{{ stats?.law_citation_count ?? 0 }} 次</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">🎯 策略种类</span>
                  <span class="stat-value">{{ stats?.strategy_count ?? 0 }} 种</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">❤️ 最终耐心</span>
                  <span class="stat-value">{{ stats?.final_patience ?? "-" }}</span>
                </div>
              </div>
            </div>

            <div class="tip-card">
              <span class="tip-icon">💡</span>
              <p>{{ result.review_tip }}</p>
            </div>

            <p v-if="result.summary" class="summary-text">{{ result.summary }}</p>

            <div v-if="missedClauses.length" class="result-card">
              <div class="section-title no-gap">漏谈条款</div>
              <div class="pill-list">
                <span v-for="item in missedClauses" :key="item" class="risk-pill missed">{{ item }}</span>
              </div>
            </div>

            <div v-if="riskNotes.length" class="result-card">
              <div class="section-title no-gap">风险提示</div>
              <div class="risk-list">
                <p v-for="(item, idx) in riskNotes" :key="`${idx}-${item}`" class="risk-item">
                  {{ item }}
                </p>
              </div>
            </div>

            <div v-if="transcript.length" class="transcript-section">
              <button type="button" class="transcript-toggle" @click="showTranscript = !showTranscript">
                💬 {{ showTranscript ? "收起对话记录" : "查看对话记录" }}
                <span class="transcript-count">（{{ transcript.length }} 条）</span>
              </button>
              <div v-show="showTranscript" class="transcript-panel">
                <div
                  v-for="(msg, idx) in transcript"
                  :key="`${msg.role}-${idx}-${msg.content.slice(0, 12)}`"
                  class="transcript-row"
                  :class="msg.role === 'hr' ? 'is-hr' : msg.role === 'player' ? 'is-me' : 'is-system'"
                >
                  <template v-if="msg.role === 'system'">
                    <div class="transcript-system">{{ msg.content }}</div>
                  </template>
                  <template v-else>
                    <img
                      class="transcript-avatar"
                      :src="msg.role === 'hr' ? bossAvatarUrl : playerAvatarUrl"
                      :alt="msg.role === 'hr' ? 'HR' : '我'"
                    />
                    <div class="transcript-bubble-wrap">
                      <div class="transcript-role">{{ msg.role === "hr" ? hrLabel : playerLabel }}</div>
                      <div class="transcript-bubble">{{ msg.content }}</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="result-loading">暂无结算数据</div>
        </div>

        <div class="result-actions">
          <button class="btn-primary" type="button" @click="goHome">↺ 再来一局</button>
          <button class="btn-secondary" type="button" @click="goHome">⌂ 返回首页</button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runtimeAdapter } from "../runtime";
import { saveLocalLeaderboardEntry } from "../runtime/leaderboard";
import type { SettleResultView } from "../runtime/battle_runtime_adapter";
import { bossAvatarUrl, playerAvatarUrl } from "../assets/avatars";
import {
  hireVerdictLabel,
  resolveTextHireVerdict,
  type HireVerdict,
} from "../utils/hire_verdict";
import {
  clearBattleTranscript,
  loadBattleTranscript,
  normalizeConversationHistory,
  type TranscriptMessage,
} from "../utils/battle_transcript";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const loading = ref(false);
const error = ref("");
const result = ref<SettleResultView | null>(null);
const hireVerdict = ref<HireVerdict>("hired");
const transcript = ref<TranscriptMessage[]>([]);
const showTranscript = ref(false);
const playerLabel = ref("我");
const hrLabel = ref("HR");

function persistTranscriptFromSession(raw: string | null) {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as {
      user_name?: string;
      conversation_history?: Array<{ role?: string; content?: string; round_index?: number }>;
      hr_personality_id?: string;
    };
    if (parsed.user_name?.trim()) {
      playerLabel.value = parsed.user_name.trim();
    }
    return normalizeConversationHistory(parsed.conversation_history);
  } catch {
    return [];
  }
}

function applyHrLabelFromStorage() {
  const raw = sessionStorage.getItem("hrPersonalityMeta");
  if (!raw) return;
  try {
    const meta = JSON.parse(raw) as { name?: string; emoji?: string };
    if (meta.name) hrLabel.value = `${meta.emoji || "😊"} ${meta.name}`;
  } catch {
    /* ignore */
  }
}

async function loadResult() {
  loading.value = true;
  error.value = "";
  let sessionPatience: number | null = null;
  let sessionUserName = "候选人";
  let historyFromCache: TranscriptMessage[] = loadBattleTranscript(sessionId.value);
  applyHrLabelFromStorage();
  const cachedSession = sessionStorage.getItem("currentSession");
  if (cachedSession) {
    try {
      const parsed = JSON.parse(cachedSession) as {
        hr_patience?: number;
        user_name?: string;
        conversation_history?: Array<{ role?: string; content?: string; round_index?: number }>;
      };
      if (typeof parsed.hr_patience === "number") sessionPatience = parsed.hr_patience;
      if (typeof parsed.user_name === "string" && parsed.user_name.trim()) {
        sessionUserName = parsed.user_name.trim();
        playerLabel.value = sessionUserName;
      }
      if (!historyFromCache.length) {
        historyFromCache = normalizeConversationHistory(parsed.conversation_history);
      }
    } catch {
      /* ignore */
    }
  }
  try {
    const data = await runtimeAdapter.settle(sessionId.value);
    result.value = data.result;
    hireVerdict.value = resolveTextHireVerdict(data.result, sessionPatience);
    const historyFromSettle = normalizeConversationHistory(data.conversation_history);
    transcript.value = historyFromCache.length
      ? historyFromCache
      : historyFromSettle.length
        ? historyFromSettle
        : persistTranscriptFromSession(cachedSession);
    saveLocalLeaderboardEntry({
      user_name: sessionUserName,
      final_score: data.result.final_score,
      final_salary: data.result.final_salary,
      grade: data.result.grade,
    });
    sessionStorage.removeItem("currentSession");
    sessionStorage.removeItem("hrOpening");
    sessionStorage.removeItem("hrPersonalityMeta");
  } catch (e) {
    error.value = `结算失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
}

function goHome() {
  clearBattleTranscript(sessionId.value);
  router.push("/");
}

const gradeTitle = computed(() => {
  if (!result.value) return "谈判结算";
  const score = result.value.final_score;
  if (score >= 95) return "谈判大师";
  if (score >= 85) return "老练求职者";
  if (score >= 70) return "稳健求职者";
  return "入门求职者";
});

const stats = computed(() => result.value?.stats);

const salaryText = computed(() => {
  if (!result.value) return "-";
  return `${Math.round(result.value.final_salary / 1000)}K / 月`;
});

const equityText = computed(() => {
  const ratio = result.value?.offer?.equity_ratio ?? 0;
  return `${(ratio * 100).toFixed(1)}%`;
});

const offerRows = computed(() => {
  const offer = result.value?.offer;
  return [
    { icon: "💰", label: "最终薪资", value: salaryText.value },
    { icon: "📈", label: "期权比例", value: equityText.value },
    { icon: "🏥", label: "社保基数", value: offer?.social_security_base || "待确认" },
    { icon: "🏠", label: "公积金", value: offer?.housing_fund_ratio || "未约定" },
    { icon: "⏰", label: "加班费", value: offer?.overtime_policy || "待确认" },
    { icon: "📋", label: "工时约定", value: offer?.working_hours_agreement || "未约定" },
  ];
});

const scoreBars = computed(() => {
  const b = result.value?.breakdown;
  return [
    { key: "dq", label: "成交质量", value: b?.dq ?? 0, tone: "tone-gold" },
    { key: "td", label: "陷阱识别", value: b?.td ?? 0, tone: "tone-orange" },
    { key: "wh", label: "工时目标", value: b?.wh ?? 0, tone: "tone-blue" },
    { key: "si", label: "社保匹配", value: b?.si ?? 0, tone: "tone-green" },
  ];
});

const trapLabelText = computed(() => {
  const labels = stats.value?.trap_labels || [];
  return labels.length ? labels.join("、") : "";
});

const riskNotes = computed(() => result.value?.risk_notes || []);
const missedClauses = computed(() => result.value?.missed_clauses || []);

if (!sessionId.value) {
  router.push("/");
} else {
  void loadResult();
}
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell {
  width: 100%;
  height: 100%;
  border-radius: 32px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a;
  background: #fff;
}
.phone-notch {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 24px;
  background: #1a1a1a;
  border-radius: 0 0 16px 16px;
  z-index: 10;
}
.status-bar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}
.status-bar.blue { background: #00c2a2; }

.result-page {
  background: #f6f6f6;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.result-header {
  background: #00c2a2;
  padding: 8px 16px 12px;
  color: #fff;
  display: flex;
  align-items: center;
}
.result-back { font-size: 18px; width: 28px; cursor: pointer; }
.result-header-title { flex: 1; text-align: center; font-size: 16px; font-weight: 600; }
.result-header-spacer { width: 28px; }

.result-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 16px 8px;
}

.result-loading {
  text-align: center;
  color: #999;
  font-size: 14px;
  padding: 40px 0;
}

.result-hero {
  text-align: center;
  padding: 8px 0 16px;
}
.result-verdict {
  font-size: 52px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: 0.12em;
  margin-bottom: 10px;
}
.result-verdict.is-hired {
  color: #00a88d;
  text-shadow: 0 6px 18px rgba(0, 168, 141, 0.22);
}
.result-verdict.is-rejected {
  color: #ff4757;
  text-shadow: 0 6px 18px rgba(255, 71, 87, 0.18);
}
.result-medal { font-size: 40px; line-height: 1; }
.result-title {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #e6a017;
}
.result-score {
  margin-top: 4px;
  font-size: 36px;
  font-weight: 800;
  color: #e6a017;
  line-height: 1.1;
}
.result-score span { font-size: 16px; font-weight: 600; }

.result-card {
  background: #fff;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  margin-bottom: 12px;
}

.offer-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f3f3f3;
  font-size: 13px;
}
.offer-row:last-child { border-bottom: none; }
.offer-icon { width: 20px; text-align: center; flex-shrink: 0; }
.offer-label { flex: 1; color: #666; }
.offer-value { color: #1a1a1a; font-weight: 600; text-align: right; }

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: #333;
  margin: 4px 0 8px;
}

.section-title.no-gap {
  margin: 0 0 8px;
}

.outcome-card {
  margin-bottom: 12px;
}

.outcome-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #333;
}

.score-card { padding-bottom: 10px; }
.score-row { margin-bottom: 12px; }
.score-row-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
.score-row-head strong { color: #333; font-size: 13px; }
.score-track {
  height: 8px;
  background: #ececec;
  border-radius: 4px;
  overflow: hidden;
}
.score-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.tone-gold { background: linear-gradient(90deg, #ffd56b, #ffb347); }
.tone-orange { background: linear-gradient(90deg, #ffb347, #ff8c42); }
.tone-blue { background: linear-gradient(90deg, #6eb5ff, #4a90e2); }
.tone-green { background: linear-gradient(90deg, #7dcea0, #00c2a2); }

.stats-grid {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
  display: grid;
  gap: 8px;
}
.stat-item { font-size: 12px; line-height: 1.5; }
.stat-label { color: #888; margin-right: 6px; }
.stat-value { color: #333; font-weight: 600; }

.tip-card {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.tip-icon { flex-shrink: 0; font-size: 16px; }
.tip-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #614700;
}

.summary-text {
  font-size: 12px;
  line-height: 1.6;
  color: #666;
  margin: 0 0 8px;
  padding: 0 2px;
}

.pill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.risk-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.risk-pill.missed {
  color: #9c3b00;
  background: #fff2e8;
  border: 1px solid #ffd1b3;
}

.risk-list {
  display: grid;
  gap: 8px;
}

.risk-item {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #5b3a00;
  background: #fff8e6;
  border: 1px solid #ffe7a3;
  border-radius: 10px;
  padding: 9px 10px;
}

.result-actions {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px 16px 18px;
  background: #f6f6f6;
  border-top: 1px solid #ececec;
}
.btn-primary,
.btn-secondary {
  border: none;
  border-radius: 24px;
  padding: 12px 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary {
  background: linear-gradient(135deg, #ff6b81, #ff4757);
  color: #fff;
}
.btn-secondary {
  background: #fff;
  color: #333;
  border: 1px solid #ddd;
}
.error {
  text-align: center;
  color: #ff4757;
  font-size: 12px;
  padding: 0 16px 8px;
}

.transcript-section {
  margin: 8px 0 12px;
}

.transcript-toggle {
  width: 100%;
  border: 1px solid #dce9e6;
  background: #fff;
  color: #007a68;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}

.transcript-count {
  font-weight: 500;
  color: #888;
}

.transcript-panel {
  margin-top: 10px;
  max-height: 240px;
  overflow-y: auto;
  padding: 10px;
  border-radius: 12px;
  background: #f0f4f3;
  border: 1px solid #e3ebe8;
}

.transcript-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.transcript-row.is-me {
  flex-direction: row-reverse;
}

.transcript-row.is-system {
  justify-content: center;
}

.transcript-system {
  font-size: 11px;
  color: #888;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 4px 10px;
  max-width: 92%;
  text-align: center;
  line-height: 1.45;
}

.transcript-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.transcript-bubble-wrap {
  max-width: 78%;
}

.transcript-row.is-me .transcript-bubble-wrap {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
}

.transcript-role {
  font-size: 10px;
  color: #888;
  margin-bottom: 2px;
}

.transcript-bubble {
  background: #fff;
  border-radius: 12px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  color: #333;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  word-break: break-word;
}

.transcript-row.is-me .transcript-bubble {
  background: #dcf8c6;
}

.transcript-row.is-hr .transcript-bubble {
  background: #fff;
}
</style>
