<template>
  <section
    class="battle-stage"
    :class="{
      'is-expanded': isExpanded,
      'is-morphing': isMorphing,
      'is-card-prelude': cardPreludePlaying,
    }"
  >
    <div class="expand-backdrop" aria-hidden="true">
      <div class="expand-grid" />
      <div class="expand-glow" />
    </div>

    <div
      class="battle-viewport"
      :class="{ 'is-expanded': isExpanded }"
      :style="{ '--battle-scale': uiScale }"
    >
      <div class="expand-flash" aria-hidden="true" />

      <div v-if="showBgmPanel" class="bgm-panel" @click.self="showBgmPanel = false">
        <div class="bgm-panel-card">
          <div class="bgm-panel-title">
            <span>🎵 BGM 音量</span>
            <button type="button" class="bgm-panel-close" @click="showBgmPanel = false">×</button>
          </div>
          <div class="bgm-panel-row">
            <input v-model.number="bgmVolume" class="bgm-panel-range" type="range" min="0" max="1" step="0.01" />
            <span class="bgm-panel-val">{{ Math.round(bgmVolume * 100) }}%</span>
          </div>
        </div>
      </div>

      <div v-if="isExpanded" class="battle-top-bar">
        <button type="button" class="battle-top-back" title="返回" @click="$router.push('/')">‹</button>
        <div v-if="cardSession" class="battle-top-round">
          第 {{ cardSession.round_index }} / {{ cardSession.max_round }} 轮
        </div>
        <BattleTurnCountdown
          class="battle-top-countdown"
          :progress-percent="turnProgressPercent"
          :remaining-seconds="turnRemainingSeconds"
          :is-urgent="turnIsUrgent"
          :is-running="turnIsRunning"
        />
        <button
          v-if="cardSession"
          type="button"
          class="battle-top-accept"
          :disabled="!canAccept || cardBusy"
          :title="acceptHint"
          @click="onAcceptOffer"
        >
          🤝 接受 Offer
        </button>
        <button type="button" class="battle-top-bgm" title="BGM 音量" @click="showBgmPanel = true">🔊</button>
        <button
          type="button"
          class="battle-top-expand"
          title="退出全屏"
          aria-label="退出全屏"
          @click="toggleExpand"
        >
          <span class="expand-icon contracted">
            <span /><span /><span /><span />
          </span>
        </button>
      </div>

      <BattleCardLandscape
        v-if="isExpanded"
        :card-session="cardSession"
        :display-hr-text="displayHrText"
        :last-player-card-text="lastPlayerCardText"
        :card-waiting="cardWaiting"
        :card-busy="cardBusy"
        :card-dialog-loading="cardDialogLoading"
        :card-error="cardError"
        :last-delta-hint="lastDeltaHint"
        :selected-card="selectedCard"
        :flash-delta="flashDelta"
        :show-delta="showDelta"
        :card-hr-meter="cardHrMeter"
        :card-player-meter="cardPlayerMeter"
        :hr-mood="hrMood"
        :player-mood="playerMood"
        :hr-mood-meta="hrMoodMeta"
        :player-mood-meta="playerMoodMeta"
        :hr-role-label="hrRoleLabel"
        :player-role-label="playerDisplayName"
        :ui-scale="uiScale"
        :countdown-running="turnIsRunning"
        :turn-progress-percent="turnProgressPercent"
        :turn-remaining-seconds="turnRemainingSeconds"
        @select-card="onSelectCard"
      />

      <div v-show="!isExpanded" class="battle-center">
        <div v-if="cardPreludePlaying" class="card-prelude-overlay" aria-hidden="true">
          <div class="card-prelude-ring" />
          <p class="card-prelude-caption">决战载入中…</p>
        </div>

        <div class="phone-shell" :class="{ 'is-expanded': isExpanded }">
        <div class="phone-notch" />
        <div class="status-bar blue">
          <span>9:41</span>
          <span>📶 🔋</span>
        </div>
        <div class="boss-chat">
        <div class="boss-header">
          <div class="boss-header-top">
            <div class="boss-back" @click="$router.push('/')">‹</div>
            <div class="boss-header-center">
              <div class="boss-header-name">{{ waitingHr ? "对方正在输入中..." : hrHeaderName }}</div>
              <div v-if="!waitingHr && hrPersonalityTagline" class="boss-header-tagline">{{ hrPersonalityTagline }}</div>
            </div>
            <button type="button" class="boss-bgm-btn" title="BGM 音量" @click="showBgmPanel = true">🔊</button>
            <button
              v-if="showExpandButton || isExpanded"
              type="button"
              class="boss-expand-btn"
              :title="expandButtonTitle"
              :aria-label="expandButtonTitle"
              @click="toggleExpand"
            >
              <span class="expand-icon" :class="{ contracted: isExpanded }">
                <span /><span /><span /><span />
              </span>
            </button>
          </div>
        </div>

        <div class="boss-company-card">
          <img class="boss-company-logo" :src="bossAvatarUrl" alt="HR" />
          <div class="boss-company-info">
            <div class="boss-company-name">{{ session?.scene_context?.meta?.scene_name || "灵创科技" }}</div>
            <div class="boss-company-meta">A轮 · AI/大模型 · 50-100人</div>
          </div>
          <div class="boss-company-salary">{{ salaryText }}</div>
        </div>

        <div class="boss-sat-bar-wrap">
          <div class="boss-sat-label">😊 满意度</div>
          <div class="boss-sat-track">
            <div class="boss-sat-fill" :style="{ width: `${session?.hr_patience ?? 0}%` }"></div>
          </div>
          <div class="boss-sat-val">{{ session?.hr_patience ?? "-" }}</div>
        </div>
        <p v-if="cardModeThresholdHint && !isExpanded" class="card-mode-hint" :class="{ urgent: cardModeHintUrgent }">
          {{ cardModeThresholdHint }}
        </p>

        <div class="boss-hud-row">
          <div class="boss-hud-item" title="薪资越多越好，是谈判的核心目标">
            <span class="boss-hud-icon">💰</span>
            <span class="boss-hud-label">当前薪资</span>
            <span class="boss-hud-val">{{ salaryHudText }}</span>
          </div>
          <div class="boss-hud-item" title="日工时、周工时、加班费写入合同的程度，越高代表条款越有利">
            <span class="boss-hud-icon">⏱️</span>
            <span class="boss-hud-label">当前工时</span>
            <span class="boss-hud-val">{{ workHoursText }}</span>
          </div>
          <div class="boss-hud-item" title="五险一金基数+比例+合同明确度，越高代表保障越到位">
            <span class="boss-hud-icon">🛡️</span>
            <span class="boss-hud-label">当前保障</span>
            <span class="boss-hud-val">{{ securityText }}</span>
          </div>
        </div>

        <div ref="chatAreaRef" class="boss-chat-area">
          <div class="boss-time-divider">今天 {{ nowTime }}</div>
          <template v-for="(m, idx) in messages" :key="idx">
            <div v-if="m.type === 'system'" class="boss-system-msg">{{ m.text }}</div>
            <div v-else class="boss-msg" :class="m.role === 'hr' ? 'hr' : 'me'">
              <img
                class="boss-msg-avatar"
                :src="m.role === 'hr' ? bossAvatarUrl : playerAvatarUrl"
                :alt="m.role === 'hr' ? 'HR' : '我'"
              />
              <div class="boss-msg-content">
                <div v-if="m.role === 'hr'" class="boss-msg-role">{{ hrRoleLabel }}</div>
                <div class="boss-msg-bubble">{{ m.text }}</div>
              </div>
            </div>
          </template>
          <div v-if="waitingHr" class="boss-msg hr">
            <img class="boss-msg-avatar" :src="bossAvatarUrl" alt="HR" />
            <div class="boss-msg-content">
              <div class="boss-msg-role">{{ hrRoleLabel }}</div>
              <div class="boss-msg-bubble boss-typing-bubble">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="boss-input-area">
          <input
            v-model="customText"
            class="boss-input-field"
            placeholder="请输入你的回复（按回车发送）"
            :disabled="chatInputLocked"
            @keydown.enter="sendCustomText"
          />
          <button class="boss-input-send" @click="sendCustomText" :disabled="chatInputLocked || !customText.trim()">
            {{ loading ? "…" : "↑" }}
          </button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
        </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { bossAvatarUrl, playerAvatarUrl } from "../assets/avatars";
import BattleCardLandscape from "../components/battle/BattleCardLandscape.vue";
import BattleTurnCountdown from "../components/battle/BattleTurnCountdown.vue";
import type { BubbleEntrance } from "../types/bubbleEntrance";
import { normalizeBubbleEntrance } from "../types/bubbleEntrance";
import { syncHrPersonalityMeta, type HrPersonalityMeta } from "../constants/hr_personalities";
import { useBattleCardGame } from "../composables/useBattleCardGame";
import { useCardModeTrigger } from "../composables/useCardModeTrigger";
import { playCardModePrelude } from "../composables/useCardModePrelude";
import { useBattleMood } from "../composables/useBattleMood";
import { useBattleTurnCountdown } from "../composables/useBattleTurnCountdown";
import { useBattleViewport } from "../composables/useBattleViewport";
import { runtimeAdapter } from "../runtime";
import type { SessionState } from "../runtime/battle_runtime_adapter";

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));
const cardPreludePlaying = ref(false);
const cardPreludeStarted = ref(false);
const loading = ref(false);
const error = ref("");
const customText = ref("");
const waitingHr = ref(false);

const chatInputLocked = computed(() => loading.value || cardPreludePlaying.value || waitingHr.value);
const session = ref<SessionState | null>(null);
type BattleMessage = {
  id: number;
  role: "hr" | "me" | "system";
  text: string;
  type?: "system";
  bubbleEntrance?: BubbleEntrance;
};

let messageSeq = 0;
let streamingHrMessageId: number | null = null;

function pushMessage(msg: Omit<BattleMessage, "id">) {
  messages.value.push({ id: ++messageSeq, ...msg });
}

function appendStreamingHrToken(chunk: string) {
  if (!chunk) return;
  if (streamingHrMessageId === null) {
    pushMessage({ role: "hr", text: chunk, bubbleEntrance: "fade" });
    streamingHrMessageId = messageSeq;
    waitingHr.value = false;
    return;
  }
  const msg = messages.value.find((item) => item.id === streamingHrMessageId);
  if (msg) msg.text += chunk;
}

function finalizeStreamingHrMessage(finalText: string, bubbleEntrance?: BubbleEntrance) {
  if (streamingHrMessageId === null) {
    pushMessage({ role: "hr", text: finalText, bubbleEntrance: bubbleEntrance ?? "fade" });
  } else {
    const msg = messages.value.find((item) => item.id === streamingHrMessageId);
    if (msg) {
      msg.text = finalText;
      if (bubbleEntrance) msg.bubbleEntrance = bubbleEntrance;
    }
  }
  streamingHrMessageId = null;
}

const messages = ref<BattleMessage[]>([]);
const chatAreaRef = ref<HTMLElement | null>(null);
const { isExpanded, isMorphing, uiScale, toggleExpand, expand } = useBattleViewport();
const { hrMood, playerMood, hrMoodMeta, playerMoodMeta } = useBattleMood(session);
const {
  progressPercent: turnProgressPercent,
  remainingSeconds: turnRemainingSeconds,
  isUrgent: turnIsUrgent,
  isRunning: turnIsRunning,
  reset: resetTurnCountdown,
  pause: pauseTurnCountdown,
} = useBattleTurnCountdown(10);
const nowTime = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

const showBgmPanel = ref(false);
const bgmVolume = ref(0.6);
try {
  const raw = localStorage.getItem("bgmVolume");
  const value = raw == null ? NaN : Number(raw);
  if (Number.isFinite(value)) {
    bgmVolume.value = Math.max(0, Math.min(1, value));
  }
} catch {}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const normalBgmUrl = `${apiBaseUrl}/resources/music&effect/普通阶段.mp3`;
const cardBgmUrl = `${apiBaseUrl}/resources/music&effect/打牌阶段.mp3`;

type BgmState = { audio: HTMLAudioElement | null; fadeTimer: number | null; targetVolume: number };
const normalBgm = ref<BgmState>({ audio: null, fadeTimer: null, targetVolume: bgmVolume.value });
const cardBgm = ref<BgmState>({ audio: null, fadeTimer: null, targetVolume: bgmVolume.value });
let bgmUnlocked = false;

// #region debug-point bgm-telemetry
const DEBUG_SERVER_URL = "http://127.0.0.1:7777/event";
function dbg(event: string, payload: Record<string, unknown> = {}) {
  try {
    void fetch(DEBUG_SERVER_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        sessionId: "bgm-not-playing",
        runId: "pre",
        hypothesisId: "H?",
        event,
        ts: Date.now(),
        payload,
      }),
      keepalive: true,
    });
  } catch {}
}
// #endregion debug-point bgm-telemetry

function clearFade(state: BgmState) {
  if (state.fadeTimer != null) {
    window.clearInterval(state.fadeTimer);
    state.fadeTimer = null;
  }
}

async function ensureAudio(state: BgmState, url: string) {
  if (state.audio) return state.audio;
  const audio = new Audio(encodeURI(url));
  audio.loop = true;
  audio.preload = "auto";
  audio.volume = 0;
  state.audio = audio;
// #region debug-point bgm-audio-events
  dbg("bgm_audio_created", { url });
  audio.addEventListener("playing", () => dbg("bgm_playing", { url, volume: audio.volume }), { passive: true });
  audio.addEventListener("pause", () => dbg("bgm_pause", { url, volume: audio.volume }), { passive: true });
  audio.addEventListener("canplaythrough", () => dbg("bgm_canplaythrough", { url, rs: audio.readyState }), { passive: true });
  audio.addEventListener(
    "error",
    () =>
      dbg("bgm_error", {
        url,
        code: audio.error?.code ?? null,
        message: audio.error?.message ?? null,
        rs: audio.readyState,
      }),
    { passive: true },
  );
// #endregion debug-point bgm-audio-events
  return audio;
}

function fadeVolume(state: BgmState, target: number, ms: number) {
  const audio = state.audio;
  if (!audio) return;
  clearFade(state);
  const safeTarget = Math.max(0, Math.min(1, target));
  const start = audio.volume;
  const t0 = performance.now();
  const tick = () => {
    const t = (performance.now() - t0) / ms;
    const k = t >= 1 ? 1 : t;
    audio.volume = start + (safeTarget - start) * k;
    if (k >= 1) clearFade(state);
  };
  state.fadeTimer = window.setInterval(tick, 30);
  tick();
}

function applyBgmVolumeTargets() {
  normalBgm.value.targetVolume = bgmVolume.value;
  cardBgm.value.targetVolume = bgmVolume.value;
  try {
    localStorage.setItem("bgmVolume", String(bgmVolume.value));
  } catch {}

  const normal = normalBgm.value.audio;
  if (normal && !normal.paused && normal.volume > 0.001) {
    fadeVolume(normalBgm.value, normalBgm.value.targetVolume, 180);
  }
  const card = cardBgm.value.audio;
  if (card && !card.paused && card.volume > 0.001) {
    fadeVolume(cardBgm.value, cardBgm.value.targetVolume, 180);
  }
}

watch(bgmVolume, (v) => {
  const safe = Math.max(0, Math.min(1, Number(v)));
  if (safe !== bgmVolume.value) {
    bgmVolume.value = safe;
    return;
  }
  applyBgmVolumeTargets();
});

applyBgmVolumeTargets();

async function playBgm(state: BgmState, url: string) {
  if (!bgmUnlocked) return;
  const audio = await ensureAudio(state, url);
// #region debug-point bgm-play-attempt
  dbg("bgm_play_attempt", {
    url,
    paused: audio.paused,
    muted: audio.muted,
    volume: audio.volume,
    target: state.targetVolume,
    unlocked: bgmUnlocked,
    expanded: isExpanded.value,
  });
// #endregion debug-point bgm-play-attempt
  try {
    if (audio.paused) await audio.play();
    fadeVolume(state, state.targetVolume, 650);
// #region debug-point bgm-play-ok
    dbg("bgm_play_ok", { url, paused: audio.paused, volume: audio.volume, target: state.targetVolume });
// #endregion debug-point bgm-play-ok
  } catch {}
}

function stopBgm(state: BgmState) {
  const audio = state.audio;
  if (!audio) return;
// #region debug-point bgm-stop
  dbg("bgm_stop", { volume: audio.volume, paused: audio.paused });
// #endregion debug-point bgm-stop
  fadeVolume(state, 0, 350);
  window.setTimeout(() => {
    if (audio.volume <= 0.02) {
      audio.pause();
      audio.currentTime = 0;
    }
  }, 420);
}

function unlockBgm() {
  if (bgmUnlocked) return;
  bgmUnlocked = true;
// #region debug-point bgm-unlock
  dbg("bgm_unlocked", { expanded: isExpanded.value, normalBgmUrl, cardBgmUrl });
// #endregion debug-point bgm-unlock
  if (!isExpanded.value) {
    playBgm(normalBgm.value, normalBgmUrl);
  }
  window.removeEventListener("pointerdown", unlockBgm);
  window.removeEventListener("keydown", unlockBgm);
}

const hrPersonalityMeta = ref<HrPersonalityMeta | null>(null);

const playerDisplayName = computed(() => {
  const name = (session.value?.user_name || "").trim();
  return name && name !== "候选人" ? `${name} · 候选人` : "候选人";
});

const hrRoleLabel = computed(() => {
  const meta = hrPersonalityMeta.value;
  if (meta?.name) return `${meta.emoji || "😊"} ${meta.name} · HR`;
  return "HR";
});

const hrHeaderName = computed(() => {
  const meta = hrPersonalityMeta.value;
  if (meta?.name) return `${meta.name} · HR负责人`;
  return "HR负责人";
});

const hrPersonalityTagline = computed(() => hrPersonalityMeta.value?.tagline || "");

const expandButtonTitle = computed(() => (isExpanded.value ? "退出全屏" : "进入卡牌阶段"));

const {
  cardSession,
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
} = useBattleCardGame(
  () => sessionId.value,
  () => session.value,
  { reset: resetTurnCountdown, pause: pauseTurnCountdown },
  (cardId) => router.push(`/card-game/result/${cardId}`),
);

const { cardPhaseUnlocked, markUnlocked, evaluate: evaluateCardTrigger } = useCardModeTrigger(
  () => sessionId.value,
);

const showExpandButton = computed(() => cardPhaseUnlocked.value);

/** 正式版：满意度触发后才显示展开入口 */
const cardModeThresholdHint = computed(() => {
  if (cardPhaseUnlocked.value || isExpanded.value || cardPreludePlaying.value) return "";
  return evaluateCardTrigger(session.value).hint;
});

const cardModeHintUrgent = computed(() => evaluateCardTrigger(session.value).approaching);

async function tryEnterCardMode(options?: { autoExpand?: boolean }) {
  if (cardPreludeStarted.value || cardPhaseUnlocked.value) return false;

  const check = evaluateCardTrigger(session.value);
  if (!check.shouldTrigger) return false;

  cardPreludeStarted.value = true;
  cardPreludePlaying.value = true;
  pauseTurnCountdown();

  try {
    await playCardModePrelude(
      (text) => pushMessage({ role: "system", text, type: "system" }),
      () => scrollChatToBottom(),
    );

    markUnlocked();
    cardPreludePlaying.value = false;

    const shouldAutoExpand = options?.autoExpand ?? true;
    if (shouldAutoExpand && !isExpanded.value) {
      await nextTick();
      expand();
    }
    return true;
  } catch (e) {
    cardPreludePlaying.value = false;
    error.value = `进入卡牌阶段失败：${String(e)}`;
    return false;
  }
}

const cachedSession = sessionStorage.getItem("currentSession");
if (cachedSession) {
  session.value = JSON.parse(cachedSession) as SessionState;
  hrPersonalityMeta.value = syncHrPersonalityMeta(session.value);
}
const opening = sessionStorage.getItem("hrOpening");
if (opening) {
  pushMessage({ role: "hr", text: opening, bubbleEntrance: "fade" });
}

const latestPlayerSpeech = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    const msg = messages.value[i];
    if (msg.role === "me") return msg;
  }
  return null;
});

function scrollChatToBottom() {
  nextTick(() => {
    const el = chatAreaRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

watch(
  () => [messages.value.length, waitingHr.value],
  () => scrollChatToBottom(),
);

watch(isExpanded, async (expanded) => {
  scrollChatToBottom();
  if (expanded) {
    await enterCardPhase();
    stopBgm(normalBgm.value);
    await playBgm(cardBgm.value, cardBgmUrl);
  } else {
    leaveCardPhase();
    stopBgm(cardBgm.value);
    await playBgm(normalBgm.value, normalBgmUrl);
  }
});

watch(
  () => turnRemainingSeconds.value,
  (sec, prev) => {
    if (isExpanded.value && prev > 0 && sec <= 0) {
      onCardCountdownExpire();
    }
  },
);

onMounted(async () => {
  window.addEventListener("pointerdown", unlockBgm, { once: true });
  window.addEventListener("keydown", unlockBgm, { once: true });
  scrollChatToBottom();
  if (cardPhaseUnlocked.value) {
    if (!isExpanded.value) expand();
    if (isExpanded.value) await enterCardPhase();
    if (isExpanded.value) await playBgm(cardBgm.value, cardBgmUrl);
    return;
  }
  await tryEnterCardMode();
  if (isExpanded.value) await enterCardPhase();
  if (isExpanded.value) await playBgm(cardBgm.value, cardBgmUrl);
});

onUnmounted(() => {
  stopBgm(normalBgm.value);
  stopBgm(cardBgm.value);
  clearFade(normalBgm.value);
  clearFade(cardBgm.value);
});

async function sendCustomText() {
  if (chatInputLocked.value) return;
  await runTurn({ player_text: customText.value.trim() });
  customText.value = "";
}

async function runTurn(payload: {
  strategy?: string;
  player_text?: string;
  displayText?: string;
}) {
  const text = payload.displayText || payload.player_text?.trim();
  if (text) {
    pushMessage({ role: "me", text, bubbleEntrance: "slide" });
  }
  loading.value = true;
  waitingHr.value = true;
  pauseTurnCountdown();
  error.value = "";
  try {
    streamingHrMessageId = null;
    const data = await runtimeAdapter.textTurn(
      sessionId.value,
      {
        strategy: payload.strategy as "strong_push" | "probe" | "concede" | "counter_pressure" | undefined,
        player_text: payload.player_text,
      },
      {
        onToken(chunk) {
          appendStreamingHrToken(chunk);
          void scrollChatToBottom();
        },
      },
    );
    if (data.result.player_bubble_entrance && latestPlayerSpeech.value) {
      latestPlayerSpeech.value.bubbleEntrance = normalizeBubbleEntrance(
        data.result.player_bubble_entrance,
        latestPlayerSpeech.value.bubbleEntrance ?? "slide",
      );
    }
    finalizeStreamingHrMessage(
      data.result.hr_reply,
      normalizeBubbleEntrance(data.result.hr_bubble_entrance, "fade"),
    );
    if (data.flow?.reason) {
      pushMessage({ role: "system", text: `💡 ${data.flow.reason}`, type: "system" });
    }
    session.value = data.session;
    hrPersonalityMeta.value = syncHrPersonalityMeta(data.session);
    sessionStorage.setItem("currentSession", JSON.stringify(data.session));

    const gameEnding =
      data.flow?.next_phase === "end" || data.result.is_game_over || data.session.status === "settled";

    if (!gameEnding) {
      await tryEnterCardMode();
    }

    if (gameEnding) {
      router.push(`/result/${sessionId.value}`);
    }
  } catch (e) {
    streamingHrMessageId = null;
    error.value = `回合请求失败：${String(e)}`;
  } finally {
    waitingHr.value = false;
    loading.value = false;
  }
}

function formatMaybeFloat(value: number) {
  if (!Number.isFinite(value)) return "-";
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 1e-6) return String(rounded);
  return value.toFixed(1);
}

const salaryText = computed(() => {
  const offer = session.value?.current_salary_offer;
  if (!offer) return "15K";
  return `${Math.round(Number(offer) / 1000)}K`;
});

const salaryHudText = computed(() => {
  const k = cardSession.value?.stats?.salary_k;
  if (k == null) return salaryText.value;
  return `${k.toFixed(1)}K`;
});

const workHoursText = computed(() => {
  const value = cardSession.value?.stats?.work_hours;
  if (value == null) return "-";
  return formatMaybeFloat(value);
});

const securityText = computed(() => {
  const value = cardSession.value?.stats?.security;
  if (value == null) return "-";
  return formatMaybeFloat(value);
});
</script>

<style scoped>
.battle-stage {
  --morph-ease: cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.battle-stage.is-expanded {
  position: fixed;
  inset: 0;
  z-index: 2000;
}

.expand-backdrop {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.battle-stage.is-expanded .expand-backdrop {
  opacity: 1;
}

.expand-grid {
  position: absolute;
  inset: -50%;
  background-image:
    linear-gradient(rgba(0, 194, 162, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 194, 162, 0.07) 1px, transparent 1px);
  background-size: 48px 48px;
  animation: gridDrift 18s linear infinite;
}

.expand-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(0, 194, 162, 0.22), transparent 60%),
    radial-gradient(ellipse 60% 50% at 100% 100%, rgba(250, 107, 61, 0.12), transparent 55%),
    linear-gradient(160deg, #0a1628 0%, #0d2137 45%, #091018 100%);
}

.battle-viewport {
  --battle-scale: 1;
  width: 375px;
  height: 700px;
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  transition:
    width 0.68s var(--morph-ease),
    height 0.68s var(--morph-ease);
}

.battle-viewport.is-expanded {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-columns: minmax(0, 1fr);
  align-items: stretch;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.battle-viewport.is-expanded :deep(.battle-card-landscape) {
  min-height: 0;
}

.battle-top-bar {
  grid-column: 1 / -1;
  grid-row: 1;
  z-index: 12;
  display: grid;
  grid-template-columns: auto auto 1fr auto auto auto;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid rgba(255, 71, 87, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
}

.battle-top-round {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  color: #0a1628;
}

.battle-top-accept {
  height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 10px;
  background: rgba(0, 194, 162, 0.18);
  color: #7bed9f;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.battle-top-accept:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.battle-top-back,
.battle-top-bgm,
.battle-top-expand {
  align-self: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: rgba(0, 194, 162, 0.12);
  color: #0a1628;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.battle-top-expand {
  background: rgba(0, 0, 0, 0.06);
}

.battle-top-bgm {
  background: rgba(0, 0, 0, 0.06);
  font-size: 18px;
}

.battle-top-bar :deep(.battle-top-countdown) {
  padding: 10px 8px 8px;
  background: transparent;
  border-bottom: none;
  box-shadow: none;
}

.battle-top-bar :deep(.battle-top-countdown .turn-timer-title) {
  font-size: 12px;
}

.battle-top-bar :deep(.battle-top-countdown .turn-timer-val) {
  font-size: 14px;
}

.battle-top-bar :deep(.battle-top-countdown .turn-timer-track) {
  height: 8px;
}

.battle-landscape-input {
  width: min(100%, 300px);
  padding: calc(8px * var(--battle-scale)) calc(10px * var(--battle-scale));
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: calc(16px * var(--battle-scale));
  display: flex;
  gap: calc(6px * var(--battle-scale));
  align-items: center;
}

.battle-landscape-input .boss-input-field {
  flex: 1;
  height: calc(36px * var(--battle-scale));
  border: none;
  background: rgba(255, 255, 255, 0.92);
  border-radius: calc(18px * var(--battle-scale));
  padding: 0 calc(14px * var(--battle-scale));
  font-size: calc(14px * var(--battle-scale));
  outline: none;
}

.battle-landscape-input .boss-input-send {
  width: calc(36px * var(--battle-scale));
  height: calc(36px * var(--battle-scale));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  background: #00c2a2;
  color: #fff;
}

.landscape-error {
  color: #ffb4b4;
  text-align: center;
  max-width: 300px;
}

.battle-viewport.is-expanded :deep(.action-cards) {
  width: min(100%, calc(300px * var(--battle-scale)));
  gap: calc(10px * var(--battle-scale));
}

.battle-viewport.is-expanded :deep(.action-card) {
  padding: calc(10px * var(--battle-scale)) calc(8px * var(--battle-scale));
  border-radius: calc(12px * var(--battle-scale));
}

.battle-viewport.is-expanded :deep(.action-emoji) {
  font-size: calc(22px * var(--battle-scale));
}

.battle-viewport.is-expanded :deep(.action-label) {
  font-size: calc(12px * var(--battle-scale));
}

.battle-viewport.is-expanded :deep(.action-desc) {
  font-size: calc(10px * var(--battle-scale));
}

.battle-center {
  position: relative;
  width: 100%;
  height: 100%;
  justify-self: center;
}

.expand-flash {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 50;
  opacity: 0;
  border-radius: 32px;
  background: radial-gradient(circle at 50% 45%, rgba(255, 255, 255, 0.55) 0%, transparent 55%);
}

.battle-viewport.is-expanded .expand-flash {
  border-radius: 0;
}

.battle-stage.is-morphing .expand-flash {
  animation: expandFlash 0.68s var(--morph-ease) forwards;
}

@keyframes expandFlash {
  0% { opacity: 0; }
  18% { opacity: 0.85; }
  100% { opacity: 0; }
}

@keyframes gridDrift {
  from { transform: translate(0, 0); }
  to { transform: translate(48px, 48px); }
}

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
  transition:
    border-radius 0.68s var(--morph-ease),
    box-shadow 0.68s var(--morph-ease);
}

.phone-shell.is-expanded {
  border-radius: 0;
  box-shadow: 0 0 0 1px rgba(0, 194, 162, 0.25), 0 24px 80px rgba(0, 0, 0, 0.45);
}

.battle-viewport.is-expanded .phone-shell.is-expanded {
  border-radius: 0;
}

.battle-stage.is-morphing .phone-shell {
  animation: shellPulse 0.68s var(--morph-ease);
}

@keyframes shellPulse {
  0% { filter: brightness(1); }
  25% { filter: brightness(1.08); }
  100% { filter: brightness(1); }
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
  transition: opacity 0.35s ease, transform 0.5s var(--morph-ease);
}

.phone-shell.is-expanded .phone-notch {
  opacity: 0;
  transform: translateX(-50%) translateY(-120%);
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

.boss-chat {
  background: #f6f6f6;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.boss-header { background: #00c2a2; padding: 8px 16px 12px; color: #fff; }
.boss-header-top { display: flex; align-items: center; justify-content: space-between; }
.boss-header-center { flex: 1; min-width: 0; text-align: center; }
.boss-back { font-size: 18px; width: 28px; cursor: pointer; }
.boss-header-name { font-size: 16px; font-weight: 600; line-height: 1.25; }
.boss-header-tagline { margin-top: 2px; font-size: 11px; line-height: 1.3; opacity: 0.88; font-weight: 500; }

.boss-expand-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.boss-expand-btn:hover {
  background: rgba(255, 255, 255, 0.32);
  box-shadow: 0 0 16px rgba(255, 255, 255, 0.25);
}

.boss-bgm-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 6px;
  color: #fff;
  font-size: 14px;
}

.boss-bgm-btn:hover {
  background: rgba(255, 255, 255, 0.26);
}

.bgm-panel {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;
  background: rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(2px);
}

.bgm-panel-card {
  width: min(360px, calc(100vw - 32px));
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
}

.bgm-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: #0a1628;
  margin-bottom: 10px;
}

.bgm-panel-close {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.06);
  color: #0a1628;
  font-size: 18px;
  cursor: pointer;
}

.bgm-panel-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
}

.bgm-panel-range {
  width: 100%;
}

.bgm-panel-val {
  font-size: 12px;
  font-weight: 700;
  color: #0a1628;
  min-width: 48px;
  text-align: right;
}

.expand-icon {
  position: relative;
  width: 14px;
  height: 14px;
  transition: transform 0.45s var(--morph-ease);
}

.expand-icon span {
  position: absolute;
  width: 5px;
  height: 5px;
  border: 1.5px solid #fff;
  transition: all 0.45s var(--morph-ease);
}

.expand-icon span:nth-child(1) { top: 0; left: 0; border-right: none; border-bottom: none; }
.expand-icon span:nth-child(2) { top: 0; right: 0; border-left: none; border-bottom: none; }
.expand-icon span:nth-child(3) { bottom: 0; left: 0; border-right: none; border-top: none; }
.expand-icon span:nth-child(4) { bottom: 0; right: 0; border-left: none; border-top: none; }

.expand-icon.contracted span:nth-child(1) { transform: translate(3px, 3px); }
.expand-icon.contracted span:nth-child(2) { transform: translate(-3px, 3px); }
.expand-icon.contracted span:nth-child(3) { transform: translate(3px, -3px); }
.expand-icon.contracted span:nth-child(4) { transform: translate(-3px, -3px); }

.boss-company-card {
  background: #fff;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.boss-company-logo { width: 40px; height: 40px; border-radius: 8px; object-fit: cover; flex-shrink: 0; background: #f0f0f0; }
.boss-company-info { flex: 1; min-width: 0; }
.boss-company-name { font-size: 14px; font-weight: 600; color: #1a1a1a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.boss-company-meta { font-size: 11px; color: #999; margin-top: 1px; }
.boss-company-salary { font-size: 15px; font-weight: 700; color: #fa6b3d; }

.boss-sat-bar-wrap { padding: 8px 16px; background: #fff; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 8px; }
.boss-sat-label { font-size: 11px; color: #666; white-space: nowrap; }
.boss-sat-track { flex: 1; height: 6px; background: #e8e8e8; border-radius: 3px; overflow: hidden; }
.boss-sat-fill { height: 100%; background: linear-gradient(90deg, #ff4757, #ffa502, #00c2a2); }
.boss-sat-val { font-size: 12px; font-weight: 700; color: #333; min-width: 24px; text-align: right; }

.card-mode-hint {
  margin: 0;
  padding: 0 16px 6px;
  font-size: 10px;
  color: #999;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.card-mode-hint.urgent {
  color: #c0392b;
  background: #fff8f6;
  font-weight: 600;
}

.card-prelude-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(9, 16, 24, 0.55);
  backdrop-filter: blur(2px);
  pointer-events: none;
  animation: preludeOverlayIn 0.45s ease both;
}

.card-prelude-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 3px solid rgba(255, 71, 87, 0.35);
  border-top-color: #ff4757;
  animation: preludeSpin 0.9s linear infinite;
  box-shadow: 0 0 24px rgba(255, 71, 87, 0.35);
}

.card-prelude-caption {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #ffb4b4;
  letter-spacing: 0.08em;
  animation: preludeCaptionPulse 1.2s ease-in-out infinite;
}

.battle-stage.is-card-prelude .phone-shell {
  animation: preludeShellShake 0.5s ease-in-out 2;
}

@keyframes preludeOverlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes preludeSpin {
  to { transform: rotate(360deg); }
}

@keyframes preludeCaptionPulse {
  0%, 100% { opacity: 0.72; }
  50% { opacity: 1; }
}

@keyframes preludeShellShake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

.boss-hud-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 10px 8px;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f4f8 100%);
  border-bottom: 1px solid #e0e6ed;
  gap: 6px;
}

.boss-hud-item {
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: #fff;
  border-radius: 10px;
  padding: 8px 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  cursor: help;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
  position: relative;
}

.boss-hud-item:hover {
  box-shadow: 0 4px 14px rgba(0, 194, 162, 0.15);
  transform: translateY(-1px);
}

.boss-hud-item::after {
  content: "?";
  position: absolute;
  top: 3px;
  right: 5px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  color: #999;
  font-size: 9px;
  font-weight: 700;
  line-height: 14px;
  text-align: center;
  pointer-events: none;
}

.boss-hud-icon {
  display: block;
  font-size: 15px;
  line-height: 1;
  margin-bottom: 2px;
}

.boss-hud-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #555;
  margin-bottom: 3px;
}

.boss-hud-val {
  display: block;
  font-size: 15px;
  font-weight: 800;
  color: #00c2a2;
}

.boss-chat-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.boss-time-divider { text-align: center; font-size: 11px; color: #bbb; }
.boss-system-msg { text-align: center; font-size: 11px; color: #999; padding: 4px 8px; background: rgba(0, 0, 0, 0.03); border-radius: 4px; align-self: center; max-width: 80%; }
.boss-msg { display: flex; align-items: flex-start; gap: 8px; max-width: 85%; }
.boss-msg.me { align-self: flex-end; flex-direction: row-reverse; }
.boss-msg.hr { align-self: flex-start; }
.boss-msg-avatar { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; flex-shrink: 0; background: #f0f0f0; }
.boss-msg-content { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.boss-msg-role { font-size: 11px; color: #888; line-height: 1.2; padding: 0 2px; }
.boss-msg.me .boss-msg-content { align-items: flex-end; }
.boss-msg-bubble { padding: 10px 14px; border-radius: 8px; font-size: 14px; line-height: 1.5; word-break: break-word; overflow-wrap: anywhere; }
.boss-msg.hr .boss-msg-bubble { background: #fff; border-top-left-radius: 2px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04); }
.boss-msg.me .boss-msg-bubble { background: #00c2a2; color: #fff; border-top-right-radius: 2px; }
.boss-typing-bubble { display: flex; align-items: center; gap: 4px; min-width: 42px; }
.boss-typing-bubble span { width: 6px; height: 6px; border-radius: 50%; background: #b7b7b7; animation: dotPulse 1.1s infinite ease-in-out; }
.boss-typing-bubble span:nth-child(2) { animation-delay: 0.15s; }
.boss-typing-bubble span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.boss-input-area { padding: 8px 10px; background: #f6f6f6; border-top: 1px solid #eee; display: flex; gap: 6px; align-items: center; }
.boss-input-send { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: none; background: #00c2a2; color: #fff; }
.boss-input-field { flex: 1; height: 36px; border: none; background: #fff; border-radius: 18px; padding: 0 14px; font-size: 14px; outline: none; }
.error { margin: 6px 10px 8px; color: #c00; font-size: 12px; }

/* 全屏：组件随 --battle-scale 放大，flex 聊天区自动撑满 */
.battle-viewport.is-expanded .status-bar {
  height: calc(36px * var(--battle-scale));
  padding: 0 calc(24px * var(--battle-scale));
  font-size: calc(11px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-header {
  padding: calc(8px * var(--battle-scale)) calc(16px * var(--battle-scale)) calc(12px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-back {
  font-size: calc(18px * var(--battle-scale));
  width: calc(28px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-header-name {
  font-size: calc(16px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-expand-btn {
  width: calc(28px * var(--battle-scale));
  height: calc(28px * var(--battle-scale));
}

.battle-viewport.is-expanded .expand-icon {
  width: calc(14px * var(--battle-scale));
  height: calc(14px * var(--battle-scale));
}

.battle-viewport.is-expanded .expand-icon span {
  width: calc(5px * var(--battle-scale));
  height: calc(5px * var(--battle-scale));
  border-width: calc(1.5px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-company-card {
  padding: calc(12px * var(--battle-scale)) calc(16px * var(--battle-scale));
  gap: calc(10px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-company-logo {
  width: calc(40px * var(--battle-scale));
  height: calc(40px * var(--battle-scale));
  border-radius: calc(8px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-company-name { font-size: calc(14px * var(--battle-scale)); }
.battle-viewport.is-expanded .boss-company-meta { font-size: calc(11px * var(--battle-scale)); }
.battle-viewport.is-expanded .boss-company-salary { font-size: calc(15px * var(--battle-scale)); }

.battle-viewport.is-expanded .boss-sat-bar-wrap {
  padding: calc(8px * var(--battle-scale)) calc(16px * var(--battle-scale));
  gap: calc(8px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-sat-label { font-size: calc(11px * var(--battle-scale)); }
.battle-viewport.is-expanded .boss-sat-track {
  height: calc(6px * var(--battle-scale));
  border-radius: calc(3px * var(--battle-scale));
}
.battle-viewport.is-expanded .boss-sat-val {
  font-size: calc(12px * var(--battle-scale));
  min-width: calc(24px * var(--battle-scale));
}

.battle-viewport.is-expanded .boss-hud-row {
  padding: calc(6px * var(--battle-scale)) calc(10px * var(--battle-scale));
  gap: calc(8px * var(--battle-scale));
  font-size: calc(10px * var(--battle-scale));
}
</style>
