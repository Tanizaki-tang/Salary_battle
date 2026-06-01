<template>
  <section class="vb-stage">
    <CardGameDeltaFlash :delta="flashDeltaOverlay" :visible="showDeltaFlash" />
    <div class="phone-shell">
      <div class="phone-notch" />
      <div class="status-bar">
        <span>{{ nowTime }}</span>
        <span>📶 🔋</span>
      </div>

      <div class="call-body">
        <div class="call-top">
          <button type="button" class="call-back" @click="router.push('/')">‹</button>
          <div class="call-kpi">
            <span class="kpi-chip" :class="chipFlashClass.salary">💰 {{ salaryHudText }}</span>
            <span class="kpi-chip" :class="chipFlashClass.hours">⏱️ {{ workHoursText }}</span>
            <span class="kpi-chip" :class="chipFlashClass.security">🛡️ {{ securityText }}</span>
          </div>
        </div>

        <div class="call-contact">
          <img class="call-avatar" :src="bossAvatarUrl" alt="HR" />
          <div class="call-name">{{ hrName }}</div>
          <div class="call-sub">
            <span>{{ statusText }}</span>
            <span v-if="running && callTimerText"> · {{ callTimerText }}</span>
          </div>
        </div>

        <div v-if="gamePointHint" class="game-point-tip" :class="gamePointHint.status === 'resolved' ? 'is-resolved' : ''">
          <div class="game-point-tag">
            {{ gamePointHint.status === "resolved" ? "识破成功" : "博弈点提示" }}
          </div>
          <div class="game-point-type">{{ gamePointHint.trap_type }}</div>
          <div class="game-point-text">{{ gamePointHint.explanation }}</div>
        </div>

        <div class="call-chat-shell">
          <div class="chat-head">
            <span>通话转写</span>
            <button type="button" class="chat-toggle" @click="showChat = !showChat">
              {{ showChat ? "收起" : "展开" }}
            </button>
          </div>
          <div v-show="showChat" ref="chatViewport" class="call-chat">
            <div v-if="!bubbles.length" class="chat-empty">接通后，这里会实时显示你和 HR 的对话气泡。</div>
            <div
              v-for="bubble in bubbles"
              :key="bubble.id"
              class="chat-row"
              :class="bubble.role === 'player' ? 'is-me' : 'is-hr'"
            >
              <div class="chat-tag">{{ bubble.role === "player" ? "我" : "HR" }}</div>
              <div class="chat-bubble" :class="bubble.streaming ? 'is-streaming' : ''">
                {{ bubble.text || "…" }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="call-controls">
        <button type="button" class="ctl-btn" :disabled="!running" :class="{ on: !micMuted }" @click="toggleMic">
          <span class="ctl-emoji">🎙️</span>
          <span class="ctl-label">{{ micMuted ? "已静音" : "麦克风" }}</span>
        </button>
        <button
          type="button"
          class="ctl-btn"
          :disabled="!running"
          :class="{ on: speakerOn }"
          @click="toggleSpeaker"
        >
          <span class="ctl-emoji">🔊</span>
          <span class="ctl-label">{{ speakerOn ? "扬声器" : "听筒" }}</span>
        </button>
        <button type="button" class="ctl-btn" :disabled="true">
          <span class="ctl-emoji">⌨️</span>
          <span class="ctl-label">键盘</span>
        </button>
      </div>

      <div class="call-action">
        <button
          type="button"
          class="call-action-btn"
          :class="running ? 'hangup' : 'pickup'"
          @click="running ? stopCall() : startCall()"
        >
          {{ running ? "挂断" : "接听" }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { bossAvatarUrl } from "../assets/avatars";
import CardGameDeltaFlash from "../components/card-game/CardGameDeltaFlash.vue";
import type { CardDeltaView } from "../card-game/types";
import type { GamePointHint, SessionState } from "../runtime/battle_runtime_adapter";
import { Pcm16MicrophoneCapture } from "../runtime/pcm16_capture";
import { PcmStreamPlayer } from "../runtime/pcm_stream_player";
import { connectVoiceBattle } from "../runtime/voice_battle_ws";
import { saveBattleTranscript } from "../utils/battle_transcript";

type VoiceBubble = {
  id: string;
  role: "hr" | "player";
  text: string;
  streaming: boolean;
};

type VoiceKpiDelta = {
  salary_k: number;
  work_hours: number;
  security: number;
};

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => String(route.params.sessionId || ""));

const running = ref(false);
const statusText = ref("未连接");
const session = ref<SessionState | null>(null);
const showChat = ref(true);
const micMuted = ref(false);
const speakerOn = ref(true);
const callStartedAt = ref<number | null>(null);
const nowTime = ref(new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }));
const callElapsedSec = ref(0);
const bubbles = ref<VoiceBubble[]>([]);
const chatViewport = ref<HTMLElement | null>(null);
let clockTimer: number | null = null;
let callTimer: number | null = null;
let currentPlayerBubbleId: string | null = null;
let currentHrBubbleId: string | null = null;
let chipFlashTimer: number | null = null;
let deltaFlashTimer: number | null = null;
const kpiFlashTone = ref<{ salary: "" | "good" | "bad"; hours: "" | "good" | "bad"; security: "" | "good" | "bad" }>({
  salary: "",
  hours: "",
  security: "",
});
const voiceDeltaFlash = ref<VoiceKpiDelta | null>(null);
const showDeltaFlash = ref(false);
const gamePointHint = ref<GamePointHint | null>(null);

const capture = new Pcm16MicrophoneCapture(16000, 40);
const player = new PcmStreamPlayer();
let wsConn: ReturnType<typeof connectVoiceBattle> | null = null;

const callTimerText = computed(() => {
  const sec = callElapsedSec.value;
  if (!running.value || sec <= 0) return "";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const hrName = computed(() => {
  try {
    const raw = sessionStorage.getItem("hrPersonalityMeta");
    if (!raw) return "HR";
    const meta = JSON.parse(raw) as { name?: string; emoji?: string };
    if (meta?.name) return `${meta.emoji || "😊"} ${meta.name}`;
  } catch {
    /* ignore */
  }
  return "HR";
});

function formatMaybeFloat(value: number) {
  if (!Number.isFinite(value)) return "-";
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 1e-6) return String(rounded);
  return value.toFixed(1);
}

const salaryHudText = computed(() => {
  const offer = session.value?.current_salary_offer;
  if (!offer) return "-";
  return `${Math.round(Number(offer) / 1000)}K`;
});

const workHoursText = computed(() => {
  const value = (session.value as SessionState & { work_hours?: number } | null)?.work_hours;
  if (value == null) return "-";
  return formatMaybeFloat(Number(value));
});

const securityText = computed(() => {
  const value = (session.value as SessionState & { security?: number } | null)?.security;
  if (value == null) return "-";
  return formatMaybeFloat(Number(value));
});

const chipFlashClass = computed(() => ({
  salary: kpiFlashTone.value.salary ? `flash-${kpiFlashTone.value.salary}` : "",
  hours: kpiFlashTone.value.hours ? `flash-${kpiFlashTone.value.hours}` : "",
  security: kpiFlashTone.value.security ? `flash-${kpiFlashTone.value.security}` : "",
}));

const flashDeltaOverlay = computed<CardDeltaView | null>(() => {
  const d = voiceDeltaFlash.value;
  if (!d) return null;
  return {
    satisfaction: 0,
    salary_k: d.salary_k,
    work_hours: d.work_hours,
    security: d.security,
  };
});

function asNumber(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toSalaryK(sessionLike: SessionState | null): number | null {
  const offer = asNumber(sessionLike?.current_salary_offer);
  return offer == null ? null : Number((offer / 1000).toFixed(1));
}

function toWorkHours(sessionLike: SessionState | null): number | null {
  return asNumber((sessionLike as SessionState & { work_hours?: number } | null)?.work_hours);
}

function toSecurity(sessionLike: SessionState | null): number | null {
  return asNumber((sessionLike as SessionState & { security?: number } | null)?.security);
}

function computeVoiceKpiDelta(prev: SessionState | null, next: SessionState | null): VoiceKpiDelta | null {
  const salaryPrev = toSalaryK(prev);
  const salaryNext = toSalaryK(next);
  const hoursPrev = toWorkHours(prev);
  const hoursNext = toWorkHours(next);
  const secPrev = toSecurity(prev);
  const secNext = toSecurity(next);

  const delta: VoiceKpiDelta = {
    salary_k: salaryPrev == null || salaryNext == null ? 0 : Number((salaryNext - salaryPrev).toFixed(1)),
    work_hours: hoursPrev == null || hoursNext == null ? 0 : Number((hoursNext - hoursPrev).toFixed(1)),
    security: secPrev == null || secNext == null ? 0 : Number((secNext - secPrev).toFixed(1)),
  };

  if (delta.salary_k === 0 && delta.work_hours === 0 && delta.security === 0) {
    return null;
  }
  return delta;
}

function resetKpiFlash() {
  kpiFlashTone.value = { salary: "", hours: "", security: "" };
}

function triggerKpiEffects(next: SessionState) {
  const delta = computeVoiceKpiDelta(session.value, next);
  if (!delta) return;

  voiceDeltaFlash.value = delta;
  showDeltaFlash.value = false;
  window.requestAnimationFrame(() => {
    showDeltaFlash.value = true;
  });

  kpiFlashTone.value = {
    salary: delta.salary_k > 0 ? "good" : delta.salary_k < 0 ? "bad" : "",
    hours: delta.work_hours > 0 ? "good" : delta.work_hours < 0 ? "bad" : "",
    security: delta.security > 0 ? "good" : delta.security < 0 ? "bad" : "",
  };

  if (deltaFlashTimer != null) window.clearTimeout(deltaFlashTimer);
  deltaFlashTimer = window.setTimeout(() => {
    showDeltaFlash.value = false;
  }, 1450);

  if (chipFlashTimer != null) window.clearTimeout(chipFlashTimer);
  chipFlashTimer = window.setTimeout(() => {
    resetKpiFlash();
  }, 1200);
}

function scrollChatToBottom() {
  window.requestAnimationFrame(() => {
    const el = chatViewport.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  });
}

function snapshotTranscript() {
  return bubbles.value
    .filter((bubble) => bubble.text.trim())
    .map((bubble) => ({
      role: bubble.role === "player" ? "player" : "hr",
      content: bubble.text.trim(),
    }));
}

function persistTranscript() {
  saveBattleTranscript(sessionId.value, snapshotTranscript());
}

function makeBubble(role: "hr" | "player", text = "", streaming = true) {
  const bubble: VoiceBubble = {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    text,
    streaming,
  };
  bubbles.value.push(bubble);
  scrollChatToBottom();
  return bubble.id;
}

function findBubble(id: string | null) {
  if (!id) return null;
  return bubbles.value.find((bubble) => bubble.id === id) || null;
}

function updatePlayerPartial(text: string) {
  if (!text.trim()) return;
  if (!currentPlayerBubbleId) {
    currentPlayerBubbleId = makeBubble("player", text, true);
  }
  const bubble = findBubble(currentPlayerBubbleId);
  if (!bubble) return;
  bubble.text = text;
  bubble.streaming = true;
  statusText.value = "你正在说话…";
  scrollChatToBottom();
}

function finalizePlayerText(text: string) {
  if (!text.trim()) return;
  if (!currentPlayerBubbleId) {
    currentPlayerBubbleId = makeBubble("player", text, true);
  }
  const bubble = findBubble(currentPlayerBubbleId);
  if (!bubble) return;
  bubble.text = text;
  bubble.streaming = false;
  currentPlayerBubbleId = null;
  persistTranscript();
  scrollChatToBottom();
}

function startHrBubble() {
  currentHrBubbleId = makeBubble("hr", "", true);
  statusText.value = "HR 回复中…";
}

function appendHrDelta(text: string) {
  if (!text) return;
  if (!currentHrBubbleId) {
    startHrBubble();
  }
  const bubble = findBubble(currentHrBubbleId);
  if (!bubble) return;
  bubble.text += text;
  bubble.streaming = true;
  scrollChatToBottom();
}

function finalizeHrText(text?: string) {
  const bubble = findBubble(currentHrBubbleId);
  if (!bubble) return;
  if (text?.trim()) {
    bubble.text = text;
  }
  bubble.streaming = false;
  currentHrBubbleId = null;
  persistTranscript();
  statusText.value = "通话中";
  scrollChatToBottom();
}

function restoreOpeningAndSession() {
  bubbles.value = [];
  currentPlayerBubbleId = null;
  currentHrBubbleId = null;
  const rawSession = sessionStorage.getItem("currentSession");
  if (rawSession) {
    try {
      session.value = JSON.parse(rawSession) as SessionState;
    } catch {
      session.value = null;
    }
  }
  const opening = (sessionStorage.getItem("hrOpening") || "").trim();
  if (opening) {
    bubbles.value.push({
      id: "opening-hr",
      role: "hr",
      text: opening,
      streaming: false,
    });
  }
  persistTranscript();
}

function toggleMic() {
  micMuted.value = !micMuted.value;
}

function toggleSpeaker() {
  speakerOn.value = !speakerOn.value;
}

function startTimers() {
  if (clockTimer == null) {
    clockTimer = window.setInterval(() => {
      nowTime.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    }, 1000);
  }
  if (callTimer == null) {
    callTimer = window.setInterval(() => {
      if (!callStartedAt.value) return;
      callElapsedSec.value = Math.max(0, Math.floor((Date.now() - callStartedAt.value) / 1000));
    }, 300);
  }
}

function stopTimers() {
  if (callTimer != null) {
    window.clearInterval(callTimer);
    callTimer = null;
  }
  if (clockTimer != null) {
    window.clearInterval(clockTimer);
    clockTimer = null;
  }
  if (chipFlashTimer != null) {
    window.clearTimeout(chipFlashTimer);
    chipFlashTimer = null;
  }
  if (deltaFlashTimer != null) {
    window.clearTimeout(deltaFlashTimer);
    deltaFlashTimer = null;
  }
}

function shutdownRealtime() {
  capture.stop();
  wsConn?.close();
  wsConn = null;
  player.stop();
}

function finishBattleAndGoResult() {
  if (session.value) {
    sessionStorage.setItem("currentSession", JSON.stringify(session.value));
  }
  persistTranscript();
  shutdownRealtime();
  running.value = false;
  callStartedAt.value = null;
  callElapsedSec.value = 0;
  stopTimers();
  router.push(`/result/${sessionId.value}`);
}

async function startCall() {
  if (running.value) return;
  running.value = true;
  statusText.value = "连接中…";
  callElapsedSec.value = 0;
  callStartedAt.value = null;
  micMuted.value = false;
  speakerOn.value = true;
  restoreOpeningAndSession();
  startTimers();

  wsConn = connectVoiceBattle(sessionId.value, {
    onEvent: (evt) => {
      if (evt.type === "ready") {
        statusText.value = "通话中";
        callStartedAt.value = Date.now();
      } else if (evt.type === "asr.partial") {
        updatePlayerPartial(evt.text);
      } else if (evt.type === "asr.final") {
        finalizePlayerText(evt.text);
      } else if (evt.type === "hr.text.start") {
        startHrBubble();
      } else if (evt.type === "hr.text.delta") {
        appendHrDelta(evt.text);
      } else if (evt.type === "hr.text.done") {
        finalizeHrText(evt.text);
      } else if (evt.type === "hr.audio.delta") {
        if (speakerOn.value) {
          player.playPcm16Base64(evt.audio_b64, evt.sample_rate);
        }
      } else if (evt.type === "turn.done") {
        triggerKpiEffects(evt.session);
        session.value = evt.session;
        gamePointHint.value = evt.result.game_point_hint || null;
        sessionStorage.setItem("currentSession", JSON.stringify(evt.session));
        if (evt.flow?.should_end || evt.session.status === "settled") {
          finishBattleAndGoResult();
        }
      } else if (evt.type === "error") {
        statusText.value = evt.message;
      }
    },
  });

  wsConn.ws.onopen = async () => {
    try {
      await capture.start({
        onFrame: (pcm16) => {
          if (micMuted.value) return;
          wsConn?.sendAudio(pcm16);
        },
      });
    } catch (e) {
      statusText.value = `麦克风不可用：${String(e)}`;
      stopCall();
    }
  };

  wsConn.ws.onclose = () => {
    if (running.value) statusText.value = "连接已断开";
    running.value = false;
    callStartedAt.value = null;
    callElapsedSec.value = 0;
  };
}

function stopCall() {
  if (!running.value) return;
  running.value = false;
  statusText.value = "通话已结束";
  shutdownRealtime();
  callStartedAt.value = null;
  callElapsedSec.value = 0;
  stopTimers();
  persistTranscript();
}

onMounted(() => {
  restoreOpeningAndSession();
  startTimers();
});

onUnmounted(() => {
  if (running.value) {
    shutdownRealtime();
  } else {
    player.stop();
  }
  stopTimers();
});
</script>

<style scoped>
.vb-stage {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background:
    radial-gradient(ellipse 90% 70% at 50% 0%, rgba(0, 194, 162, 0.22), transparent 60%),
    radial-gradient(ellipse 70% 60% at 100% 100%, rgba(250, 107, 61, 0.14), transparent 55%),
    linear-gradient(160deg, #0a1628 0%, #0d2137 45%, #091018 100%);
}

.phone-shell {
  width: 375px;
  height: 700px;
  border-radius: 32px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45), 0 0 0 2px #1a1a1a;
  background: rgba(10, 22, 40, 0.96);
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
  z-index: 20;
}

.status-bar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.call-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 10px 18px 0;
  position: relative;
}

.call-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.call-back {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
  font-size: 22px;
}

.call-kpi {
  display: flex;
  gap: 8px;
  min-width: 0;
  justify-content: flex-end;
}

.kpi-chip {
  padding: 6px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  font-weight: 700;
  transition:
    transform 0.24s ease,
    box-shadow 0.24s ease,
    border-color 0.24s ease,
    background 0.24s ease;
}

.kpi-chip.flash-good {
  animation: kpiPulseGood 0.95s cubic-bezier(0.22, 1, 0.36, 1);
  border-color: rgba(123, 237, 159, 0.7);
  background: rgba(123, 237, 159, 0.16);
  box-shadow: 0 0 0 1px rgba(123, 237, 159, 0.15), 0 8px 24px rgba(123, 237, 159, 0.2);
}

.kpi-chip.flash-bad {
  animation: kpiPulseBad 0.95s cubic-bezier(0.22, 1, 0.36, 1);
  border-color: rgba(255, 107, 129, 0.7);
  background: rgba(255, 107, 129, 0.16);
  box-shadow: 0 0 0 1px rgba(255, 107, 129, 0.14), 0 8px 24px rgba(255, 107, 129, 0.2);
}

.call-contact {
  padding-top: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.call-avatar {
  width: 112px;
  height: 112px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.35);
  border: 2px solid rgba(255, 255, 255, 0.18);
}

.call-name {
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.call-sub {
  color: rgba(255, 255, 255, 0.75);
  font-size: 12px;
  font-weight: 600;
}

.call-chat-shell {
  margin-top: 16px;
  flex: 1;
  min-height: 0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.game-point-tip {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(250, 107, 61, 0.12);
  border: 1px solid rgba(250, 107, 61, 0.26);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
}

.game-point-tip.is-resolved {
  background: rgba(46, 213, 115, 0.12);
  border-color: rgba(46, 213, 115, 0.26);
}

.game-point-tag {
  font-size: 11px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.08em;
}

.game-point-type {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}

.game-point-text {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.82);
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  font-weight: 800;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.chat-toggle {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.74);
  font-size: 11px;
  font-weight: 700;
}

.call-chat {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-empty {
  color: rgba(255, 255, 255, 0.58);
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
  padding: 22px 12px;
}

.chat-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-row.is-me {
  justify-content: flex-end;
}

.chat-tag {
  min-width: 28px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.86);
  background: rgba(255, 255, 255, 0.1);
}

.chat-row.is-me .chat-tag {
  order: 2;
  background: rgba(0, 194, 162, 0.22);
}

.chat-row.is-hr .chat-tag {
  background: rgba(250, 107, 61, 0.22);
}

.chat-bubble {
  max-width: 78%;
  padding: 10px 12px;
  border-radius: 16px;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.94);
  background: rgba(255, 255, 255, 0.1);
  word-break: break-word;
  white-space: pre-wrap;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.chat-row.is-me .chat-bubble {
  background: linear-gradient(135deg, rgba(0, 194, 162, 0.8), rgba(46, 213, 115, 0.72));
}

.chat-row.is-hr .chat-bubble {
  background: rgba(255, 255, 255, 0.12);
}

.chat-bubble.is-streaming::after {
  content: " ·";
  opacity: 0.8;
  animation: blink 1s steps(1) infinite;
}

.call-controls {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  padding: 10px 22px 0;
}

.ctl-btn {
  border: none;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 10px;
}

.ctl-btn:disabled {
  opacity: 0.45;
}

.ctl-btn.on {
  background: rgba(0, 194, 162, 0.16);
  border-color: rgba(0, 194, 162, 0.28);
}

.ctl-emoji {
  font-size: 22px;
}

.ctl-label {
  font-size: 11px;
  font-weight: 800;
}

.call-action {
  padding: 14px 22px 22px;
}

.call-action-btn {
  width: 100%;
  height: 56px;
  border-radius: 999px;
  border: none;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.06em;
  color: #fff;
}

.call-action-btn.pickup {
  background: linear-gradient(135deg, #00c2a2 0%, #2ed573 100%);
}

.call-action-btn.hangup {
  background: linear-gradient(135deg, #ff4757 0%, #fa6b3d 100%);
}

@keyframes blink {
  50% {
    opacity: 0.25;
  }
}

@keyframes kpiPulseGood {
  0% {
    transform: scale(1);
  }
  35% {
    transform: translateY(-2px) scale(1.08);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes kpiPulseBad {
  0% {
    transform: scale(1);
  }
  20% {
    transform: translateX(-2px) scale(1.04);
  }
  40% {
    transform: translateX(2px) scale(1.04);
  }
  100% {
    transform: scale(1);
  }
}

@media (max-width: 420px) {
  .vb-stage {
    padding: 0;
  }
  .phone-shell {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
    box-shadow: none;
  }
  .phone-notch {
    top: 0;
  }
}
</style>
